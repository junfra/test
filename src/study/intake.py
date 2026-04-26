"""Source intake system for native/web_search/file/pasted_text sources.

All functions receive ``subject_root: pathlib.Path`` — no bare root paths.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from .models import ProgressState, SourceReference


def _save_progress(subject_root: Path, state: ProgressState) -> None:
    """Persist ``ProgressState`` to progress_state.json."""
    (subject_root / "progress_state.json").write_text(state.model_dump_json(indent=2))


def add_sources(subject_root: Path, sources: list[SourceReference | dict[str, Any]]) -> None:
    """Store each source as a ``.json`` file in ``subject_root/source_reference_data/``.

    Parameters
    ----------
    subject_root : Path
        Root of the study subject directory (e.g. `<workspace>/subjects/<id>`).
    sources : list[SourceReference | dict]
        Each element is either a fully-formed ``SourceReference`` or a plain dict that will be
        coerced via :meth:`~SourceReference.model_validate`.

    Updates ``progress_state.json`` in *subject_root* — increments the manifest count by
    the number of sources added.
    """
    ref_dir = subject_root / "source_reference_data"
    ref_dir.mkdir(parents=True, exist_ok=True)

    validated: list[SourceReference] = []
    for item in sources:
        if isinstance(item, dict):
            validated.append(SourceReference.model_validate(item))
        else:
            validated.append(item)

    for i, src in enumerate(validated):
        (ref_dir / f"source_{i:04d}.json").write_text(src.model_dump_json())

    # Update manifest count via load+save round-trip.
    state = ProgressState.model_validate(json.loads((subject_root / "progress_state.json").read_text()))
    state.source_manifest_count += len(validated)
    # Side-effect: log each source addition
    import hashlib as _hashlib
    from .logging import log_session_event
    for i, src in enumerate(validated):
        content_hash = _hashlib.sha256(src.content.encode()).hexdigest()[:16]
        log_session_event(
            subject_root, "source_added",
            {"kind": src.kind, "content_hash": content_hash},
        )
    _save_progress(subject_root, state)


def load_source_data(subject_root: Path) -> list[SourceReference]:
    """Load all ``.json`` files from *source_reference_data* and return them as :class:`SourceReference` objects.

    Files are loaded in **sorted** filename order for deterministic results.
    Returns an empty list when the directory does not exist or contains no JSON files.
    """
    ref_dir = subject_root / "source_reference_data"
    if not ref_dir.is_dir():
        return []

    refs: list[SourceReference] = []
    for json_file in sorted(ref_dir.glob("*.json")):
        data = json.loads(json_file.read_text())
        refs.append(SourceReference.model_validate(data))
    return refs


__all__ = ["add_sources", "load_source_data"]
