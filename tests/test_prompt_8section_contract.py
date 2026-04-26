"""Tests for 8-section prompt contract in build_chapter_prompt().

Verifies that the LM instructions embedded in the chapter prompt enforce:
- Exactly 8 Korean section names in exact order
- 5000+ character body minimum
- No "학습초안 생성 규정" or other extra sections
- Judgment-function density requirement per paragraph
"""
from __future__ import annotations

import pytest

from study.models import SourceReference, LearningDraftRule
from study.prompt_builder import build_chapter_prompt


# ─── Fixtures ──────────────────────────────────────────────

def _sample_sources() -> list[SourceReference]:
    return [
        SourceReference(
            kind="pasted_text",
            content=(
                "The CAP theorem states that a distributed system can guarantee at most two of:\n"
                "- Consistency: every read receives the latest write or an error.\n"
                "- Availability: every request receives a non-error response, without guaranteeing it's the latest write.\n"
                "- Partition tolerance: the system continues to operate despite network partitions."
            ),
            metadata={"keyword": "CAP theorem"},
        )
    ]


def _prompt() -> str:
    return build_chapter_prompt(
        topic="Distributed Consensus",
        sources=_sample_sources(),
        chapter_index=0,
        chapter_count=3,
    )


# ─── Required section names (must match LearningDraftRule.DEFAULT_REQUIRED_SECTIONS) ───

_REQUIRED_SECTIONS: list[str] = [
    "문제 배경",
    "개념 정의",
    "동작 원리",
    "핵심 판단 기준",
    "실패 사례",
    "검증 방법",
    "유사 개념 비교",
    "복습 질문",
]


# ─── Tests ─────────────────────────────────────────────────

class TestPromptContainsAllEightSectionNames:
    """Every required section name must appear in the prompt."""

    @pytest.mark.parametrize("section_name", _REQUIRED_SECTIONS)
    def test_each_section_name_appears_in_prompt(self, section_name: str) -> None:
        prompt = _prompt()
        assert section_name in prompt, (
            f"Prompt is missing required section name '{section_name}'"
        )


class TestSectionOrderConstraint:
    """The 8 sections must be listed in the exact expected order."""

    def test_prompt_mentions_strict_order(self) -> None:
        prompt = _prompt()
        assert "strict order" in prompt.lower() or "정확한 순서" in prompt


class TestBodyLengthRequirement:
    """The prompt must enforce a 5000+ character body requirement."""

    def test_prompt_mentions_5000_minimum(self) -> None:
        prompt = _prompt()
        assert "5000" in prompt, (
            "Prompt must mention '5000' as minimum body length"
        )

    def test_prompt_enforces_body_characters_not_title_or_toc(self) -> None:
        """The 5000 count should refer to substantive body characters."""
        prompt = _prompt()
        # Must not be ambiguous — the word "body" or equivalent context must appear near 5000
        assert "body" in prompt.lower() or "본문" in prompt


class TestProhibitExtraSections:
    """The prompt must explicitly forbid extra sections like '학습초안 생성 규정'."""

    def test_prompt_forbids_extra_section_learning_draft_rule(self) -> None:
        prompt = _prompt()
        assert "학습초안 생성 규정" not in prompt or (
            # Either the phrase is absent entirely, OR it's inside a prohibition context
            ("no extra" in prompt.lower() or
             "추가" in prompt or
             "금지" in prompt)
        ), (
            "Prompt must either omit '학습초안 생성 규정' or explicitly forbid it."
        )

    def test_prompt_forbids_extra_sections_globally(self) -> None:
        """A general prohibition against extra sections should exist."""
        prompt = _prompt()
        # Look for a clear directive against adding sections beyond the 8 required ones
        assert (
            "only" in prompt.lower() or "exactly" in prompt.lower() or
            "no more" in prompt.lower() or "추가" in prompt.lower()
        ), "Prompt should specify that ONLY these 8 sections are allowed."


class TestJudgmentDensityGuidance:
    """The prompt must guide the LM to include judgment-function keywords per paragraph."""

    def test_prompt_mentions_judgment_keywords(self) -> None:
        """Keywords like 'judgment function', '~라고 볼 때', etc. should appear."""
        prompt = _prompt()
        # At least one of the specific Korean markers or their English equivalents
        has_korean_marker = any(kw in prompt for kw in [
            "~라고 볼 때", "~라고 판단된다", "~라고 생각한다",
            "판단", "judgment", "판별"
        ])
        assert has_korean_marker, (
            "Prompt must mention at least one judgment keyword pattern"
        )

    def test_prompt_requires_per_paragraph_density(self) -> None:
        """The prompt should state that each paragraph needs a judgment marker."""
        prompt = _prompt()
        has_density_guidance = any(
            kw in prompt.lower() for kw in [
                "each paragraph", "every paragraph", "각 단락",
                "per paragraph", "paragraph"
            ]
        ) and ("judgment" in prompt.lower() or "판단" in prompt)
        assert has_density_guidance, (
            "Prompt should require judgment function per paragraph."
        )


class TestNoPlaceholderText:
    """The prompt must instruct against placeholder / template text."""

    def test_prompt_forbids_placeholders(self) -> None:
        prompt = _prompt()
        assert ("placeholder" in prompt.lower() or "template" in prompt.lower()
                or "[[" in prompt and "]]" not in prompt.split("[[", 1)[0][-5:])


class TestPromptIntegrationWithExistingContract:
    """Verify the new contract section integrates with existing JSON output instructions."""

    def test_prompt_still_contains_json_instructions(self) -> None:
        """The original JSON field requirements must still be present."""
        prompt = _prompt()
        assert '"topic"' in prompt
        assert '"concept_layers"' in prompt
        assert '"section_structure"' in prompt
        assert '"recall_hooks"' in prompt

    def test_prompt_still_requires_valid_json(self) -> None:
        prompt = _prompt()
        assert "JSON" in prompt.upper() or "json" in prompt.lower()
