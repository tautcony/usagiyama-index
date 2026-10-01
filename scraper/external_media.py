"""Reconcile existing external image records without network access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .external_articles import extract_image_sources, parse_capture
from .media import MediaArchive, is_valid_image, with_name


def reconcile_external_media(
    captures: dict[str, dict[str, Any]], media: MediaArchive, workspace: Path
) -> dict[str, int]:
    """Apply current body filters and heal filenames even for completed items.

    Missing/unparseable raw HTML is not evidence for deletion. Only files
    explicitly removed from a parsed capture and unused by other captures are
    deleted; unrelated files are never swept from the media directory.
    """
    counts = {"filtered": 0, "renamed": 0, "deleted": 0}
    obsolete: set[Path] = set()
    root = (media.cfg.media_dir / "external-articles").resolve()

    def local_path(local: str) -> Path | None:
        if not local.startswith("/media/external-articles/"):
            return None
        path = (media.cfg.media_dir / local.removeprefix("/media/")).resolve()
        return path if path.is_relative_to(root) else None

    for url, capture in captures.items():
        selected = None
        if parse_capture(url, capture, workspace) is not None:
            selected = set(extract_image_sources(url, capture, workspace))
        for field in ("archivedImages", "imageFailures"):
            mapping = capture.get(field) or {}
            for source, local in list(mapping.items()):
                if selected is not None and source not in selected:
                    if field == "archivedImages" and (path := local_path(str(local))):
                        obsolete.add(path)
                    del mapping[source]
                    counts["filtered"] += 1
                    continue
                if field != "archivedImages":
                    continue
                path = local_path(str(local))
                if path is None:
                    continue
                # A previous interrupted rename may already have produced the
                # corrected sibling, leaving only the old URL in metadata.
                existing = media._existing_archived(path)
                if existing is not None:
                    actual = media.heal_suffix(existing)
                    corrected = with_name(str(local), actual.name)
                    if corrected != local:
                        mapping[source] = corrected
                        counts["renamed"] += 1
            if field in capture and not mapping:
                capture.pop(field)

    retained = {
        path for capture in captures.values()
        for local in (capture.get("archivedImages") or {}).values()
        if (path := local_path(str(local))) is not None
    }
    for path in obsolete - retained:
        if path.is_file() and is_valid_image(path):
            path.unlink()
            counts["deleted"] += 1
    return counts
