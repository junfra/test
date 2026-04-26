"""State persistence via JSON (progress_state.json) and jsonl (recall_history.jsonl).

All functions receive `subject_root: pathlib.Path` — no bare root paths.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import ProgressState, RecallSessionEntry


def save_progress(subject_root: Path, state: ProgressState) -> None:
    """Save *state* to ``subject_root/progress_state.json``."""
    path = subject_root / "progress_state.json"
    path.write_text(state.model_dump_json(indent=2))


def load_progress(subject_root: Path) -> ProgressState:
    """Load *ProgressState* from ``subject_root/progress_state.json``."""
    path = subject_root / "progress_state.json"
    data = json.loads(path.read_text())
    return ProgressState.model_validate(data)


def append_recalls(subject_root: Path, entries: list[RecallSessionEntry]) -> None:
    """Append *entries* as JSON lines to ``subject_root/recall_history.jsonl``."""
    path = subject_root / "recall_history.jsonl"
    with open(path, "a") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")


__all__ = ["save_progress", "load_progress", "append_recalls"]
