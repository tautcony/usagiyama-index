"""命令行入口：把各模块编排成一条可重复运行、可断点续接的流水线。

子命令
------

``sync``    抓取 + 生成站点（增量；已完成的单元自动跳过）
``emit``    仅根据已有数据重新生成产物（离线，零网络请求）
``discover`` 只枚举站点结构，不抓详情（用于 ``--dry-run`` 预估规模）
``report``  输出进度报告
``verify``  校验归档结果
``test``    跑 HTML→Markdown 转换的回归测试

断点续接
--------

任何阶段被中断（Ctrl-C / 断网 / 熔断）后，直接重新执行同样的命令即可：
已完成单元由 ``state/progress.json`` 跳过，已抓内容由 ``state/cache/`` 命中，
已下载图片按文件存在性 + magic bytes 校验跳过。
"""

from __future__ import annotations

import argparse
import logging
import re
import signal
import sys
from collections.abc import Callable, Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from . import auth
from .archive import WaybackClient
from .browser import BrowserFetcher, detect_chrome_ua
from .config import (
    CONFIG,
    DEFAULT_SPEED,
    ROBOTS_CRAWL_DELAY,
    SPEED_TIERS,
    Config,
    describe_delay,
    ensure_dirs,
    speed_tier,
)
from .discover import SiteDiscovery, SiteStructure, enumerate_album_photos
from .emit import EmitContext, SiteEmitter
from .http_client import CircuitBreakerOpen, Fetcher, estimate_duration
from .transport import Transport
from .index_map import (
    FALLBACK_CATEGORY,
    build_note_to_group,
    group_by_category,
    parse_index,
)
from .media import MediaArchive, album_image_variants, album_original_variants
from .models import (
    Album,
    Availability,
    Bulletin,
    Comment,
    Discussion,
    ExternalPage,
    MiniblogStatus,
    Note,
    PhotoMeta,
    SourceStatus,
    Video,
)
from .parsers import (
    parse_album_title,
        parse_external_page,
        parse_note_comment_pages,
        parse_page_step,
        parse_note_comments,
    parse_bulletin,
    parse_discussion,
    parse_miniblog,
    parse_note,
    parse_photo_detail,
)
from .progress import ItemStatus, ProgressStore, StageResult, StageRunner
from .resolver import PageResolver, UnavailableRecord
from .util import human_duration, human_size, now_iso, read_json, truncate, write_json

log = logging.getLogger("usagi")

# 索引公告的标题关键字（用于识别索引①/②）
INDEX_BULLETIN_KEYWORDS = ("索引",)

# 全部阶段（按依赖顺序）
ALL_STAGES = (
    "rooms",
    "bulletins",
    "notes",
    "photos",
    "albums",
    "videos",
    "forum",
    "miniblog",
    # 站外页面（www.douban.com 的 /topic/、/note/）需要登录才能访问，
    # 因此单独成一个阶段，便于登录后配合 --recheck-unavailable 单独补抓。
    "main",
)

#: 站外页面的域名（索引①/② 里指向这些域名的条目需要登录）
EXTERNAL_HOSTS = ("www.douban.com", "douban.com")

ROBOTS_NOTICE = """
⚠️  抓取前请确认你已阅读目标站点的 robots.txt：

    https://site.douban.com/robots.txt  →  User-agent: * / Disallow: /
    https://www.douban.com/robots.txt   →  部分禁止，并注明 Crawl-delay: 5

本工具以「单线程 + 请求间隔 {interval} + 指数退避 + 熔断」的方式运行。
{tier_note}
请仅将归档结果用于个人保存与阅读。确认理解后，加上 --i-have-read-robots 重新运行。
"""


def robots_notice(cfg: Config) -> str:
    """填好当前限速档位的 robots 提示文本。"""
    warning = crawl_delay_warning(cfg)
    return ROBOTS_NOTICE.format(
        interval=describe_delay(cfg.delay_min, cfg.delay_max),
        impersonate=cfg.impersonate,
        tier_note=f"\n⚠️  {warning}\n" if warning else "",
    )


def crawl_delay_warning(cfg: Config) -> str:
    """比 ``robots.txt`` 的 ``Crawl-delay`` 更快的档位要明确说一句，否则返回空串。

    默认档正好卡在 ``Crawl-delay: 5`` 上，是该守的线；另外两档是使用者**主动**
    选择"更快"，工具照办，但不该让这件事无声发生：提示里点一次，抓取开始时
    再记一条 WARNING，剩下的交给使用者自己判断。
    """
    if cfg.delay_min >= ROBOTS_CRAWL_DELAY:
        return ""
    return (
        f"当前档位 {describe_delay(cfg.delay_min, cfg.delay_max)}快于 "
        f"www.douban.com/robots.txt 的 Crawl-delay: {ROBOTS_CRAWL_DELAY:g}，"
        "对源站的压力高于默认档位，请自行确认可以接受。"
    )


# ------------------------------------------------------------------ 日志


def setup_logging(verbose: bool, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)-14s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # 第三方库日志降噪。
    # playwright 的 DEBUG 日志可能带请求头（含 cookie），必须压到 WARNING。
    for name in ("curl_cffi", "urllib3", "chardet", "playwright"):
        logging.getLogger(name).setLevel(logging.WARNING)


# ------------------------------------------------------------------ 参数

#: ``--speed`` 的帮助文本，由档位表生成 —— 改表就不用改文案，也就不会对不上。
_SPEED_HELP = "请求间隔档位：" + "、".join(
    f"{name}={lo:g}~{hi:g}s" + ("（默认）" if name == DEFAULT_SPEED else "")
    for name, (lo, hi) in SPEED_TIERS.items()
)


def add_common_args(
    parser: argparse.ArgumentParser, *, suppress_defaults: bool = False
) -> None:
    """注册全局参数。

    同时挂到主解析器与各子命令上（见 ``_common_parent``），
    这样 ``--limit 3`` 无论放在子命令前还是后都能识别 —— 用户自然会两种写法都试。

    :param suppress_defaults: 挂到**子命令**时必须为 ``True``。
        argparse 的子解析器会在解析完子命令后用自己的默认值覆盖同名属性，
        于是 ``--archive sync``（参数写在子命令前）会被子命令的默认值重置，
        表现为"参数不生效"。用 ``argparse.SUPPRESS`` 让子命令副本在未显式
        传参时不写入属性，主解析器已解析的值就能保留下来。
        读取端统一用 ``getattr(args, name, fallback)`` 兜底。
    """
    d_true = argparse.SUPPRESS if suppress_defaults else False
    d_none = argparse.SUPPRESS if suppress_defaults else None
    d_zero = argparse.SUPPRESS if suppress_defaults else 0

    parser.add_argument("-v", "--verbose", action="store_true", default=d_true, help="输出调试日志")
    parser.add_argument("-q", "--quiet", action="store_true", default=d_true, help="只输出警告与错误")
    parser.add_argument(
        "--impersonate",
        default=d_none,
        help=f"curl_cffi 浏览器指纹（默认 {CONFIG.impersonate}，可换 chrome136 / safari18_0 等）",
    )
    parser.add_argument(
        "--offline", action="store_true", default=d_true, help="只读本地缓存，绝不联网"
    )
    # 用 BooleanOptionalAction 自动生成 --archive / --no-archive 两个选项。
    # （不要手写 "--no-archive"：Python 3.13 的 argparse 会把它重写成 "--archive"，
    #   导致传参时报 "unrecognized arguments"。）
    # default=False：Internet Archive 补足是**可选项，默认关闭**。
    # 开启后仅对抓取失败的页面额外查询 archive.org，单次可能耗时 10~60s。
    parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS if suppress_defaults else False,
        help="启用 Internet Archive 补足（默认关闭；用 --no-archive 显式关闭）",
    )
    # 浏览器传输开关。默认启用（见 Config.browser_enabled）；
    # --no-browser 可退回纯 HTTP（快、轻，但拿不到需登录的内容）。
    parser.add_argument(
        "--browser",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS if suppress_defaults else True,
        help="用无头浏览器抓取页面（默认启用；用 --no-browser 退回纯 HTTP）",
    )
    # 限速二选一：--speed 是档位预设，--delay 是精确覆盖。
    # 两者同时给出时该听谁的，不该让使用者去猜，于是交给 argparse 直接报错。
    # （参数分别写在子命令两侧时 argparse 拦不住 —— 主解析器与子解析器各管一段 ——
    #   那种写法下由 _config_from_args 里更具体的 --delay 优先。）
    rate = parser.add_mutually_exclusive_group()
    rate.add_argument("--speed", choices=list(SPEED_TIERS), default=d_none, help=_SPEED_HELP)
    rate.add_argument(
        "--delay",
        type=float,
        default=d_none,
        help=(
            "请求间隔下限（秒），上限为下限 +2；精确覆盖档位，"
            f"默认 {SPEED_TIERS[DEFAULT_SPEED][0]:g}"
        ),
    )
    parser.add_argument(
        "--limit", type=int, default=d_zero, help="每阶段最多处理 N 项（冒烟测试用）"
    )


def _common_parent() -> argparse.ArgumentParser:
    """构造只含全局参数、供子命令继承的父解析器。

    用 ``suppress_defaults=True``：子命令未显式传参时不覆盖主解析器的值。
    """
    parent = argparse.ArgumentParser(add_help=False)
    add_common_args(parent, suppress_defaults=True)
    return parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scraper.cli",
        description="「兔子山的小站」内容归档工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python -m scraper.cli sync --dry-run\n"
            "  python -m scraper.cli sync --i-have-read-robots\n"
            "  python -m scraper.cli sync --limit 3 --delay 0.5     # 冒烟测试\n"
            "  python -m scraper.cli sync --speed normal            # 换成 2~3 秒档\n"
            "  python -m scraper.cli emit                           # 离线重新生成\n"
            "  python -m scraper.cli verify\n"
        ),
    )
    add_common_args(parser)

    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="抓取并生成站点（增量）", parents=[_common_parent()])
    p_sync.add_argument("--dry-run", action="store_true", help="只预估规模与耗时，不抓取")
    p_sync.add_argument("--force", action="store_true", help="忽略进度，强制重抓")
    p_sync.add_argument(
        "--recheck-unavailable",
        action="store_true",
        help="重新探测此前标记为不可访问的页面",
    )
    p_sync.add_argument(
        "--stages",
        default=",".join(ALL_STAGES),
        help=f"要执行的阶段，逗号分隔。可选：{','.join(ALL_STAGES)}",
    )
    p_sync.add_argument("--no-emit", action="store_true", help="只抓取，不生成站点产物")
    p_sync.add_argument(
        "--i-have-read-robots",
        action="store_true",
        help="确认已阅读目标站点 robots.txt 并理解抓取策略",
    )
    p_sync.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="显示进度条（用 --no-progress 关闭）",
    )

    sub.add_parser("emit", help="仅根据已有数据重新生成产物（离线）", parents=[_common_parent()])
    sub.add_parser("discover", help="只枚举站点结构", parents=[_common_parent()])
    sub.add_parser("report", help="输出进度报告", parents=[_common_parent()])

    p_verify = sub.add_parser("verify", help="校验归档结果", parents=[_common_parent()])
    p_verify.add_argument("--sample", type=int, default=5, help="内容抽查篇数")

    p_login = sub.add_parser(
        "login",
        help="打开浏览器完成豆瓣登录并保存会话（工具不接触密码）",
        parents=[_common_parent()],
    )
    p_login.add_argument(
        "--check",
        action="store_true",
        help="只校验已保存的会话是否有效，不打开浏览器",
    )
    p_login.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=f"等待登录的超时秒数（默认 {CONFIG.browser_login_timeout:.0f}）",
    )

    sub.add_parser("test", help="跑 HTML→Markdown 转换回归测试", parents=[_common_parent()])

    return parser


def resolve_stages(raw: str) -> list[str]:
    stages = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [s for s in stages if s not in ALL_STAGES]
    if unknown:
        raise SystemExit(f"未知阶段：{', '.join(unknown)}。可选：{', '.join(ALL_STAGES)}")
    return stages


# ------------------------------------------------------------------ 上下文


class SyncContext:
    """一次同步运行的全部依赖与累积结果。"""

    def __init__(
        self,
        cfg: Config,
        *,
        use_archive: bool = True,
        transport: Transport | None = None,
    ) -> None:
        self.cfg = cfg
        # 传输方式：默认按配置选（浏览器 / 纯 HTTP），也允许外部注入（测试用）
        if transport is not None:
            self.fetcher: Transport = transport
        elif cfg.browser_enabled:
            self.fetcher = BrowserFetcher(cfg)
        else:
            self.fetcher = Fetcher(cfg)
        # 默认不构造 WaybackClient，避免任何 archive.org 请求
        self.wayback = WaybackClient(cfg) if use_archive else None
        self.resolver = PageResolver(self.fetcher, self.wayback, cfg)
        self.media = MediaArchive(self.fetcher, self.wayback, cfg)
        # 离线模式下进度只读：缓存未命中只是"本地还没这份数据"，
        # 若照常落盘会把整站误标为"原站不可访问"。见 ProgressStore 的说明。
        self.progress = ProgressStore(cfg=cfg, readonly=cfg.offline)
        self.emitter = SiteEmitter(cfg, EmitContext())
        self.discovery = SiteDiscovery(self.resolver, cfg)
        self.structure = SiteStructure()
        self.notes: dict[str, Note] = {}
        # 照片详情在 stage_photos 抓过一次，stage_albums 直接复用，避免重复请求
        self.photo_meta: dict[tuple[str, str], Any] = {}
        self.albums: dict[str, Album] = {}
        self.bulletins: dict[str, Bulletin] = {}
        self.videos: list[Video] = []
        self.discussions: list[Discussion] = []
        self.miniblog: list[MiniblogStatus] = []
        # 站外页面（需登录），key 为 page_id
        self.external: dict[str, ExternalPage] = {}
        self.index_groups: list[Any] = []
        self.results: list[StageResult] = []
        self.unavailable: list[UnavailableRecord] = []
        self._prev_manifest: dict[str, Any] = read_json(cfg.manifest_path, default={}) or {}

    # ------------------------------------------------------------------ 收尾

    def close(self) -> None:
        self.fetcher.close()
        if self.wayback is not None:
            self.wayback.close()

    def __enter__(self) -> "SyncContext":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------------------------------------------------------------- 数据

    def load_existing(self) -> None:
        """从上次的中间产物恢复全部状态。

        断点续接的关键一环：某个阶段被跳过（已完成）或本次没运行时，
        它此前产出的数据必须能从 ``data/`` 恢复，否则会出现
        「索引分组为空 → sidebar 全空」「只跑 notes 阶段时结构丢失」这类问题。
        """
        def payload_of(value: Any, default: Any) -> Any:
            if isinstance(value, dict) and "_meta" in value:
                return value.get("items", default) if "items" in value else {
                    k: v for k, v in value.items() if k != "_meta"
                }
            return value

        notes = payload_of(read_json(self.cfg.data_dir / "notes.json", default={}), {}) or {}
        for note_id, payload in notes.items():
            self.notes[note_id] = _note_from_dict(note_id, payload)

        albums = payload_of(read_json(self.cfg.data_dir / "albums.json", default={}), {}) or {}
        for album_id, payload in albums.items():
            self.albums[album_id] = _album_from_dict(album_id, payload)

        bulletins = payload_of(read_json(self.cfg.data_dir / "bulletins.json", default={}), {}) or {}
        for bid, payload in bulletins.items():
            self.bulletins[bid] = _bulletin_from_dict(bid, payload)

        for payload in payload_of(read_json(self.cfg.data_dir / "videos.json", default=[]), []) or []:
            self.videos.append(_video_from_dict(payload))

        for payload in payload_of(read_json(self.cfg.data_dir / "forum.json", default=[]), []) or []:
            self.discussions.append(_discussion_from_dict(payload))

        for payload in payload_of(read_json(self.cfg.data_dir / "miniblog.json", default=[]), []) or []:
            self.miniblog.append(MiniblogStatus(**payload))

        external = payload_of(read_json(self.cfg.data_dir / "external.json", default={}), {}) or {}
        for page_id, payload in external.items():
            self.external[page_id] = _external_from_dict(page_id, payload)

        index_payload = read_json(self.cfg.data_dir / "index.json", default=None)
        index_payload = payload_of(index_payload, [])
        if index_payload:
            from .models import IndexEntry, IndexGroup

            for group in index_payload:
                entries = [
                    IndexEntry(
                        title=e.get("title", ""),
                        url=e.get("url", ""),
                        note_id=e.get("noteId"),
                        status=Availability(e.get("status", "not_fetched")),
                    )
                    for e in group.get("entries", [])
                ]
                self.index_groups.append(
                    IndexGroup(
                        title=group.get("title", ""),
                        doulist_url=group.get("doulistUrl"),
                        entries=entries,
                    )
                )

        structure = payload_of(read_json(self.cfg.data_dir / "structure.json", default=None), None)
        if structure:
            self._restore_structure(structure)

        log.info(
            "已从本地产物恢复：%d 篇日记、%d 个相册、%d 个公告、%d 条视频、"
            "%d 条日记摘要、%d 张照片",
            len(self.notes),
            len(self.albums),
            len(self.bulletins),
            len(self.videos),
            len(self.structure.note_entries),
            self.structure.photo_count,
        )

    def _restore_structure(self, payload: dict[str, Any]) -> None:
        """从 ``data/structure.json`` 恢复站点结构（离线模式下使用）。

        ``build_manifest`` 会把结构原样写回 ``structure.json``，所以这里
        必须把 ``to_dict`` 产出的字段全部还原：漏还原哪个字段，跑一次
        ``emit`` 就会把它从磁盘上抹掉。
        """
        from .models import Room, Widget

        self.structure.meta = payload.get("meta") or {}

        for room_payload in payload.get("rooms") or []:
            room = Room(
                room_id=str(room_payload.get("room_id", "")),
                title=room_payload.get("title", ""),
                url=room_payload.get("url", ""),
                is_home=bool(room_payload.get("is_home")),
            )
            room.status = _status_from_dict(room_payload.get("status"))
            for widget_payload in room_payload.get("widgets") or []:
                room.widgets.append(
                    Widget(
                        kind=widget_payload.get("kind", ""),
                        widget_id=str(widget_payload.get("widget_id", "")),
                        room_id=room.room_id,
                        title=widget_payload.get("title", ""),
                    )
                )
            self.structure.rooms.append(room)

        self.structure.bulletins = [
            _bulletin_from_dict(str(item.get("bulletin_id", "")), item)
            for item in payload.get("bulletins") or []
        ]
        self.structure.videos = [
            _video_from_dict(item) for item in payload.get("videos") or []
        ]

        from .parsers import NoteListEntry

        for entry in payload.get("noteEntries") or []:
            self.structure.note_entries.append(
                NoteListEntry(
                    note_id=str(entry.get("noteId", "")),
                    widget_id=str(entry.get("widgetId", "")),
                    title=entry.get("title", ""),
                    date=entry.get("date", ""),
                    comment_count=int(entry.get("commentCount", 0) or 0),
                    url=entry.get("url", ""),
                )
            )

        self.structure.photo_ids = {
            str(k): [str(x) for x in v] for k, v in (payload.get("photoIds") or {}).items()
        }
        self.structure.album_titles = {
            str(k): str(v) for k, v in (payload.get("albumTitles") or {}).items()
        }
        self.structure.forum_topics = {
            str(k): [(str(a), str(b)) for a, b in v]
            for k, v in (payload.get("forumTopics") or {}).items()
        }

    # ------------------------------------------------------------ 渲染前准备

    def refresh_album_media(self) -> None:
        """以磁盘为准，刷新每个相册照片的本地路径（预览图与原图各一份）。

        ``local`` / ``local_original`` 记录的是"图片在不在本地"这一磁盘事实，
        会随下载与清理而变。图片完全可能在上一次相册阶段之后才落盘
        （例如本次只跑了 ``photos`` 阶段），而 ``load_existing`` 发生在所有
        抓取阶段之前，读到的必然是运行前的旧值。因此统一挪到渲染前重推一次：
        否则已归档的相册会被整页报成"未能归档"。
        """
        for album in self.albums.values():
            for photo in album.photos:
                preview = self.media.find_album_image(album.album_id, photo.photo_id)
                original = self.media.find_album_original(album.album_id, photo.photo_id)
                photo.local_original = original[1] if original is not None else ""
                # 只有原图时拿它当显示图，与 stage_photos 的处理保持一致
                found = preview or original
                photo.local = found[1] if found is not None else ""

    def refresh_unavailable(self) -> None:
        """汇总「当前仍不可得」的条目，供 ``data/unavailable.md`` 与清单文件使用。

        清单必须跨运行累积、且以进度库为准，因为**绝大多数失败条目本次根本
        不会被重新抓取**：它们在进度里已是终态，``StageRunner`` 直接跳过；
        ``emit`` 只读本地产物，不发起任何请求。此前直接复用 resolver 本次
        的失败列表当全量清单，于是每次重新生成都把清单清空成
        「全部内容均已成功归档」，而进度里明明还躺着十几条抓不到的条目。

        合并规则：

        * 磁盘上的历史记录保留，除非本次运行已成功取回该地址
          （``PageResolver.resolved_ok``）或本次产生了同一地址的新记录；
        * 进度里仍标记为不可得的条目，若没有对应的明细记录就按进度补一条
          ——进度是"还缺什么"的唯一事实源，补这一笔清单才不会漏项。
        """
        prior = [
            _unavailable_from_dict(item)
            for item in read_json(self.cfg.data_dir / "unavailable.json", default=[]) or []
        ]
        fresh = list(self.resolver.unavailable)
        recovered = self.resolver.resolved_ok
        superseded = {record.url for record in fresh}

        records = [
            record
            for record in prior
            if record.url not in recovered and record.url not in superseded
        ]
        records.extend(fresh)

        known = {record.url for record in records}
        for item in self.progress.unavailable():
            # 还原不出地址时退回显示内部键，总好过整条丢掉
            url = self._page_url_of(item) or item.key
            if url in known:
                continue
            known.add(url)
            records.append(
                UnavailableRecord(
                    url=url,
                    availability=Availability.UNAVAILABLE,
                    detail=item.detail,
                    context=_STAGE_LABELS.get(item.stage, item.stage),
                )
            )

        self.unavailable = records
        log.info("不可访问条目：%d 条", len(records))

    def _page_url_of(self, item: Any) -> str:
        """还原一条进度记录对应的页面地址（仅用于清单展示）。

        新写入的进度条目自带 ``meta["url"]``；这个改动之前的老条目只有
        内部键（``note:314598362``、``photo:13431950:2321232981``……），
        这里按各阶段的键格式尽力还原。
        """
        url = str((item.meta or {}).get("url", ""))
        if url:
            return url

        cfg = self.cfg
        kind, _, rest = str(item.key).partition(":")
        if kind == "photo":
            album_id, _, photo_id = rest.partition(":")
            if album_id and photo_id:
                return cfg.photo_url(album_id, photo_id)
        elif kind == "note":
            entry = self.structure.entry_by_note_id().get(rest)
            if entry is not None and entry.url:
                return entry.url
        elif kind == "room":
            for room in self.structure.rooms:
                if room.room_id == rest:
                    return room.url
        elif kind == "bulletin":
            for widget in self.structure.widgets_of("bulletin"):
                if widget.widget_id == rest:
                    return f"{cfg.base_url}/room/{widget.room_id}/"
        elif kind == "discussion":
            for widget_id, topics in self.structure.forum_topics.items():
                if any(topic[0] == rest for topic in topics):
                    return cfg.discussion_url(widget_id, rest)
        elif kind == "miniblog":
            return cfg.miniblog_url(rest)
        elif kind == "main":
            page = self.external.get(rest)
            if page is not None:
                return page.url
        return ""

    # -------------------------------------------------------------- 索引分组

    def build_index_groups(self) -> list[Any]:
        """从已归档的公告栏内容重建索引①/② 的分类结构。

        刻意放在"生成"而非"抓取"阶段：抓取阶段可能因断点续接而整体跳过，
        但索引结构任何时候都必须能从已归档内容里重建出来。
        按分组标题去重，避免同一分组在 sidebar 里出现两次。
        """
        self.index_groups = []
        seen: set[str] = set()
        for bulletin in self.bulletins.values():
            if not any(kw in bulletin.title for kw in INDEX_BULLETIN_KEYWORDS):
                continue
            for group in parse_index(bulletin.content_html, self.cfg):
                if group.title in seen:
                    log.debug("跳过分组重复：%s", group.title)
                    continue
                seen.add(group.title)
                self.index_groups.append(group)
        log.info(
            "索引分组：%d 个（%d 条目）",
            len(self.index_groups),
            sum(len(g.entries) for g in self.index_groups),
        )
        return self.index_groups

    def persist_products(self) -> None:
        """把本次抓到的内容落盘（不渲染站点时也要做）。

        ``--no-emit`` 只是"不生成站点产物"，抓到的内容仍然必须保存：
        解析结果一旦不落盘、进度却已记为 done，下次运行就会跳过这些条目，
        数据再没有第二次机会进 ``data/``。索引分组同理——它由 ``save_data``
        写进 ``data/index.json``，所以必须先重建，否则会把索引写空，
        sidebar 跟着空掉。
        """
        self.build_index_groups()
        self.save_data()

    # ---------------------------------------------------------------- 路由

    def rebuild_context(self) -> None:
        """重建链接重写所需的映射表。"""
        self.emitter.ctx.route_map = {nid: f"/notes/{nid}" for nid in self.notes}
        self.emitter.ctx.external_routes = {
            page.url: page.route for page in self.external.values()
        }
        for page in self.external.values():
            self.emitter.ctx.external_routes.setdefault(page.url.rstrip("/"), page.route)
        self.emitter.ctx.album_routes = {aid: f"/albums/{aid}" for aid in self.albums}

    def save_data(self) -> None:
        """把中间产物写入 ``data/``（供 ``emit`` 与人工查看）。"""
        cfg = self.cfg
        updated_at = now_iso()

        def stamped(value: Any) -> Any:
            if isinstance(value, dict):
                return {"_meta": {"updatedAt": updated_at}, **value}
            return value

        write_json(
            cfg.data_dir / "notes.json",
            stamped({nid: n.to_dict() for nid, n in sorted(self.notes.items())}),
        )
        write_json(
            cfg.data_dir / "albums.json",
            stamped({aid: a.to_dict() for aid, a in sorted(self.albums.items())}),
        )
        write_json(
            cfg.data_dir / "bulletins.json",
            stamped({bid: b.to_dict() for bid, b in sorted(self.bulletins.items())}),
        )
        write_json(cfg.data_dir / "videos.json", stamped([v.to_dict() for v in self.videos]))
        write_json(cfg.data_dir / "forum.json", stamped([d.to_dict() for d in self.discussions]))
        write_json(cfg.data_dir / "miniblog.json", stamped([m.to_dict() for m in self.miniblog]))
        write_json(
            cfg.data_dir / "external.json",
            stamped({pid: p.to_dict() for pid, p in sorted(self.external.items())}),
        )
        write_json(
            cfg.data_dir / "index.json",
            stamped([g.to_dict() for g in self.index_groups]),
        )
        write_json(cfg.data_dir / "structure.json", stamped(self.structure.to_dict()))
        write_json(
            cfg.data_dir / "unavailable.json",
            [asdict(record) for record in self.unavailable],
        )
        write_json(
            cfg.data_dir / "updated-at.json",
            {"updatedAt": updated_at, "source": "sync"},
        )

    def build_manifest(self) -> dict[str, Any]:
        """内容级单一事实源。"""
        return {
            "site": self.cfg.site_url,
            "siteName": self.cfg.site_name,
            "generatedAt": now_iso(),
            "siteMeta": self.structure.meta,
            "counts": {
                "notes": len(self.notes),
                "albums": len(self.albums),
                "photos": sum(len(a.photos) for a in self.albums.values()),
                "videos": len(self.videos),
                "bulletins": len(self.bulletins),
                "discussions": len(self.discussions),
                "miniblog": len(self.miniblog),
                "external": len(self.external),
                "comments": sum(len(n.comments) for n in self.notes.values())
                + sum(len(p.comments) for p in self.external.values()),
                "unavailable": len(self.unavailable),
            },
            "rooms": [r.to_dict() for r in self.structure.rooms],
            "bulletins": {bid: b.to_dict() for bid, b in sorted(self.bulletins.items())},
            "index": [g.to_dict() for g in self.index_groups],
            "notes": {nid: n.to_dict() for nid, n in sorted(self.notes.items())},
            "albums": {aid: a.to_dict() for aid, a in sorted(self.albums.items())},
            "videos": [v.to_dict() for v in self.videos],
            "external": {pid: p.to_dict() for pid, p in sorted(self.external.items())},
        }


# ------------------------------------------------------------ 反序列化辅助


def merge_by(
    target: list[Any],
    incoming: Iterable[Any],
    key: Callable[[Any], str],
) -> None:
    """按 ID 把 ``incoming`` 合并进 ``target``，同 ID 覆盖而非追加。

    完全幂等：不仅防止新增重复，还会**修复 target 里已有的重复**。
    这一点是必需的 —— 早期版本产生的 ``data/*.json`` 里可能已经存了
    重复条目（实测广播动态被存成 40 条，唯一 ID 只有 20 个），
    如果只防新增，重复会一直留在产物里。

    顺序按首次出现的位置保留，值取最后一次写入的。
    """
    merged: dict[str, Any] = {}
    for item in target:
        merged[key(item)] = item
    for item in incoming:
        merged[key(item)] = item
    target[:] = list(merged.values())


def _status_from_dict(payload: Any) -> SourceStatus:
    if not isinstance(payload, dict):
        return SourceStatus()
    return SourceStatus(
        availability=Availability(payload.get("availability", "not_fetched")),
        http_status=payload.get("httpStatus"),
        detail=payload.get("detail", ""),
        retryable=bool(payload.get("retryable", False)),
        wayback_url=payload.get("waybackUrl"),
        wayback_timestamp=payload.get("waybackTimestamp"),
    )


#: 源站抖动（小站 widget 的间歇性 404）最多按"失败待重试"记几次。
#: 抖动会自愈，但不会永远抖下去 —— 试够次数还拿不到，就该进不可访问清单
#: 交由人工确认，而非无限重试以致清单被持续掩盖。
RETRYABLE_MAX_ATTEMPTS = 3


def record_source_failure(
    progress: ProgressStore,
    key: str,
    status: SourceStatus,
    *,
    stage: str,
    url: str = "",
    detail: str = "",
) -> None:
    """把"这次没拿到内容"记进进度，按状态决定是"待重试"还是"不可得"。

    :attr:`SourceStatus.retryable` 为真表示源站这次的拒绝**不可信**
    （小站 widget 的间歇性 404 / ``src="None"``，见
    :func:`scraper.http_client.is_untrusted_missing`）：记 ``FAILED``，
    下次同步自动重试（``ProgressStore.pending`` 默认重试失败项），
    重试满 :data:`RETRYABLE_MAX_ATTEMPTS` 次仍未成功才转为 ``UNAVAILABLE``。
    """
    text = detail or status.detail or status.label
    record = progress.get(key)
    attempts = record.attempts if record is not None else 0
    if status.retryable and attempts < RETRYABLE_MAX_ATTEMPTS:
        progress.mark_failed(key, text, stage=stage)
        return
    progress.mark_unavailable(key, text, stage=stage, url=url)


#: 进度阶段 → 不可访问清单「上下文」列的中文名
_STAGE_LABELS = {
    "rooms": "房间",
    "bulletins": "公告栏",
    "notes": "日记",
    "photos": "照片",
    "albums": "相册",
    "videos": "视频",
    "forum": "讨论帖",
    "miniblog": "广播室",
    "main": "站外页面",
}


def _unavailable_from_dict(payload: Any) -> UnavailableRecord:
    """还原 ``data/unavailable.json`` 里的一条记录。"""
    if not isinstance(payload, dict):
        return UnavailableRecord(url="", availability=Availability.UNAVAILABLE)
    return UnavailableRecord(
        url=str(payload.get("url", "")),
        availability=Availability(payload.get("availability", str(Availability.UNAVAILABLE))),
        http_status=payload.get("http_status"),
        detail=str(payload.get("detail", "")),
        wayback_url=payload.get("wayback_url"),
        wayback_timestamp=payload.get("wayback_timestamp"),
        context=str(payload.get("context", "")),
    )


def _comments_from_dict(payload: dict[str, Any]) -> list[Comment]:
    """把 ``comments`` 字段还原为 :class:`Comment` 列表。

    断点续接要求"没跑的阶段能从上一次产物里恢复"，评论也是产物的一部分：
    漏还原就会在"日记已 done、本次被跳过"时静默丢掉全部评论。
    """
    return [
        Comment(
            author=item.get("author", ""),
            date=item.get("date", ""),
            content_html=item.get("content_html", ""),
            avatar_url=item.get("avatar_url", ""),
            comment_id=str(item.get("comment_id", "")),
        )
        for item in payload.get("comments") or []
    ]


def _note_from_dict(note_id: str, payload: dict[str, Any]) -> Note:
    from .models import ImageRef

    note = Note(
        note_id=note_id,
        widget_id=str(payload.get("widget_id", "")),
        title=payload.get("title", ""),
        date=payload.get("date", ""),
        content_html=payload.get("content_html", ""),
        comment_count=int(payload.get("comment_count", 0) or 0),
        source_url=payload.get("source_url", ""),
        also_in=list(payload.get("also_in") or []),
        category=payload.get("category", ""),
        index_order=int(payload.get("index_order", 0) or 0),
        content_hash=payload.get("content_hash", ""),
    )
    note.status = _status_from_dict(payload.get("status"))
    for img in payload.get("images") or []:
        note.images.append(ImageRef(**img))
    note.comments = _comments_from_dict(payload)
    return note


def _album_from_dict(album_id: str, payload: dict[str, Any]) -> Album:
    from .models import PhotoMeta

    album = Album(
        album_id=album_id,
        title=payload.get("title", ""),
        room_id=str(payload.get("room_id", "")),
        source_url=payload.get("source_url", ""),
    )
    album.status = _status_from_dict(payload.get("status"))
    for item in payload.get("photos") or []:
        photo = PhotoMeta(
            photo_id=str(item.get("photo_id", "")),
            album_id=album_id,
            caption=item.get("caption", ""),
            thumb_url=item.get("thumb_url", ""),
            large_url=item.get("large_url", ""),
            original_url=item.get("original_url", ""),
            source_url=item.get("source_url", ""),
            local=item.get("local", ""),
            local_original=item.get("local_original", ""),
        )
        photo.status = _status_from_dict(item.get("status"))
        album.photos.append(photo)
    return album


def _bulletin_from_dict(bulletin_id: str, payload: dict[str, Any]) -> Bulletin:
    bulletin = Bulletin(
        bulletin_id=bulletin_id,
        room_id=str(payload.get("room_id", "")),
        title=payload.get("title", ""),
        content_html=payload.get("content_html", ""),
        source_url=payload.get("source_url", ""),
    )
    bulletin.status = _status_from_dict(payload.get("status"))
    return bulletin


def _video_from_dict(payload: dict[str, Any]) -> Video:
    video = Video(
        video_id=str(payload.get("video_id", "")),
        widget_id=str(payload.get("widget_id", "")),
        title=payload.get("title", ""),
        thumb_url=payload.get("thumb_url", ""),
        external_url=payload.get("external_url", ""),
        date=payload.get("date", ""),
        source_url=payload.get("source_url", ""),
        local_thumb=payload.get("local_thumb", ""),
    )
    video.status = _status_from_dict(payload.get("status"))
    return video


def _external_from_dict(page_id: str, payload: dict[str, Any]) -> ExternalPage:
    page = ExternalPage(
        page_id=page_id,
        url=payload.get("url", ""),
        title=payload.get("title", ""),
        content_html=payload.get("content_html", ""),
        origin=payload.get("origin", ""),
    )
    page.status = _status_from_dict(payload.get("status"))
    page.comments = _comments_from_dict(payload)
    return page


def _discussion_from_dict(payload: dict[str, Any]) -> Discussion:
    discussion = Discussion(
        discussion_id=str(payload.get("discussion_id", "")),
        forum_id=str(payload.get("forum_id", "")),
        title=payload.get("title", ""),
        author=payload.get("author", ""),
        date=payload.get("date", ""),
        content_html=payload.get("content_html", ""),
        source_url=payload.get("source_url", ""),
    )
    discussion.status = _status_from_dict(payload.get("status"))
    discussion.comments = _comments_from_dict(payload)
    return discussion


# ------------------------------------------------------------------ 各阶段


def prepare_structure(ctx: SyncContext, stages: Sequence[str]) -> SiteStructure:
    """按需发现站点结构（房间 → 模块 → 内容 ID 全集）。

    所有列表页都会被 HTTP 磁盘缓存，因此重复运行不会产生额外请求，
    这也让中断后的续跑几乎零成本。
    """
    discovery = ctx.discovery
    log.info("发现站点结构…")
    discovery.discover_rooms()

    if "bulletins" in stages:
        discovery.discover_bulletins()
    if "notes" in stages:
        discovery.discover_notes()
    if "photos" in stages or "albums" in stages:
        discovery.discover_photos()
    if "videos" in stages:
        discovery.discover_videos()
    if "forum" in stages:
        discovery.discover_forum()
    if "main" in stages and not discovery.structure.bulletins:
        # main 阶段依赖索引①/② 的内容来定位站外条目
        discovery.discover_bulletins()

    ctx.structure = discovery.structure
    return ctx.structure


def stage_rooms(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 1：房间与模块清单（结构已在 prepare_structure 中获取）。

    房间清单本身已在发现阶段抓取，这里只是把结果写进进度；仍经 StageRunner
    路由，使 ``--force`` / ``--recheck-unavailable`` / ``--limit`` / 续跑能一致生效
    （见 WARN-13）。
    """
    cfg = ctx.cfg
    rooms = ctx.structure.rooms
    if not rooms:
        raise SystemExit("未能发现任何房间，请检查网络或首页是否可访问")

    runner = StageRunner(
        ctx.progress,
        "rooms",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(room: Any) -> str:
        return f"room:{room.room_id}"

    def handler(room: Any) -> None:
        key = key_of(room)
        if room.widgets:
            ctx.progress.mark_done(
                key, stage="rooms", detail=f"{room.title}（{len(room.widgets)} 个模块）"
            )
        else:
            record_source_failure(ctx.progress, key, room.status, stage="rooms", url=room.url)

    result = runner.run(rooms, handler, key_of, desc="房间", limit=limit)
    ctx.results.append(result)
    log.info(
        "房间 %d 个，模块 %d 个",
        len(rooms),
        sum(len(r.widgets) for r in rooms),
    )
    return result


def stage_bulletins(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                    recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 2：公告栏 / 索引①/②。"""
    cfg = ctx.cfg
    widgets = ctx.structure.widgets_of("bulletin")
    runner = StageRunner(
        ctx.progress,
        "bulletins",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(widget: Any) -> str:
        return f"bulletin:{widget.widget_id}"

    def handler(widget: Any) -> None:
        url = f"{cfg.base_url}/room/{widget.room_id}/"
        page = ctx.resolver.resolve(url, context=f"公告栏 {widget.title}")
        if not page.has_content:
            record_source_failure(
                ctx.progress, key_of(widget), page.status, stage="bulletins", url=url
            )
            return
        bulletin = parse_bulletin(page.html, widget.widget_id, url, widget.room_id, cfg)
        if not bulletin.title:
            bulletin.title = widget.title
        bulletin.status = page.status
        ctx.bulletins[widget.widget_id] = bulletin
        ctx.progress.mark_done(
            key_of(widget), stage="bulletins", detail=truncate(bulletin.title, 40)
        )

    result = runner.run(widgets, handler, key_of, desc="公告栏", limit=limit)
    ctx.results.append(result)

    # 索引分组在 generate_site() 里统一重建，见 SyncContext.build_index_groups
    return result


COMMENTS_PER_PAGE = 10


def _collect_note_comments(
    ctx: SyncContext, html: str, note_url: str, title: str
) -> list[Comment]:
    """收集一篇日记的全部评论（含翻页）。

    评论是服务端静态渲染的，**不需要登录**。翻页走 note URL 的 ``?start=N``。
    """
    comments = parse_note_comments(html, ctx.cfg)
    total_pages = parse_note_comment_pages(html, ctx.cfg)
    step = parse_page_step(html, ctx.cfg, COMMENTS_PER_PAGE)

    for index in range(1, total_pages):
        sub_url = f"{note_url}?start={index * step}"
        page = ctx.resolver.resolve(sub_url, context=f"日记评论 {truncate(title, 30)} 第 {index + 1} 页")
        if page.has_content:
            comments.extend(parse_note_comments(page.html, ctx.cfg))

    # 翻页边界可能重复，按 comment_id 去重
    seen: set[str] = set()
    unique: list[Comment] = []
    for comment in comments:
        if comment.comment_id and comment.comment_id in seen:
            continue
        if comment.comment_id:
            seen.add(comment.comment_id)
        unique.append(comment)
    return unique


def stage_notes(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 3：日记详情 + 配图归档。"""
    cfg = ctx.cfg
    entries = ctx.structure.note_entries
    if not entries:
        log.warning("没有发现日记列表，跳过")
        return StageResult(stage="notes")

    runner = StageRunner(
        ctx.progress,
        "notes",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(entry: Any) -> str:
        return f"note:{entry.note_id}"

    def handler(entry: Any) -> None:
        key = key_of(entry)
        url = cfg.note_url(entry.widget_id, entry.note_id)
        page = ctx.resolver.resolve(url, context=f"日记 {entry.title}")

        if not page.has_content:
            # 正文拿不到，但仍保留标题/日期等元信息，页面会带提示块
            note = Note(
                note_id=entry.note_id,
                widget_id=entry.widget_id,
                title=entry.title,
                date=entry.date,
                comment_count=entry.comment_count,
                source_url=url,
                status=page.status,
            )
            ctx.notes[entry.note_id] = note
            record_source_failure(ctx.progress, key, page.status, stage="notes", url=url)
            return

        note = parse_note(page.html, entry.widget_id, entry.note_id, url, cfg)
        if not note.title:
            note.title = entry.title
        if not note.date:
            note.date = entry.date
        # 评论数以列表页条目的 "(N回应)" 为准：详情页没有权威数量
        # （那里的"回应"只是每条评论的回复按钮，见 parse_note 的说明）
        note.comment_count = entry.comment_count
        note.status = page.status

        # 归档配图并建立重写映射
        refs = ctx.media.collect_note_images(note.content_html, note.note_id)
        if refs:
            ctx.media.archive_note_images(refs, note.note_id)
        note.images = refs

        # 归档评论。评论是服务端静态渲染的，免登录即可拿到；
        # 数量多时 note URL 支持 ?start=N 翻页（每页 10 条）。
        note.comments = _collect_note_comments(ctx, page.html, url, entry.title)

        ctx.notes[note.note_id] = note
        ctx.progress.mark_done(
            key,
            stage="notes",
            detail=f"{truncate(note.title, 40)} · {len(refs)} 图 · {len(note.comments)} 评论",
            images=len(refs),
            comments=len(note.comments),
        )

    result = runner.run(entries, handler, key_of, desc="日记", limit=limit)
    ctx.results.append(result)
    return result


def _archive_photo_original(ctx: SyncContext, meta: PhotoMeta) -> str:
    """归档照片原图，成功时写回 :attr:`PhotoMeta.local_original`。

    返回错误信息（成功为空串）。原图只是"更好的一份"，拿不到不算失败 ——
    网格里还有预览图可看，页面照样成立。
    """
    if not meta.original_url:
        return ""
    dest, local = ctx.media.album_original_path(meta.album_id, meta.photo_id, meta.original_url)
    outcome = ctx.media.download(
        meta.original_url, dest, local, variants=album_original_variants(meta.original_url)
    )
    if outcome.ok:
        # 落盘名字由内容决定，可能已不是按 URL 后缀算出来的那个，以返回值为准
        meta.local_original = outcome.local_url
        return ""
    return outcome.error


def _archive_photo_preview(ctx: SyncContext, meta: PhotoMeta) -> str:
    """归档网格里显示的预览图，成功时写回 :attr:`PhotoMeta.local`。

    页面没给出图片地址时，让原图兼作显示图 —— 网格里宁可显示大图，
    也不能开天窗。返回错误信息（成功为空串）。
    """
    if not meta.large_url:
        meta.local = meta.local_original
        return ""
    dest, local = ctx.media.album_image_path(meta.album_id, meta.photo_id, meta.large_url)
    outcome = ctx.media.download(
        meta.large_url, dest, local, variants=album_image_variants(meta.large_url)
    )
    if outcome.ok:
        # 同上：URL 后缀会撒谎，落盘名字以返回值为准
        meta.local = outcome.local_url
        return ""
    # 预览图拿不到、原图在：用原图顶上，至少网格里看得见
    meta.local = meta.local_original
    return outcome.error


def stage_photos(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                 recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 4：相册图片归档。"""
    cfg = ctx.cfg
    pairs: list[tuple[str, str]] = []
    # ``--limit`` is an album-level smoke-test limit.  Keep photos and album
    # stages aligned so an album emitted in the same run always has its photo
    # details eligible for processing (SUG-23).
    album_items = list(ctx.structure.photo_ids.items())
    if limit > 0:
        album_items = album_items[:limit]
    for album_id, photo_ids in album_items:
        pairs.extend((album_id, pid) for pid in photo_ids)

    if not pairs:
        log.warning("没有发现相册图片，跳过")
        return StageResult(stage="photos")

    runner = StageRunner(
        ctx.progress,
        "photos",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(pair: tuple[str, str]) -> str:
        return f"photo:{pair[0]}:{pair[1]}"

    def handler(pair: tuple[str, str]) -> None:
        album_id, photo_id = pair
        url = cfg.photo_url(album_id, photo_id)
        page = ctx.resolver.resolve(url, context=f"照片 {photo_id}")
        if not page.has_content:
            record_source_failure(
                ctx.progress, key_of(pair), page.status, stage="photos", url=url
            )
            return
        meta = parse_photo_detail(page.html, album_id, photo_id, url, cfg)
        if not (meta.original_url or meta.large_url):
            record_source_failure(ctx.progress, key_of(pair), meta.status, stage="photos", url=url)
            return
        # 无论下载成败都记住描述，供 stage_albums 复用
        ctx.photo_meta[pair] = meta
        # 原图与预览图各存一份：网格里显示预览图（小），点开预览的是原图（大）。
        # 页面 <img> 的 large 只是豆瓣的处理版（长边 1600，小图还会被放大），
        # 原图才是上传时的文件，只有"查看原图"链接指向它。
        error = _archive_photo_original(ctx, meta)
        error = _archive_photo_preview(ctx, meta) or error
        # 但两者是同一份字节时就只留预览：原图不比它多任何信息。
        # 必须放在两次归档之后 —— 原图先落盘时预览还没有，无从比对。
        if ctx.media.drop_redundant_original(meta.album_id, meta.photo_id):
            meta.local_original = ""
        if meta.local or meta.local_original:
            ctx.progress.mark_done(key_of(pair), stage="photos", detail=meta.caption[:40])
        else:
            ctx.progress.mark_unavailable(
                key_of(pair), error or "图片归档失败", stage="photos", url=url
            )

    result = runner.run(pairs, handler, key_of, desc="照片")
    ctx.results.append(result)
    return result


def stage_albums(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                 recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 5：汇总相册元信息（图片已在上一阶段归档）。

    优先复用发现阶段已枚举好的照片（``ctx.structure.album_photos``），避免同步时
    再次 resolve + 解析同一份列表页（见 WARN-12）；只有发现阶段没拿到枚举结果时
    才现场抓取。
    """
    cfg = ctx.cfg
    album_ids = list(ctx.structure.photo_ids.keys())
    if not album_ids:
        return StageResult(stage="albums")

    runner = StageRunner(
        ctx.progress,
        "albums",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(album_id: str) -> str:
        return f"album:{album_id}"

    def handler(album_id: str) -> None:
        url = cfg.photos_list_url(album_id)
        # 优先复用发现阶段枚举好的照片（含分页），省一次 resolve + 解析
        stored_photos = ctx.structure.album_photos.get(album_id)
        if stored_photos is not None:
            photos = stored_photos
            status = ctx.structure.album_status.get(album_id) or SourceStatus()
            title = ctx.structure.album_titles.get(album_id, "")
        else:
            page = ctx.resolver.resolve(url, context=f"相册 {album_id}")
            title = ctx.structure.album_titles.get(album_id, "")
            if page.has_content and not title:
                title = parse_album_title(page.html, cfg)
            status = page.status
            # 列表页分页：只读第一页会把后面的照片整批漏掉
            photos = (
                enumerate_album_photos(ctx.resolver, album_id, cfg, first_html=page.html)
                if page.has_content else []
            )

        album = Album(
            album_id=album_id,
            title=title or f"相册 {album_id}",
            source_url=url,
            status=status,
        )
        album.photos = photos

        # 复用 stage_photos 已解析的描述，避免重复请求；本地路径则以磁盘为准
        for photo in album.photos:
            pair = (album_id, photo.photo_id)
            cached_meta = ctx.photo_meta.get(pair)
            if cached_meta is not None and cached_meta.caption:
                photo.caption = cached_meta.caption
            original = ctx.media.find_album_original(album_id, photo.photo_id)
            if original is not None:
                photo.local_original = original[1]
            found = ctx.media.find_album_image(album_id, photo.photo_id)
            if found is not None:
                photo.local = found[1]
            elif original is not None:
                # 只有原图时拿它当显示图（与 stage_photos / refresh_album_media 一致）
                photo.local = original[1]

        ctx.albums[album_id] = album
        ctx.progress.mark_done(
            key_of(album_id), stage="albums", detail=f"{album.title}（{len(album.photos)} 张）"
        )

    result = runner.run(album_ids, handler, key_of, desc="相册", limit=limit)
    ctx.results.append(result)
    log.info("相册：%d 个，照片：%d 张", len(ctx.albums), sum(len(a.photos) for a in ctx.albums.values()))
    return result


def stage_videos(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                 recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 6：视频条目（缩略图归档，正片在优酷）。"""
    cfg = ctx.cfg
    videos = ctx.structure.videos
    if not videos:
        return StageResult(stage="videos")

    runner = StageRunner(
        ctx.progress,
        "videos",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(video: Video) -> str:
        return f"video:{video.video_id}"

    def handler(video: Video) -> None:
        if video.thumb_url:
            dest, local = ctx.media.video_thumb_path(video.video_id, video.thumb_url)
            outcome = ctx.media.download(video.thumb_url, dest, local)
            if outcome.ok:
                video.local_thumb = outcome.local_url
        merge_by(ctx.videos, [video], lambda v: v.video_id)
        ctx.progress.mark_done(key_of(video), stage="videos", detail=truncate(video.title, 40))

    result = runner.run(videos, handler, key_of, desc="视频", limit=limit)
    ctx.results.append(result)
    return result


def stage_forum(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 7：论坛讨论帖（评论为静态渲染，可完整归档）。"""
    cfg = ctx.cfg
    topics: list[tuple[str, str, str]] = []
    for forum_id, items in ctx.structure.forum_topics.items():
        topics.extend((forum_id, did, title) for did, title in items)
    if not topics:
        return StageResult(stage="forum")

    runner = StageRunner(
        ctx.progress,
        "forum",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(topic: tuple[str, str, str]) -> str:
        return f"discussion:{topic[1]}"

    def handler(topic: tuple[str, str, str]) -> None:
        forum_id, discussion_id, title = topic
        url = cfg.discussion_url(forum_id, discussion_id)
        page = ctx.resolver.resolve(url, context=f"讨论帖 {title}")
        if not page.has_content:
            record_source_failure(
                ctx.progress, key_of(topic), page.status, stage="forum", url=url
            )
            return
        discussion = parse_discussion(page.html, forum_id, discussion_id, url, cfg)
        if not discussion.title:
            discussion.title = title
        discussion.status = page.status
        merge_by(ctx.discussions, [discussion], lambda d: d.discussion_id)
        ctx.progress.mark_done(
            key_of(topic), stage="forum", detail=f"{len(discussion.comments)} 条回应"
        )

    result = runner.run(topics, handler, key_of, desc="讨论帖", limit=limit)
    ctx.results.append(result)
    return result


def stage_miniblog(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
                   recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 8：广播室动态流。

    经 StageRunner 路由，使续跑 / ``--force`` / ``--limit`` 能一致生效
    （此前每轮无条件 ``mark_done``、从不查询进度，见 WARN-13）。
    """
    cfg = ctx.cfg
    widgets = ctx.structure.widgets_of("miniblog")
    if not widgets:
        return StageResult(stage="miniblog")

    runner = StageRunner(
        ctx.progress,
        "miniblog",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(widget: Any) -> str:
        return f"miniblog:{widget.widget_id}"

    def handler(widget: Any) -> None:
        key = key_of(widget)
        url = cfg.miniblog_url(widget.widget_id)
        page = ctx.resolver.resolve(url, context=f"广播室 {widget.title}")
        if not page.has_content:
            # 广播室列表页可能 302，回退到房间页
            room_url = f"{cfg.base_url}/room/{widget.room_id}/"
            page = ctx.resolver.resolve(room_url, context=f"广播室 {widget.title}")
        if not page.has_content:
            record_source_failure(ctx.progress, key, page.status, stage="miniblog", url=url)
            return
        statuses = parse_miniblog(page.html, cfg)
        merge_by(ctx.miniblog, statuses, lambda s: s.status_id)
        ctx.progress.mark_done(key, stage="miniblog", detail=f"{len(statuses)} 条动态")

    result = runner.run(widgets, handler, key_of, desc="广播室", limit=limit)
    ctx.results.append(result)
    return result


def _external_page_id(url: str) -> str:
    """由 URL 派生稳定的页面 ID，例如 ``/topic/499780453/`` → ``topic-499780453``。"""
    path = (urlparse(url).path or "").strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    return slug or "page"


def _external_targets(ctx: SyncContext) -> list[tuple[str, str, str]]:
    """从索引①/② 里找出指向豆瓣主站的条目，返回 ``[(page_id, url, origin)]``。"""
    seen: set[str] = set()
    targets: list[tuple[str, str, str]] = []
    for group in ctx.index_groups:
        for entry in group.entries:
            url = (entry.url or "").strip()
            if not url:
                continue
            host = (urlparse(url).hostname or "").lower()
            if host not in EXTERNAL_HOSTS:
                continue
            page_id = _external_page_id(url)
            if page_id in seen:
                continue
            seen.add(page_id)
            targets.append((page_id, url, group.title))
    return targets


def stage_main(ctx: SyncContext, *, show_progress: bool, limit: int = 0,
               recheck_unavailable: bool = False, force: bool = False) -> StageResult:
    """阶段 9：补抓索引里指向豆瓣主站的页面（需要登录）。

    这些页面未登录会 302 到 ``sec.douban.com``，因此只在登录后才有内容。
    用独立的 key（``main:{page_id}``）而不是复用 notes 的 key，
    这样 ``--recheck-unavailable`` 只重试这些页面，不会把已归档的 144 篇日记全部重抓。
    """
    cfg = ctx.cfg
    if not ctx.index_groups:
        ctx.build_index_groups()

    targets = _external_targets(ctx)
    if not targets:
        log.info("索引里没有指向站外（%s）的条目，跳过", "/".join(EXTERNAL_HOSTS))
        return StageResult(stage="main")

    runner = StageRunner(
        ctx.progress,
        "main",
        cfg=cfg,
        show_progress=show_progress,
        recheck_unavailable=recheck_unavailable,
        recheck_done=force,
    )

    def key_of(target: tuple[str, str, str]) -> str:
        return f"main:{target[0]}"

    def handler(target: tuple[str, str, str]) -> None:
        page_id, url, origin = target
        page = ctx.resolver.resolve(url, context=f"站外页面 {url}")
        if not page.has_content:
            # 仍保留元信息，页面会带"需登录"提示块，索引里也不会成为死链
            ctx.external[page_id] = ExternalPage(
                page_id=page_id, url=url, origin=origin, status=page.status
            )
            record_source_failure(
                ctx.progress, key_of(target), page.status, stage="main", url=url
            )
            return
        external = parse_external_page(page.html, url, page_id, origin, cfg)
        external.status = page.status
        ctx.external[page_id] = external
        ctx.progress.mark_done(
            key_of(target),
            stage="main",
            detail=f"{truncate(external.title, 40)} · {len(external.comments)} 评论",
        )

    result = runner.run(targets, handler, key_of, desc="站外页面", limit=limit)
    ctx.results.append(result)
    return result


STAGE_FUNCS = {
    "rooms": stage_rooms,
    "bulletins": stage_bulletins,
    "notes": stage_notes,
    "photos": stage_photos,
    "albums": stage_albums,
    "videos": stage_videos,
    "forum": stage_forum,
    "miniblog": stage_miniblog,
    "main": stage_main,
}


# ------------------------------------------------------------------ 生成产物


def generate_site(ctx: SyncContext, *, verbose: bool = False) -> dict[str, Any]:
    """把抓取结果渲染成 VitePress 站点产物。"""
    cfg = ctx.cfg
    ctx.refresh_album_media()
    ctx.refresh_unavailable()
    ctx.rebuild_context()
    ctx.build_index_groups()

    # 分类归属：索引①/② 优先，未覆盖的归入 尚子的房间
    mapping = build_note_to_group(ctx.index_groups)
    categories = group_by_category(list(ctx.notes.keys()), mapping)
    for note_id, note in ctx.notes.items():
        group_title, order = mapping.get(note_id, (FALLBACK_CATEGORY, 0))
        note.category = group_title
        note.index_order = order

    notes_by_category = categories
    fallback_ids = notes_by_category.get(FALLBACK_CATEGORY, [])
    fallback_notes = [ctx.notes[nid] for nid in fallback_ids if nid in ctx.notes]

    # 站点素材（头像）
    avatar_local = ""
    avatar_url = ctx.structure.meta.get("avatar", "")
    if avatar_url:
        avatar_local = ctx.media.archive_site_asset(avatar_url, "avatar.jpg")

    albums = sorted(ctx.albums.values(), key=lambda a: a.album_id)
    notes = ctx.notes

    # 逐篇渲染
    for note in notes.values():
        ctx.emitter.emit_note(note)

    for album in albums:
        ctx.emitter.emit_album(album)

    # 索引公告里的"关于"页（About PPK）
    about_bulletin = next(
        (b for b in ctx.bulletins.values() if "About" in b.title or "PPK" in b.title),
        None,
    )

    ctx.emitter.emit_home(
        ctx.structure.meta,
        ctx.index_groups,
        albums,
        avatar_local=avatar_local,
        stats={
            "notes": len(notes),
            "photos": sum(len(a.photos) for a in albums),
            "albums": len(albums),
            "videos": len(ctx.videos),
        },
    )
    ctx.emitter.emit_notes_index(ctx.index_groups, notes, fallback_notes=fallback_notes)
    ctx.emitter.emit_albums_index(albums)
    ctx.emitter.emit_about(about_bulletin, ctx.structure.meta)
    ctx.emitter.emit_videos(ctx.videos)
    ctx.emitter.emit_board(ctx.discussions)
    ctx.emitter.emit_broadcast(ctx.miniblog)
    external_pages = sorted(ctx.external.values(), key=lambda p: p.page_id)
    for page in external_pages:
        ctx.emitter.emit_external(page)
    ctx.emitter.emit_external_index(external_pages)

    ctx.emitter.emit_sidebar(
        ctx.index_groups,
        notes,
        fallback_notes=fallback_notes,
        albums=albums,
        videos_count=len(ctx.videos),
        external_count=len(external_pages),
    )

    ctx.emitter.emit_unavailable_report(ctx.unavailable)
    manifest = ctx.build_manifest()
    ctx.emitter.emit_manifest(manifest)

    ctx.save_data()
    return manifest


def write_sync_report(ctx: SyncContext, *, mode: str) -> Path:
    """产出同步报告。"""
    stats = ctx.fetcher.finalize().to_dict()
    summary = {
        "模式": mode,
        "日记": len(ctx.notes),
        "相册": len(ctx.albums),
        "照片": sum(len(a.photos) for a in ctx.albums.values()),
        "视频": len(ctx.videos),
        "公告栏": len(ctx.bulletins),
        "讨论帖": len(ctx.discussions),
        "广播动态": len(ctx.miniblog),
        "站外页面": len(ctx.external),
        "不可访问页面": len(ctx.unavailable),
        "图片下载": ctx.media.summary()["downloaded"],
        "图片跳过（已存在）": ctx.media.summary()["skipped"],
        "图片失败": ctx.media.summary()["failed"],
        "图片字节": human_size(int(ctx.media.summary()["bytesTotal"])),
    }
    payload = {
        "generatedAt": now_iso(),
        "summary": summary,
        "stages": [
            {
                "stage": r.stage,
                "processed": r.processed,
                "total": r.total,
                "skipped": r.skipped,
                "failed": r.failed,
                "elapsed": human_duration(r.elapsed),
            }
            for r in ctx.results
        ],
        "http": stats,
    }
    return ctx.emitter.emit_sync_report(payload)


# ------------------------------------------------------------------ 子命令


def cmd_discover(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    with SyncContext(cfg, use_archive=cfg.archive_enabled) as ctx:
        discovery = SiteDiscovery(ctx.resolver, cfg)
        structure = discovery.crawl_structure()
        write_json(cfg.data_dir / "structure.json", structure.to_dict())
        print()
        print(f"房间：{len(structure.rooms)}")
        for kind in ("bulletin", "notes", "photos", "videos", "forum", "miniblog"):
            widgets = structure.widgets_of(kind)
            if widgets:
                print(f"  {kind:9s} {len(widgets):2d} 个模块")
        print(f"日记：{structure.note_count} 篇")
        print(f"照片：{structure.photo_count} 张")
        print(f"视频：{len(structure.videos)} 条")
        print(f"讨论帖：{sum(len(v) for v in structure.forum_topics.values())} 个")
        stats = ctx.fetcher.finalize()
        print(f"\n请求 {stats.requests} 次，缓存命中 {stats.cache_hits} 次，"
              f"耗时 {human_duration(stats.elapsed)}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    stages = resolve_stages(args.stages)

    if not args.i_have_read_robots and not cfg.offline and not args.dry_run:
        print(robots_notice(cfg))
        return 2

    ensure_dirs(cfg)

    with SyncContext(cfg, use_archive=cfg.archive_enabled) as ctx:
        # 总是先恢复既有产物：断点续接时被跳过的阶段（已完成）
        # 产出的数据仍然需要参与最终生成。
        ctx.load_existing()
        if args.offline:
            log.info("离线模式：只读本地缓存与已抓取产物")

        if args.dry_run:
            return _dry_run(ctx, stages, args)

        log.info("=" * 68)
        log.info("开始同步：阶段 = %s", ", ".join(stages))
        log.info("请求间隔 %s · 传输 %s · archive.org 补足 %s",
                 describe_delay(cfg.delay_min, cfg.delay_max),
                 f"浏览器({cfg.browser_channel})" if cfg.browser_enabled else f"HTTP({cfg.impersonate})",
                 "开" if (ctx.wayback and ctx.wayback.enabled) else "关（默认）")
        rate_note = crawl_delay_warning(cfg)
        if rate_note:
            # 快于 Crawl-delay 的档位在这里再记一次：上面那行 INFO 只说"是多少"，
            # 该提示说明操作的实际影响，避免数小时运行后才发现档位选错。
            log.warning(rate_note)
        log.info("=" * 68)

        try:
            # Always revalidate discovery/list pages.  Completed progress items
            # may still have changed upstream; only unchanged detail stages
            # remain skipped afterwards.
            ctx.resolver.revalidate = True
            prepare_structure(ctx, stages)
            ctx.resolver.revalidate = False
            for name in stages:
                func = STAGE_FUNCS[name]
                func(
                    ctx,
                    show_progress=args.progress,
                    limit=args.limit,
                    recheck_unavailable=args.recheck_unavailable,
                    force=args.force,
                )
        except CircuitBreakerOpen as exc:
            log.error("已熔断停止：%s", exc)
            ctx.progress.save(force=True)
            ctx.save_data()
            if getattr(ctx.fetcher, "session_expired", False):
                log.error(
                    "检测到豆瓣人机校验（sec.douban.com），登录态可能已失效。\n"
                    "  请先重新登录：npm run login\n"
                    "  再续跑：      npm run sync -- --i-have-read-robots --recheck-unavailable"
                )
            log.error(
                "进度已保存。建议等待 30~60 分钟后再续跑（已完成内容不会重复请求）。"
            )
            return 3
        except KeyboardInterrupt:
            log.warning("收到中断信号，正在保存进度…")
            ctx.progress.save(force=True)
            ctx.save_data()
            log.warning("进度已保存，重新执行同一命令即可续跑。")
            return 130
        except Exception as exc:
            # 解析 bug / 异常响应 / 缺字段等不在上方两类中的异常会冒泡到此处，
            # 必须先把内存里已解析但未落盘的批次数据写盘，否则 progress.json 已
            # 标记 done 而 data/*.json 仍是旧快照，resume 时会永久丢失最后一批内容。
            log.error("同步过程中发生未预期错误：%s", exc)
            ctx.progress.save(force=True)
            ctx.save_data()
            raise

        ctx.refresh_unavailable()

        if not args.no_emit:
            log.info("生成站点产物…")
            generate_site(ctx)
            report = write_sync_report(ctx, mode="sync")
            log.info("同步报告：%s", report)
        else:
            ctx.persist_products()

        ctx.progress.save(force=True)
        _print_summary(ctx)
    return 0


def _dry_run(ctx: SyncContext, stages: list[str], args: argparse.Namespace) -> int:
    """预演：只枚举结构并估算请求数与耗时。"""
    cfg = ctx.cfg
    print("预演模式：只枚举站点结构，不抓取详情。\n")
    structure = prepare_structure(ctx, stages)

    page_requests = 0
    if "rooms" in stages:
        page_requests += 1 + len(structure.rooms)
    if "bulletins" in stages:
        page_requests += len(structure.widgets_of("bulletin"))
    if "notes" in stages:
        widgets = structure.widgets_of("notes")
        page_requests += len(widgets) * 5 + structure.note_count  # 列表页按平均 5 页估
    if "photos" in stages:
        page_requests += structure.photo_count + len(structure.photo_ids)
    if "albums" in stages:
        page_requests += len(structure.photo_ids)
    if "videos" in stages:
        page_requests += len(structure.widgets_of("videos"))
    if "forum" in stages:
        page_requests += sum(len(v) for v in structure.forum_topics.values()) + 1
    if "miniblog" in stages:
        page_requests += len(structure.widgets_of("miniblog"))

    image_requests = 0
    if "notes" in stages:
        image_requests += structure.note_count * 2   # 每篇平均约 2 张配图
    if "photos" in stages:
        image_requests += structure.photo_count
    if "videos" in stages:
        image_requests += len(structure.videos)

    total = page_requests + image_requests
    cached = 0
    try:
        from .http_client import count_cached

        urls: list[str] = [cfg.site_url]
        cached = count_cached(cfg, urls)
    except Exception:  # noqa: BLE001
        pass

    print(f"计划抓取：")
    print(f"  页面请求  约 {page_requests:5d} 次")
    print(f"  图片请求  约 {image_requests:5d} 次")
    print(f"  合计      约 {total:5d} 次")
    print(f"  预估耗时  约 {estimate_duration(total, cfg)}"
          f"（间隔 {describe_delay(cfg.delay_min, cfg.delay_max)}，用 --speed 换档）")
    print()
    print(f"内容规模：")
    print(f"  房间       {len(structure.rooms)}")
    print(f"  日记       {structure.note_count} 篇")
    print(f"  相册       {len(structure.photo_ids)} 个 / {structure.photo_count} 张")
    print(f"  视频       {len(structure.videos)} 条")
    print(f"  讨论帖     {sum(len(v) for v in structure.forum_topics.values())} 个")
    print()
    print("确认无误后执行：npm run sync -- --i-have-read-robots")
    write_json(cfg.data_dir / "structure.json", structure.to_dict())
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    ensure_dirs(cfg)
    with SyncContext(cfg, use_archive=False) as ctx:
        ctx.load_existing()
        if not ctx.notes and not ctx.albums:
            print("没有找到已抓取的数据，请先运行 sync。", file=sys.stderr)
            return 1
        manifest = generate_site(ctx)
        print(f"已生成站点产物：{len(manifest['notes'])} 篇日记、"
              f"{len(manifest['albums'])} 个相册")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    # report 是纯读命令，不应该反过来改写进度文件
    store = ProgressStore(cfg=cfg, readonly=True)
    print(store.report())
    path = cfg.data_dir / "progress-report.md"
    from .util import atomic_write_text

    atomic_write_text(path, store.report())
    print(f"（已写入 {path}）")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    from .verify import Verifier

    verifier = Verifier(cfg)
    ok = verifier.run(sample=args.sample)
    print(verifier.report_text())
    return 0 if ok else 1


def cmd_login(args: argparse.Namespace) -> int:
    """打开浏览器让用户登录，或校验已有会话。"""
    cfg = _config_from_args(args)
    ensure_dirs(cfg)

    if args.check:
        status = auth.check_session(cfg)
        print(f"会话状态：{status.label}")
        print(f"  {status.detail}")
        if status.state_path:
            print(f"  状态文件：{status.state_path}")
        if status.logged_in:
            print("\n可以直接执行：npm run sync -- --i-have-read-robots")
        else:
            print("\n请执行：npm run login")
        return 0 if status.logged_in else 1

    print()
    print("=" * 68)
    print("豆瓣登录")
    print("=" * 68)
    print("即将打开一个 Chrome 窗口，请在其中完成登录：")
    print("  · 扫码 / 短信 / 账号密码 / 图形验证码 都可以")
    print("  · 本工具全程不接触你的密码，只保存登录后的会话状态")
    print("  · 登录成功后会自动检测并关闭窗口")
    print(f"  · 最长等待 {int(args.timeout or cfg.browser_login_timeout)} 秒")
    print("=" * 68)
    print()

    def on_tick(elapsed: float) -> None:
        print(f"\r  等待登录… {int(elapsed)} 秒", end="", flush=True)

    ok, detail = auth.run_login_flow(
        cfg,
        timeout=args.timeout,
        headless=False,
        on_tick=on_tick,
    )
    print("\r" + " " * 40 + "\r", end="")

    if not ok:
        print(f"✗ 登录未完成：{detail}")
        print("  会话文件未写入。请重新执行 npm run login")
        return 1

    print(f"✓ 登录状态已保存：{cfg.auth_state_path}")
    print(f"  {detail}")
    print("  权限已设为 0600，且已在 .gitignore 中排除")
    print()
    print("下一步（补抓此前拿不到的内容）：")
    print("  npm run sync -- --i-have-read-robots --recheck-unavailable")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "scraper/tests", "-q"],
        cwd=str(CONFIG.root),
    )
    return result.returncode


# ------------------------------------------------------------------ 辅助


def _config_from_args(args: argparse.Namespace) -> Config:
    import dataclasses

    overrides: dict[str, Any] = {}
    if getattr(args, "offline", False):
        overrides["offline"] = True
    # 显式跟随命令行：默认 False（关闭），--archive 打开，--no-archive 关闭
    overrides["archive_enabled"] = bool(getattr(args, "archive", False))
    # 浏览器传输：默认开启，--no-browser 关闭
    overrides["browser_enabled"] = bool(getattr(args, "browser", True))
    # 限速：--speed 写入档位预设，--delay 写入精确值（更具体，故优先）。
    # 两者互斥由 argparse 保证；参数写在子命令两侧时它拦不住，这里兜住。
    if getattr(args, "speed", None):
        overrides["delay_min"], overrides["delay_max"] = speed_tier(args.speed)
    if getattr(args, "delay", None):
        overrides["delay_min"] = args.delay
        overrides["delay_max"] = args.delay + 2.0
    if getattr(args, "impersonate", None):
        overrides["impersonate"] = args.impersonate
    cfg = dataclasses.replace(CONFIG, **overrides) if overrides else CONFIG
    ensure_dirs(cfg)
    return cfg


def _print_summary(ctx: SyncContext) -> None:
    stats = ctx.fetcher.finalize()
    media = ctx.media.summary()
    print()
    print("=" * 68)
    print("同步完成")
    print("=" * 68)
    print(f"  日记        {len(ctx.notes):5d} 篇")
    print(f"  相册        {len(ctx.albums):5d} 个（{sum(len(a.photos) for a in ctx.albums.values())} 张）")
    print(f"  视频        {len(ctx.videos):5d} 条")
    print(f"  讨论帖      {len(ctx.discussions):5d} 个")
    print(f"  广播动态    {len(ctx.miniblog):5d} 条")
    if ctx.external:
        print(f"  站外页面    {len(ctx.external):5d} 个（需登录）")
    print(f"  不可访问    {len(ctx.unavailable):5d} 个（详见 data/unavailable.md）")
    print(f"  图片下载    {int(media['downloaded']):5d} 张"
          f"（跳过 {int(media['skipped'])}，失败 {int(media['failed'])}，"
          f"{human_size(int(media['bytesTotal']))}）")
    if int(media["archivedFromWayback"]):
        print(f"  其中 archive.org 补足 {int(media['archivedFromWayback'])} 张")
    print(f"  网络请求    {stats.requests:5d} 次（缓存命中 {stats.cache_hits}，"
          f"重试 {stats.retries}，被拦截 {stats.blocked}）")
    print(f"  耗时        {human_duration(stats.elapsed)}")
    print()
    print("下一步：npm run docs:dev 预览，npm run verify 校验")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.quiet)

    # Ctrl-C 时不打印 traceback
    def _sigint(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _sigint)

    handlers = {
        "sync": cmd_sync,
        "emit": cmd_emit,
        "discover": cmd_discover,
        "report": cmd_report,
        "verify": cmd_verify,
        "login": cmd_login,
        "test": cmd_test,
    }
    handler = handlers[args.command]
    try:
        return handler(args)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，给出可读错误
        log.error("执行失败：%s", exc, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
