"""Tests for prompt construction for LM-driven chapter generation."""
from study.models import SourceReference
from study.prompt_builder import build_chapter_prompt


def test_build_chapter_prompt_demands_exact_seed_json_fields() -> None:
    prompt = build_chapter_prompt(
        topic="Distributed Systems",
        sources=[
            SourceReference(
                kind="pasted_text",
                content="Consensus coordinates replicas under failure without relying on shared memory.",
                metadata={"keyword": "consensus"},
            )
        ],
        chapter_index=0,
        chapter_count=3,
    )

    assert "Return only valid JSON" in prompt
    assert '"topic"' in prompt
    assert '"concept_layers"' in prompt
    assert '"section_structure"' in prompt
    assert '"recall_hooks"' in prompt
    assert '"verification_points"' in prompt
    assert '"bibliography"' in prompt


def test_build_chapter_prompt_forbids_source_copy_paste_body() -> None:
    prompt = build_chapter_prompt(
        topic="Databases",
        sources=[
            SourceReference(
                kind="pasted_text",
                content="Indexes trade write cost for read-path selectivity and access-path control.",
                metadata={},
            )
        ],
        chapter_index=1,
        chapter_count=3,
    )

    assert "Do not copy source paragraphs into the chapter body" in prompt
    assert "bibliography" in prompt.lower()
    assert "Chapter 2 of 3" in prompt
