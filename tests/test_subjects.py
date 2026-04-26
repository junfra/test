"""Tests for study.subjects — written BEFORE implementation (TDD fail-first)."""
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


# --------------------------------------------------------------------------- #
# 1. test_create_subject_creates_directory
# --------------------------------------------------------------------------- #

class TestCreateSubject:
    def create_subject(self, workspace_root: Path, subject_id: str, topic: str) -> Path:
        from study.subjects import create_subject as _cs
        return _cs(workspace_root, subject_id, topic)

    def test_creates_subject_directory(self, tmp_workspace: Path) -> None:
        """subject/{id}/ directory is created under workspace."""
        root = self.create_subject(tmp_workspace, "math-101", "algebra")
        assert root.is_dir()
        assert (tmp_workspace / "subjects" / "math-101").exists()

    def test_creates_source_reference_data_subdir(self, tmp_workspace: Path) -> None:
        """subject/{id}/source_reference_data/ is created."""
        root = self.create_subject(tmp_workspace, "cs2", "algorithms")
        assert (root / "source_reference_data").is_dir()

    def test_creates_session_logs_subdir(self, tmp_workspace: Path) -> None:
        """subject/{id}/session_logs/ is created."""
        root = self.create_subject(tmp_workspace, "cs2", "algorithms")
        assert (root / "session_logs").is_dir()

    def test_progress_state_json_exists(self, tmp_workspace: Path) -> None:
        """progress_state.json is written with initial state."""
        root = self.create_subject(tmp_workspace, "math-101", "calculus")
        ps_file = root / "progress_state.json"
        assert ps_file.exists()

        data = json.loads(ps_file.read_text())
        assert data["subject_id"] == "math-101"
        assert data["topic"] == "calculus"
        assert data["phase"] == "intake"
        assert data["approval_status"] is False

    def test_returns_path_to_subject_root(self, tmp_workspace: Path) -> None:
        """create_subject returns the subject root path."""
        from study.subjects import create_subject as _cs
        result = _cs(tmp_workspace, "bio-101", "genetics")
        assert isinstance(result, Path)
        assert result == tmp_workspace / "subjects" / "bio-101"


# --------------------------------------------------------------------------- #
# 2. test_list_subjects
# --------------------------------------------------------------------------- #

class TestListSubjects:
    def list_subjects(self, workspace_root: Path) -> list[tuple[str, str]]:
        from study.subjects import list_subjects as _ls
        return _ls(workspace_root)

    def test_empty_workspace_returns_empty_list(self, tmp_workspace: Path) -> None:
        assert self.list_subjects(tmp_workspace) == []

    def test_two_subjects_returned_with_topics(self, tmp_workspace: Path) -> None:
        from study.subjects import create_subject as _cs
        _cs(tmp_workspace, "math-101", "algebra")
        _cs(tmp_workspace, "physics-202", "thermo")

        result = self.list_subjects(tmp_workspace)
        assert len(result) == 2
        assert ("math-101", "algebra") in result
        assert ("physics-202", "thermo") in result

    def test_list_sorted_by_subject_id(self, tmp_workspace: Path) -> None:
        from study.subjects import create_subject as _cs
        _cs(tmp_workspace, "z-subject", "zzz-topic")
        _cs(tmp_workspace, "a-subject", "aaa-topic")

        result = self.list_subjects(tmp_workspace)
        ids = [sid for sid, _ in result]
        assert ids == sorted(ids), "subjects should be returned in sorted order"


# --------------------------------------------------------------------------- #
# 3. test_delete_subject_removes_all_files
# --------------------------------------------------------------------------- #

class TestDeleteSubject:
    def delete_subject(self, subject_root: Path) -> None:
        from study.subjects import delete_subject as _ds
        return _ds(subject_root)

    def test_directory_removed(self, tmp_workspace: Path) -> None:
        """delete_subject removes the entire directory tree."""
        from study.subjects import create_subject as _cs
        root = _cs(tmp_workspace, "math-101", "algebra")
        assert root.exists()

        self.delete_subject(root)
        assert not root.exists()

    def test_parent_untouched(self, tmp_workspace: Path) -> None:
        """Other subjects under the same parent are preserved."""
        from study.subjects import create_subject as _cs

        _cs(tmp_workspace, "math-101", "algebra")
        math_root = tmp_workspace / "subjects" / "math-101"

        _cs(tmp_workspace, "physics-202", "thermo")
        physics_root = tmp_workspace / "subjects" / "physics-202"

        self.delete_subject(math_root)
        assert not math_root.exists()
        assert physics_root.is_dir(), "physics subject should still exist"

    def test_session_logs_removed(self, tmp_workspace: Path) -> None:
        """session_logs directory is also removed on delete."""
        from study.subjects import create_subject as _cs
        root = _cs(tmp_workspace, "math-101", "algebra")
        (root / "session_logs" / "log.txt").write_text("hello")

        self.delete_subject(root)
        assert not root.exists()


# --------------------------------------------------------------------------- #
# CLI smoke test (import check — actual command testing is optional for TDD)
# --------------------------------------------------------------------------- #

class TestCLIImport:
    def test_cli_module_exists(self, tmp_workspace: Path) -> None:
        """The cli module can be imported."""
        import study.cli  # noqa: F401


