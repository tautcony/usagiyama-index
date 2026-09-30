"""日记评论归档测试。

此前误判为「评论由 AJAX 加载、需登录才能拿」，实际是**服务端静态渲染**的。
这里把这个结论钉死，避免再次回退。
"""

from __future__ import annotations

import pytest

from scraper.models import Comment, Note
from scraper.parsers import (
    parse_comment_items,
    parse_note_comment_pages,
    parse_note_comments,
)

COMMENT_HTML = """
<div id="comments">
  <div class="comment-item" data-cid="57095888" data-target_id="673585518">
    <div class="pic"><a href="/people/151409267/">
      <img src="https://img9.doubanio.com/icon/u151409267-5.jpg" alt="贫僧读物理"></a></div>
    <div class="content report-comment">
      <div class="author"><span>2019-01-24 15:22:41</span>
        <a href="/people/151409267/">贫僧读物理</a></div>
      <p>希望兔子山能翻译一些利兹与青鸟的文章==</p>
    </div>
  </div>
  <div class="comment-item" data-cid="2">
    <div class="content">
      <div class="author"><span>2020-06-01 08:00:00</span><a>另一位读者</a></div>
      <p>第二条评论</p>
    </div>
  </div>
</div>
"""


class TestParseNoteComments:
    def test_parses_all_fields(self) -> None:
        comments = parse_note_comments(COMMENT_HTML)
        assert len(comments) == 2
        first = comments[0]
        assert first.comment_id == "57095888"
        assert first.author == "贫僧读物理"
        assert first.date == "2019-01-24 15:22:41"
        assert "利兹与青鸟" in first.content_html
        assert first.avatar_url.endswith("u151409267-5.jpg")

    def test_zero_comments(self) -> None:
        """没有评论的页面必须返回空列表而不是报错（此前正是这里被误判）。"""
        assert parse_note_comments('<div id="comments"></div>') == []
        assert parse_note_comments("<html><body>无评论容器</body></html>") == []

    def test_duplicate_cid_deduplicated(self) -> None:
        html = (
            '<div id="comments">'
            '<div class="comment-item" data-cid="1"><div class="content"><p>a</p></div></div>'
            '<div class="comment-item" data-cid="1"><div class="content"><p>b</p></div></div>'
            "</div>"
        )
        assert len(parse_note_comments(html)) == 1

    def test_missing_author_is_empty_not_crash(self) -> None:
        html = (
            '<div id="comments">'
            '<div class="comment-item" data-cid="9"><div class="content"><p>匿名</p></div></div>'
            "</div>"
        )
        comments = parse_note_comments(html)
        assert len(comments) == 1
        assert comments[0].author == ""
        assert comments[0].content_html == "匿名"

    def test_collects_all_comment_paragraphs(self) -> None:
        html = ('<div id="comments"><div class="comment-item" data-cid="10">'
                '<div class="content"><p>第一段</p><p>第二段 <b>保留格式</b></p></div>'
                '</div></div>')
        comment = parse_note_comments(html)[0]
        assert "第一段" in comment.content_html
        assert "第二段" in comment.content_html
        assert "<b>保留格式</b>" in comment.content_html

    def test_shares_logic_with_discussion(self) -> None:
        """论坛讨论帖与日记用的是同一套解析（结构一致）。"""
        assert parse_comment_items(
            __import__("bs4").BeautifulSoup(COMMENT_HTML, "lxml")
        ) == parse_note_comments(COMMENT_HTML)


class TestCommentPagination:
    def test_no_paginator_is_single_page(self) -> None:
        assert parse_note_comment_pages(COMMENT_HTML) == 1

    def test_reads_total_page(self) -> None:
        html = (
            '<div id="comments"><div class="paginator">'
            '<span class="thispage" data-total-page="4">1</span>'
            "</div></div>"
        )
        assert parse_note_comment_pages(html) == 4

    def test_missing_container_is_single_page(self) -> None:
        assert parse_note_comment_pages("<html></html>") == 1

    def test_invalid_value_is_single_page(self) -> None:
        html = '<div id="comments"><div class="paginator"><span data-total-page="x">1</span></div></div>'
        assert parse_note_comment_pages(html) == 1


class TestNoteModel:
    def test_note_has_comments_field(self) -> None:
        note = Note(note_id="1", widget_id="w")
        assert note.comments == []
        note.comments.append(Comment(author="a", comment_id="1"))
        assert len(note.comments) == 1

    def test_comment_id_serialised(self) -> None:
        assert Comment(author="a", comment_id="c1").to_dict()["comment_id"] == "c1"
