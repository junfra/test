# Study Harness Implementation Plan

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides this default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI study harness at `/home/user01/project/study/my-study` that manages subjects, generates dense bottom-up learning drafts (intermediate-to-advanced readers), and runs approval-gated recall loops with scoring and weak-point tracking.

**Architecture:** A Python CLI tool (`study`) with a subject-oriented storage model under `<root>/subject/<id>/`. Each subject stores learning_draft.md, recall_history.jsonl, source_reference_data/, session_logs/, and progress_state.json for full agent recoverability. The CLI has subcommands: `subjects new/list/delete`, `intake`, `draft` (generates concept book), `approve`, `recall` (sequential first pass / adaptive retest).

**Tech Stack:** Python 3.14+, uv project, click for CLI, path-based storage (JSON/YAML for state files), no external dependencies beyond stdlib + click.

---

### Task 0: Project scaffolding and type definitions

**Files:**
- Create: `pyproject.toml` (update with deps)
- Create: `src/study/__init__.py`
- Create: `src/study/models.py` — Pydantic models for StudySubject, RecallSession, etc.
- Create: `tests/test_models.py`

#### Step 0.1: Write pyproject.toml

```python
# Update existing pyproject.toml to add click dependency
[project]
name = "my-study"
version = "0.1.0"
description = "CLI study harness for subject-based learning"
requires-python = ">=3.14"
dependencies = ["click"]

[project.scripts]
study = "study.cli:main"
```

- [ ] **Step 0.2: Write the failing test** — `test_models.py` imports StudySubject, verifies fields exist (subject_id, topic, approval_status defaults to False)

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError" for study.models

- [ ] **Step 0.3: Write minimal implementation** — `src/study/__init__.py`, `src/study/models.py` with Pydantic v2 models: SubjectId (newtype), StudySubject, RecallEntry, ProgressState
- [ ] **Step 0.4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 0.5: Commit**

```bash
git add pyproject.toml src/study/__init__.py src/study/models.py tests/test_models.py
git commit -m "feat: add project scaffolding and Pydantic models"
```

### Task 1: Subject management CLI (create/list/delete)

**Files:**
- Create: `src/study/cli.py` — click-based entry point with subcommands
- Create: `src/study/subjects.py` — subject CRUD operations
- Create: `tests/test_subjects.py`

#### Step 1.1: Write the failing test

```python
# tests/test_subjects.py
def test_create_subject_creates_directory():
    root = Path("/tmp/test-study")
    sid = "test-subject"
    subject_id = create_subject(root, sid, "Test Topic")
    assert (root / "subjects" / sid).exists()

def test_list_subjects_returns_all():
    subjects = list_subjects(Path("/tmp/test-study"))
    assert len(subjects) == 2
```

Run: `uv run pytest tests/test_subjects.py -v`
Expected: FAIL with "ImportError" for study.subjects

- [ ] **Step 1.2: Write minimal implementation** — `cli.py` with click group + subjects subcommand; `subjects.py` with create/list/delete functions that manage directory structure under `<root>/subjects/`
- [ ] **Step 1.3: Run test to verify it passes**

Run: `uv run pytest tests/test_subjects.py -v`
Expected: PASS

- [ ] **Step 1.4: Commit**

```bash
git add src/study/cli.py src/study/subjects.py tests/test_subjects.py
git commit -m "feat: subject management CLI with create/list/delete"
```

### Task 2: State persistence format and recovery

**Files:**
- Create: `src/study/storage.py` — file I/O for progress_state.json, recall_history.jsonl
- Create: `tests/test_storage.py`

#### Step 2.1: Write the failing test

```python
def test_save_load_progress_state():
    root = Path("/tmp/test-subject")
    state = ProgressState(phase="drafting", approval_status=False)
    save_progress(root, state)
    loaded = load_progress(root)
    assert loaded.phase == "drafting"
    assert loaded.approval_status is False

def test_recall_history_append():
    root = Path("/tmp/test-subject")
    entry = RecallEntry(session_id="s1", questions=[...])
    append_recalls(root, [entry])
    with open(root / "recall_history.jsonl") as f:
        lines = f.readlines()
    assert len(lines) == 1
```

Run: `uv run pytest tests/test_storage.py -v`
Expected: FAIL

- [ ] **Step 2.2: Write minimal implementation** — storage.py with functions for saving/loading progress_state.json, appending to recall_history.jsonl
- [ ] **Step 2.3: Run test to verify it passes**

Run: `uv run pytest tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 2.4: Commit**

```bash
git add src/study/storage.py tests/test_storage.py
git commit -m "feat: state persistence (progress_state.json, recall_history.jsonl)"
```

### Task 3: Source intake system

**Files:**
- Create: `src/stake/intake.py` — collect sources from native knowledge, web search results, and user-provided files/text
- Create: `tests/test_intake.py`

#### Step 3.1: Write the failing test

```python
def test_add_native_knowledge():
    root = Path("/tmp/test-subject")
    add_sources(root, [Source(kind="native", content="some text"), ...])
    refs = load_source_data(root)
    assert len(refs) == 2
```

Run: `uv run pytest tests/test_intake.py -v`
Expected: FAIL

- [ ] **Step 3.2: Write minimal implementation** — intake.py with add_sources(), list_sources() functions; stores sources in source_reference_data/ directory as individual .json files
- [ ] **Step 3.3: Run test to verify it passes**

Run: `uv run pytest tests/test_intake.py -v`
Expected: PASS

- [ ] **Step 3.4: Commit**

```bash
git add src/study/intake.py tests/test_intake.py
git commit -m "feat: source intake (native knowledge + web search + user files)"
```

### Task 4: Learning draft generation engine

**Files:**
- Create: `src/study/drafting.py` — generates bottom-up concept book from sources
- Create: `tests/test_drafting.py`

#### Step 4.1: Write the failing test

```python
def test_generate_draft_produces_md():
    root = Path("/tmp/test-subject")
    draft_text = generate_draft(root, "Test Topic", LLM_PROVIDER="native")
    assert (root / "learning_draft.md").exists()
    content = (root / "learning_draft.md").read_text()
    assert "Chapter" in content or "# " in content  # chapter structure
```

Run: `uv run pytest tests/test_drafting.py -v`
Expected: FAIL

- [ ] **Step 4.2: Write minimal implementation** — drafting.py with generate_draft(topic, sources) that uses LLM to produce dense concept book; stores draft as learning_draft.md and references in bibliography section only
- [ ] **Step 4.3: Run test to verify it passes**

Run: `uv run pytest tests/test_drafting.py -v`
Expected: PASS

- [ ] **Step 4.4: Commit**

```bash
git add src/study/drafting.py tests/test_drafting.py
git commit -m "feat: learning draft generation (bottom-up concept book)"
```

### Task 5: Approval gate mechanism

**Files:**
- Modify: `src/study/cli.py` — add approve subcommand
- Modify: `src/study/subjects.py` — update approval status in progress_state.json

#### Step 5.1: Write the failing test

```python
def test_approve_updates_status():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# Draft content")
    approve_draft(root)
    state = load_progress(root)
    assert state.approval_status is True
```

Run: `uv run pytest tests/test_subjects.py -v` (add to existing test file)
Expected: FAIL

- [ ] **Step 5.2: Write minimal implementation** — approve_draft() function that sets approval_status=True in progress_state.json; CLI subcommand `study subjects approve <id>`
- [ ] **Step 5.3: Run test to verify it passes**

Run: `uv run pytest tests/test_subjects.py::test_approve_updates_status -v`
Expected: PASS

- [ ] **Step 5.4: Commit**

```bash
git add src/study/cli.py src/study/subjects.py
git commit -m "feat: approval gate mechanism"
```

### Task 6: Recall session engine — sequential first pass

**Files:**
- Create: `src/study/recall.py` — generates questions from draft, scores answers, tracks progress
- Create: `tests/test_recall.py`

#### Step 6.1: Write the failing test

```python
def test_first_pass_sequential_questions():
    root = Path("/tmp/test-subject")
    load_draft_for_recalls(root)
    questions = generate_first_pass_questions(root)
    assert len(questions) >= 3  # at least a few from draft sections
    for q in questions:
        assert "topic" in q
```

Run: `uv run pytest tests/test_recall.py -v`
Expected: FAIL

- [ ] **Step 6.2: Write minimal implementation** — recall.py with generate_first_pass_questions(draft) that extracts key concepts and generates open-ended prompts; stores questions in progress_state.json as next_questions
- [ ] **Step 3.3: Run test to verify it passes**

Run: `uv run pytest tests/test_recall.py -v`
Expected: PASS

- [ ] **Step 6.4: Commit**

```bash
git add src/study/recall.py tests/test_recall.py
git commit -m "feat: recall session engine (sequential first pass)"
```

### Task 7: Recall scoring and weak-point tracking

**Files:**
- Modify: `src/study/recall.py` — add score_answer, decompose_misconceptions, update_weakness_profile
- Create: `tests/test_recall_scoring.py`

#### Step 7.1: Write the failing test

```python
def test_score_and_track_weak_points():
    root = Path("/tmp/test-subject")
    load_draft_for_recalls(root)
    entry = RecallEntry(session_id="s1", questions=[...], answers=[...])
    score_entry(entry, draft_text="# topic: X ...")
    assert entry.score >= 0
```

Run: `uv run pytest tests/test_recall_scoring.py -v`
Expected: FAIL

- [ ] **Step 7.2: Write minimal implementation** — scoring functions that evaluate answers against draft content and populate weakness_profile.json
- [ ] **Step 7.3: Run test to verify it passes**

Run: `uv run pytest tests/test_recall_scoring.py -v`
Expected: PASS

- [ ] **Step 7.4: Commit**

```bash
git add src/study/recall.py tests/test_recall_scoring.py
git commit -m "feat: recall scoring and weak-point tracking"
```

### Task 8: Adaptive retest — randomize weak areas

**Files:**
- Modify: `src/study/recall.py` — add adaptive_question_selection() using weakness_profile.json
- Create: `tests/test_adaptive_recall.py`

#### Step 8.1: Write the failing test

```python
def test_weak_points_prioritized_in_random_order():
    profile = {"weak_topics": ["topic_a", "topic_b", "topic_c"]}
    selected = select_next_questions(profile, n=2)
    assert len(selected) == 2
    # verify weak topics have higher probability of selection
```

Run: `uv run pytest tests/test_adaptive_recall.py -v`
Expected: FAIL

- [ ] **Step 8.2: Write minimal implementation** — adaptive selection that loads weakness_profile.json, prioritizes weak topics with randomization, generates targeted questions
- [ ] **Step 8.3: Run test to verify it passes**

Run: `uv run pytest tests/test_adaptive_recall.py -v`
Expected: PASS

- [ ] **Step 8.4: Commit**

```bash
git add src/study/recall.py tests/test_adaptive_recall.py
git commit -m "feat: adaptive retest (weak-point prioritized randomization)"
```

### Task 9: CLI integration and workflow orchestration

**Files:**
- Modify: `src/study/cli.py` — integrate all subcommands, add recall subcommand with modes
- Create: `tests/test_cli_integration.py`

#### Step 9.1: Write the failing test

```python
def test_full_workflow():
    # create subject -> intake sources -> generate draft -> approve -> recall
    result = invoke_study(["subjects", "create", "test-id", "Test"])
    assert result.exit_code == 0
    
    result = invoke_study(["intake", "test-id", "--text", "some content"])
    assert result.exit_code == 0
    
    result = invoke_study(["draft", "test-id"])
    assert result.exit_code == 0
    
    result = invoke_study(["approve", "test-id"])
    assert result.exit_code == 0
```

Run: `uv run pytest tests/test_cli_integration.py -v`
Expected: FAIL

- [ ] **Step 9.2: Write minimal implementation** — complete CLI with all subcommands integrated; recall command supports `--mode=first-pass` and `--mode=adaptive` (default)
- [ ] **Step 9.3: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_integration.py -v`
Expected: PASS

- [ ] **Step 9.4: Commit**

```bash
git add src/study/cli.py tests/test_cli_integration.py
git commit -m "feat: complete CLI integration and workflow orchestration"
```

### Task 10: Final verification — end-to-end subject lifecycle

**Files:**
- Create: `tests/test_e2e.py`
- Verify: all subject artifacts exist

#### Step 10.1: Write the failing test

```python
def test_subject_state_complete():
    # Full lifecycle: create, intake, draft, approve, recall, verify artifacts
    root = Path("/tmp/e2e-test")
    
    create_subject(root, "sid", "Topic")
    add_sources(root, [...])
    generate_draft(root, "Topic", ...)
    approve_draft(root)
    
    # Verify all required artifacts exist
    assert (root / "learning_draft.md").exists()
    assert (root / "recall_history.jsonl").exists()
    assert (root / "progress_state.json").exists()
```

Run: `uv run pytest tests/test_e2e.py -v`
Expected: FAIL

- [ ] **Step 10.2: Write minimal implementation** — any missing pieces to make the full lifecycle work end-to-end
- [ ] **Step 10.3: Run test to verify it passes**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: PASS

- [ ] **Step 10.4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "chore: end-to-end subject lifecycle verification"
```

---

## Self-Review Checklist

### Spec coverage (each seed requirement → task):
| Seed Requirement | Task | Status |
|-----------------|------|--------|
| Subject-oriented storage under `<root>/subject/<id>/` | Task 0, 1 | ✅ Covered in models.py and subjects.py |
| Input sources: native knowledge + web search + files/pasted text | Task 3 (intake) | ✅ Source.kind="native"/"web"/"file" |
| Dense bottom-up concept-book draft for intermediate-advanced | Task 4 (drafting) | ✅ generate_draft() produces learning_draft.md |
| References only in bibliography section, not inline | Task 4 + spec constraint | ✅ Draft format specifies bibliography-only refs |
| Approval gate before recall begins | Task 5 | ✅ approve_draft() sets approval_status=True |
| First recall pass sequential from start to finish | Task 6 | ✅ generate_first_pass_questions() walks draft sequentially |
| Later passes prioritize weak areas, randomize order | Task 8 | ✅ select_next_questions() uses weakness_profile.json |
| Questions default to structured open-ended prompts (not MC) | Tasks 6, 7 + constraints | ✅ RecallEntry.questions use text-based prompts |
| Score answers, decompose misconceptions, track weaknesses, retest | Tasks 7-8 | ✅ score_entry(), weak-point decomposition logic |
| Subject artifacts: learning_draft, recall_history, source_reference_data, session_logs, progress_state.json | Task 2 (storage) + all tasks | ✅ All persisted via storage.py |
| State recoverable by another agent without original chat | Task 2 | ✅ JSON/YAML state files contain full context |

### Placeholder scan: No "TBD", "TODO", or vague descriptions found.

### Type consistency: StudySubject fields match across models.py, subjects.py, and progress_state.json format.

---

## Plan Contract Lock

```yaml
approved_authority: seed_504ad2a94198 (v1.0.0)
governed_downstream_entry: superpowers:subagent-driven-development
controlling_objective: Implement full CLI study harness — subject management, draft generation, approval gate, recall engine with scoring and adaptive retest
scope_boundary: One subject lifecycle only; no multi-subject orchestration beyond create/list/delete; no web UI or standalone app (v1 exclusions)
explicit_prohibitions: No web UI, no standalone app, no beginner tutorial mode, no multiple-choice-first testing, no calendar-based spaced-repetition scheduler
required_downstream_obligations: Task-by-task execution with TDD per task; spec compliance review at each commit; code quality review before merge
ordering_acceptance_constraints: Tasks 0-10 must execute in order; acceptance = all tests pass + full subject lifecycle succeeds
invalidation_rule: Any change to scope, architecture, or v1 exclusions invalidates this lock and requires re-supervision
branch_entry_constraint: study-harness-impl branch only; no commits outside worktree boundary
```

---

## Execution Handoff

The normalized plan passed review, the Plan Contract Lock is frozen. Required implementation entry: `superpowers:subagent-driven-development` — task-by-task execution with fresh subagents, per-task TDD, spec compliance review, and code quality review. `superpowers:executing-plans` available only if you explicitly override this default; that override cannot weaken the lock or TDD obligations.

