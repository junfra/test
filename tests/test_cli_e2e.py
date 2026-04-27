"""End-to-end CLI surface tests for the study harness — full lifecycle + approval gate."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from click.testing import CliRunner

from study.cli import main as cli_main


def invoke_study(args: list[str], cwd: str | None = None):
    """Run the study CLI with *args* using Click's CliRunner, optionally setting a working directory."""
    runner = CliRunner()
    
    def patched_getcwd():
        return cwd
    
    original_getcwd = os.getcwd
    os.getcwd = patched_getcwd  # type: ignore[assignment]
    
    try:
        result = runner.invoke(cli_main, args, catch_exceptions=False)
        return result
    finally:
        os.getcwd = original_getcwd


class TestCLIE2ELifecycle:

    def test_full_cli_lifecycle(self):
        """End-to-end CLI surface test covering all declared commands: new, intake, draft, approve, recall.

        Steps (all via CLI, no direct function calls):
          1. ``study subjects new <ws> test-id "Test Topic"``
          2. ``study intake test-id --text "some content about thermodynamics"``
          3. ``study draft test-id``
          4. ``study approve test-id``
          5. ``study recall test-id --mode=first-pass``

        Every step must exit with code 0 — this is the key verification that all CLI commands
        work together correctly in sequence.
        """
        root = Path("/tmp/cli-e2e-lifecycle")
        if root.exists():
            shutil.rmtree(root)
        (root / "subjects").mkdir(parents=True, exist_ok=True)

        # 1. Create subject via CLI (uses cwd to find subjects dir)
        result = invoke_study(
            ["subjects", "new", "test-id", "Test Topic"],
            cwd=str(root),
        )
        assert result.exit_code == 0, f"New failed: {result.output}"

        # 2. Intake content via CLI (uses -C for workspace root)
        result = invoke_study(
            ["intake", "-C", str(root), "test-id", "--text",
             "some content about thermodynamics and heat transfer"],
        )
        assert result.exit_code == 0, f"Intake failed: {result.output}"

        # 3. Generate draft via CLI (uses -C for workspace root)
        result = invoke_study(
            ["draft", "--skip-validation", "-C", str(root), "test-id"],
        )
        assert result.exit_code == 0, f"Draft failed: {result.output}"

        # 4. Approve (required before recall) via CLI (uses cwd — no -C option)
        result = invoke_study(
            ["subjects", "approve", "test-id"],
            cwd=str(root),
        )
        assert result.exit_code == 0, f"Approve failed: {result.output}"

        # 5. Recall first-pass via CLI (uses -C for workspace root) — THIS IS THE KEY VERIFICATION
        result = invoke_study(
            ["recall", "-C", str(root), "test-id", "--mode=first-pass"],
        )
        assert result.exit_code == 0, f"Recall failed: {result.output}"


    def test_cli_recall_fails_without_approval(self):
        """CLI recall must fail if draft not approved (approval gate enforcement at CLI level).

        Steps:
          1. Create a subject via CLI
          2. Generate a draft (but DO NOT approve)
          3. Attempt ``study recall`` — MUST exit non-zero with error message
        """
        root = Path("/tmp/cli-e2e-fail")
        if root.exists():
            shutil.rmtree(root)
        (root / "subjects").mkdir(parents=True, exist_ok=True)

        # Create subject via CLI
        result = invoke_study(
            ["subjects", "new", "no-approve-test", "Topic"],
            cwd=str(root),
        )
        assert result.exit_code == 0, f"New failed: {result.output}"

        # Generate draft via CLI (but DO NOT approve)
        result = invoke_study(
            ["intake", "-C", str(root), "no-approve-test", "--text", "content"]
        )
        assert result.exit_code == 0, f"Intake failed: {result.output}"

        result = invoke_study(["draft", "--skip-validation", "-C", str(root), "no-approve-test"])
        assert result.exit_code == 0, f"Draft failed: {result.output}"

        # Recall without approval — MUST FAIL (non-zero exit)
        result = invoke_study(
            ["recall", "-C", str(root), "no-approve-test"],
        )
        assert result.exit_code != 0, "CLI recall must fail without approval"
        assert "approved" in result.output.lower() or "Error" in result.output
