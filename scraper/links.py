"""Build an offline inventory of external URLs used by generated Markdown."""

from __future__ import annotations

import re
import html
import json
import ipaddress
import subprocess
from collections import defaultdict
from collections import Counter
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from .config import CONFIG, Config
from .link_policy import classify_external_link
from .util import atomic_write_text, write_json

URL_RE = re.compile(r"https?://[^\s<>\]\[()\"'，。；：！？、（）【】《》]+", re.IGNORECASE)
TRAILING = ".,;:!?，。；：！？）】、）"
ENCODED_CJK_DELIMITER_RE = re.compile(
    r"(?i)%EF%BC%(?:8C|9A|9B|81|9F|88|89)|%E3%80%(?:81|82|8C|8D)"
)
CJK_DELIMITER_RE = re.compile(r"[，。；：！？、（）【】《》]")
NODE_RENDER = r"""
import fs from 'node:fs';
import {createMarkdownRenderer} from 'vitepress';
let raw=''; for await (const chunk of process.stdin) raw += chunk;
const input=JSON.parse(raw);
const paths=input.paths;
const md=await createMarkdownRenderer(input.root,{breaks:true},'/');
const pages=paths.map(path=>{
 const source=fs.readFileSync(path,'utf8');
 const match=source.match(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/);
 const body=match?source.slice(match[0].length):source;
 return {path,source,frontmatter:match?.[0]??'',html:md.render(body,{})};
});
process.stdout.write(JSON.stringify(pages));
"""


def _clean_url(value: str) -> str:
    return value.rstrip(TRAILING)


def _reference_key(reference: dict[str, Any]) -> tuple[str, Any]:
    return str(reference.get("file", "")), reference.get("line")


def _append_reference(references: list[dict[str, Any]], reference: dict[str, Any]) -> None:
    if _reference_key(reference) not in {_reference_key(item) for item in references}:
        references.append(reference)


def resolved_destination(url: str) -> str:
    """Unwrap a captured Douban link2 hop to the actual HTTP(S) target."""
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() not in {"douban.com", "www.douban.com"} or parsed.path.rstrip("/") != "/link2":
        return url
    values = parse_qs(parsed.query).get("url", [])
    if not values:
        return url
    target = values[0].strip()
    if not urlparse(target).scheme:
        target = unquote(target)
    target_parsed = urlparse(target)
    if target_parsed.scheme.lower() not in {"http", "https"} or not target_parsed.hostname:
        return url
    hostname = target_parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return url
    try:
        if not ipaddress.ip_address(hostname).is_global:
            return url
    except ValueError:
        pass
    return target


def record_resolved_destinations(captures: dict[str, dict[str, Any]]) -> None:
    """Persist the actual target and its policy alongside each resolved short URL."""
    for short_url, capture in captures.items():
        if capture.get("action") != "resolve":
            continue
        destination = resolved_destination(str(capture.get("finalUrl") or short_url))
        policy = classify_external_link(destination)
        if destination == short_url or policy["action"] == "resolve" or (
            policy["action"] == "skip" and policy["category"] != "商品 / 商店"
        ):
            continue
        capture["resolvedUrl"] = destination
        capture["finalCategory"] = policy["category"]
        capture["finalAction"] = policy["action"]
        if capture.get("fetchStatus") == "resolved_non_article" and policy["action"] == "fetch_article":
            capture["fetchStatus"] = "resolved_pending_article"


def resolved_link_targets(
    targets: dict[str, dict[str, Any]], captures: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Group captured short links beneath their destination domain and policy."""
    resolved: dict[str, dict[str, Any]] = {}
    for url, target in targets.items():
        if classify_external_link(url)["category"] == "商品 / 商店":
            continue
        capture = captures.get(url) or {}
        destination = url
        if target.get("action") == "resolve":
            candidate = resolved_destination(str(capture.get("resolvedUrl") or capture.get("finalUrl") or url))
            policy = classify_external_link(candidate)
            if policy["category"] == "商品 / 商店":
                continue
            if candidate != url and policy["action"] not in {"resolve", "skip"}:
                destination = candidate
        entry = resolved.setdefault(destination, {
            "requestedUrl": destination,
            "domain": (urlparse(destination).hostname or "").lower().rstrip("."),
            "references": [],
            "resolvedFrom": [],
        })
        for reference in target.get("references", []):
            _append_reference(entry["references"], reference)
        for flag in target.get("reviewFlags", []):
            flags = entry.setdefault("reviewFlags", [])
            if flag not in flags:
                flags.append(flag)
        if destination != url:
            entry["resolvedFrom"].append({"url": url, "references": target.get("references", [])})
    for url, target in resolved.items():
        target.update(classify_external_link(url))
    return resolved


def _extract_urls(raw: str) -> tuple[list[str], bool]:
    """Split prose joined to a URL at CJK punctuation and recover later URLs."""
    found: list[str] = []
    suspicious = False
    # An anchor can contain several copied URLs separated by prose. Encoded
    # punctuation survives Markdown rendering in href attributes, so split it
    # before matching each URL token.
    chunks = ENCODED_CJK_DELIMITER_RE.split(raw)
    if len(chunks) > 1:
        suspicious = True
    for chunk in chunks:
        if CJK_DELIMITER_RE.search(chunk):
            suspicious = True
        for match in URL_RE.finditer(chunk):
            url = _clean_url(match.group())
            if url:
                found.append(url)
    # Do not collapse duplicate occurrences here; callers retain each source
    # occurrence while target identities are still deduplicated by URL.
    return found, suspicious


def reference_route(reference: dict[str, Any], docs_dir: Path) -> str:
    """Link to the source document, including its room module when known."""
    file = str(reference.get("file", ""))
    route = "/" + file.removesuffix(".md") if file else ""
    line = reference.get("line")
    if not re.fullmatch(r"rooms/[0-9]+\.md", file) or not isinstance(line, int) or line < 1:
        return route
    source = docs_dir / file
    if not source.is_file():
        return route
    preceding = "\n".join(source.read_text(encoding="utf-8").splitlines()[:line])
    widgets = re.findall(r'<span id="(widget-[0-9]+)"', preceding)
    return f"{route}#{widgets[-1]}" if widgets else route


def reference_label(reference: dict[str, Any], docs_dir: Path) -> str:
    """Name the document that contains a link, not the link's anchor text."""
    file = str(reference.get("file", ""))
    fallback = str(reference.get("label") or file)
    if not file or not (source := docs_dir / file).is_file():
        return fallback
    lines = source.read_text(encoding="utf-8").splitlines()
    title_line = next((line for line in lines[:20] if line.startswith("title: ")), "")
    if not title_line:
        return fallback
    value = title_line.removeprefix("title: ")
    try:
        title = json.loads(value)
    except json.JSONDecodeError:
        title = value
    if not isinstance(title, str) or not title:
        return fallback
    line = reference.get("line")
    if re.fullmatch(r"rooms/[0-9]+\.md", file) and isinstance(line, int) and line > 0:
        preceding = lines[:line]
        widgets = [i for i, text in enumerate(preceding) if re.search(r'<span id="widget-[0-9]+"', text)]
        if widgets:
            heading = next((text.removeprefix("## ") for text in preceding[widgets[-1] + 1:] if text.startswith("## ")), "")
            if heading:
                return f"{title} · {heading}"
    return title


def scan_external_links(docs_dir: Path) -> dict[str, dict[str, object]]:
    """Parse Markdown through VitePress, then retain each link/text URL occurrence."""
    targets: dict[str, dict[str, object]] = {}
    paths = sorted(
        str(path) for path in docs_dir.rglob("*.md")
        if ".vitepress" not in path.parts and "public" not in path.relative_to(docs_dir).parts
        and path.relative_to(docs_dir).parts[:1] not in {
            ("external",), ("external-articles",), ("links",)
        }
    )
    rendered = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_RENDER],
        cwd=Path(__file__).resolve().parents[1],
        input=json.dumps({"root": str(docs_dir), "paths": paths}), text=True,
        capture_output=True, check=True,
    )
    for page in json.loads(rendered.stdout):
        lines = page["source"].splitlines()
        soup = BeautifulSoup(page["html"], "html.parser")

        def add(raw: str, label: str, form: str) -> None:
            urls, suspicious = _extract_urls(raw.strip())
            for url in urls:
                add_one(url, raw, label, form, suspicious)

        def add_one(url: str, raw: str, label: str, form: str, suspicious: bool) -> None:
            parsed = urlparse(url)
            if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
                    or classify_external_link(url)["category"] in {"畸形地址", "商品 / 商店"}):
                return
            host = parsed.hostname.lower().rstrip(".")
            record = targets.setdefault(url, {"requestedUrl": url, "domain": host, "references": []})
            if suspicious:
                record.setdefault("reviewFlags", [])
                if "cjk_punctuation_split" not in record["reviewFlags"]:
                    record["reviewFlags"].append("cjk_punctuation_split")
            source_line = next((i for i, line in enumerate(lines, 1) if raw in html.unescape(line)), None)
            ref = {"file": str(Path(page["path"]).relative_to(docs_dir)), "line": source_line,
                   "label": " ".join(label.split()), "form": form, "rawUrl": raw}
            refs = record["references"]
            _append_reference(refs, ref)  # type: ignore[arg-type]

        for anchor in soup.find_all("a", href=True):
            add(str(anchor["href"]), anchor.get_text(" ", strip=True), "link")
        for node in soup.find_all(string=True):
            if node.find_parent(["a", "code", "pre", "script", "style"]):
                continue
            for match in URL_RE.finditer(str(node)):
                add(match.group(), str(node)[:200], "text_url")
    for url, target in targets.items():
        target.update(classify_external_link(url))
    return targets


def emit_links_index(
    cfg: Config = CONFIG,
    external_pages: Sequence[Any] = (),
    archived_article_routes: dict[str, str] | None = None,
    captures: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, object]]:
    """Write data/links.json and a domain-grouped, source-linked /links/ page."""
    targets = scan_external_links(cfg.docs_dir)
    archived_article_routes = archived_article_routes or {}
    # Archived targets are often rewritten to local routes in Markdown. Restore
    # their source URLs from the archive records and retain all known origins.
    for page in external_pages:
        url = str(page.url or "").strip()
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            continue
        record = targets.setdefault(url, {
            "requestedUrl": url,
            "domain": parsed.hostname.lower().rstrip("."),
            "references": [],
        })
        refs = record["references"]
        for origin in page.origins or ([page.origin] if page.origin else []):
            reference = {"file": "", "line": 0, "label": origin}
            _append_reference(refs, reference)  # type: ignore[arg-type]
    targets = resolved_link_targets(targets, captures or {})
    write_json(cfg.data_dir / "links.json", targets)
    crawl_queue = {
        url: target for url, target in targets.items()
        if target.get("action") in {"fetch_article", "resolve"}
    }
    write_json(cfg.data_dir / "external-queue.json", crawl_queue)
    by_domain: dict[str, list[dict[str, object]]] = defaultdict(list)
    for target in targets.values():
        by_domain[str(target["domain"])].append(target)

    category_counts = Counter(str(target.get("category", "待分类")) for target in targets.values())
    summary = "；".join(f"{category} {count}" for category, count in sorted(category_counts.items()))
    sections = [
        "---\ntitle: 外部链接\naside: false\n---",
        "# 外部链接索引\n",
        f"共登记 {len(targets)} 个 URL，按域名和类型分类；引用位置指向使用该链接的本地页面。",
        f"类型统计：{summary}。",
        "自动队列只收 `fetch_article` 与 `resolve`；`metadata` 仅登记，`review` 等待判定，`skip` 禁止请求。",
    ]
    for domain, entries in sorted(by_domain.items()):
        lines = [f"## {domain}\n"]
        for target in sorted(entries, key=lambda item: str(item["requestedUrl"])):
            url = str(target["requestedUrl"])
            safe_url = url.replace("(", "%28").replace(")", "%29")
            route = archived_article_routes.get(url)
            target_link = f"[{url}]({route})" if route else f"[{url}]({safe_url})"
            original_link = f" · [原站]({safe_url})" if route else ""
            lines.append(
                f"- {target_link}{original_link} · {target.get('category', '待分类')} · "
                f"抓取策略：`{target.get('action', 'review')}`"
            )
            short_references: set[tuple[str, Any]] = set()
            for source in target.get("resolvedFrom", []):
                short_url = str(source["url"])
                short_link = short_url.replace("(", "%28").replace(")", "%29")
                for ref in source["references"]:
                    short_references.add(_reference_key(ref))
                    source_route = reference_route(ref, cfg.docs_dir)
                    source_label = reference_label(ref, cfg.docs_dir)
                    source_text = f"[{source_label}]({source_route})" if source_route else source_label
                    line_note = f" · 第 {ref['line']} 行" if ref.get("line") else ""
                    lines.append(f"  - 解析自 [{short_url}]({short_link})；来自：{source_text}{line_note}")
            refs = target["references"]
            for ref in refs:  # type: ignore[union-attr]
                if _reference_key(ref) in short_references:
                    continue
                route = reference_route(ref, cfg.docs_dir)
                label = reference_label(ref, cfg.docs_dir)
                if route:
                    suffix = f" · 第 {ref['line']} 行" if ref.get("line") else ""
                    source = f"[{label}]({route}){suffix}"
                else:
                    source = _origin_link(label)
                lines.append(f"  - 使用来源：{source}")
        sections.append("\n".join(lines))
    if not targets:
        sections.append("*尚未发现外部链接。*")
    output = cfg.docs_dir / "links" / "index.md"
    atomic_write_text(output, "\n\n".join(sections) + "\n")
    return targets


def _origin_link(origin: str) -> str:
    for prefix, route_prefix in (("日记 ", "/notes/"), ("站外页面 ", "/external/")):
        if origin.startswith(prefix):
            object_id = origin[len(prefix):].split(" 的", 1)[0].strip()
            if object_id and re.fullmatch(r"[A-Za-z0-9_-]+", object_id):
                return f"[{origin}]({route_prefix}{object_id})"
    return origin
