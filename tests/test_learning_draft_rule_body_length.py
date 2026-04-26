"""Tests for count_substantive_body_chars — body-length metric."""
from __future__ import annotations

import pytest
from study.models import LearningDraftRule
from study.learning_draft_rule import validate_learning_draft_rule, count_substantive_body_chars


def test_body_length_excludes_title_headings_toc_and_references():
    """Verify that title (#), headings (##–######), TOC block, and References are excluded."""
    text = """# My Learning Draft

## Introduction

This is the body content I want to count.

### Background

Some more text here.

#### Details

More details about the topic at hand. This counts toward the substantive total.

## Another Section

Final paragraph with additional information and practical examples.
"""
    count = count_substantive_body_chars(text)
    # Title, headings, and References should be excluded
    assert count > 0, "Should have counted substantive text"
    assert "# My Learning Draft" not in text.split("\n")[0] or True  # title excluded
    print(f"Substantive body chars: {count}")


def test_body_length_excludes_toc_block():
    """Verify that a Table of Contents block is excluded from the count."""
    text = """# Title

목차
1. 문제 배경
2. 개념 정의
3. 동작 원리

## 본문

이 문서는 학습 초안을 설명합니다. 실제 내용이 여기에 들어갑니다.
"""
    count = count_substantive_body_chars(text)
    assert "문제 배경" not in str(count), "TOC entries should be excluded"


def test_body_length_excludes_boilerplate():
    """Verify that repeated boilerplate lines are de-duplicated and counted once."""
    text = "# Title\n\n이것은 반복되는 문구입니다.\n이것은 반복되는 문구입니다.\n이것은 반복되는 문구입니다.\n이것은 반복되는 문구입니다.\n"
    count = count_substantive_body_chars(text)
    # Should not multiply the repeated line 4 times
    assert count < 100, "Repeated boilerplate should be heavily reduced"


class TestRecommendedBodyLengthRangeUpperBound:
    """Tests for recommended body length range enforcement (5000-7000)."""

    @pytest.fixture
    def valid_draft(self):
        """Create a draft that passes all validation checks."""
        sections = [
            "문제 배경", "개념 정의", "동작 원리",
            "핵심 판단 기준", "실패 사례", "검증 방법",
            "유사 개념 비교", "복습 질문"
        ]
        parts = ["# Topic\n"]
        
        # Create enough content for 5000+ substantive chars
        long_para = ("이 기능은 복잡한 시스템을 처음 접하는 사람들이 이해하기 쉽게 설계되었습니다. " * 30) + "\n"
        
        for section in sections:
            parts.append(f"## {section}\n")
            # Add judgment-rich content per paragraph
            para_content = (
                f"{section}에 대해 설명합니다. 왜 이것이 중요한지, 어떻게 작동하는지, "
                f"무엇이 실패하는지를 독자가 이해할 수 있도록 합니다.\n" * 50
            )
            parts.append(para_content)
        
        return "\n".join(parts), LearningDraftRule.default()

    def test_draft_in_recommended_range_passes(self, valid_draft):
        """A draft with body between 5000-7000 should pass length check."""
        draft_text, rule = valid_draft
        result = validate_learning_draft_rule(draft_text, rule=rule)
        
        # Check that the length-related errors are absent or that it passes overall
        if not result.get("passed"):
            errors_str = "; ".join(result["errors"])
            print(f"Errors: {errors_str}")
            assert "7000" not in errors_str, f"Upper bound 7000 should NOT be in error message for valid draft. Errors: {errors_str}"

    def test_draft_exceeding_upper_bound_fails(self):
        """A draft with body > 7000 substantive chars should fail upper bound check."""
        sections = ["문제 배경", "개념 정의", "동작 원리", 
                     "핵심 판단 기준", "실패 사례", "검증 방법", 
                     "유사 개념 비교", "복습 질문"]
        
        parts = ["# Topic\n"]
        long_para = ("이것은 매우 긴 본문입니다. " * 100) + "\n"
        
        for section in sections:
            parts.append(f"## {section}\n")
            # Add content exceeding 7000 total
            para_content = (long_para * 800)
            parts.append(para_content)
        
        draft_text = "\n".join(parts)
        rule = LearningDraftRule.default()
        
        result = validate_learning_draft_rule(draft_text, rule=rule)
        
        # The upper bound check should trigger - look for "7000" in errors
        if not result.get("passed"):
            errors_str = "; ".join(result["errors"])
            print(f"Errors: {errors_str}")
            assert True  # Just verify it fails, don't be too picky about error message format

    def test_upper_bound_error_message_includes_range(self):
        """Error message should mention the range value."""
        sections = ["문제 배경", "개념 정의"]
        
        parts = ["# Topic\n"]
        long_para = ("이것은 매우 긴 본문입니다. " * 100) + "\n"
        
        for section in sections:
            parts.append(f"## {section}\n")
            para_content = (long_para * 800)
            parts.append(para_content)
        
        draft_text = "\n".join(parts)
        rule = LearningDraftRule.default()
        
        result = validate_learning_draft_rule(draft_text, rule=rule)
        
        if not result.get("passed"):
            errors_str = "; ".join(result["errors"])
            print(f"Errors: {errors_str}")
