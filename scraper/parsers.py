"""HTML → 结构化数据。

所有选择器均基于对目标站点的实测结果，集中在此处便于源站改版时定位修复点。
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, Tag

from .config import CONFIG, Config
from .models import (
    Album,
    Bulletin,
    Comment,
    Discussion,
    MiniblogStatus,
    Note,
    PhotoMeta,
    Room,
    SourceStatus,
    Video,
    Widget,
)

log = logging.getLogger("usagi.parse")

# 房间页面内的功能模块：<div class="mod" id="notes-17565710">
WIDGET_RE = re.compile(r"^(bulletin|notes|photos|videos|forum|miniblog)-(\d+)$")
# 房间导航：<li ...><a href=".../room/2793793/"><span>宇宙的入口</span></a>
ROOM_LINK_RE = re.compile(r"/211330/room/(\d+)/?$")
# 日记详情路径
NOTE_PATH_RE = re.compile(r"/widget/notes/(\d+)/note/(\d+)/")
# 相册详情路径
PHOTO_PATH_RE = re.compile(r"/widget/photos/(\d+)/photo/(\d+)/")
# 视频路径
VIDEO_PATH_RE = re.compile(r"/widget/videos/(\d+)/video/(\d+)/")
# 讨论帖路径
DISCUSSION_PATH_RE = re.compile(r"/widget/forum/(\d+)/discussion/(\d+)/")
# 回应数："(3回应)" 或 "3回应"（不同位置括号可有可无）
COMMENT_COUNT_RE = re.compile(r"\(?\s*(\d+)\s*回应\s*\)?")
# 标题后缀
TITLE_SUFFIX_RE = re.compile(r"\s*[（(](?:兔子山的小站|豆瓣)[)）]\s*$")
# 相册大图 URL
PHOTO_SIZE_RE = re.compile(r"/view/photo/([a-z]+)/public/(p\d+\.\w+)$")
# 日记图片 URL
NOTE_IMG_RE = re.compile(r"/view/note/([a-z]+)/public/(\w+\.\w+)$")
# 日期
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?")
# 视频上传日期
VIDEO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*上传")


def make_soup(html: str, cfg: Config = CONFIG) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def clean_title(raw: str) -> str:
    """剥离豆瓣附加的站点名后缀。"""
    if not raw:
        return ""
    return TITLE_SUFFIX_RE.sub("", raw.replace("\n", " ")).strip()


def parse_date(text: str) -> str:
    match = DATE_RE.search(text or "")
    return match.group(0) if match else ""


def parse_comment_count(text: str) -> int:
    match = COMMENT_COUNT_RE.search(text or "")
    return int(match.group(1)) if match else 0


def _link_report(soup: BeautifulSoup, note_id: str = "") -> str:
    """提取正文容器 ``#link-report`` 的内部 HTML。"""
    if note_id:
        full = soup.find(id=f"note_{note_id}_full")
        if isinstance(full, Tag):
            inner = full.find(id="link-report")
            return (inner or full).decode_contents()
    node = soup.find(id="link-report")
    return node.decode_contents() if isinstance(node, Tag) else ""


# ------------------------------------------------------------------ 站点骨架


def parse_site_meta(html: str, cfg: Config = CONFIG) -> dict[str, str]:
    """从首页提取小站元信息。"""
    soup = make_soup(html, cfg)
    meta: dict[str, str] = {"name": cfg.site_name}

    title = soup.find("title")
    if isinstance(title, Tag):
        name = clean_title(title.get_text())
        if name:
            meta["name"] = name

    desc = soup.select_one("#sp-user .desc")
    if isinstance(desc, Tag):
        text = " ".join(desc.get_text(" ").split())
        if text:
            meta["description"] = text

    avatar = soup.select_one("#sp-user .user-pic img")
    if isinstance(avatar, Tag) and avatar.get("src"):
        meta["avatar"] = str(avatar["src"])

    return meta


def parse_room_nav(html: str, cfg: Config = CONFIG) -> list[tuple[str, str, str]]:
    """解析首页房间导航，返回 ``[(room_id, title, url)]``（保持原站顺序）。"""
    soup = make_soup(html, cfg)
    rooms: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select(".nav-items a[href]"):
        href = str(anchor.get("href", ""))
        match = ROOM_LINK_RE.search(urlparse(href).path)
        if not match:
            continue
        room_id = match.group(1)
        if room_id in seen:
            continue
        seen.add(room_id)
        title = " ".join(anchor.get_text(" ").split())
        rooms.append((room_id, title, href))
    return rooms


def parse_widgets(html: str, room_id: str, cfg: Config = CONFIG) -> list[Widget]:
    """解析房间页面内的功能模块清单。"""
    soup = make_soup(html, cfg)
    widgets: list[Widget] = []
    seen: set[tuple[str, str]] = set()
    for node in soup.find_all("div", class_="mod", id=True):
        match = WIDGET_RE.match(str(node.get("id", "")))
        if not match:
            continue
        kind, widget_id = match.group(1), match.group(2)
        if (kind, widget_id) in seen:
            continue
        seen.add((kind, widget_id))
        heading = node.find("h2")
        title = ""
        if isinstance(heading, Tag):
            span = heading.find("span")
            title = " ".join((span or heading).get_text(" ").split())
        widgets.append(Widget(kind=kind, widget_id=widget_id, room_id=room_id, title=title))
    return widgets


# -------------------------------------------------------------------- 公告栏


def parse_bulletin(html: str, bulletin_id: str, url: str, room_id: str = "",
                   cfg: Config = CONFIG) -> Bulletin:
    """解析公告栏。

    一个房间可能包含**多个**公告栏（首页就同时挂着索引①与索引②），
    因此必须按 ``#bulletin-{id}`` 精确定位容器，不能直接取页面里
    第一个 ``#link-report`` —— 否则所有公告都会读到同一份内容。
    """
    soup = make_soup(html, cfg)

    container = soup.find(id=f"bulletin-{bulletin_id}")
    scope = container if isinstance(container, Tag) else soup

    title = ""
    heading = scope.find("h2")
    if isinstance(heading, Tag):
        span = heading.find("span")
        title = " ".join((span or heading).get_text(" ").split())
    if not title:
        node = soup.find("title")
        title = clean_title(node.get_text()) if isinstance(node, Tag) else bulletin_id

    body = scope.find(id="link-report")
    content = body.decode_contents() if isinstance(body, Tag) else ""
    if not content and scope is soup:
        content = _link_report(soup)

    return Bulletin(
        bulletin_id=bulletin_id,
        room_id=room_id,
        title=title,
        content_html=content,
        source_url=url,
        status=SourceStatus(
            availability="ok" if content.strip() else "unavailable",
            detail="" if content.strip() else "未找到公告内容容器",
        ),
    )


def parse_index_bulletin_content(html: str, cfg: Config = CONFIG) -> str:
    """首页的索引公告（索引①/②）正文 HTML。"""
    return _link_report(make_soup(html, cfg))


# ---------------------------------------------------------------------- 日记


def parse_total_pages(html: str) -> int:
    match = re.search(r'data-total-page="(\d+)"', html or "")
    return int(match.group(1)) if match else 1


#: 分页链接里的页偏移，形如 ``?start=30``
_PAGE_START_RE = re.compile(r"[?&]start=(\d+)")


def parse_page_step(html: str, cfg: Config = CONFIG, fallback: int = 1) -> int:
    """从分页链接推导「每页条数」。

    站点用 ``?start=N`` 标记页偏移，相邻页码之差就是每页条数。

    取**最小**间距是有意的：分页器里可能混着跨页跳转（如「首页」直接跳回
    ``start=0``），而步长只要不超过真实页容量就不会漏抓（多走一页只是
    重复解析、按 ID 去重后无害）；一旦大于页容量，每个列表尾部都会有
    若干条目永远枚举不到——相册曾按 26 计算，而实际每页 30 张。
    """
    soup = make_soup(html, cfg)
    starts = sorted(
        {
            int(match.group(1))
            for anchor in soup.select(".paginator a[href]")
            if (match := _PAGE_START_RE.search(str(anchor.get("href", ""))))
        }
    )
    steps = [b - a for a, b in zip(starts, starts[1:]) if b > a]
    if not steps:
        return fallback
    step = min(steps)
    # 步长 1（或 0）必然是误读，照做会把列表页逐条翻一遍
    return step if step > 1 else fallback


class NoteListEntry:
    """日记列表页的一条摘要。"""

    __slots__ = ("note_id", "widget_id", "title", "date", "comment_count", "url", "summary")

    def __init__(self, note_id: str, widget_id: str, title: str, date: str,
                 comment_count: int, url: str, summary: str = "") -> None:
        self.note_id = note_id
        self.widget_id = widget_id
        self.title = title
        self.date = date
        self.comment_count = comment_count
        self.url = url
        self.summary = summary

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<NoteListEntry {self.note_id} {self.title[:20]!r}>"


# 日记列表有两种页面结构，必须都支持：
#   内嵌列表（房间页）：<div class="item-entry">  +  .title a
#   独立列表（模块页）：<div class="note-item" id="note-{id}"> + .note-hd h3 a
NOTE_ITEM_SELECTORS = (".item-entry", ".note-item")
NOTE_TITLE_SELECTORS = (".title a[href]", ".note-hd h3 a[href]")


def _note_entry_from(item: Tag, widget_id: str) -> NoteListEntry | None:
    """从条目容器中提取摘要，兼容两种页面结构。"""
    anchor: Tag | None = None
    for selector in NOTE_TITLE_SELECTORS:
        found = item.select_one(selector)
        if isinstance(found, Tag):
            anchor = found
            break
    if anchor is None:
        return None

    href = str(anchor.get("href", ""))
    match = NOTE_PATH_RE.search(urlparse(href).path)
    if not match:
        return None

    title = " ".join((anchor.get("title") or anchor.get_text(" ")).split())
    date_node = item.select_one(".datetime")
    summary_node = item.select_one(".summary")

    # 评论数：优先读指向 #comments 的链接，其次在整条文本里找 "(N回应)"
    count = 0
    comment_link = item.select_one('a[href*="#comments"]')
    if isinstance(comment_link, Tag):
        count = parse_comment_count(comment_link.get_text(" "))
    if not count:
        count = parse_comment_count(item.get_text(" "))

    return NoteListEntry(
        note_id=match.group(2),
        widget_id=match.group(1) or widget_id,
        title=title,
        date=parse_date(date_node.get_text()) if isinstance(date_node, Tag) else "",
        comment_count=count,
        url=href,
        summary=" ".join(summary_node.get_text(" ").split()) if isinstance(summary_node, Tag) else "",
    )


def parse_note_list(html: str, widget_id: str, cfg: Config = CONFIG) -> list[NoteListEntry]:
    """解析日记列表页（含分页），兼容内嵌列表与独立列表两种结构。"""
    soup = make_soup(html, cfg)
    entries: list[NoteListEntry] = []
    seen: set[str] = set()

    for selector in NOTE_ITEM_SELECTORS:
        for item in soup.select(selector):
            entry = _note_entry_from(item, widget_id)
            if entry is None or entry.note_id in seen:
                continue
            seen.add(entry.note_id)
            entries.append(entry)
    return entries


def parse_note(html: str, widget_id: str, note_id: str, url: str,
               cfg: Config = CONFIG) -> Note:
    """解析日记详情页。"""
    soup = make_soup(html, cfg)

    title_node = soup.find("title")
    title = clean_title(title_node.get_text()) if isinstance(title_node, Tag) else ""

    # 详情页标题在 <h1> 里更准确，优先使用
    h1 = soup.find("h1")
    if isinstance(h1, Tag):
        candidate = " ".join(h1.get_text(" ").split())
        if candidate:
            title = candidate

    date_node = soup.select_one(".datetime")
    date = parse_date(date_node.get_text()) if isinstance(date_node, Tag) else ""

    content = _link_report(soup, note_id)
    note = Note(
        note_id=note_id,
        widget_id=widget_id,
        title=title,
        date=date,
        content_html=content,
        comment_count=parse_comment_count(soup.get_text(" ")),
        source_url=url,
        status=SourceStatus(
            availability="ok" if content.strip() else "unavailable",
            detail="" if content.strip() else "正文容器为空",
        ),
    )
    return note


# ---------------------------------------------------------------------- 相册


def parse_album_title(html: str, cfg: Config = CONFIG) -> str:
    soup = make_soup(html, cfg)
    h1 = soup.find("h1")
    if isinstance(h1, Tag):
        return " ".join(h1.get_text(" ").split())
    node = soup.find("title")
    return clean_title(node.get_text()) if isinstance(node, Tag) else ""


def parse_photo_list(html: str, album_id: str, cfg: Config = CONFIG) -> list[PhotoMeta]:
    """解析相册列表页。"""
    soup = make_soup(html, cfg)
    photos: list[PhotoMeta] = []
    seen: set[str] = set()

    for anchor in soup.select("a.album_photo[href]"):
        href = str(anchor.get("href", ""))
        match = PHOTO_PATH_RE.search(urlparse(href).path)
        if not match:
            continue
        photo_id = match.group(2)
        if photo_id in seen:
            continue
        seen.add(photo_id)

        img = anchor.find("img")
        thumb = str(img.get("src", "")) if isinstance(img, Tag) else ""
        caption = (anchor.get("title") or anchor.get("alt") or "").strip()
        if not caption:
            desc = anchor.parent.select_one(".desc p") if anchor.parent else None
            if isinstance(desc, Tag):
                caption = " ".join(desc.get_text(" ").split())

        photos.append(
            PhotoMeta(
                photo_id=photo_id,
                album_id=match.group(1),
                caption=caption,
                thumb_url=thumb,
                source_url=href,
                status=SourceStatus(availability="ok"),
            )
        )
    return photos


def parse_photo_detail(html: str, album_id: str, photo_id: str, url: str,
                       cfg: Config = CONFIG) -> PhotoMeta:
    """解析相册详情页，提取大图 URL 与完整描述。"""
    soup = make_soup(html, cfg)
    large = ""
    for img in soup.find_all("img"):
        src = str(img.get("src", ""))
        match = PHOTO_SIZE_RE.search(urlparse(src).path)
        if match and match.group(2).startswith(f"p{photo_id}"):
            if match.group(1) == "large":
                large = src
                break
            if match.group(1) == "photo" and not large:
                large = src

    caption = ""
    node = soup.select_one(".photo-desc") or soup.select_one("#link-report")
    if isinstance(node, Tag):
        caption = " ".join(node.get_text(" ").split())
    if not caption:
        title_node = soup.find("title")
        caption = clean_title(title_node.get_text()) if isinstance(title_node, Tag) else ""

    return PhotoMeta(
        photo_id=photo_id,
        album_id=album_id,
        caption=caption,
        large_url=large,
        source_url=url,
        status=SourceStatus(
            availability="ok" if large else "unavailable",
            detail="" if large else "未找到大图 URL",
        ),
    )


# ---------------------------------------------------------------------- 论坛


def parse_comment_items(scope: BeautifulSoup | Tag) -> list[Comment]:
    """解析 ``.comment-item`` 列表。

    日记详情页与论坛讨论帖用的是同一套评论结构，因此共用这段逻辑。
    按 ``data-cid`` 去重，避免翻页时重复计入。
    """
    comments: list[Comment] = []
    seen: set[str] = set()
    for item in scope.select(".comment-item"):
        cid = str(item.get("data-cid") or item.get("id") or "").strip()
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)

        avatar = item.select_one(".pic img")
        author_node = item.select_one(".content .author")
        body = item.select_one(".content p")
        author = ""
        date = ""
        if isinstance(author_node, Tag):
            anchors = author_node.find_all("a")
            if anchors:
                author = anchors[-1].get_text(strip=True)
            date = parse_date(author_node.get_text())
        comments.append(
            Comment(
                author=author,
                date=date,
                content_html=body.decode_contents() if isinstance(body, Tag) else "",
                avatar_url=str(avatar.get("src", "")) if isinstance(avatar, Tag) else "",
                comment_id=cid,
            )
        )
    return comments


#: 站外页面的正文容器候选。豆瓣主站不同页面用的容器不同，按顺序尝试。
EXTERNAL_CONTENT_SELECTORS = (
    "#link-report",
    ".topic-content",
    ".note-content",
    ".article",
    "article",
    "#content .main",
)

#: 站外页面的标题候选
EXTERNAL_TITLE_SELECTORS = ("h1", ".topic-title", ".note-header h1", "#content h1")


def parse_external_page(html: str, url: str, page_id: str, origin: str = "",
                        cfg: Config = CONFIG) -> "ExternalPage":
    """解析豆瓣主站上的独立页面（``/topic/``、``/note/`` 等）。

    这些页面的 DOM 结构不如小站规整，因此正文与标题都用**候选选择器依次尝试**，
    取第一个有实际内容的。
    """
    from .models import ExternalPage

    soup = make_soup(html, cfg)

    title = ""
    for selector in EXTERNAL_TITLE_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            candidate = " ".join(node.get_text(" ").split())
            if candidate:
                title = clean_title(candidate)
                break
    if not title:
        node = soup.find("title")
        title = clean_title(node.get_text()) if isinstance(node, Tag) else url

    content = ""
    for selector in EXTERNAL_CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag) and node.get_text(strip=True):
            content = node.decode_contents()
            break

    comments = parse_comment_items(soup)

    return ExternalPage(
        page_id=page_id,
        url=url,
        title=title,
        content_html=content,
        origin=origin,
        comments=comments,
        status=SourceStatus(
            availability="ok" if content.strip() else "unavailable",
            detail="" if content.strip() else "未找到正文容器",
        ),
    )


def parse_note_comments(html: str, cfg: Config = CONFIG) -> list[Comment]:
    """解析日记详情页的评论。

    评论是**服务端静态渲染**的，就在 ``<div id="comments">`` 里，
    免登录、免 AJAX、免滚动。
    """
    soup = make_soup(html, cfg)
    scope = soup.find(id="comments")
    return parse_comment_items(scope if isinstance(scope, Tag) else soup)


def parse_note_comment_pages(html: str, cfg: Config = CONFIG) -> int:
    """读 ``#comments`` 内的分页器，返回评论总页数（无分页器则为 1）。

    评论翻页用的是 note URL 上的 ``?start=N``（每页 10 条）。
    """
    soup = make_soup(html, cfg)
    scope = soup.find(id="comments")
    if not isinstance(scope, Tag):
        return 1
    marker = scope.select_one(".paginator .thispage[data-total-page]")
    if isinstance(marker, Tag):
        raw = str(marker.get("data-total-page", ""))
        if raw.isdigit():
            return max(1, int(raw))
    return 1


def parse_discussion_list(html: str, forum_id: str, cfg: Config = CONFIG) -> list[tuple[str, str]]:
    """解析论坛话题列表，返回 ``[(discussion_id, title)]``。"""
    soup = make_soup(html, cfg)
    topics: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("table.list-b a[href]"):
        href = str(anchor.get("href", ""))
        match = DISCUSSION_PATH_RE.search(urlparse(href).path)
        if not match:
            continue
        discussion_id = match.group(2)
        if discussion_id in seen:
            continue
        seen.add(discussion_id)
        title = (anchor.get("title") or anchor.get_text(" ")).strip()
        topics.append((discussion_id, " ".join(title.split())))
    return topics


def parse_discussion(html: str, forum_id: str, discussion_id: str, url: str,
                     cfg: Config = CONFIG) -> Discussion:
    """解析讨论帖（楼主正文 + 静态渲染的评论）。"""
    soup = make_soup(html, cfg)

    h1 = soup.find("h1")
    title = " ".join(h1.get_text(" ").split()) if isinstance(h1, Tag) else ""

    post = soup.select_one(".post-content")
    author = ""
    date = ""
    content = ""
    if isinstance(post, Tag):
        info = post.select_one(".post-info")
        if isinstance(info, Tag):
            date = parse_date(info.get_text())
            from_node = info.select_one(".from a")
            if isinstance(from_node, Tag):
                author = from_node.get_text(strip=True)
        content = _link_report(soup)

    comments = parse_comment_items(soup)

    return Discussion(
        discussion_id=discussion_id,
        forum_id=forum_id,
        title=title,
        author=author,
        date=date,
        content_html=content,
        source_url=url,
        comments=comments,
        status=SourceStatus(availability="ok" if content.strip() else "unavailable"),
    )


# -------------------------------------------------------------------- 广播室


def parse_miniblog(html: str, cfg: Config = CONFIG) -> list[MiniblogStatus]:
    """解析广播室动态流。"""
    soup = make_soup(html, cfg)
    statuses: list[MiniblogStatus] = []
    seen: set[str] = set()

    for item in soup.select(".status-item[data-sid]"):
        sid = str(item.get("data-sid", ""))
        if not sid or sid in seen:
            continue
        seen.add(sid)

        calendar = item.select_one(".hd .calendar")
        date = ""
        if isinstance(calendar, Tag):
            # 结构为 <a class="calendar">十一月<em>26</em></a>，
            # 直接取整段文本即可得到"十一月26"，不要再单独拼 em
            date = calendar.get_text("", strip=True)

        link = item.select_one("h5 a[href]")
        text_node = item.select_one(".text")
        desc_node = item.select_one(".description")
        media = item.select_one(".media img")

        statuses.append(
            MiniblogStatus(
                status_id=sid,
                date=date,
                text=" ".join(text_node.get_text(" ").split()) if isinstance(text_node, Tag) else "",
                link_url=str(link.get("href", "")) if isinstance(link, Tag) else "",
                link_title=" ".join(link.get_text(" ").split()) if isinstance(link, Tag) else "",
                image_url=str(media.get("src", "")) if isinstance(media, Tag) else "",
            )
        )
    return statuses


# ---------------------------------------------------------------------- 视频


def parse_video_list(html: str, widget_id: str, cfg: Config = CONFIG) -> list[Video]:
    """解析视频列表（缩略图 + 优酷外链）。"""
    soup = make_soup(html, cfg)
    videos: list[Video] = []
    seen: set[str] = set()

    for item in soup.select(".item-video"):
        anchor = item.select_one(".pic a[href]")
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor.get("href", ""))
        match = VIDEO_PATH_RE.search(urlparse(href).path)
        if not match:
            continue
        video_id = match.group(2)
        if video_id in seen:
            continue
        seen.add(video_id)

        img = anchor.find("img")
        thumb = str(img.get("src", "")) if isinstance(img, Tag) else ""
        external = str(img.get("name", "")) if isinstance(img, Tag) else ""

        title_node = item.select_one(".info a")
        title = " ".join(title_node.get_text(" ").split()) if isinstance(title_node, Tag) else ""
        info_text = item.select_one(".info")
        date_match = VIDEO_DATE_RE.search(info_text.get_text(" ") if isinstance(info_text, Tag) else "")

        videos.append(
            Video(
                video_id=video_id,
                widget_id=widget_id,
                title=title,
                thumb_url=thumb,
                external_url=external or unquote(external),
                date=date_match.group(1) if date_match else "",
                source_url=href,
                status=SourceStatus(availability="ok"),
            )
        )
    return videos


def build_room(room_id: str, title: str, url: str, html: str,
               cfg: Config = CONFIG) -> Room:
    room = Room(room_id=room_id, title=title, url=url, widgets=parse_widgets(html, room_id, cfg))
    room.status = SourceStatus(availability="ok")
    return room
