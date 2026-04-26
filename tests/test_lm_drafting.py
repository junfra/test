"""Tests for LM-driven drafting — _build_learning_system, fallback, and _render_draft."""
from pathlib import Path
from unittest.mock import MagicMock

from study.drafting import generate_draft, _build_learning_system, _render_draft, _build_fallback_learning_system
from study.intake import add_sources, load_source_data
from study.lm_client import LMGenerationError
from study.models import LMConfig, LearningDraftSystem, ProgressState, SourceReference
from study.storage import load_progress, save_progress


def _make_subject(tmp_path: Path) -> Path:
    root = tmp_path / "subjects" / "test-subject"
    root.mkdir(parents=True)
    (root / "source_reference_data").mkdir()
    (root / "session_logs").mkdir()
    save_progress(
        root,
        ProgressState(
            subject_id="test-subject",
            topic="Test Topic",
            phase="intake",
        ),
    )
    return root


def test_build_learning_system_calls_lm_once_per_chapter(tmp_path) -> None:
    root = _make_subject(tmp_path)
    add_sources(
        root,
        [
            SourceReference(kind="pasted_text", content="Source A content.", metadata={}),
            SourceReference(kind="pasted_text", content="Source B content.", metadata={}),
        ],
    )

    mock_client = MagicMock()
    system = LearningDraftSystem(
        topic="Test Topic",
        concept_layers=["Layer 1"],
        section_structure=["# Chapter 1: Test\n\n## Concept Reconstruction\nDense content here that is well over the minimum length requirement for a chapter section."],
        recall_hooks=["Hook 1"],
        verification_points=["Check 1"],
        bibliography=["Source A: pasted_text", "Source B: pasted_text"],
    )
    mock_client.generate.return_value = system.model_dump_json()

    result = _build_learning_system(root, "Test Topic", load_source_data(root), lm_client=mock_client)

    assert isinstance(result, LearningDraftSystem)
    # _chapter_count returns max(3, len(sources)), so 2 sources -> 3 chapters
    assert mock_client.generate.call_count == 3


def test_build_fallback_learning_system_on_lm_failure(tmp_path) -> None:
    root = _make_subject(tmp_path)
    add_sources(
        root,
        [SourceReference(kind="pasted_text", content="Content.", metadata={})],
    )

    mock_client = MagicMock()
    mock_client.generate.side_effect = LMGenerationError("mock LM crashed")

    result = _build_learning_system(root, "Test Topic", load_source_data(root), lm_client=mock_client)

    assert isinstance(result, LearningDraftSystem)
    assert len(result.section_structure) >= 3
    assert len(result.section_structure[0]) > 200


def test_render_draft_produces_sectioned_output(tmp_path) -> None:
    system = LearningDraftSystem(
        topic="Test Topic",
        concept_layers=["Concept layer one."],
        section_structure=["# Chapter 1: Test\n\n## Concept Reconstruction\nDense content here."],
        recall_hooks=["Recall hook one."],
        verification_points=["Verification point one."],
        bibliography=["Source 1"],
    )

    draft = _render_draft(system)
    assert "Test Topic" in draft
    assert "# Chapter 1:" in draft
    assert "## Concept Reconstruction" in draft
    assert "## Recall Hooks" in draft
    assert "## Learning Model" in draft
    assert "# References" in draft
    assert "Source 1" in draft


def test_generate_draft_uses_config_not_hardcoded_mock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STUDY_LM_PROVIDER", "mock")
    monkeypatch.setenv("STUDY_LM_MODEL", "mock-dense-reconstruction")

    root = _make_subject(tmp_path)
    add_sources(
        root,
        [SourceReference(kind="pasted_text", content="Source content.", metadata={})],
    )

    draft = generate_draft(root, "Test Topic")
    assert len(draft) >= 3000
    assert draft.count("# Chapter ") >= 3

    state = load_progress(root)
    assert state.phase == "drafting"
    assert state.draft_version_hash is not None
