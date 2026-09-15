"""抓取传输层：磁盘缓存 + 礼貌限速 + 退避重试 + 熔断 + 统计。

模块结构：

* :class:`RateLimiter` —— 请求间隔控制（被 HTTP 与浏览器后端共享）
* :class:`RawResponse` —— 一次网络尝试的归一化结果（抹平各传输库的差异）
* :class:`BaseFetcher` —— 与传输无关的抓取骨架，子类只需实现 ``_attempt()``
* :class:`Fetcher` —— curl_cffi 实现（默认传输）
* :class:`~scraper.browser.BrowserFetcher` —— Playwright 实现（见 browser.py）

**归档策略**：

* **磁盘缓存**：同一 URL 二次运行直接命中缓存，零网络请求。
  这是增量同步与断点续接的基础，也被浏览器后端复用（同一套缓存布局）。
  例外是**不可信的 404**（见 :func:`is_untrusted_missing`）：既不入缓存、
  也不从缓存里取，避免源站一次抖动被永久固化。
* **礼貌限速**：单线程，请求间隔 ``delay_min ~ delay_max`` 随机抖动。
  豆瓣 ``www.douban.com/robots.txt`` 注明 ``Crawl-delay: 5``，默认以此为下限。
  注意间隔按「距上次请求**开始**的时间」计算，因此浏览器导航耗时会被吸收进间隔里，
  单请求总时长是 ``max(delay, 导航耗时)`` 而非两者相加。
* **指数退避**：由 tenacity 提供（指数增长 + 抖动）。
* **熔断**：连续 N 次被拦截（403/418）立即停止，避免把 IP 拖进黑名单。
* **不规避风控**：固定指纹、不轮换 UA、不轮换代理。

**图片请求头另有一套**（见 :func:`image_request_headers`）：``impersonate`` 给的默认头
是**顶层导航**的那一套，直接拿去要 ``.jpg`` 会自报"这是一次文档导航"。
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from curl_cffi import requests as curl_requests  # noqa: F401  （保留以兼容外部导入）
from curl_cffi.requests import Session
from curl_cffi.requests.exceptions import (
    ChunkedEncodingError,
    ConnectionError as CurlConnectionError,
    IncompleteRead,
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

from .config import CONFIG, Config
from .util import atomic_write_bytes, atomic_write_text, host_matches, now_iso, url_cache_key

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
# "内容不存在"的响应码。多数情况下 404 是确定性结论，可以直接缓存；
# 但在 Config.untrusted_404_hosts 列出的域名上它不是 —— 见 is_untrusted_missing。
MISSING_STATUS = 404

# 可重试的网络异常（curl_cffi 的异常体系）。
#
# 只保留**具体的瞬态异常子类**，不要包含基类 ``CurlError``：``CurlError`` 是
# 所有 curl_cffi 异常的父类，把它放进来会让 ``ImpersonateError``（``USAGI_IMPERSONATE``
# 配了无效值）、``DNSError``、结构错误的 URL 等**致命配置错误**也被退避重试，
# 每个请求白白重试 ``max_retries`` 次才失败，既掩盖真实配置错误、又把运行时间
# 放大约 6×。瞬态的网络抖动由下面这些具体子类覆盖即可。
CURL_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    CurlConnectionError,
    CurlTimeout,
    CurlSSLError,
    ChunkedEncodingError,
    IncompleteRead,
)

# 兼容旧名字（外部可能已导入）
RETRYABLE_EXCEPTIONS = CURL_RETRYABLE_EXCEPTIONS


# ------------------------------------------------------------------ 请求头特征

#: 浏览器加载图片时的 ``Accept``。
#: 注意与导航用的 ``text/html,application/xhtml+xml,…`` 完全不同 —— 后者对图片请求
#: 是个明显的错配信号。
IMAGE_ACCEPT = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"

#: 只属于导航、图片请求里不该出现的头。curl_cffi 的 impersonate 会注入它们，
#: 传 ``None`` 作为值即可**真正删除**（见 curl_cffi ``set_curl_options``：
#: ``v is None`` 时发的是 ``"Name:"``，libcurl 据此删掉该头）。
NAVIGATION_ONLY_HEADERS: tuple[str, ...] = ("Sec-Fetch-User", "Upgrade-Insecure-Requests")


def site_suffix(host: str) -> str:
    """取可注册域名的近似值（最后两段），用于判定 same-site。

    对本站用到的域名（``site.douban.com`` / ``img3.doubanio.com`` /
    ``web.archive.org``）足够准确；不处理 ``foo.co.uk`` 这类多段公共后缀
    —— 判错的后果只是 ``Sec-Fetch-Site`` 写成 ``cross-site``，与现状一致。
    """
    parts = [part for part in host.lower().split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def fetch_site(url: str, referer: str | None) -> str:
    """计算 ``Sec-Fetch-Site``：浏览器用来说明"发起方与目标是何关系"。

    ``none``（用户直接输入/没有来源）、``same-origin``、``same-site``、``cross-site``
    四选一。图片请求固定是 ``no-cors`` 模式，来源页与图片不在同一个域，
    因此取值基本都是 ``cross-site``。
    """
    if not referer:
        return "none"
    target = urlparse(url).hostname or ""
    origin = urlparse(referer).hostname or ""
    if not target or not origin:
        return "none"
    if target.lower() == origin.lower():
        return "same-origin"
    if site_suffix(target) == site_suffix(origin):
        return "same-site"
    return "cross-site"


def image_request_headers(url: str, referer: str | None) -> dict[str, str | None]:
    """图片请求该带的头 —— 与真实浏览器加载 ``<img>`` 时发出的那一套逐项对齐。

    ``impersonate`` 注入的默认头是**文档导航**的：``Accept: text/html,…``、
    ``Sec-Fetch-Dest: document``、``Sec-Fetch-Mode: navigate``、
    ``Sec-Fetch-Site: none``、``Sec-Fetch-User: ?1``、``Upgrade-Insecure-Requests: 1``。
    通过本地回显服务器实测，curl_cffi 的 ``impersonate`` 默认对上述六个导航类请求头
    同样下发，即服务器收到的请求语义是「加载一份 HTML 文档」而非图片，与真实的
    ``<img>`` 加载行为不符。这与「请求是否像浏览器」直接相关，因此这里整组换掉，
    而不是只补 ``Referer``。

    不做的事与项目原则一致：不伪造 UA、不轮换指纹，``Sec-Ch-Ua*`` 仍由 impersonate
    提供（值与 TLS 指纹同源，改动反而会自相矛盾）。
    """
    headers: dict[str, str | None] = {
        "Accept": IMAGE_ACCEPT,
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": fetch_site(url, referer),
    }
    for name in NAVIGATION_ONLY_HEADERS:
        headers[name] = None
    if referer:
        headers["Referer"] = referer
    return headers


# ------------------------------------------------------------------ 404 的可信度


def is_untrusted_missing(url: str, status: int, cfg: Config = CONFIG) -> bool:
    """这个 404 是否**不能**作为"内容已不存在"的证据。

    小站（``site.douban.com``）的 widget 后端有已知抖动：**同一个 URL** 会间歇性
    返回通用 404 页（"呃...你想访问的页面不存在"），几分钟后再请求就是 200
    （实测：``/widget/photos/13431950/photo/2325379542/`` 一个小时内 404 → 200）。
    存档一旦把内容判成"不存在"就不再回头看，因此这种 404 必须区别对待：

    * **不写缓存** —— 否则一次抖动会被固化成永久结论；
    * **不从缓存取** —— 修好之前写进去的那几条也算数，无需 ``--force``；
    * 解析层据此把单元标为"可重试"，下次同步自动重试。

    真正的死链因此会多花一两次请求，但不会丢内容。域名清单见
    :attr:`Config.untrusted_404_hosts`（测试里可替换为空以恢复默认行为）。
    """
    if status != MISSING_STATUS:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host_matches(host, cfg.untrusted_404_hosts)


# --------------------------------------------------------------------- 缓存布局


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
    if not cfg.cache_dir.exists():
        return 0

    moved = 0
    for meta_path in sorted(cfg.cache_dir.glob("*.json")):
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
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
        if not body_path.is_file():
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


# ----------------------------------------------------------------------- 异常


class FetchError(Exception):
    """抓取失败基类。"""

    def __init__(self, url: str, message: str, status: int | None = None) -> None:
        super().__init__(f"{message} [{status or '-'}] {url}")
        self.url = url
        self.status = status
        #: 不含 URL 的裸消息。调用方常常已经在报错里带上了 URL，
        #: 直接复用 ``str(exc)`` 会把它重复一遍。
        self.message = message


class BlockedError(FetchError):
    """被源站拦截（403/418），或触发了人机校验。"""


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


# ------------------------------------------------------------------- 数据结构


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


@dataclass
class RawResponse:
    """一次网络尝试的归一化结果。

    存在的意义是把各传输库的响应对象抹平成同一种形状，
    这样 :class:`BaseFetcher` 的缓存/熔断/统计逻辑与传输方式无关。
    """

    status: int
    content: bytes
    content_type: str = ""
    final_url: str = ""


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
    #: 源站返回了不可信的 404（见 :func:`is_untrusted_missing`）的次数
    transient_misses: int = 0
    by_status: dict[int, int] = field(default_factory=dict)

    def record_status(self, status: int) -> None:
        self.by_status[status] = self.by_status.get(status, 0) + 1

    def merge(self, other: "FetchStats") -> None:
        """合并另一份统计（浏览器后端需要把内部 curl 的图片请求并入）。"""
        self.requests += other.requests
        self.cache_hits += other.cache_hits
        self.retries += other.retries
        self.blocked += other.blocked
        self.bytes_downloaded += other.bytes_downloaded
        self.transient_misses += other.transient_misses
        for status, count in other.by_status.items():
            self.by_status[status] = self.by_status.get(status, 0) + count

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "cacheHits": self.cache_hits,
            "retries": self.retries,
            "blocked": self.blocked,
            "bytesDownloaded": self.bytes_downloaded,
            "transientMisses": self.transient_misses,
            "elapsedSeconds": round(self.elapsed, 1),
            "impersonate": self.impersonate,
            "byStatus": {str(k): v for k, v in sorted(self.by_status.items())},
        }


# --------------------------------------------------------------------- 限速


class RateLimiter:
    """请求间隔控制。

    语义是「保证两次网络请求**开始**之间至少间隔 delay_min~delay_max」。
    由于计时从上次请求开始算起，**导航本身的耗时会被吸收进这个间隔**：
    单请求总时长是 ``max(delay, 实际耗时)`` 而不是两者相加。
    这对浏览器后端尤其重要——它让浏览器导航的额外延迟几乎不增加总时长。

    多个后端可以共享同一个实例（例如浏览器页面与 curl 图片下载），
    这样它们共用一条时间线，整体请求速率仍然受控。
    """

    def __init__(self, cfg: Config = CONFIG, sleep: Callable[[float], None] = time.sleep) -> None:
        self.cfg = cfg
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        """按需休眠，使本次请求距上次请求开始至少间隔 delay。"""
        if self._last is None:
            return
        delay = random.uniform(self.cfg.delay_min, self.cfg.delay_max)
        remaining = delay - (time.monotonic() - self._last)
        if remaining > 0:
            self._sleep(remaining)

    def mark(self) -> None:
        """记录本次请求的开始时刻。必须在发起网络请求前调用。"""
        self._last = time.monotonic()

    @property
    def last_request_at(self) -> float | None:
        return self._last


# ----------------------------------------------------------------- 抓取骨架


class BaseFetcher:
    """与传输无关的抓取骨架。

    子类只需实现：

    * ``_attempt(url, referer, image=False) -> RawResponse``：执行一次网络尝试，
      可重试的错误以异常抛出交给 tenacity。
    * ``close()``：释放底层资源。
    * ``retryable_exceptions``：该传输方式下值得重试的异常类型。

    基类负责：磁盘缓存、限速、退避重试、熔断、统计。
    """

    #: 子类覆盖：本传输方式下值得重试的异常类型
    retryable_exceptions: tuple[type[BaseException], ...] = ()

    def __init__(
        self,
        cfg: Config = CONFIG,
        *,
        offline: bool | None = None,
        sleep: Callable[[float], None] = time.sleep,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.cfg = cfg
        self.offline = cfg.offline if offline is None else offline
        self._sleep = sleep
        self._limiter = limiter or RateLimiter(cfg, sleep=sleep)
        self.cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        # 旧版本把缓存平铺在 cache/ 下，这里做一次幂等迁移
        migrate_flat_cache(self.cfg)

        self.stats = FetchStats()
        self._consecutive_blocked = 0
        self._started_at = time.monotonic()

    # -------------------------------------------------------------- 子类接口

    def _attempt(
        self, url: str, referer: str | None, image: bool = False
    ) -> RawResponse:
        """执行一次网络尝试。

        :param image: 本次要的是图片（``<img>`` 子资源）而不是文档。
            传输层据此选择请求头特征，见 :func:`image_request_headers`。
        """
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - 子类实现
        pass

    # ------------------------------------------------------------------ 缓存

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        return cache_paths(self.cfg, url)

    def _read_cache(self, url: str) -> CachedResponse | None:
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

    def invalidate_cache(self, url: str) -> bool:
        """丢弃某个 URL 的缓存条目（调用方判定缓存内容不可用时使用）。

        给"缓存里的东西不可用"这类场景用：例如一份 200 的 HTML 错误页被当成图片
        存了下来，不删掉的话每次运行都会重放同一份坏内容，只能靠 ``--force`` 自救。
        删掉后下次运行会重新请求 —— 常规的失效仍由 :data:`NO_CACHE_STATUS` 负责。

        返回是否真的删掉了条目；删除失败只记日志不抛异常（缓存清理不该让抓取流程失败）。
        """
        body_path, meta_path = self._cache_paths(url)
        existed = body_path.exists() or meta_path.exists()
        for path in (body_path, meta_path):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                log.warning("缓存条目删除失败 %s：%s", url, exc)
                return False
        if existed:
            log.info("已丢弃不可用的缓存条目：%s", url)
        return existed

    # -------------------------------------------------------------- 重试/熔断

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
            retry=retry_if_exception_type((_RetryableStatus, *self.retryable_exceptions)),
            before_sleep=self._on_retry,
            reraise=True,
            sleep=self._sleep,
        )

    def _classify_blocked(self, raw: RawResponse, url: str) -> BlockedError | None:
        """判断一次响应是否属于"被拦截"。

        基类只看状态码；子类可覆盖以识别自己特有的拦截信号
        （浏览器后端会把"被重定向到人机校验页"也算作被拦截）。
        返回 ``None`` 表示正常放行。
        """
        if raw.status in BLOCKED_STATUS:
            return BlockedError(url, "源站拒绝访问", raw.status)
        return None

    def _fetch_network(
        self,
        url: str,
        referer: str | None,
        image: bool = False,
        *,
        raise_for_blocked: bool = True,
    ) -> CachedResponse:
        try:
            raw = self._retryer()(self._attempt, url, referer, image=image)
        except _RetryableStatus as exc:
            raise FetchError(
                url, f"重试 {self.cfg.max_retries} 次后仍为 HTTP {exc.status}", exc.status
            ) from exc
        except self.retryable_exceptions as exc:
            raise FetchError(
                url, f"重试 {self.cfg.max_retries} 次后仍失败：{type(exc).__name__}: {exc}"
            ) from exc

        self.stats.bytes_downloaded += len(raw.content)
        resp = CachedResponse(
            url=url,
            status=raw.status,
            content=raw.content,
            content_type=raw.content_type,
            fetched_at=now_iso(),
        )

        blocked = self._classify_blocked(raw, url)
        if blocked is not None:
            self._consecutive_blocked += 1
            self.stats.blocked += 1
            # 只缓存真实的 4xx 拒绝（避免同一 URL 反复冲击源站）。
            # 人机校验页虽然也是"被拦截"，但它可能是 200，缓存下来会污染后续运行。
            if raw.status in BLOCKED_STATUS:
                self._write_cache(resp)
            if self._consecutive_blocked >= self.cfg.circuit_break_after:
                raise CircuitBreakerOpen(
                    url,
                    f"连续 {self._consecutive_blocked} 次被拦截，已熔断停止。"
                    f"进度已保存，稍后可直接续跑。",
                    raw.status,
                )
            if raise_for_blocked:
                raise blocked
            # 调用方显式要求"拿到被拦截的响应体"（例如拿 403 body 去走
            # archive.org 兜底），此时不抛异常，直接把响应交回去。
            return resp

        self._consecutive_blocked = 0
        # 不可信的 404（小站 widget 抖动）不能固化：不写缓存，下次运行重新请求
        if is_untrusted_missing(url, raw.status, self.cfg):
            self.stats.transient_misses += 1
            log.warning("源站返回 %d，但该域名上的 404 不可信，不写缓存：%s", raw.status, url)
            return resp
        # 4xx 视为确定性结果并缓存；429 与 5xx 是暂时性的，不缓存以便下次重试
        if raw.status in NO_CACHE_STATUS:
            return resp
        # 2xx 却一个字节都没有：这不是可用内容，多半是源站出错或中间层拦截。
        # 缓存下来会让这个 URL **永久失败** —— 后续运行连网络请求都不发，直接重放
        # 那份空内容。空 404 不在其列：那是"这个地址没有内容"的确定性结论，
        # 照旧缓存（多尺寸候选里"此尺寸不存在"是常态，每次重问一遍反而更像爬虫）。
        if resp.ok and not raw.content:
            log.warning("源站返回空响应（HTTP %d），不写缓存：%s", raw.status, url)
            return resp
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
        image: bool = False,
    ) -> CachedResponse:
        """抓取一个 URL，优先命中磁盘缓存。

        缓存命中即返回，**但两种条目除外**：429/5xx（暂时性失败），
        以及 :meth:`_cache_is_stale` 认定"结论会被时间推翻"的条目
        （403/418、不可信的 404）—— 联网时它们一律重新请求一次。

        :param referer: 部分资源（尤其 ``img*.doubanio.com``）需要 Referer 才返回 200。
        :param force: 忽略缓存强制重新请求。
        :param raise_for_blocked: 被拦截时是否抛 ``BlockedError``。
            设为 ``False`` 时（如 archive.org 兜底路径）会返回被拦截的响应体，
            **但缓存命中路径上的拦截仍由该参数控制**（见上方 ``BLOCKED_STATUS`` 分支）。
        :param image: 这是图片子资源请求，改用图片的请求头特征
            （见 :func:`image_request_headers`）。缓存命中时该参数无影响。
        """
        if not force:
            cached = self._read_cache(url)
            if cached is not None:
                # 429/5xx 属于暂时性失败，历史缓存一律视为过期
                if cached.status not in NO_CACHE_STATUS:
                    if not self.offline and self._cache_is_stale(cached, url):
                        log.info("缓存中的 %d 不可信，改为重新请求：%s", cached.status, url)
                    else:
                        self.stats.cache_hits += 1
                        if cached.status in BLOCKED_STATUS and raise_for_blocked:
                            raise BlockedError(url, "缓存记录为被拦截", cached.status)
                        return cached

        if self.offline:
            raise OfflineCacheMiss(url, "离线模式下缓存未命中")

        return self._fetch_network(url, referer, image, raise_for_blocked=raise_for_blocked)

    def _cache_is_stale(self, cached: CachedResponse, url: str) -> bool:
        """缓存里这份"拿不到"的结论是否可能已经被时间推翻（只在联网时问）。

        两类缓存会在原地结成死结，联网时一律不信、重新请求一次：

        * **403 / 418**。那是"此刻被拒绝"，不是"内容不存在"：登录态变了、
          风控窗口过去了、防盗链的请求头修好了，它就不成立 —— 而它恰恰是最
          需要重试的一类。写进缓存是有意的（避免同一 URL 反复冲击源站），
          但**重放**它会让 ``--recheck-unavailable`` 变成一句空话：进度里把
          条目重新选出来，请求还没出门就被磁盘上的 403 顶回去，日志与上一次
          一模一样，只能靠手工删缓存文件才能重置。
        * **不可信的 404**（小站 widget 抖动，见 :func:`is_untrusted_missing`）。
        """
        return cached.status in BLOCKED_STATUS or is_untrusted_missing(url, cached.status, self.cfg)

    def get_html(self, url: str, **kwargs: Any) -> str:
        return self.fetch(url, **kwargs).text

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        return self.fetch(url, **kwargs).content

    def get_image(self, url: str, *, force: bool = False) -> CachedResponse:
        """抓取图片。

        两件事都不能少：带 ``Referer``（否则 doubanio 的防盗链返回 **418**），
        以及换成图片的请求头特征（``image=True``，见 :func:`image_request_headers`）。
        """
        return self.fetch(url, referer=self.cfg.image_referer, force=force, image=True)

    # ------------------------------------------------------------------ 收尾

    def __enter__(self) -> "BaseFetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def finalize(self) -> FetchStats:
        self.stats.elapsed = time.monotonic() - self._started_at
        return self.stats


# ---------------------------------------------------------------- curl_cffi 实现


class Fetcher(BaseFetcher):
    """基于 curl_cffi 的 HTTP 抓取器（带浏览器 TLS 指纹）。"""

    retryable_exceptions = CURL_RETRYABLE_EXCEPTIONS

    def __init__(
        self,
        cfg: Config = CONFIG,
        *,
        offline: bool | None = None,
        session: Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        impersonate: str | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        super().__init__(cfg, offline=offline, sleep=sleep, limiter=limiter)
        self.impersonate = impersonate or cfg.impersonate
        self._session = session or self._build_session()
        self.stats.impersonate = self.impersonate

    def _build_session(self) -> Session:
        """构造带浏览器指纹的会话。"""
        session = Session(impersonate=self.impersonate, timeout=self.cfg.timeout)
        # 声明中文优先，与真实浏览器一致（不轮换）
        session.headers["Accept-Language"] = "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7"
        # 让 libcurl 读取 http_proxy / https_proxy 环境变量
        session.trust_env = True
        return session

    def _attempt(
        self, url: str, referer: str | None, image: bool = False
    ) -> RawResponse:
        """单次网络尝试。可重试的错误以异常抛出交给 tenacity。

        文档导航只补 ``Referer``，其余头交给 ``impersonate`` 的默认值
        （那本来就是导航的头）；图片则整组换掉，见 :func:`image_request_headers`。
        """
        if image:
            headers: dict[str, str | None] = image_request_headers(url, referer)
        else:
            headers = {"Referer": referer} if referer else {}

        self._limiter.wait()
        self._limiter.mark()
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

        return RawResponse(
            status=resp.status_code,
            content=resp.content,
            content_type=resp.headers.get("Content-Type", "") or "",
            final_url=str(getattr(resp, "url", "") or url),
        )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:  # noqa: BLE001 - 关闭失败无关紧要
            pass


# ---------------------------------------------------------------------- 辅助


def estimate_duration(request_count: int, cfg: Config = CONFIG) -> str:
    """按平均间隔估算耗时，用于 ``--dry-run`` 预演。"""
    from .util import human_duration

    avg = (cfg.delay_min + cfg.delay_max) / 2
    return human_duration(request_count * avg)


def count_cached(cfg: Config, urls: Iterable[str]) -> int:
    """统计给定 URL 中有多少已在缓存内（离线可用数量）。"""
    return sum(1 for u in urls if cache_paths(cfg, u)[0].exists())
