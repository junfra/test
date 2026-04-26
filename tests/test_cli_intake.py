"""Tests for study CLI — intake subcommand."""
from __future__ import annotations

import shutil
from pathlib import Path

from click.testing import CliRunner

from study.cli import main as cli_main


def invoke_study(args: list[str]):
    """Run the study CLI with *args* and return the Click result object."""
    runner = CliRunner()
    return runner.invoke(cli_main, args)


class TestCLIIIntake:

    def _setup_subject(self, ws: Path, sid: str):
        """Create a subject directory structure in Python (avoids CLI cwd issues)."""
        from study.subjects import create_subject as _cs
        _cs(ws, sid, "Topic")

    def test_cli_intake_creates_pasted_text_source(self):
        """Intake command stores pasted_text source in subject's source_reference_data/.

        Steps:
          1. Create a subject directory via Python (to control cwd),
          2. Intake text via CLI (`intake sid --text "content"`),
          3. Load sources from disk and verify kind == "pasted_text".
        """
        ws = Path("/tmp/study-cli-test")
        if ws.exists():
            shutil.rmtree(ws)
        (ws / "subjects").mkdir(parents=True, exist_ok=True)

        sid = "sid"
        topic = "Topic"

        # Create the subject directory directly.
        self._setup_subject(ws, sid)

        # --- intake via CLI ------------------------------------------------
        result = invoke_study(["intake", "-C", str(ws), sid, "--text", "some content to intake"])
        assert result.exit_code == 0, f"intake command failed: {result.output}\n{result.exception}"

        # --- verify --------------------------------------------------------
        from study.intake import load_source_data

        subject_dir = ws / "subjects" / sid
        sources = load_source_data(subject_dir)
        assert any(s.kind == "pasted_text" for s in sources), (
            f"No pasted_text source found. Got: {[s.kind for s in sources]}"
        )

    def test_cli_intake_error_on_missing_subject(self):
        """Intake should fail when subject directory does not exist."""
        ws = Path("/tmp/study-cli-test-missing")
        if ws.exists():
            shutil.rmtree(ws)
        (ws / "subjects").mkdir(parents=True, exist_ok=True)

        result = invoke_study(["intake", "-C", str(ws), "nonexistent", "--text", "content"])
        assert result.exit_code != 0
