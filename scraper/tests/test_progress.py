"""进度记录与断点续接测试。

断点续接是长期维护的核心能力，这里把状态机行为全部钉死。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scraper.progress import (
    PARSER_REVISION,
    ItemStatus,
    ProgressStore,
    StageRunner,
)


class TestProgressStore:
    def test_new_store_is_empty(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        assert store.totals()[str(ItemStatus.DONE)] == 0

    def test_mark_done_and_persist(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("note:1", stage="notes", detail="标题")
        store.save(force=True)

        reloaded = ProgressStore(cfg=cfg)
        assert reloaded.is_done("note:1")
        assert reloaded.get("note:1").stage == "notes"
        assert reloaded.get("note:1").detail == "标题"

    def test_mark_failed_keeps_detail(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_failed("note:2", "连接超时", stage="notes")
        store.save(force=True)
        record = ProgressStore(cfg=cfg).get("note:2")
        assert record.status == str(ItemStatus.FAILED)
        assert "连接超时" in record.detail

    def test_attempts_increment(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_failed("note:3", "err", stage="notes")
        store.mark_failed("note:3", "err", stage="notes")
        store.mark_done("note:3", stage="notes")
        assert store.get("note:3").attempts == 3

    def test_metadata_stored(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("note:4", stage="notes", images=3)
        assert store.get("note:4").meta["images"] == 3

    def test_atomic_write_leaves_valid_json(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        for index in range(5):
            store.mark_done(f"note:{index}", stage="notes")
        store.save(force=True)
        payload = json.loads(cfg.progress_path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert len(payload["items"]) == 5

    def test_corrupted_file_recovers(self, cfg) -> None:
        cfg.progress_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.progress_path.write_text("{ 坏掉的 json", encoding="utf-8")
        store = ProgressStore(cfg=cfg)
        assert store.totals()[str(ItemStatus.DONE)] == 0


class TestPending:
    """pending() 决定断点续接时哪些项需要处理。"""

    def test_unknown_keys_are_pending(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        assert store.pending(["a", "b"]) == ["a", "b"]

    def test_done_keys_skipped(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("a", stage="s")
        assert store.pending(["a", "b"]) == ["b"]

    def test_failed_keys_retried_by_default(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_failed("a", "err", stage="s")
        assert store.pending(["a"]) == ["a"]

    def test_failed_keys_can_be_skipped(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_failed("a", "err", stage="s")
        assert store.pending(["a"], recheck_failed=False) == []

    def test_unavailable_not_retried_by_default(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_unavailable("a", "403", stage="s")
        assert store.pending(["a"]) == []

    def test_unavailable_rechecked_on_demand(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_unavailable("a", "403", stage="s")
        assert store.pending(["a"], recheck_unavailable=True) == ["a"]

    def test_force_rechecks_done(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("a", stage="s")
        assert store.pending(["a"], recheck_done=True) == ["a"]

    def test_preserves_input_order(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("b", stage="s")
        assert store.pending(["a", "b", "c"]) == ["a", "c"]


class TestReset:
    def test_reset_all(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("a", stage="s1")
        store.mark_done("b", stage="s2")
        assert store.reset() == 2
        assert ProgressStore(cfg=cfg).totals()[str(ItemStatus.DONE)] == 0

    def test_reset_by_stage(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("a", stage="s1")
        store.mark_done("b", stage="s2")
        assert store.reset(stages=["s1"]) == 1
        reloaded = ProgressStore(cfg=cfg)
        assert not reloaded.is_done("a")
        assert reloaded.is_done("b")


class TestReport:
    def test_report_contains_sections(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("note:1", stage="notes")
        store.mark_unavailable("note:2", "403", stage="notes")
        store.mark_failed("note:3", "超时", stage="notes")
        report = store.report()
        assert "# 抓取进度报告" in report
        assert "notes" in report
        assert "待重试项" in report
        assert "不可访问项" in report

    def test_stage_stats(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("a", stage="s1")
        store.mark_failed("b", "出错", stage="s1")
        store.mark_done("c", stage="s2")
        stats = store.stage_stats()
        assert stats["s1"][str(ItemStatus.DONE)] == 1
        assert stats["s1"][str(ItemStatus.FAILED)] == 1
        assert stats["s2"][str(ItemStatus.DONE)] == 1


class TestStageRunner:
    def test_processes_all_items(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        seen: list[str] = []
        result = runner.run(["a", "b", "c"], seen.append, lambda x: f"k:{x}")
        assert sorted(seen) == ["a", "b", "c"]
        assert result.processed == 3
        assert result.failed == 0

    def test_skips_already_done(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        store.mark_done("k:a", stage="s")
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        seen: list[str] = []
        result = runner.run(["a", "b"], seen.append, lambda x: f"k:{x}")
        assert seen == ["b"]
        assert result.skipped == 1
        assert result.processed == 1

    def test_failure_does_not_abort_batch(self, cfg) -> None:
        """单个坏页面不能阻塞整体归档。"""
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        seen: list[str] = []

        def handler(item: str) -> None:
            if item == "b":
                raise RuntimeError("坏页面")
            seen.append(item)

        result = runner.run(["a", "b", "c"], handler, lambda x: f"k:{x}")
        assert seen == ["a", "c"]
        assert result.processed == 2
        assert result.failed == 1
        assert store.get("k:b").status == str(ItemStatus.FAILED)

    def test_circuit_breaker_propagates(self, cfg) -> None:
        from scraper.http_client import CircuitBreakerOpen

        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)

        def handler(item: str) -> None:
            raise CircuitBreakerOpen("https://x/", "熔断", 403)

        with pytest.raises(CircuitBreakerOpen):
            runner.run(["a"], handler, lambda x: f"k:{x}")

    def test_marks_done_even_if_handler_forgets(self, cfg) -> None:
        """handler 未自行标记时，StageRunner 必须兜底标记以保证续跑可靠。"""
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        runner.run(["a", "b"], lambda item: None, lambda x: f"k:{x}")
        assert store.is_done("k:a")
        assert store.is_done("k:b")
        assert store.pending(["k:a", "k:b"]) == []

    def test_handler_detail_not_overwritten(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)

        def handler(item: str) -> None:
            store.mark_done(f"k:{item}", stage="s", detail="handler 给的说明")

        runner.run(["a"], handler, lambda x: f"k:{x}")
        assert store.get("k:a").detail == "handler 给的说明"

    def test_resumable_across_runs(self, cfg) -> None:
        """第一次跑到一半中断，第二次只处理剩余项。"""
        items = [f"n{i}" for i in range(10)]

        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        first: list[str] = []

        def flaky(item: str) -> None:
            if len(first) >= 4:
                raise KeyboardInterrupt
            first.append(item)

        with pytest.raises(KeyboardInterrupt):
            runner.run(items, flaky, lambda x: f"k:{x}")
        store.save(force=True)

        store2 = ProgressStore(cfg=cfg)
        runner2 = StageRunner(store2, "s", cfg=cfg, show_progress=False)
        second: list[str] = []
        result = runner2.run(items, second.append, lambda x: f"k:{x}")

        assert len(first) == 4
        assert len(second) == 6
        assert set(first).isdisjoint(second)
        assert result.skipped == 4
        assert result.processed == 6


class TestParserRevisionInvalidation:
    """解析器语义变更后，旧进度必须自动作废重跑。

    否则修好选择器后，旧的错误结果会一直因为"已完成"而被跳过。
    由于原始 HTML 都在磁盘缓存里，重跑只走本地解析、不产生网络请求。
    """

    def _write_progress(self, cfg, revision, items) -> None:
        import json

        cfg.progress_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.progress_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "parserRevision": revision,
                    "site": cfg.site_url,
                    "items": items,
                }
            ),
            encoding="utf-8",
        )

    def test_same_revision_keeps_progress(self, cfg) -> None:
        self._write_progress(
            cfg, PARSER_REVISION, {"note:1": {"stage": "notes", "status": "done"}}
        )
        store = ProgressStore(cfg=cfg)
        assert store.is_done("note:1")

    def test_older_revision_invalidates(self, cfg) -> None:
        self._write_progress(
            cfg, PARSER_REVISION - 1, {"note:1": {"stage": "notes", "status": "done"}}
        )
        store = ProgressStore(cfg=cfg)
        assert not store.is_done("note:1")
        assert store.pending(["note:1"]) == ["note:1"]

    def test_missing_revision_invalidates(self, cfg) -> None:
        """旧版本写的进度文件没有该字段，同样应作废。"""
        self._write_progress(
            cfg, None, {"note:1": {"stage": "notes", "status": "done"}}
        )
        assert not ProgressStore(cfg=cfg).is_done("note:1")

    def test_invalidation_is_persisted(self, cfg) -> None:
        """作废后立刻落盘，避免每次启动都重新告警。"""
        import json

        self._write_progress(
            cfg, PARSER_REVISION - 1, {"note:1": {"stage": "notes", "status": "done"}}
        )
        ProgressStore(cfg=cfg)
        payload = json.loads(cfg.progress_path.read_text(encoding="utf-8"))
        assert payload["parserRevision"] == PARSER_REVISION
        assert payload["items"] == {}

    def test_saved_revision_is_current(self, cfg) -> None:
        import json

        store = ProgressStore(cfg=cfg)
        store.mark_done("note:1", stage="notes")
        store.save(force=True)
        payload = json.loads(cfg.progress_path.read_text(encoding="utf-8"))
        assert payload["parserRevision"] == PARSER_REVISION


class TestTerminalOutcomesNotOverwritten:
    """StageRunner 的兜底标记不能把 handler 主动标记的终态改写成 done。

    历史缺陷：兜底判断用的是 ``is_done``，于是 handler 标了 ``unavailable``
    之后又被改写为 ``done``。后果是 ``--recheck-unavailable`` 永远筛不出这些
    条目，``data/unavailable.md`` 也会变空 —— 不可访问的内容被静默当成已归档。
    """

    def test_unavailable_survives_fallback(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)

        def handler(item: str) -> None:
            store.mark_unavailable(item, "原站不可访问", stage="s")

        runner.run(["a", "b"], handler, lambda item: item)

        assert store.status_of("a") == "unavailable"
        assert store.status_of("b") == "unavailable"
        assert store.unavailable()

    def test_unavailable_is_recheckable(self, cfg) -> None:
        """被标 unavailable 的条目必须能被 --recheck-unavailable 重新筛出。"""
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        runner.run(["a"], lambda k: store.mark_unavailable(k, "x", stage="s"), lambda k: k)

        assert store.pending(["a"]) == []
        assert store.pending(["a"], recheck_unavailable=True) == ["a"]

    def test_skipped_survives_fallback(self, cfg) -> None:
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)

        def handler(item: str) -> None:
            store.mark_skipped(item, "策略跳过", stage="s")

        runner.run(["a"], handler, lambda item: item)
        assert store.status_of("a") == "skipped"

    def test_silent_handler_still_gets_done(self, cfg) -> None:
        """handler 什么都没标时，兜底仍要补上 done。"""
        store = ProgressStore(cfg=cfg)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        runner.run(["a"], lambda item: None, lambda item: item)
        assert store.is_done("a")


class TestReadonlyStore:
    """``--offline`` 用的只读进度库：读得到，写不下去。

    离线模式下的"缓存未命中"只是本地还没有这份数据，并不代表源站不可得。
    若照常落盘，一次离线运行就会把整站标成"原站不可访问"。
    """

    def test_marks_do_not_persist(self, cfg) -> None:
        store = ProgressStore(cfg=cfg, readonly=True)
        store.mark_done("note:1", stage="notes")
        store.mark_unavailable("note:2", "x", stage="notes")
        store.save(force=True)

        assert not cfg.progress_path.exists()

    def test_existing_progress_is_still_read(self, cfg) -> None:
        seeded = ProgressStore(cfg=cfg)
        seeded.mark_done("note:1", stage="notes")
        seeded.save(force=True)

        store = ProgressStore(cfg=cfg, readonly=True)
        assert store.is_done("note:1")
        assert store.pending(["note:1", "note:2"]) == ["note:2"]

    def test_revision_change_is_not_persisted(self, cfg) -> None:
        """只读模式下即使解析器版本变了，也不该改写磁盘上的进度。"""
        import json

        cfg.progress_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.progress_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "parserRevision": PARSER_REVISION - 1,
                    "site": cfg.site_url,
                    "items": {"note:1": {"stage": "notes", "status": "done"}},
                }
            ),
            encoding="utf-8",
        )
        ProgressStore(cfg=cfg, readonly=True)
        payload = json.loads(cfg.progress_path.read_text(encoding="utf-8"))
        assert payload["parserRevision"] == PARSER_REVISION - 1
        assert "note:1" in payload["items"]

    def test_readonly_runner_keeps_memory_state(self, cfg) -> None:
        """内存里仍要反映本次运行的结果，否则统计与报告会失真。"""
        store = ProgressStore(cfg=cfg, readonly=True)
        runner = StageRunner(store, "s", cfg=cfg, show_progress=False)
        runner.run(["a"], lambda k: None, lambda k: k)

        assert store.is_done("a")
        assert store.totals()["done"] == 1
        assert not cfg.progress_path.exists()
