"""站外页面（需登录）的解析、路由与渲染测试。"""

from __future__ import annotations

import json

import pytest

from scraper.cli import EXTERNAL_HOSTS, _external_page_id, _external_targets
from scraper.emit import EmitContext, SiteEmitter
from scraper.html2md import ConvertContext, html_to_markdown
from scraper.models import Availability, ExternalPage, IndexEntry, IndexGroup, SourceStatus
from scraper.parsers import parse_external_page

PAGE_HTML = """
<html><head><title>某访谈 (豆瓣)</title></head><body>
  <h1>“珍视角色”——山田尚子访谈</h1>
  <div id="link-report">第一段<br><br>第二段</div>
  <div id="comments">
    <div class="comment-item" data-cid="1">
      <div class="content"><div class="author"><span>2020-01-01 00:00:00</span><a>读者</a></div>
      <p>好评</p></div>
    </div>
  </div>
</body></html>
"""


class TestExternalPageId:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://www.douban.com/topic/499780453/", "topic-499780453"),
            ("https://www.douban.com/note/624442255/", "note-624442255"),
            ("https://www.douban.com/topic/499780453", "topic-499780453"),
            ("https://www.douban.com/", "page"),
        ],
    )
    def test_derives_stable_id(self, url: str, expected: str) -> None:
        assert _external_page_id(url) == expected


class TestExternalTargets:
    def _ctx(self, groups):
        class Ctx:
            index_groups = groups

            def build_index_groups(self):
                return groups

        return Ctx()

    def test_picks_only_douban_main_site(self) -> None:
        groups = [
            IndexGroup(
                title="穹庐下的魔女",
                entries=[
                    IndexEntry(title="访谈", url="https://www.douban.com/topic/499780453/"),
                    IndexEntry(title="站内文章", url="https://site.douban.com/211330/widget/notes/1/note/2/"),
                    IndexEntry(title="参考站", url="https://www.kyotoanimation.co.jp/"),
                ],
            )
        ]
        targets = _external_targets(self._ctx(groups))
        assert len(targets) == 1
        page_id, url, origin = targets[0]
        assert page_id == "topic-499780453"
        assert origin == "穹庐下的魔女"

    def test_deduplicates_same_page(self) -> None:
        entry = IndexEntry(title="x", url="https://www.douban.com/topic/1/")
        groups = [IndexGroup(title="A", entries=[entry]), IndexGroup(title="B", entries=[entry])]
        assert len(_external_targets(self._ctx(groups))) == 1

    def test_empty_index(self) -> None:
        assert _external_targets(self._ctx([])) == []


class TestParseExternalPage:
    def test_extracts_title_content_comments(self) -> None:
        page = parse_external_page(PAGE_HTML, "https://www.douban.com/topic/1/", "topic-1", "穹庐下的魔女")
        assert page.title == "“珍视角色”——山田尚子访谈"
        assert "第一段" in page.content_html
        assert len(page.comments) == 1
        assert page.comments[0].author == "读者"
        assert page.origin == "穹庐下的魔女"
        assert page.route == "/external/topic-1"
        assert page.status.availability == Availability.OK

    def test_falls_back_to_title_tag(self) -> None:
        page = parse_external_page("<html><head><title>备用标题 (豆瓣)</title></head></html>", "u", "p")
        assert page.title == "备用标题"

    def test_no_content_container_marks_unavailable(self) -> None:
        page = parse_external_page("<html><body><h1>标题</h1></body></html>", "u", "p")
        assert page.status.availability == Availability.UNAVAILABLE
        assert "容器" in page.status.detail

    def test_alternative_content_selector(self) -> None:
        html = '<html><body><h1>T</h1><article>用 article 容器</article></body></html>'
        page = parse_external_page(html, "u", "p")
        assert "article 容器" in page.content_html


class TestExternalRoutes:
    def test_html2md_rewrites_archived_external_link(self) -> None:
        ctx = ConvertContext(external_routes={"https://www.douban.com/topic/1/": "/external/topic-1"})
        html = '<a href="https://www.douban.com/topic/1/">访谈</a>'
        assert html_to_markdown(html, ctx) == "[访谈](/external/topic-1)"

    def test_html2md_rewrites_without_trailing_slash(self) -> None:
        ctx = ConvertContext(external_routes={"https://www.douban.com/topic/1/": "/external/topic-1"})
        html = '<a href="https://www.douban.com/topic/1">访谈</a>'
        assert html_to_markdown(html, ctx) == "[访谈](/external/topic-1)"

    def test_unarchived_external_link_kept(self) -> None:
        """未归档时保留外链，不能制造死链（否则构建期报 dead link）。"""
        html = '<a href="https://www.douban.com/topic/999/">未归档</a>'
        assert html_to_markdown(html) == "[未归档](https://www.douban.com/topic/999/)"


class TestEmitExternal:
    def test_writes_page_with_frontmatter_and_comments(self, cfg) -> None:
        page = ExternalPage(
            page_id="topic-1",
            url="https://www.douban.com/topic/1/",
            title="访谈标题",
            content_html="正文<br><br>第二段",
            origin="穹庐下的魔女",
            status=SourceStatus(availability=Availability.OK),
        )
        emitter = SiteEmitter(cfg, EmitContext())
        path = emitter.emit_external(page)
        text = path.read_text(encoding="utf-8")
        assert path.name == "topic-1.md"
        assert '"访谈标题"' in text
        assert '"pageId": "topic-1"' not in text  # frontmatter 不是 JSON
        assert "pageId:" in text
        assert "穹庐下的魔女" in text
        assert "正文" in text

    def test_unavailable_page_gets_notice(self, cfg) -> None:
        page = ExternalPage(
            page_id="topic-2",
            url="https://www.douban.com/topic/2/",
            title="拿不到",
            status=SourceStatus(
                availability=Availability.LOGIN_REQUIRED,
                http_status=403,
                detail="需要登录",
            ),
        )
        text = SiteEmitter(cfg, EmitContext()).emit_external(page).read_text(encoding="utf-8")
        assert ":::" in text
        assert "需要登录" in text
        assert "正文未能归档" in text

    def test_external_index_lists_pages(self, cfg) -> None:
        pages = [
            ExternalPage(page_id="topic-1", url="u1", title="第一篇", origin="A",
                         status=SourceStatus(availability=Availability.OK)),
            ExternalPage(page_id="topic-2", url="u2", title="第二篇",
                         status=SourceStatus(availability=Availability.LOGIN_REQUIRED)),
        ]
        text = SiteEmitter(cfg, EmitContext()).emit_external_index(pages).read_text(encoding="utf-8")
        assert "[第一篇](/external/topic-1)" in text
        assert "[第二篇](/external/topic-2)" in text
        assert "需要登录" in text  # 未归档的页面会带上状态徽章

    def test_external_index_empty(self, cfg) -> None:
        text = SiteEmitter(cfg, EmitContext()).emit_external_index([]).read_text(encoding="utf-8")
        assert "还没有归档站外文章" in text


class TestSidebarWithExternal:
    def test_archived_external_entry_gets_internal_link(self, cfg) -> None:
        """已归档的站外条目在 sidebar 里指向站内路由，而不是外链。"""
        groups = [
            IndexGroup(
                title="穹庐下的魔女",
                entries=[IndexEntry(title="访谈", url="https://www.douban.com/topic/1/")],
            )
        ]
        ctx = EmitContext(external_routes={"https://www.douban.com/topic/1/": "/external/topic-1"})
        text = SiteEmitter(cfg, ctx).emit_sidebar(groups, {}).read_text(encoding="utf-8")
        payload = json.loads(text.split("= ", 1)[1].rsplit(" as DefaultTheme.Sidebar", 1)[0])
        item = payload["/notes/"][0]["items"][0]
        assert item == {"text": "访谈", "link": "/external/topic-1"}

    def test_unarchived_external_entry_has_no_link(self, cfg) -> None:
        groups = [
            IndexGroup(
                title="穹庐下的魔女",
                entries=[IndexEntry(title="访谈", url="https://www.douban.com/topic/1/")],
            )
        ]
        text = SiteEmitter(cfg, EmitContext()).emit_sidebar(groups, {}).read_text(encoding="utf-8")
        assert "https://www.douban.com/topic/1/" not in text
        payload = json.loads(text.split("= ", 1)[1].rsplit(" as DefaultTheme.Sidebar", 1)[0])
        assert "link" not in payload["/notes/"][0]["items"][0]

    def test_external_group_added_when_pages_exist(self, cfg) -> None:
        text = SiteEmitter(cfg, EmitContext()).emit_sidebar(
            [], {}, external_count=2
        ).read_text(encoding="utf-8")
        assert "/external/" in text

    def test_external_group_absent_when_no_pages(self, cfg) -> None:
        text = SiteEmitter(cfg, EmitContext()).emit_sidebar([], {}).read_text(encoding="utf-8")
        assert "/external/" not in text
