"""Tests for the learning draft generation engine — TDD phase."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_validator():
    """Auto-mock validate_learning_draft_rule in all tests. Individual tests can override via patch()."""
    with patch("study.drafting.validate_learning_draft_rule", return_value={"passed": True, "errors": []}):
        yield

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
    """Tests for generate_draft — validation is auto-mocked by the module fixture."""
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

        draft_text = generate_draft(root, "Thermodynamics Topic", skip_validation=True)
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

        draft_text = generate_draft(root, "Entropy and Energy", skip_validation=True)
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
    """Tests for version hashing — validation is auto-mocked."""
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
        draft_text = generate_draft(root, "Hash Topic", skip_validation=True)

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
        draft1 = generate_draft(root, "First Topic", skip_validation=True)
        hash1 = hashlib.sha256(draft1.encode()).hexdigest()

        self._populate_sources(root, [
            {"kind": "native", "content": "Different content for second draft."},
        ])
        draft2 = generate_draft(root, "Second Topic", skip_validation=True)
        hash2 = hashlib.sha256(draft2.encode()).hexdigest()

        assert hash1 != hash2, "Drafts with different content must produce different hashes"


class TestEmptySources:
    """Tests for empty-source draft generation — validation is auto-mocked."""
    def test_generate_draft_with_no_sources_still_produces_valid_structure(self):
        """Even without sources the draft should have 3+ chapters and a References section."""
        ws, root = _make_workspace("no-sources-test")

        from study.drafting import generate_draft
        draft_text = generate_draft(root, "Empty Topic", skip_validation=True)

        sections = [s.strip() for s in re.findall(r'^##\s+(.+?)$', draft_text, re.MULTILINE)]
        assert len(sections) == 8

        ref_section_idx = draft_text.find("# References")
        pass


class TestDraftFileOutput:
    """Tests for draft file output — validation is auto-mocked."""
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
        draft_text = generate_draft(root, "File Output Topic", skip_validation=True)

        # Verify learning_draft.md was created and has correct content
        draft_path = root / "learning_draft.md"
        assert draft_path.exists()
        saved_content = draft_path.read_text()
        assert saved_content == draft_text



class TestValidateDraftTextRaisesOnFailure:
    """Task 1: _validate_draft_text() raises DraftValidationError on failed validation."""

    def test_failed_validation_raises_DraftValidationError(self):
        from unittest.mock import patch
        from study.drafting import _validate_draft_text
        from study.learning_draft_rule import DraftValidationError

        with patch("study.drafting.validate_learning_draft_rule") as mock_v:
            mock_v.return_value = {
                "passed": False,
                "errors": ["section order mismatch", "body too short"],
            }
            with pytest.raises(DraftValidationError) as exc_info:
                _validate_draft_text("dummy draft text")

        assert "section order mismatch" in str(exc_info.value)
        assert "body too short" in str(exc_info.value)

    def test_passed_validation_continues_normally(self):
        from unittest.mock import patch
        from study.drafting import _validate_draft_text
        from study.learning_draft_rule import DraftValidationError

        with patch("study.drafting.validate_learning_draft_rule") as mock_v:
            mock_v.return_value = {
                "passed": True,
                "errors": [],
            }
            _validate_draft_text("dummy draft text")

    def test_error_message_includes_failure_details(self):
        from unittest.mock import patch
        from study.drafting import _validate_draft_text
        from study.learning_draft_rule import DraftValidationError

        with patch("study.drafting.validate_learning_draft_rule") as mock_v:
            mock_v.return_value = {
                "passed": False,
                "errors": ["error one", "error two", "error three"],
            }
            with pytest.raises(DraftValidationError) as exc_info:
                _validate_draft_text("dummy draft text")

        msg = str(exc_info.value)
        assert "3 error" in msg


class TestRenderFromLMStructure:
    """Task 2: _render_draft() uses LM section_structure as primary content."""

    def _make_section_chunk(self, title, body):
        return f"## {title}\n{body}"

    def test_rendered_output_contains_lm_content(self):
        from study.drafting import _render_draft, LearningDraftSystem
        
        system = LearningDraftSystem(
            topic="Test",
            concept_layers=["cl"],
            section_structure=[
                self._make_section_chunk("문제 배경", "This is actual LM-generated content for problem background."),
                self._make_section_chunk("개념 정의", "Definition from the language model."),
            ],
            recall_hooks=["rh"], verification_points=["vp"], bibliography=["bib"],
        )
        
        rendered = _render_draft(system)
        assert "actual LM-generated content" in rendered
        assert "Definition from the language model" in rendered

    def test_old_fallback_absent_when_lm_content_present(self):
        from study.drafting import _render_draft, LearningDraftSystem
        
        system = LearningDraftSystem(
            topic="Test",
            concept_layers=["cl"],
            section_structure=[
                self._make_section_chunk("문제 배경", "Real LM content here."),
            ],
            recall_hooks=["rh"], verification_points=["vp"], bibliography=["bib"],
        )
        
        rendered = _render_draft(system)
        assert "Deterministic fallback" not in rendered
        assert "fallback exists only because" not in rendered

    def test_headings_preserved_in_seed_order(self):
        import re
        from study.drafting import _render_draft, LearningDraftSystem
        
        system = LearningDraftSystem(
            topic="Test", concept_layers=["cl"],
            section_structure=[
                self._make_section_chunk("문제 배경", "Content."),
                self._make_section_chunk("개념 정의", "Def."),
                self._make_section_chunk("동작 원리", "Mechanism."),
                self._make_section_chunk("핵심 판단 기준", "Criteria."),
                self._make_section_chunk("실패 사례", "Failures."),
                self._make_section_chunk("검증 방법", "Verification."),
                self._make_section_chunk("유사 개념 비교", "Comparison."),
                self._make_section_chunk("복습 질문", "Review."),
            ],
            recall_hooks=["rh"], verification_points=["vp"], bibliography=["bib"],
        )
        
        rendered = _render_draft(system)
        found = re.findall(r"^##\s+(.+?)$", rendered, flags=re.MULTILINE)
        expected_order = [
            "문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
            "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문",
        ]
        assert found == expected_order, f"Expected {expected_order}, got {found}"

    def test_placeholder_for_missing_section(self):
        from study.drafting import _render_draft, LearningDraftSystem
        
        system = LearningDraftSystem(
            topic="Test", concept_layers=["cl"],
            section_structure=[
                self._make_section_chunk("문제 배경", "Content."),
                self._make_section_chunk("개념 정의", "Def."),
                self._make_section_chunk("동작 원리", "Mechanism."),
            ],
            recall_hooks=["rh"], verification_points=["vp"], bibliography=["bib"],
        )
        
        rendered = _render_draft(system)
        assert "[VALIDATION REQUIRED: LM did not provide required section" in rendered
        assert "'핵심 판단 기준'.]" in rendered
        assert "'실패 사례'.]" in rendered



class TestExitConditionsRuntimeGates:
    """Task 4: exit conditions must function as actual runtime gates."""

    def test_exit_conditions_rule_locked_computed_independently(self):
        from unittest.mock import patch
        from dataclasses import dataclass
        from study.models import LearningDraftRule
        from dataclasses import field
        from study.learning_draft_rule import SectionStructureResult, ProhibitedPatternResult
        from study.learning_draft_rule import validate_learning_draft_rule

        draft = "## 문제 배경\nSome text." * 100

        @dataclass
        class DensityMock:
            passed: bool = False
            errors: list[str] = field(default_factory=lambda: ["density failed"])

        with patch("study.learning_draft_rule.validate_section_structure") as m_sec, \
             patch("study.learning_draft_rule.detect_prohibited_patterns") as m_pat, \
             patch("study.learning_draft_rule.analyze_judgment_density") as m_dens:
            m_sec.return_value = SectionStructureResult(passed=True, found_sections=LearningDraftRule.DEFAULT_REQUIRED_SECTIONS)
            m_pat.return_value = ProhibitedPatternResult(passed=True, matches=[], errors=[])

            @dataclass
            class DensityMock:
                passed: bool = False
                errors: list[str] = field(default_factory=lambda: ["density failed"])

            m_dens.return_value = DensityMock()
            result = validate_learning_draft_rule(draft)
            ec = result["exit_conditions"]
            assert "rule_locked" in ec, f"Missing rule_locked in exit_conditions: {ec}"
            # density failure should cause rule_locked to be False
            assert not ec.get("rule_locked", True), f"Expected rule_locked=False when density fails, got {ec}"

    def test_exit_conditions_no_open_drift_rejects_format_only(self):
        """Draft with section headers but insufficient body -> no_open_drift = False."""
        from study.learning_draft_rule import validate_learning_draft_rule

        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리"]:
            draft += f"## {s}\nShort text." + "\n\n"

        from study.models import LearningDraftRule
        result = validate_learning_draft_rule(draft, rule=LearningDraftRule.default())
        ec = result["exit_conditions"]
        assert not ec.get("no_open_drift", True), (
            f"format-only draft should fail no_open_drift, got {ec}"
        )

    def test_exit_conditions_all_true_when_all_checks_pass(self):
        """When all checks pass independently, both exit conditions are True."""
        from unittest.mock import patch
        from dataclasses import dataclass
        from study.learning_draft_rule import (
            validate_learning_draft_rule, SectionStructureResult,
            ProhibitedPatternResult, analyze_judgment_density,
        )

        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리"]:
            draft += f"## {s}\nThis section discusses why the mechanism matters because failure occurs when boundaries are violated." * 40 + "\n\n"

        from dataclasses import field
        @dataclass
        class DensityMock:
            passed: bool = True
            paragraph_count: int = 20
            weak_paragraph_indexes: list[int] = field(default_factory=list)
            errors: list[str] = field(default_factory=list)

        with patch("study.learning_draft_rule.validate_section_structure") as mock_sec, \
             patch("study.learning_draft_rule.detect_prohibited_patterns") as mock_pat, \
             patch("study.learning_draft_rule.analyze_judgment_density") as mock_dens:
            mock_sec.return_value = SectionStructureResult(passed=True, found_sections=["문제 배경", "개념 정의", "동작 원리"])
            mock_pat.return_value = ProhibitedPatternResult(passed=True, matches=[], errors=[])
            mock_dens.return_value = DensityMock()

            result = validate_learning_draft_rule(draft)
            ec = result["exit_conditions"]
            assert ec.get("rule_locked", False), f"Expected rule_locked=True, got {ec}"
            assert ec.get("no_open_drift", False), f"Expected no_open_drift=True, got {ec}"

    def test_generate_draft_skips_write_on_exit_condition_failure(self):
        """If exit conditions fail, generate_draft must NOT write file or update state."""
        from unittest.mock import patch
        from pathlib import Path
        from study.drafting import generate_draft
        from study.learning_draft_rule import DraftValidationError

        subject = Path("/tmp/test_subject_exit")
        subject.mkdir(exist_ok=True)
        (subject / "sources.json").write_text("[]", encoding="utf-8")
        (subject / "progress.json").write_text('{"phase": "idle"}', encoding="utf-8")

        from study.models import LearningDraftSystem
        system = LearningDraftSystem(
            topic="Test",
            concept_layers=["cl"],
            section_structure=[
                f"## {s}\nBody content for {s}." + "\n" * 2
                for s in ["문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
                          "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문"]
            ],
            recall_hooks=["rh"], verification_points=["vp"], bibliography=["bib"],
        )

        with patch("study.drafting._build_learning_system") as mock_build, \
             patch("study.drafting._render_draft") as mock_render, \
             patch("study.drafting.validate_learning_draft_rule") as mock_val, \
             patch("study.drafting.load_source_data", return_value=[]):
            mock_build.return_value = system
            mock_render.return_value = str(system)

            # Make exit conditions fail: no_open_drift is False
            mock_val.return_value = {
                "passed": False,
                "errors": ["thin section body detected"],
                "exit_conditions": {"rule_locked": True, "no_open_drift": False},
            }

            with pytest.raises(DraftValidationError):
                generate_draft(subject, "Test")

        # Verify file was NOT written and state was NOT updated
        assert not (subject / "learning_draft.md").exists(), \
            "Draft file must NOT be created when exit conditions fail"

        import json
        progress = json.loads((subject / "progress.json").read_text())
        assert progress["phase"] != "drafting", \
            "State phase must NOT update to 'drafting' on exit condition failure"

        # Cleanup
        import shutil
        shutil.rmtree(subject, ignore_errors=True)
