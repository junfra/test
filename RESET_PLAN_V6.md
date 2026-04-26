# Reset Plan — Writing Plan v6 (Session Logging + Weakness Exit Condition)

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

## Artifact Type
Writing plan for study harness implementation.

## Revision Number
v6

## Next Draft Owner
main agent

## Goal
Fix three remaining drift items in study-harness:
1. **F9 session_logs**: Replace empty session_logs directory with actual structured JSONL logging — record creation events, draft generation events, recall session events
2. **X3 weakness_loop_active**: Add explicit `verify_exit_conditions(subject_id)` function that checks len(progress_state.weak_points) > 0 after scoring
3. **E5 source_fidelity (minor)**: Already partially covered by test_bibliography_only_references — no change needed

## Rewrite Map
1. Header + Goal + Architecture — unchanged from v5
2. Tasks 0-6 — carry forward exactly as v5
3. **Task 2 REWRITE** (storage.py patch): Add `log_session_event(subject_root, event_type, payload)` function that writes structured JSONL to session_logs/<event_type>.jsonl. Call this from create_subject() and approve_draft().
4. **New Task 12**: Exit condition verification — add verify_exit_conditions(subject_id) in subjects.py or a new module; write acceptance test verifying len(weak_points) > 0 after scoring
5. All other tasks (7-11) carry forward unchanged

## Per-Section Instructions for Session Logging

### File: src/study/logging.py (NEW) + tests/test_logging.py (NEW)

#### Core function signature:
```python
def log_session_event(subject_root: Path, event_type: str, payload: dict):
    """Append a structured session event to session_logs/<event_type>.jsonl."""
    # Implementation: 
    # 1. Create session_logs dir if not exists (mkdir parents=True)
    # 2. Generate UUID for session_log_id
    # 3. Get ISO timestamp from datetime.now(utc)  
    # 4. Write JSON line to subject_root/session_logs/<event_type>.jsonl with fields:
    #    - session_log_id, timestamp, event_type, payload (the dict passed in)
```

#### Test requirements:
- `test_log_session_event_creates_file_and_entry`: Create subject dir, call log_session_event("subject_created", {"topic": "Math"}), verify file exists with exactly 1 line containing the correct JSON
- `test_log_session_event_multiple_types`: Log two different event types to same directory, verify both files exist with correct entries

#### Integration points:
- Call `log_session_event(subject_root, "subject_created", {"topic": topic})` at end of create_subject() in subjects.py
- Call `log_session_event(subject_root, "draft_generated", {"version_hash": hash, "chapters": len(chapters)})` at end of generate_draft() in drafting.py  
- Call `log_session_event(subject_root, "approved")` at end of approve_draft() in subjects.py
- Call `log_session_event(subject_root, "recall_session", {"question_ids": [...], "scores": [...], "outcome": ...})` at end of record_session() in recall.py

## Per-Section Instructions for Exit Condition Verification

### File: src/study/subjects.py (MODIFY) + tests/test_exit_conditions.py (NEW)

#### Function signature:
```python
def verify_exit_conditions(subject_id: str, workspace_root: Path = None) -> dict:
    """Verify all exit conditions are met for a subject.
    
    Returns:
        dict with keys: draft_approved (bool), first_recall_complete (bool), 
                       weakness_loop_active (bool), subject_state_complete (bool)
    """
```

#### Implementation logic:
- Load progress_state.json
- Check approval_status == True → draft_approved = True
- Check phase in ("recall_first_pass", "recall_adaptive") and next_recursors_cursor > 0 → first_recall_complete = True  
- Check len(weak_points) > 0 → weakness_loop_active = True
- Check all required files exist (learning_draft.md, recall_history.jsonl, source_reference_data/, session_logs/, progress_state.json) AND session_logs has at least one entry file → subject_state_complete = True

#### Test requirements:
- `test_verify_exit_conditions_weakness_after_scoring`: Run full lifecycle through record_session with low scores, then call verify_exit_conditions() and assert weakness_loop_active == True (this is the key assertion for X3)
- `test_verify_exit_conditions_subject_state_with_logs`: After logging creation event, verify subject_state_complete returns True only when session_logs directory has log files

## Explicit Prohibitions
- DO NOT add any new external dependencies — use stdlib uuid, datetime, json only
- DO NOT modify existing function signatures in tasks 0-11 (API lock)
- Session logging must not affect the core recall flow — it's a side effect for observability
- exit condition verification must be read-only (load_progress only, no save)

## Drafting Checks (must pass before supervision)
1. log_session_event() creates proper JSONL files under session_logs/
2. All four integration points call log_session_event with correct event_type and payload
3. verify_exit_conditions returns accurate dict with weakness_loop_active == True after scoring
4. All existing 80 tests continue to pass (session logging is a side effect, should not break anything)

## Lineage Evidence Inputs
- failed_artifact_ref: current PLAN.md v5 on study-harness-impl branch
- stopping_stalled_retries_ref: this document's output  
- reset_brief_ref: null
- writing_reset_plan_ref: current file
- Revision Number: v6
- Next Draft Owner: main agent (QWEN worker via subagent-driven-development)
