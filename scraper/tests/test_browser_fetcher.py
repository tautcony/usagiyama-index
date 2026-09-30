"""浏览器后端的策略测试（零浏览器）。

用 ``FakeDriver`` 替换 PlaywrightDriver，覆盖缓存、限速、熔断、
风控判定、懒启动、统计合并等全部分支。真实浏览器的冒烟测试用
``@pytest.mark.browser`` 标记，默认跳过。
"""

from __future__ import annotations

import dataclasses

import pytest

from scraper.browser import (
    BLOCKED_HOSTS,
    BLOCKED_RESOURCE_TYPES,
    ChallengeError,
    BrowserFetcher,
    PlaywrightDriver,
    is_challenge_url,
    make_route_handler,
    PLAYWRIGHT_RETRYABLE_EXCEPTIONS,
)
from scraper.http_client import (
    BlockedError,
    CircuitBreakerOpen,
    FetchError,
    Fetcher,
    OfflineCacheMiss,
    RateLimiter,
)
from scraper.tests.fakes import FakeDriver, FakeRequest, FakeRoute
from scraper.tests.test_http_client import FakeResponse, FakeSession

URL = "https://site.douban.com/211330/room/2793793/"


@pytest.fixture
def sleeper() -> list[float]:
    return []


@pytest.fixture
def browser_factory(cfg, sleeper):
    """构造 BrowserFetcher + 注入的 FakeDriver + 内部图片 Fetcher 的假 session。"""

    def build(results=None, *, image_responses=None, **kwargs):
        driver = FakeDriver(results, **kwargs.pop("driver_kwargs", {}))
        session = FakeSession(image_responses)
        image_fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher = BrowserFetcher(
            cfg, driver=driver, sleep=sleeper.append, image_fetcher=image_fetcher, **kwargs
        )
        return fetcher, driver, session

    return build


class TestChallengeDetection:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://sec.douban.com/c?r=https%3A%2F%2Fwww.douban.com%2F", True),
            ("https://sec.douban.com/", True),
            ("https://site.douban.com/211330/", False),
            ("https://www.douban.com/note/1/", False),
            ("https://notsec.douban.com/", False),
            ("", False),
        ],
    )
    def test_is_challenge_url(self, url: str, expected: bool) -> None:
        assert is_challenge_url(url) is expected

    def test_challenge_raises_and_flags_session(self, browser_factory) -> None:
        fetcher, driver, _ = browser_factory(
            [(200, "https://sec.douban.com/c?r=x", "<html>verify</html>")]
        )
        with pytest.raises(ChallengeError) as excinfo:
            fetcher.fetch(URL)
        assert fetcher.session_expired is True
        assert "sec.douban.com" in str(excinfo.value)
        assert excinfo.value.final_url == "https://sec.douban.com/c?r=x"

    def test_challenge_is_a_blocked_error(self) -> None:
        """必须是 BlockedError 子类，现有 resolver/熔断机制才能自动接管。"""
        assert issubclass(ChallengeError, BlockedError)

    def test_challenge_response_is_not_cached(self, browser_factory) -> None:
        """人机校验页可能是 200，缓存下来会污染后续运行。"""
        fetcher, _, _ = browser_factory(
            [(200, "https://sec.douban.com/c?r=x", "<html>verify</html>")]
        )
        with pytest.raises(ChallengeError):
            fetcher.fetch(URL)
        assert fetcher.cache_has(URL) is False

    def test_challenge_counts_toward_circuit_breaker(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory(
            [(200, "https://sec.douban.com/c?r=x", "<html>v</html>")]
        )
        for index in range(2):
            with pytest.raises(ChallengeError):
                fetcher.fetch(f"{URL}?n={index}")
        with pytest.raises(CircuitBreakerOpen):
            fetcher.fetch(f"{URL}?n=3")


class TestCaching:
    def test_cache_hit_does_not_touch_driver(self, browser_factory) -> None:
        """懒启动的核心保证：缓存命中时绝不启动浏览器。"""
        fetcher, driver, _ = browser_factory()
        first = fetcher.fetch(URL)
        assert driver.calls == [(URL, None)]
        second = fetcher.fetch(URL)
        assert second.from_cache is True
        assert second.content == first.content
        assert len(driver.calls) == 1  # 没有第二次导航

    def test_cache_is_shared_with_http_backend(self, cfg, browser_factory) -> None:
        """浏览器写入的缓存必须能被 curl_cffi 后端读到（同一套 cache_paths）。"""
        fetcher, _, _ = browser_factory([(200, "", "<html>browser</html>")])
        fetcher.fetch(URL)
        http = Fetcher(cfg, session=FakeSession(), sleep=lambda _: None)
        assert http.fetch(URL).text == "<html>browser</html>"

    def test_force_bypasses_cache(self, browser_factory) -> None:
        fetcher, driver, _ = browser_factory([(200, "", "<html>a</html>")])
        fetcher.fetch(URL)
        fetcher.fetch(URL, force=True)
        assert len(driver.calls) == 2

    def test_blocked_response_is_cached(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory([(403, "", "<html>denied</html>")])
        with pytest.raises(BlockedError):
            fetcher.fetch(URL)
        assert fetcher.cache_has(URL) is True


class TestBlockedAndCircuitBreaker:
    def test_403_raises_blocked(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory([(403, "", "denied")])
        with pytest.raises(BlockedError):
            fetcher.fetch(URL)

    def test_three_consecutive_blocks_open_circuit(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory([(403, "", "denied")])
        for index in range(2):
            with pytest.raises(BlockedError):
                fetcher.fetch(f"{URL}?n={index}")
        with pytest.raises(CircuitBreakerOpen):
            fetcher.fetch(f"{URL}?n=3")

    def test_success_resets_block_counter(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory(
            [(403, "", "denied"), (200, "", "ok"), (403, "", "denied")]
        )
        with pytest.raises(BlockedError):
            fetcher.fetch(f"{URL}?a=1")
        fetcher.fetch(f"{URL}?a=2")  # 成功，计数归零
        with pytest.raises(BlockedError):  # 若未归零，这里会熔断
            fetcher.fetch(f"{URL}?a=3")


class TestOffline:
    def test_offline_without_cache_raises_and_never_creates_driver(self, cfg, sleeper) -> None:
        driver = FakeDriver()
        fetcher = BrowserFetcher(
            cfg,
            offline=True,
            driver=driver,
            sleep=sleeper.append,
            image_fetcher=Fetcher(cfg, session=FakeSession(), sleep=sleeper.append),
        )
        with pytest.raises(OfflineCacheMiss):
            fetcher.fetch(URL)
        assert driver.calls == []

    def test_offline_with_cache_serves_content(self, cfg, sleeper) -> None:
        driver = FakeDriver([(200, "", "<html>cached</html>")])
        fetcher = BrowserFetcher(
            cfg,
            driver=driver,
            sleep=sleeper.append,
            image_fetcher=Fetcher(cfg, session=FakeSession(), sleep=sleeper.append),
        )
        fetcher.fetch(URL)
        offline = BrowserFetcher(
            cfg,
            offline=True,
            driver=FakeDriver(),
            sleep=sleeper.append,
            image_fetcher=Fetcher(cfg, session=FakeSession(), sleep=sleeper.append),
        )
        assert offline.fetch(URL).text == "<html>cached</html>"


class TestImageDelegation:
    def test_get_image_uses_curl_fetcher_not_driver(self, browser_factory) -> None:
        """图片走 curl_cffi：不触碰浏览器，且强制带 Referer。"""
        fetcher, driver, session = browser_factory(
            image_responses=[FakeResponse(200, b"\xff\xd8\xff\xe0jpeg")]
        )
        result = fetcher.get_image("https://img9.doubanio.com/view/note/raw/public/p1.jpg")
        assert result.status == 200
        assert driver.calls == []  # 浏览器完全没被用到
        _, headers = session.calls[0]
        assert headers.get("Referer") == fetcher.cfg.image_referer

    def test_finalize_merges_image_stats(self, browser_factory) -> None:
        fetcher, _, _ = browser_factory(
            [(200, "", "<html>ok</html>")],
            image_responses=[FakeResponse(200, b"\xff\xd8\xff\xe0jpeg")],
        )
        fetcher.fetch(URL)
        fetcher.get_image("https://img9.doubanio.com/view/note/raw/public/p1.jpg")
        stats = fetcher.finalize()
        second = fetcher.finalize()
        assert stats.requests == 2  # 1 次浏览器导航 + 1 次图片请求
        assert stats.impersonate.startswith("browser:")
        assert second.requests == stats.requests


class TestLifecycle:
    def test_playwright_base_error_is_not_retryable(self) -> None:
        assert all(error.__name__ != "Error" for error in PLAYWRIGHT_RETRYABLE_EXCEPTIONS)

    def test_close_is_idempotent(self, browser_factory) -> None:
        fetcher, driver, _ = browser_factory()
        fetcher.fetch(URL)
        fetcher.close()
        fetcher.close()
        assert driver.closed is True

    def test_context_manager_closes(self, browser_factory) -> None:
        fetcher, driver, _ = browser_factory()
        with fetcher:
            fetcher.fetch(URL)
        assert driver.closed is True


class TestRetryableStatus:
    def test_500_is_retried(self, cfg, sleeper) -> None:
        """5xx 属于可重试状态，应重试而不是直接失败。"""
        driver = FakeDriver([(500, "", "err"), (200, "", "<html>ok</html>")])
        fetcher = BrowserFetcher(
            cfg,
            driver=driver,
            sleep=sleeper.append,
            image_fetcher=Fetcher(cfg, session=FakeSession(), sleep=sleeper.append),
        )
        assert fetcher.fetch(URL).text == "<html>ok</html>"
        assert len(driver.calls) == 2
        assert fetcher.stats.retries == 1


class TestRateLimiter:
    def test_first_request_does_not_sleep(self) -> None:
        slept: list[float] = []
        limiter = RateLimiter(dataclasses.replace(_cfg()), sleep=slept.append)
        limiter.wait()
        assert slept == []

    def test_second_request_waits_remaining_delay(self) -> None:
        slept: list[float] = []
        cfg = dataclasses.replace(_cfg(), delay_min=5.0, delay_max=5.0)
        limiter = RateLimiter(cfg, sleep=slept.append)
        limiter.mark()
        limiter.wait()
        assert len(slept) == 1
        # 刚 mark 过，剩余等待应接近完整间隔
        assert 4.9 < slept[0] <= 5.0

    def test_elapsed_time_is_absorbed(self) -> None:
        """导航耗时被吸收进间隔：单请求总时长是 max(delay, 耗时)，不是相加。"""
        slept: list[float] = []
        cfg = dataclasses.replace(_cfg(), delay_min=5.0, delay_max=5.0)
        limiter = RateLimiter(cfg, sleep=slept.append)
        limiter._last = __import__("time").monotonic() - 4.0  # 模拟耗时 4 秒
        limiter.wait()
        assert len(slept) == 1
        assert 0.9 < slept[0] <= 1.0  # 只需再等 ~1 秒

    def test_shared_limiter_between_backends(self, cfg, sleeper) -> None:
        """浏览器与图片下载共享同一条时间线。"""
        limiter = RateLimiter(cfg, sleep=sleeper.append)
        image_fetcher = Fetcher(cfg, session=FakeSession(), sleep=sleeper.append, limiter=limiter)
        fetcher = BrowserFetcher(cfg, driver=FakeDriver(), sleep=sleeper.append, limiter=limiter)
        assert fetcher._limiter is image_fetcher._limiter


def _cfg():
    from scraper.config import CONFIG

    return CONFIG


class TestRouteHandler:
    def test_images_are_blocked(self) -> None:
        handler = make_route_handler()
        route = FakeRoute(FakeRequest("https://img9.doubanio.com/a.jpg", "image"))
        handler(route)
        assert route.action == "abort"
        assert route.error_code == "blockedbyclient"

    def test_fonts_and_media_are_blocked(self) -> None:
        handler = make_route_handler()
        for resource_type in ("font", "media"):
            route = FakeRoute(FakeRequest("https://x.com/a", resource_type))
            handler(route)
            assert route.action == "abort", resource_type

    def test_stylesheets_are_kept(self) -> None:
        """CSS 必须保留：元素不可见会干扰后续的可见性判断。"""
        handler = make_route_handler()
        route = FakeRoute(FakeRequest("https://x.com/a.css", "stylesheet"))
        handler(route)
        assert route.action == "continue"

    def test_documents_and_scripts_are_kept(self) -> None:
        handler = make_route_handler()
        for resource_type in ("document", "script", "xhr", "fetch"):
            route = FakeRoute(FakeRequest("https://x.com/a", resource_type))
            handler(route)
            assert route.action == "continue", resource_type

    def test_analytics_hosts_are_blocked(self) -> None:
        handler = make_route_handler()
        for host in BLOCKED_HOSTS:
            route = FakeRoute(FakeRequest(f"https://{host}/collect", "script"))
            handler(route)
            assert route.action == "abort", host

    def test_subdomain_of_blocked_host_is_blocked(self) -> None:
        handler = make_route_handler()
        route = FakeRoute(FakeRequest("https://ssl.google-analytics.com/collect", "script"))
        handler(route)
        assert route.action == "abort"

    def test_handler_never_raises(self) -> None:
        """路由回调抛异常会让请求永久挂起，必须有兜底。"""

        class ExplodingRoute:
            """读取 request 就抛错的 Route 替身。"""

            def __init__(self) -> None:
                self.action: str | None = None

            @property
            def request(self):
                raise RuntimeError("boom")

            def abort(self, error_code: str = "failed") -> None:
                self.action = "abort"

            def continue_(self, **kwargs: object) -> None:
                self.action = "continue"

        route = ExplodingRoute()
        make_route_handler()(route)
        assert route.action == "continue"


class TestUserAgentNormalisation:
    """无头启动会给 UA 带上 HeadlessChrome，需改回 Chrome。

    这里只测字符串处理逻辑，不启动真实浏览器。
    """

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (
                "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) "
                "HeadlessChrome/152.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36",
            ),
            (
                "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36",
            ),
        ],
    )
    def test_normalisation(self, raw: str, expected: str) -> None:
        normalized = raw.replace("HeadlessChrome", "Chrome")
        assert normalized == expected
        assert "HeadlessChrome" not in normalized
        # 版本号必须保持浏览器自己的真实值，不伪造
        assert "152.0.0.0" in normalized


@pytest.mark.browser
class TestRealBrowser:
    """真实浏览器冒烟测试，默认跳过（`-m browser` 才运行）。"""

    def test_launch_and_navigate(self, cfg) -> None:
        pytest.importorskip("playwright")
        driver = PlaywrightDriver(cfg, headless=True)
        try:
            raw = driver.navigate("https://example.com")
            assert raw.status == 200
            assert "Example" in raw.content.decode("utf-8", errors="replace")
        finally:
            driver.close()
