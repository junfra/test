"""Tests for recall extraction with LM-generated section structure."""
from pathlib import Path

from study.models import ProgressState
from study.recall import extract_sections, generate_first_pass_questions
from study.storage import save_progress


def test_extract_sections_reads_lm_generated_chapter_subsections() -> None:
    draft = """# Operating Systems — LM-Driven Concept Reconstruction

# Chapter 1: Process Reconstruction

## Concept Reconstruction
A process is an owned execution context.

## Mechanism
The scheduler changes observable execution.

## Learning Model
The learner reconstructs state, transition, and check.

# References
1. Source 1
"""

    sections = extract_sections(draft)

    titles = [title for _chapter, title, _content in sections]
    assert "Concept Reconstruction" in titles
    assert "Mechanism" in titles
    assert "Learning Model" in titles


def test_recall_questions_remain_approval_gated_for_lm_draft(tmp_path) -> None:
    root = tmp_path / "subjects" / "os"
    root.mkdir(parents=True)
    save_progress(
        root,
        ProgressState(
            subject_id="os",
            topic="Operating Systems",
            phase="draft_approved",
            approval_status=True,
            draft_version_hash="a" * 64,
        ),
    )
    (root / "learning_draft.md").write_text(
        """# Operating Systems — LM-Driven Concept Reconstruction

# Chapter 1: Process Reconstruction

## Concept Reconstruction
A process is an owned execution context.

## Mechanism
The scheduler changes observable execution.

## Learning Model
The learner reconstructs state, transition, and check.

# References
1. Source 1
""",
        encoding="utf-8",
    )

    questions = generate_first_pass_questions(root, n=3)

    assert len(questions) == 3
    assert questions[0].topic == "Concept Reconstruction"
