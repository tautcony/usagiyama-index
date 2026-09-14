"""HTTP 客户端：浏览器指纹模拟 + 限速 + 退避重试 + 磁盘缓存 + 熔断。

传输层使用 **curl_cffi**（curl-impersonate 的 Python 绑定），而不是自行拼装
请求头。原因是目标站点对 TLS 指纹有校验：实测裸 ``requests`` 的首个请求会
连续 4 次收到 ``SSLEOFError``，而 curl_cffi 维护着一套与真实浏览器逐字节
一致的 TLS/HTTP2 指纹配置，直接 ``impersonate="chrome"`` 即可稳定 200。

这正是"参考业界实现，不要自己做"的落点：指纹、HTTP2 帧序、头部顺序、
扩展列表等细节全部交给经过大量站点验证的库，本模块只负责**归档策略**：

* **磁盘缓存**：同一 URL 二次运行直接命中缓存，零网络请求。
  这是增量同步与断点续接的基础。
* **礼貌限速**：单线程，请求间隔 ``delay_min ~ delay_max`` 随机抖动。
  豆瓣 ``www.douban.com/robots.txt`` 注明 ``Crawl-delay: 5``，默认以此为下限。
* **指数退避**：由 tenacity 提供（指数增长 + 抖动）。
* **熔断**：连续 N 次被拦截（403/418/429）立即停止，避免把 IP 拖进黑名单。
* **不规避风控**：固定指纹、不轮换 UA、不轮换代理。
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from curl_cffi import requests as curl_requests
from curl_cffi.requests import Session
from curl_cffi.requests.exceptions import (
    ChunkedEncodingError,
    ConnectionError as CurlConnectionError,
    CurlError,
    IncompleteRead,
    ReadTimeout,
    SSLError as CurlSSLError,
    Timeout as CurlTimeout,
)
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from urllib.parse import urlparse

from .config import CONFIG, Config
from .util import now_iso, url_cache_key

log = logging.getLogger("usagi.http")

# 被拦截的响应码：源站明确拒绝，计入熔断计数并立即停止。
# 403（禁止）/ 418（防盗链触发）都属于"再来也没用"。
BLOCKED_STATUS = frozenset({403, 418})
# 可重试的响应码。
# 429 是"请求过频"而非"被封"，应当退避后重试而不是熔断；
# archive.org 的 CDX 接口尤其容易返回 429。
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
# 不写入缓存的响应码。429/5xx 是暂时性状态，缓存会让下次运行永久失败。
NO_CACHE_STATUS = frozenset({429, 500, 502, 503, 504, 508})

# 可重试的网络异常（curl_cffi 的异常体系）
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    CurlConnectionError,
    CurlTimeout,
    CurlSSLError,
    ChunkedEncodingError,
    IncompleteRead,
    CurlError,
)


def cache_domain(url: str) -> str:
    """提取用于缓存分目录的域名。

    缓存按域名隔离，好处有三：
    1. 不同源站（``site.douban.com`` / ``img*.doubanio.com`` / ``web.archive.org``）
       的缓存互不干扰，键空间天然分离；
    2. 可以按域名单独清理或检查缓存，排查问题时定位明确；
    3. 日后接入新站点时不会与既有缓存冲突。
    """
    host = urlparse(url).hostname or "unknown"
    return host.lower()


def cache_paths(cfg: Config, url: str) -> tuple[Path, Path]:
    """返回 ``(body 路径, meta 路径)``，位于 ``cache/<域名>/`` 下。"""
    key = url_cache_key(url)
    base = cfg.cache_dir / cache_domain(url)
    return base / f"{key}.body", base / f"{key}.json"


def migrate_flat_cache(cfg: Config) -> int:
    """把旧版扁平缓存迁移到按域名分目录的新布局。

    只处理 ``cache/*.json`` 这类顶层文件；meta 里记录了原始 URL，
    据此即可算出正确的域名子目录。返回迁移的文件组数。
    """
    import json as _json

    if not cfg.cache_dir.exists():
        return 0

    moved = 0
    for meta_path in sorted(cfg.cache_dir.glob("*.json")):
        if not meta_path.is_file():
            continue
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, _json.JSONDecodeError):
            # 损坏的 meta 无法判断归属，直接删掉，让它下次重新抓取
            meta_path.unlink(missing_ok=True)
            continue

        url = meta.get("url")
        if not url:
            meta_path.unlink(missing_ok=True)
            continue

        target_dir = cfg.cache_dir / cache_domain(url)
        body_path = meta_path.with_suffix(".body")

        # 迁移过程中可能被打断，留下"只有 body"或"只有 meta"的半截状态。
        # 这类残留无法使用，直接清掉即可（下次会重新抓取）。
        has_body = body_path.is_file()
        if not has_body:
            meta_path.unlink(missing_ok=True)
            continue

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            body_path.replace(target_dir / body_path.name)
            meta_path.replace(target_dir / meta_path.name)
            moved += 1
        except OSError as exc:
            log.warning("缓存迁移失败 %s：%s", meta_path.name, exc)

    if moved:
        log.info("已把 %d 组旧缓存迁移到按域名分目录的新布局", moved)
    return moved


class FetchError(Exception):
    """抓取失败基类。"""

    def __init__(self, url: str, message: str, status: int | None = None) -> None:
        super().__init__(f"{message} [{status or '-'}] {url}")
        self.url = url
        self.status = status


class BlockedError(FetchError):
    """被源站拦截（403/418/429）。"""


class CircuitBreakerOpen(FetchError):
    """连续被拦截次数超阈值，主动停止。"""


class OfflineCacheMiss(FetchError):
    """离线模式下缓存未命中。"""


class _RetryableStatus(Exception):
    """内部信号：遇到可重试的 HTTP 状态码，交给 tenacity 重试。"""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} {url}")
        self.status = status
        self.url = url


@dataclass
class CachedResponse:
    """一次抓取（或缓存命中）的结果。"""

    url: str
    status: int
    content: bytes
    content_type: str = ""
    fetched_at: str = ""
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        return decode_html(self.content, self.content_type)

    @property
    def size(self) -> int:
        return len(self.content)


def decode_html(content: bytes, content_type: str = "") -> str:
    """按 content-type 的 charset 解码，缺省 utf-8，失败则替换。"""
    charset = "utf-8"
    lowered = (content_type or "").lower()
    if "charset=" in lowered:
        charset = lowered.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return content.decode(charset, errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")


@dataclass
class FetchStats:
    """运行统计，用于产出同步报告。"""

    requests: int = 0
    cache_hits: int = 0
    retries: int = 0
    blocked: int = 0
    bytes_downloaded: int = 0
    elapsed: float = 0.0
    impersonate: str = ""
    by_status: dict[int, int] = field(default_factory=dict)

    def record_status(self, status: int) -> None:
        self.by_status[status] = self.by_status.get(status, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "cacheHits": self.cache_hits,
            "retries": self.retries,
            "blocked": self.blocked,
            "bytesDownloaded": self.bytes_downloaded,
            "elapsedSeconds": round(self.elapsed, 1),
            "impersonate": self.impersonate,
            "byStatus": {str(k): v for k, v in sorted(self.by_status.items())},
        }


class Fetcher:
    """带指纹模拟、缓存与限速的 HTTP 抓取器（单线程）。"""

    def __init__(
        self,
        cfg: Config = CONFIG,
        *,
        offline: bool | None = None,
        session: Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        impersonate: str | None = None,
    ) -> None:
        self.cfg = cfg
        self.offline = cfg.offline if offline is None else offline
        self.impersonate = impersonate or cfg.impersonate
        self._sleep = sleep
        self._session = session or self._build_session()
        self.cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        # 旧版本把缓存平铺在 cache/ 下，这里做一次幂等迁移
        migrate_flat_cache(self.cfg)

        self.stats = FetchStats(impersonate=self.impersonate)
        self._last_request_at: float | None = None
        self._consecutive_blocked = 0
        self._started_at = time.monotonic()

    def _build_session(self) -> Session:
        """构造带浏览器指纹的会话。"""
        session = Session(impersonate=self.impersonate, timeout=self.cfg.timeout)
        # 声明中文优先，与真实浏览器一致（不轮换）
        session.headers["Accept-Language"] = "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7"
        # 让 libcurl 读取 http_proxy / https_proxy 环境变量
        session.trust_env = True
        return session

    # ------------------------------------------------------------------ 缓存

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        return cache_paths(self.cfg, url)

    def _read_cache(self, url: str) -> CachedResponse | None:
        import hashlib
        import json

        body_path, meta_path = self._cache_paths(url)
        if not body_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            content = body_path.read_bytes()
        except (OSError, json.JSONDecodeError):
            return None
        if meta.get("sha1") and hashlib.sha1(content).hexdigest() != meta["sha1"]:
            log.warning("缓存内容校验失败，忽略：%s", url)
            return None
        return CachedResponse(
            url=url,
            status=int(meta.get("status", 0)),
            content=content,
            content_type=meta.get("contentType", ""),
            fetched_at=meta.get("fetchedAt", ""),
            from_cache=True,
        )

    def _write_cache(self, resp: CachedResponse) -> None:
        import hashlib
        import json

        from .util import atomic_write_bytes, atomic_write_text

        body_path, meta_path = self._cache_paths(resp.url)
        meta = {
            "url": resp.url,
            "status": resp.status,
            "contentType": resp.content_type,
            "fetchedAt": resp.fetched_at,
            "size": len(resp.content),
            "sha1": hashlib.sha1(resp.content).hexdigest(),
        }
        try:
            atomic_write_bytes(body_path, resp.content)
            atomic_write_text(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        except OSError as exc:  # 缓存写失败不应中断抓取
            log.warning("缓存写入失败 %s: %s", resp.url, exc)

    def cache_has(self, url: str) -> bool:
        return self._cache_paths(url)[0].exists()

    # -------------------------------------------------------------- 限速/重试

    def _respect_rate_limit(self) -> None:
        """在两次网络请求之间保持最小间隔（带随机抖动）。"""
        if self._last_request_at is None:
            return
        delay = random.uniform(self.cfg.delay_min, self.cfg.delay_max)
        remaining = delay - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            self._sleep(remaining)

    def _attempt(self, url: str, referer: str | None) -> Any:
        """单次网络尝试。可重试的错误以异常抛出交给 tenacity。"""
        headers: dict[str, str] = {}
        if referer:
            headers["Referer"] = referer

        self._respect_rate_limit()
        self._last_request_at = time.monotonic()
        self.stats.requests += 1

        resp = self._session.get(
            url,
            headers=headers,
            timeout=self.cfg.timeout,
            allow_redirects=True,
        )
        self.stats.record_status(resp.status_code)

        if resp.status_code in RETRYABLE_STATUS:
            raise _RetryableStatus(resp.status_code, url)
        return resp

    def _on_retry(self, state: RetryCallState) -> None:
        self.stats.retries += 1
        exc = state.outcome.exception() if state.outcome else None
        log.warning(
            "第 %d 次重试 %s（下次等待 %.0fs）：%s",
            state.attempt_number,
            state.args[0] if state.args else "?",
            state.next_action.sleep if state.next_action else 0,
            exc,
        )

    def _retryer(self) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self.cfg.max_retries + 1),
            wait=wait_exponential_jitter(
                initial=self.cfg.backoff_base,
                max=self.cfg.backoff_base * 16,
                jitter=self.cfg.backoff_base / 2,
            ),
            retry=retry_if_exception_type((_RetryableStatus, *RETRYABLE_EXCEPTIONS)),
            before_sleep=self._on_retry,
            reraise=True,
            sleep=self._sleep,
        )

    def _fetch_network(self, url: str, referer: str | None) -> CachedResponse:
        try:
            raw = self._retryer()(self._attempt, url, referer)
        except _RetryableStatus as exc:
            raise FetchError(url, f"重试 {self.cfg.max_retries} 次后仍为 HTTP {exc.status}", exc.status)
        except CurlError as exc:
            raise FetchError(url, f"重试 {self.cfg.max_retries} 次后仍失败：{type(exc).__name__}") from exc

        self.stats.bytes_downloaded += len(raw.content)
        content_type = raw.headers.get("Content-Type", "") or ""
        resp = CachedResponse(
            url=url,
            status=raw.status_code,
            content=raw.content,
            content_type=content_type,
            fetched_at=now_iso(),
        )

        if raw.status_code in BLOCKED_STATUS:
            self._consecutive_blocked += 1
            self.stats.blocked += 1
            # 缓存被拦截的结果，避免同一 URL 反复冲击源站
            self._write_cache(resp)
            if self._consecutive_blocked >= self.cfg.circuit_break_after:
                raise CircuitBreakerOpen(
                    url,
                    f"连续 {self._consecutive_blocked} 次被拦截，已熔断停止。"
                    f"进度已保存，稍后可直接续跑。",
                    raw.status_code,
                )
            raise BlockedError(url, "源站拒绝访问", raw.status_code)

        self._consecutive_blocked = 0
        # 4xx 视为确定性结果并缓存；429 与 5xx 是暂时性的，不缓存以便下次重试
        if raw.status_code not in NO_CACHE_STATUS:
            self._write_cache(resp)
        return resp

    # ------------------------------------------------------------------ 对外

    def fetch(
        self,
        url: str,
        *,
        referer: str | None = None,
        force: bool = False,
        raise_for_blocked: bool = True,
    ) -> CachedResponse:
        """抓取一个 URL，优先命中磁盘缓存。

        :param referer: 部分资源（尤其 ``img*.doubanio.com``）需要 Referer 才返回 200。
        :param force: 忽略缓存强制重新请求。
        :param raise_for_blocked: 被拦截时是否抛 ``BlockedError``。
        """
        if not force:
            cached = self._read_cache(url)
            if cached is not None:
                # 429/5xx 属于暂时性失败，历史缓存一律视为过期
                if cached.status not in NO_CACHE_STATUS:
                    self.stats.cache_hits += 1
                    if cached.status in BLOCKED_STATUS and raise_for_blocked:
                        raise BlockedError(url, "缓存记录为被拦截", cached.status)
                    return cached

        if self.offline:
            raise OfflineCacheMiss(url, "离线模式下缓存未命中")

        return self._fetch_network(url, referer)

    def get_html(self, url: str, **kwargs: Any) -> str:
        return self.fetch(url, **kwargs).text

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        return self.fetch(url, **kwargs).content

    def get_image(self, url: str, *, force: bool = False) -> CachedResponse:
        """抓取图片，强制带 Referer（否则 doubanio 返回 418）。"""
        return self.fetch(url, referer=self.cfg.image_referer, force=force)

    # ------------------------------------------------------------------ 收尾

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:  # noqa: BLE001 - 关闭失败无关紧要
            pass

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def finalize(self) -> FetchStats:
        self.stats.elapsed = time.monotonic() - self._started_at
        return self.stats


def estimate_duration(request_count: int, cfg: Config = CONFIG) -> str:
    """按平均间隔估算耗时，用于 ``--dry-run`` 预演。"""
    from .util import human_duration

    avg = (cfg.delay_min + cfg.delay_max) / 2
    return human_duration(request_count * avg)


def count_cached(cfg: Config, urls: Iterable[str]) -> int:
    """统计给定 URL 中有多少已在缓存内（离线可用数量）。"""
    return sum(1 for u in urls if cache_paths(cfg, u)[0].exists())
