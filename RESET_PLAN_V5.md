# Reset Plan — Writing Plan v5 (Recovery + CLI Completion)

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

## Artifact Type
Writing plan for CLI study harness implementation.

## Revision Number
v5

## Next Draft Owner
main agent

## Goal
Fix the recovery test to assert all required state fields after scoring, and extend the plan beyond Task 8 to fully implement CLI intake/draft/recall commands with corresponding tests — completing the "CLI study harness" contract declared in the header.

## Rewrite Map
1. Header + Goal + Architecture — unchanged from v4 (carry forward)
2. Tasks 0–6 — carry forward exactly as v4
3. **Task 7 REWRITE** — add full recovery state assertions after scoring (phase, approval_status, draft_version_hash, next_recalls_cursor all populated correctly)
4. Add Task 9: CLI intake command implementation and test
5. Add Task 10: CLI draft command implementation and test  
6. Add Task 11: CLI recall command implementation and e2e CLI surface test (replaces old Task 9/10 numbering)

## Per-Section Instructions for Task 7 Rewrite

### New Test Requirements (add to existing scoring test):
```python
def test_scoring_populates_recovery_state():
    root = Path("/tmp/test-subject")
    add_sources(root, [SourceReference(kind="native", content="substantive content about X and Y")])
    
    # Generate draft with version hash established
    draft_text = generate_draft(root, "Topic")  # establish draft_version_hash in progress_state
    
    approve_draft(root)  # set approval_status=True
    
    q1 = RecallQuestion(id="q1", topic="Section A", prompt="Explain X...")
    q2 = RecallQuestion(id="q2", topic="Section B", prompt="Explain Y...")
    
    entry = record_session(root, [q1, q2], 
                           ["some answer about X", "weak answer with misconceptions about Y"],
                           [0.8, 0.3])
    
    # VERIFY ALL RECOVERY STATE FIELDS ARE POPULATED:
    state = load_progress(root)
    assert state.phase == "recall_adaptive"  # phase updated after scoring
    assert state.approval_status is True      # approval status preserved
    assert state.draft_version_hash is not None and len(state.draft_version_hash) > 0  # hash established during draft generation
    assert state.next_recalls_cursor >= 1     # cursor advanced after recording session
    assert len(state.weak_points) >= 1        # weak points populated from low scores
    assert any(wp.topic == "Section B" for wp in state.weak_points)  # Section B is weak

def test_recovery_from_disk():
    """Simulate another agent resuming: load from disk and verify all context recoverable."""
    root = Path("/tmp/test-subject")
    
    # Rebuild state from disk (simulating fresh process/agent)
    loaded_state = load_progress(root)
    assert loaded_state.phase == "recall_adaptive"
    assert loaded_state.approval_status is True
    assert len(loaded_state.draft_version_hash) > 0
    
    # Verify we can continue: generate next adaptive questions from recovered state
    questions = select_next_questions_weak(root, n=2)
    assert len(questions) == 2
```

## Per-Section Instructions for CLI Completion (New Tasks 9-11)

### Task 9: CLI intake command
- Implement `study intake <subject_id> --text "content"` in cli.py
- Calls add_sources(subject_root, [SourceReference(kind="pasted_text", content=...)])
- Test: invoke_study(["intake", "sid", "--text", "hello"]) exits 0, sources verified in source_reference_data/

### Task 10: CLI draft command  
- Implement `study draft <subject_id>` in cli.py
- Calls generate_draft(subject_root, topic) — subject root determined from workspace and id
- Test: invoke_study(["draft", "sid"]) exits 0, learning_draft.md exists with depth verified

### Task 11: CLI recall command + e2e CLI surface test
- Implement `study recall <subject_id> --mode=first-pass|adaptive` in cli.py
- Must check approval_status before generating questions (ApprovalRequiredError if not approved)
- Test file: tests/test_cli_e2e.py with full lifecycle via CLI: new → intake → draft → approve → recall first-pass → (score answers interactively) → recall adaptive

## Explicit Prohibitions
- NO recovery test that doesn't assert all five state fields after scoring
- NO plan that ends at Task 8 without implementing the declared CLI commands (intake, draft, recall)

## Drafting Checks (must pass before supervision)
1. Task 7 includes: phase=="recall_adaptive", approval_status=True, draft_version_hash populated, next_recalls_cursor >= 1, weak_points with evidence after scoring
2. New Tasks 9-11 implement ALL declared CLI commands from header: intake, draft, recall --mode=first-pass|adaptive
3. Task 11 includes full e2e CLI surface test covering new → intake → draft → approve → recall
4. All other tasks (0-6) carry forward exactly as v4 without modification

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (v4, study-harness-supervise-v6 fail)
- stopping_stalled_retries_ref: this document's output
- reset_brief_ref: `/tmp/reset_brief_v3.md`
- writing_reset_plan_ref: current file
- Revision Number: v5
- Next Draft Owner: main agent
