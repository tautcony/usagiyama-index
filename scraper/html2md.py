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

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

from .config import CONFIG, Config

# 需要整段丢弃的标签
DROP_TAGS = ("script", "style", "noscript", "iframe", "object", "embed")
# 只保留子节点、丢掉自身结构的标签
UNWRAP_TAGS = ("table", "thead", "tbody", "tfoot", "tr", "td", "th", "center", "font")

LINK2_HOST_MARKER = "douban.com/link2"
PLAIN_URL_RE = re.compile(
    r"https?://[^\s<>\]\[()\"'，。；：！？、（）【】《》]+", re.IGNORECASE
)

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
    # 注：``urlparse`` / ``parse_qs`` 不会因畸形输入抛出 ``ValueError``
    # （最多返回空结果），此前的 ``try/except ValueError`` 是永不触发的死代码。
    query = parse_qs(urlparse(url).query)
    values = query.get("url")
    if not values:
        return url
    target = values[0].strip()
    return target or url


#: 允许出现在 Markdown 链接里的协议；其余（``javascript:`` / ``data:`` /
#: ``file:`` 等）一律视为危险，退化为纯文字，避免注入可点击的 XSS 链接。
#: 站内相对路径（无 scheme）与 ``/notes/…`` 这类 VitePress 路由也放行。
_SAFE_URL_SCHEMES = ("http", "https", "mailto")


def sanitize_markdown_url(url: str) -> str:
    """把 URL 转成 Markdown 链接安全的写法。

    * 拒绝 ``javascript:`` / ``data:`` 等危险协议（只放行 http(s)/mailto
      与站内相对路径）；
    * 含空格或 ``(`` / ``)`` 的 URL 用尖括号包裹，否则会破坏 ``[text](url)``
      的语法——``)`` 会提前闭合括号，``(`` 同样让解析错位，导致链接目标泄漏。
    """
    if not url:
        return url
    # A raw angle bracket can terminate Markdown's <...> destination and turn
    # the remainder of an attacker-controlled URL into an HTML token.
    if re.search(r"[<>\x00-\x1f]", url):
        return ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme.lower() not in _SAFE_URL_SCHEMES:
        return ""
    if any(ch in url for ch in (" ", "\t", "(", ")")):
        return f"<{url}>"
    return url


def escape_markdown_link_text(text: str) -> str:
    """转义 Markdown 链接文字里的 ``[`` / ``]``，避免提前闭合链接括号。

    例如标题 ``C# [笔记]`` 会让 ``[text](url)`` 在第一个 ``]`` 处提前闭合、
    把剩余 ``](url)`` 泄漏成可见文字。用反斜杠转义后 markdown-it 还原为字面
    方括号，不会破坏链接。
    """
    return text.replace("[", "\\[").replace("]", "\\]")


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
    # forum discussion id → stable local topic anchor
    discussion_routes: dict[str, str] = field(default_factory=dict)
    # video id → stable local module occurrence anchor
    video_routes: dict[str, str] = field(default_factory=dict)
    # 是否保留未归档图片的远程 URL（否则丢弃，避免裂图）
    keep_remote_images: bool = True


class DoubanConverter(MarkdownConverter):
    """针对豆瓣正文定制的 Markdown 转换器。"""

    def __init__(self, ctx: ConvertContext, **options: object) -> None:
        self.ctx = ctx
        super().__init__(**options)

    def escape(self, text: str, parent_tags: set[str]) -> str:
        """Keep text-node markup literal when Markdown is rendered as a page.

        BeautifulSoup decodes entities before markdownify sees them. Escape the
        HTML delimiters here so untrusted text cannot become a raw HTML token.
        ``&`` must be escaped first to avoid double-decoding.
        """
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return super().escape(text, parent_tags)

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
            return f"![{escape_markdown_link_text(alt)}]({sanitize_markdown_url(local)})"
        if self.ctx.keep_remote_images:
            return f"![{escape_markdown_link_text(alt)}]({sanitize_markdown_url(src)})"
        return ""

    def convert_a(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        href = unwrap_link2((el.get("href") or "").strip())
        label = text.strip()
        if not label:
            # 空链接（多为锚点或图标）直接丢弃
            return ""
        if not href or href.startswith("#"):
            return label
        target = self._rewrite_href(href)
        safe_target = sanitize_markdown_url(target)
        if not safe_target:
            # 危险协议（javascript:/data: 等）退化为纯文字，不渲染可点击链接
            return label
        rendered_label = label if "![" in label else escape_markdown_link_text(label)
        return f"[{rendered_label}]({safe_target})"

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

        discussion_match = re.search(
            r"/widget/forum/\d+/discussion/(\d+)(?:/|$)", urlparse(href).path or href
        )
        if discussion_match:
            route = self.ctx.discussion_routes.get(discussion_match.group(1))
            if route:
                return route

        video_match = re.search(
            r"/widget/videos/\d+/video/(\d+)(?:/|$)", urlparse(href).path or href
        )
        if video_match:
            route = self.ctx.video_routes.get(video_match.group(1))
            if route:
                return route

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

        # 同一条豆瓣链接在正文里常见 http/https、www/裸域和尾斜杠的不同写法。
        # 外站目标按页面 ID 去重后只保存了一个原始 URL，因此用 host + path
        # 匹配已有路由，避免这些等价写法漏改写。查询参数与 fragment 不改变页面身份。
        parsed = urlparse(href)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        path = (parsed.path or "/").rstrip("/") or "/"
        if host:
            for key, route in self.ctx.external_routes.items():
                candidate = urlparse(key)
                candidate_host = (candidate.hostname or "").lower().removeprefix("www.")
                candidate_path = (candidate.path or "/").rstrip("/") or "/"
                if host == candidate_host and path == candidate_path:
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
    soup = BeautifulSoup(cleaned, "lxml")
    for text_node in list(soup.find_all(string=True)):
        if text_node.find_parent(["a", "code", "pre", "script", "style"]):
            continue
        raw = str(text_node)
        matches = list(PLAIN_URL_RE.finditer(raw))
        if not matches:
            continue
        pieces: list[object] = []
        cursor = 0
        for match in matches:
            url = match.group().rstrip(".,;:!?，。；：！？、）】》")
            suffix = match.group()[len(url):]
            if not url or converter._rewrite_href(url) == url:
                continue
            pieces.append(NavigableString(raw[cursor:match.start()]))
            anchor = soup.new_tag("a", href=url)
            anchor.string = url
            pieces.append(anchor)
            if suffix:
                pieces.append(NavigableString(suffix))
            cursor = match.end()
        if pieces:
            pieces.append(NavigableString(raw[cursor:]))
            first = pieces[0]
            text_node.replace_with(first)
            for piece in pieces[1:]:
                first.insert_after(piece)
                first = piece
    markdown = converter.convert(str(soup))

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


#: 链接/图片的方括号文字，容许一层嵌套方括号。
#: 豆瓣评论里有人手写 ``[img]…[/img]``，写坏的 URL 里也带着 ``[/img]``，
#: 而 ``[^\]]*`` 一碰到这种 ``]`` 就止步，整条链接匹配不上 —— 于是链接目标
#: 会以 ``](https://…)`` 的形式泄漏进比对文本，从而人为压低相似度。
_BRACKET_TEXT = r"(?:[^\[\]]|\[[^\]]*\])*"


def markdown_to_plain_text(markdown: str) -> str:
    """从 Markdown 还原纯文本，用于与原始 HTML 的纯文本比对。"""
    text = re.sub(r"!\[" + _BRACKET_TEXT + r"\]\([^)]*\)", "", markdown)   # 图片
    text = re.sub(r"\[(" + _BRACKET_TEXT + r")\]\([^)]*\)", r"\1", text)    # 链接保留文字
    text = re.sub(r"[`*_>#]+", "", text)                     # 强调/引用/标题符号
    text = re.sub(r"^\s*[-+*]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("\\", "")
    return re.sub(r"\s+", " ", text).strip()
