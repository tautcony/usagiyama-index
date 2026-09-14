"""页面解析层：统一处理"抓取 → 失败标记 → Internet Archive 补足"。

这是"页面无法访问的需要标记，并尝试使用 archive.org 补足"要求的落点。

判定顺序：

1. 源站正常返回 → ``Availability.OK``
2. 源站不可访问（403/404/410/418/429 等）→ 查询 Wayback Machine
   * 命中快照 → ``Availability.ARCHIVED``（记录快照时间与链接）
   * 无快照   → ``Availability.ARCHIVE_MISSING``
3. 命中已知需要登录的路径（``www.douban.com/note/``、``/topic/``）→
   ``Availability.LOGIN_REQUIRED``，仍会尝试 archive.org

所有非 OK 的页面都会被记入 ``PageResolver.unavailable``，
最终产出 ``data/unavailable.md`` 清单，便于人工核对。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .archive import WaybackClient
from .config import CONFIG, Config
from .http_client import BlockedError, CircuitBreakerOpen, FetchError, Fetcher, OfflineCacheMiss
from .models import Availability, SourceStatus

log = logging.getLogger("usagi.resolve")

# 这些路径在豆瓣主站需要登录，静态抓取拿不到
LOGIN_REQUIRED_PATTERNS = (
    "/note/",
    "/topic/",
)

UNAVAILABLE_STATUS = frozenset({401, 403, 404, 410, 418, 429, 451})


@dataclass
class ResolvedPage:
    """一次页面解析的结果。"""

    url: str
    html: str = ""
    status: SourceStatus = field(default_factory=SourceStatus)

    @property
    def ok(self) -> bool:
        return bool(self.html) and self.status.availability in {
            Availability.OK,
            Availability.ARCHIVED,
        }

    @property
    def has_content(self) -> bool:
        return bool(self.html.strip())


@dataclass
class UnavailableRecord:
    """一条不可访问记录，用于产出清单。"""

    url: str
    availability: Availability
    http_status: int | None = None
    detail: str = ""
    wayback_url: str | None = None
    wayback_timestamp: str | None = None
    context: str = ""


def _looks_login_required(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc not in {"www.douban.com", "douban.com"}:
        return False
    return any(pattern in parsed.path for pattern in LOGIN_REQUIRED_PATTERNS)


class PageResolver:
    """抓取页面，失败时标记并尝试 archive.org 补足。"""

    def __init__(
        self,
        fetcher: Fetcher,
        wayback: WaybackClient | None = None,
        cfg: Config = CONFIG,
    ) -> None:
        self.fetcher = fetcher
        self.wayback = wayback if wayback is not None else WaybackClient(cfg)
        self.cfg = cfg
        self.unavailable: list[UnavailableRecord] = []

    # ------------------------------------------------------------------ 核心

    def resolve(
        self,
        url: str,
        *,
        referer: str | None = None,
        force: bool = False,
        context: str = "",
        allow_archive: bool = True,
    ) -> ResolvedPage:
        """抓取页面；失败则标记并尝试 archive.org 补足。"""
        try:
            resp = self.fetcher.fetch(url, referer=referer, force=force)
        except CircuitBreakerOpen:
            raise
        except BlockedError as exc:
            return self._fallback(url, exc.status or 403, f"源站拒绝访问：{exc}", context, allow_archive)
        except OfflineCacheMiss as exc:
            return self._fallback(url, None, f"离线模式且无缓存：{exc}", context, allow_archive)
        except FetchError as exc:
            return self._fallback(url, exc.status, f"抓取失败：{exc}", context, allow_archive)

        if resp.ok and resp.content:
            return ResolvedPage(
                url=url,
                html=resp.text,
                status=SourceStatus(
                    availability=Availability.OK,
                    http_status=resp.status,
                    detail="缓存命中" if resp.from_cache else "",
                ),
            )

        return self._fallback(
            url, resp.status, f"源站返回 HTTP {resp.status}", context, allow_archive
        )

    def _fallback(
        self,
        url: str,
        http_status: int | None,
        detail: str,
        context: str,
        allow_archive: bool,
    ) -> ResolvedPage:
        """源站不可用时的 archive.org 补足流程。"""
        login_required = _looks_login_required(url)
        log.warning("不可访问 %s（%s）%s", url, http_status or "-", detail)

        wayback_url: str | None = None
        wayback_ts: str | None = None

        if allow_archive and self.wayback.enabled:
            html, snapshot = (None, None)
            result = self.wayback.fetch_html(url)
            if result is not None:
                html, snapshot = result
                wayback_url = snapshot.wayback_url
                wayback_ts = snapshot.timestamp

            if html:
                log.info("已从 Internet Archive 补足 %s（快照 %s）", url, wayback_ts)
                record = UnavailableRecord(
                    url=url,
                    availability=Availability.ARCHIVED,
                    http_status=http_status,
                    detail=f"{detail}；已用 archive.org 快照补足",
                    wayback_url=wayback_url,
                    wayback_timestamp=wayback_ts,
                    context=context,
                )
                self.unavailable.append(record)
                return ResolvedPage(
                    url=url,
                    html=html,
                    status=SourceStatus(
                        availability=Availability.ARCHIVED,
                        http_status=http_status,
                        detail=record.detail,
                        wayback_url=wayback_url,
                        wayback_timestamp=wayback_ts,
                    ),
                )

        availability = Availability.LOGIN_REQUIRED if login_required else (
            Availability.ARCHIVE_MISSING if self.wayback.enabled else Availability.UNAVAILABLE
        )
        if self.wayback.enabled:
            detail = f"{detail}；Internet Archive 亦无可用快照"

        record = UnavailableRecord(
            url=url,
            availability=availability,
            http_status=http_status,
            detail=detail,
            wayback_url=wayback_url,
            wayback_timestamp=wayback_ts,
            context=context,
        )
        self.unavailable.append(record)

        return ResolvedPage(
            url=url,
            html="",
            status=SourceStatus(
                availability=availability,
                http_status=http_status,
                detail=detail,
                wayback_url=wayback_url,
                wayback_timestamp=wayback_ts,
            ),
        )

    # ------------------------------------------------------------------ 便捷

    def resolve_required(
        self, url: str, *, referer: str | None = None, force: bool = False, context: str = ""
    ) -> ResolvedPage:
        """抓取页面；若最终仍无内容则抛错，用于关键路径。"""
        page = self.resolve(url, referer=referer, force=force, context=context)
        if not page.has_content:
            raise FetchError(url, f"无法获取内容（{page.status.label}）")
        return page

    def resolve_optional(self, *args: object, **kwargs: object) -> ResolvedPage | None:
        """抓取页面；失败返回 ``None`` 而不抛错，用于可选内容。"""
        try:
            return self.resolve(*args, **kwargs)  # type: ignore[arg-type]
        except CircuitBreakerOpen:
            raise
        except Exception as exc:  # noqa: BLE001 - 可选内容失败不应中断整体流程
            log.warning("可选内容抓取失败：%s", exc)
            return None

    def summary(self) -> dict[str, int]:
        """按可访问性分类统计。"""
        counts: dict[str, int] = {}
        for record in self.unavailable:
            counts[str(record.availability)] = counts.get(str(record.availability), 0) + 1
        return counts
