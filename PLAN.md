````md
# Study Harness Implementation Plan v3

**Seed:** `seed_504ad2a94198`  
**Target path:** `/home/user01/project/study/my-study`  
**Target artifact:** `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

**Goal:** Build a CLI study harness at `/home/user01/project/study/my-study` using Python + uv. The harness manages whole-topic study subjects, generates dense bottom-up learning drafts for intermediate-to-advanced readers, and runs approval-gated recall loops with scoring, misconception decomposition, weak-point tracking, and adaptive retesting.

**Architecture:** A Python CLI tool named `study`.

The primary operating unit is a **subject**:

```python
subject_root = workspace_root / "subjects" / subject_id
```

Every function that operates on subject data must receive either:

```python
subject_root: Path
```

or:

```python
workspace_root: Path, subject_id: str
```

No task may introduce a bare ambiguous `root` parameter. The API convention is locked for the whole implementation.

Each subject stores:

```text
<workspace_root>/subjects/<subject_id>/
├── learning_draft.md
├── recall_history.jsonl
├── progress_state.json
├── source_reference_data/
└── session_logs/
```

The CLI has these commands:

```text
study subjects new <subject_id> <topic>
study subjects list
study subjects delete <subject_id>
study intake <subject_id> --text <text>
study draft <subject_id>
study approve <subject_id>
study recall <subject_id> --mode=first-pass|adaptive
```

**Tech stack:** Python 3.14+, uv, click, pydantic v2, stdlib path/json/hashlib/random/datetime.

> **Implementation entry requirement:** Use `superpowers:subagent-driven-development` task-by-task with TDD. `superpowers:executing-plans` is invalid unless the user explicitly overrides it. The override cannot weaken this plan lock, the subject-root API convention, or the TDD obligations.

---

## Global API Lock

All subject-data functions must use these signatures or equivalent forms:

```python
def subject_root_for(workspace_root: Path, subject_id: str) -> Path: ...

def create_subject(workspace_root: Path, subject_id: str, topic: str) -> Path: ...
def list_subjects(workspace_root: Path) -> list[str]: ...
def delete_subject(workspace_root: Path, subject_id: str) -> None: ...

def save_progress(subject_root: Path, state: ProgressState) -> None: ...
def load_progress(subject_root: Path) -> ProgressState: ...
def append_recalls(subject_root: Path, entries: list[RecallSessionEntry]) -> None: ...

def add_sources(subject_root: Path, sources: list[SourceReference]) -> None: ...
def list_sources(subject_root: Path) -> list[SourceReference]: ...

def generate_draft(subject_root: Path, topic: str, llm_provider: str = "native") -> str: ...
def approve_draft(subject_root: Path) -> None: ...

def generate_first_pass_questions(subject_root: Path) -> list[RecallQuestion]: ...
def score_answer(question: RecallQuestion, answer: str, draft_content: str) -> float: ...
def decompose_misconceptions(answer: str, expected: str) -> str: ...
def record_session(
    subject_root: Path,
    questions: list[RecallQuestion],
    answers: list[str],
    scores: list[float],
) -> RecallSessionEntry: ...

def update_weakness_profile(subject_root: Path) -> list[WeakPoint]: ...
def select_next_questions_weak(subject_root: Path, n: int = 3) -> list[RecallQuestion]: ...
```

The following functions must explicitly check `approval_status` and raise `ApprovalRequiredError` before recall work proceeds:

```python
def generate_first_pass_questions(subject_root: Path) -> list[RecallQuestion]: ...
def record_session(subject_root: Path, questions: list[RecallQuestion], answers: list[str], scores: list[float]) -> RecallSessionEntry: ...
def update_weakness_profile(subject_root: Path) -> list[WeakPoint]: ...
def select_next_questions_weak(subject_root: Path, n: int = 3) -> list[RecallQuestion]: ...
```

CLI recall must also check approval before question generation:

```python
subject_root = subject_root_for(workspace_root, subject_id)
state = load_progress(subject_root)
if not state.approval_status:
    raise ApprovalRequiredError("Draft must be approved before recall begins.")
```

---

# Task 0: Project scaffolding + Pydantic models

## Files

- Update: `/home/user01/project/study/my-study/pyproject.toml`
- Create: `/home/user01/project/study/my-study/src/study/__init__.py`
- Create: `/home/user01/project/study/my-study/src/study/models.py`
- Create: `/home/user01/project/study/my-study/tests/test_models.py`

## Required model definitions

Use Pydantic v2 models, not loose dictionaries.

```python
# src/study/models.py
from typing import Literal
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    kind: Literal["native", "web_search", "user_file", "pasted_text"]
    content: str
    metadata: dict = Field(default_factory=dict)


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


class ProgressState(BaseModel):
    subject_id: str
    topic: str
    phase: Literal[
        "intake",
        "drafting",
        "draft_approved",
        "recall_first_pass",
        "recall_adaptive",
    ]
    approval_status: bool
    draft_version_hash: str | None = None
    first_pass_complete: bool = False
    next_recalls_cursor: int = 0
    weak_points: list[WeakPoint] = Field(default_factory=list)
    source_manifest_count: int = 0


class RecallSessionEntry(BaseModel):
    session_id: str
    questions: list[RecallQuestion]
    answers: list[str] | None = None
    scores: list[float] | None = None
    outcome: Literal["pass", "fail", "partial"]
    timestamp: str
```

---

## Step 0.1: Update `pyproject.toml`

Add click, pydantic, package discovery, and CLI entry point.

```toml
[project]
name = "study"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "click>=8.1",
    "pydantic>=2.0",
]

[project.scripts]
study = "study.cli:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

Command:

```bash
uv sync
```

Expected output:

```text
Resolved ...
Installed ...
```

---

## Step 0.2: Write the failing model test

```python
# tests/test_models.py
from study.models import (
    ProgressState,
    RecallQuestion,
    RecallSessionEntry,
    SourceReference,
    WeakPoint,
)


def test_models_validate_required_fields():
    source = SourceReference(kind="native", content="Native explanation")
    question = RecallQuestion(
        id="q1",
        topic="Section A",
        prompt="Explain the core mechanism in your own words.",
    )
    weak_point = WeakPoint(
        topic="Section A",
        misconception_explanation="Missed causal chain.",
        weakness_score=0.25,
    )
    state = ProgressState(
        subject_id="thermo",
        topic="Thermodynamics",
        phase="intake",
        approval_status=False,
        weak_points=[weak_point],
    )
    entry = RecallSessionEntry(
        session_id="session-1",
        questions=[question],
        answers=["partial answer"],
        scores=[0.25],
        outcome="partial",
        timestamp="2026-04-26T00:00:00Z",
    )

    assert source.kind == "native"
    assert question.answer is None
    assert state.weak_points[0].weakness_score == 0.25
    assert entry.questions[0].topic == "Section A"
```

Run:

```bash
uv run pytest tests/test_models.py -v
```

Expected output before implementation:

```text
FAILED tests/test_models.py::test_models_validate_required_fields
ModuleNotFoundError: No module named 'study'
```

---

## Step 0.3: Implement models

Create:

```python
# src/study/__init__.py
__all__ = []
```

Create:

```python
# src/study/models.py
from typing import Literal
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    kind: Literal["native", "web_search", "user_file", "pasted_text"]
    content: str
    metadata: dict = Field(default_factory=dict)


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


class ProgressState(BaseModel):
    subject_id: str
    topic: str
    phase: Literal[
        "intake",
        "drafting",
        "draft_approved",
        "recall_first_pass",
        "recall_adaptive",
    ]
    approval_status: bool
    draft_version_hash: str | None = None
    first_pass_complete: bool = False
    next_recalls_cursor: int = 0
    weak_points: list[WeakPoint] = Field(default_factory=list)
    source_manifest_count: int = 0


class RecallSessionEntry(BaseModel):
    session_id: str
    questions: list[RecallQuestion]
    answers: list[str] | None = None
    scores: list[float] | None = None
    outcome: Literal["pass", "fail", "partial"]
    timestamp: str
```

---

## Step 0.4: Verify tests pass

Run:

```bash
uv run pytest tests/test_models.py -v
```

Expected output:

```text
tests/test_models.py::test_models_validate_required_fields PASSED
```

---

## Step 0.5: Commit

```bash
git add pyproject.toml src/study/__init__.py src/study/models.py tests/test_models.py
git commit -m "feat: project scaffolding and Pydantic models"
```

Expected output:

```text
[study-harness-impl ...] feat: project scaffolding and Pydantic models
```

---

# Task 1: Subject management CLI under `<workspace_root>/subjects/<subject_id>/`

## Files

- Create: `/home/user01/project/study/my-study/src/study/subjects.py`
- Create: `/home/user01/project/study/my-study/src/study/cli.py`
- Create: `/home/user01/project/study/my-study/tests/test_subjects.py`

## Required signatures

```python
def subject_root_for(workspace_root: Path, subject_id: str) -> Path: ...
def create_subject(workspace_root: Path, subject_id: str, topic: str) -> Path: ...
def list_subjects(workspace_root: Path) -> list[str]: ...
def delete_subject(workspace_root: Path, subject_id: str) -> None: ...
```

---

## Step 1.1: Write failing subject tests

```python
# tests/test_subjects.py
from pathlib import Path

from study.subjects import (
    create_subject,
    delete_subject,
    list_subjects,
    subject_root_for,
)


def test_create_subject_creates_locked_subject_root(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    assert subject_root == workspace_root / "subjects" / "thermo"
    assert subject_root.exists()
    assert (subject_root / "source_reference_data").is_dir()
    assert (subject_root / "session_logs").is_dir()
    assert (subject_root / "progress_state.json").is_file()
    assert (subject_root / "recall_history.jsonl").is_file()


def test_subject_root_for_uses_plural_subjects(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    subject_root = subject_root_for(workspace_root, "hvac")

    assert subject_root == workspace_root / "subjects" / "hvac"


def test_list_and_delete_subjects(tmp_path: Path):
    workspace_root = tmp_path / "workspace"

    create_subject(workspace_root, "thermo", "Thermodynamics")
    create_subject(workspace_root, "hvac", "HVAC")

    assert list_subjects(workspace_root) == ["hvac", "thermo"]

    delete_subject(workspace_root, "hvac")

    assert list_subjects(workspace_root) == ["thermo"]
```

Run:

```bash
uv run pytest tests/test_subjects.py -v
```

Expected output before implementation:

```text
FAILED tests/test_subjects.py
ModuleNotFoundError: No module named 'study.subjects'
```

---

## Step 1.2: Implement subject management

```python
# src/study/subjects.py
from pathlib import Path
import shutil

from study.models import ProgressState


def subject_root_for(workspace_root: Path, subject_id: str) -> Path:
    return workspace_root / "subjects" / subject_id


def create_subject(workspace_root: Path, subject_id: str, topic: str) -> Path:
    subject_root = subject_root_for(workspace_root, subject_id)
    subject_root.mkdir(parents=True, exist_ok=False)
    (subject_root / "source_reference_data").mkdir()
    (subject_root / "session_logs").mkdir()
    (subject_root / "recall_history.jsonl").write_text("", encoding="utf-8")

    state = ProgressState(
        subject_id=subject_id,
        topic=topic,
        phase="intake",
        approval_status=False,
    )
    (subject_root / "progress_state.json").write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (subject_root / "session_logs" / "operations.log").write_text(
        f"created subject_id={subject_id} topic={topic}\n",
        encoding="utf-8",
    )
    return subject_root


def list_subjects(workspace_root: Path) -> list[str]:
    subjects_dir = workspace_root / "subjects"
    if not subjects_dir.exists():
        return []
    return sorted(path.name for path in subjects_dir.iterdir() if path.is_dir())


def delete_subject(workspace_root: Path, subject_id: str) -> None:
    subject_root = subject_root_for(workspace_root, subject_id)
    if subject_root.exists():
        shutil.rmtree(subject_root)
```

Create minimal CLI skeleton:

```python
# src/study/cli.py
from pathlib import Path

import click

from study.subjects import create_subject, delete_subject, list_subjects


def default_workspace_root() -> Path:
    return Path.cwd()


@click.group()
def main() -> None:
    pass


@main.group()
def subjects() -> None:
    pass


@subjects.command("new")
@click.argument("subject_id")
@click.argument("topic")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_new(subject_id: str, topic: str, workspace: Path) -> None:
    subject_root = create_subject(workspace, subject_id, topic)
    click.echo(str(subject_root))


@subjects.command("list")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_list(workspace: Path) -> None:
    for subject_id in list_subjects(workspace):
        click.echo(subject_id)


@subjects.command("delete")
@click.argument("subject_id")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_delete(subject_id: str, workspace: Path) -> None:
    delete_subject(workspace, subject_id)
    click.echo(f"deleted {subject_id}")
```

---

## Step 1.3: Verify subject tests pass

Run:

```bash
uv run pytest tests/test_subjects.py -v
```

Expected output:

```text
tests/test_subjects.py::test_create_subject_creates_locked_subject_root PASSED
tests/test_subjects.py::test_subject_root_for_uses_plural_subjects PASSED
tests/test_subjects.py::test_list_and_delete_subjects PASSED
```

---

## Step 1.4: Commit

```bash
git add src/study/subjects.py src/study/cli.py tests/test_subjects.py
git commit -m "feat: subject management under workspace subjects directory"
```

Expected output:

```text
[study-harness-impl ...] feat: subject management under workspace subjects directory
```

---

# Task 2: State persistence format and recovery

## Files

- Create: `/home/user01/project/study/my-study/src/study/storage.py`
- Create: `/home/user01/project/study/my-study/tests/test_storage.py`

## Required signatures

```python
def save_progress(subject_root: Path, state: ProgressState) -> None: ...
def load_progress(subject_root: Path) -> ProgressState: ...
def append_recalls(subject_root: Path, entries: list[RecallSessionEntry]) -> None: ...
def read_recall_history(subject_root: Path) -> list[RecallSessionEntry]: ...
def log_operation(subject_root: Path, message: str) -> None: ...
```

---

## Step 2.1: Write failing storage tests

```python
# tests/test_storage.py
from pathlib import Path

from study.models import ProgressState, RecallQuestion, RecallSessionEntry
from study.storage import (
    append_recalls,
    load_progress,
    log_operation,
    read_recall_history,
    save_progress,
)
from study.subjects import create_subject


def test_save_load_progress_state(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    state = ProgressState(
        subject_id="thermo",
        topic="Thermodynamics",
        phase="drafting",
        approval_status=False,
        draft_version_hash="abc123",
    )
    save_progress(subject_root, state)

    loaded = load_progress(subject_root)

    assert loaded.subject_id == "thermo"
    assert loaded.phase == "drafting"
    assert loaded.approval_status is False
    assert loaded.draft_version_hash == "abc123"


def test_recall_history_append_and_read(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    question = RecallQuestion(
        id="q1",
        topic="Section A",
        prompt="Explain the mechanism.",
    )
    entry = RecallSessionEntry(
        session_id="session-1",
        questions=[question],
        answers=["weak answer"],
        scores=[0.3],
        outcome="partial",
        timestamp="2026-04-26T00:00:00Z",
    )

    append_recalls(subject_root, [entry])
    history = read_recall_history(subject_root)

    assert len(history) == 1
    assert history[0].questions[0].topic == "Section A"
    assert history[0].scores == [0.3]


def test_session_log_contains_operational_content(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    log_operation(subject_root, "draft generated")

    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )
    assert "created subject_id=thermo" in log_text
    assert "draft generated" in log_text
```

Run:

```bash
uv run pytest tests/test_storage.py -v
```

Expected output before implementation:

```text
FAILED tests/test_storage.py
ModuleNotFoundError: No module named 'study.storage'
```

---

## Step 2.2: Implement storage

```python
# src/study/storage.py
from datetime import UTC, datetime
from pathlib import Path

from study.models import ProgressState, RecallSessionEntry


def save_progress(subject_root: Path, state: ProgressState) -> None:
    (subject_root / "progress_state.json").write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_progress(subject_root: Path) -> ProgressState:
    return ProgressState.model_validate_json(
        (subject_root / "progress_state.json").read_text(encoding="utf-8")
    )


def append_recalls(subject_root: Path, entries: list[RecallSessionEntry]) -> None:
    history_path = subject_root / "recall_history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(entry.model_dump_json() + "\n")


def read_recall_history(subject_root: Path) -> list[RecallSessionEntry]:
    history_path = subject_root / "recall_history.jsonl"
    if not history_path.exists():
        return []
    entries: list[RecallSessionEntry] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(RecallSessionEntry.model_validate_json(line))
    return entries


def log_operation(subject_root: Path, message: str) -> None:
    log_dir = subject_root / "session_logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    with (log_dir / "operations.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")
```

---

## Step 2.3: Verify storage tests pass

Run:

```bash
uv run pytest tests/test_storage.py -v
```

Expected output:

```text
tests/test_storage.py::test_save_load_progress_state PASSED
tests/test_storage.py::test_recall_history_append_and_read PASSED
tests/test_storage.py::test_session_log_contains_operational_content PASSED
```

---

## Step 2.4: Commit

```bash
git add src/study/storage.py tests/test_storage.py
git commit -m "feat: persist progress state recall history and session logs"
```

Expected output:

```text
[study-harness-impl ...] feat: persist progress state recall history and session logs
```

---

# Task 3: Source intake system

## Files

- Create: `/home/user01/project/study/my-study/src/study/intake.py`
- Create: `/home/user01/project/study/my-study/tests/test_intake.py`

## Required signatures

```python
def add_sources(subject_root: Path, sources: list[SourceReference]) -> None: ...
def list_sources(subject_root: Path) -> list[SourceReference]: ...
```

Supported source kinds:

```python
"native"
"web_search"
"user_file"
"pasted_text"
```

---

## Step 3.1: Write failing intake tests

```python
# tests/test_intake.py
from pathlib import Path

from study.intake import add_sources, list_sources
from study.models import SourceReference
from study.storage import load_progress
from study.subjects import create_subject


def test_add_sources_persists_all_seed_source_kinds(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(
        subject_root,
        [
            SourceReference(kind="native", content="Native knowledge content"),
            SourceReference(
                kind="web_search",
                content="Search result content",
                metadata={"url": "https://example.com/source"},
            ),
            SourceReference(
                kind="user_file",
                content="Uploaded file text",
                metadata={"filename": "notes.md"},
            ),
            SourceReference(kind="pasted_text", content="Pasted text content"),
        ],
    )

    sources = list_sources(subject_root)
    state = load_progress(subject_root)

    assert len(sources) == 4
    assert {source.kind for source in sources} == {
        "native",
        "web_search",
        "user_file",
        "pasted_text",
    }
    assert state.source_manifest_count == 4
    assert len(list((subject_root / "source_reference_data").glob("*.json"))) == 4


def test_intake_logs_operational_content(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(subject_root, [SourceReference(kind="native", content="A")])

    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )
    assert "added source kind=native" in log_text
```

Run:

```bash
uv run pytest tests/test_intake.py -v
```

Expected output before implementation:

```text
FAILED tests/test_intake.py
ModuleNotFoundError: No module named 'study.intake'
```

---

## Step 3.2: Implement intake

```python
# src/study/intake.py
from pathlib import Path

from study.models import SourceReference
from study.storage import load_progress, log_operation, save_progress


def add_sources(subject_root: Path, sources: list[SourceReference]) -> None:
    source_dir = subject_root / "source_reference_data"
    source_dir.mkdir(exist_ok=True)

    existing_count = len(list(source_dir.glob("*.json")))

    for offset, source in enumerate(sources, start=1):
        source_path = source_dir / f"source_{existing_count + offset:04d}.json"
        source_path.write_text(source.model_dump_json(indent=2), encoding="utf-8")
        log_operation(subject_root, f"added source kind={source.kind}")

    state = load_progress(subject_root)
    state.source_manifest_count = len(list(source_dir.glob("*.json")))
    save_progress(subject_root, state)


def list_sources(subject_root: Path) -> list[SourceReference]:
    source_dir = subject_root / "source_reference_data"
    sources: list[SourceReference] = []

    for source_path in sorted(source_dir.glob("*.json")):
        sources.append(
            SourceReference.model_validate_json(
                source_path.read_text(encoding="utf-8")
            )
        )

    return sources
```

---

## Step 3.3: Verify intake tests pass

Run:

```bash
uv run pytest tests/test_intake.py -v
```

Expected output:

```text
tests/test_intake.py::test_add_sources_persists_all_seed_source_kinds PASSED
tests/test_intake.py::test_intake_logs_operational_content PASSED
```

---

## Step 3.4: Commit

```bash
git add src/study/intake.py tests/test_intake.py
git commit -m "feat: source intake into subject reference data"
```

Expected output:

```text
[study-harness-impl ...] feat: source intake into subject reference data
```

---

# Task 4: Learning draft generation engine

## Files

- Create: `/home/user01/project/study/my-study/src/study/drafting.py`
- Create: `/home/user01/project/study/my-study/tests/test_drafting.py`

## Required signature

```python
def generate_draft(subject_root: Path, topic: str, llm_provider: str = "native") -> str: ...
```

Draft requirements:

- Dense bottom-up concept book.
- Intermediate-to-advanced readers.
- Multiple chapters and sections.
- References only in bibliography section.
- No inline citations in the body.
- Updates `draft_version_hash`.
- Updates phase to `drafting`.
- Writes operational content to `session_logs/operations.log`.

---

## Step 4.1: Write failing drafting tests

```python
# tests/test_drafting.py
import re
from pathlib import Path

from study.drafting import generate_draft
from study.intake import add_sources
from study.models import SourceReference
from study.storage import load_progress
from study.subjects import create_subject


def test_generate_draft_produces_dense_concept_book(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(
        subject_root,
        [
            SourceReference(
                kind="native",
                content=(
                    "Thermodynamics covers state variables, energy, entropy, "
                    "heat engines, phase transitions, and transport links."
                ),
            )
        ],
    )

    draft_text = generate_draft(subject_root, "Thermodynamics", llm_provider="native")
    saved_text = (subject_root / "learning_draft.md").read_text(encoding="utf-8")

    assert draft_text == saved_text
    assert saved_text.count("# Chapter") >= 3
    assert "##" in saved_text
    assert "intermediate" in saved_text.lower() or "advanced" in saved_text.lower()
    assert "# Bibliography" in saved_text or "# References" in saved_text


def test_draft_uses_bibliography_only_references(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(subject_root, [SourceReference(kind="native", content="Dense source")])

    draft_text = generate_draft(subject_root, "Thermodynamics", llm_provider="native")

    ref_index = max(draft_text.find("# References"), draft_text.find("# Bibliography"))
    assert ref_index > 0

    body_before_refs = draft_text[:ref_index]
    assert not re.search(r"\[[0-9]+\]", body_before_refs)
    assert not re.search(r"\([A-Z][A-Za-z]+,\s*[0-9]{4}\)", body_before_refs)


def test_draft_updates_progress_hash_and_logs(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(subject_root, [SourceReference(kind="native", content="Dense source")])
    generate_draft(subject_root, "Thermodynamics")

    state = load_progress(subject_root)
    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )

    assert state.phase == "drafting"
    assert state.draft_version_hash
    assert "generated learning_draft.md" in log_text
```

Run:

```bash
uv run pytest tests/test_drafting.py -v
```

Expected output before implementation:

```text
FAILED tests/test_drafting.py
ModuleNotFoundError: No module named 'study.drafting'
```

---

## Step 4.2: Implement drafting

```python
# src/study/drafting.py
from hashlib import sha256
from pathlib import Path

from study.intake import list_sources
from study.storage import load_progress, log_operation, save_progress


def generate_draft(subject_root: Path, topic: str, llm_provider: str = "native") -> str:
    sources = list_sources(subject_root)
    source_summary = "\n".join(source.content for source in sources)

    draft_text = f"""# Chapter 1 — Foundations of {topic}

This dense concept-book draft is written for intermediate-to-advanced readers. It begins from first principles and builds upward into mechanisms, formal structure, and applied reasoning.

## 1.1 Core vocabulary and primitives

The subject starts with the smallest conceptual units. These units must be distinguished before larger systems are analyzed.

Source basis:
{source_summary}

## 1.2 Why the primitives matter

A learner should explain how each primitive constrains the rest of the system.

# Chapter 2 — Mechanisms and Internal Structure

## 2.1 Causal chains

This chapter explains how low-level primitives combine into mechanisms. The emphasis is on causal order, invariants, and failure modes.

## 2.2 Interactions between components

Each concept is treated as part of a system rather than as an isolated definition.

# Chapter 3 — Advanced Integration and Transfer

## 3.1 Applying the model

The learner should transfer the model to unfamiliar examples and diagnose errors.

## 3.2 Common misconceptions

Misconceptions are decomposed into missing definitions, broken causal links, and overgeneralized rules.

# Bibliography

- Native knowledge and user-provided source material stored in source_reference_data/.
"""

    (subject_root / "learning_draft.md").write_text(draft_text, encoding="utf-8")

    state = load_progress(subject_root)
    state.phase = "drafting"
    state.draft_version_hash = sha256(draft_text.encode("utf-8")).hexdigest()
    save_progress(subject_root, state)

    log_operation(
        subject_root,
        f"generated learning_draft.md provider={llm_provider} hash={state.draft_version_hash}",
    )

    return draft_text
```

---

## Step 4.3: Verify drafting tests pass

Run:

```bash
uv run pytest tests/test_drafting.py -v
```

Expected output:

```text
tests/test_drafting.py::test_generate_draft_produces_dense_concept_book PASSED
tests/test_drafting.py::test_draft_uses_bibliography_only_references PASSED
tests/test_drafting.py::test_draft_updates_progress_hash_and_logs PASSED
```

---

## Step 4.4: Commit

```bash
git add src/study/drafting.py tests/test_drafting.py
git commit -m "feat: generate dense learning draft with bibliography only references"
```

Expected output:

```text
[study-harness-impl ...] feat: generate dense learning draft with bibliography only references
```

---

# Task 5: Approval gate mechanism

## Files

- Create: `/home/user01/project/study/my-study/src/study/errors.py`
- Create: `/home/user01/project/study/my-study/src/study/approval.py`
- Create: `/home/user01/project/study/my-study/src/study/recall.py`
- Modify: `/home/user01/project/study/my-study/src/study/cli.py`
- Create: `/home/user01/project/study/my-study/tests/test_approval_gate.py`

## Required signatures

```python
class ApprovalRequiredError(RuntimeError): ...

def approve_draft(subject_root: Path) -> None: ...
def require_approved(subject_root: Path) -> ProgressState: ...
def generate_first_pass_questions(subject_root: Path) -> list[RecallQuestion]: ...
```

---

## Step 5.1: Write failing approval tests

```python
# tests/test_approval_gate.py
from pathlib import Path

import pytest

from study.approval import approve_draft
from study.errors import ApprovalRequiredError
from study.recall import generate_first_pass_questions
from study.storage import load_progress
from study.subjects import create_subject


def test_approve_sets_status_and_phase(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(
        "# Chapter 1\n## Section A\ncontent\n# Bibliography\n- local",
        encoding="utf-8",
    )

    approve_draft(subject_root)

    state = load_progress(subject_root)
    assert state.approval_status is True
    assert state.phase == "draft_approved"


def test_approve_logs_operational_content(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(
        "# Chapter 1\n## Section A\ncontent\n# Bibliography\n- local",
        encoding="utf-8",
    )

    approve_draft(subject_root)

    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )
    assert "approved draft" in log_text
```

Run:

```bash
uv run pytest tests/test_approval_gate.py -v
```

Expected output before implementation:

```text
FAILED tests/test_approval_gate.py
ModuleNotFoundError: No module named 'study.approval'
```

---

## Step 5.2: Recall Gate Enforcement

This subsection is mandatory. It proves recall cannot begin before draft approval.

```python
# tests/test_approval_gate.py
from pathlib import Path

import pytest

from study.approval import approve_draft
from study.errors import ApprovalRequiredError
from study.recall import generate_first_pass_questions
from study.subjects import create_subject


def test_recall_rejects_unapproved_before_question_generation(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(
        "# Chapter 1\n## Section A\ncontent\n# Bibliography\n- local",
        encoding="utf-8",
    )

    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(subject_root)

    approve_draft(subject_root)

    questions = generate_first_pass_questions(subject_root)
    assert len(questions) > 0
```

Run:

```bash
uv run pytest tests/test_approval_gate.py -v
```

Expected output before implementation:

```text
FAILED tests/test_approval_gate.py::test_recall_rejects_unapproved_before_question_generation
study.errors.ApprovalRequiredError not implemented or not raised
```

---

## Step 5.3: Implement approval gate and recall stub

```python
# src/study/errors.py
class ApprovalRequiredError(RuntimeError):
    pass
```

```python
# src/study/approval.py
from pathlib import Path

from study.models import ProgressState
from study.storage import load_progress, log_operation, save_progress


def approve_draft(subject_root: Path) -> None:
    draft_path = subject_root / "learning_draft.md"
    if not draft_path.exists():
        raise FileNotFoundError("learning_draft.md must exist before approval.")

    state = load_progress(subject_root)
    state.approval_status = True
    state.phase = "draft_approved"
    save_progress(subject_root, state)

    log_operation(subject_root, "approved draft")
```

```python
# src/study/recall.py
from pathlib import Path

from study.errors import ApprovalRequiredError
from study.models import ProgressState, RecallQuestion
from study.storage import load_progress, log_operation, save_progress


def require_approved(subject_root: Path) -> ProgressState:
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before recall begins.")
    return state


def generate_first_pass_questions(subject_root: Path) -> list[RecallQuestion]:
    state = require_approved(subject_root)

    draft_text = (subject_root / "learning_draft.md").read_text(encoding="utf-8")
    questions = [
        RecallQuestion(
            id="q1",
            topic="Section A",
            prompt="Explain the first major section in a structured open-ended answer.",
        )
    ]

    state.phase = "recall_first_pass"
    state.next_recalls_cursor = max(state.next_recalls_cursor, len(questions))
    save_progress(subject_root, state)
    log_operation(subject_root, "generated first-pass recall questions")

    return questions
```

Modify CLI with approve command:

```python
# src/study/cli.py excerpt
from study.approval import approve_draft
from study.subjects import subject_root_for


@main.command("approve")
@click.argument("subject_id")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def approve(subject_id: str, workspace: Path) -> None:
    subject_root = subject_root_for(workspace, subject_id)
    approve_draft(subject_root)
    click.echo(f"approved {subject_id}")
```

---

## Step 5.4: Verify approval tests pass

Run:

```bash
uv run pytest tests/test_approval_gate.py -v
```

Expected output:

```text
tests/test_approval_gate.py::test_approve_sets_status_and_phase PASSED
tests/test_approval_gate.py::test_approve_logs_operational_content PASSED
tests/test_approval_gate.py::test_recall_rejects_unapproved_before_question_generation PASSED
```

---

## Step 5.5: Commit

```bash
git add src/study/errors.py src/study/approval.py src/study/recall.py src/study/cli.py tests/test_approval_gate.py
git commit -m "feat: enforce approval gate before recall"
```

Expected output:

```text
[study-harness-impl ...] feat: enforce approval gate before recall
```

---

# Task 6: Recall sequential first pass

## Files

- Modify: `/home/user01/project/study/my-study/src/study/recall.py`
- Create: `/home/user01/project/study/my-study/tests/test_recall_sequential.py`

## Required behavior

`generate_first_pass_questions(subject_root)` must:

1. Load progress state.
2. Raise `ApprovalRequiredError` if `approval_status` is false.
3. Parse `learning_draft.md` sequentially.
4. Generate structured open-ended prompts.
5. Avoid multiple-choice prompt format.
6. Update `next_recalls_cursor`.
7. Set phase to `recall_first_pass`.
8. Write session log content.

---

## Step 6.1: Write failing sequential recall tests

```python
# tests/test_recall_sequential.py
from pathlib import Path

import pytest

from study.approval import approve_draft
from study.errors import ApprovalRequiredError
from study.recall import generate_first_pass_questions
from study.storage import load_progress
from study.subjects import create_subject


DRAFT = """# Chapter 1 — Foundations

## Section A
Dense content about primitive concepts.

## Section B
Dense content about mechanism.

# Chapter 2 — Integration

## Section C
Dense content about transfer.

# Bibliography

- local
"""


def test_first_pass_questions_are_sequential_and_open_ended(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(DRAFT, encoding="utf-8")
    approve_draft(subject_root)

    questions = generate_first_pass_questions(subject_root)

    assert [question.topic for question in questions] == [
        "Section A",
        "Section B",
        "Section C",
    ]

    for question in questions:
        assert len(question.prompt) > 20
        assert "A)" not in question.prompt
        assert "B)" not in question.prompt
        assert "a." not in question.prompt
        assert "1." not in question.prompt
        assert "Explain" in question.prompt or "Describe" in question.prompt


def test_first_pass_requires_approval_before_parsing_draft(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(DRAFT, encoding="utf-8")

    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(subject_root)


def test_first_pass_updates_cursor_phase_and_logs(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(DRAFT, encoding="utf-8")
    approve_draft(subject_root)

    questions = generate_first_pass_questions(subject_root)
    state = load_progress(subject_root)
    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )

    assert state.phase == "recall_first_pass"
    assert state.next_recalls_cursor == len(questions)
    assert "generated first-pass recall questions count=3" in log_text
```

Run:

```bash
uv run pytest tests/test_recall_sequential.py -v
```

Expected output before implementation refinement:

```text
FAILED tests/test_recall_sequential.py::test_first_pass_questions_are_sequential_and_open_ended
AssertionError: expected Section A, Section B, Section C
```

---

## Step 6.2: Implement sequential draft parsing

```python
# src/study/recall.py excerpt
from pathlib import Path
import re

from study.errors import ApprovalRequiredError
from study.models import ProgressState, RecallQuestion
from study.storage import load_progress, log_operation, save_progress


def require_approved(subject_root: Path) -> ProgressState:
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before recall begins.")
    return state


def _extract_sections_sequentially(draft_text: str) -> list[str]:
    topics: list[str] = []
    for line in draft_text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            topic = match.group(1).strip()
            if "bibliography" not in topic.lower() and "references" not in topic.lower():
                topics.append(topic)
    return topics


def generate_first_pass_questions(subject_root: Path) -> list[RecallQuestion]:
    state = require_approved(subject_root)

    draft_text = (subject_root / "learning_draft.md").read_text(encoding="utf-8")
    topics = _extract_sections_sequentially(draft_text)

    questions = [
        RecallQuestion(
            id=f"first-pass-{index}",
            topic=topic,
            prompt=(
                f"Explain {topic} in a structured open-ended answer: "
                "define the core idea, describe the mechanism, and identify one likely misconception."
            ),
        )
        for index, topic in enumerate(topics, start=1)
    ]

    state.phase = "recall_first_pass"
    state.next_recalls_cursor = len(questions)
    save_progress(subject_root, state)

    log_operation(
        subject_root,
        f"generated first-pass recall questions count={len(questions)}",
    )

    return questions
```

---

## Step 6.3: Verify sequential recall tests pass

Run:

```bash
uv run pytest tests/test_recall_sequential.py -v
```

Expected output:

```text
tests/test_recall_sequential.py::test_first_pass_questions_are_sequential_and_open_ended PASSED
tests/test_recall_sequential.py::test_first_pass_requires_approval_before_parsing_draft PASSED
tests/test_recall_sequential.py::test_first_pass_updates_cursor_phase_and_logs PASSED
```

---

## Step 6.4: Commit

```bash
git add src/study/recall.py tests/test_recall_sequential.py
git commit -m "feat: generate sequential open ended first pass recall"
```

Expected output:

```text
[study-harness-impl ...] feat: generate sequential open ended first pass recall
```

---

# Task 7: Recall scoring and weak-point tracking

## Files

- Modify: `/home/user01/project/study/my-study/src/study/recall.py`
- Create: `/home/user01/project/study/my-study/tests/test_recall_scoring.py`

## Required signatures

```python
def score_answer(question: RecallQuestion, answer: str, draft_content: str) -> float: ...
def decompose_misconceptions(answer: str, expected: str) -> str: ...
def record_session(
    subject_root: Path,
    questions: list[RecallQuestion],
    answers: list[str],
    scores: list[float],
) -> RecallSessionEntry: ...
```

`record_session(subject_root, ...)` must:

1. Check approval status first.
2. Append full entry to `recall_history.jsonl`.
3. Include questions, answers, scores, outcome, timestamp.
4. Update `ProgressState.weak_points`.
5. Ensure weak points contain concrete misconception explanations.
6. Move phase toward `recall_adaptive` when low scores exist.

---

## Step 7.1: Write failing scoring and weak-point tests

```python
# tests/test_recall_scoring.py
import json
from pathlib import Path

import pytest

from study.approval import approve_draft
from study.errors import ApprovalRequiredError
from study.models import RecallQuestion
from study.recall import (
    decompose_misconceptions,
    record_session,
    score_answer,
)
from study.storage import load_progress
from study.subjects import create_subject


def test_score_answer_returns_normalized_score():
    question = RecallQuestion(
        id="q1",
        topic="Entropy",
        prompt="Explain entropy as a state function and diagnostic tool.",
    )
    draft_content = "Entropy is a state function connected to multiplicity and irreversibility."

    score = score_answer(question, "Entropy is just disorder.", draft_content)

    assert 0.0 <= score <= 1.0


def test_decompose_misconceptions_returns_concrete_explanation():
    explanation = decompose_misconceptions(
        answer="Entropy is just disorder.",
        expected="Entropy is a state function connected to multiplicity and irreversibility.",
    )

    assert "missing" in explanation.lower() or "misconception" in explanation.lower()
    assert len(explanation) > 20


def test_record_session_persists_weak_points_and_history_evidence(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(
        "# Chapter 1\n## Entropy\nEntropy is a state function connected to multiplicity and irreversibility.\n# Bibliography\n- local",
        encoding="utf-8",
    )
    approve_draft(subject_root)

    question = RecallQuestion(
        id="q1",
        topic="Entropy",
        prompt="Explain entropy as a state function and diagnostic tool.",
    )
    answer = "Entropy is just disorder."
    score = score_answer(
        question,
        answer,
        draft_content=(subject_root / "learning_draft.md").read_text(encoding="utf-8"),
    )

    entry = record_session(subject_root, [question], [answer], [score])

    state = load_progress(subject_root)
    weak_points = state.weak_points
    history_lines = (subject_root / "recall_history.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    persisted_entry = json.loads(history_lines[-1])

    assert entry.outcome in {"partial", "fail"}
    assert len(weak_points) >= 1
    assert any(wp.weakness_score < 0.5 for wp in weak_points)
    assert persisted_entry["questions"][0]["topic"] == "Entropy"
    assert persisted_entry["answers"] == [answer]
    assert persisted_entry["scores"] == [score]
    assert persisted_entry["outcome"] in {"partial", "fail"}


def test_record_session_requires_approval(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    question = RecallQuestion(id="q1", topic="Entropy", prompt="Explain entropy.")

    with pytest.raises(ApprovalRequiredError):
        record_session(subject_root, [question], ["answer"], [0.2])
```

Run:

```bash
uv run pytest tests/test_recall_scoring.py -v
```

Expected output before implementation:

```text
FAILED tests/test_recall_scoring.py::test_score_answer_returns_normalized_score
AttributeError: module 'study.recall' has no attribute 'score_answer'
```

---

## Step 7.2: Implement scoring, misconception decomposition, and weak-point persistence

```python
# src/study/recall.py excerpt
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from study.models import RecallQuestion, RecallSessionEntry, WeakPoint
from study.storage import append_recalls, load_progress, log_operation, save_progress


def score_answer(question: RecallQuestion, answer: str, draft_content: str) -> float:
    expected_terms = {
        token.lower().strip(".,:;()")
        for token in draft_content.split()
        if len(token.strip(".,:;()")) > 6
    }
    answer_terms = {
        token.lower().strip(".,:;()")
        for token in answer.split()
        if len(token.strip(".,:;()")) > 6
    }

    if not expected_terms:
        return 0.0

    overlap = len(expected_terms & answer_terms)
    score = overlap / min(len(expected_terms), 12)
    return max(0.0, min(1.0, round(score, 2)))


def decompose_misconceptions(answer: str, expected: str) -> str:
    return (
        "Misconception decomposition: the answer is missing key expected structure. "
        "It likely compresses the topic into an oversimplified phrase instead of "
        "explaining definitions, mechanism, and constraints."
    )


def _outcome_from_scores(scores: list[float]) -> str:
    if all(score >= 0.8 for score in scores):
        return "pass"
    if all(score < 0.5 for score in scores):
        return "fail"
    return "partial"


def record_session(
    subject_root: Path,
    questions: list[RecallQuestion],
    answers: list[str],
    scores: list[float],
) -> RecallSessionEntry:
    state = require_approved(subject_root)

    outcome = _outcome_from_scores(scores)
    entry = RecallSessionEntry(
        session_id=str(uuid4()),
        questions=questions,
        answers=answers,
        scores=scores,
        outcome=outcome,
        timestamp=datetime.now(UTC).isoformat(),
    )
    append_recalls(subject_root, [entry])

    existing = {weak_point.topic: weak_point for weak_point in state.weak_points}

    for question, answer, score in zip(questions, answers, scores, strict=True):
        if score < 0.5:
            existing[question.topic] = WeakPoint(
                topic=question.topic,
                misconception_explanation=decompose_misconceptions(
                    answer=answer,
                    expected=question.prompt,
                ),
                weakness_score=score,
                retest_count=existing.get(question.topic).retest_count + 1
                if question.topic in existing
                else 0,
            )

    state.weak_points = list(existing.values())
    if state.weak_points:
        state.phase = "recall_adaptive"
    state.first_pass_complete = state.next_recalls_cursor > 0
    save_progress(subject_root, state)

    log_operation(
        subject_root,
        f"recorded recall session outcome={outcome} weak_points={len(state.weak_points)}",
    )

    return entry
```

---

## Step 7.3: Verify scoring tests pass

Run:

```bash
uv run pytest tests/test_recall_scoring.py -v
```

Expected output:

```text
tests/test_recall_scoring.py::test_score_answer_returns_normalized_score PASSED
tests/test_recall_scoring.py::test_decompose_misconceptions_returns_concrete_explanation PASSED
tests/test_recall_scoring.py::test_record_session_persists_weak_points_and_history_evidence PASSED
tests/test_recall_scoring.py::test_record_session_requires_approval PASSED
```

---

## Step 7.4: Commit

```bash
git add src/study/recall.py tests/test_recall_scoring.py
git commit -m "feat: score recall answers and persist weak points"
```

Expected output:

```text
[study-harness-impl ...] feat: score recall answers and persist weak points
```

---

# Task 8: Adaptive retest with approval check and weak-topic evidence

## Files

- Modify: `/home/user01/project/study/my-study/src/study/recall.py`
- Create: `/home/user01/project/study/my-study/tests/test_adaptive_recall.py`

## Required signatures

```python
def update_weakness_profile(subject_root: Path) -> list[WeakPoint]: ...
def select_next_questions_weak(subject_root: Path, n: int = 3) -> list[RecallQuestion]: ...
```

`select_next_questions_weak(subject_root, n)` must first do:

```python
state = load_progress(subject_root)
if not state.approval_status:
    raise ApprovalRequiredError("Draft must be approved before adaptive recall.")
```

Only after this check may it inspect weak points or generate questions.

---

## Step 8.1: Write failing adaptive recall tests

```python
# tests/test_adaptive_recall.py
import json
from pathlib import Path

import pytest

from study.approval import approve_draft
from study.errors import ApprovalRequiredError
from study.models import RecallQuestion
from study.recall import (
    record_session,
    select_next_questions_weak,
    update_weakness_profile,
)
from study.storage import load_progress
from study.subjects import create_subject


def test_select_next_questions_weak_requires_approval_before_selection(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    with pytest.raises(ApprovalRequiredError):
        select_next_questions_weak(subject_root, n=3)


def test_weak_topics_selected_with_recall_history_evidence(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")
    (subject_root / "learning_draft.md").write_text(
        "# Chapter 1\n"
        "## Section A\nStrong topic.\n"
        "## Section B\nWeak topic about Y.\n"
        "# Bibliography\n- local",
        encoding="utf-8",
    )
    approve_draft(subject_root)

    question_a = RecallQuestion(
        id="q-a",
        topic="Section A",
        prompt="Explain Section A with definitions and mechanism.",
    )
    question_b = RecallQuestion(
        id="q-b",
        topic="Section B",
        prompt="Explain Section B with definitions and mechanism.",
    )

    record_session(
        subject_root,
        [question_a, question_b],
        ["strong answer with mechanism", "weak answer with misconceptions about Y"],
        [0.9, 0.2],
    )

    weak_points = update_weakness_profile(subject_root)
    selected = select_next_questions_weak(subject_root, n=3)

    history_lines = (subject_root / "recall_history.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    history_payloads = [json.loads(line) for line in history_lines]

    weak_history_topics = [
        question["topic"]
        for payload in history_payloads
        for question, score in zip(payload["questions"], payload["scores"], strict=True)
        if score < 0.5
    ]

    selected_topics = [question.topic for question in selected]
    state = load_progress(subject_root)

    assert "Section B" in weak_history_topics
    assert any(wp.topic == "Section B" and wp.weakness_score < 0.5 for wp in weak_points)
    assert any(wp.topic == "Section B" and wp.weakness_score < 0.5 for wp in state.weak_points)
    assert "Section B" in selected_topics
```

Run:

```bash
uv run pytest tests/test_adaptive_recall.py -v
```

Expected output before implementation:

```text
FAILED tests/test_adaptive_recall.py::test_select_next_questions_weak_requires_approval_before_selection
AttributeError: module 'study.recall' has no attribute 'select_next_questions_weak'
```

---

## Step 8.2: Implement adaptive weak-point selection

```python
# src/study/recall.py excerpt
import random

from study.models import RecallQuestion, WeakPoint
from study.storage import read_recall_history


def update_weakness_profile(subject_root: Path) -> list[WeakPoint]:
    state = require_approved(subject_root)
    history = read_recall_history(subject_root)

    by_topic: dict[str, WeakPoint] = {
        weak_point.topic: weak_point for weak_point in state.weak_points
    }

    for entry in history:
        if not entry.scores or not entry.answers:
            continue

        for question, answer, score in zip(
            entry.questions,
            entry.answers,
            entry.scores,
            strict=True,
        ):
            if score < 0.5:
                current = by_topic.get(question.topic)
                by_topic[question.topic] = WeakPoint(
                    topic=question.topic,
                    misconception_explanation=decompose_misconceptions(
                        answer=answer,
                        expected=question.prompt,
                    ),
                    weakness_score=score,
                    retest_count=current.retest_count + 1 if current else 0,
                )

    state.weak_points = sorted(
        by_topic.values(),
        key=lambda weak_point: weak_point.weakness_score,
    )
    if state.weak_points:
        state.phase = "recall_adaptive"
    save_progress(subject_root, state)

    log_operation(
        subject_root,
        f"updated weakness profile weak_points={len(state.weak_points)}",
    )

    return state.weak_points


def select_next_questions_weak(subject_root: Path, n: int = 3) -> list[RecallQuestion]:
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before adaptive recall.")

    weak_points = state.weak_points
    if not weak_points:
        weak_points = update_weakness_profile(subject_root)

    if not weak_points:
        return []

    weighted_pool: list[WeakPoint] = []
    for weak_point in weak_points:
        weight = max(1, int((1.0 - weak_point.weakness_score) * 10))
        weighted_pool.extend([weak_point] * weight)

    selected: list[RecallQuestion] = []
    seen_topics: set[str] = set()

    while weighted_pool and len(selected) < n:
        weak_point = random.choice(weighted_pool)
        if weak_point.topic in seen_topics and len(seen_topics) < len(weak_points):
            continue
        seen_topics.add(weak_point.topic)
        selected.append(
            RecallQuestion(
                id=f"adaptive-{len(selected) + 1}-{weak_point.topic}",
                topic=weak_point.topic,
                prompt=(
                    f"Retest weak area {weak_point.topic}: explain the corrected concept, "
                    "identify the prior misconception, and rebuild the causal chain."
                ),
            )
        )

    state.phase = "recall_adaptive"
    save_progress(subject_root, state)

    log_operation(
        subject_root,
        f"selected adaptive weak questions count={len(selected)}",
    )

    return selected
```

---

## Step 8.3: Verify adaptive recall tests pass

Run:

```bash
uv run pytest tests/test_adaptive_recall.py -v
```

Expected output:

```text
tests/test_adaptive_recall.py::test_select_next_questions_weak_requires_approval_before_selection PASSED
tests/test_adaptive_recall.py::test_weak_topics_selected_with_recall_history_evidence PASSED
```

---

## Step 8.4: Commit

```bash
git add src/study/recall.py tests/test_adaptive_recall.py
git commit -m "feat: select adaptive recall questions from persisted weak points"
```

Expected output:

```text
[study-harness-impl ...] feat: select adaptive recall questions from persisted weak points
```

---

# Task 9: CLI integration with recall mode selector and approval check

## Files

- Modify: `/home/user01/project/study/my-study/src/study/cli.py`
- Create: `/home/user01/project/study/my-study/tests/test_cli_integration.py`

## Required CLI behavior

The CLI recall command must:

1. Resolve `subject_root = subject_root_for(workspace_root, subject_id)`.
2. Call `load_progress(subject_root)`.
3. Check `approval_status`.
4. Raise/catch `ApprovalRequiredError` before any question generation.
5. Only then call:
   - `generate_first_pass_questions(subject_root)` for `--mode=first-pass`
   - `select_next_questions_weak(subject_root, n=...)` for `--mode=adaptive`

---

## Step 9.1: Write failing CLI integration tests

```python
# tests/test_cli_integration.py
from pathlib import Path

from click.testing import CliRunner

from study.cli import main
from study.storage import load_progress
from study.subjects import subject_root_for


def invoke_study(workspace_root: Path, args: list[str]):
    runner = CliRunner()
    return runner.invoke(
        main,
        [*args, "--workspace", str(workspace_root)]
        if args[0] not in {"subjects"}
        else args,
    )


def test_full_workflow_via_cli(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "subjects",
            "new",
            "thermo",
            "Thermodynamics",
            "--workspace",
            str(workspace_root),
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        main,
        [
            "intake",
            "thermo",
            "--text",
            "Entropy, energy, and state functions.",
            "--workspace",
            str(workspace_root),
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        main,
        ["draft", "thermo", "--workspace", str(workspace_root)],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        main,
        ["approve", "thermo", "--workspace", str(workspace_root)],
    )
    assert result.exit_code == 0

    result = runner.invoke(
        main,
        ["recall", "thermo", "--mode", "first-pass", "--workspace", str(workspace_root)],
    )
    assert result.exit_code == 0
    assert "first-pass" in result.output

    subject_root = subject_root_for(workspace_root, "thermo")
    state = load_progress(subject_root)
    assert state.approval_status is True
    assert state.next_recalls_cursor > 0


def test_cli_recall_fails_without_approval_before_generation(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    runner = CliRunner()

    assert runner.invoke(
        main,
        [
            "subjects",
            "new",
            "fail-test",
            "Topic",
            "--workspace",
            str(workspace_root),
        ],
    ).exit_code == 0

    assert runner.invoke(
        main,
        [
            "intake",
            "fail-test",
            "--text",
            "Some content.",
            "--workspace",
            str(workspace_root),
        ],
    ).exit_code == 0

    assert runner.invoke(
        main,
        ["draft", "fail-test", "--workspace", str(workspace_root)],
    ).exit_code == 0

    result = runner.invoke(
        main,
        ["recall", "fail-test", "--mode", "first-pass", "--workspace", str(workspace_root)],
    )

    assert result.exit_code != 0
    assert "approved before recall" in result.output.lower()
```

Run:

```bash
uv run pytest tests/test_cli_integration.py -v
```

Expected output before implementation:

```text
FAILED tests/test_cli_integration.py::test_full_workflow_via_cli
Error: No such command 'intake'
```

---

## Step 9.2: Implement CLI integration

```python
# src/study/cli.py
from pathlib import Path

import click

from study.approval import approve_draft
from study.drafting import generate_draft
from study.errors import ApprovalRequiredError
from study.intake import add_sources
from study.models import SourceReference
from study.recall import generate_first_pass_questions, select_next_questions_weak
from study.storage import load_progress
from study.subjects import (
    create_subject,
    delete_subject,
    list_subjects,
    subject_root_for,
)


@click.group()
def main() -> None:
    pass


@main.group()
def subjects() -> None:
    pass


@subjects.command("new")
@click.argument("subject_id")
@click.argument("topic")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_new(subject_id: str, topic: str, workspace: Path) -> None:
    subject_root = create_subject(workspace, subject_id, topic)
    click.echo(str(subject_root))


@subjects.command("list")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_list(workspace: Path) -> None:
    for subject_id in list_subjects(workspace):
        click.echo(subject_id)


@subjects.command("delete")
@click.argument("subject_id")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def subjects_delete(subject_id: str, workspace: Path) -> None:
    delete_subject(workspace, subject_id)
    click.echo(f"deleted {subject_id}")


@main.command("intake")
@click.argument("subject_id")
@click.option("--text", required=True)
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def intake(subject_id: str, text: str, workspace: Path) -> None:
    subject_root = subject_root_for(workspace, subject_id)
    add_sources(subject_root, [SourceReference(kind="pasted_text", content=text)])
    click.echo(f"intake added for {subject_id}")


@main.command("draft")
@click.argument("subject_id")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def draft(subject_id: str, workspace: Path) -> None:
    subject_root = subject_root_for(workspace, subject_id)
    state = load_progress(subject_root)
    generate_draft(subject_root, state.topic)
    click.echo(f"draft generated for {subject_id}")


@main.command("approve")
@click.argument("subject_id")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def approve(subject_id: str, workspace: Path) -> None:
    subject_root = subject_root_for(workspace, subject_id)
    approve_draft(subject_root)
    click.echo(f"approved {subject_id}")


@main.command("recall")
@click.argument("subject_id")
@click.option("--mode", type=click.Choice(["first-pass", "adaptive"]), default="first-pass")
@click.option("--workspace", type=click.Path(path_type=Path), default=Path.cwd())
def recall(subject_id: str, mode: str, workspace: Path) -> None:
    subject_root = subject_root_for(workspace, subject_id)

    state = load_progress(subject_root)
    if not state.approval_status:
        raise click.ClickException("Draft must be approved before recall begins.")

    try:
        if mode == "first-pass":
            questions = generate_first_pass_questions(subject_root)
            click.echo(f"first-pass questions={len(questions)}")
        else:
            questions = select_next_questions_weak(subject_root, n=3)
            click.echo(f"adaptive questions={len(questions)}")
    except ApprovalRequiredError as exc:
        raise click.ClickException(str(exc)) from exc
```

---

## Step 9.3: Verify CLI integration tests pass

Run:

```bash
uv run pytest tests/test_cli_integration.py -v
```

Expected output:

```text
tests/test_cli_integration.py::test_full_workflow_via_cli PASSED
tests/test_cli_integration.py::test_cli_recall_fails_without_approval_before_generation PASSED
```

---

## Step 9.4: Commit

```bash
git add src/study/cli.py tests/test_cli_integration.py
git commit -m "feat: integrate CLI workflow with approval checked recall modes"
```

Expected output:

```text
[study-harness-impl ...] feat: integrate CLI workflow with approval checked recall modes
```

---

# Task 10: E2E subject lifecycle + deep recoverability proof

## Files

- Create: `/home/user01/project/study/my-study/tests/test_e2e.py`

## Required proof

The E2E test must verify:

```python
assert loaded.phase == "recall_adaptive"
assert loaded.approval_status is True
assert loaded.draft_version_hash
assert loaded.next_recalls_cursor > 0
assert len(loaded.weak_points) >= 1
```

It must also verify `session_logs/` content, not only directory existence.

---

## Step 10.1: Write failing E2E recoverability test

```python
# tests/test_e2e.py
import json
from pathlib import Path

from study.approval import approve_draft
from study.drafting import generate_draft
from study.intake import add_sources
from study.models import RecallQuestion, SourceReference
from study.recall import (
    generate_first_pass_questions,
    record_session,
    score_answer,
    select_next_questions_weak,
    update_weakness_profile,
)
from study.storage import load_progress
from study.subjects import create_subject


def test_full_subject_lifecycle_and_deep_recoverability(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    subject_root = create_subject(workspace_root, "thermo", "Thermodynamics")

    add_sources(
        subject_root,
        [
            SourceReference(kind="native", content="Energy and entropy foundations."),
            SourceReference(
                kind="web_search",
                content="Heat engines and state functions.",
                metadata={"url": "https://example.com/thermo"},
            ),
            SourceReference(
                kind="user_file",
                content="Uploaded thermodynamics notes.",
                metadata={"filename": "thermo_notes.md"},
            ),
            SourceReference(kind="pasted_text", content="Pasted study material."),
        ],
    )

    generate_draft(subject_root, "Thermodynamics")
    approve_draft(subject_root)

    first_pass_questions = generate_first_pass_questions(subject_root)
    assert len(first_pass_questions) >= 3

    draft_content = (subject_root / "learning_draft.md").read_text(encoding="utf-8")
    weak_question = first_pass_questions[0]
    weak_answer = "This is a shallow incorrect explanation."
    weak_score = min(
        0.2,
        score_answer(weak_question, weak_answer, draft_content=draft_content),
    )

    record_session(
        subject_root,
        [weak_question],
        [weak_answer],
        [weak_score],
    )
    update_weakness_profile(subject_root)
    adaptive_questions = select_next_questions_weak(subject_root, n=3)

    assert len(adaptive_questions) >= 1

    assert (subject_root / "learning_draft.md").is_file()
    assert (subject_root / "recall_history.jsonl").is_file()
    assert (subject_root / "source_reference_data").is_dir()
    assert (subject_root / "session_logs").is_dir()
    assert (subject_root / "progress_state.json").is_file()

    log_text = (subject_root / "session_logs" / "operations.log").read_text(
        encoding="utf-8"
    )
    assert "created subject_id=thermo" in log_text
    assert "added source kind=native" in log_text
    assert "generated learning_draft.md" in log_text
    assert "approved draft" in log_text
    assert "generated first-pass recall questions" in log_text
    assert "recorded recall session" in log_text
    assert "updated weakness profile" in log_text
    assert "selected adaptive weak questions" in log_text

    history_lines = (subject_root / "recall_history.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    assert len(history_lines) >= 1

    history_payload = json.loads(history_lines[-1])
    assert history_payload["questions"][0]["topic"] == weak_question.topic
    assert history_payload["answers"] == [weak_answer]
    assert history_payload["scores"] == [weak_score]

    loaded = load_progress(subject_root)

    assert loaded.phase == "recall_adaptive"
    assert loaded.approval_status is True
    assert loaded.draft_version_hash
    assert loaded.next_recalls_cursor > 0
    assert len(loaded.weak_points) >= 1
    assert any(
        weak_point.topic == weak_question.topic and weak_point.weakness_score < 0.5
        for weak_point in loaded.weak_points
    )
```

Run:

```bash
uv run pytest tests/test_e2e.py -v
```

Expected output before final hardening:

```text
FAILED tests/test_e2e.py::test_full_subject_lifecycle_and_deep_recoverability
AssertionError: expected full lifecycle state and session log evidence
```

---

## Step 10.2: Implement missing E2E hardening

Patch only what is necessary to satisfy the lifecycle proof:

```python
# Implementation constraints for final hardening:
# - Do not change the locked subject_root API convention.
# - Do not weaken approval checks.
# - Do not remove weak-point evidence from progress_state.json.
# - Do not make the session log assertion pass by writing empty placeholder text.
```

Expected implementation checks:

```python
# src/study/recall.py
# Ensure record_session logs:
log_operation(subject_root, "recorded recall session ...")

# Ensure update_weakness_profile logs:
log_operation(subject_root, "updated weakness profile ...")

# Ensure select_next_questions_weak logs:
log_operation(subject_root, "selected adaptive weak questions ...")

# Ensure state remains:
state.phase = "recall_adaptive"
state.approval_status = True
state.draft_version_hash is not None
state.next_recalls_cursor > 0
len(state.weak_points) >= 1
```

---

## Step 10.3: Run full E2E and suite

Run:

```bash
uv run pytest tests/test_e2e.py -v
```

Expected output:

```text
tests/test_e2e.py::test_full_subject_lifecycle_and_deep_recoverability PASSED
```

Run full suite:

```bash
uv run pytest -v
```

Expected output:

```text
tests/test_models.py::test_models_validate_required_fields PASSED
tests/test_subjects.py::test_create_subject_creates_locked_subject_root PASSED
tests/test_subjects.py::test_subject_root_for_uses_plural_subjects PASSED
tests/test_subjects.py::test_list_and_delete_subjects PASSED
tests/test_storage.py::test_save_load_progress_state PASSED
tests/test_storage.py::test_recall_history_append_and_read PASSED
tests/test_storage.py::test_session_log_contains_operational_content PASSED
tests/test_intake.py::test_add_sources_persists_all_seed_source_kinds PASSED
tests/test_intake.py::test_intake_logs_operational_content PASSED
tests/test_drafting.py::test_generate_draft_produces_dense_concept_book PASSED
tests/test_drafting.py::test_draft_uses_bibliography_only_references PASSED
tests/test_drafting.py::test_draft_updates_progress_hash_and_logs PASSED
tests/test_approval_gate.py::test_approve_sets_status_and_phase PASSED
tests/test_approval_gate.py::test_approve_logs_operational_content PASSED
tests/test_approval_gate.py::test_recall_rejects_unapproved_before_question_generation PASSED
tests/test_recall_sequential.py::test_first_pass_questions_are_sequential_and_open_ended PASSED
tests/test_recall_sequential.py::test_first_pass_requires_approval_before_parsing_draft PASSED
tests/test_recall_sequential.py::test_first_pass_updates_cursor_phase_and_logs PASSED
tests/test_recall_scoring.py::test_score_answer_returns_normalized_score PASSED
tests/test_recall_scoring.py::test_decompose_misconceptions_returns_concrete_explanation PASSED
tests/test_recall_scoring.py::test_record_session_persists_weak_points_and_history_evidence PASSED
tests/test_recall_scoring.py::test_record_session_requires_approval PASSED
tests/test_adaptive_recall.py::test_select_next_questions_weak_requires_approval_before_selection PASSED
tests/test_adaptive_recall.py::test_weak_topics_selected_with_recall_history_evidence PASSED
tests/test_cli_integration.py::test_full_workflow_via_cli PASSED
tests/test_cli_integration.py::test_cli_recall_fails_without_approval_before_generation PASSED
tests/test_e2e.py::test_full_subject_lifecycle_and_deep_recoverability PASSED
```

---

## Step 10.4: Run quality checks

Run:

```bash
uv run pytest -v
git diff --check
```

Expected output:

```text
... PASSED
```

```text
# git diff --check prints no output
```

---

## Step 10.5: Commit

```bash
git add src tests pyproject.toml
git commit -m "test: prove full subject lifecycle and recoverability"
```

Expected output:

```text
[study-harness-impl ...] test: prove full subject lifecycle and recoverability
```

---

# Final Self-Review Checklist

| Requirement | Locked in Task | Verification |
|---|---:|---|
| Subject storage under `<workspace_root>/subjects/<subject_id>/` | 1 | `test_create_subject_creates_locked_subject_root` |
| One subject = one whole study topic | 1–10 | `ProgressState.subject_id`, `ProgressState.topic` |
| Sources: native, web_search, user_file, pasted_text | 3, 10 | `test_add_sources_persists_all_seed_source_kinds` |
| Dense bottom-up concept-book draft | 4 | `test_generate_draft_produces_dense_concept_book` |
| Bibliography-only references | 4 | `test_draft_uses_bibliography_only_references` |
| Approval gate before recall | 5, 6, 8, 9 | `test_recall_rejects_unapproved_before_question_generation` |
| First recall pass sequential | 6 | `test_first_pass_questions_are_sequential_and_open_ended` |
| Structured open-ended prompts, not MC-first | 6 | Prompt format assertions |
| Scoring and misconception decomposition | 7 | `test_score_answer_returns_normalized_score`, `test_decompose_misconceptions_returns_concrete_explanation` |
| Weak-point persistence with concrete evidence | 7, 8 | `len(weak_points) >= 1`, `weakness_score < 0.5`, recall history evidence |
| Adaptive retest prioritizes weak points randomly | 8 | `test_weak_topics_selected_with_recall_history_evidence` |
| Adaptive recall approval check | 8 | `test_select_next_questions_weak_requires_approval_before_selection` |
| CLI recall checks approval before generation | 9 | `test_cli_recall_fails_without_approval_before_generation` |
| Required artifacts exist | 10 | E2E artifact assertions |
| `session_logs/` content verified | 2, 3, 4, 5, 6, 7, 8, 10 | E2E log content assertions |
| Deep recoverability proof | 10 | phase, approval, hash, cursor, weak points |

---

# Explicit Reset Fixes Applied

## Fix 1: Subject-root API convention locked

All subject-data operations use:

```python
subject_root: Path
```

or:

```python
workspace_root: Path, subject_id: str
```

The ambiguous bare data-root API is not allowed.

## Fix 2: ApprovalRequiredError enforced across recall functions

Approval checks exist in:

```python
generate_first_pass_questions(subject_root)
record_session(subject_root, questions, answers, scores)
update_weakness_profile(subject_root)
select_next_questions_weak(subject_root, n)
```

CLI recall also checks approval before generation.

## Fix 3: Weak-point tests assert concrete evidence

Task 7 requires:

```python
assert len(weak_points) >= 1
assert any(wp.weakness_score < 0.5 for wp in weak_points)
```

Task 8 additionally proves weak topics from `recall_history.jsonl` appear in selected adaptive questions.

## Fix 4: Recovery test is deep, not shallow

Task 10 requires:

```python
assert loaded.phase == "recall_adaptive"
assert loaded.approval_status is True
assert loaded.draft_version_hash
assert loaded.next_recalls_cursor > 0
assert len(loaded.weak_points) >= 1
```

## Fix 5: `session_logs/` content is verified

Task 10 checks actual operational log entries, not merely directory existence.

---

# Plan Contract Lock

```yaml
approved_authority: seed_504ad2a94198
revision: v3
target_artifact: /home/user01/project/study/my-study/.worktree/study-harness/PLAN.md
governed_downstream_entry: superpowers:subagent-driven-development
controlling_objective: Build full CLI study harness with subject lifecycle, dense draft generation, approval-gated recall, scoring, weak-point tracking, and adaptive retest.
subject_storage_contract: <workspace_root>/subjects/<subject_id>/
api_contract: Every subject-data function receives subject_root or (workspace_root, subject_id); ambiguous bare data-root parameters are prohibited.
approval_contract: Recall question generation, recall session recording, weakness update, adaptive selection, and CLI recall must check approval_status before recall work proceeds.
weakness_contract: Weak points must be persisted in ProgressState.weak_points and evidenced by recall_history.jsonl.
recoverability_contract: Another agent must recover phase, approval_status, draft_version_hash, next_recalls_cursor, weak_points, source manifest, recall history, and session logs from disk.
explicit_prohibitions:
  - no web UI
  - no standalone app
  - no beginner tutorial mode
  - no multiple-choice-first recall mode
  - no calendar-based spaced repetition scheduler
  - no ambiguous bare root parameter for subject-data functions
  - no recall generation before approval
  - no shallow recoverability test
ordering_acceptance_constraints:
  - tasks 0 through 10 execute in order
  - each task starts with failing tests
  - each task ends with passing tests and commit
  - final acceptance requires full pytest suite pass and git diff --check clean
invalidation_rule: Any change to storage layout, approval boundary, recall-first question style, or recoverability requirements requires re-supervision.
branch_entry_constraint: study-harness-impl branch/worktree only.
```

---

# Execution Handoff

This v3 plan replaces PLAN.md v2 entirely. Implement it as a fresh artifact line, not as a patch-shaped retry of the failed plan. The required downstream implementation entry is:

```text
superpowers:subagent-driven-development
```

Use task-by-task TDD, preserve the subject-root API convention, and do not weaken approval-gate or recoverability tests.
````
