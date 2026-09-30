"""产物生成：Markdown 页面、sidebar、manifest、索引页、不可访问清单。

生成逻辑全部以 ``manifest``（内容级单一事实源）为输入，
因此重复运行是幂等的，增量同步只需更新 manifest 中变化的条目。
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

from .config import CONFIG, Config
from .html2md import ConvertContext, html_to_markdown, sanitize_markdown_url, unwrap_link2
from .index_map import FALLBACK_CATEGORY, LINKS_CATEGORY
from .models import (
    Album,
    Availability,
    Bulletin,
    Discussion,
    IndexGroup,
    MiniblogStatus,
    Note,
    Room,
    RoomArticleSection,
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

#: 评论区块的标题行模式。内容抽查（:mod:`scraper.verify`）按它把 md 切成
#: 「正文」与「评论」两段，好拿评论去和原始 HTML 里的 ``#comments`` 比。
#: 评论不在 ``#link-report`` 内，若仅比对正文，md 侧会额外多出整段评论内容。
COMMENT_HEADING_RE = re.compile(r"^## 评论（\d+）$", re.MULTILINE)


def comment_heading(count: int) -> str:
    """评论区块的小标题。生成与匹配共用，避免两边写歪。"""
    return f"## 评论（{count}）"


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
    if status.wayback_url and (safe_wayback := md_safe_url(status.wayback_url)):
        stamp = status.wayback_timestamp or ""
        date = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) >= 8 else stamp
        lines.append(f"\n快照时间：{date} · [查看原始快照]({safe_wayback})")

    lines.append(":::")
    return "\n".join(lines)


def source_footer(source_url: str, *, comment_count: int = 0, extra: str = "") -> str:
    """页面底部的来源标注。

    ``comment_count`` 用于在**评论未归档**时说明原因；评论已归档时
    由正文的评论区块自行展示数量，这里不再重复。
    """
    parts = [f"*本页归档自 [原站页面]({md_safe_url(source_url)})"]
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


def md_escape_link_text(value: str) -> str:
    """转义 Markdown 链接文字里的 ``[`` / ``]``，避免提前闭合链接括号。

    标题如 ``C# [笔记]`` 会让 ``[text](url)`` 在首个 ``]`` 处提前闭合，
    把 ``](url)`` 泄漏成可见文字。用反斜杠转义后被渲染为字面方括号。
    """
    return (value or "").replace("[", "\\[").replace("]", "\\]")


def md_safe_url(value: str) -> str:
    """用正文转换层同一策略处理链接目标。"""
    return sanitize_markdown_url(value)


def slug_anchor(text: str) -> str:
    """Match VitePress's heading slugify implementation."""
    value = unicodedata.normalize("NFKD", str(text))
    value = re.sub(r"[\u0300-\u036f]", "", value)
    value = re.sub(r"[\x00-\x1f]", "", value)
    value = re.sub(r"[\s~`!@#$%^&*()\-_+=[\]{}|\\;:\"'“”‘’<>,.?/]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    value = re.sub(r"^(\d)", r"_\1", value)
    return value.lower()


def markdown_blockquote(text: str) -> str:
    """Prefix every line, including blank lines, to keep full text in a quote."""
    return "\n".join(f"> {line}" for line in (text or "").split("\n"))


def md_table_cell(value: Any) -> str:
    """Escape a value for a Markdown table cell."""
    text = str(value if value is not None else "").replace("\\", "\\\\")
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


# ------------------------------------------------------------------ 数据模型


@dataclass
class EmitContext:
    """生成产物时共享的映射表。"""

    route_map: dict[str, str] = field(default_factory=dict)
    album_routes: dict[str, str] = field(default_factory=dict)
    photo_album_routes: dict[str, str] = field(default_factory=dict)
    photo_image_routes: dict[str, str] = field(default_factory=dict)
    note_image_routes: dict[str, str] = field(default_factory=dict)
    external_routes: dict[str, str] = field(default_factory=dict)
    discussion_routes: dict[str, str] = field(default_factory=dict)
    video_routes: dict[str, str] = field(default_factory=dict)


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

    def _external_route(self, url: str) -> str | None:
        """按 host + path 查找已归档豆瓣页面，忽略协议、尾斜杠与 query。"""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        path = (parsed.path or "/").rstrip("/") or "/"
        if not host:
            return None
        for key, route in self.ctx.external_routes.items():
            candidate = urlparse(key)
            candidate_host = (candidate.hostname or "").lower().removeprefix("www.")
            candidate_path = (candidate.path or "/").rstrip("/") or "/"
            if host == candidate_host and path == candidate_path:
                return route
        return None

    # ------------------------------------------------------------------ 日记

    def emit_note(self, note: Note) -> Path:
        """渲染一篇日记。"""
        output_path = self.cfg.notes_dir / f"{note.note_id}.md"
        context = ConvertContext(
            note_id=note.note_id,
            route_map=self.ctx.route_map,
            image_map={img.src: img.local for img in note.images if img.archived},
            album_routes=self.ctx.album_routes,
            external_routes=self.ctx.external_routes,
            discussion_routes=self.ctx.discussion_routes,
            video_routes=self.ctx.video_routes,
            keep_remote_images=False,
        )
        body = html_to_markdown(note.content_html, context, self.cfg)

        blocks: list[str] = []
        fm = {
            "title": note.title or f"日记 {note.note_id}",
            "date": note.date,
            "noteId": note.note_id,
            "source": note.source_url,
            "commentCount": note.comment_count or None,
            "availability": str(note.status.availability),
            "archivedAt": self._archived_at(output_path),
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

        # 评论数量缺口：只有当确实没归档到任何评论，或归档数量少于源站
        # 声明的评论数（分页不全）时，才在来源标注里提示，否则会误导
        # verify 阶段的源/快照比对（"## 评论（N）"的 N 会偏低且无从察觉）。
        archived_comments = len(note.comments)
        if archived_comments == 0:
            missing_comments = note.comment_count
        elif note.comment_count and archived_comments < note.comment_count:
            missing_comments = note.comment_count - archived_comments
            log.warning(
                "日记 %s 评论分页不全：归档 %d 条，但源站显示 %d 条",
                note.note_id, archived_comments, note.comment_count,
            )
        else:
            missing_comments = 0
        blocks.append(source_footer(note.source_url, comment_count=missing_comments))

        path = output_path
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
            discussion_routes=self.ctx.discussion_routes,
            video_routes=self.ctx.video_routes,
        )
        blocks = [comment_heading(len(comments))]
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
        output_path = self.cfg.albums_dir / f"{album.album_id}.md"
        blocks: list[str] = []
        fm = {
            "title": album.title or f"相册 {album.album_id}",
            "albumId": album.album_id,
            "photoCount": len(album.photos),
            "source": album.source_url,
            "availability": str(album.status.availability),
            "archivedAt": self._archived_at(output_path),
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
            # 无描述时不输出对应属性，避免生成空的 title/alt
            attr = f' alt="{html_attr(caption)}"' if caption else ""
            tip = f"{caption} · 查看原图" if has_original and caption else (
                "查看原图" if has_original else caption
            )
            title = f' title="{html_attr(tip)}"' if tip else ""
            # data-caption 供站点脚本（放大预览）取用，不依赖光标提示
            data = f' data-caption="{html_attr(caption)}"' if caption else ""
            img = f'<img src="{html_attr(preview)}"{attr} loading="lazy" />'
            # class 是给放大预览脚本的挂载点；JS 未生效时它就是一个普通链接
            inner = (
                f'<a class="photo-preview" href="{html_attr(full)}" target="_blank"{title}{data}>'
                f"{img}</a>"
            )
            if caption:
                inner += f'<p class="caption">{html_text(caption)}</p>'
            cards.append(
                f'<figure class="photo-card" id="photo-{html_attr(photo.photo_id)}">'
                f"{inner}</figure>"
            )

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

        path = output_path
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        return path

    # ------------------------------------------------------------ 站外页面

    def emit_external(self, page: Any) -> Path:
        """渲染一个站外（``www.douban.com``）页面。"""
        output_path = self.cfg.docs_dir / "external" / f"{page.page_id}.md"
        blocks = [
            frontmatter(
                {
                    "title": page.title or page.page_id,
                    "pageId": page.page_id,
                    "origin": page.origin,
                    "source": page.url,
                    "availability": str(page.status.availability),
                    "archivedAt": self._archived_at(output_path),
                }
            )
        ]
        notice = status_notice(page.status)
        if notice:
            blocks.append(notice)
            self.report.unavailable_pages += 1

        if page.origin:
            blocks.append(f"*原站索引分组：{html_text(page.origin)}*")

        body = html_to_markdown(
            page.content_html,
            ConvertContext(
                route_map=self.ctx.route_map,
                album_routes=self.ctx.album_routes,
                external_routes=self.ctx.external_routes,
                discussion_routes=self.ctx.discussion_routes,
                video_routes=self.ctx.video_routes,
                keep_remote_images=False,
            ),
            self.cfg,
        )
        blocks.append(body or "*正文未能归档。*")

        comments_block = self._render_comments(page.comments)
        if comments_block:
            blocks.append(comments_block)

        blocks.append(source_footer(page.url))

        path = output_path
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append(f"external/{page.page_id}.md")
        return path

    def emit_external_index(self, pages: Sequence[Any]) -> Path:
        """渲染 /external/ 索引页。"""
        blocks = [
            frontmatter({"title": "站外文章", "aside": False}),
            "# 站外文章\n",
            "原站索引①/② 里有一部分条目直接指向豆瓣主站",
        ]
        if pages:
            items = []
            for page in pages:
                badge = ""
                if page.status.availability != Availability.OK:
                    badge = f" <small class=\"badge-unavailable\">{page.status.label}</small>"
                origin = f" — <small>{page.origin}</small>" if page.origin else ""
                items.append(f"- [{md_escape_link_text(page.title)}]({page.route}){origin}{badge}")
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
        rooms: Sequence[Room] = (),
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

        home_room = next((room for room in rooms if room.is_home), None)
        features = []
        if home_room:
            for widget in home_room.widgets:
                if widget.kind == "photos":
                    link = f"/albums/{widget.widget_id}"
                else:
                    link = f"/rooms/{home_room.room_id}#widget-{widget.widget_id}"
                features.append({
                    "title": widget.title or widget.kind,
                    "details": f"{widget.kind} · {widget.widget_id}",
                    "link": link,
                })

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

        home_album_ids = {
            widget.widget_id for widget in home_room.widgets
            if widget.kind == "photos"
        } if home_room else {"13432051"}
        home_albums = [album for album in albums if album.album_id in home_album_ids]
        if home_albums:
            cards: list[str] = []
            for album in home_albums:
                cover = next((p.local for p in album.photos if p.local), "")
                route = self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}")
                count = len(album.photos)
                title_attr = html_attr(album.title)
                title_text = html_text(album.title)
                if cover:
                    cards.append(
                        f'<a class="poster" href="{html_attr(route)}">'
                        f'<img src="{html_attr(cover)}" alt="{title_attr}" loading="lazy" />'
                        f'<span>{title_text}<em>{count} 张</em></span></a>'
                    )
                else:
                    cards.append(
                        f'<a class="poster" href="{html_attr(route)}">'
                        f'<span>{title_text}<em>{count} 张</em></span></a>'
                    )
            blocks.append("## 首页相册模块\n\n" + '<div class="poster-wall">\n' + "\n".join(cards) + "\n</div>")

        blocks.append(
            f"::: info 关于本站\n"
            f"本站为 [兔子山的小站]({self.cfg.site_url}) 的本地归档，内容版权归原作者所有。"
            f"原站由 **{self.cfg.owner}** 于 {self.cfg.owner_created} 创建。\n"
            f":::"
        )

        path = self.cfg.docs_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("index.md")
        return path

    # ------------------------------------------------------------ 文章索引页

    def _archived_at(self, path: Path) -> str:
        """Keep the original archive date when regenerating unchanged output."""
        if path.exists():
            match = re.search(r"^archivedAt:\s*(\S+)", path.read_text(encoding="utf-8"), re.MULTILINE)
            if match:
                value = match.group(1)
                # Older output could contain a JSON-quoted date. Normalize it
                # before feeding it back through yaml_value, otherwise each
                # regeneration adds another layer of escaping.
                if value.startswith('"'):
                    try:
                        decoded = json.loads(value)
                        if isinstance(decoded, str):
                            value = decoded
                    except json.JSONDecodeError:
                        pass
                return value.strip('"')
        return now_iso()[:10]

    def _resolve_entry_route(self, entry: Any, notes: dict[str, Note]) -> str | None:
        """为索引条目解析站内路由（消除 emit_notes_index / emit_sidebar 的重复，见 SUG-17）。

        已归档日记（``entry.note_id`` 在 ``notes`` 中）走 ``route_map``；
        指向已归档站外页面的条目走 ``external_routes``；其余返回 ``None``
        （调用方据此保留外链或标注"未归档"）。
        """
        if entry.note_id and entry.note_id in notes:
            return self.ctx.route_map.get(entry.note_id, f"/notes/{entry.note_id}")
        return self.ctx.external_routes.get(entry.url) or self.ctx.external_routes.get(
            entry.url.rstrip("/")
        )

    def emit_notes_index(
        self,
        groups: Sequence[IndexGroup],
        notes: dict[str, Note],
        *,
        fallback_notes: Sequence[Note] = (),
        room_sections: Sequence[RoomArticleSection] | None = None,
    ) -> Path:
        """渲染 /notes/ 索引页，优先按原站 room 列出文章。"""
        blocks = [
            frontmatter({"title": "文章索引", "aside": False}),
            "# 文章索引\n",
            f"共收录 **{len(notes)}** 篇文章。\n",
        ]

        if room_sections is not None:
            current_room_id = ""
            for section in room_sections:
                if section.room.room_id != current_room_id:
                    current_room_id = section.room.room_id
                    blocks.append(
                        f"## {section.room.title}\n\n"
                        f"[进入房间](/rooms/{section.room.room_id})\n"
                    )
                blocks.append(
                    f"### {section.title}\n\n"
                    f"[查看源模块](/rooms/{section.room.room_id}#widget-{section.widget_id})\n"
                )
                items: list[str] = []
                for note in section.notes:
                    route = self.ctx.route_map.get(note.note_id, f"/notes/{note.note_id}")
                    date = f" <small>{note.date[:10]}</small>" if note.date else ""
                    badge = ""
                    if note.status.availability != Availability.OK:
                        badge = f' <small class="badge-unavailable">{note.status.label}</small>'
                    items.append(f"- [{md_escape_link_text(note.title)}]({route}){date}{badge}")
                blocks.append("\n".join(items))
        else:
            for group in groups:
                if group.title == LINKS_CATEGORY:
                    continue
                blocks.append(f"## {group.title}\n")
                if group.doulist_url:
                    blocks.append(f"[豆瓣豆列]({group.doulist_url})\n")
                items: list[str] = []
                for entry in group.entries:
                    route = self._resolve_entry_route(entry, notes)
                    if entry.note_id and entry.note_id in notes:
                        note = notes[entry.note_id]
                        date = f" <small>{note.date[:10]}</small>" if note.date else ""
                        badge = ""
                        if note.status.availability != Availability.OK:
                            badge = f' <small class="badge-unavailable">{note.status.label}</small>'
                        items.append(f"- [{md_escape_link_text(note.title)}]({route}){date}{badge}")
                    else:
                        if route:
                            items.append(f"- [{md_escape_link_text(entry.title)}]({route})")
                        else:
                            badge = ' <small class="badge-unavailable">未归档</small>'
                            items.append(
                                f"- [{md_escape_link_text(entry.title)}]({md_safe_url(entry.url)}){badge}"
                            )
                blocks.append("\n".join(items))

            if fallback_notes:
                blocks.append(f"## {FALLBACK_CATEGORY}\n")
                ordered = sorted(fallback_notes, key=lambda n: n.date, reverse=True)
                items = []
                for note in ordered:
                    route = self.ctx.route_map.get(note.note_id, f"/notes/{note.note_id}")
                    date = f" <small>{note.date[:10]}</small>" if note.date else ""
                    items.append(f"- [{md_escape_link_text(note.title)}]({route}){date}")
                blocks.append("\n".join(items))

        path = self.cfg.notes_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("notes/index.md")
        return path

    def emit_curated_index(
        self, groups: Sequence[IndexGroup], notes: dict[str, Note]
    ) -> Path:
        """Render hand-curated index references as a separate derived view."""
        blocks = [
            frontmatter({"title": "人工索引", "aside": False}),
            "# 人工索引\n",
            "以下顺序与标签来自原站公告栏。它表示站长的精选引用关系，不改变文章所属房间或日记模块。",
        ]
        current_bulletin = ""
        for group in groups:
            if group.source_bulletin_id != current_bulletin:
                current_bulletin = group.source_bulletin_id
                label = current_bulletin or "未标识的公告"
                blocks.append(f"## 公告 {label}\n")
            blocks.append(f"### {group.title}\n")
            if group.doulist_url:
                blocks.append(f"[豆瓣豆列]({md_safe_url(group.doulist_url)})\n")
            items: list[str] = []
            for entry in group.entries:
                route = self._resolve_entry_route(entry, notes)
                target = route or md_safe_url(entry.url)
                items.append(f"- [{md_escape_link_text(entry.title)}]({target})")
            blocks.append("\n".join(items) if items else "*此分组没有可解析条目。*")

        path = self.cfg.docs_dir / "curated" / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("curated/index.md")
        return path

    def emit_room_pages(
        self,
        rooms: Sequence[Room],
        notes: dict[str, Note],
        albums: Sequence[Album],
        videos: Sequence[Video],
        bulletins: Sequence[Bulletin],
        *,
        note_entries: Sequence[Any] = (),
    ) -> list[Path]:
        """按源站每个 Room 及其标题栏 widget 生成独立入口页。"""
        pages: list[Path] = []
        albums_by_widget = {album.album_id: album for album in albums}
        notes_by_widget: dict[str, list[Note]] = {}
        for note in notes.values():
            notes_by_widget.setdefault(note.widget_id, []).append(note)
        videos_by_widget: dict[str, list[Video]] = {}
        for video in videos:
            videos_by_widget.setdefault(video.widget_id, []).append(video)
        bulletins_by_widget = {bulletin.bulletin_id: bulletin for bulletin in bulletins}

        note_order: dict[str, list[str]] = {}
        for entry in note_entries:
            ids = note_order.setdefault(entry.widget_id, [])
            if entry.note_id not in ids:
                ids.append(entry.note_id)

        for room in rooms:
            blocks = [
                frontmatter({"title": room.title, "aside": False}),
                f"# {room.title}\n",
                f"[返回文章索引](/notes/) · [返回首页](/)\n",
            ]
            for widget in room.widgets:
                blocks.append(
                    f'<span id="widget-{html_attr(widget.widget_id)}"></span>\n\n'
                    f"## {widget.title or widget.kind}\n"
                )
                items: list[str] = []
                if widget.kind == "notes":
                    by_id = {note.note_id: note for note in notes_by_widget.get(widget.widget_id, [])}
                    ordered = [by_id[note_id] for note_id in note_order.get(widget.widget_id, [])
                               if note_id in by_id]
                    seen = {note.note_id for note in ordered}
                    ordered.extend(note for note in notes_by_widget.get(widget.widget_id, [])
                                   if note.note_id not in seen)
                    for note in ordered:
                        route = self.ctx.route_map.get(note.note_id, f"/notes/{note.note_id}")
                        date = f" <small>{note.date[:10]}</small>" if note.date else ""
                        items.append(f"- [{md_escape_link_text(note.title)}]({route}){date}")
                    if not items:
                        items.append("*没有归档到文章。*")
                elif widget.kind == "photos":
                    album = albums_by_widget.get(widget.widget_id)
                    if album:
                        route = self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}")
                        items.append(
                            f"- [{md_escape_link_text(album.title)}]({route}) — {len(album.photos)} 张照片"
                        )
                    else:
                        items.append("*没有归档到相册。*")
                elif widget.kind == "videos":
                    source_url = self.cfg.videos_list_url(widget.widget_id)
                    declared_count = widget.declared_count
                    archived_count = widget.preview_count
                    if archived_count is None:
                        archived_count = len(videos_by_widget.get(widget.widget_id, []))
                    if declared_count is not None:
                        items.append(
                            f"当前保存 **{archived_count}** 条，源模块标题声明 **{declared_count}** 条；"
                            "状态：仅有房间页预览，未枚举完整列表。"
                        )
                    items.append(f"[打开原站视频模块]({md_safe_url(source_url)})")
                    for video in videos_by_widget.get(widget.widget_id, []):
                        items.append(
                            f'<span id="video-{html_attr(video.video_id)}"></span>'
                        )
                        target_url = video.external_url or video.source_url
                        target = md_safe_url(self._external_route(target_url) or target_url)
                        items.append(f"- [{md_escape_link_text(video.title)}]({target})")
                    if not items:
                        items.append("[查看视频归档](/videos)")
                elif widget.kind == "bulletin":
                    bulletin = bulletins_by_widget.get(widget.widget_id)
                    if bulletin:
                        notice = status_notice(bulletin.status)
                        if notice:
                            items.append(notice)
                        body = html_to_markdown(
                            bulletin.content_html,
                            ConvertContext(
                                route_map=self.ctx.route_map,
                                album_routes=self.ctx.album_routes,
                                discussion_routes=self.ctx.discussion_routes,
                                video_routes=self.ctx.video_routes,
                                external_routes=self.ctx.external_routes,
                            ),
                            self.cfg,
                        )
                        if body:
                            items.append(body)
                        else:
                            items.append("*公告正文未能归档。*")
                    if widget.title.startswith("索引"):
                        items.append("[查看人工索引](/curated/)")
                    elif "About" in widget.title or "PPK" in widget.title:
                        items.append("[关于山田尚子](/about)")
                    else:
                        if not bulletin:
                            items.append("*公告栏内容未能归档。*")
                elif widget.kind == "forum":
                    items.append(f"[进入留言板](/board)")
                elif widget.kind == "miniblog":
                    items.append("[进入广播室](/broadcast)")
                else:
                    items.append(f"[查看{md_escape_link_text(widget.title or widget.kind)}](/)")
                blocks.append("\n".join(items))

            path = self.cfg.docs_dir / "rooms" / f"{room.room_id}.md"
            atomic_write_text(path, "\n\n".join(blocks) + "\n")
            self.report.pages.append(path.relative_to(self.cfg.docs_dir).as_posix())
            pages.append(path)
        return pages

    def emit_albums_index(
        self, albums: Sequence[Album], videos: Sequence[Video] = ()
    ) -> Path:
        """渲染包含相册与视频的 /albums/ 媒体索引页。"""
        blocks = [
            frontmatter({"title": "相册", "aside": False}),
            "# 相册\n",
            f"共 **{len(albums)}** 个相册、**{len(videos)}** 条视频。\n",
        ]
        items = []
        for album in albums:
            route = self.ctx.album_routes.get(album.album_id, f"/albums/{album.album_id}")
            items.append(f"- [{md_escape_link_text(album.title)}]({route}) — {len(album.photos)} 张")
        blocks.append("\n".join(items))

        blocks.append("## 视频\n")
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

        path = self.cfg.albums_dir / "index.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("albums/index.md")
        return path

    # ------------------------------------------------------------ 其他页面

    def emit_about(self, bulletin: Bulletin | None, meta: dict[str, str]) -> Path:
        """渲染「关于」页（原站 About PPK）。"""
        blocks = [frontmatter({"title": "关于", "aside": False})]

        if bulletin and bulletin.content_html:
            notice = status_notice(bulletin.status)
            if notice:
                blocks.append(notice)
            body = html_to_markdown(
                bulletin.content_html,
                ConvertContext(route_map=self.ctx.route_map, album_routes=self.ctx.album_routes,
                               external_routes=self.ctx.external_routes,
                               discussion_routes=self.ctx.discussion_routes,
                               video_routes=self.ctx.video_routes),
                self.cfg,
            )
            blocks.append(body)
        else:
            blocks.append("# 关于\n\n*内容未能归档。*")

        blocks.append(
            f"::: info 来源\n本页原为小站公告栏「{bulletin.title if bulletin else 'About PPK'}」，"
            f"归档自 [原站]({self.cfg.site_url})。\n:::"
        )
        path = self.cfg.docs_dir / "about.md"
        atomic_write_text(path, "\n\n".join(blocks) + "\n")
        self.report.pages.append("about.md")
        return path

    def emit_videos(self, videos: Sequence[Video]) -> Path:
        """保留旧 /videos/ 地址，并指向合并后的相册页。"""
        blocks = [
            frontmatter({"title": "视频已并入相册", "aside": False}),
            "# 视频已并入相册\n",
            f"本站的 {len(videos)} 条视频已并入 [相册页面](/albums/#视频)。",
        ]

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
            blocks.append(
                f'<span id="discussion-{html_attr(discussion.discussion_id)}"></span>\n\n'
                f"## {md_escape_link_text(discussion.title)}\n"
            )
            meta_line = " · ".join(
                part for part in [discussion.author, discussion.date] if part
            )
            if meta_line:
                blocks.append(f"*{meta_line}*\n")
            body = html_to_markdown(
                discussion.content_html,
                ConvertContext(route_map=self.ctx.route_map, album_routes=self.ctx.album_routes,
                               external_routes=self.ctx.external_routes,
                               discussion_routes=self.ctx.discussion_routes,
                               video_routes=self.ctx.video_routes),
                self.cfg,
            )
            blocks.append(body or "*正文未能归档。*")

            if discussion.comments:
                blocks.append(f"### 回应（{len(discussion.comments)}）\n")
                for comment in discussion.comments:
                    head = " · ".join(part for part in [comment.author, comment.date] if part)
                    text = html_to_markdown(
                        comment.content_html,
                        ConvertContext(route_map=self.ctx.route_map,
                                       external_routes=self.ctx.external_routes,
                                       discussion_routes=self.ctx.discussion_routes,
                                       video_routes=self.ctx.video_routes),
                        self.cfg,
                    )
                    blocks.append(f"**{head}**\n\n{markdown_blockquote(text)}")
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
        """渲染带图片的广播室卡片，并拆成独立静态分页。"""
        page_size = 10
        page_count = max(1, (len(statuses) + page_size - 1) // page_size)
        page_dir = self.cfg.docs_dir / "broadcast" / "page"

        # 页数减少时移除本生成器之前创建的过期分页文件。
        if page_dir.exists():
            for stale in page_dir.glob("[0-9]*.md"):
                if stale.stem.isdigit() and int(stale.stem) > page_count:
                    stale.unlink()

        first_path: Path | None = None
        for page_number in range(1, page_count + 1):
            start = (page_number - 1) * page_size
            page_items = statuses[start : start + page_size]
            title = "广播室" if page_number == 1 else f"广播室 · 第 {page_number} 页"
            blocks = [
                frontmatter({"title": title, "aside": False}),
                "# 兔子山快报\n",
                f"动态共 **{len(statuses)}** 条 · 第 **{page_number}/{page_count}** 页。\n",
                '<div class="broadcast-feed">',
            ]

            for item in page_items:
                action = html_text(item.text or "更新")
                date = html_text(item.date)
                date_match = re.fullmatch(r"(.+?)(\d{1,2})", item.date)
                date_markup = ""
                if date_match:
                    date_markup = (
                        '<time class="broadcast-date">'
                        f"<span>{html_text(date_match.group(1))}</span>"
                        f"<strong>{html_text(date_match.group(2))}</strong></time>"
                    )
                elif date:
                    date_markup = f'<time class="broadcast-date">{date}</time>'

                link = item.link_url or ""
                if item.object_kind == "1015" and item.object_id:
                    link = self.ctx.route_map.get(item.object_id) or self._external_route(link) or link
                elif item.object_kind == "1025" and item.object_id:
                    link = self.ctx.photo_album_routes.get(item.object_id) or self._external_route(link) or link
                else:
                    note_match = re.search(r"/note/(\d+)/?", link)
                    if note_match:
                        link = self.ctx.route_map.get(note_match.group(1), "") or self._external_route(link) or ""
                    else:
                        link = self._external_route(link) or link
                safe_link = md_safe_url(link) if link else ""

                headline = item.link_title or ("查看归档" if safe_link else "")
                headline_markup = (
                    f'<a class="broadcast-title" href="{html_attr(safe_link)}">'
                    f"{html_text(headline)}</a>"
                    if headline and safe_link
                    else f'<span class="broadcast-title">{html_text(headline)}</span>' if headline else ""
                )
                content = (
                    f'<p class="broadcast-content">{html_text(item.content)}</p>'
                    if item.content
                    else ""
                )

                image = ""
                if item.object_kind == "1025" and item.object_id:
                    image = self.ctx.photo_image_routes.get(item.object_id, "")
                elif item.object_kind == "1015" and item.object_id:
                    image = self.ctx.note_image_routes.get(item.object_id, "")
                # 原站 CDN 对站外图片请求返回 418；只写入已经归档的本地图片，
                # 避免生成必然失败的豆瓣图片请求。
                image_markup = ""
                if image:
                    safe_image = md_safe_url(image)
                    image_markup = (
                        f'<img src="{html_attr(safe_image)}" alt="{html_attr(item.link_title or action)}" '
                        'loading="lazy" decoding="async" />'
                    )
                    if safe_link:
                        image_markup = f'<a class="broadcast-image" href="{html_attr(safe_link)}">{image_markup}</a>'
                    else:
                        image_markup = f'<div class="broadcast-image">{image_markup}</div>'

                blocks.append(
                    '<article class="broadcast-card">'
                    f"{date_markup}"
                    '<div class="broadcast-body">'
                    f'<p class="broadcast-action">{action}</p>'
                    f"{headline_markup}{content}"
                    "</div>"
                    f"{image_markup}"
                    "</article>"
                )

            if not page_items:
                blocks.append('<p class="broadcast-empty">未能归档到动态。</p>')
            blocks.append("</div>")

            if page_count > 1:
                previous = page_number - 1
                following = page_number + 1
                previous_href = "/broadcast/" if previous == 1 else f"/broadcast/page/{previous}"
                next_href = f"/broadcast/page/{following}"
                previous_link = (
                    f'<a class="broadcast-page-link" href="{previous_href}" rel="prev">上一页</a>'
                    if page_number > 1
                    else '<span class="broadcast-page-disabled">上一页</span>'
                )
                next_link = (
                    f'<a class="broadcast-page-link" href="{next_href}" rel="next">下一页</a>'
                    if page_number < page_count
                    else '<span class="broadcast-page-disabled">下一页</span>'
                )
                blocks.append(
                    '<nav class="broadcast-pagination" aria-label="广播室分页">'
                    f"{previous_link}<span>第 {page_number} / {page_count} 页</span>{next_link}</nav>"
                )

            path = (
                self.cfg.docs_dir / "broadcast.md"
                if page_number == 1
                else page_dir / f"{page_number}.md"
            )
            atomic_write_text(path, "\n\n".join(blocks) + "\n")
            self.report.pages.append(path.relative_to(self.cfg.docs_dir).as_posix())
            if page_number == 1:
                first_path = path

        return first_path or (self.cfg.docs_dir / "broadcast.md")

    # ------------------------------------------------------------ Sidebar

    def emit_sidebar(
        self,
        groups: Sequence[IndexGroup],
        notes: dict[str, Note],
        *,
        fallback_notes: Sequence[Note] = (),
        albums: Sequence[Album] = (),
        external_count: int = 0,
        room_sections: Sequence[RoomArticleSection] | None = None,
        rooms: Sequence[Room] = (),
    ) -> Path:
        """生成 ``sidebar.generated.mts``。

        选择生成静态 TS 文件而不是运行时读 JSON：
        构建期零 IO、可被 git 追踪（内容更新时 diff 可见）、
        无需额外插件或虚拟模块。
        """
        notes_sidebar: list[dict[str, Any]] = []
        featured_labels = {
            "聲之形": "☆ 聲之形",
            "玉子市场＆玉子爱情故事": "☆ 玉子",
            "轻音！系列": "☆ 轻音",
            "吹响悠风号": "☆ 悠风 etc.",
        }
        for group in groups:
            if group.title == LINKS_CATEGORY:
                continue
            items: list[dict[str, Any]] = []
            for entry in group.entries:
                route = self._resolve_entry_route(entry, notes)
                if entry.note_id and entry.note_id in notes:
                    note = notes[entry.note_id]
                    items.append({"text": note.title, "link": route})
                else:
                    # 未归档的条目**不能**把外站 URL 当作 link：
                    # VitePress 的 sidebar link 必须是站内路由，否则构建期报
                    # "Invalid route component: undefined"。
                    # 已归档的站外页面则指向站内路由。
                    if route:
                        items.append({"text": entry.title, "link": route})
                    else:
                        items.append({"text": f"{entry.title}（未归档）"})
            if items:
                notes_sidebar.append(
                    {
                        "text": featured_labels.get(group.title, group.title),
                        **(
                            {"link": f"/notes/#{slug_anchor(group.title)}"}
                            if group.title in featured_labels
                            else {}
                        ),
                        "collapsed": True,
                        "items": items,
                    }
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
            },
            {"text": "视频", "link": "/albums/#视频"},
        ]

        room_sidebar: list[dict[str, Any]] = []
        note_sections = {section.widget_id: section for section in (room_sections or [])}
        for room in rooms:
            module_items: list[dict[str, Any]] = []
            for widget in room.widgets:
                widget_href = f"/rooms/{room.room_id}#widget-{widget.widget_id}"
                section = note_sections.get(widget.widget_id)
                if section:
                    module_items.append({
                        "text": widget.title or "日记",
                        "link": widget_href,
                        "collapsed": True,
                        "items": [
                            {
                                "text": note.title,
                                "link": self.ctx.route_map.get(note.note_id, f"/notes/{note.note_id}"),
                            }
                            for note in section.notes
                        ],
                    })
                else:
                    module_items.append({"text": widget.title or widget.kind, "link": widget_href})
            room_sidebar.append({
                "text": room.title,
                "link": "/" if room.is_home else f"/rooms/{room.room_id}",
                "collapsed": True,
                "items": module_items,
            })

        index_items = room_sidebar if rooms else notes_sidebar
        site_sidebar = [
            {
                "text": "房间",
                "collapsed": False,
                "items": index_items,
            },
            {
                "text": "归档视图",
                "collapsed": True,
                "items": [
                    {
                        "text": "文章索引",
                        "link": "/notes/",
                    },
                    {"text": "人工索引", "link": "/curated/"},
                    {"text": "相册", "link": "/albums/"},
                    {"text": "视频", "link": "/videos"},
                    {"text": "关于山田尚子", "link": "/about"},
                    {"text": "留言板汇总", "link": "/board"},
                    {"text": "广播室汇总", "link": "/broadcast"},
                ],
            }
        ]

        sidebar = {
            "/albums/": albums_sidebar,
            "/": site_sidebar,
        }

        content = (
            "// 本文件由 scraper/emit.py 自动生成，请勿手工编辑。\n"
            "// 数据来源：原站 room/widget 结构及其日记列表。\n"
            "import type { DefaultTheme } from 'vitepress'\n\n"
            "export const sidebar: DefaultTheme.Sidebar = "
            + json.dumps(sidebar, ensure_ascii=False, indent=2)
            + " as DefaultTheme.Sidebar\n"
        )
        atomic_write_text(self.cfg.sidebar_path, content)
        self.report.pages.append("sidebar.generated.mts")
        nav = [
            {"text": room.title, "link": "/" if room.is_home else f"/rooms/{room.room_id}"}
            for room in rooms
        ]
        nav_content = (
            "// 本文件由 scraper/emit.py 自动生成，请勿手工编辑。\n"
            "import type { DefaultTheme } from 'vitepress'\n\n"
            "export const nav: DefaultTheme.NavItem[] = "
            + json.dumps(nav, ensure_ascii=False, indent=2)
            + "\n"
        )
        nav_path = self.cfg.docs_dir / ".vitepress" / "nav.generated.mts"
        atomic_write_text(nav_path, nav_content)
        self.report.pages.append("nav.generated.mts")
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
            detail = getattr(record, "detail", "") or ""
            wayback = getattr(record, "wayback_url", None)
            label = labels.get(str(availability), str(availability))
            safe_wayback = md_safe_url(wayback) if wayback else ""
            if safe_wayback:
                label = f"{label}（[快照]({safe_wayback})）"
            cells = (label, url, context, status or "-", detail)
            lines.append("| " + " | ".join(md_table_cell(cell) for cell in cells) + " |")

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
            # 下次同步会自动重试，仅在有实际发生时列出，避免报告中充斥零值。
            transient = stats.get("transientMisses", 0)
            if transient:
                lines.append(
                    f"- 不可信的 404（源站抖动，未写缓存、下次重试）：**{transient}**"
                )

        path = self.cfg.data_dir / "sync-report.md"
        atomic_write_text(path, "\n".join(lines) + "\n")
        return path
