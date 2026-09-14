"""HTTP 客户端测试：缓存、限速、退避、熔断。

用假 session 替换 curl_cffi 的真实 Session，从而在不联网的前提下
验证归档策略本身是否正确。
"""

from __future__ import annotations

import dataclasses

import pytest

from scraper.http_client import (
    BLOCKED_STATUS,
    IMAGE_ACCEPT,
    NO_CACHE_STATUS,
    RETRYABLE_STATUS,
    BlockedError,
    CircuitBreakerOpen,
    FetchError,
    Fetcher,
    OfflineCacheMiss,
    cache_domain,
    cache_paths,
    decode_html,
    fetch_site,
    image_request_headers,
    is_untrusted_missing,
    migrate_flat_cache,
    site_suffix,
)


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 40


class FakeResponse:
    def __init__(self, status: int, content: bytes = b"ok", content_type: str = "text/html; charset=utf-8"):
        self.status_code = status
        self.content = content
        self.headers = {"Content-Type": content_type}


class FakeSession:
    """最小的 curl_cffi Session 替身。"""

    def __init__(self, responses: list[FakeResponse] | None = None) -> None:
        self.headers: dict[str, str] = {}
        self.trust_env = False
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.closed = False
        self._responses = list(responses or [FakeResponse(200)])
        self._index = 0

    def get(self, url: str, headers: dict[str, str] | None = None, **kwargs: object) -> FakeResponse:
        self.calls.append((url, dict(headers or {})))
        if self._index < len(self._responses):
            response = self._responses[self._index]
            self._index += 1
        else:
            response = self._responses[-1]
        return response

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def sleeper() -> list[float]:
    return []


@pytest.fixture
def fetcher_factory(cfg, sleeper):
    def build(responses=None, **kwargs):
        session = FakeSession(responses)
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append, **kwargs)
        return fetcher, session

    return build


class TestStatusSets:
    def test_429_is_retryable_not_blocked(self) -> None:
        """429 是限流而非封禁，应退避重试而不是熔断。"""
        assert 429 in RETRYABLE_STATUS
        assert 429 not in BLOCKED_STATUS

    def test_403_and_418_are_blocked(self) -> None:
        assert {403, 418} <= BLOCKED_STATUS

    def test_transient_statuses_not_cached(self) -> None:
        assert {429, 500, 502, 503, 504} <= NO_CACHE_STATUS


class TestDecodeHtml:
    def test_utf8_default(self) -> None:
        assert decode_html("中文".encode()) == "中文"

    def test_charset_from_content_type(self) -> None:
        assert decode_html("中文".encode("gbk"), "text/html; charset=gbk") == "中文"

    def test_bad_bytes_replaced(self) -> None:
        assert decode_html(b"\xff\xfe\x00") is not None


class TestCaching:
    def test_response_cached_and_reused(self, fetcher_factory) -> None:
        fetcher, session = fetcher_factory([FakeResponse(200, b"<html>a</html>")])
        first = fetcher.fetch("https://x/a")
        assert not first.from_cache

        second = fetcher.fetch("https://x/a")
        assert second.from_cache
        assert second.content == first.content
        assert len(session.calls) == 1  # 第二次没有再发请求

    def test_cache_survives_new_fetcher(self, cfg, sleeper) -> None:
        """跨进程续跑依赖磁盘缓存。"""
        session1 = FakeSession([FakeResponse(200, b"<html>cached</html>")])
        Fetcher(cfg, session=session1, sleep=sleeper.append).fetch("https://x/b")

        session2 = FakeSession()
        result = Fetcher(cfg, session=session2, sleep=sleeper.append).fetch("https://x/b")
        assert result.from_cache
        assert session2.calls == []

    def test_force_bypasses_cache(self, fetcher_factory) -> None:
        fetcher, session = fetcher_factory([FakeResponse(200, b"v1"), FakeResponse(200, b"v2")])
        fetcher.fetch("https://x/c")
        result = fetcher.fetch("https://x/c", force=True)
        assert result.content == b"v2"
        assert len(session.calls) == 2

    def test_404_is_cached(self, fetcher_factory) -> None:
        """确定性结果缓存下来，避免每次运行都重新撞 404。"""
        fetcher, session = fetcher_factory([FakeResponse(404, b"nope")])
        fetcher.fetch("https://x/gone")
        fetcher.fetch("https://x/gone")
        assert len(session.calls) == 1

    def test_429_is_retried_then_succeeds(self, cfg, sleeper) -> None:
        """429 是限流而非封禁：应退避重试，而不是直接失败。"""
        session = FakeSession([FakeResponse(429), FakeResponse(200, b"recovered")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        assert fetcher.fetch("https://x/limited").content == b"recovered"
        assert fetcher.stats.retries == 1

    def test_persistent_429_is_not_cached(self, cfg, sleeper) -> None:
        """重试用尽仍 429 时不应落缓存，否则下次运行会永久失败。"""
        session = FakeSession([FakeResponse(429)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        with pytest.raises(FetchError):
            fetcher.fetch("https://x/limited")
        assert not fetcher.cache_has("https://x/limited")

    def test_stale_429_cache_ignored(self, cfg, sleeper) -> None:
        """即使历史缓存里存了 429，也应视为过期重新请求。"""
        session = FakeSession([FakeResponse(429)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        try:
            fetcher.fetch("https://x/stale")
        except FetchError:
            pass

        session2 = FakeSession([FakeResponse(200, b"fresh")])
        fetcher2 = Fetcher(cfg, session=session2, sleep=sleeper.append)
        assert fetcher2.fetch("https://x/stale").content == b"fresh"


class TestUntrustedMissing:
    """小站的间歇性 404 不能当作"内容已不存在"。

    实测：同一个照片页 URL 会间歇性返回通用 404 页（"呃...你想访问的页面不存在"），
    几分钟后再请求就是 200。归档一旦判定"不存在"就不再回头看，所以这类 404
    既不写缓存、也不从缓存里取，解析层据此把单元标成"可重试"。
    域名清单见 ``Config.untrusted_404_hosts``。
    """

    GONE = "https://site.douban.com/211330/widget/photos/13431950/photo/2325379542/"

    def test_only_404_on_configured_hosts(self, cfg) -> None:
        assert is_untrusted_missing(self.GONE, 404, cfg)
        # 子域也算
        assert is_untrusted_missing("https://site.douban.com.evil/?", 404, cfg) is False
        assert is_untrusted_missing("https://www.douban.com/note/1/", 404, cfg) is False
        assert is_untrusted_missing(self.GONE, 200, cfg) is False

    def test_untrusted_404_not_written_to_cache(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(404, b"nope")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.fetch(self.GONE)

        assert not fetcher.cache_has(self.GONE)
        assert fetcher.stats.transient_misses == 1

    def test_cached_untrusted_404_is_refetched(self, cfg, sleeper) -> None:
        """修好之前写进去的缓存同样不算数：无需 ``--force`` 就能自愈。"""
        trusted = dataclasses.replace(cfg, untrusted_404_hosts=())
        Fetcher(
            trusted, session=FakeSession([FakeResponse(404, b"stale")]), sleep=sleeper.append
        ).fetch(self.GONE)

        session = FakeSession([FakeResponse(200, b"<html>back</html>")])
        result = Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.GONE)

        assert result.content == b"<html>back</html>"
        assert not result.from_cache
        assert len(session.calls) == 1

    def test_offline_still_uses_cached_untrusted_404(self, cfg, sleeper) -> None:
        """离线时没有别的办法，缓存照用（否则离线渲染会凭空少掉页面）。"""
        trusted = dataclasses.replace(cfg, untrusted_404_hosts=())
        Fetcher(
            trusted, session=FakeSession([FakeResponse(404, b"stale")]), sleep=sleeper.append
        ).fetch(self.GONE)

        offline_cfg = dataclasses.replace(cfg, offline=True)
        result = Fetcher(offline_cfg, session=FakeSession(), sleep=sleeper.append).fetch(self.GONE)
        assert result.from_cache
        assert result.status == 404


class TestCircuitBreaker:
    def test_403_raises_blocked(self, fetcher_factory) -> None:
        fetcher, _ = fetcher_factory([FakeResponse(403)])
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/forbidden")

    def test_consecutive_blocks_open_circuit(self, fetcher_factory) -> None:
        fetcher, _ = fetcher_factory([FakeResponse(403)])
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/1")
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/2")
        with pytest.raises(CircuitBreakerOpen):
            fetcher.fetch("https://x/3")

    def test_success_resets_counter(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(403), FakeResponse(200), FakeResponse(403), FakeResponse(403)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/a")
        fetcher.fetch("https://x/b")  # 成功，计数归零
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/c")
        with pytest.raises(BlockedError):
            fetcher.fetch("https://x/d")  # 仍只是 Blocked，未熔断


class TestBlockedCache:
    """被拦截（403/418）的缓存条目不能就地"结案"。

    实测：``www.douban.com`` 的话题页未登录时返回 403「没有访问权限」，并被写进
    缓存（写是有意的 —— 免得同一 URL 反复冲击源站）。但**重放**它会让
    ``--recheck-unavailable`` 变成空话：条目会被重新选出来，请求却还没出门就被
    磁盘上的 403 顶回去，日志跟上次一模一样。于是登录之后再想补抓，只能手工删掉
    缓存文件 —— 一条 URL 一个 sha1 文件名，这不是使用者该做的事。
    """

    TOPIC = "https://www.douban.com/topic/499780453/"

    def _seed_blocked_cache(self, cfg, sleeper, status: int = 403) -> None:
        """先用一次真实请求把 403 写进缓存（网络路径**总是**抛，与缓存命中一样）。"""
        fetcher = Fetcher(
            cfg,
            session=FakeSession([FakeResponse(status, b"<html>denied</html>")]),
            sleep=sleeper.append,
        )
        with pytest.raises(BlockedError):
            fetcher.fetch(self.TOPIC)
        assert fetcher.cache_has(self.TOPIC)  # 前提：拒绝确实被缓存了

    def test_cached_403_is_refetched(self, cfg, sleeper) -> None:
        """登录后重跑：缓存里的 403 不作数，真的再请求一次。"""
        self._seed_blocked_cache(cfg, sleeper)

        session = FakeSession([FakeResponse(200, b"<html>topic</html>")])
        result = Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.TOPIC)

        assert result.content == b"<html>topic</html>"
        assert not result.from_cache
        assert len(session.calls) == 1  # 确实发了请求，而不是重放缓存

    def test_cached_418_is_refetched(self, cfg, sleeper) -> None:
        self._seed_blocked_cache(cfg, sleeper, status=418)
        session = FakeSession([FakeResponse(200, JPEG, "image/jpeg")])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.TOPIC, image=True)
        assert len(session.calls) == 1

    def test_still_blocked_after_refetch(self, cfg, sleeper) -> None:
        """源站这次还是拒绝：结论不变，但结论是**问过**之后才下的。"""
        self._seed_blocked_cache(cfg, sleeper)
        session = FakeSession([FakeResponse(403, b"<html>denied</html>")])

        with pytest.raises(BlockedError):
            Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.TOPIC)
        assert len(session.calls) == 1

    def test_offline_still_uses_cached_403(self, cfg, sleeper) -> None:
        """离线时没有别的办法，缓存照用（否则离线渲染会凭空少掉"需登录"提示）。"""
        self._seed_blocked_cache(cfg, sleeper)

        offline_cfg = dataclasses.replace(cfg, offline=True)
        result = Fetcher(offline_cfg, session=FakeSession(), sleep=sleeper.append).fetch(
            self.TOPIC, raise_for_blocked=False
        )
        assert result.from_cache
        assert result.status == 403

    def test_force_still_bypasses_cache(self, cfg, sleeper) -> None:
        """``force`` 与"缓存被认定为过期"是同一件事的两种入口，行为要一致。"""
        self._seed_blocked_cache(cfg, sleeper)
        session = FakeSession([FakeResponse(200, b"<html>topic</html>")])
        result = Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.TOPIC, force=True)
        assert result.content == b"<html>topic</html>"

    def test_plain_200_cache_is_untouched(self, cfg, sleeper) -> None:
        """别把"重新请求"扩大到普通缓存 —— 二次运行零请求是这套工具的基本盘。"""
        session = FakeSession([FakeResponse(200, b"<html>cached</html>")])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch(self.TOPIC)

        session2 = FakeSession()
        result = Fetcher(cfg, session=session2, sleep=sleeper.append).fetch(self.TOPIC)
        assert result.from_cache
        assert session2.calls == []


class TestRetry:
    def test_retries_on_5xx_then_succeeds(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(503), FakeResponse(200, b"ok")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        assert fetcher.fetch("https://x/flaky").content == b"ok"
        assert fetcher.stats.retries == 1
        assert len(session.calls) == 2

    def test_gives_up_after_max_retries(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(500)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        with pytest.raises(FetchError):
            fetcher.fetch("https://x/down")
        assert len(session.calls) == cfg.max_retries + 1

    def test_backoff_sleeps_between_retries(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(500)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        with pytest.raises(FetchError):
            fetcher.fetch("https://x/down")
        assert sleeper, "重试之间应当退避等待"


class TestRateLimit:
    def test_no_sleep_on_first_request(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200)])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch("https://x/a")
        assert sleeper == []

    def test_sleeps_between_requests(self, cfg, sleeper) -> None:
        cfg2 = dataclasses.replace(cfg, delay_min=5.0, delay_max=5.0)
        session = FakeSession([FakeResponse(200)])
        fetcher = Fetcher(cfg2, session=session, sleep=sleeper.append)
        fetcher.fetch("https://x/a")
        fetcher.fetch("https://x/b")
        # 两次请求之间至少等待一次
        assert any(value > 0 for value in sleeper)

    def test_cache_hit_does_not_sleep(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.fetch("https://x/a")
        sleeper.clear()
        fetcher.fetch("https://x/a")
        assert sleeper == []


class TestReferer:
    def test_image_request_sends_referer(self, cfg, sleeper) -> None:
        """doubanio 不带 Referer 会返回 418。"""
        session = FakeSession([FakeResponse(200, b"\xff\xd8\xff\xe0" + b"\x00" * 40, "image/jpeg")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.get_image("https://img9.doubanio.com/view/note/raw/public/p1.jpg")
        _, headers = session.calls[0]
        assert headers.get("Referer") == cfg.image_referer

    def test_plain_fetch_has_no_referer(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200)])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch("https://x/a")
        _, headers = session.calls[0]
        assert "Referer" not in headers


class TestImageRequestHeaders:
    """图片请求必须发"图片的头"，而不是 impersonate 默认的"导航的头"。

    背景：实测每个图片请求发的都是 ``Accept: text/html,…`` / ``Sec-Fetch-Dest:
    document`` / ``Sec-Fetch-Mode: navigate`` / ``Sec-Fetch-Site: none`` /
    ``Sec-Fetch-User: ?1`` / ``Upgrade-Insecure-Requests: 1`` —— 等于自报
    "我要加载一份 HTML 文档"，实际要的却是一张 jpg。
    """

    RAW = "https://img2.doubanio.com/view/photo/raw/public/p2500516321.jpg"

    def test_get_image_sends_image_profile(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, JPEG, "image/jpeg")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)

        fetcher.get_image(self.RAW)

        assert session.calls[0][0] == self.RAW
        headers = session.calls[0][1]
        assert headers["Accept"] == IMAGE_ACCEPT
        assert "text/html" not in headers["Accept"]
        assert headers["Sec-Fetch-Dest"] == "image"
        assert headers["Sec-Fetch-Mode"] == "no-cors"
        assert headers["Sec-Fetch-Site"] == "cross-site"
        assert headers["Referer"] == cfg.image_referer

    def test_navigation_only_headers_are_deleted(self, cfg, sleeper) -> None:
        """值为 ``None`` 时 curl_cffi 会真正删掉这两个头（否则自相矛盾）。"""
        session = FakeSession([FakeResponse(200, JPEG, "image/jpeg")])
        Fetcher(cfg, session=session, sleep=sleeper.append).get_image(self.RAW)
        headers = session.calls[0][1]
        assert headers["Sec-Fetch-User"] is None
        assert headers["Upgrade-Insecure-Requests"] is None

    def test_document_fetch_keeps_navigation_profile(self, cfg, sleeper) -> None:
        """文档请求不做任何额外改动，只有 Referer。"""
        session = FakeSession([FakeResponse(200)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.fetch("https://site.douban.com/211330/", referer="https://site.douban.com/")
        assert session.calls[0][1] == {"Referer": "https://site.douban.com/"}

    def test_cache_hit_does_not_re_request(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, JPEG, "image/jpeg")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.get_image(self.RAW)
        fetcher.get_image(self.RAW)
        assert len(session.calls) == 1


class TestFetchSite:
    @pytest.mark.parametrize(
        ("url", "referer", "expected"),
        [
            # 详情页与图片 CDN 的域名不同（douban.com vs doubanio.com）
            ("https://img2.doubanio.com/p.jpg", "https://site.douban.com/211330/", "cross-site"),
            # 同一注册域下的不同主机名则是 same-site（这正是该取值的定义）
            ("https://www.douban.com/p.jpg", "https://site.douban.com/211330/", "same-site"),
            # 同一注册域的图片分片
            ("https://img1.doubanio.com/p.jpg", "https://img9.doubanio.com/p.jpg", "same-site"),
            ("https://img1.doubanio.com/p.jpg", "https://img1.doubanio.com/page", "same-origin"),
            # 没有来源页
            ("https://img1.doubanio.com/p.jpg", None, "none"),
            ("https://img1.doubanio.com/p.jpg", "", "none"),
        ],
    )
    def test_values(self, url: str, referer: str | None, expected: str) -> None:
        assert fetch_site(url, referer) == expected

    def test_site_suffix_takes_registrable_domain(self) -> None:
        assert site_suffix("img2.doubanio.com") == "doubanio.com"
        assert site_suffix("site.douban.com") == "douban.com"
        assert site_suffix("localhost") == "localhost"

    def test_headers_helper_without_referer(self) -> None:
        headers = image_request_headers("https://img1.doubanio.com/p.jpg", None)
        assert headers["Sec-Fetch-Site"] == "none"
        assert "Referer" not in headers


class TestCacheHygiene:
    def test_empty_2xx_is_not_cached(self, cfg, sleeper) -> None:
        """空 200 不是可用内容，缓存下来会让这个 URL 永久失败。"""
        session = FakeSession([FakeResponse(200, b"")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)

        first = fetcher.fetch("https://x/empty")
        second = fetcher.fetch("https://x/empty")

        assert first.status == 200 and first.content == b""
        assert not second.from_cache
        assert len(session.calls) == 2

    def test_empty_404_is_still_cached(self, cfg, sleeper) -> None:
        """空 404 是确定性结论，照旧缓存 —— 否则每次运行都要重问一遍。"""
        session = FakeSession([FakeResponse(404, b"", "text/html; charset=utf-8")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)

        fetcher.fetch("https://img2.doubanio.com/view/photo/raw/public/p1.jpg")
        second = fetcher.fetch("https://img2.doubanio.com/view/photo/raw/public/p1.jpg")

        assert second.from_cache and second.status == 404
        assert len(session.calls) == 1

    def test_invalidate_cache_removes_both_files(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, b"<html>error</html>")])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        url = "https://img2.doubanio.com/view/photo/raw/public/p1.jpg"
        fetcher.fetch(url)

        assert fetcher.cache_has(url)
        assert fetcher.invalidate_cache(url) is True
        assert not fetcher.cache_has(url)
        body, meta = cache_paths(cfg, url)
        assert not body.exists() and not meta.exists()

    def test_invalidate_missing_entry_is_noop(self, cfg) -> None:
        assert Fetcher(cfg, session=FakeSession()).invalidate_cache("https://x/none") is False

    def test_invalidated_url_is_refetched_next_run(self, cfg, sleeper) -> None:
        """坏缓存清掉之后，下一次运行会重新请求（无需 --force）。"""
        url = "https://img1.doubanio.com/view/note/raw/public/p1.jpg"
        first = FakeSession([FakeResponse(200, b"<html>challenge</html>")])
        Fetcher(cfg, session=first, sleep=sleeper.append).fetch(url)

        second = FakeSession([FakeResponse(200, JPEG, "image/jpeg")])
        fetcher = Fetcher(cfg, session=second, sleep=sleeper.append)
        assert fetcher.fetch(url).from_cache  # 坏内容仍在缓存里

        fetcher.invalidate_cache(url)
        assert fetcher.fetch(url).content == JPEG
        assert len(second.calls) == 1


class TestFetchErrorMessage:
    def test_bare_message_kept_separate_from_url(self) -> None:
        exc = FetchError("https://x/a", "源站拒绝访问", 418)
        assert exc.message == "源站拒绝访问"
        assert exc.status == 418
        assert "源站拒绝访问 [418] https://x/a" == str(exc)


class TestOffline:
    def test_offline_hits_cache(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, b"cached")])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch("https://x/a")
        offline = Fetcher(cfg, session=FakeSession(), sleep=sleeper.append, offline=True)
        assert offline.fetch("https://x/a").content == b"cached"

    def test_offline_miss_raises(self, cfg, sleeper) -> None:
        offline = Fetcher(cfg, session=FakeSession(), sleep=sleeper.append, offline=True)
        with pytest.raises(OfflineCacheMiss):
            offline.fetch("https://x/never-fetched")


class TestStats:
    def test_counts_requests_and_hits(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.fetch("https://x/a")
        fetcher.fetch("https://x/a")
        assert fetcher.stats.requests == 1
        assert fetcher.stats.cache_hits == 1

    def test_stats_serialisable(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200)])
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.fetch("https://x/a")
        payload = fetcher.finalize().to_dict()
        assert payload["requests"] == 1
        assert "impersonate" in payload
        assert payload["byStatus"] == {"200": 1}

    def test_close_is_safe(self, cfg, sleeper) -> None:
        session = FakeSession()
        fetcher = Fetcher(cfg, session=session, sleep=sleeper.append)
        fetcher.close()
        assert session.closed

class TestCacheIsolationByDomain:
    """缓存按域名分目录，确保不同源站互相隔离。"""

    def test_domain_extracted(self) -> None:
        assert cache_domain("https://site.douban.com/211330/room/1/") == "site.douban.com"
        assert cache_domain("https://img9.doubanio.com/view/note/raw/public/p1.jpg") == "img9.doubanio.com"
        assert cache_domain("https://web.archive.org/cdx/search/cdx?url=x") == "web.archive.org"

    def test_domain_lowercased(self) -> None:
        assert cache_domain("https://SITE.Douban.COM/x") == "site.douban.com"

    def test_port_ignored(self) -> None:
        assert cache_domain("http://site.douban.com:80/211330/") == "site.douban.com"

    def test_cache_path_under_domain_dir(self, cfg) -> None:
        body, meta = cache_paths(cfg, "https://site.douban.com/211330/room/1/")
        assert body.parent == cfg.cache_dir / "site.douban.com"
        assert meta.parent == cfg.cache_dir / "site.douban.com"
        assert body.suffix == ".body"
        assert meta.suffix == ".json"
        assert body.stem == meta.stem

    def test_same_path_different_domains_isolated(self, cfg) -> None:
        """不同域名下的同名路径必须落到不同目录。"""
        a, _ = cache_paths(cfg, "https://a.example.com/page")
        b, _ = cache_paths(cfg, "https://b.example.com/page")
        assert a.parent != b.parent
        assert a != b

    def test_different_domains_same_hash_possible_but_isolated(self, cfg) -> None:
        """sha1 只对完整 URL 取，域名不同则 URL 不同，键自然不同。"""
        a, _ = cache_paths(cfg, "https://a.example.com/x")
        b, _ = cache_paths(cfg, "https://b.example.com/x")
        assert a.name != b.name

    def test_writes_go_to_domain_dir(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, b"body")])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch("https://site.douban.com/211330/")
        domain_dir = cfg.cache_dir / "site.douban.com"
        assert domain_dir.is_dir()
        assert len(list(domain_dir.glob("*.body"))) == 1
        # 顶层不应有残留
        assert not list(cfg.cache_dir.glob("*.body"))

    def test_cache_read_from_domain_dir(self, cfg, sleeper) -> None:
        session = FakeSession([FakeResponse(200, b"cached")])
        Fetcher(cfg, session=session, sleep=sleeper.append).fetch("https://site.douban.com/211330/")
        second = Fetcher(cfg, session=FakeSession(), sleep=sleeper.append).fetch(
            "https://site.douban.com/211330/"
        )
        assert second.from_cache


class TestFlatCacheMigration:
    """旧版扁平缓存应被迁移到按域名分目录的新布局。"""

    def _write_flat(self, cfg, url: str, body: bytes = b"data") -> None:
        import hashlib
        import json

        key = hashlib.sha1(url.encode()).hexdigest()
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        (cfg.cache_dir / f"{key}.body").write_bytes(body)
        (cfg.cache_dir / f"{key}.json").write_text(
            json.dumps({"url": url, "status": 200, "sha1": hashlib.sha1(body).hexdigest()}),
            encoding="utf-8",
        )

    def test_migrates_flat_files(self, cfg) -> None:
        self._write_flat(cfg, "https://site.douban.com/211330/")
        assert migrate_flat_cache(cfg) == 1
        target = cfg.cache_dir / "site.douban.com"
        assert len(list(target.glob("*.body"))) == 1
        assert not list(cfg.cache_dir.glob("*.json"))

    def test_migration_is_idempotent(self, cfg) -> None:
        self._write_flat(cfg, "https://site.douban.com/211330/")
        migrate_flat_cache(cfg)
        assert migrate_flat_cache(cfg) == 0

    def test_migrated_cache_is_readable(self, cfg, sleeper) -> None:
        url = "https://site.douban.com/211330/"
        self._write_flat(cfg, url, b"<html>migrated</html>")
        migrate_flat_cache(cfg)
        result = Fetcher(cfg, session=FakeSession(), sleep=sleeper.append).fetch(url)
        assert result.from_cache
        assert result.content == b"<html>migrated</html>"

    def test_orphan_meta_without_body_removed(self, cfg) -> None:
        """迁移被打断留下的半截状态应被清理，而不是永久报错。"""
        import hashlib
        import json

        key = hashlib.sha1(b"https://x/y").hexdigest()
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        (cfg.cache_dir / f"{key}.json").write_text(
            json.dumps({"url": "https://x/y", "status": 200}), encoding="utf-8"
        )
        assert migrate_flat_cache(cfg) == 0
        assert not (cfg.cache_dir / f"{key}.json").exists()

    def test_corrupt_meta_removed(self, cfg) -> None:
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        (cfg.cache_dir / "broken.json").write_text("{ not json", encoding="utf-8")
        assert migrate_flat_cache(cfg) == 0
        assert not (cfg.cache_dir / "broken.json").exists()

    def test_missing_cache_dir_is_safe(self, cfg) -> None:
        assert migrate_flat_cache(cfg) == 0
