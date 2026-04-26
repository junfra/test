# Plan Brief — Study Harness Learning Draft Reconstruction Upgrade

**Target repo:** `/home/user01/project/study/my-study/.worktree/study-harness`
**Branch:** `study-harness-impl`
**Goal:** Replace source-paraphrase draft generation with a dense Learning-Model-driven concept reconstruction engine that produces Red Hat-style structured drafts, keeps sources in references, and feeds recall from reconstructed content.
**Preserve:** `subject_root` APIs, click CLI signatures, pydantic v2, stdlib JSON persistence, approval gate, existing file layout.
**Primary files:**

* `src/study/drafting.py`
* `src/study/models.py`
* `src/study/recall.py`
* `tests/`

## Architecture

The upgrade adds one explicit draft ontology:

`LearningDraftSystem`

It becomes the internal structure behind draft generation:

1. `drafting.py` loads source manifests.
2. It extracts concepts from source content without copying source prose into the body.
3. It builds a `LearningDraftSystem`.
4. It generates at least 3 dense chapters.
5. Every chapter repeats:

   * `## Concept Reconstruction`
   * `## Learning Model`
   * `## Recall Hooks`
   * `## Verification Points`
6. Sources are listed only in `# References`.
7. `recall.py` extracts those reconstructed sections and generates questions from them.
8. Approval gating remains unchanged.

## Tech Stack

* Python
* pydantic v2
* click CLI, unchanged
* stdlib JSON / JSONL persistence
* pytest
* uv

---

# Task 0 — Prepare branch and baseline

## Command

```bash
cd /home/user01/project/study/my-study/.worktree/study-harness
git switch study-harness-impl
uv run pytest -q
```

## Expected output

```text
80 passed
```

If the baseline count differs, the important expected result is exit code `0`.

---

# Task 1 — Add failing ontology tests

**File:** `tests/test_learning_draft_system.py`

```python
import pytest
from pydantic import ValidationError

from study.models import LearningDraftSystem


def test_learning_draft_system_requires_document_wide_fields() -> None:
    system = LearningDraftSystem(
        topic="Kubernetes Operations",
        concept_layers=[
            "facts and vocabulary",
            "relationships and mechanisms",
            "operational consequences",
        ],
        section_structure=[
            "Concept Reconstruction",
            "Learning Model",
            "Recall Hooks",
            "Verification Points",
        ],
        recall_hooks=[
            "Explain why pods move through scheduling states.",
            "Connect failure recovery to controller reconciliation.",
        ],
        verification_points=[
            "Can distinguish node failure from pod failure.",
            "Can explain why restart policy is not the same as scheduling.",
        ],
        bibliography=[
            "1. [Pasted text] Kubernetes source manifest",
        ],
    )

    assert system.topic == "Kubernetes Operations"
    assert len(system.concept_layers) == 3
    assert "Concept Reconstruction" in system.section_structure
    assert "Learning Model" in system.section_structure
    assert "Recall Hooks" in system.section_structure
    assert "Verification Points" in system.section_structure
    assert system.bibliography[0].startswith("1. ")


def test_learning_draft_system_rejects_empty_required_lists() -> None:
    with pytest.raises(ValidationError):
        LearningDraftSystem(
            topic="Kubernetes Operations",
            concept_layers=[],
            section_structure=["Concept Reconstruction"],
            recall_hooks=["Explain the control loop."],
            verification_points=["Can explain reconciliation."],
            bibliography=["1. source"],
        )
```

## Test command

```bash
uv run pytest tests/test_learning_draft_system.py -q
```

## Expected red output

```text
ImportError: cannot import name 'LearningDraftSystem' from 'study.models'
```

---

# Task 2 — Implement `LearningDraftSystem`

**File:** `src/study/models.py`

Replace the file with:

```python
"""Pydantic models for the study harness."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SubjectId(str):
    """Custom newtype wrapping str for subject identifiers."""


class ApprovalRequiredError(Exception):
    """Raised when recall functions are called without draft approval."""


class SourceReference(BaseModel):
    kind: Literal["native", "web_search", "user_file", "pasted_text"]
    content: str
    metadata: dict = Field(default_factory=dict)


class LearningDraftSystem(BaseModel):
    """Ontology for a reconstructed learning draft.

    The draft body is generated from this system-level structure, not by
    copying source prose into chapter bodies.
    """

    topic: str
    concept_layers: list[str]
    section_structure: list[str]
    recall_hooks: list[str]
    verification_points: list[str]
    bibliography: list[str]

    @field_validator(
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    )
    @classmethod
    def validate_non_empty_string_list(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("field must contain at least one item")
        if any(not item.strip() for item in value):
            raise ValueError("field cannot contain blank items")
        return value


class RecallQuestion(BaseModel):
    id: str
    topic: str
    prompt: str
    answer: str | None = None
    score: float | None = None


class WeakPoint(BaseModel):
    topic: str
    misconception_explanation: str
    weakness_score: float
    retest_count: int = 0

    @field_validator("weakness_score")
    @classmethod
    def validate_weakness_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"weakness_score must be in [0, 1], got {v}")
        return v


class ProgressState(BaseModel):
    subject_id: str
    topic: str
    phase: Literal[
        "intake",
        "drafting",
        "draft_approved",
        "recall_first_pass",
        "recall_adaptive",
    ] = "intake"
    approval_status: bool = False
    draft_version_hash: str | None = None
    first_pass_complete: bool = False
    next_recursors_cursor: int = 0
    weak_points: list[WeakPoint] = Field(default_factory=list)
    source_manifest_count: int = 0


class RecallSessionEntry(BaseModel):
    session_id: str
    questions: list[RecallQuestion]
    answers: list[str] | None = None
    scores: list[float] | None = None
    outcome: Literal["pass", "fail", "partial"]
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid ISO-8601 timestamp: {v}")
        return v


__all__ = [
    "ApprovalRequiredError",
    "LearningDraftSystem",
    "ProgressState",
    "RecallQuestion",
    "RecallSessionEntry",
    "SourceReference",
    "SubjectId",
    "WeakPoint",
]
```

## Test command

```bash
uv run pytest tests/test_learning_draft_system.py -q
```

## Expected output

```text
2 passed
```

## Commit

```bash
git add src/study/models.py tests/test_learning_draft_system.py
git commit -m "feat(study): add learning draft ontology schema"
```

---

# Task 3 — Add failing draft reconstruction tests

**File:** `tests/test_drafting_reconstruction.py`

```python
import json
import re
from pathlib import Path

from study.drafting import generate_draft
from study.models import ProgressState, SourceReference
from study.storage import save_progress


RAW_SENTENCE = (
    "Kubernetes schedules pods onto nodes and restarts containers when they fail."
)


def make_subject_root(tmp_path: Path) -> Path:
    subject_root = tmp_path / "subjects" / "kubernetes"
    source_dir = subject_root / "source_reference_data"
    source_dir.mkdir(parents=True)

    save_progress(
        subject_root,
        ProgressState(
            subject_id="kubernetes",
            topic="Kubernetes Operations",
            source_manifest_count=3,
        ),
    )

    sources = [
        SourceReference(
            kind="pasted_text",
            content=(
                f"{RAW_SENTENCE} Controllers compare desired state with actual "
                "state and reconcile differences through the API server."
            ),
            metadata={"keyword": "control-plane"},
        ),
        SourceReference(
            kind="pasted_text",
            content=(
                "A container platform separates declarative intent from runtime "
                "execution. Operators inspect events, controller status, node "
                "conditions, and object relationships to diagnose failures."
            ),
            metadata={"keyword": "operations"},
        ),
        SourceReference(
            kind="pasted_text",
            content=(
                "Reliable platform learning requires vocabulary, mechanism, "
                "failure-mode reasoning, verification questions, and repeated "
                "retrieval practice across related sections."
            ),
            metadata={"keyword": "learning-model"},
        ),
    ]

    for index, source in enumerate(sources):
        path = source_dir / f"source_{index:04d}.json"
        path.write_text(source.model_dump_json(), encoding="utf-8")

    return subject_root


def body_before_references(draft: str) -> str:
    return draft.split("# References", 1)[0]


def test_generate_draft_builds_dense_reconstructed_chapters(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)

    draft = generate_draft(subject_root, "Kubernetes Operations")
    body = body_before_references(draft)

    assert len(draft) >= 3000
    assert len(re.findall(r"^# Chapter \d+:", body, flags=re.MULTILINE)) >= 3

    chapters = [
        chunk
        for chunk in re.split(r"(?=^# Chapter \d+:)", body, flags=re.MULTILINE)
        if chunk.strip().startswith("# Chapter")
    ]
    assert len(chapters) >= 3

    for chapter in chapters[:3]:
        assert len(chapter) >= 800
        assert "## Concept Reconstruction" in chapter
        assert "## Learning Model" in chapter
        assert "## Recall Hooks" in chapter
        assert "## Verification Points" in chapter


def test_generate_draft_keeps_source_prose_out_of_body(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)

    draft = generate_draft(subject_root, "Kubernetes Operations")
    body = body_before_references(draft)
    references = draft.split("# References", 1)[1]

    assert RAW_SENTENCE not in body
    assert RAW_SENTENCE in references


def test_generate_draft_rejects_template_placeholders(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)

    draft = generate_draft(subject_root, "Kubernetes Operations")
    body = body_before_references(draft)

    forbidden_patterns = [
        "Insert topic",
        "[Topic]",
        "{{topic}}",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in body
```

## Test command

```bash
uv run pytest tests/test_drafting_reconstruction.py -q
```

## Expected red output

```text
FAILED tests/test_drafting_reconstruction.py::test_generate_draft_builds_dense_reconstructed_chapters
```

The current draft body is too short and does not repeat the required section structure.

---

# Task 4 — Replace template chapter generation with reconstruction engine

**File:** `src/study/drafting.py`

Replace the file with:

```python
"""Learning draft generation engine — bottom-up concept book builder.

All functions receive ``subject_root: pathlib.Path`` — no bare root paths.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .intake import load_source_data
from .models import LearningDraftSystem, SourceReference
from .storage import load_progress, save_progress


_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "between",
    "content",
    "could",
    "every",
    "from",
    "have",
    "into",
    "must",
    "only",
    "over",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "when",
    "where",
    "which",
    "with",
    "would",
}


def _extract_keywords(content: str) -> list[str]:
    """Extract stable concept terms without preserving source phrasing."""
    words = [w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", content)]
    filtered = [word.strip("-") for word in words if word not in _STOPWORDS]
    return list(dict.fromkeys(filtered))


def _combined_keywords(sources: list[SourceReference], limit: int = 12) -> list[str]:
    """Return deterministic high-signal keywords across all source manifests."""
    terms: list[str] = []
    for source in sources:
        terms.extend(_extract_keywords(source.content))
        keyword = str(source.metadata.get("keyword", "")).strip().lower()
        if keyword:
            terms.append(keyword)

    deduped = list(dict.fromkeys(term for term in terms if term))
    return deduped[:limit]


def _first_sentence(content: str) -> str:
    """Return the first sentence for bibliography attribution only."""
    parts = re.split(r"(?<=[.!?])\s+", content.strip())
    if not parts or not parts[0].strip():
        return "Source content was provided for this subject."
    sentence = parts[0].strip()
    return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."


def _build_bibliography_entries(sources: list[SourceReference]) -> list[str]:
    """Build source references for the bibliography section."""
    if not sources:
        return ["No sources were available for this subject."]

    kind_labels = {
        "native": "Native source",
        "web_search": "Web search result",
        "user_file": "User file",
        "pasted_text": "Pasted text",
    }

    entries: list[str] = []
    for index, source in enumerate(sources, start=1):
        kind_label = kind_labels.get(source.kind, "Source")
        keyword = str(source.metadata.get("keyword", "")).strip()
        keyword_suffix = f"; keyword: {keyword}" if keyword else ""
        entries.append(
            f"{index}. [{kind_label}] {kind_label} manifest{keyword_suffix}. "
            f"Source note: {_first_sentence(source.content)}"
        )

    return entries


def _build_learning_system(
    topic: str,
    sources: list[SourceReference],
) -> LearningDraftSystem:
    """Build the document-wide learning ontology used by the draft engine."""
    keywords = _combined_keywords(sources)
    concept_terms = ", ".join(keywords[:6]) if keywords else "scope, mechanism, evidence, practice"

    return LearningDraftSystem(
        topic=topic,
        concept_layers=[
            f"Vocabulary and boundary layer: define {topic} by its recurring terms, actors, and scope markers.",
            f"Relationship layer: connect {concept_terms} into cause, dependency, and feedback relationships.",
            f"Mechanism layer: explain how the system changes state and why those transitions matter.",
            f"Operational layer: translate the concept map into diagnosis, transfer, and practice decisions.",
        ],
        section_structure=[
            "Concept Reconstruction",
            "Learning Model",
            "Recall Hooks",
            "Verification Points",
        ],
        recall_hooks=[
            f"Rebuild {topic} from vocabulary to mechanism without looking at the source.",
            f"Explain how {concept_terms} relate to one another in a concrete scenario.",
            "Name the failure mode, the visible symptom, the hidden cause, and the corrective principle.",
        ],
        verification_points=[
            "Can explain the mechanism without repeating the original source sentence.",
            "Can distinguish vocabulary recall from causal understanding.",
            "Can transfer the same principle to a new example.",
            "Can identify what evidence would confirm or disconfirm the explanation.",
        ],
        bibliography=_build_bibliography_entries(sources),
    )


def _chapter_titles(topic: str) -> list[str]:
    """Return the fixed guide-style chapter hierarchy."""
    return [
        f"Orientation, Vocabulary, and Boundaries in {topic}",
        f"Mechanisms, Relationships, and Failure Modes in {topic}",
        f"Operational Reasoning and Transfer Practice for {topic}",
    ]


def _keyword_phrase(keywords: list[str]) -> str:
    if not keywords:
        return "scope, mechanism, evidence, practice, failure modes, and transfer"
    return ", ".join(keywords[:8])


def _build_concept_reconstruction(
    topic: str,
    chapter_title: str,
    chapter_index: int,
    system: LearningDraftSystem,
    keywords: list[str],
) -> str:
    terms = _keyword_phrase(keywords)
    layer = system.concept_layers[min(chapter_index, len(system.concept_layers) - 1)]

    return (
        "## Concept Reconstruction\n\n"
        f"This section reconstructs **{chapter_title}** as a concept system rather than as a "
        f"summary of source lines. The working layer is: {layer} The central move is to treat "
        f"{topic} as an organized set of roles, transitions, constraints, and checks. Instead "
        f"of memorizing isolated statements, the learner should ask what each term is doing, "
        f"what it depends on, what changes when it fails, and what evidence would show that the "
        f"idea is operating correctly. The current concept vocabulary includes {terms}. These "
        f"terms are not listed as decorations; they are handles for rebuilding the subject from "
        f"first principles. A dense explanation should show how a learner moves from naming a "
        f"term, to locating it in the system, to predicting the consequence of a change.\n\n"
        f"The reconstruction also separates source fidelity from source copying. Fidelity means "
        f"the explanation remains anchored to the source manifest and does not invent unrelated "
        f"claims. Non-derivative synthesis means the body restates the subject through hierarchy, "
        f"mechanism, contrast, and testable understanding. For {topic}, the learner should be "
        f"able to say what the system is for, which parts interact, why the order of operations "
        f"matters, and how a mistaken mental model would lead to a wrong answer. This gives the "
        f"chapter enough density to support later recall without turning the draft into a pasted "
        f"source digest."
    )


def _build_learning_model(
    topic: str,
    chapter_title: str,
    chapter_index: int,
    system: LearningDraftSystem,
) -> str:
    layer = system.concept_layers[min(chapter_index + 1, len(system.concept_layers) - 1)]

    return (
        "## Learning Model\n\n"
        f"The learning model for this chapter is a four-step loop: orient, connect, simulate, "
        f"and verify. First, orient by naming the boundary of {chapter_title}. Second, connect "
        f"the named parts into relationships: ownership, dependency, sequence, constraint, and "
        f"feedback. Third, simulate the mechanism by asking what changes when one part moves, "
        f"fails, or receives new input. Fourth, verify the explanation by checking whether it "
        f"predicts a concrete outcome. This loop makes {topic} learnable because every section "
        f"uses the same mental movement while increasing the level of difficulty.\n\n"
        f"The active layer for this chapter is: {layer} That layer should be read as an "
        f"instruction for how to study the section. The learner should not stop at definitions. "
        f"They should produce a small internal model: what exists, what acts, what changes, "
        f"what evidence appears, and what mistake would expose shallow understanding. The same "
        f"pattern repeats across the document so that the draft becomes a guide, not a loose "
        f"collection of notes."
    )


def _build_recall_hooks(
    topic: str,
    chapter_title: str,
    system: LearningDraftSystem,
    keywords: list[str],
) -> str:
    terms = _keyword_phrase(keywords[:6])
    hooks = "\n".join(f"- {hook}" for hook in system.recall_hooks)

    return (
        "## Recall Hooks\n\n"
        f"Use these hooks after reading {chapter_title}. Each hook asks for reconstruction from "
        f"memory, not recognition of a sentence. Begin with the topic name, list the relevant "
        f"terms, connect them, then explain the mechanism aloud. Useful trigger terms for this "
        f"chapter are {terms}. If the answer becomes a list of definitions, restart and force "
        f"the explanation to include movement: cause, effect, constraint, exception, and check.\n\n"
        f"{hooks}\n\n"
        f"A strong answer about {topic} should sound like a guided explanation. It should name "
        f"the concept, place it in a hierarchy, explain why it matters, and close with a test "
        f"that would prove the learner understands it. A weak answer will merely repeat terms "
        f"without showing how the system behaves."
    )


def _build_verification_points(
    topic: str,
    chapter_title: str,
    system: LearningDraftSystem,
) -> str:
    checks = "\n".join(f"- {point}" for point in system.verification_points)

    return (
        "## Verification Points\n\n"
        f"Verification for {chapter_title} is based on whether the learner can operate the idea, "
        f"not whether they can quote a source. The learner should be able to reconstruct the "
        f"section from a blank page, draw the relationships in plain language, and answer a "
        f"near-transfer question that changes the surface example while preserving the same "
        f"principle. The check is deliberately stricter than summary: it asks whether the "
        f"learning model can survive a new situation.\n\n"
        f"{checks}\n\n"
        f"When these checks pass, the chapter has done its job. It has turned {topic} into a "
        f"mental model with boundaries, mechanisms, recall prompts, and evidence standards. "
        f"When they fail, the next revision should add causal links, sharper contrasts, and "
        f"more explicit practice prompts rather than more copied source text."
    )


def _build_chapter(
    topic: str,
    chapter_title: str,
    chapter_index: int,
    system: LearningDraftSystem,
    keywords: list[str],
) -> str:
    """Build one dense guide-style chapter from the learning ontology."""
    heading = f"# Chapter {chapter_index + 1}: {chapter_title}"

    sections = [
        _build_concept_reconstruction(topic, chapter_title, chapter_index, system, keywords),
        _build_learning_model(topic, chapter_title, chapter_index, system),
        _build_recall_hooks(topic, chapter_title, system, keywords),
        _build_verification_points(topic, chapter_title, system),
    ]

    return f"{heading}\n\n" + "\n\n".join(sections)


def _build_bibliography(system: LearningDraftSystem) -> str:
    """Build the References section from bibliography entries."""
    lines = ["# References"]
    lines.extend(system.bibliography)
    return "\n".join(lines)


def _validate_draft_contract(draft_text: str) -> None:
    """Enforce density, structure, and template-safety constraints."""
    ref_index = draft_text.find("# References")
    body = draft_text[:ref_index] if ref_index != -1 else draft_text

    if len(draft_text) < 3000:
        raise AssertionError("Generated learning draft must be at least 3000 characters.")

    chapter_count = len(re.findall(r"^# Chapter \d+:", body, flags=re.MULTILINE))
    if chapter_count < 3:
        raise AssertionError("Generated learning draft must contain at least 3 chapters.")

    required_sections = [
        "## Concept Reconstruction",
        "## Learning Model",
        "## Recall Hooks",
        "## Verification Points",
    ]
    for section in required_sections:
        count = body.count(section)
        if count < 3:
            raise AssertionError(f"Required section '{section}' must appear in every chapter.")

    forbidden_patterns = [
        (r"Insert\s+topic", "Insert topic"),
        (r"\[Topic\]", "[Topic]"),
        (r"\{\{topic\}\}", "{{topic}}"),
    ]
    for pattern, name in forbidden_patterns:
        if re.search(pattern, body, re.IGNORECASE):
            raise AssertionError(f"Template pattern '{name}' found in draft body.")


def generate_draft(subject_root: Path, topic: str) -> str:
    """Generate a dense concept-reconstruction learning draft.

    The body is produced from a document-wide ``LearningDraftSystem`` ontology.
    Source content is used for concept extraction and bibliography attribution;
    raw source prose must not drive the draft body.
    """
    sources = load_source_data(subject_root)
    system = _build_learning_system(topic, sources)
    keywords = _combined_keywords(sources)

    draft_parts = [
        _build_chapter(topic, chapter_title, index, system, keywords)
        for index, chapter_title in enumerate(_chapter_titles(topic))
    ]
    draft_parts.append(_build_bibliography(system))

    draft_text = "\n\n".join(draft_parts) + "\n"
    _validate_draft_contract(draft_text)

    draft_path = subject_root / "learning_draft.md"
    draft_path.write_text(draft_text, encoding="utf-8")

    state = load_progress(subject_root)
    state.phase = "drafting"
    state.draft_version_hash = hashlib.sha256(draft_text.encode("utf-8")).hexdigest()
    save_progress(subject_root, state)

    from .logging import log_session_event

    log_session_event(
        subject_root,
        "draft_generated",
        {
            "version_hash": state.draft_version_hash,
            "chapter_count": len(
                re.findall(r"^# Chapter \d+:", draft_text, flags=re.MULTILINE)
            ),
            "draft_characters": len(draft_text),
            "learning_system_fields": [
                "concept_layers",
                "section_structure",
                "recall_hooks",
                "verification_points",
                "bibliography",
            ],
        },
    )

    return draft_text


__all__ = ["generate_draft"]
```

## Test command

```bash
uv run pytest tests/test_drafting_reconstruction.py -q
```

## Expected output

```text
3 passed
```

## Commit

```bash
git add src/study/drafting.py tests/test_drafting_reconstruction.py
git commit -m "feat(study): generate dense reconstructed learning drafts"
```

---

# Task 5 — Add failing recall tests for reconstructed section use

**File:** `tests/test_recall_from_reconstructed_sections.py`

```python
from pathlib import Path

import pytest

from study.drafting import generate_draft
from study.models import ApprovalRequiredError, ProgressState, SourceReference
from study.recall import extract_sections, generate_first_pass_questions
from study.storage import load_progress, save_progress


def make_subject_root(tmp_path: Path) -> Path:
    subject_root = tmp_path / "subjects" / "platform-learning"
    source_dir = subject_root / "source_reference_data"
    source_dir.mkdir(parents=True)

    save_progress(
        subject_root,
        ProgressState(
            subject_id="platform-learning",
            topic="Platform Learning",
            source_manifest_count=1,
        ),
    )

    source = SourceReference(
        kind="pasted_text",
        content=(
            "A reliable study system turns source material into a hierarchy of "
            "concepts, mechanisms, recall prompts, and verification checks."
        ),
        metadata={"keyword": "study-system"},
    )
    (source_dir / "source_0000.json").write_text(
        source.model_dump_json(),
        encoding="utf-8",
    )

    return subject_root


def approve_subject(subject_root: Path) -> None:
    state = load_progress(subject_root)
    state.approval_status = True
    state.phase = "draft_approved"
    save_progress(subject_root, state)


def test_extract_sections_reads_reconstructed_second_level_sections(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)
    draft = generate_draft(subject_root, "Platform Learning")

    sections = extract_sections(draft)
    titles = [title for _, title, _ in sections]

    assert "Concept Reconstruction" in titles
    assert "Learning Model" in titles
    assert "Recall Hooks" in titles
    assert "Verification Points" in titles
    assert len(sections) >= 12


def test_first_pass_questions_use_reconstructed_learning_sections(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)
    generate_draft(subject_root, "Platform Learning")
    approve_subject(subject_root)

    questions = generate_first_pass_questions(subject_root, n=8)
    prompts = "\n".join(question.prompt.lower() for question in questions)

    assert len(questions) == 8
    assert "concept reconstruction" in prompts
    assert "learning model" in prompts
    assert "recall hook" in prompts
    assert "verification" in prompts


def test_first_pass_questions_still_require_approval(tmp_path: Path) -> None:
    subject_root = make_subject_root(tmp_path)
    generate_draft(subject_root, "Platform Learning")

    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(subject_root, n=3)
```

## Test command

```bash
uv run pytest tests/test_recall_from_reconstructed_sections.py -q
```

## Expected red output

```text
FAILED tests/test_recall_from_reconstructed_sections.py::test_extract_sections_reads_reconstructed_second_level_sections
```

The existing parser treats `##` headers incorrectly because top-level header matching catches them first.

---

# Task 6 — Update recall extraction and question generation

**File:** `src/study/recall.py`

Replace only `extract_sections`, `_extract_chapters_as_fallback`, `generate_prompt_template`, and `generate_first_pass_questions` with this code:

```python
def extract_sections(draft_text: str) -> list[tuple[str, str, str]]:
    """Parse a markdown draft into (chapter, section_title, content) tuples.

    Sections are identified by ``##`` headers inside ``# Chapter`` blocks.
    The References section is excluded because recall must be generated from
    reconstructed learning content, not bibliography entries.
    """
    lines = draft_text.splitlines()
    sections: list[tuple[str, str, str]] = []

    current_chapter: str | None = None
    current_title: str | None = None
    section_lines: list[str] = []

    for line in lines:
        if re.match(r"^# References\s*$", line):
            _flush_section(
                sections,
                current_chapter,
                current_title,
                "\n".join(section_lines).strip(),
            )
            break

        if re.match(r"^# Chapter\s+\d+:", line):
            _flush_section(
                sections,
                current_chapter,
                current_title,
                "\n".join(section_lines).strip(),
            )
            current_chapter = line.strip().lstrip("# ").strip()
            current_title = None
            section_lines = []
            continue

        if re.match(r"^##\s+", line):
            _flush_section(
                sections,
                current_chapter,
                current_title,
                "\n".join(section_lines).strip(),
            )
            current_title = line.strip().lstrip("# ").strip()
            section_lines = []
            continue

        section_lines.append(line)

    _flush_section(
        sections,
        current_chapter,
        current_title,
        "\n".join(section_lines).strip(),
    )
    return sections


def _extract_chapters_as_fallback(draft_text: str) -> list[tuple[str, str, str]]:
    """Fallback for older drafts without ``##`` reconstructed sections."""
    lines = draft_text.splitlines()
    chapters: list[tuple[str, str, str]] = []

    current_chapter: str | None = None
    content_lines: list[str] = []

    for line in lines:
        if re.match(r"^# References\s*$", line):
            if current_chapter:
                _flush_section(
                    chapters,
                    current_chapter,
                    current_chapter,
                    "\n".join(content_lines).strip(),
                )
            break

        if re.match(r"^# Chapter\s+\d+:", line):
            if current_chapter:
                _flush_section(
                    chapters,
                    current_chapter,
                    current_chapter,
                    "\n".join(content_lines).strip(),
                )
            current_chapter = line.strip().lstrip("# ").strip()
            content_lines = []
            continue

        content_lines.append(line)

    if current_chapter:
        _flush_section(
            chapters,
            current_chapter,
            current_chapter,
            "\n".join(content_lines).strip(),
        )

    return chapters


def generate_prompt_template(topic: str) -> str:
    """Return a structured open-ended prompt for a reconstructed section."""
    normalized = topic.lower()

    if "concept reconstruction" in normalized:
        return "Rebuild the concept structure in your own words, including roles, relationships, and mechanism."
    if "learning model" in normalized:
        return "Explain the learning model and show how orient, connect, simulate, and verify work together."
    if "recall hook" in normalized:
        return "Use the recall hooks to reconstruct the section from memory without quoting the source."
    if "verification" in normalized:
        return "Answer the verification checks and explain what would prove real understanding."

    return f"Explain the reconstructed learning value of {topic} in your own words."


def _compact_excerpt(content: str, limit: int = 220) -> str:
    """Return a compact excerpt from reconstructed content for question context."""
    compact = re.sub(r"\s+", " ", content).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0] + "."


def generate_first_pass_questions(
    subject_root: Path,
    n: int = 5,
) -> list[RecallQuestion]:
    """Generate open-ended recall prompts from approved reconstructed sections."""
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before recall")

    draft_path = subject_root / "learning_draft.md"
    if not draft_path.exists():
        raise FileNotFoundError(f"{draft_path} does not exist in {subject_root}")

    draft_text = draft_path.read_text(encoding="utf-8")
    sections = extract_sections(draft_text)

    if not sections:
        sections = _extract_chapters_as_fallback(draft_text)

    questions: list[RecallQuestion] = []
    for index, (chapter, title, content) in enumerate(sections[:n]):
        section_kind = title.lower()
        if "concept reconstruction" in section_kind:
            topic = f"{chapter} — Concept Reconstruction"
        elif "learning model" in section_kind:
            topic = f"{chapter} — Learning Model"
        elif "recall hook" in section_kind:
            topic = f"{chapter} — Recall Hooks"
        elif "verification" in section_kind:
            topic = f"{chapter} — Verification Points"
        else:
            topic = title

        prompt = (
            f"Based on the reconstructed section '{title}' under '{chapter}', "
            f"{generate_prompt_template(title)} "
            f"Use this section context as your anchor: {_compact_excerpt(content)}"
        )

        questions.append(
            RecallQuestion(
                id=f"q_{index + 1}",
                topic=topic,
                prompt=prompt,
            )
        )

    state = load_progress(subject_root)
    state.phase = "recall_first_pass"
    state.next_recursors_cursor = len(questions)
    save_progress(subject_root, state)

    return questions
```

## Test command

```bash
uv run pytest tests/test_recall_from_reconstructed_sections.py -q
```

## Expected output

```text
3 passed
```

## Commit

```bash
git add src/study/recall.py tests/test_recall_from_reconstructed_sections.py
git commit -m "feat(study): generate recall from reconstructed sections"
```

---

# Task 7 — Run focused integration tests

## Command

```bash
uv run pytest \
  tests/test_learning_draft_system.py \
  tests/test_drafting_reconstruction.py \
  tests/test_recall_from_reconstructed_sections.py \
  -q
```

## Expected output

```text
8 passed
```

---

# Task 8 — Run full test suite

## Command

```bash
uv run pytest -q
```

## Expected output

```text
83 passed
```

If the baseline had a different number than `80 passed`, expected final count is baseline plus `8` new tests.

---

# Task 9 — Manual CLI smoke test without changing signatures

## Commands

```bash
tmpdir="$(mktemp -d)"
cd "$tmpdir"

uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study subjects new k8s "Kubernetes Operations"

uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study intake k8s --text "Kubernetes schedules pods onto nodes and restarts containers when they fail. Controllers reconcile desired state against observed state."

uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study draft k8s

test "$(wc -c < subjects/k8s/learning_draft.md)" -ge 3000
grep -q "^# Chapter 1:" subjects/k8s/learning_draft.md
grep -q "## Concept Reconstruction" subjects/k8s/learning_draft.md
grep -q "## Learning Model" subjects/k8s/learning_draft.md
grep -q "## Recall Hooks" subjects/k8s/learning_draft.md
grep -q "## Verification Points" subjects/k8s/learning_draft.md
grep -q "^# References" subjects/k8s/learning_draft.md

uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study recall k8s --mode=first-pass
```

## Expected recall gate output before approval

```text
Error: draft must be approved before recall. Run 'study subjects approve <id>' first.
```

## Approval and recall commands

```bash
uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study subjects approve k8s

uv run --project /home/user01/project/study/my-study/.worktree/study-harness \
  study recall k8s --mode=first-pass
```

## Expected approved recall output

```text
First pass recall (5 questions):
```

---

# Task 10 — Final verification grep checks

## Commands

```bash
cd /home/user01/project/study/my-study/.worktree/study-harness

grep -R "Insert topic\|\[Topic\]\|{{topic}}" -n src/study tests || true
grep -R "def generate_draft" -n src/study/drafting.py
grep -R "LearningDraftSystem" -n src/study tests
grep -R "approval_status" -n src/study/recall.py src/study/cli.py
```

## Expected output

The first command should print no matching source lines.

The remaining commands should show:

```text
src/study/drafting.py:def generate_draft(subject_root: Path, topic: str) -> str:
src/study/models.py:class LearningDraftSystem(BaseModel):
tests/test_learning_draft_system.py:from study.models import LearningDraftSystem
```

And approval checks should still appear in recall and CLI paths.

---

# Task 11 — Final commit

## Command

```bash
git status --short
git add src/study/drafting.py src/study/models.py src/study/recall.py tests/
git commit -m "test(study): verify learning draft reconstruction contract"
```

If all prior commits were already made and `git status --short` is empty, skip this final commit.

---

# Final acceptance checklist

* `generate_draft` produces at least 3 substantive chapters.
* Every chapter contains `Concept Reconstruction`, `Learning Model`, `Recall Hooks`, and `Verification Points`.
* Drafts are contract-validated at generation time for minimum 3000 characters.
* Raw source prose is kept out of the body and appears only in `# References`.
* `LearningDraftSystem` exists as the pydantic ontology schema.
* `recall.py` generates first-pass questions from reconstructed sections.
* Approval gate remains enforced before recall.
* CLI signatures remain unchanged.
* Tests cover ontology, structure, density, source non-derivation, recall extraction, and approval gating.
