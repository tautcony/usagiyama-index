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
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from .archive import WaybackClient
from .config import CONFIG, Config
from .http_client import (
    MISSING_STATUS,
    BlockedError,
    CachedResponse,
    CircuitBreakerOpen,
    FetchError,
    OfflineCacheMiss,
)
from .transport import Transport
from .models import ImageRef
from .util import atomic_write_bytes, files_equal

log = logging.getLogger("usagi.media")

# 图片魔数 → 格式名
MAGIC_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)

# 真实格式 → 落盘后缀。``jpeg`` 一律落 ``.jpg`` —— ``.jpeg`` 是等价写法，
# 同一份内容在两种等价后缀间反复改名只会产生无意义的差异。
SUFFIX_FOR_KIND: dict[str, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "avif": ".avif",
    "gif": ".gif",
    "bmp": ".bmp",
    "svg": ".svg",
}

# 已知图片格式对应的标准后缀。
# 豆瓣图片尺寸变体路径片段
SIZE_SEGMENT_RE = re.compile(r"/view/(?:photo|note)/([a-z]+)/public/")
# 站点媒体目录
NOTE_MEDIA_PREFIX = "/media/notes"
ALBUM_MEDIA_PREFIX = "/media/albums"
VIDEO_MEDIA_PREFIX = "/media/videos"
SITE_MEDIA_PREFIX = "/media/site"
EXTERNAL_ARTICLE_MEDIA_PREFIX = "/media/external-articles"

# 相册原图的子目录：``media/albums/{albumId}/original/{photoId}.{ext}``。
# 单独一层目录、而不是与预览图并排放在相册根目录，是因为两者的后缀未必不同
# ——原图若是 webp，就会和预览图撞成同一个文件名，按后缀区分不可靠。
# 分目录之后两边都能独立地"有或没有"，也不需要任何按文件名猜含义的规则。
ORIGINAL_MEDIA_SUBDIR = "original"

# 预览图的后缀偏好：同一张照片若在相册根目录里同时存在多个后缀
# （旧版本归档留下过 ``.jpg``，现在详情页 ``<img>`` 给的是 ``.webp``），
# 取 webp —— 像素尺寸与 jpg 相同、体积小得多，正适合网格里显示。
# 点击预览看到的仍是原图（``original/`` 下的实拍文件），见 docs 主题的 lightbox。
PREVIEW_SUFFIX_ORDER = (".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp")

# 图片尺寸升级顺序（按可用性与质量）
NOTE_SIZE_ORDER = ("raw", "large", "medium", "small")
ALBUM_SIZE_ORDER = ("large", "photo", "m", "thumb")
# 相册原图（详情页"查看原图"链接）的升级顺序：原图拿不到时逐级退回。
# ``raw`` 是上传时的原文件，尺寸与格式由上传者决定，未必比 ``large`` 大；
# ``large`` 是豆瓣的处理版，长边固定 1600（小图还会被放大）。
ORIGINAL_SIZE_ORDER = ("raw", "large", "photo", "m", "thumb")


def sniff_image(data: bytes) -> str | None:
    """识别图片格式；返回 ``None`` 表示不是可识别的图片。"""
    if not data:
        return None
    # ISO-BMFF image files start with a sized ``ftyp`` box. Require an AVIF
    # brand so arbitrary MP4/HEIF payloads are not accepted as images.
    if len(data) >= 12 and data[4:8] == b"ftyp":
        box_size = int.from_bytes(data[:4], "big")
        if box_size >= 16:
            brands = [data[8:12]]
            brands.extend(
                data[offset : offset + 4]
                for offset in range(16, min(box_size, len(data) - 3), 4)
            )
            if b"avif" in brands or b"avis" in brands:
                return "avif"
    head = data.lstrip(b"\xef\xbb\xbf\x00\t\n\r ")
    for prefix, name in MAGIC_PREFIXES:
        if head.startswith(prefix):
            return name
    if head.startswith(b"BM"):
        # BITMAPFILEHEADER + a plausible DIB header and pixel offset.
        if (len(head) >= 14 and head[6:10] == b"\0\0\0\0"
                and int.from_bytes(head[10:14], "little") >= 14):
            return "bmp"
        return None
    # WebP: RIFF....WEBP
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    head = head[:512].lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "svg"
    return None


def is_valid_image(path: Path) -> bool:
    """磁盘上的文件是否为真实图片（而非 HTML 错误页）。"""
    try:
        with path.open("rb") as handle:
            # 读 512 字节而非 32：带 XML prolog 的 SVG 形如
            # ``<?xml …?>\n<svg …>``，未解码的 ``<svg`` 常落在 prolog 之后，
            # 只读 32 字节会判成"非图片"而被重下载/标记无效（见 SUG-15）。
            return sniff_image(handle.read(512)) is not None
    except OSError:
        return False


def read_kind(path: Path) -> str:
    """读文件头判定的真实格式；读不了返回空串。"""
    try:
        with path.open("rb") as handle:
            return sniff_image(handle.read(512)) or ""
    except OSError:
        return ""


def correct_suffix(path: Path, kind: str) -> Path:
    """把 ``path`` 的后缀纠正成 ``kind`` 对应的真实后缀。

    后缀缺失、不受浏览器识别、大小写不规范或与内容不符时，统一改为标准后缀。

    **必须做这一步**：豆瓣的 ``/view/photo/large/public/p{id}.webp`` 会返回
    ``Content-Type: image/webp`` 而 body 是 JPEG 字节（``raw`` 尺寸那份的字节原封不动），
    偶尔还会是 PNG。照 URL 后缀命名，盘上就会出现"后缀说 webp、内容是 JPEG"的假文件
    —— 既误导后续按后缀做的判断，也让 VitePress 按后缀发错 ``Content-Type``。
    落盘名字只认内容。
    """
    wanted = SUFFIX_FOR_KIND.get(kind)
    if not wanted or path.suffix == wanted:
        return path
    return path.with_suffix(wanted)


def with_name(local_url: str, name: str) -> str:
    """替换站内 URL 的最后一段文件名。

    落盘名字被纠正后，下载前算好的 ``local_url`` 就指向不存在的文件了，
    必须同步换掉最后一段才能写进 ``data/``。
    """
    head, sep, _ = local_url.rpartition("/")
    return f"{head}{sep}{name}" if sep else name


def describe_response(resp: CachedResponse) -> str:
    """把一个响应压成一行诊断信息。

    **错误码是排障的首要信息**：此前的实现仅上报字节数（如「返回内容不是图片（0B）」），
    无法从日志判断源站返回的状态码、内容类型与来源，只能手动重放请求确认
    （实际为 404 —— 某个不存在的 ``raw`` 尺寸）。
    """
    parts = [f"HTTP {resp.status}", resp.content_type.split(";")[0].strip() or "无类型"]
    parts.append(f"{len(resp.content)}B")
    if resp.from_cache:
        parts.append(f"来自缓存{f'（{resp.fetched_at}）' if resp.fetched_at else ''}")
    else:
        parts.append("本次网络请求")
    return " · ".join(parts)


def describe_non_image(resp: CachedResponse) -> str:
    """非图片响应的诊断信息：状态码 + 内容类型 + 体积 + 来源，外加一句判读。"""
    if resp.status == MISSING_STATUS:
        guess = "源站无此尺寸"
    elif resp.ok:
        guess = "疑似错误页"
    else:
        guess = "源站拒绝"
    return f"{describe_response(resp)}，{guess}"


def describe_failure(exc: Exception) -> str:
    """抓取异常的一行诊断：优先用带状态码的裸消息，避免把 URL 重复一遍。"""
    status = getattr(exc, "status", None)
    message = getattr(exc, "message", None) or str(exc)
    code = f"HTTP {status}" if status else "无响应"
    return f"{code} · {message}"


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
    return _safe_filename(name, fallback)


def _safe_filename(value: str, fallback: str) -> str:
    """Keep file names inside the supported portable ASCII set."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).lstrip(".")
    if not name:
        name = fallback
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
        name = _safe_filename(f"{photo_id}{suffix}", "photo.jpg")
        return (
            self.cfg.media_dir / "albums" / album_id / name,
            f"{ALBUM_MEDIA_PREFIX}/{album_id}/{name}",
        )

    def album_original_path(self, album_id: str, photo_id: str, url: str = "") -> tuple[Path, str]:
        """**原图**（"查看原图"的 ``raw`` 尺寸）的落盘路径。"""
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        name = _safe_filename(f"{photo_id}{suffix}", "photo.jpg")
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

    def drop_redundant_original(self, album_id: str, photo_id: str) -> bool:
        """原图与预览是同一份字节时删掉原图，返回是否删了。

        豆瓣的 ``large`` 与 ``raw`` 对同一张图常常返回同一份字节（尤其是原图本身就
        没超过 ``large`` 长边上限时），存两份不多任何信息。判别只能靠下载后比字节 ——
        尺寸不可靠：既有预览比原图大的，也有豆瓣给了小号预览而原图确实更大的。

        只有预览或只有原图时一律不动：那样删掉的就是**唯一**的一份
        （``local`` 会回退指向 ``original/`` 的情况正属此类）。
        """
        original = self.find_album_original(album_id, photo_id)
        preview = self.find_album_image(album_id, photo_id)
        if original is None or preview is None:
            return False
        if not files_equal(original[0], preview[0]):
            return False
        original[0].unlink()
        log.info("原图与预览字节相同，只保留预览：%s", original[0].name)
        return True

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
        name = _safe_filename(f"{video_id}{suffix}", "video.jpg")
        return (
            self.cfg.media_dir / "videos" / name,
            f"{VIDEO_MEDIA_PREFIX}/{name}",
        )

    def site_asset_path(self, name: str) -> tuple[Path, str]:
        return self.cfg.media_dir / "site" / name, f"{SITE_MEDIA_PREFIX}/{name}"

    def external_article_image_path(
        self, domain: str, article_id: str, url: str
    ) -> tuple[Path, str]:
        """Build a stable, collision-resistant path for a captured article image."""
        domain_slug = re.sub(r"[^a-z0-9.-]+", "_", domain.lower()).strip("._") or "unknown"
        image_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        original_name = basename_of(url)
        suffix = Path(original_name).suffix.lower()
        name = f"{image_id}-{Path(original_name).stem}{suffix}"
        relative = Path(domain_slug) / article_id / name
        return (
            self.cfg.media_dir / "external-articles" / relative,
            f"{EXTERNAL_ARTICLE_MEDIA_PREFIX}/{relative.as_posix()}",
        )

    # ---------------------------------------------------------------- 下载

    def _existing_archived(self, dest: Path) -> Path | None:
        """在 ``dest`` 同目录里找这张图已归档的那一份，没有返回 ``None``。

        落盘名字由内容决定，所以 ``dest``（按 URL 后缀猜的）可能根本不是实际文件名。
        按 stem 把同目录的兄弟后缀依次看一遍即可 —— 相册照片的 stem 是 ``photo_id``、
        日记配图是 URL 哈希、视频缩略图是 ``video_id``，都只对应这一张图，不会串。
        """
        if dest.exists() and is_valid_image(dest):
            return dest
        for suffix in PREVIEW_SUFFIX_ORDER:
            candidate = dest.with_suffix(suffix)
            if candidate != dest and candidate.exists() and is_valid_image(candidate):
                return candidate
        return None

    def _heal_suffix(self, path: Path) -> Path:
        """后缀与真实格式不符时就地改名，返回改名后的路径。

        这是给"URL 后缀撒谎"时代的存量文件兜底的：新下载已经由
        :func:`correct_suffix` 直接落成真实后缀，但老文件不会自己变。
        目标名已被占用时保持原样并记 WARNING —— 那说明同一目录里两张**不同**的图
        争一个名字，属于需人工确认的情况，绝不能静默覆盖其中任意一张。
        """
        kind = read_kind(path)
        target = correct_suffix(path, kind)
        if target == path:
            return path
        if target.exists():
            log.warning(
                "后缀与内容不符但纠正目标已被占用，保持原样：%s（实际是 %s）→ %s",
                path.name,
                kind,
                target.name,
            )
            return path
        path.rename(target)
        log.info("按真实格式纠正后缀：%s → %s", path.name, target.name)
        return target

    def download(
        self,
        url: str,
        dest: Path,
        local_url: str,
        *,
        variants: list[str] | None = None,
        allow_archive: bool = True,
        force: bool = False,
        referer: str | None = None,
        max_bytes: int | None = None,
    ) -> MediaResult:
        """下载一张图片到 ``dest``，返回归档结果。

        ``dest`` 只是**按 URL 后缀猜的名字**：真正落盘的名字由内容决定
        （见 :func:`correct_suffix`），因此成功时要以 ``result.local_path`` /
        ``result.local_url`` 为准，调用方不能再用传进来的 ``dest`` / ``local_url``。
        """
        result = MediaResult(url=url, local_path=dest, local_url=local_url)

        # 幂等：已归档且是有效图片则跳过（增量同步的关键）。不能只看 dest ——
        # 它可能已不是当初落盘的名字（URL 给 .webp、内容是 JPEG，落盘时纠正成了 .jpg），
        # 只看 dest 会让每次运行都把它当"没下过"而重复下载。
        existing = None if force else self._existing_archived(dest)
        if existing is not None:
            existing = self._heal_suffix(existing)
            result.ok = True
            result.local_path = existing
            result.local_url = with_name(local_url, existing.name)
            result.size_bytes = existing.stat().st_size
            result.kind = read_kind(existing)
            result.from_cache = True
            self.skipped += 1
            return result

        # 逐个候选尝试。失败的候选在这里只记 INFO —— 多尺寸候选里的"这条不存在"
        # 是**预期内**的（同一张图只有某一个尺寸/某一台 CDN 上有），
        # 此前的实现将其按 WARNING 输出，易误判为归档失败，而后续候选通常会立即成功。
        # 真正的失败由末尾那条 WARNING 一次性汇总，带上每个候选的状态码。
        failures: list[str] = []
        for candidate in variants or [url]:
            try:
                resp = (
                    self.fetcher.get_image(
                        candidate, force=True, **({"referer": referer} if referer else {})
                    )
                    if force
                    else self.fetcher.get_image(
                        candidate, **({"referer": referer} if referer else {})
                    )
                )
            except CircuitBreakerOpen:
                raise
            except (BlockedError, FetchError, OfflineCacheMiss) as exc:
                note = describe_failure(exc)
                failures.append(f"{candidate} → {note}")
                log.info("图片候选不可用 %s：%s，尝试下一个候选", candidate, note)
                continue

            kind = sniff_image(resp.content)
            if kind is None:
                note = describe_non_image(resp)
                failures.append(f"{candidate} → {note}")
                log.info("图片候选不可用 %s：%s，尝试下一个候选", candidate, note)
                # 缓存里存的 2xx 却不是图片 —— 这份缓存是坏的（源站出错时把错误页
                # 当图片缓存了）。不清掉的话每次运行都会重放它，所以当场丢弃。
                if resp.from_cache and resp.ok:
                    self.fetcher.invalidate_cache(candidate)
                continue
            if max_bytes is not None and len(resp.content) > max_bytes:
                failures.append(f"{candidate} → 图片超过上限（{len(resp.content)}B > {max_bytes}B）")
                continue

            # 落盘名字只认内容：URL 后缀是 CDN 的一面之词，实测会撒谎。
            target = correct_suffix(dest, kind)
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(target, resp.content, tmp_dir=self.cfg.tmp_dir)
            result.ok = True
            result.local_path = target
            result.local_url = with_name(local_url, target.name)
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
                kind = sniff_image(data)
                if kind is not None:
                    target = correct_suffix(dest, kind)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write_bytes(target, data, tmp_dir=self.cfg.tmp_dir)
                    result.ok = True
                    result.archived = True
                    result.wayback_url = wayback_url
                    result.local_path = target
                    result.local_url = with_name(local_url, target.name)
                    result.size_bytes = len(data)
                    result.kind = kind
                    self.archived += 1
                    self.bytes_total += result.size_bytes
                    log.info("图片已从 archive.org 补足：%s", url)
                    return result
                failures.append(f"archive.org 快照 → {len(data)}B，不是图片")

        self.failed += 1
        if failures:
            result.error = "；".join(failures)
        elif not result.error:
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

    def archive_note_images(
        self, refs: list[ImageRef], note_id: str, *, force: bool = False
    ) -> dict[str, str]:
        """下载日记配图，返回 ``{源URL: 站内URL}`` 映射供 Markdown 重写。"""
        mapping: dict[str, str] = {}
        for ref in refs:
            dest, local_url = self.note_image_path(note_id, ref.src)
            result = self.download(
                ref.src,
                dest,
                local_url,
                variants=note_image_variants(ref.src),
                force=force,
            )
            ref.archived = result.ok
            ref.bytes = result.size_bytes
            ref.archive_url = result.wayback_url
            if result.ok:
                # 落盘后缀可能被纠正过，映射要用纠正后的站内 URL
                ref.local = result.local_url
                mapping[ref.src] = result.local_url
            elif force:
                # 强制检查失败时保留旧归档图，避免临时网络故障使已保存正文裂图。
                existing = self._existing_archived(dest)
                if existing is not None:
                    ref.archived = True
                    ref.local = with_name(local_url, existing.name)
                    ref.bytes = existing.stat().st_size
                    mapping[ref.src] = ref.local
        return mapping

    def archive_site_asset(self, url: str, name: str) -> str:
        """归档站点素材（logo / 头像），返回站内 URL。"""
        dest, local_url = self.site_asset_path(name)
        result = self.download(url, dest, local_url)
        return result.local_url if result.ok else url

    def summary(self) -> dict[str, int | float]:
        return {
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed,
            "archivedFromWayback": self.archived,
            "bytesTotal": self.bytes_total,
        }
