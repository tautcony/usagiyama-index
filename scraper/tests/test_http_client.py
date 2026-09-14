"""HTTP 客户端测试：缓存、限速、退避、熔断。

用假 session 替换 curl_cffi 的真实 Session，从而在不联网的前提下
验证归档策略本身是否正确。
"""

from __future__ import annotations

import dataclasses

import pytest

from scraper.http_client import (
    BLOCKED_STATUS,
    cache_domain,
    cache_paths,
    migrate_flat_cache,
    cache_domain,
    cache_paths,
    migrate_flat_cache,
    NO_CACHE_STATUS,
    RETRYABLE_STATUS,
    BlockedError,
    CircuitBreakerOpen,
    FetchError,
    Fetcher,
    OfflineCacheMiss,
    decode_html,
)


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
