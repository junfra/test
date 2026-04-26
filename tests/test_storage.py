"""Tests for study.storage — state persistence via JSON/jsonl."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from study.models import ProgressState, RecallSessionEntry, RecallQuestion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="study_test_"))


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# test_save_load_progress_state
# ---------------------------------------------------------------------------

def test_save_load_progress_state():
    """Round-trip ProgressState through JSON → verify all fields survive."""
    state = ProgressState(
        subject_id="math-calculus",
        topic="integrals",
        phase="recall_adaptive",
        approval_status=True,
        draft_version_hash="abc123",
        first_pass_complete=True,
        next_recursors_cursor=42,
        weak_points=[],
        source_manifest_count=7,
    )

    d = _tmpdir()
    from study.storage import save_progress, load_progress
    save_progress(d, state)

    loaded = load_progress(d)
    assert loaded.subject_id == "math-calculus"
    assert loaded.topic == "integrals"
    assert loaded.phase == "recall_adaptive"
    assert loaded.approval_status is True
    assert loaded.draft_version_hash == "abc123"
    assert loaded.first_pass_complete is True
    assert loaded.next_recursors_cursor == 42
    assert loaded.weak_points == []
    assert loaded.source_manifest_count == 7


# ---------------------------------------------------------------------------
# test_load_progress_with_defaults
# ---------------------------------------------------------------------------

def test_load_progress_with_defaults():
    """Create state without optional fields → defaults preserved on load."""
    state = ProgressState(
        subject_id="physics-quantum",
        topic="wave-particle duality",
    )
    assert state.phase == "intake"
    assert state.approval_status is False
    assert state.weak_points == []

    d = _tmpdir()
    from study.storage import save_progress, load_progress
    save_progress(d, state)
    loaded = load_progress(d)
    assert loaded.subject_id == "physics-quantum"
    assert loaded.topic == "wave-particle duality"
    assert loaded.phase == "intake"  # default
    assert loaded.approval_status is False  # default


# ---------------------------------------------------------------------------
# test_recalls_append
# ---------------------------------------------------------------------------

def test_recalls_append():
    """Append RecallSessionEntry → read lines → verify count and content."""
    entries = [
        RecallSessionEntry(
            session_id="s1",
            questions=[RecallQuestion(id="q1", topic="topic-A", prompt="?", answer="a", score=0.9)],
            answers=["a"],
            scores=[0.9],
            outcome="pass",
            timestamp=_now_iso(),
        ),
    ]

    d = _tmpdir()
    from study.storage import append_recalls
    append_recalls(d, entries)

    jsonl_path = d / "recall_history.jsonl"
    lines = jsonl_path.read_text().strip().splitlines()
    assert len(lines) == 1

    parsed = RecallSessionEntry.model_validate(json.loads(lines[0]))
    assert parsed.session_id == "s1"
    assert parsed.outcome == "pass"


# ---------------------------------------------------------------------------
# test_append_multiple_entries
# ---------------------------------------------------------------------------

def test_append_multiple_entries():
    """Append 3 entries → file has exactly 3 lines, each parseable."""
    entries = [
        RecallSessionEntry(
            session_id="s1", questions=[], answers=None, scores=None,
            outcome="pass", timestamp=_now_iso(),
        ),
        RecallSessionEntry(
            session_id="s2", questions=[], answers=None, scores=None,
            outcome="fail", timestamp=_now_iso(),
        ),
        RecallSessionEntry(
            session_id="s3", questions=[RecallQuestion(id="q1", topic="T", prompt="?", answer=None)],
            answers=None, scores=None, outcome="partial", timestamp=_now_iso(),
        ),
    ]

    d = _tmpdir()
    from study.storage import append_recalls
    append_recalls(d, entries)

    jsonl_path = d / "recall_history.jsonl"
    lines = jsonl_path.read_text().strip().splitlines()
    assert len(lines) == 3

    for line in lines:
        RecallSessionEntry.model_validate(json.loads(line))  # no-op if valid


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
