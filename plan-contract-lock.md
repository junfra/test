````markdown
# Recall System v1 — Implementation Plan

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides; the override cannot weaken frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MD-based Codex skill harness system ("recall-system") that routes natural-language user requests into learning, study, and recall sub-skills and generates deep Korean learning materials, supports material-grounded study Q&A, and runs structured recall sessions with weak-point review and spaced repetition.
**Architecture:** Main router `SKILL.md` routes natural-language intent to three sub-skill contracts: learn, study, recall. Shared file-based infrastructure enforces safe paths, atomic writes, JSON recovery, execution locking, and queue/session persistence under `/home/user01/project/recall-system/subject/<topic_slug>/`.
**Tech Stack:** Markdown files, no external dependencies beyond Oracle Browser for web search. Python helper scripts optional.

---

### 1. seed_scope_lock

**Exact goal as quoted from Seed:**

> Build an MD-based Codex skill harness system ("recall-system") that routes
> natural-language user requests into learning, study, and recall sub-skills and:
> (1) generates deep, high-density learning materials (30,000+ characters of pure text)
> with a fixed 7-chapter structure (탄생배경 → 정의 → 하위개념 → 관계도 → 사례 → 오해 → 회상키포인트),
> recall questions per chapter, and inline retrieval points, using LLM knowledge + web search
> (Oracle Browser default, built-in web search option) with user-provided materials as optional input,
> (2) provides an interactive study session where the user can ask questions, request
> explanations, and verify understanding (MVP v1: simple material-grounded Q&A;
> richer explanation, analogy, and verification are allowed but not required beyond Q&A scope),
> and
> (3) runs structured recall sessions (free recall → analysis → scaffolded questions →
> synthesis check) with 5-level scoring, weak-point tracking, hint → retry → answer+explanation
> feedback loop, review queue persistence, and priority-based spaced repetition to strengthen
> long-term memory through retrieval practice.

**MVP v1 included scope:**

- MD-based Codex skill harness, not a command-line interface.
- Main router skill contract at `/home/user01/project/recall-system/.codex/skills/recall-system/SKILL.md`.
- Learn sub-skill contract at `/home/user01/project/recall-system/.codex/skills/recall-system-learn/SKILL.md`.
- Study sub-skill contract at `/home/user01/project/recall-system/.codex/skills/recall-system-study/SKILL.md`.
- Recall sub-skill contract at `/home/user01/project/recall-system/.codex/skills/recall-system-recall/SKILL.md`.
- Optional Python helper modules for file safety, validation, state persistence, scoring, and queue prioritization.
- Natural-language-only user operation.
- Korean default output.
- First-time learner default explanation posture.
- Learning material generation into `subject/<topic_slug>/index.md`.
- Pure text minimum of 30,000 characters per learning material.
- Fixed 7 chapters:
  1. 탄생배경
  2. 정의
  3. 하위개념
  4. 관계도
  5. 사례
  6. 오해
  7. 회상키포인트
- Recall questions at the end of every chapter.
- Inline retrieval points embedded in each chapter body.
- References only at the end of `index.md`.
- Web search through Oracle Browser by default, or built-in web search as an explicit option.
- Optional user-provided materials as input.
- Source conflict handling by official/primary source priority, recency check, uncertainty marking, and reference recording.
- File-based persistence only.
- Atomic writes through temp-file-plus-rename.
- JSON corruption recovery through `.bak` backup and reinitialization.
- Execution lock through `.lock` file.
- Safe `topic_slug` normalization.
- Path restriction to `/home/user01/project/recall-system/`.
- Study mode where the user reads `index.md` directly and Q&A is performed only on request.
- Recall 4-stage session:
  1. free recall
  2. analysis
  3. scaffolded questions
  4. synthesis check
- 5-level scoring.
- Weak answer feedback loop:
  hint → retry → answer+explanation → register review queue.
- Weak item persistence with fields:
  `concept`, `question`, `failure_reason`, `last_score`, `next_priority`, `last_seen`, `due_hint`.
- Priority-based re-asking using both recency and failure-count weighting.
- Recall session data under `subject/<topic_slug>/`.
- Router intent classes:
  `learn`, `study`, `recall`, `unknown`.
- Router asks once when confidence is low.
- 12 boundary conditions handled by explicit tests.

**Explicit exclusions:**

- No command-line interface as the primary user-facing interface.
- No user-facing commands, flags, arguments, or memorized syntax.
- No external database.
- No dashboard/statistics feature.
- No multi-user feature.
- No sharing/distribution feature.
- No voice interface.
- No file writes outside `/home/user01/project/recall-system/`.
- No references inside chapter bodies except inline retrieval points; full references are listed only at the document end.
- No dashboard-style analytics beyond the persisted review queue and recall session files required by the Seed.
- No scope expansion beyond MVP v1 study Q&A unless all mandatory MVP v1 acceptance criteria already pass.

---

### 2. seed_obligation_ledger

| ID | Source | Obligation Type | Enforced In Task # | Verification Method |
|----|--------|-----------------|--------------------|---------------------|
| C01 | Constraint: MD-based Codex skill harness, not CLI | Architecture / UX | Tasks 1, 2, 19, 20, 21, 22 | Tests assert required `SKILL.md` files exist and contain no CLI-command contract language |
| C02 | Constraint: natural-language-only operation; no CLI commands, flags, arguments, memorized syntax | UX contract | Tasks 2, 19 | Router and sub-skill contract tests reject CLI syntax examples and require natural-language request examples |
| C03 | Constraint: Primary target user is first-time learner | Content contract | Tasks 3, 20, 21, 22 | Skill contract tests assert first-time learner posture appears in router, learn, study, and recall contracts |
| C04 | Constraint: Project root `/home/user01/project/recall-system/` | Path contract | Tasks 4, 5 | Path tests assert root constant and reject any resolved path outside root |
| C05 | Constraint: Learning materials stored under `subject/<topic_slug>/index.md` | Persistence | Tasks 5, 10, 11 | Tests assert learn output path resolves exactly to root `subject/<topic_slug>/index.md` |
| C06 | Constraint: Pure text minimum 30,000 characters | Content validation | Tasks 12, 13 | Validator test fails for 29,999 chars and passes for 30,000+ pure text chars |
| C07 | Constraint: Korean default output language | Content contract | Tasks 3, 12, 20 | Contract and generated-template tests assert Korean default instructions and Korean chapter headings |
| C08 | Constraint: Fixed 7 chapters | Content structure | Tasks 12, 13 | Structure validator asserts exact ordered chapter headings |
| C09 | Constraint: Each chapter ends with recall questions | Content structure | Tasks 12, 13 | Validator asserts recall-question block after every chapter |
| C10 | Constraint: Inline retrieval points embedded in chapter body | Content structure | Tasks 12, 13 | Validator asserts each chapter body contains retrieval point markers before chapter-end questions |
| C11 | Constraint: References listed only at document end | Source hygiene | Tasks 12, 14 | Validator fails if references appear before final references section |
| C12 | Constraint: Web search via Oracle Browser default or built-in web search option | Research workflow | Tasks 14, 20 | Learn contract test asserts Oracle Browser default and built-in web search optional fallback wording |
| C13 | Constraint: Optional user-provided materials accepted | Input workflow | Tasks 14, 20 | Learn contract test asserts optional material ingestion path and source labeling |
| C14 | Constraint: Source conflict resolution official/primary → recency → uncertainty → references | Research workflow | Tasks 14, 15 | Conflict-resolution test asserts priority ordering, uncertainty marker, and final reference recording |
| C15 | Constraint: No external database; file-based persistence only | Persistence | Tasks 6, 7, 8, 16, 17 | Tests assert JSON/MD state files only and no DB dependency/configuration is introduced |
| C16 | Constraint: No dashboard/statistics, no multi-user, no sharing/distribution, no voice interface | Scope exclusion | Tasks 1, 19, 24 | Contract tests assert excluded features are explicitly forbidden |
| C17 | Constraint: Atomic writes temp file + rename | File safety | Tasks 6, 7 | Unit test asserts temp path creation and final rename semantics |
| C18 | Constraint: JSON corruption recovery via `.bak` backup + reinitialize | Recovery | Tasks 8, 9 | Corrupt JSON test asserts `.bak` is written and clean default JSON is reinitialized |
| C19 | Constraint: Execution lock via `.lock` file | Concurrency | Tasks 9, 10 | Lock tests assert second operation fails/defer-routes while lock is held |
| C20 | Constraint: `topic_slug` strips `/`, `..`, whitespace, control characters | Path safety | Tasks 4, 5 | Sanitizer tests assert dangerous chars are removed or rejected |
| C21 | Constraint: All paths restricted to project subtree | Path safety | Tasks 5, 24 | Path-resolution tests assert symlink/path traversal cannot escape root |
| A01 | Acceptance: Learn generates 30k+ material with fixed 7 chapters + recall questions + retrieval points | Learn acceptance | Tasks 11, 12, 13, 20 | End-to-end learn acceptance test validates `index.md` char count and structure |
| A02 | Acceptance: Study mode user reads `index.md` directly; Q&A on request only | Study acceptance | Tasks 18, 21 | Study contract tests assert direct-read flow and no unsolicited Q&A |
| A03 | Acceptance: Recall runs 4-stage session | Recall acceptance | Tasks 23, 24, 25, 26 | Recall pipeline tests assert ordered stages: free recall, analysis, scaffolded questions, synthesis check |
| A04 | Acceptance: Incorrect/weak answers use hint → retry → answer+explanation → review queue | Recall feedback | Tasks 27, 28 | Feedback-loop test asserts exact order and review queue registration |
| A05 | Acceptance: 5-level scoring | Recall scoring | Tasks 26, 27 | Scoring tests assert exactly 5 valid score levels and invalid scores rejected |
| A06 | Acceptance: Weak item fields | Queue schema | Tasks 16, 17, 28 | Queue schema tests assert all required fields exist |
| A07 | Acceptance: Priority-based re-asking using recency + failure-count weighting | Spaced repetition | Tasks 17, 29 | Priority tests assert both stale `last_seen` and failure count increase `next_priority` |
| A08 | Acceptance: Recall session data persists under `subject/<topic_slug>/` | Persistence | Tasks 23, 24 | Session persistence test asserts files under `subject/<topic_slug>/recall_sessions/` |
| A09 | Acceptance: Router classifies intent and asks once if low confidence | Router | Tasks 19, 30 | Router tests assert learn/study/recall/unknown and exactly one clarification on low confidence |
| A10 | Acceptance: All 12 boundary conditions handled | Edge cases | Tasks 31, 32 | Boundary matrix tests assert 12 named cases and matching handlers |
| O01 | Ontology: `subject` | Schema lifecycle | Tasks 5, 10, 16, 23 | Tests assert topic directory owns subject-scoped data |
| O02 | Ontology: `index_md` | Schema lifecycle | Tasks 11, 12, 13 | Tests assert `subject/<topic_slug>/index.md` lifecycle |
| O03 | Ontology: `metadata_json` | Schema lifecycle | Tasks 10, 15 | Tests assert metadata file creation/update/recovery |
| O04 | Ontology: `recall_queue_json` | Schema lifecycle | Tasks 16, 17, 28, 29 | Tests assert review queue persistence and priority updates |
| O05 | Ontology: `recall_sessions_dir` | Schema lifecycle | Tasks 23, 24 | Tests assert session files are created under `recall_sessions/` |
| O06 | Ontology: `study_notes_json` | Schema lifecycle | Tasks 18, 21 | Tests assert Q&A notes persistence only on user request |
| O07 | Ontology: `system_state_json` | Schema lifecycle | Tasks 9, 10, 30 | Tests assert lock/state transitions and recovery |
| O08 | Ontology: `recall_queue_entry` object | Schema lifecycle | Tasks 16, 17, 28, 29 | Tests assert entry fields and priority mutation |
| E01 | Evaluation: completeness weight 1.0 | Acceptance gate | Tasks 33, 34 | Final acceptance matrix test maps every Seed line to a passing verification |
| E02 | Evaluation: depth_and_density weight 1.0 | Acceptance gate | Tasks 12, 13, 34 | 30k+ validator and chapter-density checks |
| E03 | Evaluation: recall_effectiveness weight 0.9 | Acceptance gate | Tasks 23-29, 34 | Recall pipeline, feedback, scoring, spaced repetition tests |
| E04 | Evaluation: natural_language_ux weight 0.8 | Acceptance gate | Tasks 2, 19, 30, 34 | Router and contract tests assert natural-language UX |
| E05 | Evaluation: edge_case_resilience weight 0.7 | Acceptance gate | Tasks 31, 32, 34 | Boundary matrix test suite |
| X01 | Exit: all_criteria_pass | Completion gate | Task 34 | Final acceptance checklist requires every criterion passing |
| X02 | Exit: mvp_v1_scope_met | Completion gate | Task 34 | MVP scope checklist test |
| X03 | Exit: user_declares_done | Completion gate | Task 35 | Final handoff requires user-visible completion packet and explicit user declaration |

---

### 3. seed_to_plan_trace_table

| Seed Acceptance Criterion | Covered By Task ID(s) | Coverage Status | Verification |
|---------------------------|-----------------------|-----------------|--------------|
| Learn generates 30k+ char material with fixed 7 chapters + recall questions + retrieval points | Tasks 11, 12, 13, 20, 34 | Covered | Learn acceptance test validates path, pure text length, chapter order, recall questions, retrieval points |
| Study mode: user reads `index.md` directly; Q&A on request only | Tasks 18, 21, 34 | Covered | Study tests assert direct-read instruction and no unsolicited Q&A/session generation |
| Recall runs 4-stage session: free recall → analysis → scaffolded questions → synthesis check | Tasks 23, 24, 25, 26, 34 | Covered | Recall session state tests assert exact stage order |
| Incorrect/weak answers: hint → retry → answer+explanation → register review queue | Tasks 27, 28, 34 | Covered | Feedback-loop test asserts exact order and queue entry written |
| 5-level scoring | Tasks 26, 27, 34 | Covered | Scoring tests assert five valid levels and invalid score rejection |
| Weak item registration with fields: concept, question, failure_reason, last_score, next_priority, last_seen, due_hint | Tasks 16, 17, 28, 34 | Covered | Queue schema test asserts required fields |
| Priority-based re-asking of weak items using recency + failure-count weighting | Tasks 17, 29, 34 | Covered | Priority tests assert both recency and failure count alter ordering |
| Recall session data persists under `subject/<topic_slug>/` | Tasks 23, 24, 34 | Covered | Filesystem test asserts `subject/<topic_slug>/recall_sessions/<session_id>.json` |
| Router classifies intent learn/study/recall/unknown; asks once if low confidence | Tasks 19, 30, 34 | Covered | Router classifier tests and low-confidence clarification-count test |
| All 12 boundary conditions handled | Tasks 31, 32, 34 | Covered with explicit matrix | Boundary matrix test asserts all 12 cases and handler coverage |

**Coverage gaps:** None for Seed acceptance criteria. The only evidence limitations are listed in `evidence_gaps`.

---

### 4. ordered_tdd_task_plan

#### Phase 1: Shared Infrastructure: repository skeleton, contracts, root safety

- [ ] Task 1: Write failing test that required skill harness files exist.
```python
def test_required_skill_files_exist():
    root = Path("/home/user01/project/recall-system")
    assert (root / ".codex/skills/recall-system/SKILL.md").exists()
    assert (root / ".codex/skills/recall-system-learn/SKILL.md").exists()
    assert (root / ".codex/skills/recall-system-study/SKILL.md").exists()
    assert (root / ".codex/skills/recall-system-recall/SKILL.md").exists()
````

* [ ] Task 1.1: Run the skill-file existence test and verify it fails.

* [ ] Task 1.2: Create minimal `SKILL.md` files for router, learn, study, and recall.

* [ ] Task 1.3: Run the skill-file existence test and verify it passes.

* [ ] Task 1.4: Commit skeleton skill files.

* [ ] Task 2: Write failing test that all skill contracts forbid CLI user operation.

* [ ] Task 2.1: Run the no-CLI contract test and verify it fails.

* [ ] Task 2.2: Add explicit “MD-based Codex skill harness, not CLI” and “natural-language-only” language to all skill contracts.

* [ ] Task 2.3: Run the no-CLI contract test and verify it passes.

* [ ] Task 2.4: Commit natural-language UX contract.

* [ ] Task 3: Write failing test that all skill contracts define Korean as default language and first-time learner as primary audience.

* [ ] Task 3.1: Run the Korean/default learner contract test and verify it fails.

* [ ] Task 3.2: Add Korean default and first-time learner requirements to router and all sub-skill contracts.

* [ ] Task 3.3: Run the Korean/default learner contract test and verify it passes.

* [ ] Task 3.4: Commit language and learner contract.

* [ ] Task 4: Write failing test for `topic_slug` sanitization.

```python
def test_topic_slug_strips_dangerous_characters():
    assert sanitize_topic_slug("../ kubelet\n") == "kubelet"
    assert "/" not in sanitize_topic_slug("a/b")
    assert ".." not in sanitize_topic_slug("../a")
```

* [ ] Task 4.1: Run slug sanitizer test and verify it fails.

* [ ] Task 4.2: Implement minimal `sanitize_topic_slug()` helper.

* [ ] Task 4.3: Run slug sanitizer test and verify it passes.

* [ ] Task 4.4: Commit slug sanitizer.

* [ ] Task 5: Write failing test for project-subtree path restriction.

* [ ] Task 5.1: Run path restriction test and verify it fails.

* [ ] Task 5.2: Implement `resolve_subject_path(topic_slug)` to resolve only under `/home/user01/project/recall-system/subject/<topic_slug>/`.

* [ ] Task 5.3: Run path restriction test and verify it passes.

* [ ] Task 5.4: Commit root path guard.

#### Phase 2: Shared Infrastructure: atomic writes, JSON recovery, lock, state

* [ ] Task 6: Write failing test for atomic text write using temp file and rename.

```python
def test_atomic_write_creates_temp_and_renames(tmp_path):
    target = tmp_path / "index.md"
    atomic_write_text(target, "hello")
    assert target.read_text() == "hello"
    assert not (tmp_path / "index.md.tmp").exists()
```

* [ ] Task 6.1: Run atomic text write test and verify it fails.

* [ ] Task 6.2: Implement minimal `atomic_write_text()` with same-directory temp file and `os.replace()`.

* [ ] Task 6.3: Run atomic text write test and verify it passes.

* [ ] Task 6.4: Commit atomic text write helper.

* [ ] Task 7: Write failing test for atomic JSON write.

* [ ] Task 7.1: Run atomic JSON write test and verify it fails.

* [ ] Task 7.2: Implement `atomic_write_json()` using temp file and rename.

* [ ] Task 7.3: Run atomic JSON write test and verify it passes.

* [ ] Task 7.4: Commit atomic JSON write helper.

* [ ] Task 8: Write failing test for corrupted JSON recovery with `.bak` backup and reinitialize.

* [ ] Task 8.1: Run corrupt JSON recovery test and verify it fails.

* [ ] Task 8.2: Implement `read_json_or_recover(path, default_factory)`.

* [ ] Task 8.3: Run corrupt JSON recovery test and verify it passes.

* [ ] Task 8.4: Commit JSON recovery helper.

* [ ] Task 9: Write failing test for `.lock` execution lock.

* [ ] Task 9.1: Run lock test and verify it fails.

* [ ] Task 9.2: Implement `ExecutionLock` that creates and releases `.lock` file atomically.

* [ ] Task 9.3: Run lock test and verify it passes.

* [ ] Task 9.4: Commit execution lock helper.

* [ ] Task 10: Write failing test for subject state initialization under `subject/<topic_slug>/`.

* [ ] Task 10.1: Run subject initialization test and verify it fails.

* [ ] Task 10.2: Implement `initialize_subject(topic_slug)` to create `metadata.json`, `recall_queue.json`, `study_notes.json`, `system_state.json`, and `recall_sessions/`.

* [ ] Task 10.3: Run subject initialization test and verify it passes.

* [ ] Task 10.4: Commit subject state initializer.

#### Phase 3: Learn sub-skill: material generation contract and validation

* [ ] Task 11: Write failing test that learn output path is exactly `subject/<topic_slug>/index.md`.

* [ ] Task 11.1: Run learn output path test and verify it fails.

* [ ] Task 11.2: Implement `learn_output_path(topic_slug)` using sanitized slug and project root guard.

* [ ] Task 11.3: Run learn output path test and verify it passes.

* [ ] Task 11.4: Commit learn path helper.

* [ ] Task 12: Write failing validator test for fixed 7-chapter Korean material structure.

```python
REQUIRED_CHAPTERS = [
    "1. 탄생배경",
    "2. 정의",
    "3. 하위개념",
    "4. 관계도",
    "5. 사례",
    "6. 오해",
    "7. 회상키포인트",
]
```

* [ ] Task 12.1: Run 7-chapter validator test and verify it fails.

* [ ] Task 12.2: Implement `validate_index_md_structure(text)` for ordered chapter headings.

* [ ] Task 12.3: Run 7-chapter validator test and verify it passes.

* [ ] Task 12.4: Commit chapter structure validator.

* [ ] Task 13: Write failing validator test for 30,000+ pure text characters, recall questions per chapter, and inline retrieval points.

* [ ] Task 13.1: Run learn density validator test and verify it fails.

* [ ] Task 13.2: Extend `validate_index_md_structure(text)` to check pure text length, per-chapter recall-question blocks, and inline retrieval point markers.

* [ ] Task 13.3: Run learn density validator test and verify it passes.

* [ ] Task 13.4: Commit density, question, and retrieval-point validators.

* [ ] Task 14: Write failing test that learn contract requires Oracle Browser default, built-in web search option, and optional user material input.

* [ ] Task 14.1: Run learn research-source contract test and verify it fails.

* [ ] Task 14.2: Update learn `SKILL.md` with required research source workflow.

* [ ] Task 14.3: Run learn research-source contract test and verify it passes.

* [ ] Task 14.4: Commit learn research-source contract.

* [ ] Task 15: Write failing test for source conflict resolution metadata.

* [ ] Task 15.1: Run source conflict test and verify it fails.

* [ ] Task 15.2: Implement metadata shape for source decisions: official/primary priority, recency check, uncertainty marking, final reference recording.

* [ ] Task 15.3: Run source conflict test and verify it passes.

* [ ] Task 15.4: Commit source conflict metadata handling.

#### Phase 4: Queue schema and spaced-repetition priority

* [ ] Task 16: Write failing test for `recall_queue.json` initial schema.

* [ ] Task 16.1: Run recall queue schema test and verify it fails.

* [ ] Task 16.2: Implement default queue file shape as an object containing weak-item entries.

* [ ] Task 16.3: Run recall queue schema test and verify it passes.

* [ ] Task 16.4: Commit recall queue schema.

* [ ] Task 17: Write failing test for required `recall_queue_entry` fields.

* [ ] Task 17.1: Run queue entry field test and verify it fails.

* [ ] Task 17.2: Implement queue entry creation with `concept`, `question`, `failure_reason`, `last_score`, `next_priority`, `last_seen`, `due_hint`, and internal `failure_count`.

* [ ] Task 17.3: Run queue entry field test and verify it passes.

* [ ] Task 17.4: Commit queue entry creation.

* [ ] Task 18: Write failing test for `study_notes.json` persistence only when Q&A is requested.

* [ ] Task 18.1: Run study notes persistence test and verify it fails.

* [ ] Task 18.2: Implement minimal study-note append helper with atomic JSON write.

* [ ] Task 18.3: Run study notes persistence test and verify it passes.

* [ ] Task 18.4: Commit study notes persistence.

#### Phase 5: Router skill: intent classification and low-confidence clarification

* [ ] Task 19: Write failing test for router intent labels: `learn`, `study`, `recall`, `unknown`.

* [ ] Task 19.1: Run router intent test and verify it fails.

* [ ] Task 19.2: Implement router contract in `recall-system/SKILL.md` with natural-language intent routing rules.

* [ ] Task 19.3: Run router intent test and verify it passes.

* [ ] Task 19.4: Commit router intent contract.

* [ ] Task 20: Write failing test that router routes learn requests to learn sub-skill without CLI syntax.

* [ ] Task 20.1: Run learn route test and verify it fails.

* [ ] Task 20.2: Add learn routing examples and output obligations to router `SKILL.md`.

* [ ] Task 20.3: Run learn route test and verify it passes.

* [ ] Task 20.4: Commit learn route contract.

* [ ] Task 21: Write failing test that router routes study requests to study sub-skill and preserves direct-read Q&A-only behavior.

* [ ] Task 21.1: Run study route test and verify it fails.

* [ ] Task 21.2: Add study routing examples and Q&A-only contract to router and study skill.

* [ ] Task 21.3: Run study route test and verify it passes.

* [ ] Task 21.4: Commit study route contract.

* [ ] Task 22: Write failing test that router routes recall requests to recall sub-skill.

* [ ] Task 22.1: Run recall route test and verify it fails.

* [ ] Task 22.2: Add recall routing examples and recall-stage summary to router and recall skill.

* [ ] Task 22.3: Run recall route test and verify it passes.

* [ ] Task 22.4: Commit recall route contract.

#### Phase 6: Recall sub-skill: session pipeline and persistence

* [ ] Task 23: Write failing test for recall session directory and session file creation.

* [ ] Task 23.1: Run recall session persistence test and verify it fails.

* [ ] Task 23.2: Implement `create_recall_session(topic_slug)` writing under `subject/<topic_slug>/recall_sessions/`.

* [ ] Task 23.3: Run recall session persistence test and verify it passes.

* [ ] Task 23.4: Commit recall session creation.

* [ ] Task 24: Write failing test for recall session stage order.

* [ ] Task 24.1: Run recall stage order test and verify it fails.

* [ ] Task 24.2: Implement session stage model with `free_recall`, `analysis`, `scaffolded_questions`, `synthesis_check`.

* [ ] Task 24.3: Run recall stage order test and verify it passes.

* [ ] Task 24.4: Commit recall stage model.

* [ ] Task 25: Write failing test for free-recall capture and analysis persistence.

* [ ] Task 25.1: Run free-recall analysis test and verify it fails.

* [ ] Task 25.2: Implement free-recall capture and analysis result fields in session JSON.

* [ ] Task 25.3: Run free-recall analysis test and verify it passes.

* [ ] Task 25.4: Commit free-recall analysis persistence.

* [ ] Task 26: Write failing test for scaffolded questions and synthesis check persistence.

* [ ] Task 26.1: Run scaffold/synthesis test and verify it fails.

* [ ] Task 26.2: Implement scaffolded question records and synthesis check record in session JSON.

* [ ] Task 26.3: Run scaffold/synthesis test and verify it passes.

* [ ] Task 26.4: Commit scaffold and synthesis persistence.

* [ ] Task 27: Write failing test for exactly 5 score levels.

* [ ] Task 27.1: Run scoring test and verify it fails.

* [ ] Task 27.2: Implement score validation allowing only 1, 2, 3, 4, 5.

* [ ] Task 27.3: Run scoring test and verify it passes.

* [ ] Task 27.4: Commit 5-level scoring.

* [ ] Task 28: Write failing test for weak-answer feedback loop order.

* [ ] Task 28.1: Run feedback-loop test and verify it fails.

* [ ] Task 28.2: Implement feedback transition sequence: hint → retry → answer+explanation → register review queue.

* [ ] Task 28.3: Run feedback-loop test and verify it passes.

* [ ] Task 28.4: Commit weak-answer feedback loop.

* [ ] Task 29: Write failing test that queue priority combines recency and failure-count weighting.

* [ ] Task 29.1: Run priority weighting test and verify it fails.

* [ ] Task 29.2: Implement `calculate_next_priority(last_seen, failure_count, last_score)` with both recency and failure-count contributions.

* [ ] Task 29.3: Run priority weighting test and verify it passes.

* [ ] Task 29.4: Commit priority weighting.

* [ ] Task 30: Write failing test for low-confidence router behavior asking exactly once.

* [ ] Task 30.1: Run low-confidence router test and verify it fails.

* [ ] Task 30.2: Add router clarification rule: ask one clarifying question, then route to `unknown` if unresolved.

* [ ] Task 30.3: Run low-confidence router test and verify it passes.

* [ ] Task 30.4: Commit low-confidence router rule.

#### Phase 7: Boundary-condition matrix

* [ ] Task 31: Write failing test that the boundary matrix contains exactly 12 named boundary conditions.

* [ ] Task 31.1: Run boundary matrix count test and verify it fails.

* [ ] Task 31.2: Implement boundary matrix with these 12 Seed-derived cases:

  1. unsafe `topic_slug` contains `/`
  2. unsafe `topic_slug` contains `..`
  3. unsafe `topic_slug` contains whitespace
  4. unsafe `topic_slug` contains control characters
  5. resolved path attempts to leave project subtree
  6. corrupted JSON state file exists
  7. execution `.lock` already exists
  8. learn material is below 30,000 pure text characters
  9. learn material has missing or reordered 7 chapters
  10. study requested before `index.md` exists
  11. recall requested before `index.md` exists
  12. router confidence is low or intent is unknown

* [ ] Task 31.3: Run boundary matrix count test and verify it passes.

* [ ] Task 31.4: Commit boundary matrix.

* [ ] Task 32: Write failing test that every boundary condition has an explicit handler.

* [ ] Task 32.1: Run boundary handler coverage test and verify it fails.

* [ ] Task 32.2: Implement or document handler path for each of the 12 boundary conditions.

* [ ] Task 32.3: Run boundary handler coverage test and verify it passes.

* [ ] Task 32.4: Commit boundary handlers.

#### Phase 8: Final acceptance matrix and completion lock

* [ ] Task 33: Write failing test that every Seed constraint appears in the obligation ledger.

* [ ] Task 33.1: Run constraint ledger coverage test and verify it fails.

* [ ] Task 33.2: Add missing constraint mappings until every Seed constraint is covered.

* [ ] Task 33.3: Run constraint ledger coverage test and verify it passes.

* [ ] Task 33.4: Commit constraint ledger coverage.

* [ ] Task 34: Write failing final acceptance test for all Seed acceptance criteria.

* [ ] Task 34.1: Run final acceptance test and verify it fails.

* [ ] Task 34.2: Complete any missing tests, contract lines, validators, or helpers required by all acceptance criteria.

* [ ] Task 34.3: Run the full test suite and verify all tests pass.

* [ ] Task 34.4: Commit final acceptance completion.

* [ ] Task 35: Write final handoff checklist requiring `all_criteria_pass`, `mvp_v1_scope_met`, and `user_declares_done`.

* [ ] Task 35.1: Run handoff checklist verification and verify it fails until all prior tasks are complete.

* [ ] Task 35.2: Create completion packet showing all Seed criteria, MVP v1 scope status, and remaining need for explicit user declaration.

* [ ] Task 35.3: Run handoff checklist verification and verify it passes.

* [ ] Task 35.4: Commit completion packet.

---

### 5. ontology_inventory

| Schema Field                      | Owning File                                                                 | Lifecycle Notes                                                                                                                                                                                                                                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| subject                           | `/home/user01/project/recall-system/subject/<topic_slug>/`                  | Created by `initialize_subject(topic_slug)` after slug sanitization and root-path validation. All subject-scoped files live beneath this directory.                                                                                                                                                                   |
| index_md                          | `/home/user01/project/recall-system/subject/<topic_slug>/index.md`          | Created or replaced by learn sub-skill only through atomic text write. Validated for 30,000+ pure text characters, fixed 7 chapters, recall questions, inline retrieval points, and final references. Read directly by user in study mode and used as grounding source for study/recall.                              |
| metadata_json                     | `/home/user01/project/recall-system/subject/<topic_slug>/metadata.json`     | Created during subject initialization. Updated through atomic JSON write. Owns topic metadata, source decision notes, source conflict resolution records, web search mode, optional user-material provenance, and material validation status. Recovered through `.bak` backup and default reinitialize on corruption. |
| recall_queue_json                 | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Created during subject initialization. Updated after weak recall answers and priority recalculation. Written atomically. Recovered through `.bak` backup and default empty queue reinitialize on corruption.                                                                                                          |
| recall_sessions_dir               | `/home/user01/project/recall-system/subject/<topic_slug>/recall_sessions/`  | Created during subject initialization. Each recall session writes one session JSON file under this directory. Session files persist free recall, analysis, scaffolded questions, synthesis check, scores, weak-answer feedback state, and queue registration events.                                                  |
| study_notes_json                  | `/home/user01/project/recall-system/subject/<topic_slug>/study_notes.json`  | Created during subject initialization. Appended only when the user requests Q&A or clarification in study mode. Not used to create unsolicited study sessions. Written atomically and recovered with `.bak` on corruption.                                                                                            |
| system_state_json                 | `/home/user01/project/recall-system/subject/<topic_slug>/system_state.json` | Created during subject initialization. Tracks active operation state, last operation, lock metadata, and recovery status. Written atomically and recovered with `.bak` on corruption.                                                                                                                                 |
| recall_queue_entry.concept        | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Written when a weak answer is registered. Names the concept requiring future retrieval practice.                                                                                                                                                                                                                      |
| recall_queue_entry.question       | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Written when a weak answer is registered. Stores the re-askable recall question.                                                                                                                                                                                                                                      |
| recall_queue_entry.failure_reason | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Written after analysis of weak or incorrect answer. Explains why the answer was weak, incorrect, incomplete, or uncertain.                                                                                                                                                                                            |
| recall_queue_entry.last_score     | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Updated after each scored recall attempt. Must be one of the five valid score levels.                                                                                                                                                                                                                                 |
| recall_queue_entry.next_priority  | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Calculated after queue registration and after subsequent recall attempts. Must combine recency and failure-count weighting.                                                                                                                                                                                           |
| recall_queue_entry.last_seen      | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Updated whenever the item is asked or reviewed. Used by priority weighting to boost older items.                                                                                                                                                                                                                      |
| recall_queue_entry.due_hint       | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Written with queue entry and updated after review. Provides a natural-language due/review hint for the agent and user.                                                                                                                                                                                                |
| recall_queue_entry.failure_count  | `/home/user01/project/recall-system/subject/<topic_slug>/recall_queue.json` | Internal support field required to satisfy Seed acceptance for failure-count weighting. Not part of the Seed’s required display fields, but persisted so `next_priority` can combine recency and failure-count weighting reliably.                                                                                    |

---

### 6. evidence_gaps

| Gap ID | Missing or Incomplete Evidence                                                                                    | Why It Matters                                                                                                           | Needed Evidence                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G01    | The Seed requires “All 12 boundary conditions handled” but does not enumerate the 12 boundary conditions by name. | The implementation must avoid inventing hidden acceptance criteria while still making the boundary requirement testable. | The plan defines a Seed-derived 12-case boundary matrix in Task 31. User or supervising Oracle should approve or replace the matrix before treating boundary coverage as frozen. |
| G02    | The exact repository contents at `/home/user01/project/recall-system/` are not provided inside the Seed.          | Existing files may already contain partial contracts, helpers, or conflicting implementation.                            | Before implementation, inspect the project tree and record whether required files are new, existing, or need migration.                                                          |
| G03    | Oracle Browser invocation details are not specified by the Seed.                                                  | The learn sub-skill must default to Oracle Browser, but exact operational interface may be environment-specific.         | Record the available Oracle Browser usage pattern in the learn skill contract without introducing user-facing CLI syntax.                                                        |
| G04    | Built-in web search option is named but not mechanically specified.                                               | The fallback must be allowed without weakening the Oracle Browser default.                                               | Record in `recall-system-learn/SKILL.md` that built-in web search is an explicit optional source path when Oracle Browser is unavailable or user directs it.                     |
| G05    | The Seed does not define the exact 5-level scoring labels.                                                        | The implementation can validate five levels numerically, but user-facing labels may need stable wording.                 | Define a Korean score rubric in the recall sub-skill contract while preserving exactly five score levels.                                                                        |
| G06    | The Seed requires priority weighting by recency + failure count but does not provide a numeric formula.           | Tests need a deterministic formula to verify ordering.                                                                   | Define and test a simple deterministic formula where lower `last_score`, higher `failure_count`, and older `last_seen` increase `next_priority`.                                 |
| G07    | The Seed permits optional Python helper scripts but does not require a specific helper layout.                    | Helper-file locations must be stable for TDD tasks.                                                                      | Use minimal helper files only where needed for testable file safety, validation, persistence, and priority logic; keep the user-facing operation in MD skills.                   |

```
```
