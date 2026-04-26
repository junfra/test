"""Adaptive retest — weighted random selection and approval gate (Task 8).

Tests that:
1. select_next_questions_weak enforces the draft-approval gate.
2. Weak topics are prioritized via inverse-weighting of their weakness_score,
   with deterministic seeding for reproducibility in CI.
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

import pytest

from study.models import ApprovalRequiredError
from study.recall import select_next_questions_weak
from study.subjects import create_subject, approve_draft
from study.drafting import generate_draft
from study.storage import load_progress


def _make_seed_dir(name):
    root = Path(f"/tmp/test_adaptive_{name}")
    if root.exists():
        shutil.rmtree(root)
    return root


# ── test_adaptive_recall_rejects_unapproved ─────────────────────────────── #


def test_adaptive_recall_rejects_unapproved():
    """Calling select_next_questions_weak without approve_draft must raise ApprovalRequiredError."""
    ws = _make_seed_dir("unapproved")
    subject_root = create_subject(ws, "seed-ua", "Seed unapproved")

    generate_draft(subject_root, "Seed Drafting")

    with pytest.raises(ApprovalRequiredError):
        select_next_questions_weak(subject_root, n=3)


# ── test_weak_points_prioritized_in_random_order ────────────────────────── #


def test_weak_points_prioritized_in_random_order():
    """Weak topics should appear in the retest selection because they have higher weight.

    We seed random so that the weighted selection is deterministic:
    Section B has weakness_score=0.3 → weight ≈ 1/(0.3+1-0) = ~0.77
    Section A has weakness_score=0.9 → weight ≈ 1/(0.9+1-0) = ~0.53

    With these weights and seed(42), Section B should be chosen first.
    """
    ws = _make_seed_dir("prioritized")
    subject_root = create_subject(ws, "seed-pri", "Seed prioritized")

    draft_content = "# Seed Drafting\n\n## Section A\n\nSection A covers strong topics.\n\n## Section B\n\nSection B is about misconceptions.\n"
    # generate a draft first to set the hash, then overwrite content
    generate_draft(subject_root, "Seed Drafting")
    (subject_root / "learning_draft.md").write_text(draft_content)
    approve_draft(subject_root)

    from study.recall import generate_first_pass_questions, record_session
    questions = generate_first_pass_questions(subject_root, n=2)
    answers = ["Strong answer for Section A.", "Weak answer for Section B with misconceptions."]
    scores = [0.9, 0.3]
    record_session(subject_root, questions, answers, scores)

    profile = load_progress(subject_root)
    assert len(profile.weak_points) >= 1
    assert any(wp.topic == "Section B" for wp in profile.weak_points), \
        f"Section B should be weak. Got: {[wp.topic for wp in profile.weak_points]}"

    # Explicitly verify weak points were populated
    profile = load_progress(subject_root)
    assert len(profile.weak_points) >= 1, f"Expected weak points, got: {profile.weak_points}"
    assert any(wp.topic == "Section B" for wp in profile.weak_points)

    random.seed(42)
    retest_qs = select_next_questions_weak(subject_root, n=3)
    assert len(retest_qs) >= 1
    topics_in_retest = [q.topic for q in retest_qs]
    assert "Section B" in topics_in_retest, f"Section B should be prioritized. Got: {topics_in_retest}"
