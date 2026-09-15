"""登录会话管理测试（不启动浏览器、不联网）。"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from scraper import auth
from scraper.auth import (
    LOGIN_COOKIE_NAMES,
    cookies_from_context,
    cookies_from_state,
    is_logged_in_cookies,
    load_state,
    redact_state,
    save_state,
    wait_for_login,
)

SECRET = "THIS_MUST_NEVER_APPEAR_IN_LOGS"


def _state(**overrides) -> dict:
    cookies = [
        {"name": "dbcl2", "value": SECRET, "domain": ".douban.com", "path": "/"},
        {"name": "ck", "value": SECRET, "domain": ".douban.com", "path": "/"},
        {"name": "bid", "value": "abc", "domain": ".douban.com", "path": "/"},
    ]
    base = {"cookies": cookies, "origins": [{"origin": "https://www.douban.com", "localStorage": []}]}
    base.update(overrides)
    return base


class TestSaveAndLoad:
    def test_round_trip(self, cfg) -> None:
        save_state(cfg.auth_state_path, _state())
        loaded = load_state(cfg.auth_state_path)
        assert loaded is not None
        assert len(loaded["cookies"]) == 3

    def test_file_permission_is_0600(self, cfg) -> None:
        """会话文件含敏感 cookie，权限必须是 0600。"""
        save_state(cfg.auth_state_path, _state())
        mode = cfg.auth_state_path.stat().st_mode & 0o777
        assert mode == 0o600, f"期望 0o600，实际 {oct(mode)}"

    def test_missing_file_returns_none(self, cfg) -> None:
        assert load_state(cfg.auth_state_path) is None

    def test_corrupt_file_returns_none(self, cfg) -> None:
        cfg.auth_state_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.auth_state_path.write_text("{ not json", encoding="utf-8")
        assert load_state(cfg.auth_state_path) is None

    def test_missing_cookies_key_returns_none(self, cfg) -> None:
        save_state(cfg.auth_state_path, {"origins": []})
        assert load_state(cfg.auth_state_path) is None


class TestRedaction:
    def test_never_leaks_cookie_values(self) -> None:
        summary = redact_state(_state())
        blob = json.dumps(summary, ensure_ascii=False)
        assert SECRET not in blob
        assert "abc" not in blob  # bid 的值也不能出现

    def test_reports_counts_and_names(self) -> None:
        summary = redact_state(_state())
        assert summary["cookieCount"] == 3
        assert summary["domains"] == [".douban.com"]
        assert "dbcl2" in summary["cookieNames"]

    def test_handles_empty(self) -> None:
        assert redact_state({})["cookieCount"] == 0

    def test_handles_malformed_cookies(self) -> None:
        summary = redact_state({"cookies": ["not-a-dict", {"name": "x"}]})
        assert summary["cookieCount"] == 2


class TestLoginDetection:
    def test_dbcl2_and_ck_means_logged_in(self) -> None:
        assert is_logged_in_cookies({"dbcl2": "v", "ck": "v"}) is True

    def test_bid_alone_is_not_enough(self) -> None:
        """bid 未登录也会下发，不能作为判据。"""
        assert is_logged_in_cookies({"bid": "v"}) is False

    def test_missing_ck_is_not_logged_in(self) -> None:
        assert is_logged_in_cookies({"dbcl2": "v"}) is False

    def test_empty_values_are_not_logged_in(self) -> None:
        assert is_logged_in_cookies({"dbcl2": "", "ck": ""}) is False

    def test_cookies_from_state(self) -> None:
        cookies = cookies_from_state(_state())
        assert set(LOGIN_COOKIE_NAMES) <= set(cookies)

    def test_cookies_from_context_filters(self) -> None:
        class FakeContext:
            def cookies(self):
                return [
                    {"name": "dbcl2", "value": "v"},
                    {"name": "ck", "value": "v"},
                    {"name": "unrelated", "value": "v"},
                ]

        assert cookies_from_context(FakeContext()) == {"dbcl2": "v", "ck": "v"}

    def test_cookies_from_context_survives_error(self) -> None:
        class BrokenContext:
            def cookies(self):
                raise RuntimeError("boom")

        assert cookies_from_context(BrokenContext()) == {}


class TestWaitForLogin:
    def test_returns_true_once_cookies_appear(self) -> None:
        class Context:
            def __init__(self) -> None:
                self.calls = 0

            def cookies(self):
                self.calls += 1
                if self.calls >= 3:
                    return [{"name": "dbcl2", "value": "v"}, {"name": "ck", "value": "v"}]
                return []

        slept: list[float] = []
        assert wait_for_login(Context(), timeout=10, poll_interval=0.01, sleep=slept.append) is True
        assert len(slept) == 2

    def test_returns_false_on_timeout(self) -> None:
        class Context:
            def cookies(self):
                return []

        assert wait_for_login(Context(), timeout=0.05, poll_interval=0.01, sleep=lambda _s: None) is False

    def test_on_tick_called(self) -> None:
        ticks: list[float] = []

        class Context:
            def cookies(self):
                return []

        wait_for_login(
            Context(), timeout=0.05, poll_interval=0.01,
            sleep=lambda _s: None, on_tick=ticks.append,
        )
        assert ticks


class TestCheckSession:
    def test_missing_state_reports_not_logged_in(self, cfg) -> None:
        status = auth.check_session(cfg)
        assert status.logged_in is False
        assert "login" in status.detail

    def test_state_without_login_cookies(self, cfg) -> None:
        save_state(cfg.auth_state_path, {"cookies": [{"name": "bid", "value": "x"}], "origins": []})
        status = auth.check_session(cfg)
        assert status.logged_in is False
        assert "dbcl2" in status.detail

    def test_probe_200_means_valid(self, cfg) -> None:
        save_state(cfg.auth_state_path, _state())

        class FakeSession:
            def __init__(self) -> None:
                self.cookies = _FakeCookies()

            def get(self, url, **kwargs):
                return type("R", (), {"status_code": 200, "url": url})()

        status = auth.check_session(cfg, session=FakeSession())
        assert status.logged_in is True

    def test_probe_200_but_redirected_to_login_is_expired(self, cfg) -> None:
        """WARN-7：allow_redirects=True 下，未登录可能被 302 到登录页（仍返回 200）。

        不能因此误判为已登录。
        """
        save_state(cfg.auth_state_path, _state())

        class FakeSession:
            def __init__(self) -> None:
                self.cookies = _FakeCookies()

            def get(self, url, **kwargs):
                return type(
                    "R",
                    (),
                    {
                        "status_code": 200,
                        "url": "https://accounts.douban.com/passport/login",
                    },
                )()

        status = auth.check_session(cfg, session=FakeSession())
        assert status.logged_in is False
        assert "登录" in status.detail

    def test_probe_403_means_expired(self, cfg) -> None:
        save_state(cfg.auth_state_path, _state())

        class FakeSession:
            def __init__(self) -> None:
                self.cookies = _FakeCookies()

            def get(self, url, **kwargs):
                return type("R", (), {"status_code": 403, "url": url})()

        status = auth.check_session(cfg, session=FakeSession())
        assert status.logged_in is False
        assert "403" in status.detail

    def test_network_error_is_reported_not_raised(self, cfg) -> None:
        save_state(cfg.auth_state_path, _state())

        class BrokenSession:
            def __init__(self) -> None:
                self.cookies = _FakeCookies()

            def get(self, url, **kwargs):
                raise OSError("network down")

        status = auth.check_session(cfg, session=BrokenSession())
        assert status.logged_in is False
        assert "OSError" in status.detail


class _FakeCookies:
    def set(self, *args, **kwargs) -> None:
        pass


class _FakePage:
    def __init__(self, log: list) -> None:
        self.log = log

    def goto(self, url: str, **kwargs) -> None:
        self.log.append(("goto", url))


class _FakeContext:
    """记录 ``route`` 调用，用来证明登录流程没有注册任何路由拦截。"""

    def __init__(self, log: list) -> None:
        self.log = log

    def route(self, pattern, handler) -> None:
        self.log.append(("route", pattern))

    def new_page(self) -> _FakePage:
        self.log.append(("new_page", None))
        return _FakePage(self.log)

    def cookies(self) -> list:
        return [
            {"name": "dbcl2", "value": "x", "domain": ".douban.com"},
            {"name": "ck", "value": "y", "domain": ".douban.com"},
        ]

    def storage_state(self) -> dict:
        return {"cookies": self.cookies(), "origins": []}


class _FakeBrowser:
    def __init__(self, log: list) -> None:
        self.log = log

    def new_context(self, **kwargs) -> _FakeContext:
        self.log.append(("new_context", kwargs))
        return _FakeContext(self.log)

    def close(self) -> None:
        self.log.append(("close", None))


class _FakeChromium:
    def __init__(self, log: list) -> None:
        self.log = log

    def launch(self, **kwargs) -> _FakeBrowser:
        self.log.append(("launch", kwargs))
        return _FakeBrowser(self.log)


class _FakePlaywright:
    def __init__(self, log: list) -> None:
        self.chromium = _FakeChromium(log)


class _FakeSyncPlaywright:
    def __init__(self, log: list) -> None:
        self.log = log

    def __enter__(self) -> _FakePlaywright:
        return _FakePlaywright(self.log)

    def __exit__(self, *exc) -> bool:
        return False


class TestLoginFlowDoesNotBlockResources:
    """登录流程绝不能注册路由拦截。

    历史缺陷：登录流程复用了抓取用的 ``make_route_handler()``，
    它会 ``abort("blockedbyclient")`` 掉所有 ``image`` 请求。而豆瓣的
    风控验证码（``turing.captcha.qcloud.com`` 的滑块拼图）正是图片资源，
    于是验证码永远渲染不出来、用户根本无法登录，浏览器只报
    ``net::ERR_BLOCKED_BY_CLIENT``。
    """

    def _run(self, monkeypatch, cfg, log: list) -> tuple[bool, str]:
        import playwright.sync_api

        monkeypatch.setattr(
            playwright.sync_api, "sync_playwright", lambda: _FakeSyncPlaywright(log)
        )
        return auth.run_login_flow(cfg, timeout=5.0, headless=False)

    def test_no_route_registered(self, monkeypatch, cfg) -> None:
        log: list = []
        ok, _detail = self._run(monkeypatch, cfg, log)

        assert ok
        routes = [entry for entry in log if entry[0] == "route"]
        assert routes == [], f"登录流程不应注册路由拦截，实际注册了：{routes}"

    def test_image_requests_are_not_blocked(self, monkeypatch, cfg) -> None:
        """直接针对报错场景：验证码图片请求必须被放行。"""
        log: list = []
        self._run(monkeypatch, cfg, log)

        registered = [handler for kind, handler in log if kind == "route"]
        assert not registered, "没有任何拦截器，验证码图片自然能加载"

    def test_session_is_saved(self, monkeypatch, cfg) -> None:
        log: list = []
        ok, _detail = self._run(monkeypatch, cfg, log)

        assert ok
        state = load_state(cfg.auth_state_path)
        assert state is not None
        assert is_logged_in_cookies(cookies_from_state(state))

    def test_headless_is_forwarded(self, monkeypatch, cfg) -> None:
        """抓取时无头，登录必须有头 —— 用户要能看见并操作窗口。"""
        log: list = []
        self._run(monkeypatch, cfg, log)
        launch = next(kwargs for kind, kwargs in log if kind == "launch")
        assert launch["headless"] is False

    def test_context_is_created_without_ua_override(self, monkeypatch, cfg) -> None:
        """有头模式本来就发真实 Chrome UA，不要覆盖成 HTTP 层那个写死的 UA。"""
        log: list = []
        self._run(monkeypatch, cfg, log)
        kwargs = next(kwargs for kind, kwargs in log if kind == "new_context")
        assert "user_agent" not in kwargs

    def test_service_workers_not_blocked(self, monkeypatch, cfg) -> None:
        """block service_workers 是配合路由拦截才需要的，登录流程不该引入。

        既然这里不做任何拦截，就没必要让页面行为偏离真实浏览器。
        """
        log: list = []
        self._run(monkeypatch, cfg, log)
        kwargs = next(kwargs for kind, kwargs in log if kind == "new_context")
        assert kwargs.get("service_workers") != "block"
