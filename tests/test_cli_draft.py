"""Tests for study CLI — draft subcommand."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from click.testing import CliRunner

from study.cli import main as cli_main


def invoke_study(args: list[str]):
    """Run the study CLI with *args* and return the Click result object."""
    runner = CliRunner()
    return runner.invoke(cli_main, args)


class TestCLIDraft:

    def _setup_subject(self, ws: Path, sid: str, topic: str):
        """Create a subject directory in Python (avoids CLI cwd issues)."""
        from study.subjects import create_subject as _cs
        _cs(ws, sid, topic)

    def test_cli_draft_generates_learning_draft_with_chapters(self):
        """Draft command creates learning_draft.md with ≥ 3 chapters.

        Steps:
          1. Create a subject directory via Python (to control cwd),
          2. Intake some content so generate_draft has material,
          3. Run ``study draft -C <ws> sid``,
          4. Read learning_draft.md and verify ≥ 3 # headers.
        """
        ws = Path("/tmp/study-cli-test-draft")
        if ws.exists():
            shutil.rmtree(ws)
        (ws / "subjects").mkdir(parents=True, exist_ok=True)

        sid = "sid"
        topic = "Thermodynamics and Entropy"

        # Create subject via Python (avoids CliRunner cwd issues).
        self._setup_subject(ws, sid, topic)

        # Intake some content so generate_draft has material.
        from study.intake import add_sources as _add
        from study.models import SourceReference

        _add(
            ws / "subjects" / sid,
            [SourceReference(kind="pasted_text", content="Entropy is a measure of disorder in thermodynamic systems.")],
        )

        # --- draft via CLI -------------------------------------------------
        result = invoke_study(["draft", "--skip-validation", "-C", str(ws), sid])
        assert result.exit_code == 0, f"draft command failed: {result.output}\n{result.exception}"

        # --- verify output file --------------------------------------------
        draft_path = ws / "subjects" / sid / "learning_draft.md"
        assert draft_path.exists(), "Draft file must be created"

        md = draft_path.read_text()
        sections = [s.strip() for s in re.findall(r'^##\s+(.+?)$', md, flags=re.MULTILINE)]
        assert len(sections) == 8, (
            f"Draft should have exactly 8 sections, got {len(sections)}: {sections}"
        )

    def test_cli_draft_error_on_missing_subject(self):
        """Draft command fails when subject directory does not exist."""
        ws = Path("/tmp/study-cli-test-draft-missing")
        if ws.exists():
            shutil.rmtree(ws)
        (ws / "subjects").mkdir(parents=True, exist_ok=True)

        result = result = invoke_study(["draft", "--skip-validation", "-C", str(ws), "nonexistent"])
        assert result.exit_code == 1
        assert result.exit_code != 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
