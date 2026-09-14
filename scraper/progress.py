"""抓取进度记录与断点续接。

三份持久化状态互相配合，保证任意时刻中断都能精确续跑：

====================  ==========================  ==============================
文件                  作用                        续跑时的行为
====================  ==========================  ==============================
``state/cache/``      HTML / 图片原始响应缓存      命中则零网络请求
``state/progress.json`` 每个抓取单元的状态机        已完成项直接跳过
``state/manifest.json`` 内容级单一事实源            决定产物如何重新生成
====================  ==========================  ==============================

``progress.json`` 采用**原子写入**（同目录临时文件 + ``os.replace``），
因此进程被 Ctrl-C / 断网 / 熔断中断时，状态文件不会损坏。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from tqdm import tqdm

from .config import CONFIG, Config
from .util import human_duration, now_iso, read_json, truncate, write_json

log = logging.getLogger("usagi.progress")

T = TypeVar("T")

PROGRESS_VERSION = 1

# 解析器/转换器的语义版本。
#
# 修改了选择器、转换规则或生成逻辑后**递增此值**，会让此前标记为"已完成"
# 的单元自动失效并重跑一遍。因为原始 HTML 都在磁盘缓存里，重跑只走本地解析、
# 不产生任何网络请求 —— 相当于"免费地"用新解析器重刷全站。
#
# 这样就不必依赖使用者记得加 --force。
PARSER_REVISION = 3


class ItemStatus(StrEnum):
    """单个抓取单元的状态。"""

    DONE = "done"
    """已成功抓取并归档。"""

    UNAVAILABLE = "unavailable"
    """源站与 archive.org 均不可得，已记录标记，不再重试。"""

    FAILED = "failed"
    """抓取出错，下次运行会重试。"""

    SKIPPED = "skipped"
    """按策略主动跳过（例如本次未启用该阶段）。"""

    @property
    def terminal(self) -> bool:
        """是否为"不需要再重试"的终态。"""
        return self in {ItemStatus.DONE, ItemStatus.UNAVAILABLE, ItemStatus.SKIPPED}


@dataclass
class ItemRecord:
    """一个抓取单元的进度记录。"""

    key: str
    stage: str = ""
    status: str = str(ItemStatus.FAILED)
    attempts: int = 0
    updated_at: str = ""
    detail: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, key: str, data: dict[str, Any]) -> "ItemRecord":
        return cls(
            key=key,
            stage=str(data.get("stage", "")),
            status=str(data.get("status", ItemStatus.FAILED)),
            attempts=int(data.get("attempts", 0)),
            updated_at=str(data.get("updatedAt", "")),
            detail=str(data.get("detail", "")),
            meta=dict(data.get("meta") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "attempts": self.attempts,
            "updatedAt": self.updated_at,
            "detail": self.detail,
            "meta": self.meta,
        }


class ProgressStore:
    """断点续接的进度库。

    ``readonly=True`` 时仍然**读取**已有进度（因此已完成项照常跳过），
    但任何 ``mark_*`` 都只改内存、不落盘。

    离线模式（``--offline``）必须用只读模式：那时"缓存未命中"只是本地还没有
    这份数据，并不代表源站不可得。若照常落盘，一次离线运行就会把整站标成
    "原站不可访问"，既污染进度、又让不可访问清单失真。
    """

    def __init__(
        self, path: Path | None = None, cfg: Config = CONFIG, *, readonly: bool = False
    ) -> None:
        self.cfg = cfg
        self.path = path or cfg.progress_path
        self.readonly = readonly
        self._items: dict[str, ItemRecord] = {}
        self._stages: dict[str, dict[str, int]] = {}
        self._dirty = 0
        self._started_at = now_iso()
        self.load()

    # ------------------------------------------------------------ 加载与保存

    def load(self) -> None:
        data = read_json(self.path, default=None)
        if not isinstance(data, dict):
            self._items = {}
            return

        stored_revision = data.get("parserRevision")
        raw_items = data.get("items")
        if isinstance(raw_items, dict):
            self._items = {
                key: ItemRecord.from_dict(key, value)
                for key, value in raw_items.items()
                if isinstance(value, dict)
            }

        # 解析器语义变了 → 旧结果不可信，全部作废重跑（走本地缓存，零请求）
        if stored_revision != PARSER_REVISION:
            stale = len(self._items)
            self._items.clear()
            self._dirty = self.cfg.progress_autosave_every
            if stale:
                log.warning(
                    "解析器版本已从 %s 变更为 %s，%d 条旧进度作废，将用新解析器重跑"
                    "（原始内容在本地缓存中，不会产生额外网络请求）",
                    stored_revision,
                    PARSER_REVISION,
                    stale,
                )
            self.save(force=True)

        log.debug("已载入进度：%d 条记录", len(self._items))

    def save(self, *, force: bool = False) -> None:
        """原子落盘。默认按 ``progress_autosave_every`` 节流。"""
        if self.readonly:
            return
        if not force and self._dirty < self.cfg.progress_autosave_every:
            return
        payload = {
            "version": PROGRESS_VERSION,
            "parserRevision": PARSER_REVISION,
            "site": self.cfg.site_url,
            "startedAt": self._started_at,
            "updatedAt": now_iso(),
            "totals": self.totals(),
            "items": {key: record.to_dict() for key, record in sorted(self._items.items())},
        }
        write_json(self.path, payload)
        self._dirty = 0
        log.debug("进度已保存：%d 条", len(self._items))

    # ------------------------------------------------------------------ 查询

    def get(self, key: str) -> ItemRecord | None:
        return self._items.get(key)

    def status_of(self, key: str) -> str | None:
        record = self._items.get(key)
        return record.status if record else None

    def is_done(self, key: str) -> bool:
        record = self._items.get(key)
        return bool(record and record.status == ItemStatus.DONE)

    def is_terminal(self, key: str) -> bool:
        record = self._items.get(key)
        return bool(record and ItemStatus(record.status).terminal)

    def pending(
        self,
        keys: Iterable[str],
        *,
        recheck_failed: bool = True,
        recheck_unavailable: bool = False,
        recheck_done: bool = False,
    ) -> list[str]:
        """从给定 key 集合中筛出仍需处理的部分（断点续接的核心）。

        :param recheck_failed: 上次失败的项是否重试（默认重试）。
        :param recheck_unavailable: 已标记不可得的项是否重新探测
            （默认否；``--recheck-unavailable`` 可开启）。
        :param recheck_done: 已完成的项是否强制重抓（``--force``）。
        """
        result: list[str] = []
        for key in keys:
            record = self._items.get(key)
            if record is None:
                result.append(key)
                continue
            status = record.status
            if status == ItemStatus.DONE:
                if recheck_done:
                    result.append(key)
            elif status == ItemStatus.UNAVAILABLE:
                if recheck_unavailable:
                    result.append(key)
            elif status == ItemStatus.SKIPPED:
                if recheck_done:
                    result.append(key)
            else:  # FAILED
                if recheck_failed:
                    result.append(key)
        return result

    # ------------------------------------------------------------------ 记录

    def mark(
        self,
        key: str,
        status: ItemStatus | str,
        *,
        stage: str = "",
        detail: str = "",
        **meta: Any,
    ) -> ItemRecord:
        """记录一个抓取单元的状态。"""
        value = str(status)
        record = self._items.get(key)
        if record is None:
            record = ItemRecord(key=key, stage=stage, attempts=0)
            self._items[key] = record
        record.stage = stage or record.stage
        record.status = value
        record.attempts += 1
        record.updated_at = now_iso()
        if detail:
            record.detail = detail
        if meta:
            record.meta.update(meta)
        self._dirty += 1
        self.save()
        return record

    def mark_done(self, key: str, *, stage: str = "", detail: str = "", **meta: Any) -> None:
        self.mark(key, ItemStatus.DONE, stage=stage, detail=detail, **meta)

    def mark_failed(self, key: str, error: str, *, stage: str = "") -> None:
        self.mark(key, ItemStatus.FAILED, stage=stage, detail=truncate(error, 200))

    def mark_unavailable(self, key: str, detail: str = "", *, stage: str = "") -> None:
        self.mark(key, ItemStatus.UNAVAILABLE, stage=stage, detail=truncate(detail, 200))

    def mark_skipped(self, key: str, reason: str = "", *, stage: str = "") -> None:
        self.mark(key, ItemStatus.SKIPPED, stage=stage, detail=truncate(reason, 200))

    # ------------------------------------------------------------------ 汇总

    def totals(self) -> dict[str, int]:
        counts = {str(status): 0 for status in ItemStatus}
        for record in self._items.values():
            counts[record.status] = counts.get(record.status, 0) + 1
        return counts

    def stage_stats(self) -> dict[str, dict[str, int]]:
        """按阶段汇总：``{stage: {status: count}}``。"""
        stats: dict[str, dict[str, int]] = {}
        for record in self._items.values():
            bucket = stats.setdefault(record.stage or "(未分类)", {})
            bucket[record.status] = bucket.get(record.status, 0) + 1
        return stats

    def failures(self) -> list[ItemRecord]:
        return [r for r in self._items.values() if r.status == ItemStatus.FAILED]

    def unavailable(self) -> list[ItemRecord]:
        return [r for r in self._items.values() if r.status == ItemStatus.UNAVAILABLE]

    def report(self) -> str:
        """产出 Markdown 格式的进度报告。"""
        totals = self.totals()
        lines = [
            "# 抓取进度报告",
            "",
            f"- 站点：{self.cfg.site_url}",
            f"- 本次开始：{self._started_at}",
            f"- 生成时间：{now_iso()}",
            f"- 已记录单元：{len(self._items)}",
            "",
            "## 状态汇总",
            "",
            "| 状态 | 数量 |",
            "| --- | ---: |",
        ]
        labels = {
            str(ItemStatus.DONE): "已完成",
            str(ItemStatus.UNAVAILABLE): "不可访问（已标记）",
            str(ItemStatus.FAILED): "失败（下次重试）",
            str(ItemStatus.SKIPPED): "已跳过",
        }
        for status, label in labels.items():
            lines.append(f"| {label} | {totals.get(status, 0)} |")

        lines += ["", "## 分阶段", "", "| 阶段 | 完成 | 不可访问 | 失败 | 跳过 |", "| --- | ---: | ---: | ---: | ---: |"]
        for stage, bucket in sorted(self.stage_stats().items()):
            lines.append(
                f"| {stage} | {bucket.get(str(ItemStatus.DONE), 0)} "
                f"| {bucket.get(str(ItemStatus.UNAVAILABLE), 0)} "
                f"| {bucket.get(str(ItemStatus.FAILED), 0)} "
                f"| {bucket.get(str(ItemStatus.SKIPPED), 0)} |"
            )

        failures = self.failures()
        if failures:
            lines += ["", "## 待重试项", "", "| Key | 阶段 | 次数 | 说明 |", "| --- | --- | ---: | --- |"]
            for record in failures[:100]:
                lines.append(
                    f"| `{record.key}` | {record.stage} | {record.attempts} | {record.detail} |"
                )
            if len(failures) > 100:
                lines.append(f"| … | 其余 {len(failures) - 100} 项略 | | |")

        unavailable = self.unavailable()
        if unavailable:
            lines += ["", "## 不可访问项", "", "| Key | 阶段 | 说明 |", "| --- | --- | --- |"]
            for record in unavailable[:100]:
                lines.append(f"| `{record.key}` | {record.stage} | {record.detail} |")
            if len(unavailable) > 100:
                lines.append(f"| … | 其余 {len(unavailable) - 100} 项略 | |")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------ 维护

    def reset(self, *, stages: Sequence[str] | None = None, keys: Sequence[str] | None = None) -> int:
        """清除进度记录。返回被清除的条数。"""
        removed = 0
        if keys:
            for key in keys:
                if self._items.pop(key, None) is not None:
                    removed += 1
        elif stages:
            for key in [k for k, r in self._items.items() if r.stage in stages]:
                del self._items[key]
                removed += 1
        else:
            removed = len(self._items)
            self._items.clear()
        self._dirty = self.cfg.progress_autosave_every
        self.save(force=True)
        return removed


# ------------------------------------------------------------------ 阶段执行器


@dataclass
class StageResult:
    """一个阶段的执行结果。"""

    stage: str
    total: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    elapsed: float = 0.0

    @property
    def summary(self) -> str:
        return (
            f"{self.stage}: 处理 {self.processed}/{self.total}"
            f"（跳过已完成 {self.skipped}，失败 {self.failed}）"
            f" 用时 {human_duration(self.elapsed)}"
        )


class StageRunner:
    """带进度条、自动跳过已完成项、失败不中断的阶段执行器。"""

    def __init__(
        self,
        store: ProgressStore,
        stage: str,
        *,
        cfg: Config = CONFIG,
        show_progress: bool = True,
        recheck_unavailable: bool = False,
        recheck_done: bool = False,
    ) -> None:
        self.store = store
        self.stage = stage
        self.cfg = cfg
        self.show_progress = show_progress
        self.recheck_unavailable = recheck_unavailable
        self.recheck_done = recheck_done

    def run(
        self,
        items: Sequence[T],
        handler: Callable[[T], None],
        key_of: Callable[[T], str],
        *,
        desc: str | None = None,
        on_unavailable: Callable[[T, str], None] | None = None,
    ) -> StageResult:
        """依次处理 items，自动跳过已完成项。

        ``handler`` 抛出的 ``CircuitBreakerOpen`` 会向上冒泡（立即停止），
        其他异常记为失败并继续，保证单个坏页面不阻塞整体归档。
        """
        started = time.monotonic()
        result = StageResult(stage=self.stage, total=len(items))

        all_keys = [key_of(item) for item in items]
        pending_keys = set(
            self.store.pending(
                all_keys,
                recheck_unavailable=self.recheck_unavailable,
                recheck_done=self.recheck_done,
            )
        )
        result.skipped = len(items) - len(pending_keys)

        todo = [item for item in items if key_of(item) in pending_keys]
        if not todo:
            result.elapsed = time.monotonic() - started
            log.info("%s：全部已完成，跳过（%d 项）", self.stage, result.total)
            return result

        iterator: Iterator[T] = iter(todo)
        bar = None
        if self.show_progress:
            # 必须把真正要遍历的 todo 交给 tqdm。
            # 只传 total 再迭代 bar 本身是不行的：tqdm.__iter__ 会去
            # ``for obj in self.iterable``，而 iterable 是 None，
            # 于是抛 ``TypeError: 'NoneType' object is not iterable``。
            bar = tqdm(
                todo,
                total=len(todo),
                desc=desc or self.stage,
                unit="项",
                dynamic_ncols=True,
                leave=True,
            )
            iterator = bar  # type: ignore[assignment]

        try:
            for item in iterator:
                key = key_of(item)
                try:
                    handler(item)
                    # 兜底标记：handler 通常已自行 mark_done / mark_unavailable
                    # 并附带 detail/meta，此时不覆盖；若 handler 漏标，这里补上
                    # 以保证断点续接可靠。
                    #
                    # 判断依据必须是"终态"而不是"done"：handler 主动标记的
                    # unavailable / skipped 也是终态，用 is_done 会把它们改写成
                    # done，导致 --recheck-unavailable 永远筛不出这些条目、
                    # 不可访问清单也会变空。
                    if not self.store.is_terminal(key):
                        self.store.mark_done(key, stage=self.stage)
                    result.processed += 1
                except Exception as exc:  # noqa: BLE001 - 单点失败不阻塞整体
                    from .http_client import CircuitBreakerOpen

                    if isinstance(exc, CircuitBreakerOpen):
                        raise
                    result.failed += 1
                    self.store.mark_failed(key, str(exc), stage=self.stage)
                    log.warning("失败 %s：%s", key, exc)
                    if bar is not None:
                        bar.set_postfix_str(f"失败 {result.failed}", refresh=False)
        finally:
            if bar is not None:
                bar.close()
            self.store.save(force=True)

        result.elapsed = time.monotonic() - started
        log.info(result.summary)
        return result
