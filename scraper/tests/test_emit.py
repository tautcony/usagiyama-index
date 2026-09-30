"""产物生成测试：frontmatter 转义、提示块、sidebar、清单。"""

from __future__ import annotations

import json
import re

from scraper.emit import (
    EmitContext,
    SiteEmitter,
    frontmatter,
    html_attr,
    html_text,
    slug_anchor,
    status_notice,
)
from scraper.models import (
    Album,
    Availability,
    IndexEntry,
    IndexGroup,
    Note,
    PhotoMeta,
    SourceStatus,
)


class TestFrontmatter:
    def test_basic(self) -> None:
        out = frontmatter({"title": "标题", "noteId": "123"})
        assert out.startswith("---\n")
        assert out.endswith("\n---")
        assert 'title: "标题"' in out

    def test_quotes_escaped(self) -> None:
        """标题里常有中文引号与英文引号，必须安全转义。"""
        out = frontmatter({"title": '他说"你好"'})
        assert '\\"' in out

    def test_colon_in_value_safe(self) -> None:
        out = frontmatter({"source": "https://site.douban.com/211330/"})
        assert 'source: "https://site.douban.com/211330/"' in out

    def test_empty_values_dropped(self) -> None:
        out = frontmatter({"title": "x", "date": "", "commentCount": None})
        assert "date" not in out
        assert "commentCount" not in out

    def test_boolean_and_int(self) -> None:
        out = frontmatter({"aside": False, "count": 3})
        assert "aside: false" in out
        assert "count: 3" in out

    def test_output_is_valid_yaml(self) -> None:
        import yaml  # 若未安装则跳过

        out = frontmatter({"title": '含"引号"与:冒号', "count": 5, "aside": False})
        body = out.strip("-\n")
        parsed = yaml.safe_load(body)
        assert parsed["title"] == '含"引号"与:冒号'
        assert parsed["count"] == 5
        assert parsed["aside"] is False


class TestStatusNotice:
    def test_ok_has_no_notice(self) -> None:
        assert status_notice(SourceStatus(availability=Availability.OK)) == ""

    def test_archived_notice_includes_wayback(self) -> None:
        status = SourceStatus(
            availability=Availability.ARCHIVED,
            http_status=403,
            wayback_url="https://web.archive.org/web/20210101000000/http://x/",
            wayback_timestamp="20210101000000",
        )
        notice = status_notice(status)
        assert "::: info" in notice
        assert "Internet Archive" in notice
        assert "2021-01-01" in notice
        assert "web.archive.org" in notice

    def test_login_required_notice(self) -> None:
        notice = status_notice(
            SourceStatus(availability=Availability.LOGIN_REQUIRED, http_status=403)
        )
        assert "::: warning" in notice
        assert "登录" in notice

    def test_archive_missing_notice(self) -> None:
        notice = status_notice(SourceStatus(availability=Availability.ARCHIVE_MISSING, http_status=404))
        assert "::: danger" in notice
        assert "正文缺失" in notice


class TestSlugAnchor:
    def test_chinese_kept(self) -> None:
        assert slug_anchor("聲之形") == "聲之形"

    def test_matches_vitepress_punctuation_and_nfkd_rules(self) -> None:
        assert slug_anchor("轻音！系列") == "轻音-系列"
        assert slug_anchor("玉子市场＆玉子爱情故事") == "玉子市场-玉子爱情故事"
        assert slug_anchor("École déjà") == "ecole-deja"
        assert slug_anchor("2026 标题") == "_2026-标题"


def _note(note_id: str = "1", **kwargs) -> Note:
    note = Note(
        note_id=note_id,
        widget_id="190597056",
        title=kwargs.pop("title", "测试标题"),
        date=kwargs.pop("date", "2016-08-11 21:06:31"),
        content_html=kwargs.pop("content_html", "正文<br>第二行"),
        source_url=f"https://site.douban.com/211330/widget/notes/1/note/{note_id}/",
        **kwargs,
    )
    return note


def _photo_card(text: str) -> str:
    """取出相册页里的第一张卡片 —— 断言挂在卡片上，「哪张图配哪个链接」才说得清。"""
    start = text.index('<figure class="photo-card">')
    return text[start : text.index("</figure>", start)]


class TestEmitNote:
    def test_writes_file_with_frontmatter(self, cfg) -> None:
        emitter = SiteEmitter(cfg, EmitContext(route_map={"1": "/notes/1"}))
        path = emitter.emit_note(_note())
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "正文" in text
        assert "本页归档自" in text

    def test_note_id_and_source_present(self, cfg) -> None:
        emitter = SiteEmitter(cfg)
        path = emitter.emit_note(_note("575615184"))
        text = path.read_text(encoding="utf-8")
        assert 'noteId: "575615184"' in text
        assert "note/575615184/" in text

    def test_unavailable_note_gets_notice(self, cfg) -> None:
        note = _note(content_html="")
        note.status = SourceStatus(availability=Availability.ARCHIVE_MISSING, http_status=404)
        emitter = SiteEmitter(cfg)
        text = emitter.emit_note(note).read_text(encoding="utf-8")
        assert "::: danger" in text
        assert "正文未能归档" in text

    def test_comment_count_mentioned(self, cfg) -> None:
        note = _note(comment_count=3)
        text = SiteEmitter(cfg).emit_note(note).read_text(encoding="utf-8")
        assert "3 条评论" in text
        assert "commentCount: 3" in text

    def test_links_rewritten_using_route_map(self, cfg) -> None:
        note = _note(
            content_html=(
                '见<a href="https://site.douban.com/211330/widget/notes/1/note/999/">后文</a>'
            )
        )
        emitter = SiteEmitter(cfg, EmitContext(route_map={"999": "/notes/999"}))
        text = emitter.emit_note(note).read_text(encoding="utf-8")
        assert "[后文](/notes/999)" in text

    def test_archived_images_use_local_path(self, cfg) -> None:
        from scraper.models import ImageRef

        note = _note(content_html='<img src="https://img9.doubanio.com/view/note/raw/public/p1.jpg"/>')
        note.images = [
            ImageRef(
                src="https://img9.doubanio.com/view/note/raw/public/p1.jpg",
                local="/media/notes/1/p1.jpg",
                archived=True,
            )
        ]
        text = SiteEmitter(cfg).emit_note(note).read_text(encoding="utf-8")
        assert "![](/media/notes/1/p1.jpg)" in text
        assert "img9.doubanio.com" not in text

    def test_unarchived_images_dropped(self, cfg) -> None:
        """图片没下下来就丢弃，不要留一个会裂图的外链。"""
        note = _note(content_html='<img src="https://img9.doubanio.com/view/note/raw/public/p1.jpg"/>')
        text = SiteEmitter(cfg).emit_note(note).read_text(encoding="utf-8")
        assert "img9.doubanio.com" not in text


class TestEmitAlbum:
    def _album(self) -> Album:
        album = Album(album_id="13432051", title="海报墙", source_url="https://x/")
        album.photos = [
            PhotoMeta(
                photo_id="1", album_id="13432051", caption="描述一",
                local="/media/albums/13432051/1.jpg",
            ),
            PhotoMeta(photo_id="2", album_id="13432051", caption="", local=""),
        ]
        return album

    def test_grid_and_missing_notice(self, cfg) -> None:
        text = SiteEmitter(cfg).emit_album(self._album()).read_text(encoding="utf-8")
        assert "photo-grid" in text
        assert "/media/albums/13432051/1.jpg" in text
        assert "有 1 张图片未能归档" in text
        assert "`2`" in text

    def test_caption_rendered(self, cfg) -> None:
        text = SiteEmitter(cfg).emit_album(self._album()).read_text(encoding="utf-8")
        assert "描述一" in text

    def test_no_description_renders_no_caption_and_no_empty_attrs(self, cfg) -> None:
        """没有描述的照片：不写 `<p class="caption">`，也不留空 title/alt。"""
        album = Album(album_id="1", title="t")
        album.photos = [PhotoMeta(photo_id="1", album_id="1", local="/media/1.jpg")]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")

        assert 'class="caption"' not in text
        assert 'alt=""' not in text
        assert 'title=""' not in text
        assert '<img src="/media/1.jpg" loading="lazy" />' in text

    def test_quotes_in_caption_escaped(self, cfg) -> None:
        album = Album(album_id="1", title="t")
        album.photos = [
            PhotoMeta(photo_id="1", album_id="1", caption='含"引号"', local="/media/1.jpg")
        ]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        assert "&quot;" in text

    def test_preview_webp_click_opens_original_jpg(self, cfg) -> None:
        """有原图时：网格里显示 webp 预览图，点开的链接指向 jpg 原图。"""
        album = Album(album_id="1", title="t")
        album.photos = [
            PhotoMeta(
                photo_id="1",
                album_id="1",
                caption="描述",
                local="/media/albums/1/1.webp",
                local_original="/media/albums/1/original/1.jpg",
            )
        ]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        card = _photo_card(text)

        assert '<a class="photo-preview" href="/media/albums/1/original/1.jpg"' in card
        assert '<img src="/media/albums/1/1.webp" alt="描述" loading="lazy" />' in card
        # 描述既给缩放脚本（data-caption）也做光标提示
        assert 'data-caption="描述"' in card
        assert "查看原图" in card

    def test_without_original_click_opens_preview(self, cfg) -> None:
        """源站不给原图（或没抓到）时，点开的仍是预览图，且不吹嘘"查看原图"。"""
        album = Album(album_id="1", title="t")
        album.photos = [PhotoMeta(photo_id="1", album_id="1", local="/media/albums/1/1.webp")]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        card = _photo_card(text)

        assert 'href="/media/albums/1/1.webp"' in card
        assert "查看原图" not in card
        assert "data-caption" not in card


class TestEmitSidebar:
    def test_generates_valid_ts_object(self, cfg) -> None:
        groups = [
            IndexGroup(
                title="聲之形",
                doulist_url="https://www.douban.com/doulist/1/",
                entries=[IndexEntry(title="文章A", url="u", note_id="1")],
            )
        ]
        notes = {"1": _note("1", title="文章A")}
        path = SiteEmitter(cfg).emit_sidebar(groups, notes)
        text = path.read_text(encoding="utf-8")
        assert "export const sidebar" in text
        assert "DefaultTheme.Sidebar" in text
        # 提取 JSON 部分验证可解析
        payload = text.split("= ", 1)[1].rsplit(" as DefaultTheme.Sidebar", 1)[0]
        data = json.loads(payload)
        assert data["/notes/"][0]["text"] == "聲之形"
        assert data["/notes/"][0]["items"][0]["link"] == "/notes/1"

    def test_unavailable_entry_has_no_link(self, cfg) -> None:
        """未归档条目在 sidebar 里保留文字但**不能**有 link。

        VitePress 的 sidebar link 必须是站内路由：外站 URL 会让构建期报
        "Invalid route component: undefined"，而指向 /notes/{id} 又会制造死链
        （构建期 dead link 检查会直接失败）。外链统一放在 /notes/ 索引页里给出。
        """
        groups = [
            IndexGroup(
                title="穹庐下的魔女",
                entries=[
                    IndexEntry(title="未归档访谈", url="https://www.douban.com/topic/1/", note_id=None)
                ],
            )
        ]
        path = SiteEmitter(cfg).emit_sidebar(groups, {})
        text = path.read_text(encoding="utf-8")
        assert "https://www.douban.com/topic/1/" not in text
        assert "/notes/1" not in text
        payload = json.loads(
            text.split("= ", 1)[1].rsplit(" as DefaultTheme.Sidebar", 1)[0]
        )
        item = payload["/notes/"][0]["items"][0]
        assert item["text"] == "未归档访谈（未归档）"
        assert "link" not in item

    def test_fallback_group_collapsed(self, cfg) -> None:
        notes = {"2": _note("2", title="日志", date="2018-01-01")}
        path = SiteEmitter(cfg).emit_sidebar([], {}, fallback_notes=list(notes.values()))
        payload = json.loads(
            path.read_text(encoding="utf-8").split("= ", 1)[1].rsplit(" as DefaultTheme.Sidebar", 1)[0]
        )
        group = payload["/notes/"][0]
        assert group["text"] == "尚子的房间"
        assert group["collapsed"] is True


class TestEmitUnavailableReport:
    def test_report_lists_records(self, cfg) -> None:
        from scraper.resolver import UnavailableRecord

        records = [
            UnavailableRecord(
                url="https://www.douban.com/topic/1/",
                availability=Availability.LOGIN_REQUIRED,
                http_status=403,
                detail="需要登录",
                context="穹庐下的魔女",
            ),
            UnavailableRecord(
                url="https://www.douban.com/note/2/",
                availability=Availability.ARCHIVED,
                http_status=403,
                detail="已补足",
                wayback_url="https://web.archive.org/web/2020/http://x/",
            ),
        ]
        text = SiteEmitter(cfg).emit_unavailable_report(records).read_text(encoding="utf-8")
        assert "需登录" in text
        assert "已补足" in text
        assert "web.archive.org" in text

    def test_empty_report(self, cfg) -> None:
        text = SiteEmitter(cfg).emit_unavailable_report([]).read_text(encoding="utf-8")
        assert "全部内容均已成功归档" in text

    def test_pipe_in_detail_escaped(self, cfg) -> None:
        from scraper.resolver import UnavailableRecord

        records = [
            UnavailableRecord(
                url="u", availability=Availability.UNAVAILABLE, detail="含|竖线"
            )
        ]
        text = SiteEmitter(cfg).emit_unavailable_report(records).read_text(encoding="utf-8")
        assert "含\\|竖线" in text

    def test_all_table_fields_escape_pipes_and_newlines(self, cfg) -> None:
        from scraper.resolver import UnavailableRecord

        records = [UnavailableRecord(
            url="https://x/a|b",
            availability=Availability.UNAVAILABLE,
            context="context|line\nnext",
            detail="detail|line\nnext",
        )]
        text = SiteEmitter(cfg).emit_unavailable_report(records).read_text(encoding="utf-8")
        assert "https://x/a\\|b" in text
        assert "context\\|line<br>next" in text
        assert "detail\\|line<br>next" in text


class TestEmitHome:
    def test_home_page_generated(self, cfg) -> None:
        groups = [
            IndexGroup(title="聲之形", entries=[IndexEntry(title="A", url="u", note_id="1")])
        ]
        album = Album(album_id="13432051", title="海报墙")
        album.photos = [PhotoMeta(photo_id="1", album_id="13432051", local="/media/a.jpg")]
        emitter = SiteEmitter(cfg, EmitContext(album_routes={"13432051": "/albums/13432051"}))
        text = emitter.emit_home(
            {"name": "兔子山的小站", "description": "描述", "avatar": "https://x/a.jpg"},
            groups,
            [album],
            avatar_local="/media/site/avatar.jpg",
            stats={"notes": 1, "photos": 1, "albums": 1, "videos": 0},
        ).read_text(encoding="utf-8")
        assert "layout: home" in text
        assert "poster-wall" in text
        assert "/albums/13432051" in text
        assert "/media/site/avatar.jpg" in text
        assert "聲之形" in text

    def test_html_attribute_paths_are_escaped(self, cfg) -> None:
        album = Album(album_id="1", title="album")
        album.photos = [PhotoMeta(
            photo_id="1", album_id="1", local='/media/x.jpg"><img src=x onerror=alert(1)>'
        )]
        emitter = SiteEmitter(cfg, EmitContext(album_routes={"1": '/albums/1"><img src=x>'}))
        text = emitter.emit_home({"name": "site"}, [], [album]).read_text(encoding="utf-8")
        assert 'x.jpg"><img src=x' not in text
        assert "&quot;" in text


class TestEmitNotesIndex:
    def test_index_lists_entries_with_badges(self, cfg) -> None:
        groups = [
            IndexGroup(
                title="聲之形",
                entries=[
                    IndexEntry(title="A", url="u", note_id="1"),
                    IndexEntry(title="B", url="u2", note_id="2"),
                ],
            )
        ]
        notes = {"1": _note("1", title="A")}
        notes["2"] = _note("2", title="B")
        notes["2"].status = SourceStatus(availability=Availability.LOGIN_REQUIRED)
        emitter = SiteEmitter(cfg, EmitContext(route_map={"1": "/notes/1", "2": "/notes/2"}))
        text = emitter.emit_notes_index(groups, notes).read_text(encoding="utf-8")
        assert "[A](/notes/1)" in text
        assert "badge-unavailable" in text
        assert "需要登录" in text

    def test_link_titles_escape_square_brackets(self, cfg) -> None:
        note = _note("1", title="C# [笔记] 标题")
        fallback = SiteEmitter(cfg).emit_notes_index([], {"1": note}, fallback_notes=[note])
        assert r"C# \[笔记\] 标题" in fallback.read_text(encoding="utf-8")

    def test_album_index_titles_escape_square_brackets(self, cfg) -> None:
        text = SiteEmitter(cfg).emit_albums_index([Album(album_id="1", title="相册 [一]")])
        assert r"相册 \[一\]" in text.read_text(encoding="utf-8")


class TestHtmlEscaping:
    """相册描述里常有字面换行与引号，必须转义后才安全。"""

    def test_newlines_collapsed(self) -> None:
        assert html_attr("第一行\n\n第二行") == "第一行 第二行"

    def test_quotes_escaped(self) -> None:
        assert html_attr('含"引号"') == "含&quot;引号&quot;"

    def test_ampersand_first(self) -> None:
        """& 必须最先替换，否则会把实体二次转义。"""
        assert html_attr("a & <b>") == "a &amp; &lt;b&gt;"

    def test_ampersand_not_double_escaped(self) -> None:
        assert "&amp;amp;" not in html_attr("a & b")

    def test_text_does_not_escape_quotes(self) -> None:
        """文本节点里引号无需转义。"""
        assert html_text('含"引号"') == '含"引号"'

    def test_text_escapes_angle_brackets(self) -> None:
        assert html_text("<script>") == "&lt;script&gt;"

    def test_empty_input(self) -> None:
        assert html_attr("") == ""
        assert html_text("") == ""

    def test_tabs_and_spaces_normalised(self) -> None:
        assert html_attr("a\t\t b   c") == "a b c"

    def test_braces_escaped_for_vue(self) -> None:
        """``{{ }}`` 是 Vue 的插值语法，原样输出会被当成表达式。"""
        assert html_text("{{ x }}") == "&#123;&#123; x &#125;&#125;"
        assert html_attr("{{ x }}") == "&#123;&#123; x &#125;&#125;"


class TestAlbumCaptionEscaping:
    def test_newline_in_caption_does_not_break_html(self, cfg) -> None:
        """回归：含换行的描述曾让 VitePress 构建直接失败。"""
        album = Album(album_id="1", title="相册")
        album.photos = [
            PhotoMeta(
                photo_id="1",
                album_id="1",
                caption="第一行\n\n第二行，含\"引号\"",
                local="/media/1.jpg",
            )
        ]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        # 属性值内不能有裸换行
        for line in text.splitlines():
            if "photo-card" in line:
                assert line.count('"') % 2 == 0
        assert "&quot;" in text
        assert "第一行 第二行" in text

    def test_angle_brackets_in_caption_escaped(self, cfg) -> None:
        album = Album(album_id="1", title="相册")
        album.photos = [
            PhotoMeta(photo_id="1", album_id="1", caption="<b>粗</b>", local="/media/1.jpg")
        ]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        assert "<b>粗</b>" not in text
        assert "&lt;b&gt;" in text

    def test_braces_in_caption_neutralised(self, cfg) -> None:
        """回归：描述里的 ``{{ }}`` 会被 Vue 当成插值 —— 轻则吞掉这段文字，
        重则（括号不配对时）让整个站点构建失败。"""
        album = Album(album_id="1", title="相册")
        album.photos = [
            PhotoMeta(
                photo_id="1",
                album_id="1",
                caption="含 {{ 花括号 }} 与坏表达式 {{ (}}",
                local="/media/1.webp",
            )
        ]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        assert "{{" not in text
        assert "&#123;&#123; 花括号 &#125;&#125;" in text

    def test_local_paths_cannot_break_html_attributes(self, cfg) -> None:
        album = Album(album_id="1", title="相册")
        album.photos = [PhotoMeta(
            photo_id="1", album_id="1", local='/media/x.jpg"><img src=x onerror=alert(1)>'
        )]
        text = SiteEmitter(cfg).emit_album(album).read_text(encoding="utf-8")
        assert 'x.jpg"><img src=x' not in text
        assert "&quot;" in text


class TestEmitBoard:
    def test_multiline_comment_stays_inside_blockquote(self, cfg) -> None:
        from scraper.models import Comment, Discussion

        discussion = Discussion(
            discussion_id="1", forum_id="forum", title="话题", source_url="https://x/"
        )
        discussion.comments = [Comment(author="a", content_html="<p>第一段</p><p>## 不是标题</p>")]
        text = SiteEmitter(cfg).emit_board([discussion]).read_text(encoding="utf-8")
        assert "> 第一段\n> \n> ## 不是标题" in text


class TestEmitExternal:
    def test_archived_at_is_stable_across_days(self, cfg, monkeypatch) -> None:
        from scraper import emit as emit_module
        from scraper.models import ExternalPage

        page = ExternalPage(page_id="topic-1", url="https://x/", content_html="<p>body</p>")
        values = iter(["2026-09-30T12:00:00+08:00", "2026-10-01T12:00:00+08:00"])
        monkeypatch.setattr(emit_module, "now_iso", lambda: next(values))
        emitter = SiteEmitter(cfg)
        path = emitter.emit_external(page)
        first = path.read_text(encoding="utf-8")
        emitter.emit_external(page)
        assert path.read_text(encoding="utf-8") == first


class TestVideoEscaping:
    def test_video_title_escaped(self, cfg) -> None:
        from scraper.models import Video

        video = Video(
            video_id="1",
            widget_id="w",
            title='标题含"引号"与<标签>',
            external_url="https://v.youku.com/x",
        )
        text = SiteEmitter(cfg).emit_videos([video]).read_text(encoding="utf-8")
        # 标题落在文本节点里：尖括号必须转义，引号无需转义
        assert "&lt;标签&gt;" in text
        assert "<标签>" not in text
        assert '标题含"引号"' in text

    def test_video_external_url_in_attribute_escaped(self, cfg) -> None:
        from scraper.models import Video

        video = Video(
            video_id="1",
            widget_id="w",
            title="正常标题",
            external_url='https://x/?a=1&b="2"',
        )
        text = SiteEmitter(cfg).emit_videos([video]).read_text(encoding="utf-8")
        assert "&amp;" in text
        assert "&quot;2&quot;" in text
