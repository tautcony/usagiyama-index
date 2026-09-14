"""浏览器传输层：Playwright 驱动系统 Chrome。

目标站点有反爬措施（TLS 指纹校验、部分页面需登录、可能触发人机校验），
纯 HTTP 拿不到全部内容，因此提供一条浏览器通路。

**与 HTTP 后端的关系**：``BrowserFetcher`` 继承 :class:`~scraper.http_client.BaseFetcher`，
因此**复用同一套**磁盘缓存、礼貌限速、退避重试、熔断与统计。浏览器抓到的 HTML
与 curl 抓到的图片落在同一个 ``cache/<域名>/`` 下，增量同步、断点续接、
``--offline``、``emit`` 全部自动生效。

**几个刻意的设计选择**：

1. **懒启动**：``PlaywrightDriver`` 只在首次真正联网时才创建。
   缓存命中 / 离线模式 / ``emit`` 子命令**绝不拉起 Chrome**。
2. **图片仍走 curl_cffi**：图片是公开 CDN，不需要登录态；而 ``media.py`` 的
   尺寸升级、magic bytes 校验、archive.org 兜底整条链路都建在
   ``get_image() -> CachedResponse`` 上，换传输会牵动业务逻辑。
   798 张图片若走 ``page.goto`` 还会渲染页面，成本极高。
3. **用系统 Chrome**（``channel="chrome"``）：无需 ``playwright install`` 下载浏览器，
   且真实 Chrome 构建比自带 Chromium 更接近普通用户环境。
   Playwright 每次 launch 使用**临时 user-data-dir**，不会争抢用户 Chrome 的
   profile 锁，也读不到用户的 cookie 与密码。
4. **风控即停，不自动过验证码**：检测到 ``sec.douban.com`` 人机校验就计入熔断并停止，
   提示用户重新登录，而不是尝试绕过。

**关于自动化特征的处理边界**（与项目"不规避风控"的原则一致）：

* **做**：把无头启动产生的 ``HeadlessChrome`` 改回 ``Chrome``。这只是我们选了
  无头启动的副作用，同一个 Chrome 有头时发的就是 ``Chrome``，并不代表换了客户端。
  版本号取浏览器自己的真实值，不伪造。
* **不做**：不修改 ``navigator.webdriver``（那是真正的自动化标记），
  不轮换 UA，不轮换代理，不做指纹伪装。
  降低风险靠的是真 Chrome + 真人登录 + 5~7 秒间隔 + 单线程 + 熔断即停。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Protocol, runtime_checkable
from urllib.parse import urlparse

from .config import CONFIG, Config
from .http_client import (
    BLOCKED_STATUS,
    RETRYABLE_STATUS,
    BaseFetcher,
    BlockedError,
    Fetcher,
    FetchError,
    FetchStats,
    RateLimiter,
    RawResponse,
    _RetryableStatus,
)
from .util import atomic_write_text, host_matches

log = logging.getLogger("usagi.browser")

# 触发人机校验时豆瓣会把页面 302 到这里。这是最可靠的判据——
# 该页面本身是 JS 渲染的，取回为空，不要去解析它的 HTML。
CHALLENGE_HOST = "sec.douban.com"

# 这些资源类型一律拦截：图片另有下载通道，视频只存缩略图，字体纯排版。
# 注意不要拦 stylesheet —— 元素"不可见"会干扰后续的可见性判断，且 CSS 体积很小。
#
# **仅用于抓取**。登录流程绝不能套这套策略：豆瓣的风控验证码
# （turing.captcha.qcloud.com 的滑块拼图）本身就是图片资源，
# 拦掉之后验证码渲染不出来，用户根本无法登录，浏览器只会报
# net::ERR_BLOCKED_BY_CLIENT。见 :func:`scraper.auth.run_login_flow`。
BLOCKED_RESOURCE_TYPES = frozenset({"image", "media", "font"})

# 统计/广告域名，拦掉能减流量也减特征。
BLOCKED_HOSTS: tuple[str, ...] = (
    "hm.baidu.com",
    "google-analytics.com",
    "googletagmanager.com",
    "googlesyndication.com",
    "doubleclick.net",
    "cnzz.com",
    "umeng.com",
    "umengcloud.com",
    "ads.douban.com",
)

# playwright 的异常类型。延迟导入，使得未安装 playwright 时本模块仍可导入
# （测试环境可能没装；纯离线测试也不该依赖它）。
try:  # pragma: no cover - 取决于环境是否安装 playwright
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    PLAYWRIGHT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
        PlaywrightTimeoutError,
        PlaywrightError,
    )
except ImportError:  # pragma: no cover
    PLAYWRIGHT_RETRYABLE_EXCEPTIONS = ()


def is_challenge_url(url: str) -> bool:
    """判断 URL 是否指向人机校验页。"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host == CHALLENGE_HOST


class ChallengeError(BlockedError):
    """触发了人机校验（被 302 到 ``sec.douban.com``）。

    继承 :class:`~scraper.http_client.BlockedError`，因此现有的
    ``PageResolver`` 与熔断机制**无需改动**即可接管：
    先尝试 archive.org 补足，失败则标记为 ``LOGIN_REQUIRED``；
    连续触发达到阈值即熔断停止。
    """

    def __init__(self, url: str, final_url: str) -> None:
        super().__init__(url, f"触发人机校验，被重定向到 {final_url}", 403)
        self.final_url = final_url


def make_route_handler() -> Callable[[Any], None]:
    """构造 Playwright 的路由拦截回调。

    **只给抓取用**，不要用在登录流程 —— 它会拦掉所有图片，
    而风控验证码本身就是图片（详见 ``BLOCKED_RESOURCE_TYPES`` 的说明）。

    注意：注册路由后**每个**匹配的请求都必须显式 ``continue_()`` 或 ``abort()``，
    否则请求会永久挂起。回调内部抛异常也会导致挂起，因此这里兜底放行。
    """

    def handler(route: Any) -> None:
        try:
            request = route.request
            host = (urlparse(request.url).hostname or "").lower()
            if request.resource_type in BLOCKED_RESOURCE_TYPES or host_matches(
                host, BLOCKED_HOSTS
            ):
                route.abort("blockedbyclient")
            else:
                route.continue_()
        except Exception:  # noqa: BLE001 - 路由回调绝不能抛，否则请求挂死
            try:
                route.continue_()
            except Exception:  # noqa: BLE001
                pass

    return handler


# ------------------------------------------------------------------- 驱动协议


@runtime_checkable
class BrowserDriver(Protocol):
    """浏览器驱动接口。

    抽出来的目的是让 :class:`BrowserFetcher` 可以在**不启动真实浏览器**的情况下
    被测试——注入一个 ``FakeDriver`` 即可覆盖全部缓存/熔断/风控分支。
    """

    def navigate(
        self, url: str, *, referer: str | None = None, timeout: int | None = None
    ) -> RawResponse:
        """导航到 URL 并返回渲染后的 HTML。"""
        ...

    def close(self) -> None:
        """释放浏览器资源（幂等）。"""
        ...


# ------------------------------------------------------------- Playwright 实现


class PlaywrightDriver:
    """用 Playwright 驱动系统 Chrome。

    整个运行期只创建一次 browser / context / page 并复用——
    Playwright 的每次 ``start()`` 都会拉起一个 Node 子进程，成本很高。
    """

    def __init__(
        self,
        cfg: Config = CONFIG,
        *,
        channel: str | None = None,
        headless: bool | None = None,
        user_agent: str | None = None,
        state_path: Any = None,
    ) -> None:
        from playwright.sync_api import sync_playwright

        self.cfg = cfg
        self.channel = channel or cfg.browser_channel
        self.headless = cfg.browser_headless if headless is None else headless
        self._nav_count = 0
        self._crashed = False
        self._closed = False

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(
                channel=self.channel,
                headless=self.headless,
                args=["--no-first-run", "--no-default-browser-check"],
            )
            resolved_ua = user_agent or self._resolve_user_agent()

            # service_workers="block" 是路由拦截生效的前提：
            # Service Worker 发出的请求不会被 context.route() 截获。
            # locale 会同时影响 navigator.language 与 Accept-Language，无需再手工设头。
            self._context = self._browser.new_context(
                user_agent=resolved_ua,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1280, "height": 800},
                service_workers="block",
                storage_state=state_path if state_path else None,
            )
            self._context.route("**/*", make_route_handler())
            self._page = self._context.new_page()
            # 页面弹窗（alert/confirm）会阻塞导航，一律关闭
            self._page.on("dialog", lambda dialog: dialog.dismiss())
            self._page.on("crash", self._on_crash)
        except Exception:
            # 启动失败时必须停掉 driver，否则会留下孤儿 Node 进程
            self.close()
            raise

        log.info(
            "浏览器已启动：%s %s（UA=%s）",
            self.channel,
            "无头" if self.headless else "有头",
            resolved_ua,
        )

    # ------------------------------------------------------------ UA 处理

    def _resolve_user_agent(self) -> str:
        """确定要使用的 User-Agent。

        无头启动会让 Chrome 在 UA 里带上 ``HeadlessChrome``，而有头时同一个 Chrome
        发的是 ``Chrome``。这里把它改回来——版本号用浏览器自己的真实值，不伪造。
        可以用 ``browser_normalize_headless_ua=False`` 关闭该行为。
        """
        probe = self._browser.new_context()
        try:
            page = probe.new_page()
            raw: str = page.evaluate("navigator.userAgent")
        finally:
            probe.close()

        if self.cfg.browser_normalize_headless_ua and "HeadlessChrome" in raw:
            return raw.replace("HeadlessChrome", "Chrome")
        return raw

    # ------------------------------------------------------------ 页面生命周期

    def _on_crash(self, _page: Any) -> None:
        self._crashed = True
        log.warning("浏览器页面崩溃，将在下次导航前重建")

    def _recreate_page(self) -> None:
        try:
            self._page.close()
        except Exception:  # noqa: BLE001 - 已崩溃的 page 关闭会抛错，忽略
            pass
        self._page = self._context.new_page()
        self._page.on("dialog", lambda dialog: dialog.dismiss())
        self._page.on("crash", self._on_crash)
        self._crashed = False
        self._nav_count = 0

    def _maybe_recycle(self) -> None:
        """长时间运行后重建 page，防止内存持续增长。"""
        every = self.cfg.browser_page_recycle
        if self._crashed or (every and self._nav_count >= every):
            self._recreate_page()

    # ---------------------------------------------------------------- 导航

    def navigate(
        self, url: str, *, referer: str | None = None, timeout: int | None = None
    ) -> RawResponse:
        """导航到 URL 并返回渲染后的 HTML。

        用 ``domcontentloaded`` 而不是 ``networkidle``：豆瓣正文与评论在服务端就
        渲染进 DOM，DOMContentLoaded 后 ``page.content()`` 即完整；而
        ``networkidle`` 官方标注 DISCOURAGED，遇到长轮询还可能永不 idle。
        """
        self._maybe_recycle()
        self._nav_count += 1

        options: dict[str, Any] = {
            "wait_until": "domcontentloaded",
            "timeout": timeout or self.cfg.browser_nav_timeout_ms,
        }
        if referer:
            options["referer"] = referer

        response = self._page.goto(url, **options)
        status = response.status if response is not None else 0
        html = self._page.content()
        return RawResponse(
            status=status,
            content=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            final_url=self._page.url,
        )

    # ---------------------------------------------------------------- 收尾

    def close(self) -> None:
        """按 page → context → browser → driver 的顺序释放，每步独立兜底。"""
        if self._closed:
            return
        self._closed = True
        for name in ("_page", "_context", "_browser"):
            resource = getattr(self, name, None)
            if resource is None:
                continue
            try:
                resource.close()
            except Exception as exc:  # noqa: BLE001 - 关闭失败无关紧要
                log.debug("关闭 %s 失败：%s", name, exc)
        driver = getattr(self, "_pw", None)
        if driver is not None:
            try:
                driver.stop()
            except Exception as exc:  # noqa: BLE001
                log.debug("停止 Playwright 失败：%s", exc)


# ------------------------------------------------------------------ 浏览器后端


class BrowserFetcher(BaseFetcher):
    """基于 Playwright 的抓取器。

    页面请求走浏览器；图片请求委托给内部的 curl_cffi ``Fetcher``
    （原因见模块文档）。两者**共享同一个 RateLimiter**，因此整体请求速率仍然受控。
    """

    def __init__(
        self,
        cfg: Config = CONFIG,
        *,
        offline: bool | None = None,
        driver: BrowserDriver | None = None,
        sleep: Callable[[float], None] = time.sleep,
        limiter: RateLimiter | None = None,
        channel: str | None = None,
        headless: bool | None = None,
        image_fetcher: BaseFetcher | None = None,
    ) -> None:
        super().__init__(cfg, offline=offline, sleep=sleep, limiter=limiter)
        self.retryable_exceptions = PLAYWRIGHT_RETRYABLE_EXCEPTIONS
        self._driver = driver
        self._channel = channel or cfg.browser_channel
        self._headless = cfg.browser_headless if headless is None else headless
        # 图片走 curl_cffi，共享限速器
        self._image_fetcher = image_fetcher or Fetcher(cfg, sleep=sleep, limiter=self._limiter)
        #: 本次运行是否检测到人机校验（供 CLI 给出"重新登录"提示）
        self.session_expired = False
        self.stats.impersonate = f"browser:{self._channel}"

    # ---------------------------------------------------------------- 驱动

    def _ensure_driver(self) -> BrowserDriver:
        """懒启动：只有真正要联网时才创建浏览器。

        这让缓存命中、``--offline``、``emit`` 等场景完全不启动 Chrome。
        """
        if self._driver is None:
            state_path = self.cfg.auth_state_path
            self._driver = PlaywrightDriver(
                self.cfg,
                channel=self._channel,
                headless=self._headless,
                state_path=state_path if state_path.exists() else None,
            )
        return self._driver

    # ---------------------------------------------------------------- 抓取

    def _attempt(self, url: str, referer: str | None) -> RawResponse:
        driver = self._ensure_driver()

        self._limiter.wait()
        self._limiter.mark()
        self.stats.requests += 1

        raw = driver.navigate(
            url, referer=referer, timeout=self.cfg.browser_nav_timeout_ms
        )
        self.stats.record_status(raw.status)

        if raw.status in RETRYABLE_STATUS:
            raise _RetryableStatus(raw.status, url)
        return raw

    def _classify_blocked(self, raw: RawResponse, url: str) -> BlockedError | None:
        """把人机校验也认定为"被拦截"，从而接入现有的熔断与标记机制。"""
        if is_challenge_url(raw.final_url):
            self.session_expired = True
            return ChallengeError(url, raw.final_url)
        return super()._classify_blocked(raw, url)

    # ---------------------------------------------------------------- 图片

    def get_image(self, url: str, *, force: bool = False):
        """图片仍走 curl_cffi（公开 CDN，不需要登录态）。"""
        return self._image_fetcher.get_image(url, force=force)

    def cache_has(self, url: str) -> bool:
        return super().cache_has(url)

    # ---------------------------------------------------------------- 收尾

    def close(self) -> None:
        """释放图片 fetcher 与浏览器。

        driver 无论由谁创建都在这里关闭——``close()`` 的语义是
        「释放本 fetcher 使用的全部资源」。``PlaywrightDriver.close()``
        本身幂等，重复调用安全。测试注入的 FakeDriver 也因此能被验证。
        """
        try:
            self._image_fetcher.close()
        except Exception:  # noqa: BLE001
            pass
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def finalize(self) -> FetchStats:
        """把内部 curl 图片请求的统计并入，保证同步报告数字完整。"""
        stats = super().finalize()
        stats.merge(self._image_fetcher.stats)
        return stats


# ---------------------------------------------------------------------- 辅助


def detect_chrome_ua(cfg: Config = CONFIG, *, refresh: bool = False) -> str:
    """探测系统 Chrome 的真实 User-Agent，结果缓存到 ``state/chrome_ua.txt``。

    用于在报告里展示实际使用的浏览器版本。缓存是为了避免每次运行都开一次浏览器。
    探测失败时回退到配置里的 ``user_agent``。
    """
    cache = cfg.chrome_ua_cache_path
    if not refresh and cache.exists():
        try:
            cached = cache.read_text(encoding="utf-8").strip()
            if cached:
                return cached
        except OSError:
            pass

    ua = ""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=cfg.browser_channel, headless=True)
            try:
                page = browser.new_page()
                ua = str(page.evaluate("navigator.userAgent"))
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - 探测失败不该影响主流程
        log.warning("探测 Chrome UA 失败（%s），回退到配置值", exc)
        return cfg.user_agent

    if ua:
        try:
            atomic_write_text(cache, ua + "\n")
        except OSError:
            pass
    return ua or cfg.user_agent
