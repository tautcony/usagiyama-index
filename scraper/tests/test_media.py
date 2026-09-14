"""图片归档测试：格式识别、尺寸升级、路径命名。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest

from scraper.http_client import CachedResponse
from scraper.media import (
    MediaArchive,
    album_image_variants,
    basename_of,
    is_valid_image,
    note_image_variants,
    sniff_image,
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 40
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
GIF = b"GIF89a" + b"\x00" * 40
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 40
HTML_ERROR = b"<!DOCTYPE html><html><body>418</body></html>"


class TestSniffImage:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [(JPEG, "jpeg"), (PNG, "png"), (GIF, "gif"), (WEBP, "webp")],
    )
    def test_recognises_formats(self, data: bytes, expected: str) -> None:
        assert sniff_image(data) == expected

    def test_html_error_page_rejected(self) -> None:
        """豆瓣出错时会返回 HTML，绝不能当成图片存下来。"""
        assert sniff_image(HTML_ERROR) is None

    def test_empty_and_short_rejected(self) -> None:
        assert sniff_image(b"") is None
        assert sniff_image(b"abc") is None

    def test_svg_recognised(self) -> None:
        assert sniff_image(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>') == "svg"


class TestIsValidImage:
    def test_valid_file(self, tmp_path: Path) -> None:
        path = tmp_path / "a.jpg"
        path.write_bytes(JPEG)
        assert is_valid_image(path)

    def test_html_file_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "a.jpg"
        path.write_bytes(HTML_ERROR)
        assert not is_valid_image(path)

    def test_missing_file(self, tmp_path: Path) -> None:
        assert not is_valid_image(tmp_path / "nope.jpg")


class TestSizeVariants:
    NOTE = "https://img9.doubanio.com/view/note/large/public/p36410176.jpg"
    ALBUM = "https://img2.doubanio.com/view/photo/thumb/public/p2770778841.jpg"

    def test_note_prefers_raw_regardless_of_source_size(self) -> None:
        """配置偏好 raw，即使页面给的是 large 也应先试 raw。"""
        variants = note_image_variants(self.NOTE)
        assert "/raw/" in variants[0]
        assert any("/large/" in v for v in variants)

    def test_note_variants_are_deduped(self) -> None:
        variants = note_image_variants(self.NOTE)
        assert len(variants) == len(set(variants))

    def test_album_prefers_large(self) -> None:
        variants = album_image_variants(self.ALBUM)
        assert "/large/" in variants[0]
        assert len(variants) == len(set(variants))

    def test_original_appended_when_unknown_size(self) -> None:
        url = "https://img1.doubanio.com/view/photo/original/public/p1.jpg"
        assert url in album_image_variants(url)

    def test_unknown_url_passes_through(self) -> None:
        url = "https://example.com/a.jpg"
        assert note_image_variants(url) == [url]
        assert album_image_variants(url) == [url]


class TestNaming:
    def test_basename_from_url(self) -> None:
        assert basename_of("https://x/y/p1.jpg") == "p1.jpg"

    def test_basename_fallback_adds_extension(self) -> None:
        assert basename_of("https://x/y/noext") == "noext.jpg"

    def test_note_image_path(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        dest, local = archive.note_image_path("575615184", "https://img9.doubanio.com/view/note/raw/public/p1.jpg")
        assert dest == cfg.media_dir / "notes" / "575615184" / "p1.jpg"
        assert local == "/media/notes/575615184/p1.jpg"

    def test_album_image_path(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        dest, local = archive.album_image_path("13432051", "2770778841", "https://x/p2770778841.jpg")
        assert dest == cfg.media_dir / "albums" / "13432051" / "2770778841.jpg"
        assert local == "/media/albums/13432051/2770778841.jpg"

    def test_video_thumb_path(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        _, local = archive.video_thumb_path("783649", "https://x/t.jpg")
        assert local == "/media/videos/783649.jpg"


class TestCollectNoteImages:
    def test_collects_and_dedupes(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        html = (
            '<img src="https://img9.doubanio.com/view/note/raw/public/p1.jpg"/>'
            '<div class="cc"><table><tr><td>'
            '<img src="https://img9.doubanio.com/view/note/raw/public/p1.jpg"/></td></tr></table></div>'
            '<img src="https://img9.doubanio.com/view/note/raw/public/p2.jpg"/>'
        )
        refs = archive.collect_note_images(html, "1")
        assert len(refs) == 2
        assert refs[0].local == "/media/notes/1/p1.jpg"

    def test_empty_html(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        assert archive.collect_note_images("", "1") == []

    def test_data_src_supported(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        refs = archive.collect_note_images(
            '<img data-src="https://img9.doubanio.com/view/note/raw/public/p3.jpg"/>', "1"
        )
        assert len(refs) == 1

class TestSizeVariantPrecision:
    """尺寸替换必须落在正确的段位上。

    /view/photo/photo/public/x 里 "/photo/" 出现两次，
    朴素的 str.replace 会命中 /view/photo/ 而拼出 /view/large/photo/... 这种错 URL。
    """

    DOUBLE_PHOTO = "https://img2.doubanio.com/view/photo/photo/public/p2770778841.webp"

    def test_view_segment_untouched(self) -> None:
        for variant in album_image_variants(self.DOUBLE_PHOTO):
            assert "/view/photo/" in variant, variant

    def test_size_segment_replaced(self) -> None:
        variants = album_image_variants(self.DOUBLE_PHOTO)
        assert "/view/photo/large/public/" in variants[0]

    def test_no_mangled_path(self) -> None:
        for variant in album_image_variants(self.DOUBLE_PHOTO):
            assert "/view/large/" not in variant
            assert "/view/photo/photo/photo/" not in variant

    def test_all_variants_wellformed(self) -> None:
        for variant in album_image_variants(self.DOUBLE_PHOTO):
            path = urlparse(variant).path
            assert path.startswith("/view/photo/")
            # 尺寸段之后紧跟 /public/
            assert "/public/" in path

    def test_webp_extension_preserved(self) -> None:
        for variant in album_image_variants(self.DOUBLE_PHOTO):
            assert variant.endswith(".webp")

    def test_note_size_replaced_precisely(self) -> None:
        url = "https://img3.doubanio.com/view/note/small/public/p37187262.webp"
        variants = note_image_variants(url)
        assert "/view/note/raw/public/" in variants[0]
        assert all("/view/note/" in v for v in variants)


class TestDownloadTempFiles:
    """图片写入不得把临时文件留在 ``public/`` 里。

    Vite 的 ``copyDir`` 先 ``readdirSync`` 取名字、再逐个 ``copyFileSync``，
    所以只要临时文件落在 ``public/`` 中，就会被列进名单，而随后的
    ``os.replace`` 会把该名字移走 —— 构建便随机以
    ``ENOENT ... copyfile`` 失败。这里把"临时文件不进 public/"钉死。
    """

    class _StubTransport:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload

        def get_image(self, url: str) -> CachedResponse:
            return CachedResponse(url=url, status=200, content=self.payload)

    def test_temp_file_goes_to_tmp_dir_not_media_dir(self, cfg) -> None:
        archive = MediaArchive(self._StubTransport(JPEG), cfg=cfg)
        dest = cfg.media_dir / "notes" / "123" / "p1.jpg"
        url = "https://img1.doubanio.com/view/note/raw/public/p1.jpg"

        result = archive.download(url, dest, "/media/notes/123/p1.jpg")

        assert result.ok, result.error
        assert dest.exists()
        # 目标目录里只应有正式文件，没有 .tmp 残留
        assert [p.name for p in dest.parent.iterdir()] == ["p1.jpg"]

    def test_tmp_dir_is_outside_public_dir(self, cfg) -> None:
        """临时目录不能落在 Vite 会遍历拷贝的 ``public/`` 里。"""
        assert cfg.media_dir not in cfg.tmp_dir.parents
        assert cfg.tmp_dir != cfg.media_dir

    def test_failed_write_leaves_no_temp_file(self, cfg) -> None:
        from scraper.util import atomic_write_bytes

        dest = cfg.media_dir / "notes" / "123" / "p2.jpg"
        with pytest.raises(OSError):
            # 目标是一个目录，os.replace 会失败
            atomic_write_bytes(dest.parent, b"x", tmp_dir=cfg.tmp_dir)
        assert not list(cfg.tmp_dir.glob("*.tmp"))
