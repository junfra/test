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
"""


__all__ = ["build_chapter_prompt"]
