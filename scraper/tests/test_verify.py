"""归档校验逻辑的测试。

重点覆盖 ``_markdown_body``：它曾经因为"先转纯文本再剥 frontmatter"
而把 ``title: ...`` 等元数据当成正文，把相似度从 1.000 错压到 0.673。

内容抽查另有一条同等重要的口径：评论在页面里位于 ``#comments``，不在正文
容器 ``#link-report`` 里，而 md 侧带评论区块。只比正文会让 md 凭空多出一大
段评论，把带评论的日记全部误判成"相似度低"（实测最低 0.594）。
"""

from __future__ import annotations

import json
from pathlib import Path

from scraper.http_client import cache_paths
from scraper.models import Comment
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
    def test_missing_fragment_is_reported(self, cfg) -> None:
        guide = cfg.docs_dir / "guide"
        guide.mkdir(parents=True, exist_ok=True)
        (guide / "a.md").write_text("[同页坏锚点](#不存在)\n", encoding="utf-8")
        result = Verifier(cfg).check_links()
        assert not result.passed
        assert any("没有锚点" in problem for problem in result.problems)

    def test_heading_fragment_uses_vitepress_slug_and_duplicate_suffix(self, cfg) -> None:
        guide = cfg.docs_dir / "guide"
        guide.mkdir(parents=True, exist_ok=True)
        (guide / "a.md").write_text(
            "# École déjà!\n\n# École déjà!\n\n[second](#ecole-deja-1)\n", encoding="utf-8"
        )
        assert Verifier(cfg).check_links().passed

    def test_relative_heading_fragment_checks_target_page(self, cfg) -> None:
        guide = cfg.docs_dir / "guide"
        guide.mkdir(parents=True, exist_ok=True)
        (guide / "a.md").write_text("[target](../notes/target.md#section)\n", encoding="utf-8")
        (cfg.docs_dir / "notes").mkdir()
        (cfg.docs_dir / "notes" / "target.md").write_text("# Section\n", encoding="utf-8")
        assert Verifier(cfg).check_links().passed

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

    def test_md_extension_is_not_appended_twice(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text("[b](/notes/b.md)", encoding="utf-8")
        (notes / "b.md").write_text("b", encoding="utf-8")
        assert Verifier(cfg).check_links().passed

    def test_relative_link_uses_source_directory(self, cfg) -> None:
        deep = cfg.docs_dir / "guide" / "deep"
        deep.mkdir(parents=True, exist_ok=True)
        (deep / "a.md").write_text("[b](../b.md)", encoding="utf-8")
        (cfg.docs_dir / "guide" / "b.md").write_text("b", encoding="utf-8")
        assert Verifier(cfg).check_links().passed

    def test_missing_relative_link_is_detected(self, cfg) -> None:
        guide = cfg.docs_dir / "guide"
        guide.mkdir(parents=True, exist_ok=True)
        (guide / "a.md").write_text("[missing](./missing)", encoding="utf-8")
        (cfg.docs_dir / "missing.md").write_text("wrong base", encoding="utf-8")
        result = Verifier(cfg).check_links()
        assert not result.passed
        assert any("missing" in problem for problem in result.problems)


class TestCheckCounts:
    def test_healthy_notes_data_ignores_meta_record(self, cfg) -> None:
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        cfg.notes_dir.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(
            json.dumps({"counts": {"notes": 1}, "notes": {"1": {"comments": []}}}),
            encoding="utf-8",
        )
        (cfg.data_dir / "notes.json").write_text(
            json.dumps({"_meta": {"updatedAt": "now"}, "1": {}}), encoding="utf-8"
        )
        (cfg.notes_dir / "1.md").write_text(NOTE_MD, encoding="utf-8")
        result = Verifier(cfg).check_counts()
        assert result.passed

    def test_missing_note_page_is_detected(self, cfg) -> None:
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(
            json.dumps({"counts": {"notes": 1}, "notes": {"1": {}}}),
            encoding="utf-8",
        )
        (cfg.data_dir / "notes.json").write_text(json.dumps({"1": {}}), encoding="utf-8")
        result = Verifier(cfg).check_counts()
        assert not result.passed
        assert any("缺少 md 文件" in problem for problem in result.problems)

    def test_stale_album_and_external_pages_are_detected(self, cfg) -> None:
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(
            json.dumps({"notes": {}, "albums": {}, "external": {}}), encoding="utf-8"
        )
        (cfg.albums_dir).mkdir(parents=True, exist_ok=True)
        (cfg.docs_dir / "external").mkdir(parents=True, exist_ok=True)
        (cfg.albums_dir / "old-album.md").write_text("stale", encoding="utf-8")
        (cfg.docs_dir / "external" / "old-page.md").write_text("stale", encoding="utf-8")
        result = Verifier(cfg).check_counts()
        assert not result.passed
        assert any("albums 有 1 个过期页面" in problem for problem in result.problems)
        assert any("external 有 1 个过期页面" in problem for problem in result.problems)

    def test_ignores_external_links(self, cfg) -> None:
        notes = cfg.docs_dir / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "a.md").write_text(
            '---\ntitle: "a"\nsource: "u"\n---\n\n[外链](https://example.com/x)\n',
            encoding="utf-8",
        )
        assert Verifier(cfg).check_links().passed


class TestCheckImages:
    def test_dotfiles_are_ignored(self, cfg) -> None:
        media = cfg.media_dir / "albums"
        media.mkdir(parents=True, exist_ok=True)
        (media / ".DS_Store").write_bytes(b"mac metadata")
        result = Verifier(cfg).check_images()
        assert result.passed
        assert result.checked == 0

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

    def test_dotfiles_are_ignored(self, cfg) -> None:
        media = cfg.media_dir / "albums"
        media.mkdir(parents=True, exist_ok=True)
        (media / ".DS_Store").write_bytes(b"metadata")
        result = Verifier(cfg).check_media_formats()
        assert result.passed
        assert result.checked == 0


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

    def test_dotfiles_are_ignored(self, cfg) -> None:
        media = cfg.media_dir / "albums"
        media.mkdir(parents=True, exist_ok=True)
        (media / ".DS_Store").write_bytes(b"metadata")
        result = Verifier(cfg).check_duplicate_images()
        assert result.checked == 0


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


NOTE_WITH_COMMENTS = '''---
title: "带评论的日记"
noteId: "575615184"
source: "https://site.douban.com/211330/widget/notes/1/note/575615184/"
---

正文第一段。

## 评论（2）

**甲 · 2016-08-12 10:00:00**

> 第一条评论

**乙 · 2016-08-13 11:00:00**

> 第二条评论

*本页归档自 [原站页面](https://site.douban.com/211330/widget/notes/1/note/575615184/)*
'''

#: 详情页缓存：正文在 #link-report，评论在兄弟节点 #comments
NOTE_HTML = '''<html><body>
<div id="link-report">正文第一段。</div>
<div id="comments">
  <div class="comment-item" data-cid="c1">
    <div class="pic"><img src="a.jpg"></div>
    <div class="content">
      <div class="author"><a href="/people/x/">甲</a> 2016-08-12 10:00:00</div>
      <p>第一条评论</p>
    </div>
  </div>
  <div class="comment-item" data-cid="c2">
    <div class="content">
      <div class="author"><a href="/people/y/">乙</a> 2016-08-13 11:00:00</div>
      <p>第二条评论</p>
    </div>
  </div>
</div>
</body></html>'''


class TestMarkdownParts:
    def test_splits_comments_off(self, cfg, tmp_path: Path) -> None:
        path = tmp_path / "a.md"
        path.write_text(NOTE_WITH_COMMENTS, encoding="utf-8")
        body, comments = Verifier(cfg)._markdown_parts(path)
        assert "正文第一段" in body
        assert "第一条评论" not in body
        assert "第一条评论" in comments

    def test_heading_is_excluded_from_both_sides(self, cfg, tmp_path: Path) -> None:
        """标题是 emit 生成的脚手架，原文没有对应物，不该参与比对。"""
        path = tmp_path / "a.md"
        path.write_text(NOTE_WITH_COMMENTS, encoding="utf-8")
        _, comments = Verifier(cfg)._markdown_parts(path)
        assert "评论（2）" not in comments

    def test_note_without_comments(self, cfg, tmp_path: Path) -> None:
        path = tmp_path / "a.md"
        path.write_text(NOTE_MD, encoding="utf-8")
        body, comments = Verifier(cfg)._markdown_parts(path)
        assert "正文第一段" in body
        assert comments == ""


class TestCommentText:
    def test_matches_emit_field_order(self, cfg) -> None:
        text = Verifier(cfg)._comment_text(
            [Comment(author="甲", date="2016-08-12 10:00:00", content_html="<p>第一条评论</p>")]
        )
        assert text == "甲 · 2016-08-12 10:00:00 第一条评论"

    def test_fallbacks_match_emit(self, cfg) -> None:
        """无作者写匿名、无正文写（空），否则每次比对都凭空多出差异。"""
        assert Verifier(cfg)._comment_text([Comment(content_html="<p>x</p>")]).startswith("匿名")
        assert Verifier(cfg)._comment_text([Comment(author="甲")]).endswith("（空）")


class TestContentSample:
    """评论必须在两侧都参与比对。"""

    def _prepare(self, cfg, md_text: str, note_id: str = "575615184"):
        cfg.notes_dir.mkdir(parents=True, exist_ok=True)
        (cfg.notes_dir / f"{note_id}.md").write_text(md_text, encoding="utf-8")

        widget_id = "1"
        manifest = {
            "notes": {
                note_id: {
                    "title": "带评论的日记",
                    "widget_id": widget_id,
                    "content_html": "<p>正文第一段。</p>",
                    "status": {"availability": "ok"},
                }
            }
        }
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        body, meta = cache_paths(cfg, cfg.note_url(widget_id, note_id))
        body.parent.mkdir(parents=True, exist_ok=True)
        body.write_text(NOTE_HTML, encoding="utf-8")
        meta.write_text(json.dumps({"contentType": "text/html; charset=utf-8"}), encoding="utf-8")

    def test_archived_note_with_comments_scores_high(self, cfg) -> None:
        self._prepare(cfg, NOTE_WITH_COMMENTS)
        result = Verifier(cfg).check_content_sample(sample=5)
        assert result.passed, result.problems
        assert any("相似度 1.000" in note for note in result.notes)

    def test_lost_comments_are_detected(self, cfg) -> None:
        """回归：整段评论丢失必须判失败。

        合成一整段再比会把它稀释掉——评论偏少的长文里只掉到 0.934，
        够不着 0.9 的阈值，所以正文与评论得各自算比值。
        """
        self._prepare(cfg, NOTE_MD)  # 同一篇，但 md 里没有评论区块
        result = Verifier(cfg).check_content_sample(sample=5)
        assert not result.passed
        assert any("评论 0.000" in problem for problem in result.problems)

    def test_missing_md_is_reported(self, cfg) -> None:
        self._prepare(cfg, NOTE_WITH_COMMENTS)
        (cfg.notes_dir / "575615184.md").unlink()
        result = Verifier(cfg).check_content_sample(sample=5)
        assert not result.passed
        assert any("md 文件不存在" in problem for problem in result.problems)

    def test_missing_raw_cache_is_a_failure_not_a_silent_skip(self, cfg) -> None:
        self._prepare(cfg, NOTE_WITH_COMMENTS)
        body, meta = cache_paths(cfg, cfg.note_url("1", "575615184"))
        body.unlink()
        meta.unlink()
        result = Verifier(cfg).check_content_sample(sample=5)
        assert not result.passed
        assert result.checked == 0
        assert any("无原始 HTML 缓存" in problem for problem in result.problems)

    def test_sampling_is_reproducible_and_reports_ids(self, cfg) -> None:
        self._prepare(cfg, NOTE_WITH_COMMENTS)
        verifier = Verifier(cfg)
        first = verifier.check_content_sample(sample=5)
        second = verifier.check_content_sample(sample=5)
        assert first.notes[0] == second.notes[0]
        assert first.notes[0].startswith("抽样 ID：note:575615184")

    def test_external_pages_are_sampled(self, cfg) -> None:
        url = "https://www.douban.com/topic/123/"
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(
            json.dumps({"external": {"topic-123": {"url": url, "content_html": "真实内容"}}}),
            encoding="utf-8",
        )
        page = cfg.docs_dir / "external" / "topic-123.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("---\ntitle: t\n---\n\n完全不同", encoding="utf-8")
        body, meta = cache_paths(cfg, url)
        body.parent.mkdir(parents=True, exist_ok=True)
        body.write_text('<div class="topic-content">真实内容</div>', encoding="utf-8")
        meta.write_text(json.dumps({"contentType": "text/html; charset=utf-8"}), encoding="utf-8")
        result = Verifier(cfg).check_content_sample(sample=1)
        assert not result.passed
        assert result.checked == 1
        assert any("external:topic-123" in problem for problem in result.problems)

    def test_album_captions_are_sampled(self, cfg) -> None:
        url = "https://site.douban.com/photo/1/"
        cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.manifest_path.write_text(
            json.dumps({
                "albums": {
                    "A1": {"photos": [{"photo_id": "1", "caption": "真实描述", "source_url": url}]}
                }
            }),
            encoding="utf-8",
        )
        page = cfg.albums_dir / "A1.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("---\ntitle: album\n---\n\n错误描述", encoding="utf-8")
        body, meta = cache_paths(cfg, url)
        body.parent.mkdir(parents=True, exist_ok=True)
        body.write_text(
            '<div class="phoview"><div class="phodesc">真实描述</div>'
            '<img src="https://img.test/a.jpg"></div>',
            encoding="utf-8",
        )
        meta.write_text(json.dumps({"contentType": "text/html; charset=utf-8"}), encoding="utf-8")
        result = Verifier(cfg).check_content_sample(sample=1)
        assert not result.passed
        assert result.checked == 1
        assert any("album:A1" in problem for problem in result.problems)


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
