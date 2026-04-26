"""Tests for study.models — written BEFORE implementation (TDD fail-first)."""
from __future__ import annotations

import pytest


def test_imports_all_models() -> None:
    """Import all model classes from study.models."""
    from study.models import SubjectId, SourceReference, RecallQuestion
    from study.models import WeakPoint, ProgressState, RecallSessionEntry

    # Verify they are actual models (Pydantic BaseModel subclasses)
    assert issubclass(SubjectId, str), "SubjectId should be a str subclass"


class TestSubjectId:
    def test_subject_id_is_str_subclass(self) -> None:
        from study.models import SubjectId

        sid = SubjectId("math-101")
        assert isinstance(sid, str)
        assert str(sid) == "math-101"
        assert sid + "-extra" == "math-101-extra"


class TestSourceReference:
    def test_valid_native(self) -> None:
        from study.models import SourceReference

        src = SourceReference(kind="native", content="Hello")
        assert src.kind == "native"
        assert src.content == "Hello"
        assert src.metadata == {}

    @pytest.mark.parametrize(
        "kind", ["native", "web_search", "user_file", "pasted_text"]
    )
    def test_all_kinds_accepted(self, kind: str) -> None:
        from study.models import SourceReference

        sr = SourceReference(kind=kind, content="x")
        assert sr.kind == kind


class TestRecallQuestion:
    def test_defaults(self) -> None:
        from study.models import RecallQuestion

        q = RecallQuestion(id="q1", topic="Python", prompt="What is 2+2?", answer="4")
        assert q.id == "q1"
        assert q.topic == "Python"
        assert q.prompt == "What is 2+2?"
        assert q.answer == "4"
        assert q.score is None

    def test_with_score(self) -> None:
        from study.models import RecallQuestion

        q = RecallQuestion(id="q1", topic="P", prompt="?", answer="A", score=0.95)
        assert q.score == 0.95


class TestWeakPoint:
    def test_defaults_and_range(self) -> None:
        from study.models import WeakPoint

        wp = WeakPoint(topic="closure", misconception_explanation="...", weakness_score=0.8)
        assert wp.topic == "closure"
        assert wp.retest_count == 0

    def test_weakness_score_out_of_range_raises(self) -> None:
        from study.models import WeakPoint

        with pytest.raises(Exception):
            WeakPoint(topic="X", misconception_explanation="...", weakness_score=1.5)

        with pytest.raises(Exception):
            WeakPoint(topic="X", misconception_explanation="...", weakness_score=-0.1)


class TestProgressState:
    def test_defaults(self) -> None:
        from study.models import ProgressState

        ps = ProgressState(subject_id="math-101", topic="algebra")
        assert ps.subject_id == "math-101"
        assert ps.approval_status is False
        assert ps.first_pass_complete is False
        assert ps.next_recursors_cursor == 0
        assert ps.weak_points == []

    @pytest.mark.parametrize("phase", ["intake", "drafting", "draft_approved", "recall_first_pass", "recall_adaptive"])
    def test_all_phases_accepted(self, phase: str) -> None:
        from study.models import ProgressState

        ps = ProgressState(subject_id="s1", topic="t1", phase=phase)
        assert ps.phase == phase


class TestRecallSessionEntry:
    def test_defaults_and_outcome(self) -> None:
        from study.models import RecallSessionEntry, RecallQuestion

        entry = RecallSessionEntry(
            session_id="s1",
            questions=[RecallQuestion(id="q1", topic="t", prompt="?", answer="?")],
            outcome="pass",
            timestamp="2026-04-26T12:00:00Z",
        )
        assert entry.outcome == "pass"
        assert entry.answers is None
        assert entry.scores is None

    @pytest.mark.parametrize("outcome", ["pass", "fail", "partial"])
    def test_all_outcomes_accepted(self, outcome: str) -> None:
        from study.models import RecallSessionEntry

        e = RecallSessionEntry(session_id="s1", questions=[], outcome=outcome, timestamp="2026-04-26T12:00:00Z")
        assert e.outcome == outcome
