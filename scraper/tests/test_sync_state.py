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
from scraper.models import Bulletin, Comment, Discussion, Note, SourceStatus
from scraper.util import write_json

INDEX_HTML = (
    "☆【聲之形】<br>"
    '<a href="http://site.douban.com/211330/widget/notes/1/note/111/">文章一</a><br>'
    '<a href="http://site.douban.com/211330/widget/notes/1/note/222/">文章二</a><br>'
    "☆【轻音！系列】<br>"
    '<a href="http://site.douban.com/211330/widget/notes/2/note/333/">文章三</a>'
)


def _seed_data(cfg, *, bulletins=None, notes=None, structure=None) -> None:
    ensure_dirs(cfg)
    write_json(cfg.data_dir / "bulletins.json", bulletins or {})
    write_json(cfg.data_dir / "notes.json", notes or {})
    write_json(cfg.data_dir / "albums.json", {})
    write_json(cfg.data_dir / "videos.json", [])
    write_json(cfg.data_dir / "forum.json", [])
    write_json(cfg.data_dir / "miniblog.json", [])
    if structure is not None:
        write_json(cfg.data_dir / "structure.json", structure)


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
