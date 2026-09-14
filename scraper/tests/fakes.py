"""测试替身。

与 ``test_http_client.py`` 里用 ``FakeSession`` 替换 curl_cffi Session 的思路一致，
这里用 ``FakeDriver`` 替换 PlaywrightDriver —— 于是浏览器后端的全部策略
（缓存、限速、熔断、风控判定、懒启动）都能在**不启动真实浏览器**的前提下被测试。
"""

from __future__ import annotations

from typing import Any

from scraper.http_client import RawResponse


class FakeDriver:
    """BrowserDriver 的替身。

    ``results`` 是脚本化的响应序列，每项为 ``(status, final_url, html)``；
    用完后重复最后一项。``final_url`` 传空串表示与请求 URL 相同。
    """

    def __init__(
        self,
        results: list[tuple[int, str, str]] | None = None,
        *,
        raise_on: dict[str, BaseException] | None = None,
    ) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.closed = False
        self._results = list(results or [(200, "", "<html><body>ok</body></html>")])
        self._index = 0
        self._raise_on = raise_on or {}

    def navigate(
        self, url: str, *, referer: str | None = None, timeout: int | None = None
    ) -> RawResponse:
        self.calls.append((url, referer))
        if url in self._raise_on:
            raise self._raise_on[url]
        status, final_url, html = self._results[min(self._index, len(self._results) - 1)]
        self._index += 1
        return RawResponse(
            status=status,
            content=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            final_url=final_url or url,
        )

    def close(self) -> None:
        self.closed = True


class FakeRequest:
    """Playwright Request 的替身（路由拦截测试用）。"""

    def __init__(self, url: str, resource_type: str = "document") -> None:
        self.url = url
        self.resource_type = resource_type


class FakeRoute:
    """Playwright Route 的替身，记录被 abort 还是 continue。"""

    def __init__(self, request: FakeRequest) -> None:
        self.request = request
        self.action: str | None = None
        self.error_code: str | None = None

    def abort(self, error_code: str = "failed") -> None:
        self.action = "abort"
        self.error_code = error_code

    def continue_(self, **kwargs: Any) -> None:
        self.action = "continue"
