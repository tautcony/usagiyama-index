"""HTML 片段 → Markdown。

豆瓣日记正文是「裸文本 + 大量 ``<br>``」结构，没有 ``<p>`` 包裹，
且图片被 ``<div class="cc"><table>...`` 骨架包着。因此采用三段式流水线：

    [A] BeautifulSoup 预处理 —— 规范化为结构良好的 HTML
    [B] markdownify 转换    —— 子类化以精确控制 <br>/<a>/<img>/<table>
    [C] 正则后处理          —— 清理空行、归一化空白

另有两项豆瓣特有的重写：

* **link2 跳转解码**：所有外链都被包成
  ``https://www.douban.com/link2/?url=<urlencoded>``，必须取出真实地址。
* **站内链接重写**：指向已归档日记的链接改写成 VitePress 路由，形成站内互链。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

from .config import CONFIG, Config

# 需要整段丢弃的标签
DROP_TAGS = ("script", "style", "noscript", "iframe", "object", "embed")
# 只保留子节点、丢掉自身结构的标签
UNWRAP_TAGS = ("table", "thead", "tbody", "tfoot", "tr", "td", "th", "center", "font")

LINK2_HOST_MARKER = "douban.com/link2"

# 站内日记链接：site.douban.com/211330/widget/notes/{widget}/note/{note}/
NOTE_PATH_RE = re.compile(r"/widget/notes/(\d+)/note/(\d+)/?")
# 站内相册链接
PHOTO_PATH_RE = re.compile(r"/widget/photos/(\d+)/photo/(\d+)/?")
# 站内相册列表链接
ALBUM_PATH_RE = re.compile(r"/widget/photos/(\d+)/?$")


def unwrap_link2(url: str) -> str:
    """解码豆瓣 ``link2`` 跳转链接，取出真实地址。"""
    if not url or LINK2_HOST_MARKER not in url:
        return url
    try:
        query = parse_qs(urlparse(url).query)
    except ValueError:
        return url
    values = query.get("url")
    if not values:
        return url
    target = values[0].strip()
    return target or url


def _text_of(node: Tag) -> str:
    return node.get_text(strip=True)


@dataclass
class ConvertContext:
    """转换上下文：决定链接与图片如何重写。"""

    note_id: str = ""
    # note_id → 站内路由，例如 {"575615184": "/notes/575615184"}
    route_map: dict[str, str] = field(default_factory=dict)
    # 图片源 URL → 站内路径，例如 {"https://img9.../p1.jpg": "/media/notes/1/p1.jpg"}
    image_map: dict[str, str] = field(default_factory=dict)
    # 相册 ID → 站内路由
    album_routes: dict[str, str] = field(default_factory=dict)
    # 站外页面 URL → 站内路由（已归档的 /topic/、/note/ 等）
    external_routes: dict[str, str] = field(default_factory=dict)
    # 是否保留未归档图片的远程 URL（否则丢弃，避免裂图）
    keep_remote_images: bool = True


class DoubanConverter(MarkdownConverter):
    """针对豆瓣正文定制的 Markdown 转换器。"""

    def __init__(self, ctx: ConvertContext, **options: object) -> None:
        self.ctx = ctx
        super().__init__(**options)

    # ---------------------------------------------------------------- 行内元素

    def convert_br(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        # 单个 <br> → 普通换行。豆瓣正文靠 <br> 分行，其语义由
        # VitePress 的 markdown.breaks = true 还原（见 docs/.vitepress/config.mts）。
        return "\n"

    def convert_img(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        src = (
            el.get("src")
            or el.get("data-src")
            or el.get("data-original")
            or ""
        ).strip()
        if not src:
            return ""
        alt = (el.get("alt") or "").strip()
        local = self.ctx.image_map.get(src)
        if local:
            return f"![{alt}]({local})"
        if self.ctx.keep_remote_images:
            return f"![{alt}]({src})"
        return ""

    def convert_a(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        href = unwrap_link2((el.get("href") or "").strip())
        label = text.strip()
        if not label:
            # 空链接（多为锚点或图标）直接丢弃
            return ""
        if not href or href.startswith("#"):
            return label
        return f"[{label}]({self._rewrite_href(href)})"

    def convert_table(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        # 表格骨架已在预处理中拆掉；若仍有残留，退化为纯文本而非 Markdown 表格
        return text

    # ------------------------------------------------------------------ 工具

    def _rewrite_href(self, href: str) -> str:
        """站内链接改写为 VitePress 路由，站外保持绝对地址。

        关键约束：**只有确实归档了的对象才改写成站内路由**。
        未归档的日记（例如 About PPK 里链到的山田尚子喜欢的电影）必须保留
        原始外链，否则会指向不存在的页面，构建期触发 dead link 而失败。
        """
        match = NOTE_PATH_RE.search(href)
        if match:
            note_id = match.group(2)
            route = self.ctx.route_map.get(note_id)
            if route:
                return route
            # 未归档 → 保留外链，避免制造死链
            return href

        album_match = ALBUM_PATH_RE.search(urlparse(href).path or href)
        if album_match:
            album_id = album_match.group(1)
            route = self.ctx.album_routes.get(album_id)
            if route:
                return route
            return href

        # 已归档的站外页面（索引①/② 里指向豆瓣主站的条目）。
        # 链接写法可能带或不带尾斜杠，两种都要能命中。
        normalized = href.rstrip("/")
        for key in (href, normalized, normalized + "/"):
            route = self.ctx.external_routes.get(key)
            if route:
                return route

        return href


def preprocess(html: str, cfg: Config = CONFIG) -> str:
    """[A] 把豆瓣的松散 HTML 规范化为结构良好的 HTML。"""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()

    # 空的对齐占位单元格 / 清浮动 div
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        classes = tag.get("class") or []
        if "clear" in classes and not _text_of(tag) and not tag.find("img"):
            tag.decompose()

    # 拆掉表格与居中包装，只留内容（豆瓣用它包图片）
    for tag in soup.find_all(UNWRAP_TAGS):
        tag.unwrap()

    # 空的 <p>/<div>/<span> 清掉，避免产生空段落
    for tag in soup.find_all(["p", "div", "span"]):
        if not _text_of(tag) and not tag.find(["img", "br"]):
            tag.decompose()

    return str(soup)


def _normalize_blank_lines(text: str) -> str:
    """[C] 归一化空行与行尾空白。"""
    # 被空行跟随的硬换行空格失去意义
    text = re.sub(r"[ \t]+\n(?=[ \t]*\n)", "\n", text)
    # 仅含空白的行 → 真正的空行
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    # 三个以上换行压成两个
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 行尾空白
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # 开头结尾
    return text.strip()


def _fix_empty_links(text: str) -> str:
    """清理 ``[](url)`` 这类空文本链接，以及空图片。"""
    # 丢弃无源图片
    text = re.sub(r"!\[[^\]]*\]\(\s*\)", "", text)
    # 无文字链接退化为裸 URL；负向后顾避免误伤 ![](url) 形式的图片
    text = re.sub(r"(?<!!)\[\s*\]\(([^)]*)\)", r"\1", text)
    return text


def _fix_bullets(text: str) -> str:
    """统一列表符号，并去掉列表项前的多余空格。"""
    text = re.sub(r"^([ \t]*)[*+]([ \t]+)", r"\1-\2", text, flags=re.MULTILINE)
    return text


def html_to_markdown(
    html: str,
    ctx: ConvertContext | None = None,
    cfg: Config = CONFIG,
) -> str:
    """把一段豆瓣正文 HTML 转成 Markdown。"""
    if not html or not html.strip():
        return ""

    context = ctx or ConvertContext()
    cleaned = preprocess(html, cfg)

    converter = DoubanConverter(
        context,
        heading_style="ATX",
        bullets="-",
        strong_em_symbol="*",
        autolinks=True,
        escape_asterisks=True,
        escape_underscores=True,
        escape_misc=False,
        strip=list(DROP_TAGS),
        convert=None,
        bs4_options="lxml",
        wrap=False,
        keep_inline_images_in=["td", "th", "li", "p", "div", "span"],
    )
    markdown = converter.convert(cleaned)

    markdown = _fix_empty_links(markdown)
    markdown = _fix_bullets(markdown)
    markdown = _normalize_blank_lines(markdown)
    return markdown


# ---------------------------------------------------------------- 校验辅助


def html_to_plain_text(html: str) -> str:
    """提取纯文本，用于内容抽查比对（与 Markdown 做归一化后相似度比较）。"""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()
    text = soup.get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def markdown_to_plain_text(markdown: str) -> str:
    """从 Markdown 还原纯文本，用于与原始 HTML 的纯文本比对。"""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)   # 图片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)    # 链接保留文字
    text = re.sub(r"[`*_>#]+", "", text)                     # 强调/引用/标题符号
    text = re.sub(r"^\s*[-+*]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("\\", "")
    return re.sub(r"\s+", " ", text).strip()
