"""测试夹具：把配置指向临时目录，避免污染真实产物。"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from scraper.config import CONFIG, Config


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    """全部路径指向 tmp_path 的隔离配置。"""
    root = tmp_path
    return dataclasses.replace(
        CONFIG,
        root=root,
        cache_dir=root / "state" / "cache",
        state_dir=root / "state",
        data_dir=root / "data",
        docs_dir=root / "docs",
        media_dir=root / "docs" / "public" / "media",
        fixtures_dir=Path(__file__).parent / "fixtures",
        archive_enabled=False,
        delay_min=0.0,
        delay_max=0.0,
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
