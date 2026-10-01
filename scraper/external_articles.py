"""Extract readable article bodies from captured external HTML."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .http_client import decode_html


@dataclass(frozen=True)
class ExternalArticle:
    page_id: str
    url: str
    final_url: str
    domain: str
    title: str
    content_html: str
    references: tuple[dict[str, Any], ...]
    adapter: str
    image_map: dict[str, str]
    snapshot: dict[str, Any] | None = None
    republication: dict[str, Any] | None = None

    @property
    def domain_slug(self) -> str:
        return re.sub(r"[^a-z0-9.-]+", "_", self.domain.lower()).strip("._") or "unknown"

    @property
    def route(self) -> str:
        return f"/external-articles/{self.domain_slug}/{self.page_id}"


# Specific selectors first; generic article selectors are the final adapter.
DOMAIN_ADAPTERS: dict[str, tuple[str, ...]] = {
    # Hatena Blog's page shell contains the profile, recent posts and other
    # sidebar modules inside #content. Select the article body directly so the
    # generic density fallback cannot turn that whole shell into an article.
    "kyotoanimation.co.jp": ("article.blogArticle .content", "article .entry", ".entry-content", ".entry", ".post"),
    "mantan-web.jp": (".article_text__wrap", ".article-body", ".entry"),
    "cinema.pia.co.jp": ("#mainNewsMain",),
    "kansai.pia.co.jp": ("#detail_main_contents",),
    "ddnavi.com": ("#article_body", ".entry-content", "[itemprop=articleBody]"),
    "moca-news.net": ("#main-area-article",),
    "anifav.com": (".mod-editableArea",),
    "news.qq.com": ("#Cnt-Main-Article-QQ",),
    "kogyotsushin.com": ("#main",),
    "excite.co.jp": (".article-body", "#newsBody", "#NewsBody", "#articleBody"),
    "watch-watcher.xyz": (".text",),
    "cocolog-nifty.com": (".entry-content",),
    "hanakotoba.name": ("#content > section:first-of-type article.content",),
    "anime-recorder.com": ("#ArticleDetail_data", ".entry-content",),
    "rdm.ne.jp": (".detailin",),
    "rittor-music.jp": (".detailin",),
    "blogspot.com": (".post-body",),
    "weblog.to": (".article-body-inner", ".article-body"),
    "hatena.ne.jp": (".section", ".entry-content"),
    "hatenablog.jp": (".entry-content.hatenablog-entry", ".entry-content"),
    "hatenablog.com": (".entry-content.hatenablog-entry", ".entry-content"),
    "hatenadiary.org": (".entry-content.hatenablog-entry", ".entry-content"),
    "ameblo.jp": ("#entryBody", ".skin-entryBody", ".articleText", "article"),
    "fc2.com": (".entry_body", ".entry-body", ".entry_article", ".mainEntryBody", ".ently_text", ".entry > .index", "#main .entry"),
    "blog.jp": (".article-body-inner", ".article-body", ".entry-content", ".blogbody"),
    "livedoor.jp": (".article-body-inner", ".article-body", ".blogbody"),
    "livedoor.biz": (".blogbody",),
    "natalie.mu": ("article.NA_article", ".NA_powerpush_body", "article"),
    "animatetimes.com": (".news-content", ".article-detail", ".articleBody"),
    "animeanime.jp": ("article.arti-body", ".article_body", ".articleBody"),
    "realsound.jp": ("article.entry-single", ".articleBody", ".article-body"),
    "koenokatachi-movie.com": (".news-content", ".news_detail", ".newsDetail"),
    # These official sites currently return a news index for some archived
    # article URLs. Do not let <main> turn the index into the requested article.
    "anime-eupho.com": (".newsContentList .content", ".news-detail", ".news_detail", ".article-body"),
    "tamakolovestory.com": (
        "#newsIndexData", ".interview", ".specialContents", "#content"
    ),
    "lmaga.jp": (".main_body", ".article_main"),
    "wox.cc": ("#main .com-all[id]",),
}

REMOVE_SELECTORS = (
    "script", "style", "noscript", "iframe", "form", "nav", "header", "footer",
    ".share", ".social", ".related", ".recommend", ".breadcrumb", ".pager",
    ".advertisement", ".ad", "[role=navigation]",
    ".hatena-module", ".entry-footer", ".entry-header", ".entry-date",
    ".entry-categories", ".entry-see-more", ".comment-box",
    ".sidebar", ".sidewrapper", ".author-profile", ".article-share",
    ".share-buttons", ".sns-share", ".social-share", ".related-entries",
    ".related-articles", ".recommended-articles", ".news-navigation",
    "#bookmarkBox", ".news_page", ".fb-comments", ".newsMovies",
    "#ArticleDetail_data_pertinent", "#ArticleDetail_data_imageList_btn",
    ".entry_navi", ".pagenav-outer", ".comment_area", ".relate_dl",
    ".socialicons", ".infoarea", ".posted", ".blogHeader",
    ".ft", ".vctitle", ".vctab", ".vctool",
    ".sp-navigation", ".sp-footer-navigation", ".sp-sideblock",
)


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def detect_capture_access_failure(
    content: bytes, content_type: str, host: str
) -> str | None:
    """Recognize a successful HTTP response that is actually an access gate.

    FC2 private blogs return HTTP 200 with a password form. Treating that as a
    fetched article incorrectly marks the URL complete and prevents retries.
    """
    if not _host_matches(host.lower(), "fc2.com") or not content:
        return None
    soup = BeautifulSoup(decode_html(content, content_type), "lxml")
    text = soup.get_text(" ", strip=True)
    if soup.select_one(".private_lock, .private_lock_title") and (
        "パスワード認証" in text or "閲覧するには管理人が設定した" in text
    ):
        return "FC2 博客启用了访问密码；服务器返回密码验证页（HTTP 200）"
    return None


def article_minimum_text(adapter: str) -> int:
    if adapter == "cocolog-nifty.com":
        return 20
    return 40 if adapter.startswith("hatenablog") or adapter == "hatenadiary.org" else 80


def _select_body(
    soup: BeautifulSoup, host: str, path: str = "", fragment: str = ""
) -> tuple[Tag | None, str]:
    if _host_matches(host, 'kogyotsushin.com') and not re.fullmatch(r'/archives/minitheater/\d{6}/\d+\.php', path):
        return None, 'kogyotsushin.com'
    if host in {'rdm.ne.jp', 'rittor-music.jp'} and path.rstrip('/') == '/sound/column/tamacomanu':
        return soup.select_one('.maincont .listbox'), 'tamacomanu-collection'
    if host in {'priority1.blog51.fc2.com', 'priority1.blog.fc2.com'} and path == '/blog-category-3.html':
        return soup.select_one('.primary'), 'fc2-collection'
    if _host_matches(host, "fc2.com") and (match := re.search(r'/blog-entry-(\d+)\.html', path)):
        # Some themes reuse .entry_body for every comment. The post's stable
        # heading ID distinguishes its body from the comment containers.
        anchor = soup.find(id=match.group(1))
        if anchor and anchor.parent and "entry" in (anchor.parent.get("class") or []):
            return anchor.parent, "fc2.com"
        heading = soup.find(id="e" + match.group(1))
        if heading:
            body = heading.find_next("div", class_="entry_body")
            if body and len(body.get_text(" ", strip=True)) >= 80:
                return body, "fc2.com"
        # This theme reuses entry_article for comments outside the post.
        body = soup.select_one('.entry_container > .entry_article')
        if body:
            return body, "fc2.com"
    if _host_matches(host, "tbs.co.jp"):
        # News indexes contain several unrelated posts. Only the exact linked
        # fragment can identify the archived item.
        anchor = soup.find(id=fragment) if fragment else None
        if anchor is None:
            return None, "tbs.co.jp"
        if path == '/anime/k-on/index-j.html' and fragment == 'bdbox2':
            return anchor, 'tbs.co.jp'
        body = anchor if "news_box" in (anchor.get("class") or []) else anchor.find_next_sibling("div", class_="news_title")
        return (body, "tbs.co.jp") if body else (None, "tbs.co.jp")
    for domain, selectors in DOMAIN_ADAPTERS.items():
        if _host_matches(host, domain):
            # FC2 category/archive pages contain many .entry_body elements.
            # They are navigation pages even though each preview looks like
            # an article; only accept an individual blog-entry URL.
            if _host_matches(host, "fc2.com") and "blog-category-" in path:
                return None, domain
            for selector in selectors:
                # Publisher-specific selectors already isolate the article
                # body, so a short post can still be valid. Keep the higher
                # floor for generic page-wide heuristics below.
                minimum_text = article_minimum_text(domain)
                nodes = [
                    candidate for candidate in soup.select(selector)
                    if len(candidate.get_text(" ", strip=True)) >= minimum_text
                ]
                node = nodes[0] if len(nodes) == 1 else None
                if node:
                    return node, domain
            # A known publisher with a missing/empty article container should
            # not fall through to a page-wide heuristic. This prevents sidebar
            # text from masquerading as the article body.
            return None, domain
    for selector in ("[itemprop=articleBody]", "article", ".entry-content"):
        nodes = [
            node for node in soup.select(selector)
            if len(node.get_text(" ", strip=True)) >= 120
        ]
        if len(nodes) == 1:
            node = nodes[0]
            return node, "generic"
    return None, "unmatched"


def _strip_site_extras(body: Tag, host: str) -> None:
    """Remove publisher chrome that can be nested inside an article body."""
    for selector in REMOVE_SELECTORS:
        for node in body.select(selector):
            node.decompose()

    # Older Ameba themes put a hand-written related-post list at the end of
    # the article body instead of in a sidebar or a separately marked widget.
    if _host_matches(host, "ameblo.jp"):
        for heading in body.find_all(["p", "div"]):
            label = re.sub(r"\s+", "", heading.get_text(" ", strip=True))
            if label not in {"※関連記事", "関連記事"}:
                continue
            current = heading
            while current is not None:
                following = current.next_sibling
                if hasattr(current, "decompose"):
                    current.decompose()
                else:
                    current.extract()
                current = following
            break


def parse_capture(url: str, capture: dict[str, Any], workspace: Path) -> ExternalArticle | None:
    """Parse one successful raw capture. Never performs network requests."""
    if capture.get("fetchStatus") != "fetched" or not capture.get("rawResponse"):
        return None
    path = Path(str(capture["rawResponse"]))
    if not path.is_absolute():
        path = workspace / path
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    soup = BeautifulSoup(decode_html(raw, str(capture.get("contentType", ""))), "lxml")
    final_url = str(capture.get("finalUrl") or url)
    host = (urlparse(final_url).hostname or urlparse(url).hostname or "").lower()
    title = ""
    for selector, attr in (
        ("meta[property='og:title']", "content"),
        ("meta[name='twitter:title']", "content"),
        ("article.blogArticle .blogTitle h3", None),
        ("h1", None),
        ("title", None),
    ):
        node = soup.select_one(selector)
        candidate = str(node.get(attr, "") if attr else node.get_text(" ", strip=True)) if node else ""
        if candidate.strip():
            title = re.sub(r"\s+", " ", candidate).strip()
            break
    body, adapter = _select_body(soup, host, urlparse(final_url).path, urlparse(final_url).fragment)
    if body is None:
        return None
    if adapter == "tbs.co.jp" and (heading := body.find("h3")):
        title = heading.get_text(" ", strip=True)
    image_map = {
        str(source): str(local)
        for source, local in (capture.get("archivedImages") or {}).items()
    }
    for anchor in body.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if href and not href.startswith("#"):
            parsed_href = urlparse(href)
            if not parsed_href.scheme or href.startswith("//"):
                anchor["href"] = urljoin(final_url, href)
    for image in body.find_all("img"):
        source = str(
            image.get("data-src") or image.get("data-original") or image.get("src") or ""
        ).strip()
        if source:
            source_url = urljoin(final_url, source)
            image["src"] = image_map.get(source_url, source_url)
            image.attrs.pop("data-src", None)
            image.attrs.pop("data-original", None)
    _strip_site_extras(body, host)
    text = body.get_text(" ", strip=True)
    minimum_text = article_minimum_text(adapter)
    if len(text) < minimum_text or re.search(r"(?i)domain (?:has )?expired|404 not found|page not found", text[:500]):
        return None
    page_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    references = []
    seen_references: set[tuple[str, int]] = set()
    for reference in capture.get("references") or ():
        identity = (
            str(reference.get("file", "")),
            int(reference.get("line") or 0),
        )
        if identity not in seen_references:
            seen_references.add(identity)
            references.append(reference)
    return ExternalArticle(
        page_id=page_id,
        url=url,
        final_url=final_url,
        domain=host,
        title=title or host,
        content_html=str(body),
        references=tuple(references),
        adapter=adapter,
        image_map=image_map,
        snapshot=capture.get("snapshot"),
        republication=capture.get("republication"),
    )


def extract_image_sources(
    url: str, capture: dict[str, Any], workspace: Path
) -> list[str]:
    """Return deduplicated absolute image URLs inside the selected article body."""
    if capture.get("fetchStatus") != "fetched" or not capture.get("rawResponse"):
        return []
    path = Path(str(capture["rawResponse"]))
    if not path.is_absolute():
        path = workspace / path
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    final_url = str(capture.get("finalUrl") or url)
    host = (urlparse(final_url).hostname or urlparse(url).hostname or "").lower()
    soup = BeautifulSoup(decode_html(raw, str(capture.get("contentType", ""))), "lxml")
    body, _ = _select_body(soup, host, urlparse(final_url).path, urlparse(final_url).fragment)
    if body is None:
        return []
    _strip_site_extras(body, host)
    text = body.get_text(" ", strip=True)
    if len(text) < 80 or re.search(
        r"(?i)domain (?:has )?expired|404 not found|page not found", text[:500]
    ):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for image in body.find_all("img"):
        source = str(
            image.get("data-src") or image.get("data-original") or image.get("src") or ""
        ).strip()
        if not source or source.startswith("data:"):
            continue
        absolute = urljoin(final_url, source)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if absolute not in seen:
            seen.add(absolute)
            result.append(absolute)
    return result


def load_captured_articles(
    captures: dict[str, dict[str, Any]], workspace: Path
) -> list[ExternalArticle]:
    articles = [
        article
        for url, capture in captures.items()
        if (article := parse_capture(url, capture, workspace)) is not None
    ]
    return sorted(articles, key=lambda item: (item.domain, item.title.casefold(), item.page_id))
