"""索引①/② 解析为分类映射。

首页的两条公告栏是站长**手工编排的分类目录**：

    ☆【穹庐下的魔女】
    <a>…访谈（CREA）</a>
    ☆【聲之形】（<a>豆列</a>）
    <a>《聲之形》原作者大今良时＆导演山田尚子寄语</a>
    <a>电影《聲之形》配乐牛尾宪辅＆主题歌演唱者aiko寄语</a>
    …

因此它天然就是 VitePress 的 sidebar 结构 —— 保留站长的编排意图，
比按抓取顺序平铺 144 篇文章体验好得多。本模块把它解析成结构化数据，
作为 sidebar 的**唯一事实源**。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable

from bs4 import BeautifulSoup, NavigableString, Tag

from .config import CONFIG, Config
from .html2md import unwrap_link2
from .models import Availability, IndexEntry, IndexGroup
from .parsers import NOTE_PATH_RE

log = logging.getLogger("usagi.index")

# 分组标题：☆【聲之形】 / ○ 常用链接
GROUP_MARKER_RE = re.compile(r"[☆★]\s*【\s*([^】]+?)\s*】")
SECTION_MARKER_RE = re.compile(r"[○●]\s*([^：:（(\n]+?)\s*[：:（(]?\s*$")

# 分组标题里括号内的豆列链接
DOULIST_LABEL = "豆列"

# 未在索引中出现的日记归入此分区
FALLBACK_CATEGORY = "Papico 日志"
LINKS_CATEGORY = "常用链接"


@dataclass
class _GroupBuilder:
    title: str
    doulist_url: str | None = None
    entries: list[IndexEntry] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.entries is None:
            self.entries = []


def _iter_in_order(
    node: Tag,
    on_text: Callable[[str], None],
    on_link: Callable[[Tag], None],
) -> None:
    """按文档顺序遍历，文本与链接分别回调。"""
    for child in node.children:
        if isinstance(child, NavigableString):
            on_text(str(child))
        elif isinstance(child, Tag):
            if child.name == "a":
                on_link(child)
            else:
                _iter_in_order(child, on_text, on_link)


def _clean_group_title(raw: str) -> str:
    title = raw.strip().strip("：: ")
    # 去掉可能残留的"（豆列）"之类的尾巴
    return re.sub(r"[（(]\s*[)）]\s*$", "", title).strip()


def parse_index(content_html: str, cfg: Config = CONFIG) -> list[IndexGroup]:
    """把一条索引公告的 HTML 解析成分组列表。"""
    if not content_html or not content_html.strip():
        return []

    soup = BeautifulSoup(content_html, "lxml")
    groups: list[IndexGroup] = []
    current: _GroupBuilder | None = None

    def start_group(title: str) -> None:
        nonlocal current
        cleaned = _clean_group_title(title)
        if not cleaned:
            return
        current = _GroupBuilder(title=cleaned)
        groups.append(IndexGroup(title=cleaned, doulist_url=None, entries=current.entries))

    def on_text(text: str) -> None:
        if not text.strip():
            return
        marker = GROUP_MARKER_RE.search(text)
        if marker:
            start_group(marker.group(1))
            return
        section = SECTION_MARKER_RE.search(text.strip())
        if section:
            # 形如"○ 常用链接："。必须无条件开启新分区，
            # 否则该分区下的链接会被错误归入上一个分组。
            start_group(section.group(1))

    def on_link(anchor: Tag) -> None:
        nonlocal current
        if current is None:
            # 索引开头的零散链接（如"豆列"）忽略，避免污染分类
            return
        href = unwrap_link2(str(anchor.get("href", "")).strip())
        label = " ".join(anchor.get_text(" ").split())
        if not href:
            return

        # 分组标题后的第一个"豆列"链接归属于该分组
        if label == DOULIST_LABEL and not current.entries and current.doulist_url is None:
            current.doulist_url = href
            groups[-1].doulist_url = href
            return

        note_id: str | None = None
        match = NOTE_PATH_RE.search(href)
        if match:
            note_id = match.group(2)

        if not label:
            label = href

        current.entries.append(
            IndexEntry(
                title=label,
                url=href,
                note_id=note_id,
                status=Availability.NOT_FETCHED,
            )
        )

    _iter_in_order(soup, on_text, on_link)

    # 丢掉空分组
    result = [g for g in groups if g.entries]
    log.info("索引解析出 %d 个分组，共 %d 条目", len(result), sum(len(g.entries) for g in result))
    return result


def build_note_to_group(
    groups: list[IndexGroup],
) -> dict[str, tuple[str, int]]:
    """构建 ``note_id → (分组名, 组内序号)`` 反查表。"""
    mapping: dict[str, tuple[str, int]] = {}
    for group in groups:
        for order, entry in enumerate(group.entries, start=1):
            if not entry.note_id:
                continue
            # 同一篇出现在多个分组时保留首次出现的位置
            mapping.setdefault(entry.note_id, (group.title, order))
    return mapping


def index_entry_urls(groups: list[IndexGroup]) -> list[IndexEntry]:
    """展平所有索引条目。"""
    return [entry for group in groups for entry in group.entries]


def group_by_category(
    note_ids: list[str],
    mapping: dict[str, tuple[str, int]],
    *,
    fallback: str = FALLBACK_CATEGORY,
) -> dict[str, list[str]]:
    """按分组归类 note；未被索引覆盖的归入 fallback。"""
    categories: dict[str, list[str]] = {}
    for note_id in note_ids:
        title = mapping.get(note_id, (fallback, 0))[0]
        categories.setdefault(title, []).append(note_id)
    return categories
