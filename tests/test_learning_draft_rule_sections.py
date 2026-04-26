"""Tests for SectionStructureValidator."""
from __future__ import annotations

import pytest

from study.learning_draft_rule import validate_section_structure
from study.models import LearningDraftRule


# ─── Fixtures ──────────────────────────────────────────────

_VALID_DRAFT = """\
## 문제 배경
This is the problem background section. It explains why this topic matters...

## 개념 정의
Here we define the key concepts that are central to understanding this topic...

## 동작 원리
The mechanism works as follows: first step, second step, third step...

## 핵심 판단 기준
To determine whether a case falls under this concept, apply these criteria:
- Criterion 1
- Criterion 2
- Criterion 3

## 실패 사례
A common failure scenario is when the boundary conditions are not properly identified.

## 검증 방법
Verification can be done by checking each judgment function against test cases...

## 유사 개념 비교
This concept should not be confused with related concepts such as:
- Similar Concept A: differs in key aspect X
- Similar Concept B: differs in key aspect Y

## 복습 질문
1. What are the three criteria?
2. Describe a failure scenario.
"""


def _rule() -> LearningDraftRule:
    return LearningDraftRule.default()


# ─── Tests ─────────────────────────────────────────────────


class TestValidateSectionStructure:
    """Tests for section order validation."""

    def test_validate_section_structure_accepts_exact_required_order(self) -> None:
        """A valid draft with all 8 required sections in correct order should pass."""
        rule = _rule()
        result = validate_section_structure(_VALID_DRAFT, rule)

        assert result.passed is True, f"Expected passed=True but got errors: {result.errors}"
        assert len(result.found_sections) == 8
        assert result.errors == []

    def test_validate_section_structure_rejects_missing_section(self) -> None:
        """A draft missing a required section should fail."""
        rule = _rule()
        # Remove the "실패 사례" section entirely
        draft_no_failure = _VALID_DRAFT.replace(
            "## 실패 사례\nA common failure scenario is when the boundary conditions are not properly identified.\n\n",
            ""
        )

        result = validate_section_structure(draft_no_failure, rule)

        assert result.passed is False
        assert len(result.errors) > 0
        # Should contain an order mismatch error mentioning the missing section
        error_text = " ".join(result.errors)
        assert "실패 사례" in error_text or "order mismatch" in error_text.lower()

    def test_validate_section_structure_rejects_extra_section(self) -> None:
        """A draft with an extra unknown section header should fail."""
        rule = _rule()
        draft_with_extra = _VALID_DRAFT + "\n## 학습초안 생성 규정\nThis is a prohibited extra section.\n"

        result = validate_section_structure(draft_with_extra, rule)

        assert result.passed is False
        assert len(result.errors) > 0
        error_text = " ".join(result.errors)
        assert "extra section detected" in error_text.lower() or "extra section" in error_text
