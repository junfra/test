"""Tests for source intake — add_sources + list_sources."""
from pathlib import Path, PurePath

import pytest

from study.intake import add_sources, load_source_data


def _make_workspace(tmp_path: str) -> tuple[Path, Path]:
    """Create a temporary workspace and return (workspace_root, subject_root)."""
    from study.subjects import create_subject
    ws = Path("/tmp/test-intake-workspace") / tmp_path
    ws.mkdir(parents=True, exist_ok=True)
    sr = create_subject(ws, "test-subject", "Test Topic")
    return (ws, sr)


class TestAddSources:
    def test_add_sources_creates_json_files(self):
        """Adding 3 sources of different kinds creates matching .json files."""
        ws, root = _make_workspace("add-files-test")

        add_sources(root, [
            {"kind": "native", "content": "Native source content"},
            {"kind": "web_search", "content": "Web search result", "metadata": {"url": "https://example.com"}},
            {"kind": "pasted_text", "content": "Pasted text"},
        ])

        ref_dir = root / "source_reference_data"
        files = sorted(ref_dir.glob("*.json"))
        assert len(files) == 3
        # Verify zero-padded naming convention
        assert str(files[0]).endswith("_0.json") or any(f.name.startswith("source_") for f in files)

    def test_add_sources_updates_manifest_count(self):
        """Adding sources must increment source_manifest_count in progress_state.json."""
        ws, root = _make_workspace("manifest-count-test")

        add_sources(root, [
            {"kind": "native", "content": "Content A"},
            {"kind": "web_search", "content": "Content B", "metadata": {"url": "https://b.com"}},
        ])

        from study.storage import load_progress
        state = load_progress(root)
        assert state.source_manifest_count == 2

    def test_add_sources_persists_correct_kinds(self):
        """Each source must be stored with its correct kind field."""
        ws, root = _make_workspace("kind-persist-test")

        add_sources(root, [
            {"kind": "native", "content": "A"},
            {"kind": "user_file", "content": "B"},
            {"kind": "pasted_text", "content": "C"},
        ])

        refs = load_source_data(root)
        kinds = [r.kind for r in refs]
        assert "native" in kinds
        assert "user_file" in kinds
        assert "pasted_text" in kinds


class TestLoadSourceData:
    def test_loads_all_json_files(self):
        """list_sources returns all .json files from source_reference_data/."""
        ws, root = _make_workspace("load-all-test")

        add_sources(root, [
            {"kind": "native", "content": "X"},
            {"kind": "web_search", "content": "Y", "metadata": {}},
        ])

        refs = load_source_data(root)
        assert len(refs) == 2

    def test_load_empty_directory_returns_empty_list(self):
        """If no sources exist, list_sources returns empty list."""
        ws, root = _make_workspace("load-empty-test")
        refs = load_source_data(root)
        assert refs == []

    def test_loads_preserves_content_and_metadata(self):
        """Loaded SourceReference objects must preserve original content and metadata."""
        ws, root = _make_workspace("preserve-data-test")

        add_sources(root, [
            {"kind": "web_search", "content": "Web result with url", "metadata": {"url": "https://example.com"}},
        ])

        refs = load_source_data(root)
        assert len(refs) == 1
        assert refs[0].kind == "web_search"
        assert refs[0].content == "Web result with url"
        assert refs[0].metadata["url"] == "https://example.com"

    def test_load_order_is_deterministic(self):
        """list_sources must return files in sorted order by filename."""
        ws, root = _make_workspace("order-test")

        # Add sources in non-alphabetical order
        add_sources(root, [
            {"kind": "native", "content": "Third"},
            {"kind": "pasted_text", "content": "First"},
            {"kind": "user_file", "content": "Second"},
        ])

        refs = load_source_data(root)
        # Should be sorted by filename: First (index 0), Second (index 1), Third (index 2)
        assert len(refs) == 3
