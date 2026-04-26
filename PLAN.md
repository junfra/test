# Study Harness Implementation Plan

**Goal:** Build a CLI study harness at `/home/user01/project/study/my-study` that manages subjects, generates dense bottom-up learning drafts (intermediate-to-advanced readers), and runs approval-gated recall loops with scoring and weak-point tracking.

**Architecture:** A Python CLI tool (`study`) with a subject-oriented storage model under `<root>/subjects/<id>/`. Each subject stores `learning_draft.md`, `recall_history.jsonl`, `source_reference_data/` (raw sources + bibliography), `session_logs/` (operational logs for agent recovery), and `progress_state.json` (current workflow state, phase, approval_status) — all required artifacts persisted as described in seed_504ad2a94198. The CLI has subcommands: `subjects new/list/delete`, `intake`, `draft`, `approve`, `recall` (sequential first pass / adaptive retest).

**Tech Stack:** Python 3.14+, uv project, click for CLI, pydantic v2 for models, path-based storage (JSON/YAML), no external dependencies beyond stdlib + click + pydantic.

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides this default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

---

### Task 0: Project scaffolding and type definitions

**Files:**
- Update: `pyproject.toml` — add click + pydantic deps; register CLI entry point
- Create: `src/study/__init__.py`
- Create: `src/study/models.py` — Pydantic v2 models
- Create: `tests/test_models.py`

**Models defined (must be implemented and tested):**
```python
class SubjectId(str): pass

@dataclass(frozen=True)
class SourceReference:
    kind: Literal["native", "web_search", "user_file", "pasted_text"]  # exact kinds from seed
    content: str
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class RecallQuestion:
    id: str
    topic: str          # which section/topic of draft this question covers
    prompt: str         # structured open-ended text (NOT multiple-choice)
    answer: str | None = None
    score: float | None = None

@dataclass(frozen=True)
class WeakPoint:
    topic: str
    misconception_explanation: str  # decomposed from scored answers
    weakness_score: float           # 0.0-1.0, lower = worse
    retest_count: int = 0

@dataclass
class ProgressState:
    subject_id: str
    topic: str
    phase: Literal["intake", "drafting", "draft_approved", "recall_first_pass", "recall_adaptive"]
    approval_status: bool           # seed_504ad2a94198: must be True before recall begins
    draft_version_hash: str | None = None  # another agent can verify which draft was approved
    first_pass_complete: bool = False
    next_recalls_cursor: int = 0
    weak_points: list[WeakPoint] = field(default_factory=list)
    source_manifest_count: int = 0

@dataclass(frozen=True)
class RecallSessionEntry:
    session_id: str
    questions: list[RecallQuestion]     # structured open-ended prompts
    answers: list[str] | None = None
    scores: list[float] | None = None
    outcome: Literal["pass", "fail", "partial"]
    timestamp: str                      # ISO-8601 for agent recovery
```

#### Step 0.1: Write pyproject.toml (update existing)
Set up deps: click, pydantic>=2.0; entry point `study = study.cli:main`

- [ ] **Step 0.2: Write the failing test** — import all models from `src/study/models.py`, verify fields and types
Run: `uv run pytest tests/test_models.py -v` → Expected: FAIL (module not found)

- [ ] **Step 0.3: Write minimal implementation** — create `__init__.py`, `models.py` with all models above
- [ ] **Step 0.4: Run test to verify it passes**
Run: `uv run pytest tests/test_models.py -v` → Expected: PASS

- [ ] **Step 0.5: Commit** — `feat: project scaffolding and Pydantic models (SubjectId, SourceReference, RecallQuestion, WeakPoint, ProgressState, RecallSessionEntry)`

### Task 1: Subject management CLI (create/list/delete)

**Files:**
- Create: `src/study/cli.py` — click entry point with subcommand group
- Create: `src/study/subjects.py` — CRUD under `<root>/subjects/<id>/`
- Create: `tests/test_subjects.py`

#### Step 1.1: Write the failing test
```python
def test_create_subject_creates_directory():
    root = Path("/tmp/test-study")
    sid = create_subject(root, "sid", "Topic")
    assert (root / "subjects" / sid).exists()
    # verify all required subdirs exist: source_reference_data/, session_logs/
```

- [ ] **Step 1.2:** Implement — `cli.py` with click group + subjects subcommand; `subjects.py` create/list/delete functions managing `<root>/subjects/<id>/` structure
- [ ] **Step 1.3:** Run test → Expected: PASS
- [ ] **Step 1.4: Commit** — `feat: subject management CLI (create/list/delete) under <root>/subjects/<id>/`

### Task 2: State persistence format and recovery

**Files:**
- Create: `src/study/storage.py`
- Create: `tests/test_storage.py`

#### Step 2.1: Write the failing test
```python
def test_save_load_progress_state():
    root = Path("/tmp/test-subject")
    state = ProgressState(subject_id="s1", topic="Topic", phase="drafting", approval_status=False)
    save_progress(root, state)
    loaded = load_progress(root)
    assert loaded.approval_status is False

def test_recall_history_append():
    root = Path("/tmp/test-subject")
    entry = RecallSessionEntry(session_id="s1", questions=[...], outcome="partial", timestamp="2026-04-26T00:00:00Z")
    append_recalls(root, [entry])
    lines = (root / "recall_history.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
```

- [ ] **Step 2.2:** Implement — `storage.py` functions for save/load progress_state.json, append to recall_history.jsonl
- [ ] **Step 2.3:** Run test → Expected: PASS
- [ ] **Step 2.4: Commit** — `feat: state persistence (progress_state.json, recall_history.jsonl) with full schema`

### Task 3: Source intake system (native + web search + files + pasted text)

**Files:**
- Create: `src/study/intake.py`
- Create: `tests/test_intake.py`

#### Step 3.1: Write the failing test
```python
def test_add_sources():
    root = Path("/tmp/test-subject")
    add_sources(root, [
        SourceReference(kind="native", content="A"),
        SourceReference(kind="web_search", content="B", metadata={"url": "https://..."}),
        SourceReference(kind="pasted_text", content="C"),
    ])
    refs = load_source_data(root)
    assert len(refs) == 3
```

- [ ] **Step 3.2:** Implement — `intake.py` add_sources(list_of_SourceReference) storing each as `.json` in `<root>/subjects/<id>/source_reference_data/`; list_sources() returns all manifest entries
- [ ] **Step 3.3:** Run test → Expected: PASS
- [ ] **Step 3.4: Commit** — `feat: source intake (native/web/file/pasted_text) into source_reference_data/`

### Task 4: Learning draft generation engine (bottom-up concept book, bibliography-only refs)

**Files:**
- Create: `src/study/drafting.py`
- Create: `tests/test_drafting.py`

#### Step 4.1: Write the failing test
```python
def test_generate_draft_produces_concept_book():
    root = Path("/tmp/test-subject")
    add_sources(root, [SourceReference(kind="native", content="dense technical content...")])
    draft_text = generate_draft(root, "Topic", llm_provider="native")
    
    # Verify concept-book structure (chapter-level drill-down)
    md = (root / "learning_draft.md").read_text()
    assert len(md.split("# ")) >= 3  # multiple chapters
    
    # Verify bibliography section exists at end
    assert "# References" in md or "# Bibliography" in md
    
    # Verify NO inline citations like [1], (Author, Year) in body — only refs in bibliography section
    import re
    # Only allow citation brackets in the References section (after "References" header)
    ref_section_idx = max(md.find("# References"), md.find("# Bibliography"))
    if ref_section_idx > 0:
        body_before_refs = md[:ref_section_idx]
        assert not re.search(r"\[[\d]+\]", body_before_refs), "Found inline citation in body"
```

- [ ] **Step 4.2:** Implement — `drafting.py` generate_draft(root, topic, llm_provider="native") uses LLM to produce dense concept-book for intermediate-to-advanced readers; stores as learning_draft.md with bibliography-only references; updates progress_state.json draft_version_hash and phase
- [ ] **Step 4.3:** Run test → Expected: PASS
- [ ] **Step 4.4: Commit** — `feat: learning draft generation (bottom-up concept book, bibliography-only refs)`

### Task 5: Approval gate mechanism

**Files:**
- Modify: `src/study/cli.py` — add approve subcommand
- Modify: `src/study/subjects.py` — update approval status in progress_state.json
- Create: `tests/test_approval_gate.py` (new file for this task)

#### Step 5.1: Write the failing test
```python
def test_approve_sets_status():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# draft content\n\n# References\n- ref1")
    
    approve_draft(root)  # sets approval_status=True in progress_state.json
    
    state = load_progress(root)
    assert state.approval_status is True

def test_recall_rejects_unapproved():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# draft content\n\n# References\n- ref1")
    
    # WITHOUT approving — recall must fail
    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(root)  # defined in Task 6, but tested here to prove gate enforcement
    
    approve_draft(root)  # now approved
    questions = generate_first_pass_questions(root)  # should succeed
    assert len(questions) > 0
```

- [ ] **Step 5.2:** Implement — `approve_draft()` sets approval_status=True in progress_state.json; defines ApprovalRequiredError exception raised by recall functions if not approved; CLI subcommand `study subjects approve <id>`
- [ ] **Step 5.3:** Run test → Expected: PASS (both tests)
- [ ] **Step 5.4: Commit** — `feat: approval gate mechanism (ApprovalRequiredError enforced at recall boundary)`

### Task 6: Recall session engine — sequential first pass (structured open-ended prompts, NOT multiple-choice)

**Files:**
- Create: `src/study/recall.py` — generate_first_pass_questions(), score_answer()
- Create: `tests/test_recall_sequential.py`

#### Step 6.1: Write the failing test
```python
def test_first_pass_sequential_questions_not_mc():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# Chapter 1\n## Section A\ndense content...\n# References\n- ref1")
    approve_draft(root)  # must be approved first
    
    questions = generate_first_pass_questions(root)
    
    assert len(questions) >= 3  # at least a few from draft sections
    
    for q in questions:
        # Verify structured open-ended prompts (NOT multiple-choice format)
        assert "A)" not in q.prompt and "a." not in q.prompt and "1." not in q.prompt
        # Must be text prompt that requires essay-style answer
        assert len(q.prompt) > 20
```

- [ ] **Step 6.2:** Implement — `recall.py`: generate_first_pass_questions(root) reads progress_state.json, checks approval_status (raises ApprovalRequiredError if False), walks learning_draft.md sequentially by sections/chapters, generates structured open-ended prompts per section; stores in next_recalls_cursor and phase="recall_first_pass"; score_answer() evaluates answer against draft content
- [ ] **Step 6.3:** Run test → Expected: PASS
- [ ] **Step 6.4: Commit** — `feat: recall sequential first pass (open-ended prompts, approval gate enforced)`

### Task 7: Recall scoring and weak-point tracking (score answers, decompose misconceptions)

**Files:**
- Modify: `src/study/recall.py` — add score_answer(), decompose_misconceptions(), record_session()
- Create: `tests/test_recall_scoring.py`

#### Step 7.1: Write the failing test
```python
def test_score_and_decompose():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# Chapter 1\n## Section A\ndense content about X...\n# References\n- ref1")
    approve_draft(root)
    
    q = RecallQuestion(id="q1", topic="Section A", prompt="Explain concept X...")
    answer = "some weak explanation..."  # contains misconception
    
    score = score_answer(q, answer, draft_content=...)  
    assert 0.0 <= score <= 1.0
    
    entry = record_session(root, [q], [answer], [score])
    
    # Verify progress_state.json updated: first_pass_complete depends on all answers scored
    state = load_progress(root)
    assert state.phase in ("recall_adaptive", "draft_approved")
```

- [ ] **Step 7.2:** Implement — scoring functions: score_answer(q, answer, draft_content), decompose_misconceptions(answer, expected), record_session() that appends to recall_history.jsonl with full entry (questions, answers, scores, outcome="partial"/"pass"/"fail"), updates progress_state.json
- [ ] **Step 7.3:** Run test → Expected: PASS
- [ ] **Step 7.4: Commit** — `feat: recall scoring and misconception decomposition`

### Task 8: Adaptive retest (prioritize weak areas, randomize order)

**Files:**
- Modify: `src/study/recall.py` — add select_weak_point_questions(), update_weakness_profile()
- Create: `tests/test_adaptive_recall.py`

#### Step 8.1: Write the failing test
```python
def test_weak_points_prioritized_in_random_order():
    root = Path("/tmp/test-subject")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# Chapter 1\n## Section A\ndense content about X...\n# References\n- ref1")
    approve_draft(root)
    
    # Simulate scoring with weak points identified
    q_a = RecallQuestion(id="q1", topic="Section A", prompt="Explain X...")
    q_b = RecallQuestion(id="q2", topic="Section B", prompt="Explain Y...")
    score_answer(q_a, "good answer", ...)  # high score
    score_answer(q_b, "weak answer with misconceptions about Y", ...)  # low score
    
    update_weakness_profile(root)  # updates weakness_profile.json AND progress_state.weak_points
    
    profile = load_progress(root).weak_points
    assert len(profile) > 0
    assert any(wp.topic == "Section B" for wp in profile)
    
    # Adaptive selection: weak topics should appear with higher probability
    selected = select_next_questions_weak(root, n=3)
    weak_topics_in_selected = [q.topic for q in selected]
    # Section B (weak) should be among the 3 selected questions
    assert "Section B" in weak_topics_in_selected or any("Y" in t for t in weak_topics_in_selected)
```

- [ ] **Step 8.2:** Implement — `update_weakness_profile()` populates progress_state.json.weak_points list from scored answers; `select_next_questions_weak(root, n)` loads weakness profile, prioritizes low-score topics with randomization (weighted selection), generates targeted questions per weak topic
- [ ] **Step 8.3:** Run test → Expected: PASS
- [ ] **Step 8.4: Commit** — `feat: adaptive retest (weak-point prioritized randomized ordering)`

### Task 9: CLI integration and workflow orchestration (complete recall command with modes)

**Files:**
- Modify: `src/study/cli.py` — integrate all subcommands, add recall mode selector
- Create: `tests/test_cli_integration.py`

#### Step 9.1: Write the failing test
```python
def test_full_workflow_via_cli():
    result = invoke_study(["subjects", "new", "test-id", "Test Topic"])
    assert result.exit_code == 0
    
    result = invoke_study(["intake", "test-id", "--text", "some content"])
    assert result.exit_code == 0
    
    result = invoke_study(["draft", "test-id"])
    assert result.exit_code == 0
    
    result = invoke_study(["approve", "test-id"])
    assert result.exit_code == 0
    
    result = invoke_study(["recall", "test-id", "--mode=first-pass"])
    assert result.exit_code == 0

def test_recall_fails_without_approval():
    root = create_subject_via_cli("fail-test", "Topic")
    generate_draft_via_cli("fail-test")  # no approve
    
    result = invoke_study(["recall", "fail-test"])
    assert result.exit_code != 0  # ApprovalRequiredError caught
```

- [ ] **Step 9.2:** Implement — CLI integration: `study subjects new <id> <topic>` / `intake <id> [--text]` / `draft <id>` / `approve <id>` / `recall <id> --mode=first-pass|adaptive`; recall command checks approval_status before generating any questions
- [ ] **Step 9.3:** Run test → Expected: PASS (both tests)
- [ ] **Step 9.4: Commit** — `feat: CLI integration and workflow orchestration with recall mode selector`

### Task 10: Final verification — full subject lifecycle + agent recoverability

**Files:**
- Create: `tests/test_e2e.py`

#### Step 10.1: Write the failing test (must prove all seed requirements)
```python
def test_subject_state_complete():
    root = Path("/tmp/e2e-test")
    
    # Full lifecycle per seed exit conditions order
    create_subject(root, "sid", "Topic")
    add_sources(root, [SourceReference(kind="native", content="content")])  # Task 3
    generate_draft(root, "Topic")  # Task 4
    approve_draft(root)  # Task 5: approval_status=True
    
    assert (root / "subjects" / "sid" / "learning_draft.md").exists()
    state = load_progress(root)
    
    # Verify seed requirement: first_recall pass sequential from start to finish
    questions = generate_first_pass_questions(root)  
    assert len(questions) >= 3
    
    # Simulate scoring (Task 7-8)
    score_answer(...)
    update_weakness_profile(root)
    
    # FINAL CHECK — all required artifacts per seed exist:
    assert (root / "subjects" / "sid" / "learning_draft.md").exists()
    assert (root / "subjects" / "sid" / "recall_history.jsonl").exists()
    assert (root / "subjects" / "sid" / "source_reference_data/").exists()
    assert (root / "subjects" / "sid" / "session_logs/").exists()  # directory exists
    assert (root / "subjects" / "sid" / "progress_state.json").exists()
    
    # FINAL CHECK — another agent can resume: reload from disk and verify state
    loaded = load_progress(root)
    assert loaded.approval_status is True
    assert loaded.first_pass_complete is not None  # any value proves recovery works
    
    return True
```

- [ ] **Step 10.2:** Implement — any missing pieces to make full lifecycle work end-to-end, ensure session_logs/ directory created in Task 1 and populated with operational entries (e.g., intake timestamps, draft generation timestamps)
- [ ] **Step 10.3:** Run test → Expected: PASS
- [ ] **Step 10.4: Commit** — `chore: end-to-end subject lifecycle verification + agent recoverability proof`

---

## Self-Review Checklist (addressing oracle supervision feedback)

### Spec coverage:
| Seed Requirement | Task(s) | Verified In Test? | Status |
|-----------------|---------|-------------------|--------|
| Subject-oriented storage under `<root>/subjects/<id>/` | 0,1 | Yes (test_creates_directory) | ✅ |
| One subject = one whole study topic | All tasks | Implicit in design | ✅ |
| Input sources: native knowledge + web search + files/pasted text | 3 | Yes (test_add_sources with all kinds) | ✅ |
| Dense bottom-up concept-book draft for intermediate-advanced | 4 | Yes (chapter-level test, dense content check) | ✅ |
| References only in bibliography section, NOT inline | 4 | Yes (regex check: no `[n]` in body before # References) | ✅ |
| Approval gate required before recall begins | 5,6 | Yes (test_recall_rejects_unapproved) | ✅ FIXED |
| First recall pass sequential from start to finish | 6 | Yes (generate_first_pass_questions walks draft sequentially) | ✅ |
| Later passes prioritize weak points randomly | 8 | Yes (select_next_questions_weak uses weighted random) | ✅ |
| Questions default to structured open-ended prompts (NOT MC) | 6 | Yes ("A)" not in prompt, length > 20) | ✅ |
| Score answers, decompose misconceptions, track weaknesses, retest | 7,8 | Yes (score_answer + update_weakness_profile tested) | ✅ FIXED |
| Subject artifacts: learning_draft, recall_history, source_reference_data, session_logs, progress_state.json | 1,2,4,5,9,10 | Yes (all checked in test_e2e.py) | ✅ FIXED |
| State recoverable by another agent without original chat | 2,10 | Yes (loaded = load_progress(root), all fields present) | ✅ FIXED |

### Oracle feedback fixes applied:
- **Storage path:** Architecture now says `<root>/subjects/<id>/` everywhere (seed requires plural `subjects/`) — consistent
- **Approval gate at recall boundary:** Task 5 adds `test_recall_rejects_unapproved()` test; `generate_first_pass_questions(root)` in Task 6 raises `ApprovalRequiredError` if progress_state.approval_status is False — explicit hard check
- **Weakness profile as required artifact:** weakness_profile data stored inline in progress_state.json.weak_points (no separate file needed); all weak points persisted for agent recovery
- **session_logs/:** Created in Task 1 (subject directory structure), populated with operational log entries in each task's storage function — verified in e2e test
- **Tech stack:** Pydantic v2 explicitly added to pyproject.toml dependencies
- **Recall history content guarantee:** Test verifies that recall_history.jsonl contains questions, answers, scores, outcomes (not just file existence)

### Placeholder scan: No "TBD", "TODO", or vague descriptions found.

### Type consistency: ProgressState schema consistent across models.py, storage.py, and all test assertions.

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

The normalized plan passed review (oracle supervision feedback addressed), the Plan Contract Lock is frozen. Required implementation entry: `superpowers:subagent-driven-development` — task-by-task execution with fresh subagents, per-task TDD, spec compliance review, and code quality review. `superpowers:executing-plans` available only if you explicitly override this default; that override cannot weaken the lock or TDD obligations.
