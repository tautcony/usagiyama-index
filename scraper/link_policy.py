"""Conservative domain/path classification for the external-link crawl queue."""

from __future__ import annotations

import re
from urllib.parse import urlparse

SHORT_HOSTS = {"douc.cc", "dou.bz", "t.cn"}
VIDEO_HOSTS = {
    "youku.com", "v.youku.com", "nicovideo.jp", "ch.nicovideo.jp",
    "bilibili.com", "tudou.com", "my.tv.sohu.com",
}
MUSIC_HOSTS = {"music.163.com", "music.baidu.com", "bandcamp.com"}
SOCIAL_HOSTS = {"twitter.com", "x.com", "weibo.com", "weibo.cn"}
ENCYCLOPEDIA_HOSTS = {"wikipedia.org", "baike.baidu.com", "dic.pixiv.net", "dic.nicovideo.jp"}
COMMERCE_HOSTS = {"amazon.com", "amazon.co.jp", "kyoanishop.com", "froovie.jp", "hobbystock.jp"}
PHOTO_HOSTS = {"theta360.com", "p.twipple.jp", "img3.douban.com", "img3.doubanio.com", "ww3.sinaimg.cn", "wx4.sinaimg.cn"}
TRACKBACK_HOSTS = {"trackback.blogsys.jp"}
ARTICLE_HOSTS = {
    "blog.fc2.com", "fc2.com", "ameblo.jp", "hatena.ne.jp", "hatenablog.jp",
    "livedoor.jp", "doorblog.jp", "blog.jp", "blogspot.jp", "blogspot.com",
    "cocolog-nifty.com", "weblog.to", "seesaa.net", "wox.cc",
    "crea.bunshun.jp", "natalie.mu", "mantan-web.jp", "realsound.jp",
    "animeanime.jp", "animatetimes.com", "animatetv.jp", "anime-recorder.com",
    "dengekionline.com", "news.mynavi.jp", "asahi.com", "cinematoday.jp",
    "walkerplus.com", "moca-news.net", "news.qq.com", "news.sina.com.cn",
    "tokyo-anime-news.jp", "anifav.com", "hatena.ne.jp", "hatenanews.com",
}
ARTICLE_PATH_MARKERS = (
    "/blog/", "/entry/", "/archives/", "/blog-entry-", "/note/", "/column/",
    "/interview/", "/feature/", "/special/", "/news/", "/article/", "/post/",
)


def _matches(host: str, domains: set[str]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def classify_external_link(url: str) -> dict[str, str]:
    """Return stable category, crawl action and reason for a candidate URL.

    ``fetch_article`` is intentionally reserved for domains/paths that strongly
    identify an article. ``review`` means an operator must inspect the URL/page
    before it can enter an automated body-capture queue.
    """
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    path = (parsed.path or "/").lower()
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        return {"category": "畸形地址", "action": "skip", "reason": "仅接受有效 HTTP/HTTPS URL"}
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        ascii_host = ""
    labels = ascii_host.split(".")
    if (re.search(r"[\u3400-\u9fff]", host) and "." not in host) or not ascii_host or any(
        len(label) > 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        return {"category": "畸形地址", "action": "skip", "reason": "主机名无效或包含拼接文本"}
    if _matches(host, SHORT_HOSTS):
        return {"category": "短链接", "action": "resolve", "reason": "解析最终地址后重新分类"}
    if _matches(host, TRACKBACK_HOSTS):
        return {"category": "回链服务端点", "action": "skip", "reason": "不是面向读者的内容页面"}
    if host == "douban.com" or host.endswith(".douban.com"):
        if host in {"douban.com", "www.douban.com"} and path.rstrip("/") == "/link2":
            return {"category": "短链接", "action": "resolve", "reason": "解包豆瓣 link2 后重新分类"}
        if host in {"douban.com", "www.douban.com", "movie.douban.com", "music.douban.com"}:
            if "/note/" in path or "/topic/" in path:
                return {"category": "豆瓣日记 / 话题", "action": "fetch_article", "reason": "豆瓣文章内容路径"}
            if "/doulist/" in path:
                return {"category": "豆列", "action": "metadata", "reason": "列表使用专用有序集合适配器"}
            if "/subject_search" in path:
                return {"category": "豆瓣作品 / 人物 / 搜索", "action": "metadata", "reason": "搜索结果不作为文章正文抓取"}
            if any(part in path for part in ("/subject/", "/celebrity/", "/personage/", "/people/", "/photo/", "/trailer/")):
                return {"category": "豆瓣作品 / 人物 / 搜索", "action": "metadata", "reason": "豆瓣结构化资料页"}
        return {"category": "豆瓣其他页面", "action": "metadata", "reason": "保留资料链接，等待专用类型规则"}
    if _matches(host, VIDEO_HOSTS):
        return {"category": "视频平台", "action": "metadata", "reason": "保存播放页元信息，不抓取视频正文"}
    if _matches(host, MUSIC_HOSTS):
        return {"category": "音乐平台", "action": "metadata", "reason": "保存曲目/专辑元信息，不抓取播放内容"}
    if _matches(host, SOCIAL_HOSTS):
        return {"category": "社交帖子 / 个人主页", "action": "metadata", "reason": "静态帖子/主页元信息，不抓取动态流"}
    if _matches(host, ENCYCLOPEDIA_HOSTS):
        return {"category": "百科资料", "action": "metadata", "reason": "作为资料引用，不抓取文章副本"}
    if _matches(host, COMMERCE_HOSTS):
        return {"category": "商品 / 商店", "action": "skip", "reason": "商品及商店链接不进入外链归档"}
    if (_matches(host, PHOTO_HOSTS)
            or any(ext in path for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"))
            or "/image/" in path or "/photo/" in path):
        return {"category": "图片 / 全景资料链接", "action": "metadata", "reason": "媒体目标不进入文章抓取"}
    if _matches(host, {"ameblo.jp"}):
        if re.search(r"/entry-\d+\.html$", path):
            return {"category": "其他网页（文章 / 官网 / 博客）", "action": "fetch_article", "reason": "Ameblo 文章详情路径"}
        return {"category": "其他网页（文章 / 官网 / 博客）", "action": "metadata", "reason": "Ameblo 博客主页，不当作文章正文"}
    if _matches(host, ARTICLE_HOSTS) and path not in {"", "/"}:
        return {"category": "其他网页（文章 / 官网 / 博客）", "action": "fetch_article", "reason": "已知文章/博客/新闻发布域名"}
    strong_article_path = any(
        marker in path for marker in (
            "/entry/", "/archives/", "/blog-entry-", "/note/", "/column/",
            "/interview/", "/article/", "/post/", "/news/",
        )
    ) or ("/blog/" in path and any(key.lower() in parsed.query.lower() for key in ("p=", "id=")))
    if strong_article_path:
        return {"category": "其他网页（文章 / 官网 / 博客）", "action": "fetch_article", "reason": "明确文章路径或带文章 ID 的博客 URL"}
    if any(marker in path for marker in ARTICLE_PATH_MARKERS):
        return {"category": "其他网页（文章 / 官网 / 博客）", "action": "review", "reason": "URL 路径像文章，但域名未列入可信文章站点"}
    return {"category": "其他网页（文章 / 官网 / 博客）", "action": "review", "reason": "域名和路径不足以确认是文章页面"}
