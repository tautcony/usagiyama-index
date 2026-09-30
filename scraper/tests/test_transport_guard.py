"""The global offline fixture must catch direct transport construction paths."""

from __future__ import annotations

import pytest

from scraper import auth, browser


def test_auth_check_session_does_not_swallow_transport_guard(cfg) -> None:
    state = {"cookies": [
        {"name": "dbcl2", "value": "x"},
        {"name": "ck", "value": "y"},
    ]}
    with pytest.raises(AssertionError, match="真实请求"):
        auth.check_session(cfg, state=state)


def test_chrome_probe_does_not_swallow_browser_guard(cfg) -> None:
    pytest.importorskip("playwright.sync_api")
    with pytest.raises(AssertionError, match="真实浏览器"):
        browser.detect_chrome_ua(cfg, refresh=True)
