"""测试夹具。

**默认零网络、零浏览器。**

这个保证不是靠"记得注入 fake"的约定，而是由 :func:`forbid_real_transport` 强制：
任何未标记的测试只要试图创建真实的 curl_cffi Session 或启动 Playwright，
就会立刻失败并提示正确的做法。

需要真实联网的测试必须显式标记：

* ``@pytest.mark.network`` —— 会发起真实 HTTP 请求
* ``@pytest.mark.browser`` —— 需要真实浏览器（隐含联网）

两者都被 ``addopts`` 默认排除，要用 ``-m network`` / ``-m browser`` 显式启用。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from scraper.config import CONFIG, Config

#: 需要真实网络 / 浏览器的标记，二者都默认排除
REAL_WORLD_MARKERS = ("network", "browser")


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    """全部路径指向 tmp_path 的隔离配置。

    另外把延时归零，避免测试里真的 sleep。
    """
    root = tmp_path
    return dataclasses.replace(
        CONFIG,
        root=root,
        cache_dir=root / "state" / "cache",
        state_dir=root / "state",
        data_dir=root / "data",
        docs_dir=root / "docs",
        media_dir=root / "docs" / "public" / "media",
        fixtures_dir=Path(__file__).parent / "fixtures",
        archive_enabled=False,
        browser_enabled=False,
        delay_min=0.0,
        delay_max=0.0,
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def forbid_real_transport(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """未标记的测试禁止触碰真实网络与真实浏览器。

    为什么拦在"创建 session / 启动 driver"这一层，而不是拦 socket：
    curl_cffi 走的是 libcurl（C 层），Playwright 走的是独立子进程，
    两者都**绕过 Python 的 socket 模块**，拦 socket 会给出虚假的安全感。
    拦在构造点才能真正覆盖到所有真实传输路径。
    """
    if any(request.node.get_closest_marker(marker) for marker in REAL_WORLD_MARKERS):
        return

    from scraper import browser as browser_module
    from scraper import http_client as http_module

    class _OfflineSession:
        """占位会话：**允许构造，但任何请求都失败**。

        这样"只是构造 SyncContext 而不发请求"的测试可以正常跑，
        而真的想联网的测试会立刻失败并提示正确做法。
        """

        def __init__(self) -> None:
            self.headers: dict[str, str] = {}
            self.trust_env = False

        def get(self, url: str, **_kwargs: object) -> None:
            raise AssertionError(
                f"未标记的测试尝试发起真实请求：{url}\n"
                "  请注入 FakeSession（见 test_http_client.py），"
                "或给测试加 @pytest.mark.network。"
            )

        def close(self) -> None:
            pass

    def _offline_session(*_args: object, **_kwargs: object) -> _OfflineSession:
        return _OfflineSession()

    def _forbidden_driver(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "测试试图启动真实浏览器。\n"
            "  请注入 FakeDriver（见 tests/fakes.py），"
            "或给测试加 @pytest.mark.browser。"
        )

    monkeypatch.setattr(http_module.Fetcher, "_build_session", _offline_session)
    monkeypatch.setattr(browser_module.PlaywrightDriver, "__init__", _forbidden_driver)


@pytest.fixture(autouse=True)
def forbid_archive_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """未标记的测试禁止真的去查 archive.org。"""
    if any(request.node.get_closest_marker(marker) for marker in REAL_WORLD_MARKERS):
        return

    from scraper import archive as archive_module

    def _forbidden_cdx(*_args: object, **_kwargs: object) -> list:
        raise AssertionError(
            "测试试图查询 archive.org。请注入 fetcher，或加 @pytest.mark.network。"
        )

    monkeypatch.setattr(archive_module.WaybackClient, "cdx_search", _forbidden_cdx)
