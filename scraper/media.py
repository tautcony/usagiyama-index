"""图片归档：URL 升级、带 Referer 下载、完整性校验、archive.org 兜底。

三个必须处理好的现实问题：

1. **防盗链**：``img*.doubanio.com`` 不带 ``Referer`` 返回 **418**。
   所有图片请求强制带 ``Referer: https://site.douban.com/211330/``。
2. **尺寸**：列表页给的是 ``thumb``（13KB）。归档时升级到可用的最大尺寸
   （日记配图 ``raw``、相册优先详情页"查看原图"的 ``raw`` 原图，
   拿不到才退回 ``large``）。
3. **假成功**：源站出错时可能返回 HTML 错误页而不是图片。
   因此下载后一律做 **magic bytes 校验**，不是真图片就换尺寸重试，
   再失败则走 archive.org 快照。

命名规则保证幂等，便于增量同步：

* 日记配图  ``docs/public/media/notes/{noteId}/{原文件名}``
* 相册预览图 ``docs/public/media/albums/{albumId}/{photoId}.{后缀}``
  （网格里显示的那张，取自详情页 ``<img>``）
* 相册原图  ``docs/public/media/albums/{albumId}/original/{photoId}.{后缀}``
  （详情页"查看原图"链接指向的 ``raw`` 文件，点开预览时看的就是它）
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

# 相册原图的子目录：``media/albums/{albumId}/original/{photoId}.{ext}``。
# 单独一层目录、而不是与预览图并排放在相册根目录，是因为两者的后缀未必不同
# ——原图若是 webp，就会和预览图撞成同一个文件名，按后缀区分不可靠。
# 分目录之后两边都能独立地"有或没有"，也不需要任何按文件名猜含义的规则。
ORIGINAL_MEDIA_SUBDIR = "original"

# 预览图的后缀偏好：同一张照片若在相册根目录里同时存在多个后缀
# （旧版本归档留下过 ``.jpg``，现在详情页 ``<img>`` 给的是 ``.webp``），
# 取 webp —— 像素尺寸与 jpg 相同、体积小得多，正适合网格里显示。
# 点击预览看到的仍是原图（``original/`` 下的实拍文件），见 docs 主题的 lightbox。
PREVIEW_SUFFIX_ORDER = (".webp", ".jpg", ".jpeg", ".png", ".gif")

# 图片尺寸升级顺序（按可用性与质量）
NOTE_SIZE_ORDER = ("raw", "large", "medium", "small")
ALBUM_SIZE_ORDER = ("large", "photo", "m", "thumb")
# 相册原图（详情页"查看原图"链接）的升级顺序：原图拿不到时逐级退回。
# 注意 ``raw`` 是上传时的原文件，尺寸与格式都由上传者决定，未必比 ``large`` 大
# —— ``large`` 是豆瓣的处理版，长边固定 1600（小图还会被放大），两者不可互换。
ORIGINAL_SIZE_ORDER = ("raw", "large", "photo", "m", "thumb")


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
    """相册图片的尺寸候选（从"查看原图"链接出发时用 :func:`album_original_variants`）。"""
    return _size_variants(url, ALBUM_SIZE_ORDER)


def album_original_variants(url: str) -> list[str]:
    """相册原图（``raw``）的尺寸候选：原图优先，拿不到再逐级退回处理版。"""
    return _size_variants(url, ORIGINAL_SIZE_ORDER)


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
        """**预览图**的落盘路径：网格里显示的那张（页面 ``<img>`` 的尺寸）。

        原图另有 :meth:`album_original_path`，两者分目录存放。
        """
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        name = f"{photo_id}{suffix}"
        return (
            self.cfg.media_dir / "albums" / album_id / name,
            f"{ALBUM_MEDIA_PREFIX}/{album_id}/{name}",
        )

    def album_original_path(self, album_id: str, photo_id: str, url: str = "") -> tuple[Path, str]:
        """**原图**（"查看原图"的 ``raw`` 尺寸）的落盘路径。"""
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        name = f"{photo_id}{suffix}"
        return (
            self.cfg.media_dir / "albums" / album_id / ORIGINAL_MEDIA_SUBDIR / name,
            f"{ALBUM_MEDIA_PREFIX}/{album_id}/{ORIGINAL_MEDIA_SUBDIR}/{name}",
        )

    def find_album_image(self, album_id: str, photo_id: str) -> tuple[Path, str] | None:
        """在已归档目录中查找某张照片的**预览图**，找不到返回 ``None``。

        文件名后缀取自下载时使用的 URL，而相册列表页只给得出缩略图 URL，
        两者后缀未必一致，因此不能按 URL 反推路径，只能按 ``<photo_id>.*`` 查找。
        原图不在这一层（见 :data:`ORIGINAL_MEDIA_SUBDIR`），不会被误认成预览图。
        """
        return self._find_album_file(
            self.cfg.media_dir / "albums" / album_id,
            album_id,
            photo_id,
            preferred_suffixes=PREVIEW_SUFFIX_ORDER,
        )

    def find_album_original(self, album_id: str, photo_id: str) -> tuple[Path, str] | None:
        """查找某张照片的**原图**，找不到返回 ``None``。"""
        return self._find_album_file(
            self.cfg.media_dir / "albums" / album_id / ORIGINAL_MEDIA_SUBDIR,
            album_id,
            photo_id,
            f"{ORIGINAL_MEDIA_SUBDIR}/",
        )

    def _find_album_file(
        self,
        directory: Path,
        album_id: str,
        photo_id: str,
        prefix: str = "",
        preferred_suffixes: tuple[str, ...] = (),
    ) -> tuple[Path, str] | None:
        if not directory.is_dir():
            return None
        paths = [path for path in directory.glob(f"{photo_id}.*") if path.is_file()]
        if not paths:
            return None
        if preferred_suffixes:
            # 同一张照片可能有多个后缀的副本（早期归档留下的 ``.jpg`` 与现在的
            # ``.webp``），按偏好取第一个；其余不删 —— 它们已经进了 git 历史，
            # 删掉既省不下多少空间，又会让"归档"这件事变得不可回溯。
            rank = {suffix: order for order, suffix in enumerate(preferred_suffixes)}
            paths.sort(key=lambda path: (rank.get(path.suffix.lower(), len(rank)), path.name))
        else:
            paths.sort()
        path = paths[0]
        return path, f"{ALBUM_MEDIA_PREFIX}/{album_id}/{prefix}{path.name}"

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
