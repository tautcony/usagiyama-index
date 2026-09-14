"""图片归档：URL 升级、带 Referer 下载、完整性校验、archive.org 兜底。

三个必须处理好的现实问题：

1. **防盗链**：``img*.doubanio.com`` 不带 ``Referer`` 返回 **418**。
   所有图片请求强制带 ``Referer: https://site.douban.com/211330/``。
2. **尺寸**：列表页给的是 ``thumb``（13KB）。归档时升级到可用的最大尺寸
   （相册 ``large`` 618KB、日记配图 ``raw`` 207KB）。
3. **假成功**：源站出错时可能返回 HTML 错误页而不是图片。
   因此下载后一律做 **magic bytes 校验**，不是真图片就换尺寸重试，
   再失败则走 archive.org 快照。

命名规则保证幂等，便于增量同步：

* 日记配图  ``docs/public/media/notes/{noteId}/{原文件名}``
* 相册图片  ``docs/public/media/albums/{albumId}/{photoId}.jpg``
* 视频缩略图 ``docs/public/media/videos/{videoId}.jpg``
* 站点素材  ``docs/public/media/site/{文件名}``
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from .archive import WaybackClient
from .config import CONFIG, Config
from .http_client import BlockedError, FetchError, OfflineCacheMiss
from .transport import Transport
from .models import ImageRef
from .util import atomic_write_bytes

log = logging.getLogger("usagi.media")

# 图片魔数 → 格式名
MAGIC_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"BM", "bmp"),
)

# 豆瓣图片尺寸变体路径片段
SIZE_SEGMENT_RE = re.compile(r"/view/(?:photo|note)/([a-z]+)/public/")
# 站点媒体目录
NOTE_MEDIA_PREFIX = "/media/notes"
ALBUM_MEDIA_PREFIX = "/media/albums"
VIDEO_MEDIA_PREFIX = "/media/videos"
SITE_MEDIA_PREFIX = "/media/site"

# 图片尺寸升级顺序（按可用性与质量）
NOTE_SIZE_ORDER = ("raw", "large", "medium", "small")
ALBUM_SIZE_ORDER = ("large", "photo", "m", "thumb")


def sniff_image(data: bytes) -> str | None:
    """识别图片格式；返回 ``None`` 表示不是可识别的图片。"""
    if not data or len(data) < 12:
        return None
    for prefix, name in MAGIC_PREFIXES:
        if data.startswith(prefix):
            return name
    # WebP: RIFF....WEBP
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    head = data[:512].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "svg"
    return None


def is_valid_image(path: Path) -> bool:
    """磁盘上的文件是否为真实图片（而非 HTML 错误页）。"""
    try:
        with path.open("rb") as handle:
            return sniff_image(handle.read(32)) is not None
    except OSError:
        return False


def _size_variants(url: str, order: tuple[str, ...]) -> list[str]:
    """按偏好顺序生成同一图片的不同尺寸 URL。

    列表页给的是 ``thumb``，详情页给的是 ``large``；归档时希望拿到可用的
    最大尺寸（相册 ``large``、日记配图 ``raw``）。因此这里**按偏好顺序
    重新排列**，而不是把原 URL 放第一位 —— 否则配置里的尺寸偏好会被忽略。
    原 URL 若不在偏好列表内则追加到末尾兜底。
    """
    parsed = urlparse(url)
    match = SIZE_SEGMENT_RE.search(parsed.path)
    if not match:
        return [url]

    # 必须用正则匹配到的**位置**来替换，不能用 str.replace：
    # 形如 /view/photo/photo/public/xxx 的 URL 里 "/photo/" 出现两次，
    # 朴素替换会命中 /view/photo/ 从而拼出 /view/large/photo/... 这种错 URL。
    start, end = match.span(1)
    variants: list[str] = []
    for size in order:
        new_path = parsed.path[:start] + size + parsed.path[end:]
        candidate = urlunparse(parsed._replace(path=new_path))
        if candidate not in variants:
            variants.append(candidate)
    if url not in variants:
        variants.append(url)
    return variants


def note_image_variants(url: str) -> list[str]:
    return _size_variants(url, NOTE_SIZE_ORDER)


def album_image_variants(url: str) -> list[str]:
    return _size_variants(url, ALBUM_SIZE_ORDER)


def basename_of(url: str, fallback: str = "image") -> str:
    name = Path(urlparse(url).path).name or fallback
    return name if "." in name else f"{name}.jpg"


@dataclass
class MediaResult:
    """一次图片归档的结果。"""

    url: str
    ok: bool = False
    local_path: Path | None = None
    local_url: str = ""
    size_bytes: int = 0
    kind: str = ""
    from_cache: bool = False
    archived: bool = False
    wayback_url: str | None = None
    error: str = ""

    @property
    def rel_path(self) -> str:
        return str(self.local_path) if self.local_path else ""


class MediaArchive:
    """图片归档器。"""

    def __init__(
        self,
        fetcher: Transport,
        wayback: WaybackClient | None = None,
        cfg: Config = CONFIG,
    ) -> None:
        self.fetcher = fetcher
        self.wayback = wayback if wayback is not None else WaybackClient(cfg)
        self.cfg = cfg
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.archived = 0
        self.bytes_total = 0

    # ---------------------------------------------------------------- 路径

    def note_image_path(self, note_id: str, url: str) -> tuple[Path, str]:
        name = basename_of(url)
        return (
            self.cfg.media_dir / "notes" / note_id / name,
            f"{NOTE_MEDIA_PREFIX}/{note_id}/{name}",
        )

    def album_image_path(self, album_id: str, photo_id: str, url: str = "") -> tuple[Path, str]:
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        name = f"{photo_id}{suffix}"
        return (
            self.cfg.media_dir / "albums" / album_id / name,
            f"{ALBUM_MEDIA_PREFIX}/{album_id}/{name}",
        )

    def find_album_image(self, album_id: str, photo_id: str) -> tuple[Path, str] | None:
        """在已归档目录中查找某张照片的落盘文件，找不到返回 ``None``。

        文件名后缀取自下载时使用的大图 URL，而相册列表页只给得出缩略图 URL，
        两者后缀未必一致，因此不能按 URL 反推路径，只能按 ``<photo_id>.*`` 查找。
        """
        directory = self.cfg.media_dir / "albums" / album_id
        if not directory.is_dir():
            return None
        for path in sorted(directory.glob(f"{photo_id}.*")):
            if path.is_file():
                return path, f"{ALBUM_MEDIA_PREFIX}/{album_id}/{path.name}"
        return None

    def video_thumb_path(self, video_id: str, url: str = "") -> tuple[Path, str]:
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        name = f"{video_id}{suffix}"
        return (
            self.cfg.media_dir / "videos" / name,
            f"{VIDEO_MEDIA_PREFIX}/{name}",
        )

    def site_asset_path(self, name: str) -> tuple[Path, str]:
        return self.cfg.media_dir / "site" / name, f"{SITE_MEDIA_PREFIX}/{name}"

    # ---------------------------------------------------------------- 下载

    def download(
        self,
        url: str,
        dest: Path,
        local_url: str,
        *,
        variants: list[str] | None = None,
        allow_archive: bool = True,
        force: bool = False,
    ) -> MediaResult:
        """下载一张图片到 ``dest``，返回归档结果。"""
        result = MediaResult(url=url, local_path=dest, local_url=local_url)

        # 幂等：已存在且是有效图片则跳过（增量同步的关键）
        if not force and dest.exists() and is_valid_image(dest):
            result.ok = True
            result.size_bytes = dest.stat().st_size
            result.kind = sniff_image(dest.read_bytes()[:32]) or ""
            result.from_cache = True
            self.skipped += 1
            return result

        for candidate in variants or [url]:
            try:
                resp = self.fetcher.get_image(candidate)
            except (BlockedError, FetchError, OfflineCacheMiss) as exc:
                result.error = str(exc)
                continue

            kind = sniff_image(resp.content)
            if kind is None:
                result.error = f"返回内容不是图片（{len(resp.content)}B，疑似错误页）"
                log.warning("图片内容异常 %s：%s", candidate, result.error)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(dest, resp.content, tmp_dir=self.cfg.tmp_dir)
            result.ok = True
            result.size_bytes = len(resp.content)
            result.kind = kind
            self.downloaded += 1
            self.bytes_total += result.size_bytes
            if candidate != url:
                result.url = candidate
            return result

        # 源站拿不到 → 尝试 archive.org
        if allow_archive and self.wayback.enabled:
            shot = self.wayback.fetch_image(url)
            if shot is not None:
                data, wayback_url = shot
                if sniff_image(data) is not None:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write_bytes(dest, data, tmp_dir=self.cfg.tmp_dir)
                    result.ok = True
                    result.archived = True
                    result.wayback_url = wayback_url
                    result.size_bytes = len(data)
                    result.kind = sniff_image(data) or ""
                    self.archived += 1
                    self.bytes_total += result.size_bytes
                    log.info("图片已从 archive.org 补足：%s", url)
                    return result

        self.failed += 1
        if not result.error:
            result.error = "所有尺寸变体与 archive.org 均不可得"
        log.warning("图片归档失败 %s：%s", url, result.error)
        return result

    # ------------------------------------------------------------ 内容提取

    def collect_note_images(self, html: str, note_id: str) -> list[ImageRef]:
        """从日记正文 HTML 中提取所有图片。"""
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        refs: list[ImageRef] = []
        seen: set[str] = set()
        for img in soup.find_all("img"):
            src = str(img.get("src") or img.get("data-src") or "").strip()
            if not src or src in seen:
                continue
            seen.add(src)
            _, local_url = self.note_image_path(note_id, src)
            refs.append(
                ImageRef(src=src, local=local_url, alt=str(img.get("alt") or "").strip())
            )
        return refs

    def archive_note_images(self, refs: list[ImageRef], note_id: str) -> dict[str, str]:
        """下载日记配图，返回 ``{源URL: 站内URL}`` 映射供 Markdown 重写。"""
        mapping: dict[str, str] = {}
        for ref in refs:
            dest, local_url = self.note_image_path(note_id, ref.src)
            result = self.download(
                ref.src, dest, local_url, variants=note_image_variants(ref.src)
            )
            ref.archived = result.ok
            ref.bytes = result.size_bytes
            ref.archive_url = result.wayback_url
            if result.ok:
                mapping[ref.src] = local_url
        return mapping

    def archive_site_asset(self, url: str, name: str) -> str:
        """归档站点素材（logo / 头像），返回站内 URL。"""
        dest, local_url = self.site_asset_path(name)
        result = self.download(url, dest, local_url)
        return local_url if result.ok else url

    def summary(self) -> dict[str, int | float]:
        return {
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed,
            "archivedFromWayback": self.archived,
            "bytesTotal": self.bytes_total,
        }
