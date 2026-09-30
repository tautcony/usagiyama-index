"""Read cached source pages and current products; write only this review's evidence.

Run from the repository: uv run python reviews/2026-09-30/topology/capture_evidence.py
No network, no emit, no progress/manifest writes. Not a production topology verifier.
"""

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[3]


def load(name):
    value = json.loads((ROOT / name).read_text())
    if isinstance(value, dict):
        value.pop("_meta", None)
    return value


def relative(path):
    return path.relative_to(ROOT).as_posix()


def slug(text):
    # For auditing these Chinese headings; production verification must use
    # actual VitePress-built DOM IDs, including duplicate-heading suffixes.
    import unicodedata
    value = unicodedata.normalize("NFKD", text)
    value = re.sub(r"[\u0300-\u036f\x00-\x1f]", "", value)
    value = re.sub(r'''[\s~`!@#$%^&*()\-_+=[\]{}|\\;:\"'“”‘’<>,.?/]+''', "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-").lower()


def main():
    structure = load("data/structure.json")
    notes = load("data/notes.json")
    albums = load("data/albums.json")
    bulletins = load("data/bulletins.json")
    indexes = load("data/index.json")
    source_pages = []
    source_room_ids = []
    for meta_path in sorted((ROOT / "scraper/state/cache/site.douban.com").glob("*.json")):
        meta = json.loads(meta_path.read_text())
        url = meta.get("url", "")
        if not re.fullmatch(r"https?://site\.douban\.com/211330/(?:room/\d+/)?", url):
            continue
        body = meta_path.with_suffix(".body")
        if not body.exists() or meta.get("status") != 200:
            continue
        soup = BeautifulSoup(body.read_text(errors="replace"), "lxml")
        nav = [
            {"title": a.get_text(" ", strip=True), "url": a["href"],
             "active": "on" in (a.parent.get("class") or [])}
            for a in soup.select(".nav-items a[href]")
        ]
        if url.endswith("/211330/"):
            source_room_ids = [re.search(r"/room/(\d+)/", a["url"])[1] for a in nav]
        widgets = []
        for node in soup.select("div.mod[id]"):
            match = re.fullmatch(r"(bulletin|notes|photos|videos|forum|miniblog)-(\d+)", node["id"])
            if not match:
                continue
            heading = node.find("h2")
            widget = {
                "kind": match[1], "widgetId": match[2], "position": len(widgets),
                "heading": heading.get_text(" ", strip=True) if heading else "",
                "allLinks": [a["href"] for a in heading.select("a[href]")] if heading else [],
            }
            if match[1] == "videos":
                count = re.search(r"视频\s*\((\d+)\)", widget["heading"])
                widget["declaredCount"] = int(count[1]) if count else None
                widget["previewCount"] = len(node.select(".item-video"))
            if match[1] == "bulletin":
                report = node.find(id="link-report")
                widget["linkCount"] = len(report.select("a[href]")) if report else 0
            widgets.append(widget)
        source_pages.append({"url": url, "bodyPath": relative(body),
                             "fetchedAt": meta.get("fetchedAt"),
                             "sha256": hashlib.sha256(body.read_bytes()).hexdigest(),
                             "navigation": nav, "widgets": widgets})

    notes_text = (ROOT / "docs/notes/index.md").read_text()
    headings = re.findall(r"^## (.+)$", notes_text, re.MULTILINE)
    heading_ids = {slug(h) for h in headings}
    home_text = (ROOT / "docs/index.md").read_text()
    features_match = re.search(r"^features: (.+)$", home_text, re.MULTILINE)
    features = json.loads(features_match[1]) if features_match else []
    missing_features = [f for f in features if f.get("link", "").startswith("/notes/#")
                        and f["link"].split("#", 1)[1] not in heading_ids]
    indexed_ids = {e["noteId"] for g in indexes for e in g["entries"] if e.get("noteId")}
    owners = {w["widget_id"]: r["room_id"] for r in structure["rooms"] for w in r["widgets"]}
    audited_paths = ["scraper/models.py", "scraper/parsers.py", "scraper/discover.py",
                     "scraper/index_map.py", "scraper/cli.py", "scraper/emit.py",
                     "scraper/html2md.py", "scraper/verify.py", "docs/.vitepress/config.mts",
                     "docs/.vitepress/sidebar.generated.mts", "docs/index.md", "docs/notes/index.md",
                     "data/structure.json", "data/notes.json", "data/index.json", "data/albums.json"]
    result = {
        "capturedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "scope": "Cached source snapshot, current dirty worktree; not live-source equivalence",
        "gitHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "fileHashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in audited_paths},
        "sourcePages": source_pages, "sourceNavigationRoomIds": source_room_ids,
        "counts": {"rooms": len(structure["rooms"]),
                   "widgets": sum(len(r["widgets"]) for r in structure["rooms"]),
                   "widgetKinds": dict(Counter(w["kind"] for r in structure["rooms"] for w in r["widgets"])),
                   "notes": len(notes), "indexedUniqueNotes": len(indexed_ids),
                   "unindexedNotes": len(set(notes) - indexed_ids),
                   "albums": len(albums), "videos": len(load("data/videos.json")),
                   "bulletins": len(bulletins)},
        "noteWidgetCounts": dict(Counter(n["widget_id"] for n in notes.values())),
        "roomHomeFlags": [{"roomId": r["room_id"], "isHome": r.get("is_home")} for r in structure["rooms"]],
        "albumOwnership": [{"albumId": a["album_id"], "storedRoomId": a.get("room_id"),
                            "sourceWidgetRoomId": owners.get(a["album_id"])} for a in albums.values()],
        "indexGroups": [{"title": g["title"], "entries": len(g["entries"])} for g in indexes],
        "renderedNotesHeadings": headings,
        "homeFeatureTargetsMissingHeading": missing_features,
        "roomPagesExist": (ROOT / "docs/rooms").exists(),
        "widgetPagesExist": (ROOT / "docs/widgets").exists(),
    }
    built_notes = ROOT / "docs/.vitepress/dist/notes/index.html"
    if built_notes.exists():
        dom = BeautifulSoup(built_notes.read_text(), "lxml")
        built_ids = {n["id"] for n in dom.select("[id]")}
        result["builtDomObservation"] = {
            "path": relative(built_notes),
            "sha256": hashlib.sha256(built_notes.read_bytes()).hexdigest(),
            "noteHeadingIds": [n.get("id") for n in dom.select(".vp-doc h2")],
            "missingHomeFeatureTargets": [f["link"] for f in features
                                          if f.get("link", "").startswith("/notes/#")
                                          and f["link"].split("#", 1)[1] not in built_ids],
            "scope": "Existing build artifact; rerun docs:build before interpreting as current",
        }
    output = Path(__file__).with_name("evidence.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": relative(output), "capturedAt": result["capturedAt"],
                      "counts": result["counts"], "missingHomeFeatureTargets": len(missing_features)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
