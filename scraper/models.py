"""数据模型与"可访问性"标记。

设计要点：**每一个抓取对象都带 `status` 字段**，用于标记源站不可访问的情况，
以及是否已通过 Internet Archive 补足。这是"页面无法访问的需要标记"要求的落点。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Availability(StrEnum):
    """抓取对象的可访问性状态。"""

    OK = "ok"
    """源站正常返回，内容已归档。"""

    UNAVAILABLE = "unavailable"
    """源站返回 403/404/410 等，无法直接归档，且未找到 archive.org 快照。"""

    ARCHIVED = "archived"
    """源站不可访问，但已从 Internet Archive 取到快照并归档。"""

    ARCHIVE_MISSING = "archive_missing"
    """源站不可访问，且 archive.org 也没有可用快照。内容缺失，仅保留元信息。"""

    LOGIN_REQUIRED = "login_required"
    """需要登录才能访问（如 www.douban.com 的日记/话题页）。"""

    EXTERNAL = "external"
    """站外链接，不在归档范围内，仅保留外链。"""

    NOT_FETCHED = "not_fetched"
    """尚未抓取。"""

    @property
    def is_ok(self) -> bool:
        return self is Availability.OK

    @property
    def needs_notice(self) -> bool:
        """是否需要在渲染出的页面上显示提示块。"""
        return self in {
            Availability.UNAVAILABLE,
            Availability.ARCHIVED,
            Availability.ARCHIVE_MISSING,
            Availability.LOGIN_REQUIRED,
        }


# 状态 → 页面提示文案
STATUS_LABELS: dict[Availability, str] = {
    Availability.OK: "已归档",
    Availability.UNAVAILABLE: "原站不可访问",
    Availability.ARCHIVED: "原站不可访问，已从 Internet Archive 补足",
    Availability.ARCHIVE_MISSING: "原站与 Internet Archive 均无法获取",
    Availability.LOGIN_REQUIRED: "需要登录，无法归档",
    Availability.EXTERNAL: "站外链接",
    Availability.NOT_FETCHED: "尚未抓取",
}


@dataclass
class SourceStatus:
    """一个对象的来源与可访问性记录。"""

    availability: Availability = Availability.NOT_FETCHED
    http_status: int | None = None
    detail: str = ""
    wayback_url: str | None = None
    wayback_timestamp: str | None = None
    wayback_status: int | None = None

    retryable: bool = False
    """这次没拿到内容，但**结论不可信**（例如小站 widget 的间歇性 404）。

    :attr:`availability` 说的是"现在拿不到"，本字段说的是"这个判断能不能作数"。
    为 ``True`` 时进度记 ``FAILED``（下次同步自动重试）而不是 ``UNAVAILABLE``
    （不再回头看）—— 源站的抖动不该被固化成归档里的空白。
    """

    def __post_init__(self) -> None:
        if not isinstance(self.availability, Availability):
            self.availability = Availability(self.availability)

    def __post_init__(self) -> None:
        if not isinstance(self.availability, Availability):
            self.availability = Availability(self.availability)

    @property
    def label(self) -> str:
        return STATUS_LABELS.get(self.availability, str(self.availability))

    @property
    def needs_notice(self) -> bool:
        """是否需要在渲染出的页面上显示提示块。"""
        return self.availability.needs_notice

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability": str(self.availability),
            "label": self.label,
            "httpStatus": self.http_status,
            "detail": self.detail,
            "retryable": self.retryable,
            "waybackUrl": self.wayback_url,
            "waybackTimestamp": self.wayback_timestamp,
            "waybackStatus": self.wayback_status,
        }


@dataclass
class ImageRef:
    """一张待归档的图片。"""

    src: str
    """源站原始 URL。"""

    local: str = ""
    """站点内相对路径，如 /media/notes/575615184/p36410176.jpg"""

    alt: str = ""
    archived: bool = False
    archive_url: str | None = None
    bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Note:
    """一篇日记（文章正文）。"""

    note_id: str
    widget_id: str
    title: str = ""
    date: str = ""
    content_html: str = ""
    comment_count: int = 0
    source_url: str = ""
    also_in: list[str] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    #: 评论在服务端就渲染进 DOM，免登录即可归档（此前误判为需登录）
    comments: list[Comment] = field(default_factory=list)
    status: SourceStatus = field(default_factory=SourceStatus)
    category: str = ""
    index_order: int = 0
    content_hash: str = ""

    @property
    def route(self) -> str:
        return f"/notes/{self.note_id}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        d["route"] = self.route
        return d


@dataclass
class PhotoMeta:
    """相册中的一张照片。"""

    photo_id: str
    album_id: str
    caption: str = ""
    thumb_url: str = ""
    large_url: str = ""
    """页面 ``<img>`` 里的最大尺寸（``large``，豆瓣处理版，长边 1600，小图会放大）。"""

    original_url: str = ""
    """详情页"查看原图"链接指向的 ``raw`` 尺寸 —— 上传时的原文件。

    只有详情页才有这个链接，且并非所有照片都提供；为空时退回
    :attr:`large_url`。见 :func:`scraper.parsers.parse_photo_detail`。
    """

    source_url: str = ""
    local: str = ""
    """**预览图**的站内路径：相册网格里显示的那张（``<img src>``）。"""

    local_original: str = ""
    """**原图**的站内路径：点开预览、或在新窗口打开时看的那张（``<a href>``）。

    为空表示这张照片没有单独的原图：源站不提供、没抓到，或者原图与预览是
    同一份字节因而没有另存（见 :meth:`scraper.media.MediaArchive.drop_redundant_original`）。
    此时预览打开的仍是 :attr:`local`。
    """

    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class Album:
    """一个相册。"""

    album_id: str
    title: str = ""
    room_id: str = ""
    source_url: str = ""
    photos: list[PhotoMeta] = field(default_factory=list)
    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class Bulletin:
    """公告栏 / 索引。"""

    bulletin_id: str
    room_id: str = ""
    title: str = ""
    content_html: str = ""
    source_url: str = ""
    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class Video:
    """一个视频条目（正片在优酷，仅归档缩略图与元信息）。"""

    video_id: str
    widget_id: str
    title: str = ""
    thumb_url: str = ""
    external_url: str = ""
    date: str = ""
    source_url: str = ""
    local_thumb: str = ""
    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class Comment:
    """一条评论。

    日记详情页与论坛讨论帖的评论都是**服务端静态渲染**的，
    结构一致（``.comment-item``），因此共用一套解析逻辑与模型。
    """

    author: str = ""
    date: str = ""
    content_html: str = ""
    avatar_url: str = ""
    comment_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Discussion:
    """论坛讨论帖。"""

    discussion_id: str
    forum_id: str
    title: str = ""
    author: str = ""
    date: str = ""
    content_html: str = ""
    source_url: str = ""
    comments: list[Comment] = field(default_factory=list)
    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class ExternalPage:
    """站外（``www.douban.com``）上的独立页面。

    小站索引①/② 里有一部分条目直接指向豆瓣主站的 ``/topic/`` 或 ``/note/``，
    这些页面**需要登录**才能访问（未登录会 302 到 ``sec.douban.com``）。
    登录后把它们一并归档，避免索引里出现"指向站外且拿不到"的空洞。
    """

    page_id: str
    url: str
    title: str = ""
    content_html: str = ""
    origin: str = ""
    """来源：哪个索引分组引入了这个页面。"""

    comments: list[Comment] = field(default_factory=list)
    status: SourceStatus = field(default_factory=SourceStatus)

    @property
    def route(self) -> str:
        return f"/external/{self.page_id}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        d["route"] = self.route
        return d


@dataclass
class MiniblogStatus:
    """广播室的一条动态。"""

    status_id: str
    date: str = ""
    text: str = ""
    link_url: str = ""
    link_title: str = ""
    image_url: str = ""
    content: str = ""
    object_kind: str = ""
    object_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Widget:
    """小站房间内的一个功能模块。"""

    kind: str
    widget_id: str
    room_id: str = ""
    title: str = ""
    declared_count: int | None = None
    preview_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Room:
    """小站的一个房间。"""

    room_id: str
    title: str = ""
    url: str = ""
    is_home: bool = False
    widgets: list[Widget] = field(default_factory=list)
    status: SourceStatus = field(default_factory=SourceStatus)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.to_dict()
        return d


@dataclass
class IndexEntry:
    """索引中的一个条目。"""

    title: str
    url: str = ""
    note_id: str | None = None
    status: Availability = Availability.NOT_FETCHED
    position: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "noteId": self.note_id,
            "status": str(self.status),
            "position": self.position,
        }


@dataclass
class IndexGroup:
    """索引中的一个分组（如 ☆【聲之形】）。"""

    title: str
    doulist_url: str | None = None
    entries: list[IndexEntry] = field(default_factory=list)
    source_bulletin_id: str = ""
    position: int = 0

    @property
    def group_id(self) -> str:
        return f"{self.source_bulletin_id}:{self.position}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "doulistUrl": self.doulist_url,
            "sourceBulletinId": self.source_bulletin_id,
            "position": self.position,
            "groupId": self.group_id,
            "entries": [e.to_dict() for e in self.entries],
        }


@dataclass
class RoomArticleSection:
    """一个 notes widget 在文章索引中的源列表投影。"""

    room: Room
    title: str
    widget_id: str = ""
    notes: list[Note] = field(default_factory=list)
