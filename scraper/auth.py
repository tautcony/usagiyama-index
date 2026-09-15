"""登录会话管理。

**设计原则：工具全程不接触密码。**

``login`` 子命令打开一个有头 Chrome，由用户自己在里面完成登录
（扫码 / 短信 / 账号密码 / 图形验证码都可以），工具只做两件事：

1. 轮询检测登录是否成功
2. 把登录后的会话状态（cookies + localStorage）保存到本地文件

之后抓取时把这个状态注入浏览器上下文即可复用登录态。

**安全处理**：

* 状态文件含敏感 cookie，官方明确「可能被用于冒充你」。
  因此落在 ``scraper/state/douban.auth.json``，权限 ``0600``，且加入 ``.gitignore``。
* 日志里绝不打印 cookie 的值，只用 :func:`redact_state` 输出摘要。
* 状态文件不进 ``data/``、不进 ``manifest.json``、不进 VitePress 产物。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import CONFIG, Config
from .util import atomic_write_text, now_iso, read_json

log = logging.getLogger("usagi.auth")

# 豆瓣登录成功后 ``.douban.com`` 上会同时存在这两个 cookie；``bid``
# 不作判据，因为未登录访问也会下发。
LOGIN_COOKIE_NAMES = ("dbcl2", "ck")

DOUBAN_COOKIE_DOMAIN = ".douban.com"
LOGIN_PAGE_URL = "https://accounts.douban.com/passport/login"
# 未登录访问该页返回 403，登录后返回 200（本机实测）
SESSION_PROBE_URL = "https://www.douban.com/mine/"


@dataclass
class SessionStatus:
    """一次会话检查的结果。"""

    logged_in: bool = False
    detail: str = ""
    cookie_count: int = 0
    state_path: Path | None = None

    @property
    def label(self) -> str:
        return "已登录" if self.logged_in else "未登录"


# ------------------------------------------------------------------ 状态文件


def save_state(path: Path, state: dict[str, Any]) -> None:
    """把 storage_state 原子落盘并设为 0600。

    刻意不直接用 ``context.storage_state(path=...)``——那样用普通 ``open`` 写文件，
    权限受 umask 影响。这里走 :func:`atomic_write_text`（内部用 ``mkstemp``，
    本身就是 0600），再加一次 ``chmod`` 作为双保险。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError as exc:  # pragma: no cover - 非 POSIX 或权限异常
        log.warning("设置会话文件权限失败：%s", exc)


def load_state(path: Path) -> dict[str, Any] | None:
    """读取会话状态；文件缺失或损坏时返回 ``None``。"""
    data = read_json(path, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("cookies"), list):
        return None
    return data


def cookies_from_state(state: dict[str, Any]) -> dict[str, str]:
    """把 storage_state 里的 cookies 摊平成 ``{name: value}``。"""
    result: dict[str, str] = {}
    for cookie in state.get("cookies") or []:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        if name:
            result[name] = value
    return result


def is_logged_in_cookies(cookies: dict[str, str]) -> bool:
    """判断 cookie 集合是否代表已登录。

    判据是 ``dbcl2`` 与 ``ck`` 同时存在且非空。
    """
    return all(cookies.get(name) for name in LOGIN_COOKIE_NAMES)


def redact_state(state: dict[str, Any]) -> dict[str, Any]:
    """生成可安全写入日志的会话摘要——**绝不包含任何 cookie 值**。"""
    cookies = state.get("cookies") or []
    domains = sorted(
        {
            str(cookie.get("domain", ""))
            for cookie in cookies
            if isinstance(cookie, dict) and cookie.get("domain")
        }
    )
    names = sorted(
        {
            str(cookie.get("name", ""))
            for cookie in cookies
            if isinstance(cookie, dict) and cookie.get("name")
        }
    )
    return {
        "cookieCount": len(cookies),
        "cookieNames": names,
        "domains": domains,
        "origins": len(state.get("origins") or []),
    }


# ---------------------------------------------------------------- 会话检查


def _apply_cookies(session: Any, cookies: dict[str, str], domain: str = DOUBAN_COOKIE_DOMAIN) -> int:
    """把 cookie 注入 curl_cffi 会话。返回注入的数量。"""
    applied = 0
    for name, value in cookies.items():
        try:
            session.cookies.set(name, value, domain=domain, path="/")
            applied += 1
        except Exception as exc:  # noqa: BLE001 - 单个 cookie 失败不该中断
            log.debug("注入 cookie %s 失败：%s", name, exc)
    return applied


def check_session(
    cfg: Config = CONFIG,
    *,
    session: Any = None,
    state: dict[str, Any] | None = None,
) -> SessionStatus:
    """校验已保存的会话是否仍然有效。

    用 curl_cffi 带着状态文件里的 cookie 访问 ``/mine/``：
    未登录实测返回 403，登录后返回 200。**不需要启动浏览器**，
    因此可以低成本地在每次同步前跑一次。

    :param session: 注入的 curl_cffi Session（测试用）。
    """
    path = cfg.auth_state_path
    if state is None:
        state = load_state(path)
    if state is None:
        return SessionStatus(logged_in=False, detail="没有找到会话文件，请先执行 login", state_path=path)

    cookies = cookies_from_state(state)
    if not is_logged_in_cookies(cookies):
        missing = [name for name in LOGIN_COOKIE_NAMES if not cookies.get(name)]
        return SessionStatus(
            logged_in=False,
            detail=f"会话文件里缺少登录 cookie：{', '.join(missing)}",
            cookie_count=len(cookies),
            state_path=path,
        )

    owns_session = session is None
    if session is None:
        from curl_cffi.requests import Session

        session = Session(impersonate=cfg.impersonate, timeout=cfg.timeout)
        session.trust_env = True

    try:
        _apply_cookies(session, cookies)
        response = session.get(SESSION_PROBE_URL, allow_redirects=True)
        status = response.status_code
        final_url = str(getattr(response, "url", "") or "")
        if status == 200:
            # 未登录可能 302 到同样返回 200 的登录页，因此还要确认最终落点
            # 不在 accounts.douban.com，避免使用失效 cookie 继续抓取。
            if LOGIN_PAGE_URL in final_url or "accounts.douban.com" in final_url:
                return SessionStatus(
                    logged_in=False,
                    detail=f"会话已失效，被重定向到登录页（{final_url}）",
                    cookie_count=len(cookies),
                    state_path=path,
                )
            return SessionStatus(
                logged_in=True,
                detail=f"会话有效（{SESSION_PROBE_URL} → 200）",
                cookie_count=len(cookies),
                state_path=path,
            )
        return SessionStatus(
            logged_in=False,
            detail=f"会话可能已失效（{SESSION_PROBE_URL} → {status} {final_url}）",
            cookie_count=len(cookies),
            state_path=path,
        )
    except Exception as exc:  # noqa: BLE001 - 网络异常不该让检查本身崩掉
        return SessionStatus(
            logged_in=False,
            detail=f"校验会话时出错：{type(exc).__name__}: {exc}",
            cookie_count=len(cookies),
            state_path=path,
        )
    finally:
        if owns_session:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------ 浏览器侧检测


def cookies_from_context(context: Any) -> dict[str, str]:
    """从 Playwright BrowserContext 读取 douban 相关 cookie。"""
    result: dict[str, str] = {}
    try:
        raw = context.cookies()
    except Exception:  # noqa: BLE001
        return result
    for cookie in raw or []:
        name = str(cookie.get("name", ""))
        if name in LOGIN_COOKIE_NAMES:
            result[name] = str(cookie.get("value", ""))
    return result


def wait_for_login(
    context: Any,
    *,
    timeout: float = 300.0,
    poll_interval: float = 2.0,
    sleep: Any = None,
    on_tick: Any = None,
) -> bool:
    """轮询等待用户完成登录。返回是否成功。

    :param on_tick: 每轮回调一次，参数为已等待秒数（用于打印进度）。
    """
    import time as _time

    sleep_fn = sleep or _time.sleep
    started = _time.monotonic()
    deadline = started + timeout
    while _time.monotonic() < deadline:
        if is_logged_in_cookies(cookies_from_context(context)):
            return True
        if on_tick is not None:
            on_tick(_time.monotonic() - started)
        sleep_fn(poll_interval)
    return False


def run_login_flow(
    cfg: Config = CONFIG,
    *,
    timeout: float | None = None,
    headless: bool = False,
    on_tick: Any = None,
) -> tuple[bool, str]:
    """打开有头浏览器，让用户完成登录，然后保存会话状态。

    **工具全程不接触密码**：只打开登录页，由用户自己完成扫码 / 短信 /
    账号密码 / 图形验证码，工具只负责检测登录成功并保存会话。

    :returns: ``(是否成功, 说明文本)``
    """
    from playwright.sync_api import sync_playwright

    limit = cfg.browser_login_timeout if timeout is None else timeout

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel=cfg.browser_channel,
            headless=headless,
            args=["--no-first-run", "--no-default-browser-check"],
        )
        try:
            # 不覆盖 UA：有头模式本来就发真实的 Chrome UA。
            # 也不 block service_workers —— 那是配合路由拦截才需要的，
            # 这里既然不拦截，就没必要引入与真实浏览器不一致的行为。
            context = browser.new_context(
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1280, "height": 900},
            )
            # 这里**刻意不注册任何路由拦截**。
            #
            # 抓取时那套"拦图片/字体/统计"的策略绝不能用在这里：豆瓣的风控验证码
            # （turing.captcha.qcloud.com 的滑块拼图）本身就是图片资源，拦掉之后
            # 验证码永远渲染不出来，用户根本无法登录 —— 浏览器只会报
            # net::ERR_BLOCKED_BY_CLIENT。
            #
            # 而且这是个交互式会话：用户就坐在屏幕前，省那点流量毫无意义，
            # 正确性远比带宽重要。保持网络原样反而更接近真实浏览器。
            page = context.new_page()
            page.goto(
                LOGIN_PAGE_URL,
                wait_until="domcontentloaded",
                timeout=cfg.browser_nav_timeout_ms,
            )

            if not wait_for_login(context, timeout=limit, on_tick=on_tick):
                return False, f"等待 {int(limit)} 秒仍未检测到登录成功"

            state = context.storage_state()
            save_state(cfg.auth_state_path, state)
            return True, state_summary_for_log(state)
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


def state_summary_for_log(state: dict[str, Any]) -> str:
    """一行可安全打印的会话摘要。"""
    summary = redact_state(state)
    return (
        f"{summary['cookieCount']} 个 cookie"
        f"（域：{', '.join(summary['domains']) or '-'}）"
        f" · 关键 cookie：{', '.join(n for n in LOGIN_COOKIE_NAMES if n in summary['cookieNames']) or '无'}"
    )
