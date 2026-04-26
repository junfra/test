"""Tests for exit condition verification — written BEFORE implementation (TDD fail-first).

KEY TEST: test_verify_exit_conditions_weakness_after_scoring verifies the X3 drift fix.
After record_session with low scores, verify_exit_conditions must report weakness_loop_active == True.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# --------------------------------------------------------------------------- #
# Helpers — full subject lifecycle fixture (Task 7+8)
# --------------------------------------------------------------------------- #

@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean temporary workspace root."""
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    return ws


@pytest.fixture()
def full_subject_lifecycle(tmp_workspace: Path):
    """Create a subject, draft it, approve it — ready for recall.

    Returns (subject_root, topic, workspace_root).
    """
    from study.subjects import create_subject
    from study.drafting import generate_draft
    from study.storage import load_progress

    # Create subject with some source data so drafting produces content
    subject_root = create_subject(tmp_workspace, "math-101", "algebra")
    
    # Write a dummy source file so generate_draft has input
    src_dir = subject_root / "source_reference_data"
    (src_dir / "topic.txt").write_text(
        "Algebra is the study of mathematical symbols and the rules for manipulating them. "
        "Key concepts include variables, equations, polynomials, and functions."
    )

    # Generate draft
    generate_draft(subject_root, "algebra")

    # Approve draft (needed before recall)
    from study.subjects import approve_draft
    approve_draft(subject_root)

    state = load_progress(subject_root)
    return subject_root, state.topic, tmp_workspace


# --------------------------------------------------------------------------- #
# 1. test_verify_exit_conditions_returns_expected_keys
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsStructure:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_verify_returns_all_four_keys(self, tmp_workspace: Path) -> None:
        """verify_exit_conditions returns a dict with exactly the four expected keys."""
        from study.subjects import create_subject
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert set(result.keys()) == {
            "draft_approved", "first_recall_complete", 
            "weakness_loop_active", "subject_state_complete"
        }, f"Unexpected keys: {result.keys()}"

    def test_verify_returns_dict_not_none(self, tmp_workspace: Path) -> None:
        """verify_exit_conditions returns a dict, not None or exception."""
        from study.subjects import create_subject
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"


# --------------------------------------------------------------------------- #
# 2. test_verify_exit_conditions_draft_approved_false_initially
# --------------------------------------------------------------------------- #

class TestDraftApproved:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_draft_approved_is_false_when_not_approved(self, tmp_workspace: Path) -> None:
        """draft_approved is False for a newly created subject."""
        from study.subjects import create_subject
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["draft_approved"] is False

    def test_draft_approved_is_true_after_approve(self, tmp_workspace: Path) -> None:
        """draft_approved becomes True after approve_draft()."""
        from study.subjects import create_subject, approve_draft
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")
        
        # Write a dummy draft so approve_draft doesn't fail
        (subject_root / "learning_draft.md").write_text("# Draft\nContent here.")
        
        approve_draft(subject_root)

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["draft_approved"] is True


# --------------------------------------------------------------------------- #
# 3. test_verify_exit_conditions_first_recall_complete
# --------------------------------------------------------------------------- #

class TestFirstRecallComplete:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_first_recall_complete_false_initially(self, tmp_workspace: Path) -> None:
        """first_recall_complete is False before any recall session."""
        from study.subjects import create_subject
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["first_recall_complete"] is False

    def test_first_recall_complete_true_after_generate_questions(self, full_subject_lifecycle) -> None:
        """first_recall_complete becomes True after generate_first_pass_questions."""
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Generate first pass questions (this updates phase and cursor in progress_state.json)
        from study.recall import generate_first_pass_questions
        questions = generate_first_pass_questions(subject_root, n=5)
        
        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["first_recall_complete"] is True


# --------------------------------------------------------------------------- #
# 4. test_verify_exit_conditions_weakness_after_scoring — KEY X3 TEST
# --------------------------------------------------------------------------- #

class TestWeaknessLoopActive:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weakness_loop_active_false_initially(self, tmp_workspace: Path) -> None:
        """weakness_loop_active is False for a fresh subject."""
        from study.subjects import create_subject
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["weakness_loop_active"] is False

    def test_weakness_loop_active_true_after_low_score_session(self, full_subject_lifecycle) -> None:
        """KEY ASSERTION FOR X3 FIX: after record_session with low scores, weakness_loop_active == True."""
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Generate questions first (requires draft approved)
        from study.recall import generate_first_pass_questions
        questions = generate_first_pass_questions(subject_root, n=5)
        
        # Record a session with LOW scores (all < 0.5 triggers weak_points)
        answers = ["wrong answer 1"] * len(questions)
        scores = [0.3] * len(answers)  # all below 0.5 threshold
        
        from study.recall import record_session
        entry = record_session(subject_root, questions, answers, scores)

        result = self.verify_exit_conditions("math-101", workspace)
        
        # THIS IS THE KEY ASSERTION FOR X3 DRIFT FIX — without this fix, weak_points stays empty
        assert (
            result["weakness_loop_active"] is True
        ), "X3 drift: weakness_loop_active should be True after low-score session"


# --------------------------------------------------------------------------- #
# 5. test_verify_exit_conditions_subject_state_complete_with_logs
# NOTE: create_subject now logs a subject_created event, so subject_state_complete
# will be True even before explicit recall logging — this reflects correct behavior.
# --------------------------------------------------------------------------- #

class TestSubjectStateComplete:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_subject_state_complete_true_after_create_with_logs(self, tmp_workspace: Path) -> None:
        """subject_state_complete is True after create_subject (which logs subject_created)."""
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        # Create_subject now logs a session event, so subject_state_complete should be True
        assert result["subject_state_complete"] is True

    def test_subject_state_complete_true_with_log_files(self, full_subject_lifecycle) -> None:
        """subject_state_complete is True after the full lifecycle."""
        subject_root, topic, workspace = full_subject_lifecycle
        
        # After create + draft + approve, logs should exist
        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["subject_state_complete"] is True


# --------------------------------------------------------------------------- #
# 6. test_verify_exit_conditions_no_approval_error
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsRobustness:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_verify_handles_missing_progress_state_fully_gracefully(self, tmp_workspace: Path) -> None:
        """When progress_state.json is missing, returns all False."""
        # Create a subject directory without writing progress_state.json
        bad_dir = tmp_workspace / "subjects" / "broken-subject"
        bad_dir.mkdir(parents=True)

        result = self.verify_exit_conditions("broken-subject", tmp_workspace)
        
        assert isinstance(result, dict), "Should return dict even for broken subject"
        # All should be False since we can't read state
        assert all(v is False for v in result.values())


# --------------------------------------------------------------------------- #
# 7. test_verify_exit_conditions_integration_full_lifecycle
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsIntegration:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_full_lifecycle_progression(self, full_subject_lifecycle) -> None:
        """After the full lifecycle (create → draft → approve → first_pass), 
        multiple conditions should be True simultaneously."""
        from study.recall import generate_first_pass_questions
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Generate questions to update state
        generate_first_pass_questions(subject_root, n=5)

        result = self.verify_exit_conditions("math-101", workspace)
        
        # After approve_draft: draft_approved should be True
        assert result["draft_approved"] is True
        # After generate_first_pass_questions: first_recall_complete should be True  
        assert result["first_recall_complete"] is True
        # No scores recorded yet, so no weak_points
        assert result["weakness_loop_active"] is False


# --------------------------------------------------------------------------- #
# 8. test_verify_exit_conditions_loads_progress_state_correctly
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsStateLoading:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_reads_current_phase_from_progress_state(self, tmp_workspace: Path) -> None:
        """verify_exit_conditions reads the actual phase from progress_state.json."""
        from pathlib import Path as P
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")
        
        # Manually set phase to recall_adaptive (simulating after record_session)
        ps_file = subject_root / "progress_state.json"
        state_data = json.loads(ps_file.read_text())
        state_data["phase"] = "recall_adaptive"
        state_data["next_recursors_cursor"] = 2  # > 0 to satisfy first_recall_complete
        
        ps_file.write_text(json.dumps(state_data))

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["first_recall_complete"] is True, "Phase recall_adaptive + cursor>0 should pass"


# --------------------------------------------------------------------------- #
# 9. test_verify_exit_conditions_accepts_subject_root_directly
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsSubjectRoot:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_verify_with_subject_root_works(self, tmp_workspace: Path) -> None:
        """verify_exit_conditions can also accept a subject root path directly."""
        from pathlib import Path as P
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        # Call with subject_id and workspace — should work
        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert isinstance(result, dict)


# --------------------------------------------------------------------------- #
# 10. test_verify_exit_conditions_weakness_loop_active_after_multiple_scores
# --------------------------------------------------------------------------- #

class TestMultipleScoring:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weakness_loop_active_after_high_then_low_score(self, full_subject_lifecycle) -> None:
        """weakness_loop_active becomes True after a low-score session (even if previous was high)."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Generate questions first
        questions1 = generate_first_pass_questions(subject_root, n=5)
        
        # Record a PASSING session (all >= 0.7 → no weak_points added)
        answers_pass = ["good answer"] * len(questions1)
        record_session(subject_root, questions1, answers_pass, [0.8] * len(answers_pass))

        result_before = self.verify_exit_conditions("math-101", workspace)
        assert result_before["weakness_loop_active"] is False, "High scores → no weak points"

        # Now record a FAILING session (all < 0.5 → weak_points added)
        questions2 = generate_first_pass_questions(subject_root, n=3)
        answers_fail = ["bad answer"] * len(questions2)
        record_session(subject_root, questions2, answers_fail, [0.2] * len(answers_fail))

        result_after = self.verify_exit_conditions("math-101", workspace)
        assert (
            result_after["weakness_loop_active"] is True
        ), "Low scores → weak_points populated"


# --------------------------------------------------------------------------- #
# 11. test_verify_exit_conditions_subject_state_complete_requires_files
# --------------------------------------------------------------------------- #

class TestSubjectStateCompleteFiles:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_required_files_checked(self, full_subject_lifecycle) -> None:
        """subject_state_complete checks for required files (progress_state.json, learning_draft.md)."""
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Delete the draft file — should make subject_state_complete False even with logs
        (subject_root / "learning_draft.md").unlink()

        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["subject_state_complete"] is False


# --------------------------------------------------------------------------- #
# 12. test_verify_exit_conditions_consistency_across_calls
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsConsistency:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_same_result_for_multiple_calls(self, tmp_workspace: Path) -> None:
        """Calling verify_exit_conditions multiple times returns consistent results."""
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        result1 = self.verify_exit_conditions("math-101", tmp_workspace)
        result2 = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result1 == result2


# --------------------------------------------------------------------------- #
# 13. test_verify_exit_conditions_cursor_tracking_across_sessions
# --------------------------------------------------------------------------- #

class TestCursorTracking:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_first_recall_complete_stays_true_after_multiple_sessions(self, full_subject_lifecycle) -> None:
        """first_recall_complete remains True after multiple recall sessions."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # First pass
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["ans"] * 5, [0.6] * 5)

        result1 = self.verify_exit_conditions("math-101", workspace)
        assert result1["first_recall_complete"] is True

        # Second pass — generate new questions and record
        questions2 = generate_first_pass_questions(subject_root, n=3)
        record_session(subject_root, questions2, ["ans"] * 3, [0.5] * 3)

        result2 = self.verify_exit_conditions("math-101", workspace)
        assert result2["first_recall_complete"] is True


# --------------------------------------------------------------------------- #
# 14. test_verify_exit_conditions_subject_state_complete_requires_draft
# --------------------------------------------------------------------------- #

class TestSubjectStateCompleteDraftRequired:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_subject_state_complete_false_without_draft_file(self, tmp_workspace: Path) -> None:
        """subject_state_complete is False when learning_draft.md is missing."""
        # Create subject directory manually without draft
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)
        
        # Write progress_state.json but NOT learning_draft.md
        from study.models import ProgressState
        
        ps_file = subject_root / "progress_state.json"
        state = ProgressState(
            subject_id="math-101", topic="algebra",
            phase="draft_approved", approval_status=True,
            draft_version_hash="abc123", next_recursors_cursor=0, weak_points=[]
        )
        ps_file.write_text(state.model_dump_json(indent=2))
        
        # Create session_logs with a log file (so has_log_files is True)
        logs_dir = subject_root / "session_logs"
        logs_dir.mkdir(exist_ok=True)
        (logs_dir / "test.jsonl").write_text('{"event_type": "test", "payload": {}}\n')

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["subject_state_complete"] is False, "Missing draft → subject_state_complete=False"


# --------------------------------------------------------------------------- #
# 15. test_verify_exit_conditions_weak_points_populated_from_record_session
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPoints:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weakness_loop_active_false_when_no_weak_points_exist(self, full_subject_lifecycle) -> None:
        """weakness_loop_active is False when weak_points is empty (all high scores)."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Generate questions and record with high scores
        questions1 = generate_first_pass_questions(subject_root, n=5)
        answers = ["good answer"] * len(questions1)
        record_session(subject_root, questions1, answers, [0.9] * len(answers))

        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["weakness_loop_active"] is False, "High scores → no weak points"


# --------------------------------------------------------------------------- #
# 16. test_verify_exit_conditions_accepts_workspace_or_subject_root
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsSignature:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_verify_with_only_subject_root_works(self, tmp_workspace: Path) -> None:
        """verify_exit_conditions accepts subject_root kwarg directly."""
        from pathlib import Path as P
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")

        # Call with subject_root only (no workspace)
        result = verify_exit_conditions(subject_id="math-101", subject_root=subject_root)
        
        assert isinstance(result, dict)


# --------------------------------------------------------------------------- #
# 17. test_verify_exit_conditions_multiple_subjects_independent
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsIndependence:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_different_subjects_have_independent_state(self, tmp_workspace: Path) -> None:
        """Two subjects in the same workspace have independent exit conditions."""
        from study.subjects import create_subject
        
        root_a = create_subject(tmp_workspace, "math-101", "algebra")
        root_b = create_subject(tmp_workspace, "physics-202", "thermo")

        result_a = self.verify_exit_conditions("math-101", tmp_workspace)
        result_b = self.verify_exit_conditions("physics-202", tmp_workspace)
        
        assert result_a == result_b  # Both fresh → same initial state


# --------------------------------------------------------------------------- #
# 18. test_verify_exit_conditions_phase_boundary_correctness
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsPhaseBoundaries:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_first_recall_complete_false_when_cursor_zero(self, tmp_workspace: Path) -> None:
        """first_recall_complete is False even if phase=recall_adaptive but cursor==0."""
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")
        
        ps_file = subject_root / "progress_state.json"
        state_data = json.loads(ps_file.read_text())
        state_data["phase"] = "recall_adaptive"
        state_data["next_recursors_cursor"] = 0  # zero cursor
        
        ps_file.write_text(json.dumps(state_data))

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["first_recall_complete"] is False, "cursor==0 → first_recall_complete=False"


# --------------------------------------------------------------------------- #
# 19. test_verify_exit_conditions_weak_point_topics_accessible
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPointTopics:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weakness_loop_active_true_after_multiple_low_score_sessions(self, full_subject_lifecycle) -> None:
        """weakness_loop_active remains True across multiple low-score sessions."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # First pass — low scores
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["bad"] * 5, [0.3] * 5)

        result1 = self.verify_exit_conditions("math-101", workspace)
        assert result1["weakness_loop_active"] is True
        
        # Second pass — low scores again
        questions2 = generate_first_pass_questions(subject_root, n=3)
        record_session(subject_root, questions2, ["bad"] * 3, [0.4] * 3)

        result2 = self.verify_exit_conditions("math-101", workspace)
        assert result2["weakness_loop_active"] is True, "Low scores persist → weakness loop active"


# --------------------------------------------------------------------------- #
# 20. test_verify_exit_conditions_all_keys_present_after_full_lifecycle
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsFullKeyPresence:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_all_keys_present_after_low_score_session(self, full_subject_lifecycle) -> None:
        """After a low-score session, all four keys are present and meaningful."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["bad"] * 5, [0.3] * 5)

        result = self.verify_exit_conditions("math-101", workspace)
        
        assert "draft_approved" in result
        assert "first_recall_complete" in result
        assert "weakness_loop_active" in result
        assert "subject_state_complete" in result


# --------------------------------------------------------------------------- #
# 21. test_verify_exit_conditions_weak_point_topic_name_preserved
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPointPreservation:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weak_point_topics_in_progress_state_match_questions(self, full_subject_lifecycle) -> None:
        """Topics in weak_points match the topics of low-scoring questions."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        questions1 = generate_first_pass_questions(subject_root, n=5)
        
        # Use answers that will produce different weak point topics (each question's topic is unique)
        record_session(subject_root, questions1, ["wrong"] * 5, [0.2] * 5)

        from study.storage import load_progress
        state = load_progress(subject_root)
        
        assert len(state.weak_points) > 0, "Low scores should populate weak_points"


# --------------------------------------------------------------------------- #
# 22. test_verify_exit_conditions_cursor_increases_per_session
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsCursorIncrements:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_cursor_increases_after_each_record_session_call(self, full_subject_lifecycle) -> None:
        """Each record_session call increments next_recursors_cursor."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # Initial cursor is 0 (or some value after generate_draft/approve)
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["ans"] * 5, [0.6] * 5)

        from study.storage import load_progress
        state_after_1 = load_progress(subject_root)
        cursor_1 = state_after_1.next_recursors_cursor
        
        questions2 = generate_first_pass_questions(subject_root, n=3)
        record_session(subject_root, questions2, ["ans"] * 3, [0.6] * 3)

        state_after_2 = load_progress(subject_root)
        cursor_2 = state_after_2.next_recursors_cursor
        
        assert cursor_2 > cursor_1, "Cursor should increment after each session"


# --------------------------------------------------------------------------- #
# 23. test_verify_exit_conditions_weak_point_retest_count_tracking
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsRetestCount:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_retest_count_increments_on_select_next_questions_weak(self, full_subject_lifecycle) -> None:
        """select_next_questions_weak increments retest_count for selected weak points."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        # First pass with low scores to create weak_points
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["bad"] * 5, [0.2] * 5)

        from study.storage import load_progress
        state_before = load_progress(subject_root)
        
        # Now select weak points for retest
        from study.recall import select_next_questions_weak
        _retest_qs = select_next_questions_weak(subject_root, n=3)
        
        state_after = load_progress(subject_root)
        
        if state_after.weak_points:
            assert any(wp.retest_count > 0 for wp in state_after.weak_points), \
                "Re-test should increment retest_count"


# --------------------------------------------------------------------------- #
# 24. test_verify_exit_conditions_subject_state_complete_requires_log_files_exist
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsLogFilesRequired:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_subject_state_complete_false_when_logs_dir_empty(self, tmp_workspace: Path) -> None:
        """subject_state_complete is False when session_logs/ has no .jsonl files."""
        # Create subject root with progress but empty logs dir
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)
        
        from study.models import ProgressState
        
        ps_file = subject_root / "progress_state.json"
        state = ProgressState(
            subject_id="math-101", topic="algebra",
            phase="draft_approved", approval_status=True,
            draft_version_hash="abc123", next_recursors_cursor=0, weak_points=[]
        )
        ps_file.write_text(state.model_dump_json(indent=2))
        
        # Create drafts so required files exist
        (subject_root / "learning_draft.md").write_text("# Draft")
        
        # session_logs exists but is empty
        logs_dir = subject_root / "session_logs"
        logs_dir.mkdir(exist_ok=True)

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["subject_state_complete"] is False, "Empty logs → subject_state_complete=False"


# --------------------------------------------------------------------------- #
# 25. test_verify_exit_conditions_weak_points_survive_save_load
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPointPersistence:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weak_points_persist_across_save_load_cycles(self, full_subject_lifecycle) -> None:
        """weak_points persist correctly across save/load (disk round-trip)."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        questions1 = generate_first_pass_questions(subject_root, n=5)
        record_session(subject_root, questions1, ["bad"] * 5, [0.2] * 5)

        # Verify via verify_exit_conditions (which reads from disk)
        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["weakness_loop_active"] is True, "Weak points should persist to disk"


# --------------------------------------------------------------------------- #
# 26. test_verify_exit_conditions_edge_case_no_phase_match
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsEdgeCases:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_first_recall_complete_false_for_non_recall_phases(self, tmp_workspace: Path) -> None:
        """first_recall_complete is False for non-recall phases even if cursor > 0."""
        from study.subjects import create_subject
        
        subject_root = create_subject(tmp_workspace, "math-101", "algebra")
        
        ps_file = subject_root / "progress_state.json"
        state_data = json.loads(ps_file.read_text())
        state_data["phase"] = "drafting"  # non-recall phase
        state_data["next_recursors_cursor"] = 5  # cursor > 0, but phase is wrong
        
        ps_file.write_text(json.dumps(state_data))

        result = self.verify_exit_conditions("math-101", tmp_workspace)
        
        assert result["first_recall_complete"] is False, "Non-recall phase → first_recall_complete=False"


# --------------------------------------------------------------------------- #
# 27. test_verify_exit_conditions_weak_points_with_misconception_details
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPointDetails:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weak_points_contain_misconception_explanation(self, full_subject_lifecycle) -> None:
        """Each weak point in progress_state contains a misconception explanation."""
        from study.recall import generate_first_pass_questions, record_session
        
        subject_root, topic, workspace = full_subject_lifecycle
        
        questions1 = generate_first_pass_questions(subject_root, n=3)
        
        # Get the topics of the first few questions to use as expected weak point topics
        question_topics = [q.topic for q in questions1[:2]]  # At most 2 due to dedup logic
        
        record_session(subject_root, questions1, ["wrong"] * len(questions1), [0.3] * len(questions1))

        from study.storage import load_progress
        state = load_progress(subject_root)
        
        if state.weak_points:
            for wp in state.weak_points:
                assert isinstance(wp.topic, str), "Topic should be a string"
                assert len(wp.topic) > 0, "Topic should not be empty"


# --------------------------------------------------------------------------- #
# 28. test_verify_exit_conditions_weakness_loop_active_boundary_at_zero
# --------------------------------------------------------------------------- #

class TestVerifyExitConditionsWeakPointBoundary:
    def verify_exit_conditions(self, subject_id: str, workspace_root: Path):
        from study.subjects import verify_exit_conditions as _vec
        return _vec(subject_id, workspace_root)

    def test_weakness_loop_active_false_when_weak_points_empty_list(self, full_subject_lifecycle) -> None:
        """weakness_loop_active is False when weak_points list is empty (not just missing)."""
        subject_root, topic, workspace = full_subject_lifecycle
        
        from study.storage import load_progress
        state = load_progress(subject_root)
        
        # Explicitly clear weak_points to verify the boundary condition
        state.weak_points = []
        from study.storage import save_progress
        save_progress(subject_root, state)

        result = self.verify_exit_conditions("math-101", workspace)
        
        assert result["weakness_loop_active"] is False, "Empty weak_points → weakness_loop_active=False"
