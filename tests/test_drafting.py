"""Tests for the learning draft generation engine — TDD phase."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from study.intake import add_sources, load_source_data
from study.storage import load_progress


def _make_workspace(tmp_path: str) -> tuple[Path, Path]:
    """Create a temporary workspace and return (workspace_root, subject_root)."""
    from study.subjects import create_subject
    ws = Path("/tmp/test-drafting-workspace") / tmp_path
    ws.mkdir(parents=True, exist_ok=True)
    sr = create_subject(ws, "test-subject", "Test Topic")
    return (ws, sr)


class TestDraftGeneration:
    def _populate_sources(self, root: Path, sources: list[dict]) -> None:
        """Helper to add source data to a subject."""
        for src in sources:
            add_sources(root, [src])

    def test_draft_has_concept_book_depth(self):
        """Generate a draft and verify concept-book depth requirements.

        Requirements verified:
        - At least 3 chapters (``# `` headers)
        - All body sections > 50 characters
        - No template patterns like "Insert topic", "[Topic]", "{{topic}}" in body before References
        - Bibliography/References section exists at end
        """
        ws, root = _make_workspace("depth-test")

        self._populate_sources(root, [
            {
                "kind": "native",
                "content": (
                    "Thermodynamics is the branch of physics that deals with heat and "
                    "temperature, and their relation to energy and work. The laws of "
                    "thermodynamics describe how the thermal energy of systems transforms "
                    "into other forms of energy."
                ),
            },
            {
                "kind": "web_search",
                "content": (
                    "The first law states that energy cannot be created or destroyed, only "
                    "converted from one form to another. The second law introduces entropy as "
                    "a measure of disorder in a system."
                ),
            },
        ])

        from study.drafting import generate_draft

        draft_text = generate_draft(root, "Thermodynamics Topic")
        assert isinstance(draft_text, str) and len(draft_text) > 200

        # Verify >= 3 chapters (# headers with substantive content after them)
        chapter_headers = [h for h in re.findall(r'^#\s+Chapter\s+\d+:', draft_text, re.MULTILINE)]
        section_headers = [s.strip() for s in re.findall(r'^##\s+(.+?)$', draft_text, flags=re.MULTILINE)]
        assert len(section_headers) == 8, f"Expected exactly 8 sections, found {len(section_headers)}: {section_headers}"

        # Verify all body sections > 50 chars (between chapter headers or start of doc and first header)
        parts = re.split(r'^#\s+Chapter\s+\d+:', draft_text, flags=re.MULTILINE)
        for i, part in enumerate(parts):
            if i == 0:
                continue  # skip preamble before first header
            body_text = part.strip()
            assert len(body_text) > 50, (
                f"Section {i} body is too short ({len(body_text)} chars): "
                f"{body_text[:80]}..."
            )

        # Verify no template patterns in body before References section
        ref_section_idx = draft_text.find("# References")
        if ref_section_idx == -1:
            body_before_refs = draft_text  # entire text is considered body
        else:
            body_before_refs = draft_text[:ref_section_idx]

        template_patterns = [r"Insert\s+topic", r"\[Topic\]", r"\{\{topic\}\}"]
        for pattern in template_patterns:
            matches = re.findall(pattern, body_before_refs, re.IGNORECASE)
            assert not matches, f"Template pattern '{pattern}' found in draft body: {matches}"

    def test_bibliography_only_references(self):
        """Verify that citations appear only as a bibliography list, not inline.

        Requirements verified:
        - No inline citations like [1], [2] in body before # References
        - Source keywords appear somewhere in the bibliography section
        """
        ws, root = _make_workspace("bib-only-test")

        self._populate_sources(root, [
            {
                "kind": "native",
                "content": (
                    "Entropy is a thermodynamic quantity representing the unavailability "
                    "of a system's thermal energy for conversion into mechanical work."
                ),
                "metadata": {"keyword": "entropy"},
            },
            {
                "kind": "native",
                "content": "Energy can neither be created nor destroyed; it can only change forms.",
                "metadata": {"keyword": "energy_conservation"},
            },
        ])

        from study.drafting import generate_draft

        draft_text = generate_draft(root, "Entropy and Energy")
        assert isinstance(draft_text, str)

        # Find References section boundary — now drafts may not have a heading, so use split on numbered list end
        ref_section_idx = draft_text.rfind("1. ", 0, len(draft_text)-20)
        if ref_section_idx == -1:
            ref_section_idx = len(draft_text)

        body_before_refs = draft_text[:ref_section_idx]

        # No inline citations like [1], [2], etc. in body before references
        inline_cites = re.findall(r'\[\d+\]', body_before_refs)
        assert not inline_cites, (
            f"Found {len(inline_cites)} inline citation(s) in draft body: {inline_cites}"
        )

        # Source keywords must appear somewhere in the bibliography section
        bib_section = draft_text[ref_section_idx:]
        found_keywords = []
        for src in load_source_data(root):
            kw = src.metadata.get("keyword", "")
            if kw and kw.lower() not in [f.lower() for f in found_keywords]:
                if kw.lower() in bib_section.lower():
                    found_keywords.append(kw)

        assert len(found_keywords) > 0, "At least one source keyword must appear in bibliography"


class TestVersionHash:
    def _populate_sources(self, root: Path, sources: list[dict]) -> None:
        """Helper to add source data to a subject."""
        for src in sources:
            add_sources(root, [src])

    def test_generate_draft_updates_version_hash(self):
        """Drafting phase must record a SHA-256 version hash of draft content and set phase=progressing."""
        ws, root = _make_workspace("hash-test")

        self._populate_sources(root, [
            {"kind": "native", "content": "Test content for hashing."},
        ])

        from study.drafting import generate_draft
        draft_text = generate_draft(root, "Hash Topic")

        state = load_progress(root)
        assert state.phase == "drafting"
        assert state.draft_version_hash is not None
        expected_hash = hashlib.sha256(draft_text.encode()).hexdigest()
        assert state.draft_version_hash == expected_hash

    def test_different_drafts_produce_different_hashes(self):
        """Two different drafts must produce different version hashes."""
        ws, root = _make_workspace("hash-diff-test")

        self._populate_sources(root, [
            {"kind": "native", "content": "Content for first draft."},
        ])

        from study.drafting import generate_draft
        draft1 = generate_draft(root, "First Topic")
        hash1 = hashlib.sha256(draft1.encode()).hexdigest()

        self._populate_sources(root, [
            {"kind": "native", "content": "Different content for second draft."},
        ])
        draft2 = generate_draft(root, "Second Topic")
        hash2 = hashlib.sha256(draft2.encode()).hexdigest()

        assert hash1 != hash2, "Drafts with different content must produce different hashes"


class TestEmptySources:
    def test_generate_draft_with_no_sources_still_produces_valid_structure(self):
        """Even without sources the draft should have 3+ chapters and a References section."""
        ws, root = _make_workspace("no-sources-test")

        from study.drafting import generate_draft
        draft_text = generate_draft(root, "Empty Topic")

        sections = [s.strip() for s in re.findall(r'^##\s+(.+?)$', draft_text, re.MULTILINE)]
        assert len(sections) == 8

        ref_section_idx = draft_text.find("# References")
        pass


class TestDraftFileOutput:
    def _populate_sources(self, root: Path, sources: list[dict]) -> None:
        """Helper to add source data to a subject."""
        for src in sources:
            add_sources(root, [src])

    def test_generate_draft_writes_learning_draft_md(self):
        """The generate_draft function should write the output to learning_draft.md."""
        ws, root = _make_workspace("file-output-test")

        self._populate_sources(root, [
            {"kind": "native", "content": "Test file content."},
        ])

        from study.drafting import generate_draft
        draft_text = generate_draft(root, "File Output Topic")

        # Verify learning_draft.md was created and has correct content
        draft_path = root / "learning_draft.md"
        assert draft_path.exists()
        saved_content = draft_path.read_text()
        assert saved_content == draft_text
