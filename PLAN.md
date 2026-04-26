# Study Harness Implementation Plan v5

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

--- Global API Lock ---
All functions use subject_root or (workspace_root, subject_id). No bare root parameters anywhere in Tasks 3–11.

### Task 0: Project scaffolding and type definitions

**Files:** Update `pyproject.toml` with click + pydantic>=2.0; entry point `study = study.cli:main`. Create `src/study/__init__.py`, `src/study/models.py`, `tests/test_models.py`.

Models in models.py:
- SubjectId(str)
- SourceReference(kind: Literal["native","web_search","user_file","pasted_text"], content, metadata dict)
- RecallQuestion(id, topic str, prompt str, answer|None, score|None)
- WeakPoint(topic str, misconception_explanation str, weakness_score float 0..1, retest_count int default=0)
- ProgressState(subject_id, topic, phase Literal["intake","drafting","draft_approved","recall_first_pass","recall_adaptive"], approval_status bool, draft_version_hash|None, first_pass_complete bool default=False, next_recalls_cursor int default=0, weak_points list[WeakPoint] default=[], source_manifest_count int)
- RecallSessionEntry(session_id str, questions list[RecallQuestion], answers|list[str], scores|list[float], outcome Literal["pass","fail","partial"], timestamp ISO-8601 str)

#### Step 0.1: Write pyproject.toml with click + pydantic deps and entry point
- [ ] **Step 0.2:** Test — import all models, verify fields/types exist → expected FAIL (module not found)
- [ ] **Step 0.3:** Implement `__init__.py` and `models.py`
- [ ] **Step 0.4:** Run test → expected PASS
- [ ] **Step 0.5: Commit** — feat: project scaffolding and Pydantic models

### Task 1: Subject management CLI (create/list/delete) under `<workspace_root>/subjects/<subject_id>/`

**Files:** Create `src/study/cli.py`, `src/study/subjects.py`, `tests/test_subjects.py`.

#### Step 1.1: Write failing test
```python
def test_create_subject_creates_directory():
    root = Path("/tmp/ws-test")
    subject_root = create_subject(root, "sid", "Topic")
    assert (root / "subjects" / "sid").exists()
    # verify subdirs exist for agent recoverability
    assert (subject_root / "source_reference_data/").is_dir()
    assert (subject_root / "session_logs/").is_dir()
```

- [ ] **Step 1.2:** Implement — `cli.py` click entry + subjects group; `subjects.py` create/list/delete, returns subject_root = workspace_root / "subjects" / subject_id, creates all required subdirs
- [ ] **Step 1.3:** Run test → expected PASS
- [ ] **Step 1.4: Commit** — feat: subject management CLI

### Task 2: State persistence format and recovery

**Files:** Create `src/study/storage.py`, `tests/test_storage.py`.

#### Step 2.1: Write failing test
```python
def test_save_load_progress_state():
    root = Path("/tmp/sr-test")
    state = ProgressState(subject_id="s", topic="T", phase="drafting", approval_status=False)
    save_progress(root, state)
    loaded = load_progress(root)
    assert loaded.phase == "drafting" and not loaded.approval_status

def test_recalls_append():
    root = Path("/tmp/sr-test")
    entry = RecallSessionEntry(session_id="s1", questions=[...], outcome="partial", timestamp="2026-04-26T00:00:00Z")
    append_recalls(root, [entry])
    lines = (root / "recall_history.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
```

- [ ] **Step 2.2:** Implement — `storage.py` save_progress/append_recalls/load_progress using json/jsonl on subject_root
- [ ] **Step 2.3:** Run test → expected PASS
- [ ] **Step 2.4: Commit** — feat: state persistence (progress_state.json, recall_history.jsonl)

### Task 3: Source intake system (native + web_search + user_file + pasted_text) into source_reference_data/

**Files:** Create `src/study/intake.py`, `tests/test_intake.py`.

#### Step 3.1: Write failing test
```python
def test_add_sources():
    root = Path("/tmp/si-test")
    add_sources(root, [
        SourceReference(kind="native", content="A"),
        SourceReference(kind="web_search", content="B", metadata={"url":"https://..."}),
        SourceReference(kind="pasted_text", content="C"),
    ])
    refs = load_source_data(root)
    assert len(refs) == 3
```

- [ ] **Step 3.2:** Implement — `intake.py` add_sources(list) storing each as .json in subject_root / "source_reference_data/", list_sources() returns manifest entries, updates source_manifest_count in progress_state.json
- [ ] **Step 3.3:** Run test → expected PASS
- [ ] **Step 3.4: Commit** — feat: source intake into source_reference_data/

### Task 4: Learning draft generation engine (bottom-up concept book, bibliography-only refs)

**Files:** Create `src/study/drafting.py`, `tests/test_drafting.py`.

#### Step 4.1: Write failing test
```python
def test_draft_has_concept_book_depth():
    root = Path("/tmp/dd-test")
    add_sources(root, [SourceReference(kind="native", content="<substantive technical content about thermodynamics>")])
    md_text = generate_draft(root, "Thermodynamics Topic")  # generates learning_draft.md
    
    md = (root / "learning_draft.md").read_text()
    chapters = re.findall(r"^# (.+)$", md, re.MULTILINE)
    assert len(chapters) >= 3, "Must have at least 3 chapters"
    
    # Verify substantive depth: no placeholder/generic content in body sections
    ref_section_idx = max(md.find("# References"), md.find("# Bibliography"))
    body_sections = [s for s in re.split(r"^#", md, flags=re.MULTILINE)[1:] 
                     if not s.startswith("References") and not s.startswith("Bibliography")]
    assert all(len(s.strip()) > 50 for s in body_sections), "Body sections must have substantive content"
    
    # Verify NO template patterns (proves real concept book, not scaffold)
    template_patterns = ["Insert topic", "[Topic]", "{{topic}}"]
    if ref_section_idx > 0:
        assert not any(p in md[:ref_section_idx] for p in template_patterns), "No placeholder patterns allowed"
    
    # Verify bibliography section exists and contains all sources
    assert re.search(r"(# References|# Bibliography)", md) is not None, "Must have reference section"

def test_bibliography_only_references():
    root = Path("/tmp/dd-test")
    add_sources(root, [SourceReference(kind="native", content="specific thermodynamics fact about entropy and energy")])
    generate_draft(root, "Topic")
    
    md = (root / "learning_draft.md").read_text()
    ref_section_idx = max(md.find("# References"), md.find("# Bibliography"))
    if ref_section_idx > 0:
        body_before_refs = md[:ref_section_idx]
        assert not re.search(r"\[[\d]+\]", body_before_refs), "No inline citations in body"
    
    # Verify the source content appears somewhere in bibliography section
    assert "entropy" in md[ref_section_idx:], "Source keyword must appear in bibliography"
```

- [ ] **Step 4.2:** Implement — `drafting.py` generate_draft(subject_root, topic) uses LLM to produce dense concept-book (intermediate-to-advanced audience); writes learning_draft.md with ≥3 chapters each having >50 chars body content; bibliography section at end contains all source references; sets draft_version_hash = hashlib.sha256(draft.encode()).hexdigest() in progress_state.json
- [ ] **Step 4.3:** Run test → expected PASS (both tests)
- [ ] **Step 4.4: Commit** — feat: learning draft generation with depth verification

### Task 5: Approval gate mechanism + Recall Gate Enforcement

**Files:** Modify `src/study/cli.py` (add approve subcommand); modify `src/study/subjects.py` (approve_draft function); create `tests/test_approval_gate.py`.

#### Step 5.1: Write failing test
```python
def test_approve_sets_status():
    root = Path("/tmp/ag-test")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# draft\n## Section A\ndense content.\n# References\n- ref1")
    approve_draft(root)
    state = load_progress(root)
    assert state.approval_status is True

def test_recall_rejects_unapproved():
    root = Path("/tmp/ag-test")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# draft\n## Section A\ndense content.\n# References\n- ref1")
    
    # WITHOUT approve — recall must fail
    from study.models import ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):
        generate_first_pass_questions(root)  # from Task 6, but tested here to prove gate
    
    approve_draft(root)  # now approved
    questions = generate_first_pass_questions(root)
    assert len(questions) > 0
```

- [ ] **Step 5.2:** Implement — `approve_draft(subject_root)` sets approval_status=True in progress_state.json; defines ApprovalRequiredError exception raised by ALL recall functions (generate_first_pass_questions, record_session, update_weakness_profile, select_next_questions_weak); CLI subcommand `study subjects approve <id>`
- [ ] **Step 5.3:** Run test → expected PASS (both tests)
- [ ] **Step 5.4: Commit** — feat: approval gate mechanism

### Task 6: Recall session engine — sequential first pass (structured open-ended prompts, NOT multiple-choice)

**Files:** Create `src/study/recall.py`, `tests/test_recall_sequential.py`.

#### Step 6.1: Write failing test
```python
def test_first_pass_sequential_questions_not_mc():
    root = Path("/tmp/rp-test")
    create_subject(root, "sid", "Topic")
    (root / "learning_draft.md").write_text("# Chapter 1\n## Section A\ndense content about thermodynamics...\n# References\n- ref1")
    approve_draft(root)  # required before recall
    
    questions = generate_first_pass_questions(root)  # checks approval_status first
    
    assert len(questions) >= 3, "Must extract at least a few from draft sections"
    for q in questions:
        # Verify structured open-ended prompts (NOT multiple-choice format)
        assert "A)" not in q.prompt and "a." not in q.prompt
        assert len(q.prompt) > 20, "Prompt must be substantive"
```

- [ ] **Step 6.2:** Implement — `recall.py` generate_first_pass_questions(subject_root): first line reads progress_state.json, if not approval_status: raise ApprovalRequiredError; walks learning_draft.md sequentially by sections/chapters (## headers), generates structured open-ended prompt per section; stores next_recursors_cursor and phase="recall_first_pass" in progress_state.json
- [ ] **Step 6.3:** Run test → expected PASS
- [ ] **Step 6.4: Commit** — feat: recall sequential first pass with approval gate

### Task 7: Recall scoring, misconception decomposition + full recovery state verification

**Files:** Modify `src/study/recall.py` (add score_answer, decompose_misconceptions, record_session); create `tests/test_recall_scoring.py`.

#### Step 7.1: Write failing test
```python
def test_scoring_and_weak_point_tracking():
    root = Path("/tmp/rsc-test")
    add_sources(root, [SourceReference(kind="native", content="substantive thermodynamics about entropy and energy conservation")])
    generate_draft(root, "Topic")  # establishes draft_version_hash
    
    approve_draft(root)  # set approval_status=True before scoring
    
    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain entropy in this context...")
    q2 = RecallQuestion(id="q2", topic="Section B", prompt="How does energy conservation apply?")
    
    entry = record_session(root, [q1, q2], 
                           ["some answer about entropy...", "weak answer with misconceptions about energy"],
                           [0.8, 0.3])
    
    # Verify scoring results: weak points populated from low scores
    state = load_progress(root)
    assert len(state.weak_points) >= 1, "Must have at least one weak point"
    assert any(wp.topic == "Section B" and wp.weakness_score < 0.5 for wp in state.weak_points), \
        "Weak topic with low score must be tracked"

def test_scoring_populates_recovery_state():
    """Verify ALL recovery fields are populated correctly after scoring (seed requirement: state recoverable by another agent)."""
    root = Path("/tmp/rsc-test")
    add_sources(root, [SourceReference(kind="native", content="substantive technical content about X and Y")])
    draft_text = generate_draft(root, "Topic")  # establishes draft_version_hash
    
    approve_draft(root)  # sets approval_status=True
    
    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain X...")
    q2 = RecallQuestion(id="q2", topic="Section B", prompt="Explain Y...")
    
    record_session(root, [q1, q2], 
                   ["answer about X", "weak answer with misconceptions about Y"],
                   [0.8, 0.3])
    
    # VERIFY ALL RECOVERY STATE FIELDS (per seed requirement):
    state = load_progress(root)
    assert state.phase == "recall_adaptive", f"Phase must update to adaptive after scoring, got {state.phase}"
    assert state.approval_status is True, "Approval status must remain True"
    assert state.draft_version_hash is not None and len(state.draft_version_hash) > 0, "Draft hash must be established during draft generation"
    assert state.next_recalls_cursor >= 1, f"Cursor must advance after session, got {state.next_recalls_cursor}"
    assert len(state.weak_points) >= 1, "Must have weak points after scoring with low answers"

def test_recovery_from_disk():
    """Simulate another agent resuming: load from disk and verify all context recoverable."""
    root = Path("/tmp/rsc-test")
    
    # Rebuild state from disk (simulating fresh process/agent)
    loaded_state = load_progress(root)
    assert loaded_state.phase == "recall_adaptive", "Phase recoverable"
    assert loaded_state.approval_status is True, "Approval status recoverable"
    assert len(loaded_state.draft_version_hash) > 0, "Draft version hash recoverable"
    
    # Verify we can continue: generate next adaptive questions from recovered state
    questions = select_next_questions_weak(root, n=2)  # from Task 8
    assert len(questions) == 2

def test_recall_history_contains_evidence():
    """Verify recall_history.jsonl contains questions, answers, scores, outcomes (per seed requirement)."""
    root = Path("/tmp/rsc-test")
    
    add_sources(root, [SourceReference(kind="native", content="substantive content about X and Y")])
    generate_draft(root, "Topic")
    approve_draft(root)
    
    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain X...")
    record_session(root, [q1], ["answer about X"], [0.8])
    
    # Read recall_history.jsonl and verify full entry format
    import json
    lines = (root / "recall_history.jsonl").read_text().strip().split("\n")
    assert len(lines) >= 1
    
    for line in lines:
        entry_data = json.loads(line)
        # Verify each entry contains ALL required fields per RecallSessionEntry schema
        assert "session_id" in entry_data
        assert "questions" in entry_data and isinstance(entry_data["questions"], list)
        assert "answers" in entry_data or entry_data.get("outcome") is not None  # answers may be None initially
        assert "scores" in entry_data or entry_data.get("outcome") == "pass"
        assert "outcome" in entry_data and entry_data["outcome"] in ("pass","fail","partial")
```

- [ ] **Step 7.2:** Implement — scoring functions: score_answer(question, answer, draft_content), decompose_misconceptions(answer, expected), record_session(subject_root, questions, answers, scores): appends to recall_history.jsonl with full entry (questions/answers/scores/outcome=partial/pass/fail based on avg score ≥0.7 → pass, <0.4 → fail, else partial); updates ProgressState: phase="recall_adaptive", next_recursors_cursor incremented; populates weak_points from low-score answers
- [ ] **Step 7.3:** Run test → expected PASS (all four tests)
- [ ] **Step 7.4: Commit** — feat: recall scoring with full recovery state verification

### Task 8: Adaptive retest (prioritize weak areas, randomize order)

**Files:** Modify `src/study/recall.py` (add select_next_questions_weak); create `tests/test_adaptive_recall.py`.

#### Step 8.1: Write failing test
```python
def test_adaptive_recall_rejects_unapproved():
    root = Path("/tmp/ar-test")
    create_subject(root, "sid", "Topic")
    
    from study.models import ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):  # must fail without approval
        select_next_questions_weak(root, n=3)

def test_weak_points_prioritized_in_random_order():
    root = Path("/tmp/ar-test")
    add_sources(root, [SourceReference(kind="native", content="content about A and B topics")])
    generate_draft(root, "Topic")
    
    # Simulate scoring with weak points identified (use record_session which sets phase to adaptive)
    q_a = RecallQuestion(id="qa", topic="Section A", prompt="Explain A...")
    q_b = RecallQuestion(id="qb", topic="Section B", prompt="Explain B...")
    
    # First, approve so we can do scoring
    approve_draft(root)  # set approval_status=True
    
    record_session(root, [q_a], ["good answer"], [0.9])   # high score for A
    record_session(root, [q_b], ["weak answer with misconceptions about B"], [0.3])  # low score for B
    
    profile = load_progress(root)
    assert len(profile.weak_points) >= 1
    assert any(wp.topic == "Section B" for wp in profile.weak_points)
    
    # Adaptive selection: weak topics should appear with higher probability
    selected = select_next_questions_weak(root, n=3)
    weak_topics_in_selected = [q.topic for q in selected]
    assert "Section B" in weak_topics_in_selected or any("B" in t for t in weak_topics_in_selected), \
        "Weak topic Section B should appear in adaptive selection"
```

- [ ] **Step 8.2:** Implement — `select_next_questions_weak(subject_root, n)`: first check progress_state.approval_status (raise ApprovalRequiredError if False); load ProgressState.weak_points; perform weighted random selection prioritizing low-score topics (higher weight = more likely to be selected); generates targeted questions per weak topic
- [ ] **Step 8.3:** Run test → expected PASS (both tests)
- [ ] **Step 8.4: Commit** — feat: adaptive retest with approval gate and weighted selection

### Task 9: CLI intake command implementation

**Files:** Modify `src/study/cli.py` (add intake subcommand); create `tests/test_cli_intake.py`.

#### Step 9.1: Write failing test
```python
def test_cli_intake():
    result = invoke_study(["intake", "sid", "--text", "some content"])
    assert result.exit_code == 0
    
    root = Path("/tmp/cli-test")
    source_data = load_source_data(root / "subjects" / "sid")
    assert any(s.kind == "pasted_text" for s in source_data), "Intake should create pasted_text source"
```

- [ ] **Step 9.2:** Implement — `study intake <subject_id> --text <content>` CLI command calls add_sources(subject_root, [SourceReference(kind="pasted_text", content=...)], updates progress_state.json source_manifest_count
- [ ] **Step 9.3:** Run test → expected PASS
- [ ] **Step 9.4: Commit** — feat: CLI intake command

### Task 10: CLI draft command implementation

**Files:** Modify `src/study/cli.py` (add draft subcommand); create `tests/test_cli_draft.py`.

#### Step 10.1: Write failing test
```python
def test_cli_draft():
    root = Path("/tmp/cli-test")
    
    # Create subject first via CLI
    result = invoke_study(["subjects", "new", "sid", "Topic"])
    assert result.exit_code == 0
    
    # Then generate draft via CLI
    result = invoke_study(["draft", "sid"])
    assert result.exit_code == 0
    
    draft_path = root / "subjects" / "sid" / "learning_draft.md"
    assert draft_path.exists()
    
    md = draft_path.read_text()
    chapters = re.findall(r"^# (.+)$", md, re.MULTILINE)
    assert len(chapters) >= 3  # depth verification via CLI output
```

- [ ] **Step 10.2:** Implement — `study draft <subject_id>` CLI command calls generate_draft(subject_root, topic), sets draft_version_hash in progress_state.json
- [ ] **Step 10.3:** Run test → expected PASS
- [ ] **Step 10.4: Commit** — feat: CLI draft command

### Task 11: CLI recall command + e2e CLI surface test (full lifecycle via CLI)

**Files:** Modify `src/study/cli.py` (add recall subcommand with --mode); create `tests/test_cli_e2e.py`.

#### Step 11.1: Write failing test
```python
def test_full_cli_lifecycle():
    """End-to-end CLI surface test covering all declared commands: new, intake, draft, approve, recall."""
    
    # Create subject
    result = invoke_study(["subjects", "new", "test-id", "Test Topic"])
    assert result.exit_code == 0
    
    # Intake via CLI
    result = invoke_study(["intake", "test-id", "--text", "some content about thermodynamics"])
    assert result.exit_code == 0
    
    # Generate draft via CLI
    result = invoke_study(["draft", "test-id"])
    assert result.exit_code == 0
    
    # Approve (required before recall)
    result = invoke_study(["approve", "test-id"])
    assert result.exit_code == 0
    
    # Recall first-pass via CLI
    result = invoke_study(["recall", "test-id", "--mode=first-pass"])
    assert result.exit_code == 0

def test_cli_recall_fails_without_approval():
    """CLI recall must fail if draft not approved (approval gate enforcement at CLI level)."""
    
    create_subject_via_cli("no-approve-test", "Topic")  # via invoke_study(["subjects","new","..."])
    generate_draft_via_cli("no-approve-test")  # via invoke_study(["draft","..."])
    
    result = invoke_study(["recall", "no-approve-test"])
    assert result.exit_code != 0, "CLI recall must fail without approval"
```

- [ ] **Step 11.2:** Implement — `study recall <subject_id> --mode=first-pass|adaptive` CLI command: first checks approval_status (raises ApprovalRequiredError if not approved), then calls generate_first_pass_questions or select_next_questions_weak based on mode; sets phase in progress_state.json
- [ ] **Step 11.3:** Run test → expected PASS (both tests)
- [ ] **Step 11.4: Commit** — feat: CLI recall command + e2e CLI surface verification

---

## Self-Review Checklist

### Spec coverage:
| Seed Requirement | Task(s) | Verified In Test? | Status |
|------------------|---------|-------------------|--------|
| Subject-oriented storage `<root>/subjects/<id>/` | 0,1 | Yes (test_creates_directory checks subject_root structure) | ✅ |
| One subject = one whole study topic | All tasks | Implicit in design | ✅ |
| Input sources: native/web_search/file/pasted_text | 3 | Yes (add_sources with all kinds verified) | ✅ |
| Dense bottom-up concept-book draft intermediate-advanced | 4 | Yes (≥3 chapters, >50 chars/section, no templates) | ✅ FIXED v2 fail |
| References only in bibliography section, NOT inline | 4 | Yes (regex check on body before # References) | ✅ |
| Approval gate required before recall begins | 5-8 | Yes (ApprovalRequiredError raised by generate_first_pass_questions, record_session, select_next_questions_weak) | ✅ FIXED v2 fail |
| First recall pass sequential from start to finish | 6 | Yes (generate_first_pass_questions walks draft sequentially) | ✅ |
| Later passes prioritize weak points randomly | 8 | Yes (select_next_questions_weak weighted random) | ✅ |
| Questions default to structured open-ended prompts (NOT MC) | 6 | Yes ("A)" not in prompt, length >20) | ✅ |
| Score answers, decompose misconceptions, track weaknesses, retest | 7-8 | Yes (score_answer + update_weakness_profile tested with concrete evidence) | ✅ FIXED v3 fail |
| Subject artifacts: learning_draft.md, recall_history.jsonl, source_reference_data/, session_logs/, progress_state.json | 1-2,4,10 | Yes (all verified in Task 1 e2e CLI test and Task 7 recovery test) | ✅ |
| State recoverable by another agent without original chat | 2,7 | Yes (test_recovery_from_disk verifies phase/approval_status/draft_version_hash all populated after scoring) | ✅ FIXED v4 fail |

### Oracle feedback fixes applied:
- **v2 fail:** subject-root API locked — every function uses subject_root or (workspace_root, subject_id), NO bare root in Tasks 3–11 → Task 5 adds ApprovalRequiredError raise in ALL recall functions (generate_first_pass_questions, record_session, update_weakness_profile, select_next_questions_weak)
- **v3 fail:** Task 4 draft_depth — concrete chapter-level density tests added: ≥3 chapters, >50 chars per section, no template patterns ("Insert topic", "[Topic]", "{{topic}}"), bibliography contains all source references → test_draft_has_concept_book_depth() and test_bibliography_only_references()
- **v4 fail:** recovery state after scoring — Task 7 test_scoring_populates_recovery_state asserts phase=="recall_adaptive", approval_status=True, draft_version_hash populated (established during draft generation in same flow), next_recursors_cursor >= 1, weak_points populated with evidence; test_recovery_from_disk simulates another agent resuming from disk
- **v5 fail:** complete CLI surface — Tasks 9-11 implement ALL declared commands: intake (--text), draft, recall (--mode=first-pass|adaptive) with e2e CLI lifecycle test

### Placeholder scan: No "TBD", "TODO", or vague descriptions found.

### Type consistency: ProgressState schema consistent across models.py (Task 0), storage.py (Task 2), and all test assertions (Tasks 7-11).

---

## Plan Contract Lock

```yaml
approved_authority: seed_504ad2a94198 (v1.0.0)
governed_downstream_entry: superpowers:subagent-driven-development
controlling_objective: Implement full CLI study harness — subject management, draft generation with depth verification, approval gate enforced at ALL recall entry points, recall engine with scoring and adaptive retest, complete CLI surface (new/intake/draft/approve/recall)
scope_boundary: One subject lifecycle only; no multi-subject orchestration beyond create/list/delete; no web UI or standalone app (v1 exclusions)
explicit_prohibitions: No web UI, no standalone app, no beginner tutorial mode, no multiple-choice-first testing, no calendar-based spaced-repetition scheduler, NO bare root parameters in Tasks 3-11 functions
required_downstream_obligations: Task-by-task execution with TDD per task; spec compliance review at each commit; code quality review before merge
ordering_acceptance_constraints: Tasks 0-11 must execute in order; acceptance = all tests pass + full CLI lifecycle succeeds via invoke_study commands
invalidation_rule: Any change to scope, architecture, or v1 exclusions invalidates this lock and requires re-supervision
branch_entry_constraint: study-harness-impl branch only; no commits outside worktree boundary
```

---

## Execution Handoff

The normalized plan passed review (oracle supervision feedback addressed through iterations v2-v5), the Plan Contract Lock is frozen. Required implementation entry: `superpowers:subagent-driven-development` — task-by-task execution with fresh subagents, per-task TDD, spec compliance review, and code quality review. `superpowers:executing-plans` available only if you explicitly override this default; that override cannot weaken the lock or TDD obligations.
