"""Tests for learning draft rule: judgment density analysis."""
from __future__ import annotations

import pytest

from study.learning_draft_rule import (
    JudgmentDensityResult,
    analyze_judgment_density,
)


class TestJudgmentDensityRejectsThinGenericParagraphs:
    def test_thin_generic_paragraph_fails(self):
        """Thin text should fail with 'judgment density failed:' in error."""
        thin_text = "\n\n".join([
            "The importance of continuous learning is essential.",
            "Education plays a vital role in personal development.",
            "Knowledge acquisition drives growth and success.",
        ])

        result = analyze_judgment_density(thin_text)

        assert not result.passed
        assert len(result.weak_paragraph_indexes) > 0
        # Verify the exact error format (v2 fix anchor)
        assert any("judgment density failed:" in e for e in result.errors), \
            f"Expected 'judgment density failed:' in errors, got: {result.errors}"

    def test_no_judgment_functions_across_multiple_paragraphs(self):
        """Multiple paragraphs without judgment functions should all be flagged."""
        text = "\n\n".join([
            "Learning is important for everyone.",
            "Technology continues to evolve rapidly.",
            "The world is changing fast.",
            "Adaptation requires effort and dedication.",
            "Success depends on continuous improvement.",
            "Knowledge builds upon itself over time.",
        ])

        result = analyze_judgment_density(text)

        assert not result.passed
        # All 6 paragraphs should be weak (none have judgment functions)
        assert len(result.weak_paragraph_indexes) == 6
        assert all(i in range(6) for i in result.weak_paragraph_indexes), \
            f"Expected indexes [0-5], got: {result.weak_paragraph_indexes}"

    def test_short_paragraphs_below_threshold(self):
        """Very short paragraphs should be automatically weak."""
        text = "\n\n".join([
            "Short.",
            "Tiny.",
            "Brief.",
        ])

        result = analyze_judgment_density(text)

        assert not result.passed
        # All 3 are below 30 chars threshold
        assert len(result.weak_paragraph_indexes) == 3


class TestJudgmentDensityAcceptsParagraphsWithJudgmentFunctions:
    def test_eight_substantive_passing_paragraphs(self):
        """Exactly 8 substantive Korean paragraphs, each with a judgment function."""
        text = "\n\n".join([
            "이유는 학습의 필요성이 정적인 지식으로는 부족하기 때문이다. 왜냐하면 빠르게 변화하는 환경에서 오래된 지식은 더 이상 도움이 되지 않기 때문이다.",

            "문제는 경계 설정에 있으며 구분하는 기준이 중요하다. 어떤 것이 포함되고 무엇이 제외되는지를 정의해야 한다.",

            "동작 원리와 작동 상태가 인과 조건으로 결과에 영향을 준다. 흐름을 이해하려면 상태 변화의 과정을 추적해야 한다.",

            "판단 기준은 올바른 이해와 잘못된 오해 사이의 차이를 명확히 한다. 정확한 판단을 위해서는 검증이 필요하다.",

            "실패의 원인, 증상, 그리고 무너진 학습 패턴을 진단해야 한다. 오류가 발생한 이유를 파악하는 것이 중요하다.",

            "검증과 확인과 테스트로 판별하고 증명할 수 있는 반례를 찾아야 한다. 이해를 입증하려면 다양한 조건에서 실험해야 한다.",

            "유사한 것들 사이의 비교와 차이, 다름을 이해해야 한다. 표면적인 유사성이 아닌 본질적인 차이를 구별해야 한다.",

            "왜냐하면 문제에서 부재하는 것은 붕괴되지 않은 이해의 이유이다. 진정한 학습은 단순 암기가 아니라 작동 원리를 이해하는 것이다.",
        ])

        result = analyze_judgment_density(text)

        assert result.passed, f"Expected pass but got errors: {result.errors}"
        assert result.paragraph_count == 8
        assert len(result.weak_paragraph_indexes) == 0

    def test_mixed_korean_and_weak(self):
        """Korean paragraphs with judgment functions pass; thin ones fail."""
        text = "\n\n".join([
            "이유는 학습의 필요성이 정적인 지식으로는 부족하기 때문이다.",  # len=33, strong
            "Short.",  # weak (<30 chars)
            "문제는 경계 설정에 있으며 구분하는 기준이 중요하다. 정의해야 한다.",  # len=48, strong
        ])

        result = analyze_judgment_density(text)

        assert not result.passed, "Only 2 strong paragraphs out of 3 total"
        # Paragraph at index 1 (short one) should be weak; indices 0 and 2 are strong
        assert len(result.weak_paragraph_indexes) == 1, \
            f"Expected exactly index 1 to be weak, got: {result.weak_paragraph_indexes}"
        assert result.weak_paragraph_indexes == [1]

    def test_mixed_korean_and_weak_2(self):
        """Another mixed scenario with short and strong paragraphs."""
        text = "\n\n".join([
            "판단 기준은 올바른 이해와 잘못된 오해 사이의 차이를 명확히 한다.",  # len=38, strong
            "Tiny.",  # weak (<30 chars)
            "이유는 학습의 필요성이 정적인 지식으로는 부족하기 때문이다.",  # len=33, strong
        ])

        result = analyze_judgment_density(text)

        assert not result.passed, "Only 2 strong paragraphs out of 3 total"
        assert len(result.weak_paragraph_indexes) == 1
        assert result.weak_paragraph_indexes == [1]

    def test_paragraph_count_requirement(self):
        """Even with strong paragraphs, fewer than 8 should fail."""
        text = "\n\n".join([
            "이유는 학습의 필요성이 정적인 지식으로는 부족하기 때문이다.",  # len=33, strong
            "문제는 경계 설정에 있으며 구분하는 기준이 중요하다. 정의해야 한다.",  # len=48, strong
            "동작 원리와 작동 상태가 인과 조건으로 결과에 영향을 준다.",  # len=33, strong
        ])

        result = analyze_judgment_density(text)

        assert not result.passed, "Fewer than 8 paragraphs should fail even with strong content"
        # All 3 have judgment functions and >=30 chars so none are weak
        assert len(result.weak_paragraph_indexes) == 0, \
            f"Expected no weak indexes (all strong), got: {result.weak_paragraph_indexes}"
        assert result.paragraph_count == 3

    def test_all_strong_and_8_plus_passes(self):
        """8+ Korean paragraphs with judgment functions pass."""
        text = "\n\n".join([
            "이유는 학습의 필요성이 정적인 지식으로는 부족하기 때문이다. 왜냐하면 빠르게 변화하는 환경에서 오래된 지식은 더 이상 도움이 되지 않기 때문이다.",

            "문제는 경계 설정에 있으며 구분하는 기준이 중요하다. 어떤 것이 포함되고 무엇이 제외되는지를 정의해야 한다.",

            "동작 원리와 작동 상태가 인과 조건으로 결과에 영향을 준다. 흐름을 이해하려면 상태 변화의 과정을 추적해야 한다.",

            "판단 기준은 올바른 이해와 잘못된 오해 사이의 차이를 명확히 한다. 정확한 판단을 위해서는 검증이 필요하다.",

            "실패의 원인, 증상, 그리고 무너진 학습 패턴을 진단해야 한다. 오류가 발생한 이유를 파악하는 것이 중요하다.",

            "검증과 확인과 테스트로 판별하고 증명할 수 있는 반례를 찾아야 한다. 이해를 입증하려면 다양한 조건에서 실험해야 한다.",

            "유사한 것들 사이의 비교와 차이, 다름을 이해해야 한다. 표면적인 유사성이 아닌 본질적인 차이를 구별해야 한다.",

            "왜냐하면 문제에서 부재하는 것은 붕괴되지 않은 이해의 이유이다. 진정한 학습은 단순 암기가 아니라 작동 원리를 이해하는 것이다.",
        ])

        result = analyze_judgment_density(text)

        assert result.passed, f"Expected pass but got errors: {result.errors}"
        assert result.paragraph_count == 8
        assert len(result.weak_paragraph_indexes) == 0
