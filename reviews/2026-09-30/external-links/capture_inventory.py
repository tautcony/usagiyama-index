"""Offline inventory of URLs actually present in docs/**/*.md.

Run: uv run python reviews/2026-09-30/external-links/capture_inventory.py
Uses VitePress's Markdown parser for links, then distinguishes clickable links,
URLs in visible text, image resources and frontmatter provenance. No crawling.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
URL_RE = re.compile(r"https?://[^\s<>\"'\u3000\u3001\u3002\uff0c\uff08\uff09\u3010\u3011]+")
NODE_RENDER = r"""
import fs from 'node:fs';
import {createMarkdownRenderer} from 'vitepress';
const paths=JSON.parse(fs.readFileSync(0,'utf8'));
const md=await createMarkdownRenderer(process.cwd()+'/docs',{breaks:true},'/');
const pages=paths.map(path=>{
  const source=fs.readFileSync(path,'utf8');
  const match=source.match(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/);
  const body=match?source.slice(match[0].length):source;
  return {path,source,frontmatter:match?.[0]??'',html:md.render(body,{})};
});
process.stdout.write(JSON.stringify(pages));
"""


def canonical(raw: str) -> str:
    """Conservative identity: keep scheme, www, trailing slash and query.

    Fragment is an occurrence attribute; decode only exact Douban link2 hosts.
    This intentionally leaves unverified HTTP/HTTPS and short URL aliases apart.
    """
    url = raw.strip()
    for _ in range(3):
        parsed = urlsplit(url)
        if parsed.hostname not in {"www.douban.com", "douban.com"} or parsed.path != "/link2/":
            break
        target = parse_qs(parsed.query).get("url", [""])[0].strip()
        if not target or target == url:
            break
        url = target
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def kind(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    path = parsed.path
    if host == "site.douban.com" and re.match(r"^/211330(?:/|$)", path):
        return "original_site"
    if "." not in host:
        return "malformed"
    if host in {"douc.cc", "dou.bz", "t.cn"}:
        return "shortlink"
    if host in {"douban.com", "www.douban.com"}:
        if re.match(r"^/(note|topic)/\d+/?$", path):
            return "douban_article"
        if path.startswith("/doulist/"):
            return "douban_collection"
        return "douban_other"
    if host in {"movie.douban.com", "music.douban.com", "book.douban.com"}:
        return "douban_catalog"
    if host.endswith("wikipedia.org") or host == "baike.baidu.com":
        return "encyclopedia"
    if host in {"v.youku.com", "www.bilibili.com", "bilibili.com", "www.youtube.com", "youtu.be", "www.nicovideo.jp", "www.dailymotion.com", "www.tudou.com", "my.tv.sohu.com"}:
        return "video"
    if host in {"twitter.com", "x.com", "weibo.com"}:
        return "social"
    if host in {"www.amazon.co.jp", "www.amazon.com", "kyoanishop.com", "froovie.jp", "www.hobbystock.jp"}:
        return "commerce"
    if host in {"music.163.com", "music.baidu.com", "sensesapporo.bandcamp.com"}:
        return "audio"
    if re.search(r"\.(?:jpg|jpeg|png|gif|webp)(?:$|\[|%5b)", path, re.I) or host in {"p.twipple.jp", "theta360.com"}:
        return "media_reference"
    if host == "trackback.blogsys.jp":
        return "service_endpoint"
    return "web_reference"


LABELS = {
    "original_site": "原站链接（单列）",
    "shortlink": "短链接，待解析",
    "douban_article": "豆瓣日记 / 话题",
    "douban_collection": "豆列",
    "douban_other": "豆瓣其他页面",
    "douban_catalog": "豆瓣作品 / 人物 / 搜索",
    "encyclopedia": "百科资料",
    "video": "视频平台",
    "web_reference": "其他网页（文章 / 官网 / 博客，需细分）",
    "malformed": "畸形地址，禁止直接抓取",
    "social": "社交帖子 / 个人主页",
    "commerce": "商品 / 商店",
    "audio": "音乐平台",
    "media_reference": "图片 / 全景资料链接",
    "service_endpoint": "回链服务端点",
}


def main() -> None:
    paths = sorted(
        str(p.relative_to(ROOT)) for p in (ROOT / "docs").rglob("*.md")
        if ".vitepress" not in p.parts and "public" not in p.relative_to(ROOT / "docs").parts
    )
    rendered = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_RENDER], cwd=ROOT,
        input=json.dumps(paths), text=True, capture_output=True, check=True,
    )
    pages = json.loads(rendered.stdout)
    targets: dict[str, dict] = {}
    resources: dict[str, dict] = {}
    metadata: list[dict] = []

    for page in pages:
        lines = page["source"].splitlines()
        soup = BeautifulSoup(page["html"], "html.parser")
        line_cursors: dict[tuple[str, str], int] = {}

        def add(raw: str, label: str, form: str, *, resource: bool = False) -> None:
            if raw.startswith("//"):
                raw = "https:" + raw
            if not raw.lower().startswith(("http://", "https://")):
                return
            url = canonical(raw)
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return
            store = resources if resource else targets
            item = store.setdefault(url, {
                "id": "url-" + hashlib.sha256(url.encode()).hexdigest()[:16],
                "url": url, "host": parsed.hostname, "category": kind(url),
                "aliases": [], "labels": [], "occurrences": [],
                "networkStatus": "not_checked",
                "reviewFlags": (
                    ["invalid_hostname"] if kind(url) == "malformed" else
                    ["bbcode_in_url"] if re.search(r"\[/img\]|%5b/img%5d", url, re.I) else
                    ["possible_concatenated_prose"] if "今回は" in unquote(url) else []
                ),
            })
            if raw not in item["aliases"]:
                item["aliases"].append(raw)
            label = " ".join(label.split())
            if label and label not in item["labels"]:
                item["labels"].append(label)
            # Locate URLs in original Markdown; if renderer transformed them,
            # allow percent-decoding solely for locating the source evidence.
            candidates = [
                i for i, line in enumerate(lines, 1)
                if raw in html.unescape(line) or unquote(raw) in unquote(html.unescape(line))
            ]
            candidates = [i for i in candidates if i > len(page["frontmatter"].splitlines())]
            key = (raw, form)
            cursor = line_cursors.get(key, 0)
            line_cursors[key] = cursor + 1
            line = candidates[min(cursor, len(candidates) - 1)] if candidates else None
            item["occurrences"].append({
                "file": page["path"], "line": line, "form": form,
                "label": label, "rawUrl": raw, "fragment": urlsplit(raw).fragment,
                "context": lines[line - 1].strip() if line else "",
            })

        for anchor in soup.find_all("a", href=True):
            add(str(anchor["href"]), anchor.get_text(" ", strip=True), "link")
        for node in soup.find_all(string=True):
            if node.find_parent(["a", "code", "pre", "script", "style"]):
                continue
            for match in URL_RE.finditer(str(node)):
                # Sentence punctuation is not part of a prose URL.
                add(match.group().rstrip(".,;!，。；！）】"), str(node)[:240], "text_url")
        for image in soup.find_all("img", src=True):
            add(str(image["src"]), str(image.get("alt", "")), "image", resource=True)
        for match in URL_RE.finditer(page["frontmatter"]):
            metadata.append({"file": page["path"], "url": match.group().rstrip("\"'"), "form": "frontmatter"})

    links = sorted(targets.values(), key=lambda item: (item["host"], item["url"]))
    external = [item for item in links if item["category"] != "original_site"]
    original = [item for item in links if item["category"] == "original_site"]
    summary = {
        "markdownFiles": len(paths), "externalTargets": len(external),
        "externalOccurrences": sum(len(item["occurrences"]) for item in external),
        "externalHosts": len({item["host"] for item in external}),
        "clickableTargets": sum(any(o["form"] == "link" for o in i["occurrences"]) for i in external),
        "textOnlyTargets": sum(all(o["form"] == "text_url" for o in i["occurrences"]) for i in external),
        "originalSiteTargets": len(original),
        "originalSiteOccurrences": sum(len(item["occurrences"]) for item in original),
        "remoteImageTargets": len(resources), "frontmatterUrls": len(metadata),
        "flaggedTargets": sum(bool(item["reviewFlags"]) for item in external),
    }
    payload = {"schemaVersion": 1, "scope": "docs/**/*.md; excludes .vitepress and public", "networkChecked": False,
               "summary": summary, "links": external, "originalSiteLinks": original,
               "remoteImages": list(resources.values()), "frontmatterUrls": metadata}
    (OUT / "inventory.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    report = ["# docs Markdown 外部链接清单", "",
              "以当前 `docs/**/*.md` 为准；排除构建产物和 `public`。不读取 `data/*.json`。",
              "用 VitePress 解析 Markdown 和裸 HTML，统计可点击链接及可见正文中的纯文本 URL。",
              "原站 `site.douban.com/211330`、图片资源、frontmatter 来源另列，不混入外部资料数量。",
              "仅移除 fragment 做请求目标去重；保留 query、HTTP/HTTPS、www、尾斜杠差异，未联网确认等价。",
              "因此数量表示不同 URL 请求目标，并非已证明互不相同的文章。所有可达性均为未检查。", "",
              "```json", json.dumps(summary, ensure_ascii=False, indent=2), "```", "",
              "## 类型", "", "| 类别 | 目标 URL | 引用次数 |", "| --- | ---: | ---: |"]
    for category, count in sorted(Counter(i["category"] for i in external).items()):
        report.append(f"| {LABELS[category]} | {count} | {sum(len(i['occurrences']) for i in external if i['category'] == category)} |")
    report += ["", "## 异常地址", "", "保留原始证据，先修正/确认后再入抓取队列。", ""]
    for item in external:
        if item["reviewFlags"]:
            occurrence = item["occurrences"][0]
            report.append(f"- `{item['url']}` — {', '.join(item['reviewFlags'])}；{occurrence['file']}:{occurrence['line']}")
    report += ["", "## 域名", "", "| 域名 | 目标 URL | 引用次数 |", "| --- | ---: | ---: |"]
    for host, count in Counter(i["host"] for i in external).most_common():
        report.append(f"| {host} | {count} | {sum(len(i['occurrences']) for i in external if i['host'] == host)} |")
    report += ["", "## 完整目标列表", "", "每个 URL 列出首个引用标签和全部来源页面；精确位置、原始 URL、上下文见 `inventory.json`。", ""]

    def escape(text: str) -> str:
        return html.escape(text).replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;")

    for host in sorted({i["host"] for i in external}):
        report += [f"### {host}", "", "| 目标与标签 | 类型 / 形式 | 来源页面 |", "| --- | --- | --- |"]
        for item in external:
            if item["host"] != host:
                continue
            label = item["labels"][0][:140] if item["labels"] else item["url"]
            occurrences = list(dict.fromkeys(f"{o['file']}:{o['line'] or '?'}" for o in item["occurrences"]))
            forms = "可点击" if any(o["form"] == "link" for o in item["occurrences"]) else "纯文本"
            report.append(f"| [{escape(label)}](<{item['url']}>)<br>`{item['url']}` | {LABELS[item['category']]} / {forms} | {'<br>'.join(occurrences)} |")
        report.append("")
    report += ["## 附属 URL", "", f"原站链接：{len(original)} 个目标；见 JSON 的 `originalSiteLinks`。",
               f"正文远程图片：{len(resources)} 个目标；见 `remoteImages`。",
               f"frontmatter URL：{len(metadata)} 次；见 `frontmatterUrls`。", "",
               "重新统计：`uv run python reviews/2026-09-30/external-links/capture_inventory.py`。", ""]
    (OUT / "inventory.md").write_text("\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
