"""HTML → Markdown 转换的回归测试。

豆瓣正文的形态很特殊（裸文本 + 大量 ``<br>`` + 表格包图片 + link2 跳转），
这些用例把每种形态钉死，源站改版时能立刻定位到破坏点。
"""

from __future__ import annotations

import pytest

from scraper.html2md import (
    ConvertContext,
    html_to_markdown,
    html_to_plain_text,
    markdown_to_plain_text,
    unwrap_link2,
)


class TestUnwrapLink2:
    def test_decodes_wrapped_url(self) -> None:
        wrapped = (
            "https://www.douban.com/link2/?url=https%3A%2F%2Fwww.douban.com"
            "%2Fdoulist%2F44247823%2F&link2key=abc"
        )
        assert unwrap_link2(wrapped) == "https://www.douban.com/doulist/44247823/"

    def test_passes_through_plain_url(self) -> None:
        url = "https://example.com/a"
        assert unwrap_link2(url) == url

    def test_handles_empty(self) -> None:
        assert unwrap_link2("") == ""


class TestLinkSafety:
    """WARN-9：不可信 URI 净化，避免 XSS 与链接语法破损。"""

    def test_javascript_scheme_dropped(self) -> None:
        # 评论里的 javascript: 链接不能变成可点击链接（XSS）
        out = html_to_markdown('<a href="javascript:alert(1)">点我</a>')
        assert out == "点我"
        assert "javascript:" not in out

    def test_bracket_in_label_escaped(self) -> None:
        # 链接文字里的 ] 不应提前闭合链接括号
        out = html_to_markdown('<a href="https://example.com/n">C# [笔记]</a>')
        assert out == "[C# \\[笔记\\]](https://example.com/n)"

    def test_url_with_paren_wrapped(self) -> None:
        # 含 ) 的 URL 用尖括号包裹，避免破坏 [text](url) 语法
        out = html_to_markdown('<a href="https://example.com/x(y)">链接</a>')
        assert out == "[链接](<https://example.com/x(y)>)"

    def test_data_scheme_dropped(self) -> None:
        out = html_to_markdown('<a href="data:text/html,<script>x</script>">坏链</a>')
        assert "data:text/html" not in out
        assert out == "坏链"

    @pytest.mark.parametrize(
        "payload",
        [
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            '<iframe srcdoc="<script>alert(1)</script>">',
            "<script>alert(1)</script>",
        ],
    )
    def test_entity_encoded_html_remains_text(self, payload: str) -> None:
        from html import escape

        out = html_to_markdown(f"<p>{escape(payload)}</p>")
        assert "<img" not in out
        assert "<svg" not in out
        assert "<iframe" not in out
        assert "<script" not in out

    def test_greater_than_in_link2_target_cannot_escape_link(self) -> None:
        from urllib.parse import quote

        target = "http://x.test/a > <img src=y onerror=alert(1)>"
        wrapped = "https://www.douban.com/link2/?url=" + quote(target, safe="")
        out = html_to_markdown(f'<a href="{wrapped}">click</a>')
        assert "<img" not in out
        assert out == "click"


class TestBrHandling:
    """豆瓣靠 <br> 分行分段，这是还原语义的关键。"""

    def test_single_br_becomes_newline(self) -> None:
        assert html_to_markdown("a<br>b") == "a\nb"

    def test_double_br_becomes_paragraph(self) -> None:
        assert html_to_markdown("a<br><br>b") == "a\n\nb"

    def test_self_closing_br(self) -> None:
        assert html_to_markdown("a<br/>b") == "a\nb"

    def test_br_with_space(self) -> None:
        assert html_to_markdown("a<br />b") == "a\nb"

    def test_many_br_collapse(self) -> None:
        assert html_to_markdown("a<br><br><br><br>b") == "a\n\nb"

    def test_long_text_keeps_all_lines(self) -> None:
        html = "第一行<br>第二行<br>第三行<br><br>新段落<br>续行"
        assert html_to_markdown(html) == "第一行\n第二行\n第三行\n\n新段落\n续行"


class TestImageHandling:
    IMG = "https://img9.doubanio.com/view/note/large/public/p36410176.jpg"

    def test_plain_image(self) -> None:
        assert html_to_markdown(f'<img src="{self.IMG}"/>') == f"![]({self.IMG})"

    def test_image_localised(self) -> None:
        ctx = ConvertContext(image_map={self.IMG: "/media/notes/1/p36410176.jpg"})
        out = html_to_markdown(f'<img src="{self.IMG}"/>', ctx)
        assert out == "![](/media/notes/1/p36410176.jpg)"

    def test_table_wrapped_image_is_unwrapped(self) -> None:
        """豆瓣用 <div class="cc"><table><tr><td><img></td></tr></table></div> 包图片。"""
        html = (
            '<div class="cc"><table><tr><td><img src="' + self.IMG + '"/></td></tr>'
            '<tr><td align="center" class="wr pl"></td></tr></table></div>'
        )
        assert html_to_markdown(html) == f"![]({self.IMG})"

    def test_image_alt_preserved(self) -> None:
        out = html_to_markdown(f'<img src="{self.IMG}" alt="封面"/>')
        assert out == f"![封面]({self.IMG})"

    def test_image_without_src_dropped(self) -> None:
        assert html_to_markdown('<img alt="x"/>') == ""

    def test_remote_image_dropped_when_not_archived(self) -> None:
        """图片未归档且不允许外链时，应丢弃而不是留裂图。"""
        ctx = ConvertContext(keep_remote_images=False)
        assert html_to_markdown(f'<img src="{self.IMG}"/>', ctx) == ""


class TestLinkHandling:
    def test_clickable_image_remains_nested_image_link(self) -> None:
        ctx = ConvertContext(image_map={
            "https://img9.doubanio.com/view/note/large/public/p1.jpg": "/media/notes/1/p1.jpg"
        })
        out = html_to_markdown(
            '<a href="https://example.com/photo"><img alt="[cover]" '
            'src="https://img9.doubanio.com/view/note/large/public/p1.jpg"></a>', ctx
        )
        assert out == "[![\\[cover\\]](/media/notes/1/p1.jpg)](https://example.com/photo)"

    def test_external_link(self) -> None:
        out = html_to_markdown('<a href="https://example.com/x">链接</a>')
        assert out == "[链接](https://example.com/x)"

    def test_link2_unwrapped(self) -> None:
        html = (
            '<a href="https://www.douban.com/link2/?url=https%3A%2F%2Fwww.douban.com'
            '%2Fdoulist%2F44247823%2F">豆列</a>'
        )
        assert html_to_markdown(html) == "[豆列](https://www.douban.com/doulist/44247823/)"

    def test_unarchived_note_link_kept_external(self) -> None:
        """未归档的日记必须保留外链。

        若改写成 /notes/{id} 会指向不存在的页面，构建期触发 dead link
        （About PPK 里链到山田尚子喜欢的电影就是这种情况）。
        """
        html = (
            '<a href="https://site.douban.com/211330/widget/notes/190597056/'
            'note/518061571/">某部电影</a>'
        )
        out = html_to_markdown(html)
        assert out == (
            "[某部电影](https://site.douban.com/211330/widget/notes/190597056/note/518061571/)"
        )
        assert "/notes/518061571" not in out

    def test_archived_note_link_rewritten(self) -> None:
        html = (
            '<a href="https://site.douban.com/211330/widget/notes/190597056/'
            'note/575615184/">前文</a>'
        )
        out = html_to_markdown(html, ConvertContext(route_map={"575615184": "/notes/575615184"}))
        assert out == "[前文](/notes/575615184)"

    def test_unarchived_album_link_kept_external(self) -> None:
        html = '<a href="https://site.douban.com/211330/widget/photos/99999999/">某相册</a>'
        out = html_to_markdown(html)
        assert out == "[某相册](https://site.douban.com/211330/widget/photos/99999999/)"

    def test_internal_note_link_uses_route_map(self) -> None:
        ctx = ConvertContext(route_map={"575615184": "/notes/575615184"})
        html = (
            '<a href="https://site.douban.com/211330/widget/notes/1/note/575615184/">x</a>'
        )
        assert html_to_markdown(html, ctx) == "[x](/notes/575615184)"

    def test_album_link_rewritten(self) -> None:
        ctx = ConvertContext(album_routes={"13432051": "/albums/13432051"})
        html = '<a href="https://site.douban.com/211330/widget/photos/13432051/">海报墙</a>'
        assert html_to_markdown(html, ctx) == "[海报墙](/albums/13432051)"

    def test_empty_link_text_is_dropped(self) -> None:
        """无文字链接多为图标/分享按钮，直接丢弃避免噪声。"""
        assert html_to_markdown('<a href="https://example.com/x"></a>') == ""

    def test_anchor_only_link_becomes_text(self) -> None:
        out = html_to_markdown('<a href="#comments">3回应</a>')
        assert out == "3回应"


class TestStructuralCleanup:
    def test_script_removed(self) -> None:
        assert html_to_markdown('a<script>var x=1;</script>b') == "ab"

    def test_style_removed(self) -> None:
        assert html_to_markdown("a<style>.x{}</style>b") == "ab"

    def test_noscript_removed(self) -> None:
        assert html_to_markdown("a<noscript>提示</noscript>b") == "ab"

    def test_clear_div_removed(self) -> None:
        assert html_to_markdown('a<div class="clear"></div>b') == "ab"

    def test_empty_paragraph_removed(self) -> None:
        assert html_to_markdown("a<p></p>b") == "ab"

    def test_strong_becomes_bold(self) -> None:
        assert html_to_markdown("<strong>粗</strong>") == "**粗**"

    def test_blockquote(self) -> None:
        out = html_to_markdown("<blockquote>引用</blockquote>")
        assert out.startswith(">")
        assert "引用" in out

    def test_heading_uses_atx(self) -> None:
        assert html_to_markdown("<h2>标题</h2>") == "## 标题"

    def test_html_entity_decoded(self) -> None:
        assert html_to_markdown("&#34;引号&#34;") == '"引号"'

    def test_whitespace_only_input(self) -> None:
        assert html_to_markdown("   \n  ") == ""

    def test_empty_input(self) -> None:
        assert html_to_markdown("") == ""


class TestPlainTextRoundTrip:
    def test_html_to_plain_text_collapses(self) -> None:
        assert html_to_plain_text("<p>a</p>\n<p>b</p>") == "a b"

    def test_markdown_to_plain_text_strips_syntax(self) -> None:
        md = "# 标题\n\n**粗体** [链接](https://x) ![图](/a.jpg)"
        text = markdown_to_plain_text(md)
        assert "标题" in text
        assert "粗体" in text
        assert "链接" in text
        assert "https://x" not in text
        assert "a.jpg" not in text


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        # <div> 是块级元素，两个相邻 div 应成为两个段落
        ("<div>a</div><div>b</div>", "a\n\nb"),
        ("<p>a</p><p>b</p>", "a\n\nb"),
        ("文字<br>文字", "文字\n文字"),
    ],
)
def test_smoke(html: str, expected: str) -> None:
    assert html_to_markdown(html) == expected


def test_nested_empty_clear_container_does_not_destroy_pending_nodes():
    html = '<div class="clear"><span><em></em></span></div><p>正文保留</p>'
    assert html_to_markdown(html) == '正文保留'
