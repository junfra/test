"""Tests for LMConfig and LearningDraftSystem models — TDD fail-first."""
from pydantic import ValidationError

from study.models import LearningDraftSystem, LMConfig


def test_learning_draft_system_has_exact_seed_fields() -> None:
    assert set(LearningDraftSystem.model_fields) == {
        "topic",
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    }


def test_learning_draft_system_requires_dense_non_empty_arrays() -> None:
    system = LearningDraftSystem(
        topic="Operating Systems",
        concept_layers=["Processes become understandable when scheduling, isolation, and resource ownership are reconstructed together."],
        section_structure=["# Chapter 1: Process Model\n\n## Concept Reconstruction\nA process is not just a running program; it is an owned execution context."],
        recall_hooks=["Explain why a process needs both an address space and scheduler-visible state."],
        verification_points=["The learner can distinguish program text, process state, and scheduler behavior."],
        bibliography=["Source 1: pasted_text"],
    )

    assert system.topic == "Operating Systems"
    assert len(system.concept_layers) == 1


def test_learning_draft_system_rejects_blank_items() -> None:
    try:
        LearningDraftSystem(
            topic="Operating Systems",
            concept_layers=[""],
            section_structure=["# Chapter 1"],
            recall_hooks=["hook"],
            verification_points=["check"],
            bibliography=["Source 1"],
        )
    except ValidationError as exc:
        assert "blank" in str(exc).lower()
    else:
        raise AssertionError("blank ontology item should fail validation")


def test_lm_config_is_separate_from_learning_draft_system() -> None:
    config = LMConfig(provider="mock", model="mock-dense-reconstruction")

    assert config.provider == "mock"
    assert "provider" not in LearningDraftSystem.model_fields
    assert "model" not in LearningDraftSystem.model_fields
