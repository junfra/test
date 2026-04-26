"""Tests for study.recall — sequential first pass generation (TDD)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Tuple

import pytest


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean temporary workspace root."""
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    return ws


def _create_subject_and_draft(workspace_root: Path, subject_id: str, topic: str) -> Path:
    """Create a subject with an approved draft. Returns subject_root."""
    from study.subjects import create_subject

    root = create_subject(workspace_root, subject_id, topic)

    draft_path = root / "learning_draft.md"
    # Valid markdown structure: # Chapter → ## Section
    draft_path.write_text("""# Introduction to Python

# Chapter 1: Variables and Types
Python has dynamic typing. Integers, floats, strings are built-in types.
Use `type()` to inspect an object's type at runtime.

## Variables and Types
Python has dynamic typing. Integers, floats, strings are built-in types.

## Functions
Functions are defined with `def`. Parameters can have defaults.

# Chapter 2: Control Flow
Control flow determines which code paths execute.

## Control Flow
`if`, `elif`, `else` control execution paths.

# Chapter 3: Advanced Topics
Advanced Python features include decorators and context managers.

## References
1. Python.org documentation
2. Real Python tutorials
""")

    # Approve the draft (required before recall)
    from study.subjects import approve_draft as _ad
    _ad(root)

    return root


# --------------------------------------------------------------------------- #
# 1. test_first_pass_sequential_questions_not_mc
# --------------------------------------------------------------------------- #

class TestSequentialFirstPass:
    def create_subject_and_draft(self, workspace_root: Path, subject_id: str, topic: str) -> Path:
        """Create a subject with an approved draft."""
        return _create_subject_and_draft(workspace_root, subject_id, topic)

    def test_first_pass_sequential_questions_not_mc(self, tmp_workspace: Path) -> None:
        """Questions must be structured open-ended prompts (NOT multiple-choice format).

        - Must check approval_status before generating questions.
        - At least 3 questions should be generated from the draft sections.
        - No "A)" or "a." in any prompt text.
        - Prompt length > 20 chars.
        """
        from study.recall import generate_first_pass_questions

        root = self.create_subject_and_draft(tmp_workspace, "py-basics", "Python")

        questions = generate_first_pass_questions(root)

        assert len(questions) >= 3

        for q in questions:
            assert "A)" not in q.prompt
            assert "a." not in q.prompt
            assert len(q.prompt) > 20

    def test_first_pass_requires_approval(self, tmp_workspace: Path) -> None:
        """Calling generate_first_pass_questions before approval must raise ApprovalRequiredError."""
        from study.recall import generate_first_pass_questions
        from study.models import ApprovalRequiredError
        from study.subjects import create_subject

        root = create_subject(tmp_workspace, "unapproved", "Topic")
        (root / "learning_draft.md").write_text("# Chapter\n## Section\nContent here.")

        with pytest.raises(ApprovalRequiredError):
            generate_first_pass_questions(root)

    def test_first_pass_updates_state(self, tmp_workspace: Path) -> None:
        """After generating questions, progress_state.json should reflect recall_first_pass phase."""
        from study.recall import generate_first_pass_questions
        from study.storage import load_progress

        root = self.create_subject_and_draft(tmp_workspace, "py-basics", "Python")

        # Before: next_recursors_cursor starts at 0
        state_before = load_progress(root)
        assert state_before.next_recursors_cursor == 0

        questions = generate_first_pass_questions(root, n=5)

        # After: phase should be recall_first_pass and cursor advanced
        state_after = load_progress(root)
        assert state_after.phase == "recall_first_pass"
        assert state_after.next_recursors_cursor > 0
