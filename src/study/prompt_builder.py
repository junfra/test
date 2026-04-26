"""Prompt construction for LM-driven chapter generation."""
from __future__ import annotations

from .models import SourceReference


def _compact_text(text: str, limit: int = 700) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "\u2026"


def _source_packet(sources: list[SourceReference]) -> str:
    if not sources:
        return "No source material was provided. Build a conceptual primer from general domain knowledge."

    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        keyword = source.metadata.get("keyword", "")
        keyword_text = f", keyword={keyword}" if keyword else ""
        lines.append(
            f"Source {index}: kind={source.kind}{keyword_text}\n"
            f"Digest: {_compact_text(source.content)}"
        )

    return "\n\n".join(lines)


# ── 8-section learning-draft contract (must mirror LearningDraftRule.DEFAULT_REQUIRED_SECTIONS) ──

_LEARNING_DRAFT_CONTRACT = """\
--- LEARNING DRAFT RENDERING CONTRACT ---

When producing the final rendered chapter body for section_structure, you MUST follow this contract exactly.

## Required Section Names and Order
The rendered markdown must contain EXACTLY these 8 sections in STRICT ORDER:
1. 문제 배경 (Problem Background)
2. 개념 정의 (Concept Definition)
3. 동작 원리 (Operating Mechanism)
4. 핵심 판단 기준 (Core Judgment Criteria)
5. 실패 사례 (Failure Case)
6. 검증 방법 (Verification Method)
7. 유사 개념 비교 (Similar Concept Comparison)
8. 복습 질문 (Review Questions)

No section may be added, omitted, renamed, or reordered. No extra sections whatsoever — do NOT add "학습초안 생성 규정" or any other section beyond these eight. The output must contain ONLY these 8 section headers and their content.

## Body Length Requirement
The body characters of the rendered chapter MUST total at least 5000 characters. This count refers to substantive prose in the body sections, excluding title lines and table-of-contents references. Aim for a dense, information-rich draft well within 7000 characters.

## Judgment-Function Keyword Density per Paragraph
Every paragraph must contain at least one judgment-function keyword that signals analytical reasoning. Acceptable markers include:
- ~라고 볼 때 (can be viewed as)
- ~라고 판단된다 (judged to be)
- ~라고 생각한다 (I think / consider that)

Each major section should feature multiple such markers distributed across its paragraphs. This ensures the draft demonstrates genuine judgment-function reasoning rather than passive description.

## Prohibited Content
Do NOT include:
- Placeholder text, template markers, or "[...]" stubs
- Template-only compliance sections like "학습초안 생성 규정"
- Generic importance claims without causal linkage
- Thin section bodies (each section needs substantive body content)

Return only valid JSON with the required fields. The section_structure field must contain the actual markdown chapter body following the contract above.
"""


def build_chapter_prompt(
    *,
    topic: str,
    sources: list[SourceReference],
    chapter_index: int,
    chapter_count: int,
) -> str:
    chapter_number = chapter_index + 1

    return f"""You are generating an LM-driven concept reconstruction chapter.

Topic: {topic}
Chapter: Chapter {chapter_number} of {chapter_count}

Source digests:
{_source_packet(sources)}

Hard requirements:
- The LM must generate the actual chapter content.
- Do not copy source paragraphs into the chapter body.
- Use sources as evidence and bibliography material, not as body prose.
- Write dense Red Hat-style explanatory structure: concept, mechanism, consequence, recall hook, verification point.
- Make this chapter substantive enough that three chapters together exceed 3000 characters.
- Each major section must surface concept reconstruction, recall hooks, and the learning model.
- Return only valid JSON.
- The JSON object must contain exactly these fields:
  "topic": string
  "concept_layers": array of strings
  "section_structure": array of strings
  "recall_hooks": array of strings
  "verification_points": array of strings
  "bibliography": array of strings

The "section_structure" value must contain the actual markdown chapter body for this chapter.
The chapter body must start with "# Chapter {chapter_number}:" and include "## Concept Reconstruction", "## Mechanism", and "## Learning Model".

{_LEARNING_DRAFT_CONTRACT}
"""


__all__ = ["build_chapter_prompt"]
