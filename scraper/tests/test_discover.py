"""相册翻页枚举测试。

回归：相册列表页一页只放 30 张，只读第一页、或按错误的步长翻页，都会让
每个相册尾部的照片永远枚举不到——页面上表现为「明明已经归档却报缺失」，
而发现阶段则少下载这些图。
"""

from __future__ import annotations

from scraper.discover import enumerate_album_photos
from scraper.models import Availability, SourceStatus
from scraper.resolver import ResolvedPage


class _StubResolver:
    """按 URL 返回预置 HTML 的解析器替身。"""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def resolve(self, url: str, **_kwargs: object) -> ResolvedPage:
        self.calls.append(url)
        html = self.pages.get(url, "")
        return ResolvedPage(
            url=url,
            html=html,
            status=SourceStatus(
                availability=Availability.OK if html else Availability.UNAVAILABLE
            ),
        )


def _album_page(
    album_id: str,
    photo_ids: list[str],
    *,
    total_pages: int = 1,
    step: int | None = 30,
    current: int = 0,
) -> str:
    """伪造一个相册列表页：分页器页码按 ``step`` 递增。

    ``step`` 传 ``None`` 表示页面里没有可分页的链接（步长只能靠兜底常量）。
    """
    photos = "".join(
        f'<a class="album_photo" href="/211330/widget/photos/{album_id}/photo/{pid}/"'
        f' title="图 {pid}"><img src="https://img3.doubanio.com/view/photo/thumb/'
        f'public/p{pid}.webp"></a>'
        for pid in photo_ids
    )
    links = ""
    if step is not None:
        links = "".join(
            f'<a href="/211330/widget/photos/{album_id}/?start={index * step}">{index + 1}</a>'
            for index in range(total_pages)
            if index != current
        )
    return (
        f'<html data-total-page="{total_pages}"><body>'
        f'<div class="paginator">{links}</div>{photos}</body></html>'
    )


def _pages(cfg, album_id: str, pages: list[str], *, step: int = 30) -> dict[str, str]:
    return {
        cfg.photos_list_url(album_id, index * step): html
        for index, html in enumerate(pages)
    }


class TestEnumerateAlbumPhotos:
    def test_collects_every_page(self, cfg) -> None:
        """核心回归：第 2 页之后的照片曾经整批丢失。"""
        album_id = "13431950"
        pages = _pages(
            cfg,
            album_id,
            [
                _album_page(album_id, [f"1{i:02d}" for i in range(30)], total_pages=3),
                _album_page(album_id, [f"2{i:02d}" for i in range(30)], total_pages=3, current=1),
                _album_page(album_id, [f"3{i:02d}" for i in range(9)], total_pages=3, current=2),
            ],
        )
        resolver = _StubResolver(pages)

        photos = enumerate_album_photos(resolver, album_id, cfg)

        assert len(photos) == 69
        assert [p.photo_id for p in photos] == [f"1{i:02d}" for i in range(30)] + [
            f"2{i:02d}" for i in range(30)
        ] + [f"3{i:02d}" for i in range(9)]
        # 首页只抓一次，后续按站点自己的步长翻页
        assert resolver.calls == [
            cfg.photos_list_url(album_id, 0),
            cfg.photos_list_url(album_id, 30),
            cfg.photos_list_url(album_id, 60),
        ]

    def test_reuses_first_page_html(self, cfg) -> None:
        """调用方已抓到第一页时不应重复请求。"""
        album_id = "13431950"
        first = _album_page(album_id, ["1", "2"], total_pages=2)
        resolver = _StubResolver(
            _pages(
                cfg,
                album_id,
                [first, _album_page(album_id, ["3"], total_pages=2, current=1)],
            )
        )

        photos = enumerate_album_photos(resolver, album_id, cfg, first_html=first)

        assert [p.photo_id for p in photos] == ["1", "2", "3"]
        assert cfg.photos_list_url(album_id, 0) not in resolver.calls

    def test_covers_album_tail(self, cfg) -> None:
        """13431950 的真实情形：每页 30 张、共 114 张、4 页。

        旧实现按常量 26 翻页，只走到 start=78，尾部 6 张永远抓不到。
        """
        album_id = "13431950"
        page_ids = [
            [f"{page}{index:02d}" for index in range(30)] for page in range(3)
        ] + [[f"3{index:02d}" for index in range(24)]]
        pages = _pages(
            cfg,
            album_id,
            [
                _album_page(album_id, ids, total_pages=4, current=index)
                for index, ids in enumerate(page_ids)
            ],
        )
        resolver = _StubResolver(pages)

        photos = enumerate_album_photos(resolver, album_id, cfg)

        assert len(photos) == 114
        assert resolver.calls == [
            cfg.photos_list_url(album_id, 0),
            cfg.photos_list_url(album_id, 30),
            cfg.photos_list_url(album_id, 60),
            cfg.photos_list_url(album_id, 90),
        ]

    def test_step_taken_from_paginator_not_from_constant(self, cfg) -> None:
        """步长取自站点自己的分页链接，与常量无关。"""
        album_id = "13433748"
        step = 12
        first = _album_page(album_id, ["1"], total_pages=3, step=step)
        pages = _pages(
            cfg,
            album_id,
            [
                first,
                _album_page(album_id, ["2"], total_pages=3, step=step, current=1),
                _album_page(album_id, ["3"], total_pages=3, step=step, current=2),
            ],
            step=step,
        )
        resolver = _StubResolver(pages)

        with_cfg = enumerate_album_photos(resolver, album_id, cfg, first_html=first)

        assert [p.photo_id for p in with_cfg] == ["1", "2", "3"]
        assert resolver.calls == [
            cfg.photos_list_url(album_id, 12),
            cfg.photos_list_url(album_id, 24),
        ]

    def test_fallback_step_matches_site_page_size(self, cfg) -> None:
        """页面里没有分页链接时按常量兜底，该常量必须等于站点真实的每页条数。

        同一组 114 张、每页 30 张的数据：常量若退回 26，尾部 6 张会再次漏掉。
        """
        album_id = "13431950"
        page_ids = [
            [f"{page}{index:02d}" for index in range(30)] for page in range(3)
        ] + [[f"3{index:02d}" for index in range(24)]]
        pages = _pages(
            cfg,
            album_id,
            [
                _album_page(album_id, ids, total_pages=4, step=None)
                for ids in page_ids
            ],
        )
        resolver = _StubResolver(pages)

        photos = enumerate_album_photos(resolver, album_id, cfg)

        assert len(photos) == 114
        assert resolver.calls[-1] == cfg.photos_list_url(album_id, 90)

    def test_caption_and_thumb_kept(self, cfg) -> None:
        album_id = "13432051"
        first = _album_page(album_id, ["1957277283"])
        photos = enumerate_album_photos(
            _StubResolver(_pages(cfg, album_id, [first])), album_id, cfg, first_html=first
        )
        assert photos[0].caption == "图 1957277283"
        assert photos[0].thumb_url.endswith("p1957277283.webp")

    def test_first_page_unavailable_yields_nothing(self, cfg) -> None:
        assert enumerate_album_photos(_StubResolver({}), "13432051", cfg) == []

    def test_unavailable_later_page_keeps_earlier_photos(self, cfg) -> None:
        """中间某页抓不到时，已拿到的照片不能被丢掉。"""
        album_id = "13431950"
        first = _album_page(album_id, ["1", "2"], total_pages=3)
        resolver = _StubResolver(_pages(cfg, album_id, [first]))

        photos = enumerate_album_photos(resolver, album_id, cfg, first_html=first)

        assert [p.photo_id for p in photos] == ["1", "2"]

    def test_duplicate_ids_across_pages_deduped(self, cfg) -> None:
        """翻页窗口重叠时同一张照片只保留一次。"""
        album_id = "13431950"
        first = _album_page(album_id, ["1", "2", "3"], total_pages=2)
        second = _album_page(album_id, ["3", "4"], total_pages=2, current=1)
        pages = _pages(cfg, album_id, [first, second])
        pages[cfg.photos_list_url(album_id, 30)] = second

        photos = enumerate_album_photos(_StubResolver(pages), album_id, cfg, first_html=first)

        assert [p.photo_id for p in photos] == ["1", "2", "3", "4"]
