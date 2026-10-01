"""传输层协议。

项目有两种抓取方式：

* :class:`~scraper.http_client.Fetcher` —— curl_cffi，带浏览器 TLS 指纹（快、轻）
* :class:`~scraper.browser.BrowserFetcher` —— Playwright 驱动系统 Chrome（重、能执行 JS、带登录态）

两者都满足本模块定义的 :class:`Transport` 协议，因此 ``resolver`` / ``media``
等消费方**不需要知道自己拿到的是哪一种**，只依赖这组方法与异常。

协议刻意与 ``Fetcher`` 的既有公开面完全一致——这样引入浏览器后端时，
消费方的**运行期行为零改动**，只需把类型标注从 ``Fetcher`` 换成 ``Transport``。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .config import Config
from .http_client import CachedResponse, FetchStats


@runtime_checkable
class Transport(Protocol):
    """抓取传输方式的统一接口。"""

    cfg: Config
    stats: FetchStats

    def cache_has(self, url: str) -> bool:
        """该 URL 是否已有磁盘缓存（不发请求）。"""
        ...

    def invalidate_cache(self, url: str) -> bool:
        """丢弃某个 URL 的缓存条目，返回是否删掉了东西。

        调用方发现"缓存里的内容不可用"时使用（例如缓存了一份非图片的 200）。
        """
        ...

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

        :param image: 图片子资源请求，改用图片的请求头特征。

        :raises BlockedError: 被源站拦截（403/418）或触发人机校验
        :raises CircuitBreakerOpen: 连续被拦截超阈值
        :raises OfflineCacheMiss: 离线模式且无缓存
        :raises FetchError: 重试耗尽后仍失败
        """
        ...

    def get_html(self, url: str, **kwargs: Any) -> str:
        """抓取并解码为文本。"""
        ...

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        """抓取原始字节。"""
        ...

    def get_image(
        self, url: str, *, force: bool = False, referer: str | None = None
    ) -> CachedResponse:
        """抓取图片，强制带 Referer（否则 doubanio 返回 418）。"""
        ...

    def close(self) -> None:
        """释放底层资源（幂等）。"""
        ...

    def finalize(self) -> FetchStats:
        """收尾并返回运行统计。"""
        ...

    def __enter__(self) -> "Transport": ...

    def __exit__(self, *exc: object) -> None: ...
