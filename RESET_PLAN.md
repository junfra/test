# Reset Plan — Writing Plan v3 (CLI Study Harness)

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

## Artifact Type
Writing plan for CLI study harness implementation.

## Revision Number
v3

## Next Draft Owner
oracle

## Goal
Rewrite the writing plan to use a locked subject-root API convention throughout, add explicit approval gate enforcement in every recall-question-generation function, strengthen weak-point tracking with concrete evidence assertions, and prove agent recoverability via deep recovery test — all while maintaining TDD bite-sized task structure per superpowers:writing-plans.

## Rewrite Map
1. Header + Goal + Architecture (same format as v2)
2. Task 0–2: Scaffolding + subjects management (refactor to subject-root API)
3. Task 3: Source intake (refactor to accept subject_root)
4. Task 4: Draft generation (minor, already uses subject_root correctly)
5. Task 5: Approval gate (add explicit approval check in recall functions as new subsection)
6. Task 6: Recall sequential first pass (keep, verify approval check present)
7. Task 7: Scoring and weak-point tracking (strengthen test with concrete assertions)
8. Task 8: Adaptive retest (add ApprovalRequiredError raise; strengthen evidence tests)
9. Task 9: CLI integration (add approval check in recall subcommand)
10. Task 10: E2E + recoverability proof (deep recovery test replacing shallow one)

## Per-Section Instructions

### Header / Goal / Architecture
Same structure as v2, but explicitly state the API convention: "Every function that operates on subject data receives either `subject_root = workspace_root / 'subjects' / subject_id` or `(workspace_root, subject_id)` — never bare `root`."

### Task 0–1 (Scaffolding + subjects)
- Task 0: Same as v2 (models with ProgressState.weak_points list[WeakPoint])
- Task 1: create_subject(workspace_root, subject_id) returns subject_root = workspace_root / "subjects" / subject_id; all subsequent operations use subject_root

### Task 2–3 (Storage + Intake)
- Task 2: save_progress(subject_root, state), load_progress(subject_root), append_recalls(subject_root, entries)
- Task 3: add_sources(subject_root, sources), list_sources(subject_root) — no bare root parameter anywhere

### Task 4 (Drafting)
- generate_draft(subject_root, topic, llm_provider="native") — already correct in v2, keep as is

### Task 5–6 (Approval Gate + Recall First Pass)
- Task 5: approve_draft(subject_root) sets approval_status=True; add subsection "Recall Gate Enforcement" with test `test_recall_rejects_unapproved()` that wraps generate_first_pass_questions(subject_root) in pytest.raises(ApprovalRequiredError) — MUST execute BEFORE approve_draft() call
- Task 6: generate_first_pass_questions(subject_root): first line must be `state = load_progress(subject_root); assert state.approval_status, "ApprovalRequiredError"`; keep sequential open-ended prompt test

### Task 7–8 (Scoring + Adaptive Retest)
- Task 7: score_answer(question, answer, draft_content), decompose_misconceptions(answer, expected); record_session(subject_root, questions, answers, scores): append to recall_history.jsonl with full entry format; update ProgressState.weak_points from scored results — TEST must assert: `assert len(load_progress(subject_root).weak_points) >= 1`, `assert any(wp.weakness_score < 0.5 for wp in weak_points)`
- Task 8: select_next_questions_weak(subject_root, n): MUST first call load_progress(subject_root); if not state.approval_status: raise ApprovalRequiredError; THEN load ProgressState.weak_points and perform weighted random selection — TEST must assert specific weak topics appear in selected questions with evidence from recall_history.jsonl

### Task 9 (CLI Integration)
- add `study subjects approve <id>` and `study recall <id> --mode=first-pass|adaptive` commands; recall command MUST call load_progress(workspace_root, subject_id) then check approval_status before any question generation — TEST: test_recall_fails_without_approval()

### Task 10 (E2E + Recoverability Proof)
- Full lifecycle using subject_root convention consistently
- Recovery test must verify: `assert loaded.phase == "recall_adaptive"`, `assert loaded.approval_status is True`, `assert loaded.draft_version_hash`, `assert loaded.next_recalls_cursor > 0`, `assert len(loaded.weak_points) >= 1`
- session_logs/ verified to contain operational entries (not just existence check)

## Explicit Prohibitions
- NO bare `root` parameter — every function must use subject_root or (workspace_root, subject_id) signature
- NO generate_first_pass_questions() or select_next_questions_weak() without explicit approval_status check before question generation
- NO weak-point tests that don't assert concrete evidence in ProgressState.weak_points and/or recall_history.jsonl
- NO shallow recovery test — must verify phase, approval_status, draft_version_hash, next_recosals_cursor, weak_points all populated correctly after scoring

## Drafting Checks (must pass before supervision submission)
1. Every task function signature uses subject_root (not bare root)
2. At least 3 functions explicitly check progress_state.approval_status and raise ApprovalRequiredError
3. Weak-point tracking test asserts concrete evidence (not just "score >= 0")
4. Recovery test checks specific fields, not just "first_pass_complete is not None"
5. session_logs/ content verified (not just directory existence)

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (v2, study-harness-supervise-v4 fail)
- stopping_stalled_retries_ref: this document's output
- reset_brief_ref: `/tmp/reset_brief.md`
- writing_reset_plan_ref: current file
- Revision Number: v3
- Next Draft Owner: oracle
