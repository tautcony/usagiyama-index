"""归档校验逻辑的测试。

重点覆盖 ``_markdown_body``：它曾经因为"先转纯文本再剥 frontmatter"
而把 ``title: ...`` 等元数据当成正文，把相似度从 1.000 错压到 0.673。
"""

from __future__ import annotations

from pathlib import Path

from scraper.verify import Verifier

NOTE_MD = '''---
title: "测试标题"
date: "2016-08-11 21:06:31"
noteId: "575615184"
source: "https://site.douban.com/211330/widget/notes/1/note/575615184/"
---

正文第一段。

正文第二段。

*本页归档自 [原站页面](https://site.douban.com/211330/widget/notes/1/note/575615184/)*
'''

NOTE_MD_WITH_NOTICE = '''---
title: "缺失的页面"
noteId: "999"
---

::: warning 原站不可访问
该页面需要登录豆瓣才能访问，无法直接归档。
:::

残留的正文。

*本页归档自 [原站页面](https://x/)*
'''


class TestMarkdownBody:
    def test_strips_frontmatter(self, cfg, tmp_path: Path) -> None:
        path = tmp_path / "a.md"
        path.write_text(NOTE_MD, encoding="utf-8")
        body = Verifier(cfg)._markdown_body(path)
        assert "title:" not in body
        assert "noteId:" not in body
        assert "正文第一段" in body

    def test_strips_footer(self, cfg, tmp_path: Path) -> None:
        path = tmp_path / "a.md"
        path.write_text(NOTE_MD, encoding="utf-8")
        body = Verifier(cfg)._markdown_body(path)
        assert "本页归档自" not in body

    def test_strips_notice_block(self, cfg, tmp_path: Path) -> None:
        path = tmp_path / "b.md"
        path.write_text(NOTE_MD_WITH_NOTICE, encoding="utf-8")
        body = Verifier(cfg)._markdown_body(path)
        assert ":::" not in body
        assert "需要登录" not in body
        assert "残留的正文" in body

    def test_keeps_horizontal_rule_in_body(self, cfg, tmp_path: Path) -> None:
        """正文里的 --- 是分隔线，不能被当成 frontmatter 边界。"""
        content = "---\ntitle: \"t\"\n---\n\n上半部分\n\n---\n\n下半部分\n"
        path = tmp_path / "c.md"
        path.write_text(content, encoding="utf-8")
        body = Verifier(cfg)._markdown_body(path)
        assert "上半部分" in body
        assert "下半部分" in body

    def test_does_not_leak_metadata_into_plain_text(self, cfg, tmp_path: Path) -> None:
        """回归：元数据绝不能进入用于比对的纯文本。"""
        from scraper.html2md import markdown_to_plain_text

        path = tmp_path / "a.md"
        path.write_text(NOTE_MD, encoding="utf-8")
        text = markdown_to_plain_text(Verifier(cfg)._markdown_body(path))
        assert "575615184" not in text
        assert "2016-08-11" not in text
        assert "正文第一段" in text


class TestResolveRoute:
    def test_note_route(self, cfg) -> None:
        (cfg.docs_dir / "notes").mkdir(parents=True, exist_ok=True)
        target = cfg.docs_dir / "notes" / "123.md"
        target.write_text("x", encoding="utf-8")
        assert Verifier(cfg)._resolve_route("/notes/123") == target

    def test_media_route(self, cfg) -> None:
        resolved = Verifier(cfg)._resolve_route("/media/notes/1/p.jpg")
        assert resolved == cfg.docs_dir / "public" / "media" / "notes" / "1" / "p.jpg"

    def test_index_route(self, cfg) -> None:
        (cfg.docs_dir / "notes").mkdir(parents=True, exist_ok=True)
        target = cfg.docs_dir / "notes" / "index.md"
        target.write_text("x", encoding="utf-8")
        assert Verifier(cfg)._resolve_route("/notes/") == target

    def test_external_route_ignored(self, cfg) -> None:
        assert Verifier(cfg)._resolve_route("https://example.com/a") is None
        assert Verifier(cfg)._resolve_route("mailto:a@b.c") is None
        assert Verifier(cfg)._resolve_route("#anchor") is None

    def test_anchor_and_query_stripped(self, cfg) -> None:
        (cfg.docs_dir / "notes").mkdir(parents=True, exist_ok=True)
        (cfg.docs_dir / "notes" / "5.md").write_text("x", encoding="utf-8")
        assert Verifier(cfg)._resolve_route("/notes/5#comments") == cfg.docs_dir / "notes" / "5.md"
        assert Verifier(cfg)._resolve_route("/notes/5?x=1") == cfg.docs_dir / "notes" / "5.md"


class TestCheckLinks:
    def test_detects_missing_link(self, cfg) -> None:
        (cfg.docs_dir / "notes").mkdir(parents=True, exist_ok=True)
        (cfg.docs_dir / "notes" / "a.md").write_text(
            "---\ntitle: \"a\"\nsource: \"u\"\n---\n\n[坏链](/notes/nope)\n", encoding="utf-8"
        )
        result = Verifier(cfg).check_links()
        assert not result.passed
        assert any("nope" in problem for problem in result.problems)

    def test_passes_when_targets_exist(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text(
            '---\ntitle: "a"\nsource: "u"\n---\n\n[好链](/notes/b)\n', encoding="utf-8"
        )
        (notes / "b.md").write_text(
            '---\ntitle: "b"\nsource: "u"\n---\n\n正文\n', encoding="utf-8"
        )
        assert Verifier(cfg).check_links().passed

    def test_ignores_external_links(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text(
            '---\ntitle: "a"\nsource: "u"\n---\n\n[外链](https://example.com/x)\n',
            encoding="utf-8",
        )
        assert Verifier(cfg).check_links().passed


class TestCheckImages:
    def test_detects_html_error_page(self, cfg) -> None:
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "bad.jpg").write_bytes(b"<html><body>418</body></html>" + b" " * 100)
        result = Verifier(cfg).check_images()
        assert not result.passed
        assert any("疑似 HTML 错误页" in problem for problem in result.problems)

    def test_detects_tiny_file(self, cfg) -> None:
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "tiny.jpg").write_bytes(b"\xff\xd8\xff")
        result = Verifier(cfg).check_images()
        assert not result.passed

    def test_passes_for_valid_jpeg(self, cfg) -> None:
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "ok.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200)
        assert Verifier(cfg).check_images().passed


class TestCheckMediaFormats:
    """后缀与内容不符（CDN 拿 .webp 的 URL 发 JPEG 字节）要被抓出来。"""

    def test_detects_jpeg_hiding_behind_webp(self, cfg) -> None:
        media = cfg.media_dir / "albums" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "p1.webp").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200)
        result = Verifier(cfg).check_media_formats()
        assert not result.passed
        assert any("实际是 jpeg" in problem for problem in result.problems)
        assert any("后缀与真实格式不符" in note for note in result.notes)

    def test_detects_png_hiding_behind_webp(self, cfg) -> None:
        media = cfg.media_dir / "albums" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "p2.webp").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        result = Verifier(cfg).check_media_formats()
        assert not result.passed
        assert any("实际是 png" in problem for problem in result.problems)

    def test_passes_when_suffix_matches_content(self, cfg) -> None:
        media = cfg.media_dir / "albums" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200)
        (media / "b.webp").write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 200)
        result = Verifier(cfg).check_media_formats()
        assert result.passed
        assert result.checked == 2
        assert any("后缀与内容一致" in note for note in result.notes)

    def test_non_image_is_left_to_integrity_check(self, cfg) -> None:
        """不是图片的文件由「图片完整性」报，格式检查不重复刷问题。"""
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "bad.jpg").write_bytes(b"<html><body>418</body></html>" + b" " * 100)
        result = Verifier(cfg).check_media_formats()
        assert result.passed
        assert result.problems == []

    def test_missing_media_dir_passes(self, cfg) -> None:
        assert Verifier(cfg).check_media_formats().passed


class TestCheckDuplicates:
    def test_detects_duplicate_content(self, cfg) -> None:
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        (media / "a.jpg").write_bytes(data)
        (media / "b.jpg").write_bytes(data)
        result = Verifier(cfg).check_duplicate_images()
        assert any("重复" in note for note in result.notes)

    def test_unique_images_pass(self, cfg) -> None:
        media = cfg.media_dir / "notes" / "1"
        media.mkdir(parents=True, exist_ok=True)
        (media / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200)
        (media / "b.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x01" * 200)
        result = Verifier(cfg).check_duplicate_images()
        assert any("没有重复图片" in note for note in result.notes)


class TestCheckFrontmatter:
    def test_detects_missing_field(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text('---\ntitle: "a"\n---\n\n正文\n', encoding="utf-8")
        result = Verifier(cfg).check_frontmatter()
        assert not result.passed
        assert any("source" in problem for problem in result.problems)

    def test_detects_missing_note_id(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text(
            '---\ntitle: "a"\nsource: "u"\n---\n\n正文\n', encoding="utf-8"
        )
        result = Verifier(cfg).check_frontmatter()
        assert not result.passed
        assert any("noteId" in problem for problem in result.problems)

    def test_valid_note_passes(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text(
            '---\ntitle: "a"\nsource: "u"\nnoteId: "1"\n---\n\n正文\n', encoding="utf-8"
        )
        assert Verifier(cfg).check_frontmatter().passed

    def test_missing_frontmatter_detected(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text("没有 frontmatter\n", encoding="utf-8")
        result = Verifier(cfg).check_frontmatter()
        assert not result.passed
        assert any("缺少 frontmatter" in problem for problem in result.problems)


class TestReport:
    def test_report_text_lists_checks(self, cfg) -> None:
        verifier = Verifier(cfg)
        verifier.run(sample=0)
        text = verifier.report_text()
        assert "归档校验报告" in text
        assert "数量对账" in text
        assert "断链检查" in text

    def test_report_written_to_disk(self, cfg) -> None:
        verifier = Verifier(cfg)
        verifier.run(sample=0)
        assert (cfg.data_dir / "verify-report.md").exists()
