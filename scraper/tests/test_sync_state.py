"""同步状态恢复与断点续接的集成测试。

针对两个曾经真实踩到的坑：

1. 公告栏阶段因断点续接被整体跳过 → ``ctx.bulletins`` 为空 →
   索引分组为空 → sidebar 全空。
2. 只跑部分阶段（如 ``--stages notes``）时站点结构丢失 → 无法枚举内容。

解法是 ``SyncContext.load_existing()`` 恢复全部既有产物，
并把索引解析从"抓取阶段"移到"生成阶段"。
"""

from __future__ import annotations

import json

from scraper.cli import SyncContext, merge_by
from scraper.config import ensure_dirs
from scraper.models import (
    Album,
    Availability,
    Bulletin,
    Comment,
    Discussion,
    ExternalPage,
    IndexEntry,
    IndexGroup,
    Note,
    PhotoMeta,
    Room,
    SourceStatus,
    Video,
    Widget,
)
from scraper.util import write_json

INDEX_HTML = (
    "☆【聲之形】<br>"
    '<a href="http://site.douban.com/211330/widget/notes/1/note/111/">文章一</a><br>'
    '<a href="http://site.douban.com/211330/widget/notes/1/note/222/">文章二</a><br>'
    "☆【轻音！系列】<br>"
    '<a href="http://site.douban.com/211330/widget/notes/2/note/333/">文章三</a>'
)


def _seed_data(cfg, *, bulletins=None, notes=None, albums=None, structure=None) -> None:
    ensure_dirs(cfg)
    write_json(cfg.data_dir / "bulletins.json", bulletins or {})
    write_json(cfg.data_dir / "notes.json", notes or {})
    write_json(cfg.data_dir / "albums.json", albums or {})
    write_json(cfg.data_dir / "videos.json", [])
    write_json(cfg.data_dir / "forum.json", [])
    write_json(cfg.data_dir / "miniblog.json", [])
    if structure is not None:
        write_json(cfg.data_dir / "structure.json", structure)


def _album_payload(album_id: str, *photo_ids: str) -> dict:
    """构造一个相册产物，图片一律记为未归档（``local`` 为空）。"""
    album = Album(album_id=album_id, title="相册", source_url=f"https://x/{album_id}/")
    album.photos = [
        PhotoMeta(
            photo_id=pid,
            album_id=album_id,
            thumb_url=f"https://img3.doubanio.com/view/photo/thumb/public/p{pid}.webp",
        )
        for pid in photo_ids
    ]
    album.status = SourceStatus(availability=Availability.OK)
    return album.to_dict()


def _write_album_image(cfg, album_id: str, photo_id: str, suffix: str = ".webp") -> None:
    """在相册目录里放一个真图片文件。"""
    directory = cfg.media_dir / "albums" / album_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{photo_id}{suffix}").write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 40)


def _video_payload(video_id: str, title: str = "视频一") -> dict:
    video = Video(
        video_id=video_id,
        widget_id="15222929",
        title=title,
        thumb_url="https://vthumb.ykimg.com/abc.jpg",
        external_url="https://v.youku.com/v_show/id_x.html",
        source_url="https://site.douban.com/211330/",
    )
    video.status = SourceStatus(availability=Availability.OK)
    return video.to_dict()


def _bulletin_payload(bulletin_id: str, title: str, content: str) -> dict:
    bulletin = Bulletin(
        bulletin_id=bulletin_id,
        room_id="2793793",
        title=title,
        content_html=content,
        source_url="https://site.douban.com/211330/",
        status=SourceStatus(availability="ok"),
    )
    return bulletin.to_dict()


STRUCTURE_PAYLOAD = {
    "meta": {"name": "兔子山的小站", "description": "描述"},
    "rooms": [
        {
            "room_id": "2793793",
            "title": "宇宙的入口",
            "url": "https://site.douban.com/211330/room/2793793/",
            "is_home": True,
            "widgets": [
                {"kind": "bulletin", "widget_id": "16095492", "room_id": "2793793", "title": "索引①"},
                {"kind": "notes", "widget_id": "17565710", "room_id": "2793793", "title": "尚子的房间"},
            ],
        }
    ],
    "noteEntries": [
        {
            "noteId": "111",
            "widgetId": "17565710",
            "title": "文章一",
            "date": "2016-01-01 00:00:00",
            "commentCount": 2,
            "url": "https://site.douban.com/211330/widget/notes/17565710/note/111/",
        }
    ],
    "photoIds": {"13432051": ["1", "2", "3"]},
    "albumTitles": {"13432051": "海报墙"},
    "videos": [],
    "forumTopics": {"13466509": [["58596553", "【小站论坛开放】"]]},
}


class TestLoadExisting:
    def test_restores_bulletins(self, cfg) -> None:
        _seed_data(
            cfg,
            bulletins={"16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML)},
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert "16095492" in ctx.bulletins
            assert ctx.bulletins["16095492"].title == "索引①"

    def test_restores_structure(self, cfg) -> None:
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert ctx.structure.meta["name"] == "兔子山的小站"
            assert len(ctx.structure.rooms) == 1
            assert ctx.structure.rooms[0].is_home is True
            assert len(ctx.structure.rooms[0].widgets) == 2
            assert ctx.structure.rooms[0].widgets[0].kind == "bulletin"

    def test_restores_note_entries(self, cfg) -> None:
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert len(ctx.structure.note_entries) == 1
            entry = ctx.structure.note_entries[0]
            assert entry.note_id == "111"
            assert entry.comment_count == 2
            assert ctx.structure.note_count == 1

    def test_restores_photo_ids_and_album_titles(self, cfg) -> None:
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert ctx.structure.photo_ids == {"13432051": ["1", "2", "3"]}
            assert ctx.structure.album_titles["13432051"] == "海报墙"
            assert ctx.structure.photo_count == 3

    def test_restores_forum_topics(self, cfg) -> None:
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert ctx.structure.forum_topics["13466509"] == [("58596553", "【小站论坛开放】")]

    def test_missing_files_are_safe(self, cfg) -> None:
        ensure_dirs(cfg)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert ctx.notes == {}
            assert ctx.bulletins == {}
            assert ctx.structure.note_entries == []

    def test_failed_note_refresh_preserves_archived_body(self, cfg, monkeypatch) -> None:
        from scraper.cli import stage_notes
        from scraper.parsers import NoteListEntry
        from scraper.resolver import ResolvedPage

        archived = Note(
            note_id="111",
            widget_id="17565710",
            title="已有标题",
            content_html="<p>保留正文</p>",
            comments=[Comment(author="a", date="d", content_html="<p>保留评论</p>")],
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.notes["111"] = archived
            ctx.structure.note_entries = [
                NoteListEntry("111", "17565710", "新标题", "date", 1, "https://x/111")
            ]
            monkeypatch.setattr(
                ctx.resolver,
                "resolve",
                lambda url, **kwargs: ResolvedPage(
                    url=url,
                    status=SourceStatus(
                        availability=Availability.UNAVAILABLE, retryable=True
                    ),
                ),
            )
            stage_notes(ctx, show_progress=False, force=True)
            ctx.save_data()

        saved = json.loads((cfg.data_dir / "notes.json").read_text(encoding="utf-8"))["111"]
        assert saved["content_html"] == "<p>保留正文</p>"
        assert len(saved["comments"]) == 1
        assert saved["status"]["availability"] == "unavailable"

    def test_failed_album_refresh_preserves_existing_photo_list(self, cfg, monkeypatch) -> None:
        from scraper.cli import stage_albums
        from scraper.resolver import ResolvedPage

        old_album = Album(album_id="A1", title="旧相册", source_url="https://x/A1")
        old_album.photos = [PhotoMeta(photo_id="P1", album_id="A1", caption="保留照片")]
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.albums["A1"] = old_album
            ctx.structure.photo_ids = {"A1": []}
            monkeypatch.setattr(
                ctx.resolver,
                "resolve",
                lambda url, **kwargs: ResolvedPage(
                    url=url,
                    status=SourceStatus(
                        availability=Availability.UNAVAILABLE, retryable=True
                    ),
                ),
            )
            stage_albums(ctx, show_progress=False, force=True)
            assert [photo.photo_id for photo in ctx.albums["A1"].photos] == ["P1"]
            assert ctx.progress.status_of("album:A1") == "failed"

    def test_failed_external_refresh_preserves_existing_body(self, cfg, monkeypatch) -> None:
        from scraper.cli import stage_main
        from scraper.resolver import ResolvedPage

        old_page = ExternalPage(
            page_id="topic-1", url="https://www.douban.com/topic/1/",
            content_html="<p>保留站外正文</p>",
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.external["topic-1"] = old_page
            ctx.index_groups = [
                IndexGroup("group", entries=[IndexEntry("topic", old_page.url)])
            ]
            monkeypatch.setattr(
                ctx.resolver,
                "resolve",
                lambda url, **kwargs: ResolvedPage(
                    url=url,
                    status=SourceStatus(
                        availability=Availability.UNAVAILABLE, retryable=True
                    ),
                ),
            )
            stage_main(ctx, show_progress=False, force=True)
            assert ctx.external["topic-1"].content_html == "<p>保留站外正文</p>"
            assert ctx.progress.status_of("main:topic-1") == "failed"

    def test_video_refresh_keeps_existing_local_thumbnail(self, cfg) -> None:
        from scraper.cli import stage_videos

        old = Video(video_id="V1", widget_id="W1", local_thumb="/media/videos/V1.jpg")
        fresh = Video(video_id="V1", widget_id="W1")
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.videos = [old]
            ctx.structure.videos = [fresh]
            stage_videos(ctx, show_progress=False, force=True)
            assert ctx.videos[0].local_thumb == "/media/videos/V1.jpg"

    def test_missing_bulletin_container_is_retryable_not_done(self, cfg, monkeypatch) -> None:
        from scraper.cli import stage_bulletins
        from scraper.resolver import ResolvedPage

        other_bulletin = (
            '<div id="bulletin-1"><h2>其它</h2><div id="link-report">'
            "其它公告正文</div></div>"
            '<div id="bulletin-2"><h2>第二条</h2><div id="link-report">'
            "第二条正文</div></div>"
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.structure.rooms = [
                Room(
                    room_id="R1",
                    widgets=[Widget("bulletin", "99999999", room_id="R1", title="目标")],
                )
            ]
            monkeypatch.setattr(
                ctx.resolver,
                "resolve",
                lambda url, **kwargs: ResolvedPage(
                    url=url,
                    html=other_bulletin,
                    status=SourceStatus(availability=Availability.OK),
                ),
            )
            stage_bulletins(ctx, show_progress=False, force=True)
            assert ctx.progress.status_of("bulletin:99999999") == "failed"
            assert "99999999" not in ctx.bulletins


class TestAlbumLocalRefreshedFromDisk:
    """回归：``photo.local`` 记的是磁盘事实，渲染前必须重新推导。

    图片可能在上一次相册阶段之后才落盘（例如只跑了 ``--stages photos``），
    而 ``load_existing`` 发生在全部抓取阶段之前，读到的必然是运行前的旧值。
    此时 ``data/albums.json`` 里留的还是空路径，直接渲染会把整页报成
    「N 张图片未能归档」，而文件其实都在。
    """

    def _render(self, cfg) -> str:
        """跑一遍真正的渲染入口（``emit`` 走的就是它）。"""
        from scraper.cli import generate_site

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            generate_site(ctx)
            photos = ctx.albums["13431474"].photos
        return (cfg.albums_dir / "13431474.md").read_text(encoding="utf-8"), photos

    def test_local_filled_from_disk(self, cfg) -> None:
        _seed_data(
            cfg,
            albums={"13431474": _album_payload("13431474", "1957277283", "1959844738")},
        )
        _write_album_image(cfg, "13431474", "1957277283")

        text, photos = self._render(cfg)
        assert photos[0].local == "/media/albums/13431474/1957277283.webp"
        assert photos[1].local == ""
        # 已归档的那张出图，未归档的那张进缺失清单
        assert 'src="/media/albums/13431474/1957277283.webp"' in text
        assert "有 1 张图片未能归档" in text

    def test_local_cleared_when_file_missing(self, cfg) -> None:
        """产物里记着路径、磁盘上却没有文件，必须清空，否则渲染出死链。"""
        payload = _album_payload("13431474", "1957277283")
        payload["photos"][0]["local"] = "/media/albums/13431474/1957277283.webp"
        _seed_data(cfg, albums={"13431474": payload})

        text, photos = self._render(cfg)
        assert photos[0].local == ""
        assert "未能归档" in text

    def test_suffix_taken_from_disk_not_from_thumb_url(self, cfg) -> None:
        """落盘后缀取自大图，未必等于列表页缩略图的后缀，不能按 URL 反推。"""
        _seed_data(cfg, albums={"13431474": _album_payload("13431474", "1957277283")})
        _write_album_image(cfg, "13431474", "1957277283", suffix=".jpg")

        text, photos = self._render(cfg)
        assert photos[0].local.endswith("1957277283.jpg")
        assert 'src="/media/albums/13431474/1957277283.jpg"' in text


def _unavailable_payload(url: str, availability: Availability, **kwargs) -> dict:
    from dataclasses import asdict

    from scraper.resolver import UnavailableRecord

    return asdict(UnavailableRecord(url=url, availability=availability, **kwargs))


def _progress_item(
    key: str, *, stage: str, detail: str = "原站不可访问", url: str = ""
) -> dict:
    item = {
        "stage": stage,
        "status": "unavailable",
        "attempts": 1,
        "updatedAt": "2026-09-14T11:50:44+08:00",
        "detail": detail,
        "meta": {"url": url} if url else {},
    }
    return dict(item, key=key)


def _seed_progress(cfg, *items: dict) -> None:
    from scraper.progress import PARSER_REVISION

    write_json(
        cfg.progress_path,
        {
            "version": 3,
            "parserRevision": PARSER_REVISION,
            "items": {item["key"]: item for item in items},
        },
    )


class TestUnavailableReport:
    """回归：``data/unavailable.md`` 曾经永远是空的。

    清单原本只取「本次运行抓失败的页面」，可失败条目在进度里已是终态、
    后续运行一律跳过它；``emit`` 更是一个请求都不发。于是每次重新生成
    都把清单清空成「全部内容均已成功归档」，而进度里明明还躺着十几条
    抓不到的条目，清单文件也随之被覆盖成空。
    """

    def _render(self, cfg) -> tuple[str, list]:
        from scraper.cli import generate_site

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            generate_site(ctx)
            records = list(ctx.unavailable)
        return (cfg.data_dir / "unavailable.md").read_text(encoding="utf-8"), records

    def test_progress_item_with_url_listed(self, cfg) -> None:
        _seed_data(cfg)
        _seed_progress(
            cfg,
            _progress_item(
                "photo:13432051:9",
                stage="photos",
                detail="未找到大图",
                url="https://site.douban.com/211330/widget/photos/13432051/photo/9/",
            ),
        )

        text, records = self._render(cfg)
        assert "widget/photos/13432051/photo/9/" in text
        assert "未找到大图" in text
        assert "| 照片 |" in text
        assert len(records) == 1

    def test_legacy_progress_item_url_derived_from_structure(self, cfg) -> None:
        """改动之前落盘的进度条目只有内部键，地址要能按结构还原出来。"""
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        _seed_progress(cfg, _progress_item("note:111", stage="notes"))

        text, _ = self._render(cfg)
        assert "widget/notes/17565710/note/111/" in text
        assert "日记" in text

    def test_records_survive_offline_emit(self, cfg) -> None:
        """已补足的条目必须跨运行留存，否则 ``emit`` 一次就抹掉历史。"""
        _seed_data(cfg, structure=STRUCTURE_PAYLOAD)
        write_json(
            cfg.data_dir / "unavailable.json",
            [
                _unavailable_payload(
                    "https://www.douban.com/note/1/",
                    Availability.ARCHIVED,
                    http_status=403,
                    detail="已用 archive.org 快照补足",
                    wayback_url="https://web.archive.org/web/2020/http://x/",
                )
            ],
        )

        text, records = self._render(cfg)
        assert "已补足" in text
        assert "web.archive.org" in text

        written = json.loads((cfg.data_dir / "unavailable.json").read_text(encoding="utf-8"))
        assert len(written) == 1
        assert len(records) == 1

    def test_recovered_page_dropped(self, cfg) -> None:
        """本次运行已成功取回的页面，旧记录要撤掉，否则清单永远只增不减。"""
        url = "https://site.douban.com/211330/widget/photos/13432051/photo/9/"
        _seed_data(cfg)
        write_json(
            cfg.data_dir / "unavailable.json",
            [_unavailable_payload(url, Availability.UNAVAILABLE, detail="原站不可访问")],
        )

        from scraper.cli import generate_site

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            ctx.resolver.resolved_ok.add(url)  # 本次运行把它抓回来了
            generate_site(ctx)

        text = (cfg.data_dir / "unavailable.md").read_text(encoding="utf-8")
        assert "photo/9/" not in text
        assert "全部内容均已成功归档" in text

    def test_record_wins_over_progress_row(self, cfg) -> None:
        """同一页面既有明细记录又有进度条目时只列一行，且保留明细。"""
        url = "https://site.douban.com/211330/widget/photos/13432051/photo/9/"
        _seed_data(cfg)
        write_json(
            cfg.data_dir / "unavailable.json",
            [
                _unavailable_payload(
                    url, Availability.UNAVAILABLE, http_status=404, detail="源站返回 HTTP 404"
                )
            ],
        )
        _seed_progress(cfg, _progress_item("photo:13432051:9", stage="photos", url=url))

        text, records = self._render(cfg)
        assert text.count(url) == 1
        assert "404" in text
        assert len(records) == 1


class _Response404:
    """一个恒定 404 的响应（curl_cffi 响应的最小替身）。"""

    status_code = 404
    content = b""
    headers = {"Content-Type": "text/html; charset=utf-8"}


class _Session404:
    """恒定返回 404 的会话替身；不用它就不会有任何请求。"""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.trust_env = False
        self.calls: list[str] = []

    def get(self, url: str, headers: dict[str, str] | None = None, **_kwargs: object):
        self.calls.append(url)
        return _Response404()

    def close(self) -> None:
        pass


class _SequenceSession:
    """按顺序返回给定响应码的会话替身。"""

    def __init__(self, statuses: list[int]) -> None:
        self.headers: dict[str, str] = {}
        self.trust_env = False
        self.calls: list[str] = []
        self._statuses = list(statuses)

    def get(self, url: str, headers: dict[str, str] | None = None, **_kwargs: object):
        self.calls.append(url)
        index = min(len(self.calls), len(self._statuses)) - 1
        return _Response404() if self._statuses[index] == 404 else _Response200()

    def close(self) -> None:
        pass


class _Response200:
    status_code = 200
    content = b"<html><body><div class='phoview'></div></body></html>"
    headers = {"Content-Type": "text/html; charset=utf-8"}


class TestOfflineMissNotRecorded:
    """离线模式下的缓存未命中不是"源站不可得"的证据。

    ``--offline`` 这一轮根本没发过请求，无从判断页面还在不在。若照记，
    ``refresh_unavailable()`` 就会把它写进 ``data/unavailable.md``，说成
    "原站不可访问"——和 ``ProgressStore`` 在离线模式只读是同一个理由。
    状态本身仍返回 UNAVAILABLE，页面照旧按占位块渲染。
    """

    def test_status_unavailable_but_no_record(self, cfg) -> None:
        import dataclasses

        from scraper.http_client import Fetcher
        from scraper.resolver import PageResolver

        offline = dataclasses.replace(cfg, offline=True)
        resolver = PageResolver(Fetcher(offline), cfg=offline)
        page = resolver.resolve(
            "https://site.douban.com/211330/widget/notes/17565710/note/1/", context="日记"
        )

        assert page.status.availability == Availability.UNAVAILABLE
        assert "离线" in page.status.detail
        assert resolver.unavailable == []

    def test_online_failure_still_recorded(self, cfg) -> None:
        """对照组：404 落在**可信**域名上时仍是确定性结论，照旧进清单。"""
        import dataclasses

        from scraper.http_client import Fetcher
        from scraper.resolver import PageResolver

        trusted = dataclasses.replace(cfg, untrusted_404_hosts=())
        session = _Session404()
        resolver = PageResolver(Fetcher(trusted, session=session), cfg=trusted)
        resolver.resolve("https://site.douban.com/211330/widget/notes/17565710/note/1/", context="日记")

        assert [record.url for record in resolver.unavailable] == [
            "https://site.douban.com/211330/widget/notes/17565710/note/1/"
        ]
        # 也不该有"确认请求"——免检名单之外不做第二次请求
        assert len(session.calls) == 1


class TestTransientMissingIsRetryable:
    """小站 widget 的间歇性 404 不能固化成"内容不存在"。

    实测：同一个照片页 URL 会间歇性返回通用 404 页，几分钟后再请求就是 200。
    归档一旦判定"不存在"就不再回头看，所以这类 404 要先**确认一次**再下结论；
    确认后仍是 404 的，标成"可重试"（进度记 FAILED，下次同步重试），
    并且**不进**不可访问清单——清单要的是确认拿不到的内容，不是源站的抖动。
    """

    URL = "https://site.douban.com/211330/widget/photos/13431950/photo/2325379542/"

    def test_confirmation_recovers_page(self, cfg) -> None:
        """第一次 404、确认时 200：直接采信第二次的结果。"""
        from scraper.http_client import Fetcher
        from scraper.resolver import PageResolver

        session = _SequenceSession([404, 200])
        resolver = PageResolver(Fetcher(cfg, session=session), cfg=cfg)
        page = resolver.resolve(self.URL, context="照片")

        assert page.has_content
        assert page.status.availability == Availability.OK
        assert resolver.unavailable == []
        assert len(session.calls) == 2

    def test_persistent_404_marked_retryable(self, cfg) -> None:
        """确认后仍是 404：结论照下，但要标明"这个结论不可信"。"""
        from scraper.http_client import Fetcher
        from scraper.resolver import PageResolver

        resolver = PageResolver(Fetcher(cfg, session=_Session404()), cfg=cfg)
        page = resolver.resolve(self.URL, context="照片")

        assert not page.has_content
        assert page.status.availability == Availability.UNAVAILABLE
        assert page.status.retryable is True
        assert resolver.unavailable == []

    def test_retryable_failure_records_failed_not_unavailable(self, cfg) -> None:
        """进度侧：可重试的失败记 FAILED（下次同步会自动重试）。

        FAILED 不是终态，``ProgressStore.pending`` 默认就会把它筛出来重跑；
        记成 UNAVAILABLE 则再也不会回头看一眼。
        """
        from scraper.cli import record_source_failure
        from scraper.progress import ItemStatus as Status
        from scraper.progress import ProgressStore

        store = ProgressStore(cfg=cfg)
        record_source_failure(
            store,
            "photo:13431950:2325379542",
            SourceStatus(availability=Availability.UNAVAILABLE, retryable=True),
            stage="photos",
            url=self.URL,
        )

        assert store.status_of("photo:13431950:2325379542") == str(Status.FAILED)
        assert store.unavailable() == []
        assert store.pending(["photo:13431950:2325379542"]) == ["photo:13431950:2325379542"]

    def test_untrusted_404_never_reaches_unavailable_json(self, cfg) -> None:
        """端到端：resolve → refresh_unavailable，清单里不出现抖动页面。"""
        from scraper.http_client import Fetcher
        from scraper.resolver import PageResolver

        resolver = PageResolver(Fetcher(cfg, session=_Session404()), cfg=cfg)
        resolver.resolve(self.URL, context="照片")

        ctx = SyncContext(cfg)
        ctx.resolver = resolver
        ctx.refresh_unavailable()
        assert ctx.unavailable == []


class TestNoEmitStillPersists:
    """``--no-emit`` 只表示"不渲染站点"，抓到的东西必须照样落盘。

    进度一旦记为 done，下次运行就会跳过这些条目——解析结果若没写进
    ``data/``，就再没有第二次机会，站点会永远缺这批内容。
    """

    def test_products_written_and_index_not_wiped(self, cfg) -> None:
        _seed_data(
            cfg,
            bulletins={"16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML)},
        )

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            ctx.persist_products()

        index = json.loads((cfg.data_dir / "index.json").read_text(encoding="utf-8"))
        assert [group["title"] for group in index] == ["聲之形", "轻音！系列"]
        assert (cfg.data_dir / "notes.json").exists()
        assert (cfg.data_dir / "unavailable.json").exists()


class TestStructureFullyRestored:
    """回归：``build_manifest`` 会把结构原样写回 ``structure.json``。

    因此漏还原哪个字段，跑一次 ``emit`` 就等于把它从磁盘上删掉——
    ``bulletins`` / ``videos`` / 房间状态都曾被这样抹掉过。
    """

    def test_bulletins_videos_and_room_status_survive_roundtrip(self, cfg) -> None:
        rooms = [dict(room) for room in STRUCTURE_PAYLOAD["rooms"]]
        rooms[0]["status"] = SourceStatus(availability=Availability.OK, http_status=200).to_dict()
        payload = dict(
            STRUCTURE_PAYLOAD,
            rooms=rooms,
            bulletins=[_bulletin_payload("16095492", "索引①", INDEX_HTML)],
            videos=[_video_payload("1")],
        )
        _seed_data(cfg, structure=payload)

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert len(ctx.structure.bulletins) == 1
            assert len(ctx.structure.videos) == 1
            assert ctx.structure.videos[0].title == "视频一"
            assert ctx.structure.rooms[0].status.availability == Availability.OK

            ctx.build_manifest()
            written = json.loads((cfg.data_dir / "structure.json").read_text(encoding="utf-8"))
            assert len(written["bulletins"]) == 1
            assert len(written["videos"]) == 1
            assert written["rooms"][0]["status"]["availability"] == "ok"


class TestIndexGroupsRebuiltFromRestoredBulletins:
    """核心回归：公告栏阶段被跳过后，索引分组仍必须能重建。"""

    def test_index_groups_from_restored_bulletin(self, cfg) -> None:
        _seed_data(
            cfg,
            bulletins={"16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML)},
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            groups = ctx.build_index_groups()
            assert [g.title for g in groups] == ["聲之形", "轻音！系列"]
            assert len(groups[0].entries) == 2
            assert groups[0].entries[0].note_id == "111"

    def test_non_index_bulletin_ignored(self, cfg) -> None:
        _seed_data(
            cfg,
            bulletins={
                "13430830": _bulletin_payload("13430830", "About PPK", "山田尚子简介"),
                "16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML),
            },
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            groups = ctx.build_index_groups()
            # 只解析标题含"索引"的公告栏
            assert [g.title for g in groups] == ["聲之形", "轻音！系列"]

    def test_duplicate_group_titles_deduped(self, cfg) -> None:
        """同一分组出现在多条公告里时只保留一次。"""
        _seed_data(
            cfg,
            bulletins={
                "16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML),
                "17754656": _bulletin_payload("17754656", "索引②", INDEX_HTML),
            },
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            groups = ctx.build_index_groups()
            titles = [g.title for g in groups]
            assert len(titles) == len(set(titles))
            assert titles == ["聲之形", "轻音！系列"]

    def test_no_bulletins_yields_no_groups(self, cfg) -> None:
        ensure_dirs(cfg)
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            assert ctx.build_index_groups() == []


class TestManifestRoundTrip:
    def test_manifest_written_and_readable(self, cfg) -> None:
        _seed_data(
            cfg,
            bulletins={"16095492": _bulletin_payload("16095492", "索引①", INDEX_HTML)},
            structure=STRUCTURE_PAYLOAD,
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            ctx.build_index_groups()
            manifest = ctx.build_manifest()
            ctx.emitter.emit_manifest(manifest)

        payload = json.loads(cfg.manifest_path.read_text(encoding="utf-8"))
        assert payload["counts"]["bulletins"] == 1
        assert payload["counts"]["photos"] == 0
        assert len(payload["index"]) == 2
        assert payload["siteMeta"]["name"] == "兔子山的小站"


class TestMergeById:
    """恢复的既有数据与本次抓取的数据必须按 ID 合并，而不是叠加。"""

    def test_new_items_appended(self) -> None:
        target = [{"id": "a"}]
        merge_by(target, [{"id": "b"}], lambda x: x["id"])
        assert [x["id"] for x in target] == ["a", "b"]

    def test_existing_items_replaced_not_duplicated(self) -> None:
        """核心回归：广播动态 20 条曾被叠加成 40 条。"""
        target = [{"id": str(i), "v": 1} for i in range(20)]
        merge_by(target, [{"id": str(i), "v": 2} for i in range(20)], lambda x: x["id"])
        assert len(target) == 20
        assert all(x["v"] == 2 for x in target)

    def test_partial_overlap(self) -> None:
        target = [{"id": "a"}, {"id": "b"}]
        merge_by(target, [{"id": "b"}, {"id": "c"}], lambda x: x["id"])
        assert [x["id"] for x in target] == ["a", "b", "c"]
        assert len(target) == 3

    def test_empty_incoming(self) -> None:
        target = [{"id": "a"}]
        merge_by(target, [], lambda x: x["id"])
        assert len(target) == 1

    def test_empty_target(self) -> None:
        target: list = []
        merge_by(target, [{"id": "a"}, {"id": "a"}], lambda x: x["id"])
        assert len(target) == 1

    def test_heals_preexisting_duplicates(self) -> None:
        """早期版本可能已把重复数据写进产物，合并时必须顺手修好。"""
        target = [{"id": "a", "v": 1}, {"id": "b", "v": 1}, {"id": "a", "v": 2}]
        merge_by(target, [], lambda x: x["id"])
        assert [x["id"] for x in target] == ["a", "b"]
        assert target[0]["v"] == 2

    def test_heals_duplicates_and_merges_new(self) -> None:
        target = [{"id": "a", "v": 1}, {"id": "a", "v": 2}]
        merge_by(target, [{"id": "b", "v": 3}], lambda x: x["id"])
        assert [x["id"] for x in target] == ["a", "b"]
        assert len(target) == 2

    def test_preserves_first_seen_order(self) -> None:
        target = [{"id": "c"}, {"id": "a"}]
        merge_by(target, [{"id": "b"}, {"id": "a"}], lambda x: x["id"])
        assert [x["id"] for x in target] == ["c", "a", "b"]



class TestOfflineProgressIsReadonly:
    """``--offline`` 必须让进度库进入只读模式。

    离线时的"缓存未命中"只是本地没有这份数据，并不代表源站不可得。
    若照常落盘，一次离线运行会把整站标成"原站不可访问"，
    既让后续 ``--recheck-unavailable`` 的语义失真，也让不可访问清单失去意义。
    """

    def test_sync_context_offline_is_readonly(self, cfg) -> None:
        import dataclasses

        offline_cfg = dataclasses.replace(cfg, offline=True)
        with SyncContext(offline_cfg, use_archive=False) as ctx:
            assert ctx.progress.readonly

    def test_sync_context_online_is_writable(self, cfg) -> None:
        with SyncContext(cfg, use_archive=False) as ctx:
            assert not ctx.progress.readonly

    def test_offline_run_does_not_touch_progress_file(self, cfg) -> None:
        import dataclasses

        offline_cfg = dataclasses.replace(cfg, offline=True)
        with SyncContext(offline_cfg, use_archive=False) as ctx:
            ctx.progress.mark_unavailable("note:1", "离线无缓存", stage="notes")
            ctx.progress.save(force=True)
        assert not cfg.progress_path.exists()


class TestCommentsSurviveRoundTrip:
    """评论必须能被 ``load_existing()`` 还原。

    历史缺陷：``_note_from_dict`` 还原了 images 却漏了 comments，
    ``_discussion_from_dict`` 还额外漏了 ``comment_id``。
    后果是"日记已 done、本次被跳过"时评论被静默清空 ——
    而评论正是靠 comment_id 去重的。
    """

    COMMENT = {
        "author": "贫僧读物理",
        "date": "2019-01-24 15:22:41",
        "content_html": "<p>希望兔子山能翻译一些利兹与青鸟的文章==</p>",
        "avatar_url": "https://img9.doubanio.com/icon/u151409267-5.jpg",
        "comment_id": "57095888",
    }

    def test_note_comments_restored(self, cfg) -> None:
        note = Note(note_id="673585518", widget_id="17565710", title="谈谈丽兹")
        note.comments = [Comment(**self.COMMENT)]
        _seed_data(cfg, notes={"673585518": note.to_dict()})

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()

        restored = ctx.notes["673585518"]
        assert len(restored.comments) == 1
        assert restored.comments[0].comment_id == "57095888"
        assert restored.comments[0].author == "贫僧读物理"

    def test_discussion_comments_restored_with_id(self, cfg) -> None:
        discussion = Discussion(discussion_id="1", forum_id="2", title="留言板")
        discussion.comments = [Comment(**self.COMMENT)]
        _seed_data(cfg)
        write_json(cfg.data_dir / "forum.json", [discussion.to_dict()])

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()

        restored = ctx.discussions[0]
        assert len(restored.comments) == 1
        assert restored.comments[0].comment_id == "57095888"

    def test_comment_count_survives_manifest(self, cfg) -> None:
        note = Note(note_id="673585518", widget_id="17565710", title="谈谈丽兹")
        note.comments = [Comment(**self.COMMENT)]
        _seed_data(cfg, notes={"673585518": note.to_dict()})

        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
            manifest = ctx.build_manifest()

        assert manifest["counts"]["comments"] == 1

    def test_missing_comments_field_is_safe(self, cfg) -> None:
        """旧产物没有 comments 字段时不能报错。"""
        _seed_data(
            cfg,
            notes={
                "1": {
                    "note_id": "1",
                    "widget_id": "2",
                    "title": "旧数据",
                    "images": [],
                }
            },
        )
        with SyncContext(cfg, use_archive=False) as ctx:
            ctx.load_existing()
        assert ctx.notes["1"].comments == []
