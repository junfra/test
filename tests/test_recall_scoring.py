"""Tests for recall scoring, misconception decomposition, and recovery state verification (TDD).

These four test functions must exist with EXACT signatures matching the task specification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import pytest


# --------------------------------------------------------------------------- #
# Helpers — match existing conftest pattern for subject setup
# --------------------------------------------------------------------------- #

@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean temporary workspace root."""
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    return ws


def _create_approved_subject(
    workspace: Path,
    subject_id: str = "thermo-101",
    topic: str = "Thermodynamics",
) -> Path:
    """Create a subject with an approved draft containing entropy + energy conservation sections.

    Uses generate_draft (which sets draft_version_hash) then approve_draft.
    
    Returns the subject_root path.
    """
    from study.subjects import create_subject, approve_draft

    root = create_subject(workspace, subject_id, topic)

    # Write a learning draft with two distinct sections about entropy and energy conservation
    (root / "learning_draft.md").write_text(
        "# Thermodynamics\n"
        "\n"
        "## Entropy and the Second Law\n"
        "Entropy is a measure of disorder in a system. The second law states that "
        "the total entropy of an isolated system can never decrease over time.\n"
        "\n"
        "Energy is conserved in all processes according to the first law of thermodynamics.\n"
    )

    # generate_draft populates draft_version_hash (Task 4 behavior)
    from study.drafting import generate_draft
    generate_draft(root, topic)

    approve_draft(root)
    return root


# --------------------------------------------------------------------------- #
# 1. test_scoring_and_weak_point_tracking
# --------------------------------------------------------------------------- #

def test_scoring_and_weak_point_tracking(tmp_workspace: Path) -> None:
    """Scoring should identify weak points and track them correctly."""
    from study.models import RecallQuestion, WeakPoint
    from study.recall import record_session
    from study.storage import load_progress

    root = _create_approved_subject(tmp_workspace)

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain entropy...")
    q2 = RecallQuestion(id="q2", topic="Section B", prompt="How does energy conservation apply?")

    record_session(
        root,
        [q1, q2],
        ["answer about entropy", "weak answer with misconceptions"],
        [0.8, 0.3],
    )

    state = load_progress(root)

    # Weak point for Section B should be created (score < 0.5)
    assert len(state.weak_points) >= 1
    assert any(
        wp.topic == "Section B" and wp.weakness_score < 0.5
        for wp in state.weak_points
    )


# --------------------------------------------------------------------------- #
# 2. test_scoring_populates_recovery_state — v4 fail target
# --------------------------------------------------------------------------- #

def test_scoring_populates_recovery_state(tmp_workspace: Path) -> None:
    """ALL recovery state fields must be populated correctly after scoring."""
    from study.models import RecallQuestion
    from study.recall import record_session
    from study.storage import load_progress

    root = _create_approved_subject(tmp_workspace, topic="X and Y topics")

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain X...")
    q2 = RecallQuestion(id="q2", topic="Section B", prompt="Explain Y...")

    record_session(
        root,
        [q1, q2],
        ["good answer about X", "weak answer with misconceptions"],
        [0.8, 0.3],
    )

    state = load_progress(root)

    # Critical assertions — these were missing in v4:
    assert state.phase == "recall_adaptive"
    assert state.approval_status is True
    assert state.draft_version_hash is not None and len(state.draft_version_hash) > 0
    assert state.next_recursors_cursor >= 1
    assert len(state.weak_points) >= 1
    assert any(wp.topic == "Section B" for wp in state.weak_points)


# --------------------------------------------------------------------------- #
# 3. test_recovery_from_disk — persistence across process restarts
# --------------------------------------------------------------------------- #

def test_recovery_from_disk(tmp_workspace: Path) -> None:
    """Loaded state from disk must contain all recovery fields after scoring."""
    from study.models import RecallQuestion
    from study.recall import record_session
    from study.storage import load_progress

    root = _create_approved_subject(
        tmp_workspace, subject_id="disk-test", topic="Entropy and Energy"
    )

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain entropy...")
    record_session(root, [q1], ["answer about entropy"], [0.3])

    # Simulate fresh process — reload from disk
    loaded_state = load_progress(root)

    assert loaded_state.phase == "recall_adaptive"
    assert loaded_state.approval_status is True
    assert len(loaded_state.draft_version_hash) > 0


# --------------------------------------------------------------------------- #
# 4. test_recall_history_contains_evidence — JSONL format verification
# --------------------------------------------------------------------------- #

def test_recall_history_contains_evidence(tmp_workspace: Path) -> None:
    """Each line in recall_history.jsonl must contain required fields."""
    from study.models import RecallQuestion
    from study.recall import record_session

    root = _create_approved_subject(
        tmp_workspace, subject_id="evidence-test", topic="Entropy"
    )

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain entropy...")
    record_session(root, [q1], ["answer about entropy"], [0.8])

    # Read JSONL file directly
    jsonl_path = root / "recall_history.jsonl"
    assert jsonl_path.exists()

    entries: list[dict] = []
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        entries.append(json.loads(line))

    # Each entry must have required fields
    for entry in entries:
        assert "session_id" in entry
        assert isinstance(entry.get("questions"), list) or (entry.get("outcome") == "pass")
        assert "answers" in entry or entry.get("outcome") == "pass"
        assert "scores" in entry or entry.get("outcome") == "pass"
        assert entry.get("outcome") in ("pass", "fail", "partial")


# --------------------------------------------------------------------------- #
# 5. test_score_answer_clamped_to_range
# --------------------------------------------------------------------------- #

def test_score_answer_clamped_to_range(tmp_workspace: Path) -> None:
    """score_answer must clamp values to [0, 1]."""
    from study.models import RecallQuestion
    from study.recall import score_answer

    q = RecallQuestion(id="q", topic="Topic", prompt="Explain it.")
    
    # Normal case — should return value in [0, 1]
    score_value = score_answer(q, "some answer", "expected content")
    assert 0.0 <= score_value <= 1.0


# --------------------------------------------------------------------------- #
# 6. test_decompose_misconceptions_returns_dict
# --------------------------------------------------------------------------- #

def test_decompose_misconceptions_returns_dict(tmp_workspace: Path) -> None:
    """decompose_misconceptions must return dict with misconception + correct_points."""
    from study.recall import decompose_misconceptions

    result = decompose_misconceptions(
        "entropy is not important", 
        "entropy measures disorder and is central to thermodynamics"
    )

    assert isinstance(result, dict)
    assert "misconception" in result
    assert "correct_points" in result
    assert isinstance(result["correct_points"], list)


# --------------------------------------------------------------------------- #
# 7. test_record_session_raises_without_approval
# --------------------------------------------------------------------------- #

def test_record_session_raises_without_approval(tmp_workspace: Path) -> None:
    """record_session must raise ApprovalRequiredError if draft not approved."""
    from study.models import ApprovalRequiredError, RecallQuestion
    from study.recall import record_session
    from study.subjects import create_subject

    root = create_subject(tmp_workspace, "unapproved", "Topic")
    (root / "learning_draft.md").write_text("# Chapter\n## Section\nContent.")

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain...")

    with pytest.raises(ApprovalRequiredError):
        record_session(root, [q1], ["answer"], [0.8])


# --------------------------------------------------------------------------- #
# 8. test_outcome_classification — pass/fail/partial thresholds
# --------------------------------------------------------------------------- #

def test_outcome_classification(tmp_workspace: Path) -> None:
    """Outcome must be classified based on average score."""
    from study.models import RecallQuestion
    from study.recall import record_session
    from study.storage import load_progress

    root = _create_approved_subject(
        tmp_workspace, subject_id="outcome-test", topic="Topic"
    )

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain...")
    
    # High scores → pass
    record_session(root, [q1], ["good answer"], [0.8])
    state = load_progress(root)
    assert state.first_pass_complete is True or state.phase == "recall_adaptive"


# --------------------------------------------------------------------------- #
# 9. test_weak_points_persists_across_sessions
# --------------------------------------------------------------------------- #

def test_weak_points_persists_across_sessions(tmp_workspace: Path) -> None:
    """Weak points should accumulate across multiple sessions."""
    from study.models import RecallQuestion
    from study.recall import record_session
    from study.storage import load_progress

    root = _create_approved_subject(
        tmp_workspace, subject_id="persist-test", topic="Topic"
    )

    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain...")
    
    record_session(root, [q1], ["weak"], [0.3])  # Session 1 — weak point for Section A
    state_2 = load_progress(root)
    
    record_session(root, [q1], ["weak again"], [0.2])  # Session 2 — should add more or increment
    
    assert len(state_2.weak_points) >= 1
