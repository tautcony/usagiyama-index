"""站点结构发现：房间 → 功能模块 → 内容 ID 全集。

增量同步的第一步就是"枚举源站 ID 全集"，再与本地 manifest 比对。
所有枚举函数都支持分页（``?start=N``），总页数取自列表页的
``data-total-page`` 属性。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import CONFIG, Config
from .models import Bulletin, PhotoMeta, Room, Video, Widget
from .parsers import (
    NoteListEntry,
    parse_album_title,
    parse_bulletin,
    parse_discussion_list,
    parse_note_list,
    parse_page_step,
    parse_photo_list,
    parse_room_nav,
    parse_site_meta,
    parse_total_pages,
    parse_video_list,
    parse_widgets,
)
from .resolver import PageResolver

log = logging.getLogger("usagi.discover")

# 列表页每页条数的兜底值（实测）。真实步长优先从分页链接里读，
# 见 :func:`parse_page_step`——写死的常量与实际不符时会静默漏抓。
NOTES_PER_PAGE = 10
PHOTOS_PER_PAGE = 30


@dataclass
class SiteStructure:
    """一次完整发现的结果。"""

    meta: dict[str, str] = field(default_factory=dict)
    rooms: list[Room] = field(default_factory=list)
    bulletins: list[Bulletin] = field(default_factory=list)
    note_entries: list[NoteListEntry] = field(default_factory=list)
    photo_ids: dict[str, list[str]] = field(default_factory=dict)
    album_titles: dict[str, str] = field(default_factory=dict)
    videos: list[Video] = field(default_factory=list)
    forum_topics: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    # -------------------------------------------------------------- 便捷视图

    def widgets_of(self, kind: str) -> list[Widget]:
        return [w for room in self.rooms for w in room.widgets if w.kind == kind]

    @property
    def note_ids(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for entry in self.note_entries:
            if entry.note_id not in seen:
                seen.add(entry.note_id)
                ordered.append(entry.note_id)
        return ordered

    @property
    def note_count(self) -> int:
        return len(self.note_ids)

    @property
    def photo_count(self) -> int:
        return sum(len(ids) for ids in self.photo_ids.values())

    def entry_by_note_id(self) -> dict[str, NoteListEntry]:
        """note_id → 列表页摘要（标题/日期/评论数），用于详情页缺失时兜底。"""
        mapping: dict[str, NoteListEntry] = {}
        for entry in self.note_entries:
            mapping.setdefault(entry.note_id, entry)
        return mapping

    def to_dict(self) -> dict[str, object]:
        return {
            "meta": self.meta,
            "rooms": [r.to_dict() for r in self.rooms],
            "bulletins": [b.to_dict() for b in self.bulletins],
            "noteCount": self.note_count,
            "noteIds": self.note_ids,
            "noteEntries": [
                {
                    "noteId": e.note_id,
                    "widgetId": e.widget_id,
                    "title": e.title,
                    "date": e.date,
                    "commentCount": e.comment_count,
                    "url": e.url,
                }
                for e in self.note_entries
            ],
            "photoIds": self.photo_ids,
            "albumTitles": self.album_titles,
            "photoCount": self.photo_count,
            "videos": [v.to_dict() for v in self.videos],
            "forumTopics": {k: [list(t) for t in v] for k, v in self.forum_topics.items()},
        }


def enumerate_album_photos(
    resolver: PageResolver,
    album_id: str,
    cfg: Config = CONFIG,
    *,
    first_html: str = "",
) -> list[PhotoMeta]:
    """翻页取回一个相册的全部照片（含缩略图与描述），按 ``photo_id`` 去重。

    调用方若已抓到第一页，用 ``first_html`` 传进来即可省一次请求。

    这里同时是全站唯一的相册翻页实现：发现阶段只要照片 ID，渲染阶段要
    完整条目，两边必须走同一套翻页逻辑，否则「枚举到的」与「页面上显示的」
    会不一致——曾因为只读第一页，页面把已归档的照片整批报成缺失。
    """
    if not first_html:
        page = resolver.resolve(cfg.photos_list_url(album_id), context=f"相册列表 {album_id}")
        if not page.has_content:
            return []
        first_html = page.html

    photos: list[PhotoMeta] = []
    seen: set[str] = set()

    def absorb(html: str) -> None:
        for meta in parse_photo_list(html, album_id, cfg):
            if meta.photo_id not in seen:
                seen.add(meta.photo_id)
                photos.append(meta)

    absorb(first_html)

    step = parse_page_step(first_html, cfg, PHOTOS_PER_PAGE)
    for index in range(1, parse_total_pages(first_html)):
        url = cfg.photos_list_url(album_id, index * step)
        sub = resolver.resolve(url, context=f"相册列表 {album_id} 第 {index + 1} 页")
        if sub.has_content:
            absorb(sub.html)

    return photos


class SiteDiscovery:
    """按站点层级逐层发现内容。"""

    def __init__(self, resolver: PageResolver, cfg: Config = CONFIG) -> None:
        self.resolver = resolver
        self.cfg = cfg
        self.structure = SiteStructure()

    # ------------------------------------------------------------ 房间与模块

    def discover_rooms(self) -> list[Room]:
        """抓首页 → 房间导航 → 逐个房间抓取其功能模块。"""
        home = self.resolver.resolve_required(self.cfg.site_url, context="首页")
        self.structure.meta = parse_site_meta(home.html, self.cfg)

        nav = parse_room_nav(home.html, self.cfg)
        log.info("发现 %d 个房间导航项", len(nav))

        rooms: list[Room] = []
        for room_id, title, url in nav:
            # 首页对应的房间会 302 回首页，直接用已抓到的 HTML
            html = home.html if url.rstrip("/") == self.cfg.site_url.rstrip("/") else ""
            if not html:
                page = self.resolver.resolve(url, context=f"房间 {title}")
                if not page.has_content:
                    room = Room(room_id=room_id, title=title, url=url)
                    room.status = page.status
                    rooms.append(room)
                    continue
                html = page.html

            room = Room(
                room_id=room_id,
                title=title,
                url=url,
                is_home=url.rstrip("/") == self.cfg.site_url.rstrip("/"),
                widgets=parse_widgets(html, room_id, self.cfg),
            )
            room.status = home.status if html is home.html else page.status
            rooms.append(room)
            log.info("  房间 %s(%s)：%d 个模块", title, room_id, len(room.widgets))

        self.structure.rooms = rooms
        return rooms

    # ---------------------------------------------------------------- 公告栏

    def discover_bulletins(self) -> list[Bulletin]:
        """抓取所有公告栏（含索引①/②）。"""
        bulletins: list[Bulletin] = []
        for widget in self.structure.widgets_of("bulletin"):
            url = f"{self.cfg.base_url}/room/{widget.room_id}/"
            page = self.resolver.resolve(url, context=f"公告栏 {widget.title}")
            if not page.has_content:
                bulletin = Bulletin(
                    bulletin_id=widget.widget_id,
                    room_id=widget.room_id,
                    title=widget.title,
                    source_url=url,
                    status=page.status,
                )
                bulletins.append(bulletin)
                continue
            bulletin = parse_bulletin(
                page.html, widget.widget_id, url, widget.room_id, self.cfg
            )
            if not bulletin.title:
                bulletin.title = widget.title
            bulletin.status = page.status
            bulletins.append(bulletin)
            log.info("  公告栏 %s：%d 字", bulletin.title, len(bulletin.content_html))

        self.structure.bulletins = bulletins
        return bulletins

    # ------------------------------------------------------------------ 日记

    def enumerate_notes(self, widget_id: str) -> list[NoteListEntry]:
        """翻页枚举一个日记模块的全部条目。"""
        entries: list[NoteListEntry] = []
        first_url = self.cfg.notes_list_url(widget_id)
        page = self.resolver.resolve(first_url, context=f"日记列表 {widget_id}")
        if not page.has_content:
            log.warning("日记列表不可访问：%s", widget_id)
            return entries

        total_pages = parse_total_pages(page.html)
        step = parse_page_step(page.html, self.cfg, NOTES_PER_PAGE)
        entries.extend(parse_note_list(page.html, widget_id, self.cfg))

        for index in range(1, total_pages):
            start = index * step
            url = self.cfg.notes_list_url(widget_id, start)
            sub = self.resolver.resolve(url, context=f"日记列表 {widget_id} 第 {index + 1} 页")
            if not sub.has_content:
                continue
            entries.extend(parse_note_list(sub.html, widget_id, self.cfg))

        log.info("  日记模块 %s：%d 条（共 %d 页）", widget_id, len(entries), total_pages)
        return entries

    def discover_notes(self) -> list[NoteListEntry]:
        all_entries: list[NoteListEntry] = []
        for widget in self.structure.widgets_of("notes"):
            all_entries.extend(self.enumerate_notes(widget.widget_id))
        self.structure.note_entries = all_entries
        log.info("日记条目合计（含重复）：%d，去重后：%d", len(all_entries), self.structure.note_count)
        return all_entries

    # ------------------------------------------------------------------ 相册

    def enumerate_photos(self, album_id: str) -> list[str]:
        """翻页枚举一个相册的全部照片 ID。"""
        first_url = self.cfg.photos_list_url(album_id)
        page = self.resolver.resolve(first_url, context=f"相册列表 {album_id}")
        if not page.has_content:
            log.warning("相册列表不可访问：%s", album_id)
            return []

        self.structure.album_titles.setdefault(album_id, parse_album_title(page.html, self.cfg))

        photos = enumerate_album_photos(self.resolver, album_id, self.cfg, first_html=page.html)
        log.info(
            "  相册 %s：%d 张（共 %d 页）", album_id, len(photos), parse_total_pages(page.html)
        )
        return [meta.photo_id for meta in photos]

    def discover_photos(self) -> dict[str, list[str]]:
        for widget in self.structure.widgets_of("photos"):
            self.structure.photo_ids[widget.widget_id] = self.enumerate_photos(widget.widget_id)
        log.info("照片合计：%d 张", self.structure.photo_count)
        return self.structure.photo_ids

    # ------------------------------------------------------------------ 视频

    def discover_videos(self) -> list[Video]:
        videos: list[Video] = []
        seen: set[str] = set()
        for widget in self.structure.widgets_of("videos"):
            # 视频模块的独立列表页会 302，列表数据在房间页内
            url = f"{self.cfg.base_url}/room/{widget.room_id}/"
            page = self.resolver.resolve(url, context=f"视频列表 {widget.widget_id}")
            if not page.has_content:
                continue
            for video in parse_video_list(page.html, widget.widget_id, self.cfg):
                if video.video_id in seen:
                    continue
                seen.add(video.video_id)
                videos.append(video)
        self.structure.videos = videos
        log.info("视频条目：%d", len(videos))
        return videos

    # ------------------------------------------------------------------ 论坛

    def discover_forum(self) -> dict[str, list[tuple[str, str]]]:
        for widget in self.structure.widgets_of("forum"):
            url = self.cfg.forum_url(widget.widget_id)
            page = self.resolver.resolve(url, context=f"论坛 {widget.title}")
            if not page.has_content:
                continue
            self.structure.forum_topics[widget.widget_id] = parse_discussion_list(
                page.html, widget.widget_id, self.cfg
            )
        total = sum(len(v) for v in self.structure.forum_topics.values())
        log.info("论坛话题：%d", total)
        return self.structure.forum_topics

    # -------------------------------------------------------------------- 总

    def crawl_structure(self) -> SiteStructure:
        """完整发现流程（只抓列表页与骨架页，不抓详情）。"""
        log.info("=== 1/6 房间与模块 ===")
        self.discover_rooms()
        log.info("=== 2/6 公告栏与索引 ===")
        self.discover_bulletins()
        log.info("=== 3/6 日记列表 ===")
        self.discover_notes()
        log.info("=== 4/6 相册列表 ===")
        self.discover_photos()
        log.info("=== 5/6 视频 ===")
        self.discover_videos()
        log.info("=== 6/6 论坛 ===")
        self.discover_forum()
        return self.structure
