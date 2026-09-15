"""归档结果校验。

八项检查，全部产出可读报告：

1. **数量对账**    manifest 计数与 ``data/`` 中间产物、磁盘上的 md 文件三方比对
2. **断链检查**    扫描所有 md 中的站内链接与媒体链接，确认目标存在
3. **图片完整性**  对 ``docs/public/media`` 全量做 magic bytes 校验
                   （防止把 418 返回的 HTML 错误页当成图片存下来）
4. **图片格式**    后缀是否与真实内容一致（CDN 会拿 ``.webp`` 的 URL 发 JPEG 字节）
5. **图片重复**    按内容哈希分组，报告重复文件
6. **frontmatter** 每篇 md 必含 title / source / noteId 等字段
7. **内容抽查**    随机抽 N 篇，与缓存中的原始 HTML 做纯文本相似度比对
                   （正文对 ``#link-report``，评论对 ``#comments``——
                   评论容器在正文容器之外，两侧都得带上才谈得上比对）
8. **构建检查**    由 ``npm run docs:build`` 承担（``ignoreDeadLinks: false``）

最后写入 ``data/verify-report.md``。
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from .config import CONFIG, Config
from .emit import COMMENT_HEADING_RE
from .html2md import html_to_plain_text, markdown_to_plain_text
from .media import SUFFIX_FOR_KIND, is_valid_image, read_kind, sniff_image
from .util import atomic_write_text, human_size, now_iso, read_json

log = logging.getLogger("usagi.verify")

# Markdown 链接与图片
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# HTML 中的 src / href（相册与视频页用了裸 HTML）
HTML_ATTR_RE = re.compile(r'(?:src|href)="([^"]+)"')
# frontmatter 块（必须在原始 Markdown 上匹配，不能先转纯文本）
# 捕获组 1 为 frontmatter 正文，check_frontmatter() 依赖它
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
# VitePress 提示块（::: warning ... :::）
NOTICE_BLOCK_RE = re.compile(r"^:::[^\n]*\n.*?^:::[ \t]*$", re.DOTALL | re.MULTILINE)
# 页面底部的来源标注（归档时附加，原文没有）
FOOTER_RE = re.compile(r"^\*本页归档自.*\*[ \t]*$", re.DOTALL | re.MULTILINE)


@dataclass
class CheckResult:
    """单项检查结果。"""

    name: str
    passed: bool = True
    checked: int = 0
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_problem(self, message: str) -> None:
        self.passed = False
        if len(self.problems) < 200:
            self.problems.append(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "checked": self.checked,
            "problemCount": len(self.problems),
            "problems": self.problems[:50],
            "notes": self.notes,
        }


class Verifier:
    """归档结果校验器。"""

    def __init__(self, cfg: Config = CONFIG) -> None:
        self.cfg = cfg
        self.results: list[CheckResult] = []
        self.manifest: dict[str, Any] = read_json(cfg.manifest_path, default={}) or {}

    # ------------------------------------------------------------------ 入口

    def run(self, *, sample: int = 5) -> bool:
        self.results = [
            self.check_counts(),
            self.check_links(),
            self.check_images(),
            self.check_media_formats(),
            self.check_duplicate_images(),
            self.check_frontmatter(),
            self.check_content_sample(sample=sample),
        ]
        self.write_report()
        return all(result.passed for result in self.results)

    # -------------------------------------------------------------- 1. 对账

    def check_counts(self) -> CheckResult:
        result = CheckResult(name="数量对账")
        manifest = self.manifest
        if not manifest:
            result.add_problem("找不到 state/manifest.json，请先运行 sync")
            return result

        counts = manifest.get("counts") or {}
        result.checked = 1

        # manifest 自身计数 vs 实际条目
        actual = {
            "notes": len(manifest.get("notes") or {}),
            "albums": len(manifest.get("albums") or {}),
            "bulletins": len(manifest.get("bulletins") or {}),
            "videos": len(manifest.get("videos") or []),
        }
        for key, value in actual.items():
            declared = counts.get(key)
            if declared is not None and declared != value:
                result.add_problem(f"manifest 计数不一致：{key} 声明 {declared}，实际 {value}")

        photos = sum(len(a.get("photos") or []) for a in (manifest.get("albums") or {}).values())
        if counts.get("photos") not in (None, photos):
            result.add_problem(f"照片计数不一致：声明 {counts.get('photos')}，实际 {photos}")

        # manifest vs data/ 中间产物
        data_notes = read_json(self.cfg.data_dir / "notes.json", default={}) or {}
        if len(data_notes) != actual["notes"]:
            result.add_problem(f"data/notes.json 有 {len(data_notes)} 条，manifest 有 {actual['notes']} 条")

        # manifest vs 磁盘上的 md 文件
        md_files = {p.stem for p in self.cfg.notes_dir.glob("*.md") if p.stem != "index"}
        missing = set(actual and (manifest.get("notes") or {}).keys()) - md_files
        extra = md_files - set((manifest.get("notes") or {}).keys())
        if missing:
            result.add_problem(f"有 {len(missing)} 篇日记缺少 md 文件，例如 {sorted(missing)[:5]}")
        if extra:
            result.add_problem(f"有 {len(extra)} 个 md 文件不在 manifest 中，例如 {sorted(extra)[:5]}")

        # 评论归档情况（免登录，服务端静态渲染）
        comment_total = 0
        comment_archived = 0
        for payload in (manifest.get("notes") or {}).values():
            comment_total += int(payload.get("comment_count") or 0)
            comment_archived += len(payload.get("comments") or [])
        for payload in (manifest.get("external") or {}).values():
            comment_archived += len(payload.get("comments") or [])

        result.notes.append(
            f"日记 {actual['notes']} 篇 / 相册 {actual['albums']} 个（{photos} 张）"
            f" / 公告 {actual['bulletins']} 条 / 视频 {actual['videos']} 条"
        )
        result.notes.append(f"磁盘 md 文件 {len(md_files)} 个")
        result.notes.append(
            f"评论已归档 {comment_archived} 条"
            + (f"（原站标注共 {comment_total} 条）" if comment_total else "")
        )

        # 站外页面（需登录）
        external = manifest.get("external") or {}
        if external:
            unavailable = sum(
                1 for p in external.values()
                if (p.get("status") or {}).get("availability") != "ok"
            )
            result.notes.append(
                f"站外页面 {len(external)} 个"
                + (f"，其中 {unavailable} 个未归档" if unavailable else "")
            )
        return result

    # -------------------------------------------------------------- 2. 断链

    def _resolve_route(self, target: str) -> Path | None:
        """把站内路由映射到磁盘文件；站外链接返回 ``None``。"""
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return None
        path = target.split("#", 1)[0].split("?", 1)[0]
        if not path:
            return None

        if path.startswith("/media/"):
            return self.cfg.docs_dir / "public" / path.lstrip("/")

        candidate = path.strip("/")
        docs = self.cfg.docs_dir
        options = [
            docs / f"{candidate}.md",
            docs / candidate / "index.md",
        ]
        for option in options:
            if option.exists():
                return option
        return docs / f"{candidate}.md"

    def check_links(self) -> CheckResult:
        result = CheckResult(name="断链检查")
        docs = self.cfg.docs_dir
        if not docs.exists():
            result.add_problem("docs 目录不存在")
            return result

        for md_path in sorted(docs.rglob("*.md")):
            if ".vitepress" in md_path.parts:
                continue
            text = md_path.read_text(encoding="utf-8", errors="replace")
            targets = set(MD_LINK_RE.findall(text)) | set(MD_IMAGE_RE.findall(text))
            targets |= set(HTML_ATTR_RE.findall(text))

            for target in targets:
                resolved = self._resolve_route(target)
                if resolved is None:
                    continue
                result.checked += 1
                if not resolved.exists():
                    rel = md_path.relative_to(docs)
                    result.add_problem(f"{rel} → {target}（期望 {resolved.relative_to(docs)}）")

        return result

    # ------------------------------------------------------------ 3. 图片完整性

    def check_images(self) -> CheckResult:
        result = CheckResult(name="图片完整性")
        media_dir = self.cfg.media_dir
        if not media_dir.exists():
            result.add_problem("docs/public/media 目录不存在")
            return result

        total_bytes = 0
        for path in sorted(media_dir.rglob("*")):
            if not path.is_file():
                continue
            result.checked += 1
            size = path.stat().st_size
            total_bytes += size
            if size < 64:
                result.add_problem(f"{path.relative_to(media_dir)} 只有 {size} 字节，疑似损坏")
                continue
            if not is_valid_image(path):
                head = path.read_bytes()[:80]
                hint = "疑似 HTML 错误页" if head.lstrip().startswith(b"<") else "无法识别格式"
                result.add_problem(f"{path.relative_to(media_dir)} 不是有效图片（{hint}）")

        result.notes.append(f"合计 {result.checked} 个文件，{human_size(total_bytes)}")
        return result

    # ------------------------------------------------------------ 4. 图片格式

    def check_media_formats(self) -> CheckResult:
        """后缀是否与真实内容一致。

        豆瓣的 ``/view/photo/large/public/p{id}.webp`` 会返回 ``Content-Type: image/webp``
        而 body 是 JPEG（偶尔 PNG），照 URL 后缀命名就会落下"后缀说 webp、内容不是"的假文件。
        落盘名字由内容决定（见 :func:`scraper.media.correct_suffix`），这条检查负责
        在它失效时喊出来 —— 假后缀会让 VitePress 按后缀发错 ``Content-Type``，
        也会误导所有按后缀做的判断。
        """
        result = CheckResult(name="图片格式检测")
        media_dir = self.cfg.media_dir
        if not media_dir.exists():
            return result

        expected = {suffix: kind for kind, suffix in SUFFIX_FOR_KIND.items()}
        mismatched: list[str] = []
        for path in sorted(media_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            # 不认识的格式对应的后缀（站点素材的自定义命名）无从判断，跳过
            want = expected.get(path.suffix.lower())
            if want is None:
                continue
            result.checked += 1
            kind = read_kind(path)
            if not kind:
                # 不是图片：交给「图片完整性」报，这里不重复
                continue
            if kind != want:
                mismatched.append(f"{path.relative_to(media_dir)} 后缀为 {path.suffix}，实际是 {kind}")

        if mismatched:
            for message in mismatched[:100]:
                result.add_problem(message)
            if len(mismatched) > 100:
                result.add_problem(f"… 其余 {len(mismatched) - 100} 个后缀不符的文件见下")
            result.notes.append(f"发现 {len(mismatched)} 个后缀与真实格式不符的文件")
        else:
            result.notes.append("所有图片的后缀与内容一致")
        return result

    # ------------------------------------------------------------ 5. 图片重复

    def check_duplicate_images(self) -> CheckResult:
        result = CheckResult(name="图片重复检测")
        media_dir = self.cfg.media_dir
        if not media_dir.exists():
            return result

        by_hash: dict[str, list[Path]] = {}
        for path in sorted(media_dir.rglob("*")):
            if not path.is_file():
                continue
            digest = hashlib.md5(path.read_bytes()).hexdigest()
            by_hash.setdefault(digest, []).append(path)
            result.checked += 1

        duplicates = {h: paths for h, paths in by_hash.items() if len(paths) > 1}
        if duplicates:
            wasted = sum(
                (len(paths) - 1) * paths[0].stat().st_size for paths in duplicates.values()
            )
            result.notes.append(
                f"发现 {len(duplicates)} 组重复图片，可节省约 {human_size(wasted)}"
            )
            for paths in list(duplicates.values())[:10]:
                names = "、".join(str(p.relative_to(media_dir)) for p in paths[:4])
                result.notes.append(f"  重复：{names}")
        else:
            result.notes.append("没有重复图片")
        return result

    # --------------------------------------------------------- 6. frontmatter

    # 详情页与栏目页的字段要求不同：栏目页（首页/索引/留言板）本就没有单一来源
    DETAIL_FIELDS = ("title", "source")
    SECTION_FIELDS = ("title",)

    def _required_fields(self, rel: Path) -> tuple[str, ...]:
        """按页面类型给出必填的 frontmatter 字段。"""
        parts = rel.parts
        if not parts:
            return ()
        name = rel.name
        if name == "index.md":
            if len(parts) == 1:
                # 首页用 VitePress 的 hero.name 作为标题，没有 title 字段
                return ()
            # notes/index.md、albums/index.md 是栏目页
            return self.SECTION_FIELDS
        if parts[0] in {"notes", "albums"}:
            return self.DETAIL_FIELDS
        # about / board / broadcast / videos 等栏目页
        return self.SECTION_FIELDS

    def check_frontmatter(self) -> CheckResult:
        result = CheckResult(name="frontmatter 校验")
        docs = self.cfg.docs_dir
        if not docs.exists():
            return result

        for md_path in sorted(docs.rglob("*.md")):
            if ".vitepress" in md_path.parts:
                continue
            text = md_path.read_text(encoding="utf-8", errors="replace")
            match = FRONTMATTER_RE.match(text)
            rel = md_path.relative_to(docs)
            if not match:
                result.add_problem(f"{rel} 缺少 frontmatter")
                continue
            result.checked += 1
            try:
                front = json.loads("{" + match.group(1).replace("\n", ",").rstrip(",") + "}")
            except json.JSONDecodeError:
                # frontmatter 是 YAML，用简单逐行解析兜底
                front = {}
                for line in match.group(1).splitlines():
                    if ":" in line:
                        key, _, value = line.partition(":")
                        front[key.strip()] = value.strip()

            for field_name in self._required_fields(rel):
                if not front.get(field_name):
                    result.add_problem(f"{rel} 缺少 frontmatter 字段 `{field_name}`")

            if rel.parts and rel.parts[0] == "notes" and rel.name != "index.md":
                if not front.get("noteId"):
                    result.add_problem(f"{rel} 缺少 noteId")
        return result

    # ------------------------------------------------------------ 7. 内容抽查

    def _cached_html_for_note(self, note_id: str, widget_id: str) -> str | None:
        """从磁盘缓存里取回该日记的原始 HTML。"""
        from .http_client import cache_paths

        url = self.cfg.note_url(widget_id, note_id)
        body, meta = cache_paths(self.cfg, url)
        if not body.exists():
            return None
        from .http_client import decode_html

        content_type = ""
        if meta.exists():
            try:
                content_type = json.loads(meta.read_text(encoding="utf-8")).get("contentType", "")
            except json.JSONDecodeError:
                pass
        return decode_html(body.read_bytes(), content_type)

    @staticmethod
    def _markdown_body(path: Path) -> str:
        """取出 md 的内容部分（正文 + 评论）。

        必须在**原始 Markdown 文本**上剥离 frontmatter / 提示块 / 来源标注：
        一旦先转成纯文本，换行会被压平，frontmatter 的 ``---`` 边界就失去意义，
        正则会只吃掉开头一个 ``---``，把 ``title: ...`` 等元数据当成正文参与比对，
        从而把相似度错误地压低。
        """
        raw = path.read_text(encoding="utf-8")
        raw = FRONTMATTER_RE.sub("", raw, count=1)
        raw = NOTICE_BLOCK_RE.sub("", raw)
        raw = FOOTER_RE.sub("", raw)
        return raw

    @staticmethod
    def _markdown_parts(path: Path) -> tuple[str, str]:
        """把 md 拆成 ``(正文, 评论)`` 两段原始 Markdown。

        切在 ``## 评论（N）`` 标题行**之后**：标题是 emit 生成的脚手架，原文
        里没有对应物，两侧均不应纳入，否则每篇都会多出一段凭空插入的「评论（N）」。
        """
        raw = Verifier._markdown_body(path)
        match = COMMENT_HEADING_RE.search(raw)
        if match is None:
            return raw, ""
        return raw[: match.start()], raw[match.end() :]

    @staticmethod
    def _comment_text(comments: Iterable[Any]) -> str:
        """把评论摊成纯文本，字段顺序与兜底文案对齐 emit 的渲染。

        内容抽查要求两侧同口径：md 侧的评论由 ``emit._render_comments`` 渲染
        （作者 · 日期 + 引用块正文），这里必须复刻它的字段顺序，以及"无作者写
        匿名、无正文写（空）"两条兜底逻辑，否则每次比对都会引入额外差异。
        """
        parts: list[str] = []
        for comment in comments:
            head = " · ".join(part for part in (comment.author, comment.date) if part)
            parts.append(head or "匿名")
            parts.append(html_to_plain_text(comment.content_html) or "（空）")
        return " ".join(parts)

    def check_content_sample(self, *, sample: int = 5) -> CheckResult:
        result = CheckResult(name="内容抽查")
        notes = self.manifest.get("notes") or {}
        if not notes:
            # 没有已归档日记说明还没跑 notes 阶段；完整性由「数量对账」负责，
            # 这里只做抽样比对，无样本可抽时跳过而不是判定失败。
            result.notes.append("没有已归档的日记，跳过内容抽查（请先执行 sync 的 notes 阶段）")
            return result

        candidates = [
            (nid, payload)
            for nid, payload in notes.items()
            if payload.get("content_html") and payload.get("status", {}).get("availability") == "ok"
        ]
        if not candidates:
            result.notes.append("没有可抽查的已归档日记")
            return result

        picks = random.sample(candidates, min(sample, len(candidates)))
        for note_id, payload in picks:
            md_path = self.cfg.notes_dir / f"{note_id}.md"
            if not md_path.exists():
                result.add_problem(f"抽查 {note_id}：md 文件不存在")
                continue
            result.checked += 1

            cached = self._cached_html_for_note(note_id, str(payload.get("widget_id", "")))
            if not cached:
                result.notes.append(f"抽查 {note_id}：无原始 HTML 缓存，跳过比对")
                continue

            from bs4 import BeautifulSoup

            from .parsers import _link_report, parse_note_comments

            # 原文侧：正文对 `#link-report`，评论对 `#comments`。两个容器在页面里
            # 是兄弟节点，评论不在正文里，只能各自取出来配对
            original_html = _link_report(BeautifulSoup(cached, "lxml"), note_id)
            original_parts = (
                html_to_plain_text(original_html),
                self._comment_text(parse_note_comments(cached, self.cfg)),
            )

            # 归档侧：按同样的切分取出正文与评论
            md_body, md_comments = self._markdown_parts(md_path)
            md_parts = (
                markdown_to_plain_text(md_body),
                markdown_to_plain_text(md_comments),
            )

            if not any(original_parts):
                result.notes.append(f"抽查 {note_id}：原文为空，跳过")
                continue

            # 正文与评论**各自算比值**，取较差的一段判定。合成一整段再比会把
            # 局部丢失稀释掉：评论偏少的长文里，整段评论全丢也只掉到 0.93，
            # 够不着阈值，等于没查。
            ratios = [
                (label, SequenceMatcher(None, original, archived).ratio())
                for label, original, archived in zip(("正文", "评论"), original_parts, md_parts)
                if original or archived
            ]
            worst = min(ratio for _, ratio in ratios)
            detail = " / ".join(f"{label} {ratio:.3f}" for label, ratio in ratios)
            title = str(payload.get("title", ""))[:30]
            if worst < 0.9:
                result.add_problem(f"抽查 {note_id}（{title}）相似度仅 {worst:.3f}（{detail}）")
            else:
                result.notes.append(f"抽查 {note_id}（{title}）相似度 {worst:.3f} ✓")

        return result

    # ------------------------------------------------------------------ 报告

    def report_text(self) -> str:
        lines = [
            "",
            "=" * 68,
            "归档校验报告",
            "=" * 68,
        ]
        for result in self.results:
            mark = "✓ 通过" if result.passed else "✗ 未通过"
            lines.append(f"[{mark}] {result.name}（检查 {result.checked} 项）")
            for note in result.notes:
                lines.append(f"        · {note}")
            for problem in result.problems[:20]:
                lines.append(f"        ✗ {problem}")
            if len(result.problems) > 20:
                lines.append(f"        … 其余 {len(result.problems) - 20} 条问题见 data/verify-report.md")
        lines.append("=" * 68)
        passed = sum(1 for r in self.results if r.passed)
        lines.append(f"结果：{passed}/{len(self.results)} 项通过")
        lines.append("")
        lines.append("提示：VitePress 构建（npm run docs:build）在 ignoreDeadLinks=false 下")
        lines.append("      会独立复查一遍死链，是最后一道防线。")
        return "\n".join(lines)

    def write_report(self) -> Path:
        lines = [
            "# 归档校验报告",
            "",
            f"生成时间：{now_iso()}",
            "",
            f"| 检查项 | 结果 | 检查数 | 问题数 |",
            "| --- | --- | ---: | ---: |",
        ]
        for result in self.results:
            lines.append(
                f"| {result.name} | {'通过' if result.passed else '**未通过**'} "
                f"| {result.checked} | {len(result.problems)} |"
            )
        for result in self.results:
            lines += ["", f"## {result.name}", ""]
            if result.notes:
                for note in result.notes:
                    lines.append(f"- {note}")
            if result.problems:
                lines.append("")
                lines.append(f"发现 {len(result.problems)} 个问题：")
                lines.append("")
                for problem in result.problems[:100]:
                    lines.append(f"- {problem}")
                if len(result.problems) > 100:
                    lines.append(f"- … 其余 {len(result.problems) - 100} 条略")
            elif result.passed:
                lines.append("")
                lines.append("没有发现问题。")

        path = self.cfg.data_dir / "verify-report.md"
        atomic_write_text(path, "\n".join(lines) + "\n")
        return path
