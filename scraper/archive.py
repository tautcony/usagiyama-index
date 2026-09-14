"""Internet Archive（Wayback Machine）补足。

当源站页面不可访问（403/404/410 等）或需要登录时，尝试从 Wayback Machine
取回历史快照，让归档尽量完整。

设计要点（均来自实测）：

* **只用 CDX 接口，不用 ``/wayback/available``**。
  实测 ``/wayback/available`` 会被 archive.org 频繁限流返回 429，
  而 ``/cdx/search/cdx`` 稳定可用，且能自动匹配 URL 变体
  （查询 ``https://site.douban.com/211330/`` 会返回
  ``http://site.douban.com:80/211330/`` 等历史形态）。
  少打一个接口也意味着更少的请求压力。
* **``id_`` 修饰符**取**原始未改写**的快照内容
  （``https://web.archive.org/web/{timestamp}id_/{url}``），
  避免 Wayback 注入的工具栏与链接重写污染归档内容。
* **``im_`` 修饰符**取图片原始二进制。
* 独立且更保守的限速（默认 10~15s）与退避（20s 起）。
"""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse, urlunparse

from .config import CONFIG, Config
from .http_client import BlockedError, FetchError, Fetcher, OfflineCacheMiss

log = logging.getLogger("usagi.archive")

CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_WEB = "https://web.archive.org/web"

# CDX 返回的字段
CDX_FIELDS = "original,timestamp,statuscode"


@dataclass
class Snapshot:
    """一个 Wayback 快照。"""

    url: str
    """快照对应的原始 URL（CDX 返回的 ``original`` 字段）。"""

    timestamp: str
    wayback_url: str
    status: int | None = None

    @property
    def raw_url(self) -> str:
        """取原始未改写内容的 URL（``id_`` 修饰符）。"""
        return f"{WAYBACK_WEB}/{self.timestamp}id_/{self.url}"

    @property
    def image_url(self) -> str:
        """取图片原始二进制（``im_`` 修饰符）。"""
        return f"{WAYBACK_WEB}/{self.timestamp}im_/{self.url}"

    @property
    def human_date(self) -> str:
        """快照时间的人类可读形式。"""
        ts = self.timestamp
        if len(ts) >= 8:
            return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
        return ts

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "date": self.human_date,
            "waybackUrl": self.wayback_url,
            "status": self.status,
        }


def _archive_config(cfg: Config) -> Config:
    """基于主配置派生一份 archive.org 专用配置（更慢的限速与退避）。"""
    return dataclasses.replace(
        cfg,
        delay_min=cfg.archive_delay_min,
        delay_max=cfg.archive_delay_max,
        max_retries=cfg.archive_retries,
        backoff_base=cfg.archive_backoff_base,
    )


def url_variants(url: str) -> list[str]:
    """生成同一资源的 URL 变体，提高 CDX 命中率。

    历史快照常见的形态差异：``http`` / ``https``、带或不带 ``www.``、
    带或不带结尾斜杠、显式 ``:80`` 端口。
    """
    variants: list[str] = [url]
    parsed = urlparse(url)

    schemes = ["http", "https"] if parsed.scheme == "https" else ["https", "http"]
    hosts = [parsed.netloc]
    if parsed.netloc.startswith("www."):
        hosts.append(parsed.netloc[4:])
    else:
        hosts.append(f"www.{parsed.netloc}")

    paths = [parsed.path]
    if parsed.path.endswith("/"):
        paths.append(parsed.path.rstrip("/"))
    else:
        paths.append(f"{parsed.path}/")

    for scheme in schemes:
        for host in hosts:
            for path in paths:
                candidate = urlunparse(parsed._replace(scheme=scheme, netloc=host, path=path))
                if candidate not in variants:
                    variants.append(candidate)
    return variants


class WaybackClient:
    """Wayback Machine 客户端（CDX 单通道）。"""

    def __init__(self, cfg: Config = CONFIG, *, fetcher: Fetcher | None = None) -> None:
        self.cfg = cfg
        self.enabled = cfg.archive_enabled
        self._fetcher = fetcher or Fetcher(_archive_config(cfg))
        self._owns_fetcher = fetcher is None
        # 查询结果缓存，避免同一 URL 反复打 CDX
        self._snapshot_cache: dict[str, Snapshot | None] = {}

    # ------------------------------------------------------------ 快照查询

    def cdx_search(
        self,
        url: str,
        *,
        match: str = "exact",
        limit: int = 10,
        only_ok: bool = True,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list[Snapshot]:
        """通过 CDX API 搜索快照，按时间倒序返回（最新在前）。"""
        if not self.enabled:
            return []
        params: dict[str, str] = {
            "url": url,
            "output": "json",
            "limit": str(limit),
            "collapse": "digest",
            "fl": CDX_FIELDS,
        }
        if match != "exact":
            params["matchType"] = match
        if only_ok:
            params["filter"] = "statuscode:200"
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts

        try:
            payload = self._fetcher.get_html(f"{CDX_API}?{urlencode(params)}")
        except (BlockedError, FetchError, OfflineCacheMiss) as exc:
            log.debug("CDX 查询失败 %s：%s", url, exc)
            return []

        try:
            rows = json.loads(payload)
        except json.JSONDecodeError:
            log.debug("CDX 返回非 JSON：%s", payload[:120])
            return []
        if not isinstance(rows, list) or len(rows) < 2:
            return []

        header, *records = rows
        index = {name: position for position, name in enumerate(header)}
        snapshots: list[Snapshot] = []
        for record in records:
            if len(record) < len(header):
                continue
            original = record[index.get("original", 0)]
            timestamp = record[index.get("timestamp", 1)]
            status_raw = record[index.get("statuscode", 2)]
            snapshots.append(
                Snapshot(
                    url=original,
                    timestamp=timestamp,
                    wayback_url=f"{WAYBACK_WEB}/{timestamp}/{original}",
                    status=int(status_raw) if str(status_raw).isdigit() else None,
                )
            )
        snapshots.sort(key=lambda item: item.timestamp, reverse=True)
        return snapshots

    def best_snapshot(self, url: str) -> Snapshot | None:
        """找到最新的可用快照，依次尝试 URL 变体。"""
        if not self.enabled:
            return None
        if url in self._snapshot_cache:
            return self._snapshot_cache[url]

        snapshot: Snapshot | None = None
        for candidate in url_variants(url):
            found = self.cdx_search(candidate, limit=5)
            if found:
                snapshot = found[0]
                if candidate != url:
                    log.debug("快照命中变体 %s → %s", url, candidate)
                break

        self._snapshot_cache[url] = snapshot
        return snapshot

    # ------------------------------------------------------------ 内容获取

    def fetch_snapshot_html(self, snapshot: Snapshot) -> str | None:
        """抓取快照的原始 HTML（``id_`` 修饰，未被 Wayback 改写）。"""
        try:
            return self._fetcher.get_html(snapshot.raw_url)
        except (BlockedError, FetchError, OfflineCacheMiss) as exc:
            log.warning("快照抓取失败 %s：%s", snapshot.raw_url, exc)
            return None

    def fetch_html(self, url: str) -> tuple[str, Snapshot] | None:
        """查询并抓取某 URL 的快照 HTML。返回 ``(html, snapshot)``。"""
        snapshot = self.best_snapshot(url)
        if snapshot is None:
            return None
        html = self.fetch_snapshot_html(snapshot)
        if html is None:
            return None
        return html, snapshot

    def fetch_image(self, url: str, timestamp: str | None = None) -> tuple[bytes, str] | None:
        """抓取图片的历史快照。返回 ``(bytes, wayback_url)``。"""
        snapshot = self.best_snapshot(url)
        if snapshot is None and timestamp:
            snapshot = Snapshot(
                url=url, timestamp=timestamp, wayback_url=f"{WAYBACK_WEB}/{timestamp}/{url}"
            )
        if snapshot is None:
            return None

        raw_url = snapshot.image_url
        try:
            # 这同样是一次"要一张图片"的请求，用图片的请求头特征。
            # 这里不带 Referer：archive.org 没有防盗链，也没必要把来源页告诉它。
            resp = self._fetcher.fetch(raw_url, raise_for_blocked=False, image=True)
        except (BlockedError, FetchError, OfflineCacheMiss) as exc:
            log.debug("快照图片抓取失败 %s：%s", raw_url, exc)
            return None
        if not resp.ok or not resp.content:
            return None
        return resp.content, raw_url

    # ------------------------------------------------------------------ 收尾

    def close(self) -> None:
        if self._owns_fetcher:
            self._fetcher.close()

    def __enter__(self) -> "WaybackClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def stats(self) -> dict[str, object]:
        return self._fetcher.stats.to_dict()


def wayback_calendar_url(url: str) -> str:
    """给用户看的"查看所有快照"链接。"""
    return f"{WAYBACK_WEB}/*/{url}"
