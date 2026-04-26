"""Regression tests — anti-drift density checks (Task 7).

These three tests verify that individual validators reject hollow content:
  Test 1: headers present but only generic filler text -> caught by prohibited-pattern + density
  Test 2: long draft with repetitive boilerplate -> caught by repeated_boilerplate
  Test 3: all sections present but in wrong order -> caught by section-order mismatch
"""

from __future__ import annotations

import pytest

from study.learning_draft_rule import (
    validate_section_structure,
    detect_prohibited_patterns,
    analyze_judgment_density,
)
from study.models import LearningDraftRule


REQUIRED_SECTIONS = [
    "문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
    "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문",
]

_SUBSTANTIVE_CONTENTS: dict[str, str] = {
    "문제 배경": (
        "이 규칙이 필요한 이유는 초안이 형식만 맞추면 독자가 실패를 판별할 기준을 얻지 못하기 때문이다."
    ),
    "개념 정의": (
        "학습초안 생성 규정은 단순한 문서 양식이 아니라 경계를 설정하는 검증 규칙이다."
    ),
    "동작 원리": (
        "동작 원리는 결과 확인이 아니라 이해 판별이며, 인과 흐름을 설명해야 한다."
    ),
    "핵심 판단 기준": (
        "판단 기준은 답을 외웠는지가 아니라 판단 기능이 형성되었는지를 확인한다."
    ),
    "실패 사례": (
        "실패 사례는 단순 경고가 아니라 오개념을 교정하는 장치다."
    ),
    "검증 방법": (
        "검증 방법은 결과 확인이 아니라 이해 판별이며, 반례를 통해 이루어진다."
    ),
    "유사 개념 비교": (
        "유사 개념 비교는 경계 설정이며 차이가 발생하는 조건을 제시해야 한다."
    ),
    "복습 질문": (
        "복습 질문은 기억 확인이 아니라 재구성 압박이다."
    ),
}


def _build_draft_with_sections(section_names: list[str]) -> str:
    """Build a draft containing only the given section names in order."""
    parts = []
    for name in section_names:
        parts.append(f"## {name}\n{_SUBSTANTIVE_CONTENTS.get(name, '')}")
    return "\n\n".join(parts) + "\n"


class TestAntiDriftDensity:

    def test_rejects_headers_with_repeated_generic_filler(self) -> None:
        """A draft with all 8 headers but only generic filler text must fail."""
        rule = LearningDraftRule.default()
        filler = "이 개념은 매우 중요하다.\n" * 5
        parts = []
        for name in REQUIRED_SECTIONS:
            parts.append(f"## {name}\n{filler}")

        draft = "\n\n".join(parts) + "\n"

        # Check prohibited patterns
        pattern_result = detect_prohibited_patterns(draft, rule)
        assert not pattern_result.passed
        error_str = " ".join(pattern_result.errors) if pattern_result.errors else ""
        assert "generic importance claim" in error_str or "generic_importance_claim" in error_str

        # Also check judgment density — thin filler fails
        density_result = analyze_judgment_density(draft, rule)
        assert not density_result.passed
        assert any("judgment density failed" in err for err in density_result.errors)

    def test_rejects_long_but_repetitive_content(self) -> None:
        """A long draft with repetitive boilerplate must fail."""
        rule = LearningDraftRule.default()
        filler_text = (
            "이 개념은 중요하며 다양한 상황에서 활용된다. "
            "이 개념을 잘 이해하면 도움이 된다. "
            "이 개념은 학습에 매우 중요하다."
        )

        parts = []
        for name in REQUIRED_SECTIONS:
            repeated = "\n".join([filler_text for _ in range(20)])
            parts.append(f"## {name}\n{repeated}")

        draft = "\n\n".join(parts) + "\n"

        # Check prohibited patterns — should detect repeated_boilerplate or generic_importance_claim
        pattern_result = detect_prohibited_patterns(draft, rule)
        assert not pattern_result.passed
        error_str = " ".join(pattern_result.errors) if pattern_result.errors else ""
        assert any("boilerplate" in err for err in pattern_result.errors), \
            f"Expected boilerplate error but got: {pattern_result.errors}"

    def test_rejects_wrong_section_order_even_when_long(self) -> None:
        """Sections present but in wrong order — should fail regardless of length."""
        rule = LearningDraftRule.default()
        # Swap sections 4 and 5 (0-indexed 3 and 4)
        swapped_sections = REQUIRED_SECTIONS[:3] + [REQUIRED_SECTIONS[4], REQUIRED_SECTIONS[3]] + REQUIRED_SECTIONS[5:]

        draft = _build_draft_with_sections(swapped_sections)

        section_result = validate_section_structure(draft, rule)
        assert not section_result.passed
        error_str = " ".join(section_result.errors) if section_result.errors else ""
        assert "required section order mismatch" in error_str
