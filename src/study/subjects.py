"""Subject management logic (create, list, delete)."""
from __future__ import annotations

import json
from pathlib import Path

from .models import ProgressState


def _save_progress(subject_root: Path, state: ProgressState) -> None:
    """Persist ProgressState as progress_state.json in the subject directory."""
    (subject_root / "progress_state.json").write_text(state.model_dump_json(indent=2))


def create_subject(workspace_root: Path, subject_id: str, topic: str) -> Path:
    """Create a new subject directory structure and return subject_root.

    Creates::

        <workspace>/subjects/<id>/
            source_reference_data/
            session_logs/
            progress_state.json   ← initial intake state

    Returns the *subject_root* so callers can continue to write into it.
    """
    subject_root = workspace_root / "subjects" / subject_id
    subject_root.mkdir(parents=True, exist_ok=True)
    (subject_root / "source_reference_data").mkdir(exist_ok=True)
    (subject_root / "session_logs").mkdir(exist_ok=True)

    _save_progress(
        subject_root,
        ProgressState(subject_id=subject_id, topic=topic, phase="intake", approval_status=False),
    )
    return subject_root


def list_subjects(workspace_root: Path) -> list[tuple[str, str]]:
    """Return ``[(subject_id, topic), ...]`` for all subjects in workspace.

    Subjects are returned in **sorted** order by *subject_id*.
    Only directories that contain a valid ``progress_state.json`` are listed.
    """
    subjects_dir = workspace_root / "subjects"
    if not subjects_dir.is_dir():
        return []

    results: list[tuple[str, str]] = []
    for entry in sorted(subjects_dir.iterdir()):
        ps_file = entry / "progress_state.json"
        if not ps_file.exists() or not entry.is_dir():
            continue
        try:
            data = json.loads(ps_file.read_text())
            results.append((data["subject_id"], data["topic"]))
        except (json.JSONDecodeError, KeyError):
            continue  # skip corrupt entries silently

    return results


def delete_subject(subject_root: Path) -> None:
    """Remove *subject_root* directory and all its contents."""
    if subject_root.exists():
        import shutil
        shutil.rmtree(subject_root)
