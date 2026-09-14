"""全局配置：站点常量、抓取礼貌参数、路径布局。

所有可调参数集中在此，便于长期维护时调整（例如切换相册图片尺寸）。
支持通过环境变量覆盖，方便在不同网络环境下复用同一套代码。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 浏览器 UA。豆瓣服务端要求浏览器 UA 才会返回正常页面，
# 但本工具**不会**轮换 UA —— 这是"能访问"的最低要求，不是规避手段。
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


#: robots.txt 里注明的爬取间隔（``www.douban.com`` 的 ``Crawl-delay: 5``）。
#: 低于它的档位会在启动提示里被明确点出来，而不是悄悄跑过去。
ROBOTS_CRAWL_DELAY = 5.0

#: 请求间隔档位：``名字 → (下限秒, 上限秒)``，实际间隔在其中随机抖动。
#: 名字描述的是"有多客气"，不是"有多快"：默认档之所以慢，是因为它正好卡在
#: ``Crawl-delay: 5`` 上，而不是因为技术上做不到更快。另外两档都是**明确
#: 快于** robots.txt 建议值的选项，选之前请自行确认可以接受。
SPEED_TIERS: dict[str, tuple[float, float]] = {
    "cautious": (5.0, 7.0),
    "normal": (2.0, 3.0),
    "fast": (1.0, 2.0),
}

#: 默认档位（``--speed`` 不传时用的就是它）。
DEFAULT_SPEED = "cautious"


def speed_tier(name: str) -> tuple[float, float]:
    """档位名 → ``(delay_min, delay_max)``；未知档位抛 :class:`ValueError`。"""
    try:
        return SPEED_TIERS[name]
    except KeyError:
        raise ValueError(
            f"未知速度档位 {name!r}，可选：{'、'.join(SPEED_TIERS)}"
        ) from None


def speed_tier_name(delay_min: float, delay_max: float) -> str | None:
    """``(delay_min, delay_max)`` 反查档位名；不是任何预设档时返回 ``None``。

    单看 ``--delay 0.5`` 这种自定义间隔没法知道用户选了哪一档，
    所以这里只是**回查**用于显示，配置里的真身始终是那两个秒数。
    """
    for name, bounds in SPEED_TIERS.items():
        if (delay_min, delay_max) == bounds:
            return name
    return None


def describe_delay(delay_min: float, delay_max: float) -> str:
    """给人看的一行限速描述，如 ``5~7 秒（cautious 档）``。"""
    name = speed_tier_name(delay_min, delay_max)
    tier = f"{name} 档" if name else "自定义"
    return f"{delay_min:g}~{delay_max:g} 秒（{tier}）"


@dataclass(frozen=True)
class Config:
    """抓取与生成的全部配置。"""

    # ---------- 站点 ----------
    site_id: str = "211330"
    site_name: str = "兔子山的小站"
    base_url: str = "https://site.douban.com/211330"
    site_url: str = "https://site.douban.com/211330/"
    site_description: str = (
        "《轻音！》系列、《玉子市场》、《玉子爱情故事》、《聲之形》… "
        "世界中闪耀的光辉☆ 山田尚子作品专题站"
    )
    owner: str = "羽音"
    owner_created: str = "2013-05-01"

    # ---------- 抓取礼貌参数 ----------
    # 豆瓣 www.douban.com/robots.txt 注明 Crawl-delay: 5。
    # site.douban.com 的 robots.txt 为全量 Disallow，本工具以更低频运行并支持熔断。
    # 下面两个秒数是限速的**唯一真身**：``--speed`` 只是把 SPEED_TIERS 里的预设
    # 写进来，``--delay`` 则是直接写。所有限速逻辑都读这里，不再有第二份状态。
    delay_min: float = field(default_factory=lambda: _env_float("USAGI_DELAY_MIN", 5.0))
    delay_max: float = field(default_factory=lambda: _env_float("USAGI_DELAY_MAX", 7.0))
    timeout: float = field(default_factory=lambda: _env_float("USAGI_TIMEOUT", 30.0))
    max_retries: int = field(default_factory=lambda: int(_env_float("USAGI_MAX_RETRIES", 5)))
    backoff_base: float = field(default_factory=lambda: _env_float("USAGI_BACKOFF_BASE", 5.0))
    # 连续多少次"被拦截"响应后熔断停止
    circuit_break_after: int = field(
        default_factory=lambda: int(_env_float("USAGI_CIRCUIT_BREAK_AFTER", 3))
    )
    user_agent: str = USER_AGENT

    # ---------- Internet Archive 补足（可选，默认关闭）----------
    # 默认关闭的原因：archive.org 限流严格、单次查询可能耗时 10~60s，
    # 且绝大多数页面并不需要补足。需要时用 `--archive` 显式开启。
    archive_enabled: bool = field(
        default_factory=lambda: _env_bool("USAGI_ARCHIVE_ENABLED", False)
    )
    # archive.org 限流更严格（实测裸请求即返回 429）
    archive_delay_min: float = field(
        default_factory=lambda: _env_float("USAGI_ARCHIVE_DELAY_MIN", 10.0)
    )
    archive_delay_max: float = field(
        default_factory=lambda: _env_float("USAGI_ARCHIVE_DELAY_MAX", 15.0)
    )
    archive_retries: int = field(
        default_factory=lambda: int(_env_float("USAGI_ARCHIVE_RETRIES", 4))
    )
    # archive.org 被限流时的退避起点要比源站更大
    archive_backoff_base: float = field(
        default_factory=lambda: _env_float("USAGI_ARCHIVE_BACKOFF_BASE", 20.0)
    )

    # ---------- 源站抖动 ----------
    # site.douban.com 的小站 widget 后端不稳定：**同一个 URL** 会间歇性返回通用
    # 404 页（"呃...你想访问的页面不存在"），几分钟后再请求又是 200；同样的抖动
    # 还会把照片地址渲染成字面量 ``src="None"``。
    # 因此落在这些域名上的 404 不能当作"内容已不存在"的证据 —— 归档一旦判定不可得
    # 就不会再回头看。处理方式：不写缓存 + 解析层标为可重试，下次同步自动重试。
    untrusted_404_hosts: tuple[str, ...] = ("site.douban.com",)

    # ---------- 图片尺寸 ----------
    # 相册：thumb=13KB / m=46KB / photo=123KB / large=618KB（large 是豆瓣的
    # 处理版，长边 1600，小图还会被放大）；真正的原图要从详情页的
    # "查看原图"链接取，见 media.album_original_variants。
    album_image_size: str = "large"
    # 日记配图：small=4.9KB / medium=84KB / large=211KB / raw=207KB
    note_image_size: str = "raw"
    note_image_fallback_size: str = "large"

    # ---------- 离线模式 ----------
    # True 时只读本地缓存，绝不发起网络请求
    offline: bool = field(default_factory=lambda: _env_bool("USAGI_OFFLINE", False))

    # ---------- HTTP 传输（curl_cffi）----------
    # 使用 curl_cffi（curl-impersonate 的 Python 绑定）模拟真实浏览器的
    # TLS / HTTP2 指纹。目标站点对 TLS 指纹有校验，裸 requests 会收到
    # SSLEOFError（实测首个请求连续 4 次失败）。这是业界标准做法：
    # curl_cffi 维护着一套与真实浏览器逐字节一致的指纹配置，无需自行拼装。
    impersonate: str = field(
        default_factory=lambda: os.environ.get("USAGI_IMPERSONATE", "chrome")
    )
    # 进度文件自动落盘频率（每 N 次记录写一次），用于断点续接
    progress_autosave_every: int = field(
        default_factory=lambda: int(_env_float("USAGI_PROGRESS_AUTOSAVE_EVERY", 20))
    )

    # ---------- 浏览器传输（Playwright + 系统 Chrome）----------
    # 默认启用：目标站点有反爬措施，浏览器能执行 JS 并携带登录态。
    # 用 --no-browser 可退回纯 HTTP（快、轻，但拿不到需登录的内容）。
    browser_enabled: bool = field(
        default_factory=lambda: _env_bool("USAGI_BROWSER", True)
    )
    # 用系统已安装的 Chrome（channel="chrome"），无需 playwright install，
    # 且真实 Chrome 构建比自带 Chromium 更难被识别。
    browser_channel: str = field(
        default_factory=lambda: os.environ.get("USAGI_BROWSER_CHANNEL", "chrome")
    )
    # 抓取时无头；login 子命令会强制有头（用户需要看到登录窗口）
    browser_headless: bool = field(
        default_factory=lambda: _env_bool("USAGI_BROWSER_HEADLESS", True)
    )
    # 登录等待超时（秒）
    browser_login_timeout: float = field(
        default_factory=lambda: _env_float("USAGI_BROWSER_LOGIN_TIMEOUT", 300.0)
    )
    # 每 N 次导航重建一次 page，防止长时间运行内存增长
    browser_page_recycle: int = field(
        default_factory=lambda: int(_env_float("USAGI_BROWSER_PAGE_RECYCLE", 200))
    )
    # 浏览器导航超时（毫秒）。比 HTTP 的 timeout 宽松一些，
    # 因为要等 DOM 构建完成。
    browser_nav_timeout_ms: int = field(
        default_factory=lambda: int(_env_float("USAGI_BROWSER_NAV_TIMEOUT_MS", 45_000))
    )
    # 无头启动会让 Chrome 在 UA 里带上 "HeadlessChrome" 标识，而有头时同一个
    # Chrome 发的是 "Chrome"。这只是我们选了无头启动的副作用，并不代表换了客户端，
    # 因此默认把它改回来（基于浏览器自己的真实版本号，不伪造版本）。
    # 注意：navigator.webdriver 不在此列——那是真正的自动化标记，不做处理。
    browser_normalize_headless_ua: bool = field(
        default_factory=lambda: _env_bool("USAGI_BROWSER_NORMALIZE_UA", True)
    )

    # ---------- 路径 ----------
    root: Path = ROOT
    cache_dir: Path = ROOT / "scraper" / "state" / "cache"
    state_dir: Path = ROOT / "scraper" / "state"
    data_dir: Path = ROOT / "data"
    docs_dir: Path = ROOT / "docs"
    media_dir: Path = ROOT / "docs" / "public" / "media"
    fixtures_dir: Path = ROOT / "scraper" / "tests" / "fixtures"

    # ---------- 产物文件名 ----------
    manifest_name: str = "manifest.json"
    progress_name: str = "progress.json"
    auth_state_name: str = "douban.auth.json"

    # ---------- 派生路径 ----------
    @property
    def manifest_path(self) -> Path:
        return self.state_dir / self.manifest_name

    @property
    def progress_path(self) -> Path:
        """断点续接的进度文件。"""
        return self.state_dir / self.progress_name

    @property
    def auth_state_path(self) -> Path:
        """登录会话文件（含敏感 cookie，必须 gitignore，权限 0600）。"""
        return self.state_dir / self.auth_state_name

    @property
    def chrome_ua_cache_path(self) -> Path:
        """探测到的 Chrome UA 缓存（避免每次启动都开浏览器）。"""
        return self.state_dir / "chrome_ua.txt"

    @property
    def tmp_dir(self) -> Path:
        """原子写入的临时文件目录。

        刻意放在 ``docs/.vitepress/`` 下 —— 它和 ``docs/public/`` 在同一个
        文件系统（``os.replace`` 才能原子生效），但**不在** Vite 会遍历并
        拷贝的目录树里。原因见 :func:`scraper.util.atomic_write_bytes`。
        """
        return self.docs_dir / ".vitepress" / ".tmp"

    @property
    def notes_dir(self) -> Path:
        return self.docs_dir / "notes"

    @property
    def albums_dir(self) -> Path:
        return self.docs_dir / "albums"

    @property
    def sidebar_path(self) -> Path:
        return self.docs_dir / ".vitepress" / "sidebar.generated.mts"

    # ---------- 常用 URL 构造 ----------
    def room_url(self, room_id: str) -> str:
        return f"{self.base_url}/room/{room_id}/"

    def notes_list_url(self, widget_id: str, start: int = 0) -> str:
        url = f"{self.base_url}/widget/notes/{widget_id}/"
        return f"{url}?start={start}" if start else url

    def note_url(self, widget_id: str, note_id: str) -> str:
        return f"{self.base_url}/widget/notes/{widget_id}/note/{note_id}/"

    def photos_list_url(self, album_id: str, start: int = 0) -> str:
        url = f"{self.base_url}/widget/photos/{album_id}/"
        return f"{url}?start={start}" if start else url

    def photo_url(self, album_id: str, photo_id: str) -> str:
        return f"{self.base_url}/widget/photos/{album_id}/photo/{photo_id}/"

    def videos_list_url(self, widget_id: str) -> str:
        return f"{self.base_url}/widget/videos/{widget_id}/"

    def video_url(self, widget_id: str, video_id: str) -> str:
        return f"{self.base_url}/widget/videos/{widget_id}/video/{video_id}/"

    def forum_url(self, forum_id: str) -> str:
        return f"{self.base_url}/widget/forum/{forum_id}/"

    def discussion_url(self, forum_id: str, discussion_id: str) -> str:
        return f"{self.base_url}/widget/forum/{forum_id}/discussion/{discussion_id}/"

    def miniblog_url(self, widget_id: str) -> str:
        return f"{self.base_url}/widget/miniblog/{widget_id}/"

    # ---------- 图片 Referer ----------
    @property
    def image_referer(self) -> str:
        return self.site_url


CONFIG = Config()


def ensure_dirs(cfg: Config = CONFIG) -> None:
    """创建运行所需目录。"""
    for path in (
        cfg.cache_dir,
        cfg.state_dir,
        cfg.data_dir,
        cfg.media_dir,
        cfg.notes_dir,
        cfg.albums_dir,
        cfg.tmp_dir,
        cfg.sidebar_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
