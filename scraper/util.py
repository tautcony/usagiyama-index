"""通用工具：原子写入、JSON 读写、哈希与时间戳。

原子写入是断点续接可靠性的基础：任何时刻进程被中断，
磁盘上的状态文件要么是旧版本、要么是新版本，不会是半个文件。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """本地时区的 ISO 时间戳（秒精度）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha1_of(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha1(data).hexdigest()


def url_cache_key(url: str) -> str:
    """URL → 缓存文件名（sha1）。"""
    return sha1_of(url)


def files_equal(a: Path, b: Path) -> bool:
    """两个文件是否字节相同。先比大小早退，免得为大文件白读一遍。"""
    if a.stat().st_size != b.stat().st_size:
        return False
    return sha1_of(a.read_bytes()) == sha1_of(b.read_bytes())


def _atomic_replace(tmp: Path, target: Path) -> None:
    os.replace(tmp, target)


def _stage_file(path: Path, tmp_dir: Path | None) -> tuple[int, Path]:
    """在临时位置创建一个待写入的文件。

    ``tmp_dir`` 存在的意义见 :func:`atomic_write_bytes`。
    """
    if tmp_dir is not None:
        tmp_dir.mkdir(parents=True, exist_ok=True)
        directory = str(tmp_dir)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        directory = str(path.parent)
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    return fd, Path(tmp_name)


def atomic_write_text(path: Path, text: str, *, tmp_dir: Path | None = None) -> None:
    """原子写入文本文件（同目录临时文件 + os.replace）。"""
    fd, tmp = _stage_file(path, tmp_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _atomic_replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_bytes(path: Path, data: bytes, *, tmp_dir: Path | None = None) -> None:
    """原子写入二进制文件。

    ``tmp_dir`` 用来把临时文件放到**目标目录之外**。这不是洁癖：Vite 的
    ``copyDir`` 是"先 ``readdirSync`` 取名字列表、再逐个 ``statSync`` +
    ``copyFileSync``"，如果临时文件恰好落在 ``public/`` 里，就会被它列进名单，
    而随后的 ``os.replace`` 会把该名字移走 —— 于是构建随机地以
    ``ENOENT ... copyfile`` 失败。把临时文件挪出 ``public/`` 就从根上消除了这个竞态。

    ``tmp_dir`` 必须与目标在**同一文件系统**上（``os.replace`` 不支持跨设备），
    所以调用方应选同一个仓库内的目录，例如 ``<docs>/.vitepress/.tmp``。
    """
    fd, tmp = _stage_file(path, tmp_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _atomic_replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def read_json(path: Path, default: Any = None) -> Any:
    """读取 JSON；文件缺失或损坏时返回 ``default``。"""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """原子写入 JSON。"""
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent) + "\n")


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def human_duration(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{seconds:.0f} 秒"
    if seconds < 3600:
        return f"{seconds / 60:.1f} 分钟"
    hours, remainder = divmod(seconds, 3600)
    return f"{hours:.0f} 小时 {remainder / 60:.0f} 分"


def truncate(text: str, width: int = 60) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def host_matches(host: str, patterns: Iterable[str]) -> bool:
    """``host`` 是否等于 ``patterns`` 中的某一项（或其子域）。

    子域也算命中：``img1.doubanio.com`` 应匹配 ``doubanio.com``。
    """
    host = (host or "").lower()
    return any(host == pattern or host.endswith("." + pattern) for pattern in patterns)
