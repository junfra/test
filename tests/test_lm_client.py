"""Tests for LM client providers and mock dense output."""
from study.lm_client import LMClient, LMGenerationError, parse_learning_system_json
from study.models import LMConfig, LearningDraftSystem
from study.prompt_builder import build_chapter_prompt


def test_mock_lm_generates_parseable_learning_draft_system() -> None:
    prompt = build_chapter_prompt(
        topic="Operating Systems",
        sources=[],
        chapter_index=0,
        chapter_count=3,
    )

    client = LMClient(LMConfig(provider="mock", model="mock-dense-reconstruction"))
    raw = client.generate(prompt)
    system = parse_learning_system_json(raw)

    assert isinstance(system, LearningDraftSystem)
    assert set(system.model_fields) == {
        "topic",
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    }
    assert system.topic == "Operating Systems"
    assert "# Chapter 1:" in system.section_structure[0]
    assert len(system.section_structure[0]) > 700
