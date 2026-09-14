"""索引①/② 解析测试。

索引是 sidebar 的唯一事实源，解析错了整个导航就错，因此重点覆盖。
"""

from __future__ import annotations

from scraper.index_map import (
    FALLBACK_CATEGORY,
    build_note_to_group,
    group_by_category,
    parse_index,
)

# 与首页索引公告的真实结构一致：分组标题 + 若干 link2 包裹的条目
INDEX_HTML = (
    "☆【穹庐下的魔女】<br>"
    '<a rel="nofollow" href="https://www.douban.com/link2/?url=https%3A%2F%2Fwww.douban.com'
    '%2Ftopic%2F499780453%2F">“珍视角色”——《穹庐下的魔女》总导演山田尚子访谈（CREA）</a><br>'
    "☆【聲之形】（"
    '<a rel="nofollow" href="https://www.douban.com/link2/?url=https%3A%2F%2Fwww.douban.com'
    '%2Fdoulist%2F44247823%2F">豆列</a>）<br>'
    '<a rel="nofollow" href="https://www.douban.com/link2/?url=http%3A%2F%2Fsite.douban.com'
    '%2F211330%2Fwidget%2Fnotes%2F190597056%2Fnote%2F520557685%2F" target="_blank">'
    "《聲之形》原作者大今良时＆导演山田尚子寄语</a><br>"
    '<a rel="nofollow" href="https://www.douban.com/link2/?url=https%3A%2F%2Fsite.douban.com'
    '%2F211330%2Fwidget%2Fnotes%2F190597056%2Fnote%2F575910736%2F" target="_blank">'
    "电影《聲之形》配乐牛尾宪辅＆主题歌演唱者aiko寄语</a><br>"
    "○ 常用链接："
    '<a href="https://www.douban.com/link2/?url=http%3A%2F%2Fwww.kyotoanimation.co.jp%2F">【京アニHP】</a>'
)


class TestParseIndex:
    def test_groups_found(self) -> None:
        groups = parse_index(INDEX_HTML)
        titles = [g.title for g in groups]
        assert "穹庐下的魔女" in titles
        assert "聲之形" in titles

    def test_entries_belong_to_right_group(self) -> None:
        groups = parse_index(INDEX_HTML)
        by_title = {g.title: g for g in groups}
        assert len(by_title["穹庐下的魔女"].entries) == 1
        assert len(by_title["聲之形"].entries) == 2
        assert "大今良时" in by_title["聲之形"].entries[0].title

    def test_doulist_extracted_not_counted_as_entry(self) -> None:
        groups = parse_index(INDEX_HTML)
        sheng = next(g for g in groups if g.title == "聲之形")
        assert sheng.doulist_url == "https://www.douban.com/doulist/44247823/"
        assert all(e.title != "豆列" for e in sheng.entries)

    def test_link2_unwrapped(self) -> None:
        groups = parse_index(INDEX_HTML)
        first = groups[0].entries[0]
        assert first.url == "https://www.douban.com/topic/499780453/"
        assert "link2" not in first.url

    def test_note_id_extracted_from_site_url(self) -> None:
        groups = parse_index(INDEX_HTML)
        sheng = next(g for g in groups if g.title == "聲之形")
        assert [e.note_id for e in sheng.entries] == ["520557685", "575910736"]

    def test_external_entry_has_no_note_id(self) -> None:
        groups = parse_index(INDEX_HTML)
        assert groups[0].entries[0].note_id is None

    def test_section_marker_creates_group(self) -> None:
        groups = parse_index(INDEX_HTML)
        assert any("常用链接" in g.title for g in groups)

    def test_empty_input(self) -> None:
        assert parse_index("") == []
        assert parse_index("   ") == []

    def test_group_without_entries_dropped(self) -> None:
        assert parse_index("☆【空分组】<br>") == []


class TestNoteToGroup:
    def test_mapping(self) -> None:
        groups = parse_index(INDEX_HTML)
        mapping = build_note_to_group(groups)
        assert mapping["520557685"] == ("聲之形", 1)
        assert mapping["575910736"] == ("聲之形", 2)

    def test_first_occurrence_wins(self) -> None:
        html = (
            "☆【A】<br>"
            '<a href="http://site.douban.com/211330/widget/notes/1/note/111/">x</a>'
            "☆【B】<br>"
            '<a href="http://site.douban.com/211330/widget/notes/1/note/111/">x</a>'
        )
        mapping = build_note_to_group(parse_index(html))
        assert mapping["111"][0] == "A"


class TestGroupByCategory:
    def test_unindexed_notes_fall_back(self) -> None:
        groups = parse_index(INDEX_HTML)
        mapping = build_note_to_group(groups)
        categories = group_by_category(["520557685", "999999"], mapping)
        assert categories["聲之形"] == ["520557685"]
        assert categories[FALLBACK_CATEGORY] == ["999999"]

    def test_all_unindexed(self) -> None:
        categories = group_by_category(["1", "2"], {})
        assert categories == {FALLBACK_CATEGORY: ["1", "2"]}
