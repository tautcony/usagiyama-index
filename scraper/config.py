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
    # archive.org 被限流时的退避起点要比源站更大
    archive_backoff_base: float = field(
        default_factory=lambda: _env_float("USAGI_ARCHIVE_BACKOFF_BASE", 20.0)
    )

    # ---------- 图片尺寸 ----------
    # 相册：thumb=13KB / m=46KB / photo=123KB / large=618KB / raw 不可用
    album_image_size: str = "large"
    # 日记配图：small=4.9KB / medium=84KB / large=211KB / raw=207KB
    note_image_size: str = "raw"
    note_image_fallback_size: str = "large"

    # ---------- 离线模式 ----------
    # True 时只读本地缓存，绝不发起网络请求
    offline: bool = field(default_factory=lambda: _env_bool("USAGI_OFFLINE", False))

    # ---------- 浏览器行为模拟 ----------
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

    # ---------- 浏览器行为模拟 ----------
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

    # ---------- 派生路径 ----------
    @property
    def manifest_path(self) -> Path:
        return self.state_dir / self.manifest_name

    @property
    def progress_path(self) -> Path:
        """断点续接的进度文件。"""
        return self.state_dir / self.progress_name

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
        cfg.sidebar_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
