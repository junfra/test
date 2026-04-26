"""Tests for ProhibitedPatternDetector — hollow writing detection."""
from __future__ import annotations

import pytest

from study.learning_draft_rule import detect_prohibited_patterns, ProhibitedPatternResult
from study.models import LearningDraftRule


# ─── Fixtures ──────────────────────────────────────────────

_VALID_DRAFT = """\
## 문제 배경
프로그래밍 언어에서 변수는 메모리에 값을 저장하는 이름표입니다. 변수를 선언하면 컴퓨터가 해당 데이터의 타입을 결정하고 적절한 크기의 메모리 공간을 할당합니다.


## 개념 정의
변수 선언문은 `type name = value` 형식으로 작성됩니다. 여기서 type 은 정적언어라면 컴파일 시점에 확정되며, 동적언어라면 런타임에 추론됩니다. 변수의 수명은 스코프와 연결되어 있습니다.

"""


# ─── Tests ─────────────────────────────────────────────────


class TestProhibitedPatternDetector:
    """Tests for prohibited pattern detection."""

    def test_detects_template_placeholders(self) -> None:
        """A draft containing template placeholders should be rejected."""
        rule = LearningDraftRule.default()
        draft_with_placeholders = "Insert topic here. {{topic}} [Topic]"

        result = detect_prohibited_patterns(draft_with_placeholders, rule)

        assert result.passed is False, f"Expected passed=False but got errors: {result.errors}"
        assert "template_placeholder" in result.matches
        assert len(result.errors) > 0

    def test_detects_generic_hollow_importance_claims(self) -> None:
        """Repeated generic importance claims should be detected."""
        rule = LearningDraftRule.default()
        draft_with_generic_claims = (
            "이 개념은 매우 중요하다.\n"
            "다른 관점에서도 이것은 매우 중요하다.\n"
            "따라서 잘 이해해야 한다."
        )

        result = detect_prohibited_patterns(draft_with_generic_claims, rule)

        assert result.passed is False
        assert "generic_importance_claim" in result.matches
        assert len(result.errors) > 0

    def test_allows_specific_causal_explanation(self) -> None:
        """A well-structured draft with specific causal explanations should pass."""
        rule = LearningDraftRule.default()

        result = detect_prohibited_patterns(_VALID_DRAFT, rule)

        assert result.passed is True, f"Expected passed=True but got errors: {result.errors}"
        assert result.matches == []


    def test_detects_procedure_without_causality(self) -> None:
        """A procedural description without causal reasoning should be detected."""
        rule = LearningDraftRule.default()
        draft_with_unexplained_procedure = (
            "먼저 변수를 선언합니다. 다음으로 값을 할당하고, 마지막으로 출력합니다."
            # No "왜냐하면", "따라서", "원인", "결과", "조건", "검증", "실패"
        )

        result = detect_prohibited_patterns(draft_with_unexplained_procedure, rule)

        assert result.passed is False
        assert "procedure_without_causality" in result.matches

    def test_allows_procedure_with_causal_explanation(self) -> None:
        """A procedural description WITH causal explanation should pass."""
        rule = LearningDraftRule.default()
        draft_with_explained_procedure = (
            "먼저 변수를 선언합니다. 왜냐하면 메모리 할당이 필요하기 때문입니다."
            "다음으로 값을 할당하고, 마지막으로 출력합니다."
        )

        result = detect_prohibited_patterns(draft_with_explained_procedure, rule)

        assert result.passed is True, f"Expected passed=True but got errors: {result.errors}"
        assert result.matches == []


    def test_detects_repeated_boilerplate(self) -> None:
        """Repeated boilerplate lines (same line 3+ times) should be detected."""
        rule = LearningDraftRule.default()
        draft_with_repetition = "This is a boilerplate sentence that exceeds twenty characters.\n" * 5

        result = detect_prohibited_patterns(draft_with_repetition, rule)

        assert result.passed is False
        assert "repeated_boilerplate" in result.matches
        assert len(result.errors) > 0


    def test_valid_draft_passes_all_checks(self) -> None:
        """A well-written draft should pass all prohibited pattern checks."""
        rule = LearningDraftRule.default()

        result = detect_prohibited_patterns(_VALID_DRAFT, rule)

        assert result.passed is True
        assert result.matches == []


    def test_generic_claim_once_does_not_trigger(self) -> None:
        """A single generic importance claim should NOT trigger detection."""
        rule = LearningDraftRule.default()
        draft_with_single_claim = "이 개념은 매우 중요하다."

        result = detect_prohibited_patterns(draft_with_single_claim, rule)

        assert result.passed is True
        assert result.matches == []
