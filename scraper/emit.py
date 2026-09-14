"""产物生成：Markdown 页面、sidebar、manifest、索引页、不可访问清单。

生成逻辑全部以 ``manifest``（内容级单一事实源）为输入，
因此重复运行是幂等的，增量同步只需更新 manifest 中变化的条目。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .config import CONFIG, Config
from .html2md import ConvertContext, html_to_markdown, unwrap_link2
from .index_map import FALLBACK_CATEGORY, LINKS_CATEGORY
from .models import (
    Album,
    Availability,
    Bulletin,
    Discussion,
    IndexGroup,
    MiniblogStatus,
    Note,
    SourceStatus,
    Video,
)
from .util import atomic_write_text, now_iso

log = logging.getLogger("usagi.emit")

GENERATED_BANNER = "<!-- 本文件由 scraper/emit.py 自动生成，请勿手工编辑 -->"

# 页面提示块的样式映射
NOTICE_LEVEL = {
    Availability.UNAVAILABLE: "danger",
    Availability.ARCHIVE_MISSING: "danger",
    Availability.LOGIN_REQUIRED: "warning",
    Availability.ARCHIVED: "info",
}


# ------------------------------------------------------------------ 基础工具


# 可以安全地不加引号输出的纯量：以字母开头，只含 ASCII 字母数字与 _./-
# 以字母开头这一条很关键：它能排除 "575615184"、"2026-09-14" 这类
# 会被 YAML 解析成数字/日期的值，避免类型被悄悄改掉。
_PLAIN_SCALAR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_./-]*$")
# YAML 保留字，即使形如标识符也必须加引号
_YAML_RESERVED = {
    "true", "false", "null", "yes", "no", "on", "off", "y", "n", "~",
}


def yaml_value(value: Any) -> str:
    """把 Python 值序列化为 YAML 字面量。

    YAML 是 JSON 的超集，因此对需要引号的字符串直接用 JSON 编码即可安全
    处理引号、冒号、中文与特殊符号，无需手写转义。
    形如 ``home`` / ``ok`` 这类安全标识符则不加引号，让生成的 frontmatter
    保持可读。
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)

    text = str(value)
    if _PLAIN_SCALAR_RE.match(text) and text.lower() not in _YAML_RESERVED:
        return text
    return json.dumps(text, ensure_ascii=False)


def frontmatter(data: dict[str, Any]) -> str:
    """生成 YAML frontmatter 块。"""
    lines = ["---"]
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def status_notice(status: SourceStatus) -> str:
    """为不可访问 / 已补足的页面生成提示块。"""
    if not status.needs_notice:
        return ""

    level = NOTICE_LEVEL.get(status.availability, "warning")
    title = status.label
    lines = [f"::: {level} {title}"]

    if status.availability == Availability.ARCHIVED:
        lines.append("该页面在原站已不可访问，以下内容来自 **Internet Archive** 的历史快照。")
    elif status.availability == Availability.ARCHIVE_MISSING:
        lines.append("该页面在原站已不可访问，且 Internet Archive 中没有可用快照，正文缺失。")
    elif status.availability == Availability.LOGIN_REQUIRED:
        lines.append("该页面需要登录豆瓣才能访问，无法直接归档。")
    else:
        lines.append("该页面在原站已不可访问，正文缺失。")

    if status.http_status:
        lines.append(f"\n原站返回：`HTTP {status.http_status}`")
    if status.wayback_url:
        stamp = status.wayback_timestamp or ""
        date = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) >= 8 else stamp
        lines.append(f"\n快照时间：{date} · [查看原始快照]({status.wayback_url})")

    lines.append(":::")
    return "\n".join(lines)


def source_footer(source_url: str, *, comment_count: int = 0, extra: str = "") -> str:
    """页面底部的来源标注。

    ``comment_count`` 用于在**评论未归档**时说明原因；评论已归档时
    由正文的评论区块自行展示数量，这里不再重复。
    """
    parts = [f"*本页归档自 [原站页面]({source_url})"]
    if comment_count:
        parts.append(f"原站另有 {comment_count} 条评论未能归档")
    if extra:
        parts.append(extra)
    return " · ".join(parts) + "*"


def html_text(value: str) -> str:
    """转义为安全的 HTML **文本节点**内容。

    同时把换行压平：豆瓣的相册描述里常有字面换行，
    直接塞进 HTML 会破坏结构（Vue 的 SFC 解析器会直接报错）。

    花括号也要转成实体：``{{ … }}`` 是 Vue 模板的插值语法，
    描述里出现它时轻则被当成表达式而**整段吃掉**，重则（括号不配对）
    让整篇文档构建失败。实体在页面上仍显示为花括号本身。
    """
    text = " ".join((value or "").split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.replace("{", "&#123;").replace("}", "&#125;")


def html_attr(value: str) -> str:
    """转义为安全的 HTML **属性值**。

    ``&`` 必须最先替换，否则会把后续替换产生的实体二次转义。
    """
    return html_text(value).replace('"', "&quot;")


def slug_anchor(text: str) -> str:
    """生成 VitePress 标题锚点（与 markdown-it-anchor 的默认规则一致）。"""
    cleaned = "".join(ch for ch in text.strip() if ch.isalnum() or ch in " -_")
    return cleaned.strip().lower().replace(" ", "-")


# ------------------------------------------------------------------ 数据模型


@dataclass
class EmitContext:
    """生成产物时共享的映射表。"""

    route_map: dict[str, str] = field(default_factory=dict)
    album_routes: dict[str, str] = field(default_factory=dict)
    external_routes: dict[str, str] = field(default_factory=dict)


@dataclass
class EmitReport:
    """生成结果统计。"""

    notes: int = 0
    albums: int = 0
    photos: int = 0
    pages: list[str] = field(default_factory=list)
    unavailable_pages: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "notes": self.notes,
            "albums": self.albums,
            "photos": self.photos,
            "pages": self.pages,
            "unavailablePages": self.unavailable_pages,
        }


class SiteEmitter:
    """把结构化数据渲染成 VitePress 站点产物。"""

    def __init__(self, cfg: Config = CONFIG, context: EmitContext | None = None) -> None:
        self.cfg = cfg
        self.ctx = context or EmitContext()
        self.report = EmitReport()

    # ------------------------------------------------------------------ 日记

    def emit_note(self, note: Note) -> Path:
        """渲染一篇日记。"""
        context = ConvertContext(
            note_id=note.note_id,
            route_map=self.ctx.route_map,
            image_map={img.src: img.local for img in note.images if img.archived},
            album_routes=self.ctx.album_routes,
            external_routes=self.ctx.external_routes,
            keep_remote_images=False,
        )
        body = html_to_markdown(note.content_html, context, self.cfg)

        blocks: list[str] = []
        fm = {
            "title": note.title or f"日记 {note.note_id}",
            "date": note.date,
            "category": note.category,
            "noteId": note.note_id,
            "source": note.source_url,
            "commentCount": note.comment_count or None,
            "availability": str(note.status.availability),
            "archivedAt": now_iso()[:10],
        }
        blocks.append(frontmatter(fm))

        notice = status_notice(note.status)
        if notice:
            blocks.append(notice)
            self.report.unavailable_pages += 1

        if body:
            blocks.append(body)
        else:
            blocks.append("*正文未能归档。*")

        # 评论（服务端静态渲染，免登录即可归档）
        comments_block = self._render_comments(note.comments, note.note_id)
        if comments_block:
            blocks.append(comments_block)

        # 只有确实没归档到评论时才提示数量缺口
        missing_comments = note.comment_count if not note.comments else 0
        blocks.append(source_footer(note.source_url, comment_count=missing_comments))

        path = self.cfg.notes_dir / f"{note.note_id}.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.notes += 1
        return path

    def _render_comments(self, comments: Sequence[Any], note_id: str = "") -> str:
        """把评论渲染成 Markdown 区块。

        每条评论用引用块呈现，作者与时间加粗放在前面，与页面的正文视觉分开。
        """
        if not comments:
            return ""
        context = ConvertContext(
            note_id=note_id,
            route_map=self.ctx.route_map,
            album_routes=self.ctx.album_routes,
            external_routes=self.ctx.external_routes,
        )
        blocks = [f"## 评论（{len(comments)}）"]
        for comment in comments:
            head = " · ".join(part for part in (comment.author, comment.date) if part)
            body = html_to_markdown(comment.content_html, context, self.cfg)
            if not body:
                body = "（空）"
            quoted = "\n".join(f"> {line}" if line else ">" for line in body.splitlines())
            blocks.append(f"**{head or '匿名'}**\n\n{quoted}")
        return "\n\n".join(blocks)

    # ------------------------------------------------------------------ 相册

    def emit_album(self, album: Album) -> Path:
        """渲染一个相册（瀑布流网格 + 原图链接）。"""
        blocks: list[str] = []
        fm = {
            "title": album.title or f"相册 {album.album_id}",
            "albumId": album.album_id,
            "photoCount": len(album.photos),
            "source": album.source_url,
            "availability": str(album.status.availability),
            "archivedAt": now_iso()[:10],
        }
        blocks.append(frontmatter(fm))

        notice = status_notice(album.status)
        if notice:
            blocks.append(notice)
            self.report.unavailable_pages += 1

        cards: list[str] = []
        missing: list[str] = []
        for photo in album.photos:
            # 网格里显示预览图（小），点开预览的是原图（大）。没有原图时
            # 两者是同一个文件 —— 与 photo.local 的"只有原图就用原图"约定一致。
            preview = photo.local
            if not preview:
                missing.append(photo.photo_id)
                continue
            full = photo.local_original or preview
            caption = (photo.caption or "").strip()
            has_original = bool(photo.local_original)
            # 没有描述就整个属性都别写，免得留下一串空 title/alt
            attr = f' alt="{html_attr(caption)}"' if caption else ""
            tip = f"{caption} · 查看原图" if has_original and caption else (
                "查看原图" if has_original else caption
            )
            title = f' title="{html_attr(tip)}"' if tip else ""
            # data-caption 供站点脚本（放大预览）取用，不依赖光标提示
            data = f' data-caption="{html_attr(caption)}"' if caption else ""
            img = f'<img src="{preview}"{attr} loading="lazy" />'
            # class 是给放大预览脚本的挂载点；JS 未生效时它就是一个普通链接
            inner = (
                f'<a class="photo-preview" href="{full}" target="_blank"{title}{data}>'
                f"{img}</a>"
            )
            if caption:
                inner += f'<p class="caption">{html_text(caption)}</p>'
            cards.append(f'<figure class="photo-card">{inner}</figure>')

        if cards:
            blocks.append('<div class="photo-grid">\n' + "\n".join(cards) + "\n</div>")

        if missing:
            self.report.unavailable_pages += len(missing)
            listed = "、".join(f"`{pid}`" for pid in missing)
            blocks.append(
                f"::: warning 有 {len(missing)} 张图片未能归档\n"
                f"原站与 Internet Archive 均无法取得：{listed}\n"
                f":::"
            )

        blocks.append(source_footer(album.source_url))
        self.report.albums += 1
        self.report.photos += len([p for p in album.photos if p.local])

        path = self.cfg.albums_dir / f"{album.album_id}.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        return path

    # ------------------------------------------------------------ 站外页面

    def emit_external(self, page: Any) -> Path:
        """渲染一个站外（``www.douban.com``）页面。"""
        blocks = [
            frontmatter(
                {
                    "title": page.title or page.page_id,
                    "pageId": page.page_id,
                    "origin": page.origin,
                    "source": page.url,
                    "availability": str(page.status.availability),
                    "archivedAt": now_iso()[:10],
                }
            )
        ]
        notice = status_notice(page.status)
        if notice:
            blocks.append(notice)
            self.report.unavailable_pages += 1

        if page.origin:
            blocks.append(f"*原站索引分组：{page.origin}*")

        body = html_to_markdown(
            page.content_html,
            ConvertContext(
                route_map=self.ctx.route_map,
                album_routes=self.ctx.album_routes,
                external_routes=self.ctx.external_routes,
            ),
            self.cfg,
        )
        blocks.append(body or "*正文未能归档。*")

        comments_block = self._render_comments(page.comments)
        if comments_block:
            blocks.append(comments_block)

        blocks.append(source_footer(page.url))

        path = self.cfg.docs_dir / "external" / f"{page.page_id}.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append(f"external/{page.page_id}.md")
        return path

    def emit_external_index(self, pages: Sequence[Any]) -> Path:
        """渲染 /external/ 索引页。"""
        blocks = [
            frontmatter({"title": "站外文章", "aside": False}),
            "# 站外文章\n",
            "原站索引①/② 里有一部分条目直接指向豆瓣主站（需要登录才能访问），"
            "登录后已一并归档。\n",
        ]
        if pages:
            items = []
            for page in pages:
                badge = ""
                if page.status.availability != Availability.OK:
                    badge = f" <small class=\"badge-unavailable\">{page.status.label}</small>"
                origin = f" — <small>{page.origin}</small>" if page.origin else ""
                items.append(f"- [{page.title}]({page.route}){origin}{badge}")
            blocks.append("\n".join(items))
        else:
            blocks.append("*还没有归档站外文章。*")

        path = self.cfg.docs_dir / "external" / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("external/index.md")
        return path

    # ---------------------------------------------------------------- 首页

    def emit_home(
        self,
        meta: dict[str, str],
        groups: Sequence[IndexGroup],
        albums: Sequence[Album],
        *,
        avatar_local: str = "",
        stats: dict[str, int] | None = None,
    ) -> Path:
        """渲染首页（还原原站观感：索引分区 + 海报墙）。"""
        name = meta.get("name", self.cfg.site_name)
        description = meta.get("description", self.cfg.site_description)
        avatar = avatar_local or meta.get("avatar", "")
        stats = stats or {}

        hero_actions = [
            {"theme": "brand", "text": "开始阅读", "link": "/notes/"},
            {"theme": "alt", "text": "海报墙", "link": "/albums/13432051"},
        ]
        hero = {
            "name": name,
            "text": "世界中闪耀的光辉☆",
            "tagline": description,
            "actions": hero_actions,
        }
        if avatar:
            hero["image"] = {"src": avatar, "alt": name}

        features = []
        for group in groups:
            if group.title == LINKS_CATEGORY:
                continue
            anchor = slug_anchor(group.title)
            detail = f"{len(group.entries)} 篇"
            if group.doulist_url:
                detail += f" · [豆列]({group.doulist_url})"
            features.append(
                {
                    "title": group.title,
                    "details": detail,
                    "link": f"/notes/#{anchor}",
                }
            )

        front = {"layout": "home", "hero": hero}
        if features:
            front["features"] = features

        blocks = [frontmatter(front)]

        if stats:
            blocks.append(
                "## 归档概况\n\n"
                f"- 文章 **{stats.get('notes', 0)}** 篇\n"
                f"- 照片 **{stats.get('photos', 0)}** 张\n"
                f"- 相册 **{stats.get('albums', 0)}** 个\n"
                f"- 视频 **{stats.get('videos', 0)}** 条\n"
            )

        if albums:
            cards: list[str] = []
            for album in albums:
                cover = next((p.local for p in album.photos if p.local), "")
                route = self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}")
                count = len(album.photos)
                title_attr = html_attr(album.title)
                title_text = html_text(album.title)
                if cover:
                    cards.append(
                        f'<a class="poster" href="{route}">'
                        f'<img src="{cover}" alt="{title_attr}" loading="lazy" />'
                        f'<span>{title_text}<em>{count} 张</em></span></a>'
                    )
                else:
                    cards.append(
                        f'<a class="poster" href="{route}">'
                        f'<span>{title_text}<em>{count} 张</em></span></a>'
                    )
            blocks.append("## 海报墙\n\n" + '<div class="poster-wall">\n' + "\n".join(cards) + "\n</div>")

        blocks.append(
            f"::: info 关于本站\n"
            f"本站在 [原豆瓣小站]({self.cfg.site_url}) 内容的基础上做了完整本地化归档，"
            f"所有正文与图片均已离线保存，以便长期访问。\n"
            f"原站由 **{self.cfg.owner}** 于 {self.cfg.owner_created} 创建。\n"
            f":::"
        )

        path = self.cfg.docs_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("index.md")
        return path

    # ------------------------------------------------------------ 文章索引页

    def emit_notes_index(
        self,
        groups: Sequence[IndexGroup],
        notes: dict[str, Note],
        *,
        fallback_notes: Sequence[Note] = (),
    ) -> Path:
        """渲染 /notes/ 索引页，按原站索引分组列出全部文章。"""
        blocks = [
            frontmatter({"title": "文章索引", "aside": False}),
            "# 文章索引\n",
            f"共收录 **{len(notes)}** 篇文章，分组沿用原站站长手工编排的索引①/②。\n",
        ]

        for group in groups:
            if group.title == LINKS_CATEGORY:
                continue
            blocks.append(f"## {group.title}\n")
            if group.doulist_url:
                blocks.append(f"[豆瓣豆列]({group.doulist_url})\n")
            items: list[str] = []
            for entry in group.entries:
                if entry.note_id and entry.note_id in notes:
                    note = notes[entry.note_id]
                    route = self.ctx.route_map.get(entry.note_id, f"/notes/{entry.note_id}")
                    date = f" <small>{note.date[:10]}</small>" if note.date else ""
                    badge = ""
                    if note.status.availability != Availability.OK:
                        badge = f' <small class="badge-unavailable">{note.status.label}</small>'
                    items.append(f"- [{note.title}]({route}){date}{badge}")
                else:
                    # 已归档的站外页面指向站内路由，否则保留外链并标注未归档
                    route = self.ctx.external_routes.get(entry.url) or self.ctx.external_routes.get(
                        entry.url.rstrip("/")
                    )
                    if route:
                        items.append(f"- [{entry.title}]({route})")
                    else:
                        badge = " <small class=\"badge-unavailable\">未归档</small>"
                        items.append(f"- [{entry.title}]({entry.url}){badge}")
            blocks.append("\n".join(items))

        if fallback_notes:
            blocks.append(f"## {FALLBACK_CATEGORY}\n")
            ordered = sorted(fallback_notes, key=lambda n: n.date, reverse=True)
            items = []
            for note in ordered:
                route = self.ctx.route_map.get(note.note_id, f"/notes/{note.note_id}")
                date = f" <small>{note.date[:10]}</small>" if note.date else ""
                items.append(f"- [{note.title}]({route}){date}")
            blocks.append("\n".join(items))

        path = self.cfg.notes_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("notes/index.md")
        return path

    def emit_albums_index(self, albums: Sequence[Album]) -> Path:
        """渲染 /albums/ 索引页。"""
        blocks = [
            frontmatter({"title": "相册", "aside": False}),
            "# 相册\n",
            f"共 **{len(albums)}** 个相册。\n",
        ]
        items = []
        for album in albums:
            route = self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}")
            items.append(f"- [{album.title}]({route}) — {len(album.photos)} 张")
        blocks.append("\n".join(items))

        path = self.cfg.albums_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("albums/index.md")
        return path

    # ------------------------------------------------------------ 其他页面

    def emit_about(self, bulletin: Bulletin | None, meta: dict[str, str]) -> Path:
        """渲染「关于」页（原站 About PPK）。"""
        blocks = [frontmatter({"title": "关于山田尚子", "aside": False})]

        if bulletin and bulletin.content_html:
            notice = status_notice(bulletin.status)
            if notice:
                blocks.append(notice)
            body = html_to_markdown(
                bulletin.content_html,
                ConvertContext(route_map=self.ctx.route_map, album_routes=self.ctx.album_routes),
                self.cfg,
            )
            blocks.append(body)
        else:
            blocks.append("# 关于山田尚子\n\n*内容未能归档。*")

        blocks.append(
            f"::: info 来源\n本页原为小站公告栏「{bulletin.title if bulletin else 'About PPK'}」，"
            f"归档自 [原站]({self.cfg.site_url})。\n:::"
        )
        path = self.cfg.docs_dir / "about.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("about.md")
        return path

    def emit_videos(self, videos: Sequence[Video]) -> Path:
        """渲染视频页（缩略图 + 优酷外链，正片不归档）。"""
        blocks = [
            frontmatter({"title": "视频", "aside": False}),
            "# 视频\n",
            f"共 **{len(videos)}** 条。正片托管在优酷，本站仅归档标题、缩略图与原始链接。\n",
            "::: info 说明\n豆瓣小站的视频模块只保存缩略图，视频本身存放在外部平台，"
            "因此无法随本站一起离线保存。\n:::",
        ]
        cards: list[str] = []
        for video in videos:
            thumb = html_attr(video.local_thumb or video.thumb_url)
            target = html_attr(video.external_url or video.source_url)
            title_text = html_text(video.title)
            img = f'<img src="{thumb}" alt="" loading="lazy" />' if thumb else ""
            date = f"<time>{html_text(video.date)}</time>" if video.date else ""
            cards.append(
                f'<figure class="video-card">'
                f'<a href="{target}" target="_blank" rel="noopener">{img}</a>'
                f'<figcaption><a href="{target}" target="_blank" rel="noopener">'
                f"{title_text}</a>{date}</figcaption>"
                f"</figure>"
            )
        if cards:
            blocks.append('<div class="video-grid">\n' + "\n".join(cards) + "\n</div>")
        else:
            blocks.append("*没有归档到视频条目。*")

        path = self.cfg.docs_dir / "videos.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("videos.md")
        return path

    def emit_board(self, discussions: Sequence[Discussion]) -> Path:
        """渲染留言板（论坛帖 + 静态评论）。"""
        blocks = [
            frontmatter({"title": "留言板", "aside": False}),
            "# 留言板\n",
            "原站「兔子山论坛」的全部话题与回复。\n",
        ]
        for discussion in discussions:
            notice = status_notice(discussion.status)
            if notice:
                blocks.append(notice)
                self.report.unavailable_pages += 1
            blocks.append(f"## {discussion.title}\n")
            meta_line = " · ".join(
                part for part in [discussion.author, discussion.date] if part
            )
            if meta_line:
                blocks.append(f"*{meta_line}*\n")
            body = html_to_markdown(
                discussion.content_html,
                ConvertContext(route_map=self.ctx.route_map, album_routes=self.ctx.album_routes),
                self.cfg,
            )
            blocks.append(body or "*正文未能归档。*")

            if discussion.comments:
                blocks.append(f"### 回应（{len(discussion.comments)}）\n")
                for comment in discussion.comments:
                    head = " · ".join(part for part in [comment.author, comment.date] if part)
                    text = html_to_markdown(
                        comment.content_html,
                        ConvertContext(route_map=self.ctx.route_map),
                        self.cfg,
                    )
                    blocks.append(f"**{head}**\n\n> {text}")
            else:
                blocks.append("*没有回应。*")

            blocks.append(source_footer(discussion.source_url))

        if not discussions:
            blocks.append("*未能归档到任何话题。*")

        path = self.cfg.docs_dir / "board.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("board.md")
        return path

    def emit_broadcast(self, statuses: Sequence[MiniblogStatus]) -> Path:
        """渲染广播室动态流。"""
        blocks = [
            frontmatter({"title": "广播室", "aside": False}),
            "# 广播室\n",
            "原站「兔子山快报」的动态流。\n",
        ]
        for item in statuses:
            head = item.text or "更新"
            title = item.link_title or item.link_url
            line = f"- **{head}**"
            if item.date:
                line += f" <small>{item.date}</small>"
            if title:
                link = item.link_url or "#"
                line += f"\n  - [{title}]({link})"
            blocks.append(line)
        if not statuses:
            blocks.append("*未能归档到动态。*")

        path = self.cfg.docs_dir / "broadcast.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("broadcast.md")
        return path

    # ------------------------------------------------------------ Sidebar

    def emit_sidebar(
        self,
        groups: Sequence[IndexGroup],
        notes: dict[str, Note],
        *,
        fallback_notes: Sequence[Note] = (),
        albums: Sequence[Album] = (),
        videos_count: int = 0,
        external_count: int = 0,
    ) -> Path:
        """生成 ``sidebar.generated.mts``。

        选择生成静态 TS 文件而不是运行时读 JSON：
        构建期零 IO、可被 git 追踪（内容更新时 diff 可见）、
        无需额外插件或虚拟模块。
        """
        notes_sidebar: list[dict[str, Any]] = []
        for group in groups:
            if group.title == LINKS_CATEGORY:
                continue
            items: list[dict[str, Any]] = []
            for entry in group.entries:
                if entry.note_id and entry.note_id in notes:
                    note = notes[entry.note_id]
                    route = self.ctx.route_map.get(entry.note_id, f"/notes/{entry.note_id}")
                    items.append({"text": note.title, "link": route})
                else:
                    # 未归档的条目**不能**把外站 URL 当作 link：
                    # VitePress 的 sidebar link 必须是站内路由，否则构建期报
                    # "Invalid route component: undefined"。
                    # 已归档的站外页面则指向站内路由。
                    route = self.ctx.external_routes.get(entry.url) or self.ctx.external_routes.get(
                        entry.url.rstrip("/")
                    )
                    if route:
                        items.append({"text": entry.title, "link": route})
                    else:
                        items.append({"text": f"{entry.title}（未归档）"})
            if items:
                notes_sidebar.append(
                    {"text": group.title, "collapsed": False, "items": items}
                )

        if fallback_notes:
            ordered = sorted(fallback_notes, key=lambda n: n.date, reverse=True)
            notes_sidebar.append(
                {
                    "text": FALLBACK_CATEGORY,
                    "collapsed": True,
                    "items": [
                        {
                            "text": n.title,
                            "link": self.ctx.route_map.get(n.note_id, f"/notes/{n.note_id}"),
                        }
                        for n in ordered
                    ],
                }
            )

        albums_sidebar = [
            {
                "text": "相册",
                "items": [
                    {
                        "text": f"{album.title}（{len(album.photos)}）",
                        "link": self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}"),
                    }
                    for album in albums
                ],
            }
        ]

        other_sidebar = [
            {
                "text": "站内",
                "items": [
                    {"text": "文章索引", "link": "/notes/"},
                    *([{"text": "站外文章", "link": "/external/"}] if external_count else []),
                    {"text": "相册", "link": "/albums/"},
                    {"text": "关于山田尚子", "link": "/about"},
                    {"text": "留言板", "link": "/board"},
                    {"text": "广播室", "link": "/broadcast"},
                    *([{"text": "视频", "link": "/videos"}] if videos_count else []),
                ],
            }
        ]

        sidebar = {
            "/notes/": notes_sidebar,
            "/albums/": albums_sidebar,
            "/": other_sidebar,
        }

        content = (
            "// 本文件由 scraper/emit.py 自动生成，请勿手工编辑。\n"
            "// 数据来源：原站索引①/②（站长手工编排的分类）+ 抓取到的日记。\n"
            "import type { DefaultTheme } from 'vitepress'\n\n"
            "export const sidebar: DefaultTheme.Sidebar = "
            + json.dumps(sidebar, ensure_ascii=False, indent=2)
            + " as DefaultTheme.Sidebar\n"
        )
        atomic_write_text(self.cfg.sidebar_path, content)
        self.report.pages.append("sidebar.generated.mts")
        return self.cfg.sidebar_path

    # -------------------------------------------------- 不可访问清单

    def emit_unavailable_report(self, records: Iterable[Any]) -> Path:
        """产出不可访问内容清单，便于人工核对与后续补抓。"""
        records = list(records)
        lines = [
            "# 不可访问内容清单",
            "",
            f"生成时间：{now_iso()}",
            "",
            "本清单列出源站不可访问、或需要登录才能访问的页面。",
            "已从 Internet Archive 成功补足的条目标记为 **已补足**。",
            "",
            "| 状态 | 页面 | 上下文 | HTTP | 说明 |",
            "| --- | --- | --- | ---: | --- |",
        ]
        labels = {
            str(Availability.ARCHIVED): "已补足",
            str(Availability.ARCHIVE_MISSING): "无快照",
            str(Availability.LOGIN_REQUIRED): "需登录",
            str(Availability.UNAVAILABLE): "不可访问",
        }
        for record in records:
            availability = getattr(record, "availability", "")
            url = getattr(record, "url", "")
            context = getattr(record, "context", "") or ""
            status = getattr(record, "http_status", None)
            detail = (getattr(record, "detail", "") or "").replace("|", "\\|")
            wayback = getattr(record, "wayback_url", None)
            label = labels.get(str(availability), str(availability))
            if wayback:
                label = f"{label}（[快照]({wayback})）"
            lines.append(
                f"| {label} | {url} | {context} | {status or '-'} | {detail} |"
            )

        if not records:
            lines.append("| — | 无 | | | 全部内容均已成功归档 |")

        path = self.cfg.data_dir / "unavailable.md"
        atomic_write_text(path, "\n".join(lines) + "\n")
        return path

    # ------------------------------------------------------------ 汇总写盘

    def emit_data(self, name: str, payload: Any) -> Path:
        """把中间产物写入 ``data/``。"""
        path = self.cfg.data_dir / f"{name}.json"
        atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return path

    def emit_manifest(self, manifest: dict[str, Any]) -> Path:
        """写入内容级单一事实源。"""
        path = self.cfg.manifest_path
        atomic_write_text(path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return path

    def emit_sync_report(self, payload: dict[str, Any]) -> Path:
        """产出同步报告。"""
        lines = [
            "# 同步报告",
            "",
            f"生成时间：{payload.get('generatedAt', now_iso())}",
            "",
            "## 概览",
            "",
            "| 项目 | 数值 |",
            "| --- | ---: |",
        ]
        for key, value in (payload.get("summary") or {}).items():
            lines.append(f"| {key} | {value} |")

        stages = payload.get("stages") or []
        if stages:
            lines += [
                "",
                "## 各阶段",
                "",
                "| 阶段 | 处理 | 总数 | 跳过 | 失败 | 用时 |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
            for stage in stages:
                lines.append(
                    f"| {stage.get('stage')} | {stage.get('processed')} | {stage.get('total')} "
                    f"| {stage.get('skipped')} | {stage.get('failed')} | {stage.get('elapsed')} |"
                )

        stats = payload.get("http") or {}
        if stats:
            lines += [
                "",
                "## 请求统计",
                "",
                f"- 网络请求：**{stats.get('requests', 0)}**",
                f"- 缓存命中：**{stats.get('cacheHits', 0)}**",
                f"- 重试次数：**{stats.get('retries', 0)}**",
                f"- 被拦截：**{stats.get('blocked', 0)}**",
                f"- 下载字节：**{stats.get('bytesDownloaded', 0)}**",
                f"- 指纹：`{stats.get('impersonate', '')}`",
                f"- 耗时：**{stats.get('elapsedSeconds', 0)}s**",
            ]
            # 源站抖动的迹象：同一批"404"里有一部分其实只是 widget 后端抽风，
            # 下次同步会自动重试。只在真的出现时列出来，免得报告里全是 0。
            transient = stats.get("transientMisses", 0)
            if transient:
                lines.append(
                    f"- 不可信的 404（源站抖动，未写缓存、下次重试）：**{transient}**"
                )

        path = self.cfg.data_dir / "sync-report.md"
        atomic_write_text(path, "\n".join(lines) + "\n")
        return path
