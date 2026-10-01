"""图片归档测试：格式识别、尺寸升级、路径命名。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest

from scraper.http_client import CachedResponse
from scraper.media import (
    MediaArchive,
    album_image_variants,
    album_original_variants,
    basename_of,
    is_valid_image,
    note_image_variants,
    sniff_image,
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 40
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
GIF = b"GIF89a" + b"\x00" * 40
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 40
# Minimal ISO-BMFF ftyp header using AVIF as its major brand.
AVIF = b"\x00\x00\x00\x1cftypavif\x00\x00\x00\x00mif1avifmiaf"
HTML_ERROR = b"<!DOCTYPE html><html><body>418</body></html>"


class TestSniffImage:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [(JPEG, "jpeg"), (PNG, "png"), (GIF, "gif"), (WEBP, "webp"), (AVIF, "avif")],
    )
    def test_recognises_formats(self, data: bytes, expected: str) -> None:
        assert sniff_image(data) == expected

    def test_html_error_page_rejected(self) -> None:
        """豆瓣出错时会返回 HTML，绝不能当成图片存下来。"""
        assert sniff_image(HTML_ERROR) is None

    def test_non_avif_iso_bmff_rejected(self) -> None:
        assert sniff_image(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isom") is None

    def test_empty_and_short_rejected(self) -> None:
        assert sniff_image(b"") is None
        assert sniff_image(b"abc") is None

    def test_svg_recognised(self) -> None:
        assert sniff_image(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>') == "svg"

    def test_leading_bom_whitespace_and_short_svg(self) -> None:
        assert sniff_image(b"\xef\xbb\xbf  \xff\xd8\xff" + b"x" * 12) == "jpeg"
        assert sniff_image(b" <svg/>") == "svg"
        assert sniff_image(b"<?xml version='1.0'?> <svg/>") == "svg"
        assert sniff_image(b"BMnot-a-bitmap") is None


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

    def test_original_prefers_raw_then_falls_back(self) -> None:
        """"查看原图"链接（raw）为起点时，原图排第一，其后逐级退回处理版。"""
        raw = "https://img1.doubanio.com/view/photo/raw/public/p2325379542.jpg"
        variants = album_original_variants(raw)
        assert variants[0] == raw
        assert "/large/" in variants[1]
        assert len(variants) == len(set(variants))

    def test_original_variants_keep_extension(self) -> None:
        """只换尺寸段，不动后缀 —— 原图是 .jpg，页面那张可能是 .webp。"""
        raw = "https://img1.doubanio.com/view/photo/raw/public/p2325379542.jpg"
        assert all(v.endswith("p2325379542.jpg") for v in album_original_variants(raw))

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

    def test_external_article_image_path_normalizes_extension_case(self, cfg) -> None:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        dest, local = archive.external_article_image_path(
            "example.com", "article", "https://example.com/image/PHOTO.JPG"
        )
        assert dest.suffix == ".jpg"
        assert local.endswith(".jpg")

    def test_album_original_path_is_separate_from_preview(self, cfg) -> None:
        """原图与预览图同在``{photoId}``命名下，必须落在不同目录才不会互相覆盖。"""
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        url = "https://img1.doubanio.com/view/photo/raw/public/p2770778841.jpg"
        dest, local = archive.album_original_path("13432051", "2770778841", url)
        assert dest == cfg.media_dir / "albums" / "13432051" / "original" / "2770778841.jpg"
        assert local == "/media/albums/13432051/original/2770778841.jpg"


class TestFindAlbumFile:
    """磁盘查找：预览图与原图各自只在自己的目录里找。"""

    def _archive(self, cfg) -> MediaArchive:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        return archive

    def _write(self, path: Path, blob: bytes = b"\xff\xd8\xff\xe0" + b"0" * 20) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)

    def test_preview_prefers_webp_when_both_suffixes_present(self, cfg) -> None:
        """回归：早期归档留下过同名 ``.jpg``，网格该显示体积更小的 webp。"""
        album_dir = cfg.media_dir / "albums" / "13432051"
        self._write(album_dir / "2770778841.jpg")
        self._write(album_dir / "2770778841.webp")
        found = self._archive(cfg).find_album_image("13432051", "2770778841")
        assert found is not None
        assert found[1] == "/media/albums/13432051/2770778841.webp"

    def test_preview_falls_back_to_other_suffix(self, cfg) -> None:
        self._write(cfg.media_dir / "albums" / "13432051" / "2770778841.jpg")
        found = self._archive(cfg).find_album_image("13432051", "2770778841")
        assert found is not None
        assert found[1] == "/media/albums/13432051/2770778841.jpg"

    def test_preview_missing(self, cfg) -> None:
        self._write(cfg.media_dir / "albums" / "13432051" / "2770778842.webp")
        assert self._archive(cfg).find_album_image("13432051", "2770778841") is None

    def test_original_not_confused_with_preview(self, cfg) -> None:
        """只有预览图时，原图查找必须返回"没有" —— 否则页面会把 webp 当原图。"""
        self._write(cfg.media_dir / "albums" / "13432051" / "2770778841.webp")
        assert self._archive(cfg).find_album_original("13432051", "2770778841") is None

    def test_original_found_in_subdir(self, cfg) -> None:
        self._write(cfg.media_dir / "albums" / "13432051" / "original" / "2770778841.jpg")
        found = self._archive(cfg).find_album_original("13432051", "2770778841")
        assert found is not None
        assert found[1] == "/media/albums/13432051/original/2770778841.jpg"


class TestDropRedundantOriginal:
    """原图与预览字节相同时只留一份。

    豆瓣的 ``large`` 与 ``raw`` 对同一张图常常返回同一份字节，抓两遍存两份
    不多任何信息 —— 但判别只能靠比字节：既有预览比原图大的，也有原图确实
    更大的，尺寸不足以作准。
    """

    def _archive(self, cfg) -> MediaArchive:
        archive = MediaArchive.__new__(MediaArchive)
        archive.cfg = cfg
        return archive

    def _write(self, path: Path, blob: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        return path

    def test_identical_original_is_dropped(self, cfg) -> None:
        album_dir = cfg.media_dir / "albums" / "13433748"
        preview = self._write(album_dir / "2314125077.jpg", JPEG)
        original = self._write(album_dir / "original" / "2314125077.jpg", JPEG)

        assert self._archive(cfg).drop_redundant_original("13433748", "2314125077") is True
        assert not original.exists()
        assert preview.read_bytes() == JPEG

    def test_different_original_is_kept(self, cfg) -> None:
        """原图真的更大时必须留着 —— 这是 183 份原图的场景。"""
        album_dir = cfg.media_dir / "albums" / "13432051"
        self._write(album_dir / "2770778841.webp", WEBP)
        original = self._write(album_dir / "original" / "2770778841.jpg", JPEG)

        assert self._archive(cfg).drop_redundant_original("13432051", "2770778841") is False
        assert original.exists()

    def test_sole_original_is_never_dropped(self, cfg) -> None:
        """只有原图没有预览时它就是唯一的一份，删了图就没了。

        ``local`` 会回退指向 ``original/``，线上确实存在这种照片
        （``13431950/2325379527``）。
        """
        original = self._write(
            cfg.media_dir / "albums" / "13431950" / "original" / "2325379527.jpg", JPEG
        )

        assert self._archive(cfg).drop_redundant_original("13431950", "2325379527") is False
        assert original.exists()

    def test_missing_files_are_noop(self, cfg) -> None:
        assert self._archive(cfg).drop_redundant_original("13431373", "1") is False

    def test_real_webp_preview_wins_over_matching_jpg(self, cfg) -> None:
        """根目录同时有真 webp 预览与同字节的 jpg 时，以 webp 为准，原图留着。

        ``find_album_image`` 按 :data:`PREVIEW_SUFFIX_ORDER` 优先取 webp ——
        它才是网格里显示的那张，与它比对才算数。
        """
        album_dir = cfg.media_dir / "albums" / "190597061"
        self._write(album_dir / "2459298089.webp", WEBP)
        self._write(album_dir / "2459298089.jpg", JPEG)
        original = self._write(album_dir / "original" / "2459298089.jpg", JPEG)

        assert self._archive(cfg).drop_redundant_original("190597061", "2459298089") is False
        assert original.exists()


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


RAW_URL = "https://img2.doubanio.com/view/photo/raw/public/p2500516321.jpg"
LARGE_URL = "https://img2.doubanio.com/view/photo/large/public/p2500516321.jpg"


class _ScriptedTransport:
    """按脚本返回响应（或抛异常）的假传输层，并记录被丢弃的缓存条目。"""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.invalidated: list[str] = []
        self.calls: list[str] = []

    def get_image(self, url: str) -> CachedResponse:
        self.calls.append(url)
        outcome = self.responses[url]
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, CachedResponse)
        return outcome

    def invalidate_cache(self, url: str) -> bool:
        self.invalidated.append(url)
        return True


def _response(
    url: str,
    status: int,
    content: bytes = b"",
    content_type: str = "text/html; charset=utf-8",
    *,
    from_cache: bool = False,
    fetched_at: str = "",
) -> CachedResponse:
    return CachedResponse(
        url=url,
        status=status,
        content=content,
        content_type=content_type,
        from_cache=from_cache,
        fetched_at=fetched_at,
    )


class TestFailureDiagnostics:
    """失败信息必须带错误码。

    线上遇到过的怪事：日志里只有"返回内容不是图片（0B，疑似错误页）"，
    既没有状态码也没有内容类型，只能手工重放请求才知道那是 **404**
    —— 一个不存在的 ``raw`` 尺寸。状态码是排查的第一要素，不能省。
    """

    def test_non_image_message_carries_status(self, cfg) -> None:
        transport = _ScriptedTransport({RAW_URL: _response(RAW_URL, 404)})
        archive = MediaArchive(transport, cfg=cfg)

        result = archive.download(
            RAW_URL, cfg.media_dir / "albums" / "1" / "p.jpg", "/media/albums/1/p.jpg"
        )

        assert not result.ok
        assert "HTTP 404" in result.error
        assert "text/html" in result.error
        assert "0B" in result.error
        assert RAW_URL in result.error

    def test_error_lists_every_candidate_with_its_code(self, cfg) -> None:
        """多个候选都失败时，每个候选各自的状态码都要在，才能看出差在哪。"""
        urls = album_original_variants(RAW_URL)
        responses: dict[str, object] = {
            url: _response(url, 404) for url in urls
        }
        archive = MediaArchive(_ScriptedTransport(responses), cfg=cfg, wayback=None)
        archive.wayback.enabled = False

        result = archive.download(
            RAW_URL,
            cfg.media_dir / "albums" / "1" / "p.jpg",
            "/media/albums/1/p.jpg",
            variants=urls,
        )

        assert not result.ok
        for url in urls:
            assert url in result.error
        assert result.error.count("HTTP 404") == len(urls)

    def test_blocked_error_reports_418(self, cfg) -> None:
        from scraper.http_client import BlockedError

        transport = _ScriptedTransport({RAW_URL: BlockedError(RAW_URL, "源站拒绝访问", 418)})
        archive = MediaArchive(transport, cfg=cfg)
        result = archive.download(
            RAW_URL,
            cfg.media_dir / "albums" / "1" / "p.jpg",
            "/media/albums/1/p.jpg",
            variants=[RAW_URL],
        )
        assert not result.ok
        assert "HTTP 418" in result.error

    def test_circuit_breaker_bubbles_without_trying_more_candidates(self, cfg) -> None:
        from scraper.http_client import CircuitBreakerOpen

        breaker = CircuitBreakerOpen(RAW_URL, "熔断", 403)
        transport = _ScriptedTransport(
            {RAW_URL: breaker, LARGE_URL: _response(LARGE_URL, 200, JPEG)}
        )
        archive = MediaArchive(transport, cfg=cfg, wayback=None)
        with pytest.raises(CircuitBreakerOpen):
            archive.download(
                RAW_URL,
                cfg.media_dir / "albums" / "1" / "p.jpg",
                "/media/albums/1/p.jpg",
                variants=[RAW_URL, LARGE_URL],
            )
        assert transport.calls == [RAW_URL]

    def test_intermediate_failure_is_info_not_warning(self, cfg, caplog) -> None:
        """某个候选不存在是预期内的：回退成功后不该留下 WARNING。"""
        import logging

        transport = _ScriptedTransport(
            {
                RAW_URL: _response(RAW_URL, 404),
                LARGE_URL: _response(LARGE_URL, 200, JPEG, "image/jpeg"),
            }
        )
        archive = MediaArchive(transport, cfg=cfg)

        with caplog.at_level(logging.INFO, logger="usagi.media"):
            result = archive.download(
                RAW_URL,
                cfg.media_dir / "albums" / "1" / "p.jpg",
                "/media/albums/1/p.jpg",
                variants=[RAW_URL, LARGE_URL],
            )

        assert result.ok, result.error
        assert result.url == LARGE_URL
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("HTTP 404" in r.getMessage() for r in caplog.records)

    def test_final_failure_is_warning_with_codes(self, cfg, caplog) -> None:
        import logging

        archive = MediaArchive(
            _ScriptedTransport({RAW_URL: _response(RAW_URL, 404)}), cfg=cfg
        )
        with caplog.at_level(logging.WARNING, logger="usagi.media"):
            archive.download(
                RAW_URL,
                cfg.media_dir / "albums" / "1" / "p.jpg",
                "/media/albums/1/p.jpg",
                variants=[RAW_URL],
            )
        warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "HTTP 404" in warnings[0]

    def test_cached_2xx_non_image_is_dropped(self, cfg) -> None:
        """把错误页当成图片缓存下来的条目要当场丢弃，否则每次运行都重放它。"""
        bad = _response(
            LARGE_URL, 200, HTML_ERROR, "text/html", from_cache=True, fetched_at="2026-09-14T20:32:45+08:00"
        )
        transport = _ScriptedTransport({LARGE_URL: bad})
        archive = MediaArchive(transport, cfg=cfg)

        result = archive.download(
            LARGE_URL,
            cfg.media_dir / "albums" / "1" / "p.jpg",
            "/media/albums/1/p.jpg",
            variants=[LARGE_URL],
        )

        assert not result.ok
        assert transport.invalidated == [LARGE_URL]
        assert "来自缓存" in result.error

    def test_cached_404_is_not_dropped(self, cfg) -> None:
        """404 是确定性结论（候选确实不存在），留着它下次就不用再问一遍。"""
        transport = _ScriptedTransport({RAW_URL: _response(RAW_URL, 404, from_cache=True)})
        archive = MediaArchive(transport, cfg=cfg)

        archive.download(
            RAW_URL,
            cfg.media_dir / "albums" / "1" / "p.jpg",
            "/media/albums/1/p.jpg",
            variants=[RAW_URL],
        )

        assert transport.invalidated == []

    def test_describe_response_marks_source(self) -> None:
        from scraper.media import describe_response

        fresh = _response(RAW_URL, 404)
        assert "本次网络请求" in describe_response(fresh)

        cached = _response(RAW_URL, 404, from_cache=True, fetched_at="2026-09-14T20:32:45+08:00")
        text = describe_response(cached)
        assert "来自缓存" in text and "2026-09-14T20:32:45+08:00" in text

    def test_describe_non_image_distinguishes_missing_from_error(self) -> None:
        from scraper.media import describe_non_image

        assert "源站无此尺寸" in describe_non_image(_response(RAW_URL, 404))
        assert "疑似错误页" in describe_non_image(_response(RAW_URL, 200, HTML_ERROR, "text/html"))
        assert "源站拒绝" in describe_non_image(_response(RAW_URL, 451))


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


class TestSuffixFollowsContent:
    """落盘后缀由**内容**决定，不由 URL 后缀决定。

    豆瓣的 ``/view/photo/large/public/p{id}.webp`` 会返回 ``Content-Type: image/webp``
    而 body 是 JPEG 字节（``raw`` 尺寸那份原封不动），偶尔是 PNG。照 URL 后缀命名就会
    落下"后缀说 webp、内容是 JPEG"的假文件。这里把"名字只认内容"钉死。
    """

    class _StubTransport:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload
            self.calls: list[str] = []

        def get_image(self, url: str) -> CachedResponse:
            self.calls.append(url)
            return CachedResponse(url=url, status=200, content=self.payload)

    def test_webp_url_holding_jpeg_is_stored_as_jpg(self, cfg) -> None:
        transport = self._StubTransport(JPEG)
        archive = MediaArchive(transport, cfg=cfg)
        dest = cfg.media_dir / "albums" / "1" / "p1.webp"
        url = "https://img1.doubanio.com/view/photo/large/public/p1.webp"

        result = archive.download(url, dest, "/media/albums/1/p1.webp")

        assert result.ok, result.error
        assert result.local_path == dest.with_suffix(".jpg")
        assert result.local_url == "/media/albums/1/p1.jpg"
        assert result.kind == "jpeg"
        assert (dest.parent / "p1.jpg").exists()
        assert not dest.exists()

    def test_webp_url_holding_png_is_stored_as_png(self, cfg) -> None:
        archive = MediaArchive(self._StubTransport(PNG), cfg=cfg)
        dest = cfg.media_dir / "albums" / "1" / "p2.webp"

        result = archive.download(
            "https://img1.doubanio.com/view/photo/large/public/p2.webp",
            dest,
            "/media/albums/1/p2.webp",
        )

        assert result.ok, result.error
        assert result.local_url == "/media/albums/1/p2.png"
        assert (dest.parent / "p2.png").exists()

    def test_truthful_suffix_is_left_alone(self, cfg) -> None:
        """后缀本来就对时不该改名，也不该凭空多出文件。"""
        archive = MediaArchive(self._StubTransport(WEBP), cfg=cfg)
        dest = cfg.media_dir / "albums" / "1" / "p3.webp"

        result = archive.download(
            "https://img1.doubanio.com/view/photo/large/public/p3.webp",
            dest,
            "/media/albums/1/p3.webp",
        )

        assert result.ok, result.error
        assert result.local_url == "/media/albums/1/p3.webp"
        assert [p.name for p in dest.parent.iterdir()] == ["p3.webp"]

    def test_unrecognized_suffix_is_replaced_with_detected_image_suffix(self, cfg) -> None:
        archive = MediaArchive(self._StubTransport(JPEG), cfg=cfg)
        dest = cfg.media_dir / "external-articles" / "1" / "pixel.unknown"

        result = archive.download(
            "https://example.com/pixel.unknown",
            dest,
            "/media/external-articles/1/pixel.unknown",
        )

        assert result.ok, result.error
        assert result.local_url == "/media/external-articles/1/pixel.jpg"
        assert (dest.parent / "pixel.jpg").is_file()

    def test_existing_wrong_suffix_is_healed_without_refetch(self, cfg) -> None:
        """存量假后缀：下次 sync 时就地改名，且不该为它再发一次请求。"""
        dest = cfg.media_dir / "albums" / "1" / "p4.webp"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(JPEG)
        transport = self._StubTransport(JPEG)
        archive = MediaArchive(transport, cfg=cfg)

        result = archive.download(
            "https://img1.doubanio.com/view/photo/large/public/p4.webp",
            dest,
            "/media/albums/1/p4.webp",
        )

        assert result.ok, result.error
        assert result.from_cache
        assert transport.calls == []
        assert result.local_path == dest.with_suffix(".jpg")
        assert result.local_url == "/media/albums/1/p4.jpg"
        assert not dest.exists()
        assert (dest.parent / "p4.jpg").read_bytes() == JPEG

    def test_already_corrected_file_is_not_downloaded_again(self, cfg) -> None:
        """纠正过一次之后，再跑不能因为 URL 后缀不符就把文件当成"没下过"。"""
        corrected = cfg.media_dir / "albums" / "1" / "p5.jpg"
        corrected.parent.mkdir(parents=True, exist_ok=True)
        corrected.write_bytes(JPEG)
        transport = self._StubTransport(JPEG)
        archive = MediaArchive(transport, cfg=cfg)

        result = archive.download(
            "https://img1.doubanio.com/view/photo/large/public/p5.webp",
            cfg.media_dir / "albums" / "1" / "p5.webp",
            "/media/albums/1/p5.webp",
        )

        assert result.ok, result.error
        assert result.from_cache
        assert transport.calls == []
        assert result.local_url == "/media/albums/1/p5.jpg"

    def test_heal_never_clobbers_a_different_file(self, cfg, caplog) -> None:
        """同目录已有同名但**内容不同**的文件时保持原样 + WARNING，绝不能覆盖。"""
        import logging

        victim = cfg.media_dir / "albums" / "1" / "p6.jpg"
        victim.parent.mkdir(parents=True, exist_ok=True)
        other = b"\xff\xd8\xff\xe0" + b"\x11" * 40
        victim.write_bytes(other)
        wrong = cfg.media_dir / "albums" / "1" / "p6.webp"
        wrong.write_bytes(JPEG)
        archive = MediaArchive(self._StubTransport(JPEG), cfg=cfg)

        with caplog.at_level(logging.WARNING, logger="usagi.media"):
            result = archive.download(
                "https://img1.doubanio.com/view/photo/large/public/p6.webp",
                wrong,
                "/media/albums/1/p6.webp",
            )

        assert victim.read_bytes() == other, "已有文件被覆盖了"
        assert wrong.exists()
        assert result.ok
        assert any("已被占用" in r.getMessage() for r in caplog.records)

    def test_note_image_map_uses_corrected_url(self, cfg) -> None:
        """日记配图重写 Markdown 用的是纠正后的站内 URL。"""
        archive = MediaArchive(self._StubTransport(JPEG), cfg=cfg)
        url = "https://img1.doubanio.com/view/note/large/public/p7.webp"
        refs = archive.collect_note_images(f'<img src="{url}">', "123")

        mapping = archive.archive_note_images(refs, "123")

        assert mapping == {url: "/media/notes/123/p7.jpg"}
        assert refs[0].local == "/media/notes/123/p7.jpg"


@pytest.mark.parametrize('suffix', ['.html', '.php'])
def test_gif_dynamic_endpoint_uses_true_suffix_and_reuses_existing(cfg, suffix):
    transport = TestSuffixFollowsContent._StubTransport(GIF)
    media = MediaArchive(transport, cfg=cfg)
    dest, local = media.external_article_image_path('example.com', 'post', 'https://example.com/counter' + suffix)
    first = media.download('https://example.com/counter' + suffix, dest, local)
    assert first.ok and first.local_path.suffix == '.gif'
    assert first.local_url.endswith('.gif')
    calls = len(transport.calls)
    second = media.download('https://example.com/counter' + suffix, dest, local)
    assert second.ok and second.from_cache and second.local_url == first.local_url
    assert len(transport.calls) == calls


def test_suffix_heal_reuses_identical_canonical_file(cfg):
    directory = cfg.media_dir / 'external-articles'
    directory.mkdir(parents=True)
    wrong = directory / 'counter.html'
    right = directory / 'counter.gif'
    wrong.write_bytes(GIF)
    right.write_bytes(GIF)
    assert MediaArchive(None, cfg=cfg).heal_suffix(wrong) == right
    assert not wrong.exists() and right.read_bytes() == GIF
