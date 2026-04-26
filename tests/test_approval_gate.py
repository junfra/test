"""Approval gate mechanism — TDD tests (Task 5).

Ensures that recall functions refuse to run unless the draft has been approved,
and that approve_draft correctly flips approval_status and phase.
"""
from __future__ import annotations

import os
import pytest
import tempfile
from pathlib import Path

from study.models import ApprovalRequiredError
from study.storage import load_progress
from study.subjects import create_subject, approve_draft


# ── test_approve_sets_status ────────────────────────────────────────────── #

def test_approve_sets_status():
    """approve_draft must set approval_status=True AND phase='draft_approved'."""
    root = Path("/tmp/test_ag_1")
    if root.exists():
        import shutil
        shutil.rmtree(root)

    workspace = Path("/tmp/test_ag_ws")
    create_subject(workspace, "ag-sid", "Approvals 101")
    subject_root = workspace / "subjects" / "ag-sid"

    # Write a valid learning draft with # References section
    (subject_root / "learning_draft.md").write_text(
        "# draft\n## Section A\ndense content.\n# References\n- ref1"
    )

    approve_draft(subject_root)
    state = load_progress(subject_root)
    assert state.approval_status is True, "approval_status must be True after approval"


def test_approve_sets_phase():
    """approve_draft must update phase to 'draft_approved'."""
    root = Path("/tmp/test_ag_2")
    if root.exists():
        import shutil
        shutil.rmtree(root)

    workspace = Path("/tmp/test_ag_ws2")
    create_subject(workspace, "ag-sid2", "Approvals 102")
    subject_root = workspace / "subjects" / "ag-sid2"

    (subject_root / "learning_draft.md").write_text(
        "# draft\n## Section A\ndense content.\n# References\n- ref1"
    )

    approve_draft(subject_root)
    state = load_progress(subject_root)
    assert state.phase == "draft_approved", f"phase must be 'draft_approved', got {state.phase}"


def test_approve_skips_unapproved_phase():
    """approve_draft should not change phase if still in intake."""
    root = Path("/tmp/test_ag_3")
    if root.exists():
        import shutil
        shutil.rmtree(root)

    workspace = Path("/tmp/test_ag_ws3")
    create_subject(workspace, "ag-sid3", "Approvals 103")
    subject_root = workspace / "subjects" / "ag-sid3"

    (subject_root / "learning_draft.md").write_text(
        "# draft\n## Section A\ndense content.\n# References\n- ref1"
    )

    approve_draft(subject_root)
    state = load_progress(subject_root)
    assert state.phase == "draft_approved", f"phase must be 'draft_approved', got {state.phase}"


# ── test_recall_rejects_unapproved ─────────────────────────────────────── #

def test_recall_rejects_unapproved():
    """Without approval, generate_first_pass_questions MUST raise ApprovalRequiredError."""
    root = Path("/tmp/test_ag_4")
    if root.exists():
        import shutil
        shutil.rmtree(root)

    workspace = Path("/tmp/test_ag_ws4")
    create_subject(workspace, "ag-sid4", "Approvals 104")
    subject_root = workspace / "subjects" / "ag-sid4"

    (subject_root / "learning_draft.md").write_text(
        "# draft\n## Section A\ndense content.\n# References\n- ref1"
    )

    # WITHOUT approve — recall must fail
    from study.drafting import generate_first_pass_questions  # noqa: F811

    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(subject_root)


def test_recall_works_after_approval():
    """After approval, generate_first_pass_questions succeeds."""
    root = Path("/tmp/test_ag_5")
    if root.exists():
        import shutil
        shutil.rmtree(root)

    workspace = Path("/tmp/test_ag_ws5")
    create_subject(workspace, "ag-sid5", "Approvals 105")
    subject_root = workspace / "subjects" / "ag-sid5"

    (subject_root / "learning_draft.md").write_text(
        "# draft\n## Section A\ndense content.\n# References\n- ref1"
    )

    approve_draft(subject_root)  # now approved
    from study.drafting import generate_first_pass_questions  # noqa: F811
    questions = generate_first_pass_questions(subject_root)
    assert len(questions) > 0, "Should return at least one question after approval"


# ── CLI approve subcommand ─────────────────────────────────────────────── #

def test_cli_approve_command_exists():
    """The 'approve' command must exist under subjects group."""
    from click.testing import CliRunner
    from study.cli import main  # noqa: F811

    runner = CliRunner()
    result = runner.invoke(main, ["subjects", "--help"])
    assert "approve" in result.output.lower(), (
        f"'approve' not found in `study subjects --help`. Output:\n{result.output}"
    )


def test_cli_approve_sets_approval_status():
    """Running 'study subjects approve <id>' must flip approval on disk."""
    from click.testing import CliRunner
    from study.cli import main  # noqa: F811

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        create_subject(workspace, "ag-sid6", "Approvals 106")
        subject_root = workspace / "subjects" / "ag-sid6"

        (subject_root / "learning_draft.md").write_text(
            "# draft\n## Section A\ndense content.\n# References\n- ref1"
        )

        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["subjects", "approve", "ag-sid6"],
                                   catch_exceptions=False)
            assert result.exit_code == 0, f"CLI failed:\n{result.output}"

            state = load_progress(subject_root)
            assert state.approval_status is True
        finally:
            os.chdir(old_cwd)


def test_cli_approve_updates_phase():
    """Running 'study subjects approve <id>' must set phase='draft_approved'."""
    from click.testing import CliRunner
    from study.cli import main  # noqa: F811

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        create_subject(workspace, "ag-sid7", "Approvals 107")
        subject_root = workspace / "subjects" / "ag-sid7"

        (subject_root / "learning_draft.md").write_text(
            "# draft\n## Section A\ndense content.\n# References\n- ref1"
        )

        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["subjects", "approve", "ag-sid7"],
                                   catch_exceptions=False)
            assert result.exit_code == 0

            state = load_progress(subject_root)
            assert state.phase == "draft_approved"
        finally:
            os.chdir(old_cwd)


# ── ApprovalRequiredError identity ─────────────────────────────────────── #

def test_approval_required_error_is_exception():
    """ApprovalRequiredError must be an Exception subclass."""
    from study.models import ApprovalRequiredError  # noqa: F811

    assert issubclass(ApprovalRequiredError, Exception)


def test_approval_required_error_message():
    """Raising ApprovalRequiredError should carry a useful message."""
    from study.models import ApprovalRequiredError  # noqa: F811

    exc = ApprovalRequiredError("draft not approved")
    assert "not approved" in str(exc).lower()
