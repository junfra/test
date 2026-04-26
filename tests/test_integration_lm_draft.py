import re
"""Integration test for end-to-end mock LM draft generation."""
from pathlib import Path

from study.drafting import generate_draft
from study.intake import add_sources
from study.models import ProgressState, SourceReference
from study.storage import load_progress, save_progress


def _make_subject(tmp_path: Path) -> Path:
    root = tmp_path / "subjects" / "os"
    root.mkdir(parents=True)
    (root / "source_reference_data").mkdir()
    (root / "session_logs").mkdir()
    save_progress(
        root,
        ProgressState(
            subject_id="os",
            topic="Operating Systems",
            phase="intake",
            approval_status=False,
        ),
    )
    return root


def test_mock_lm_draft_is_dense_sectioned_and_non_derivative(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STUDY_LM_PROVIDER", "mock")
    monkeypatch.setenv("STUDY_LM_MODEL", "mock-dense-reconstruction")

    root = _make_subject(tmp_path)
    copied_sentence = "THIS EXACT SOURCE SENTENCE SHOULD NOT DRIVE THE BODY."
    add_sources(
        root,
        [
            SourceReference(
                kind="pasted_text",
                content=f"{copied_sentence} Processes isolate execution state and scheduling state.",
                metadata={"keyword": "process"},
            )
        ],
    )

    draft = generate_draft(root, "Operating Systems")

    assert len(draft) >= 3000
    assert len([s for s in re.findall(r'^##\s+(.+?)$', draft, flags=re.MULTILINE)]) == 8
    assert "## 문제 배경" in draft
    assert "## 복습 질문" in draft
    assert copied_sentence not in draft.split("# References", 1)[0]

    state = load_progress(root)
    assert state.phase == "drafting"
    assert state.draft_version_hash is not None
    assert len(state.draft_version_hash) == 64
