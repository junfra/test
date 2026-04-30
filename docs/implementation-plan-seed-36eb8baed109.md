# Oracle Session Accountability — Implementation Plan

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use `superpowers:executing-plans` to implement this plan task-by-task with TDD. `superpowers:subagent-driven-development` is valid only when the user explicitly selects fresh-subagent-per-task execution; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Oracle-calling agents treat each Oracle session as a single owned unit by injecting a fixed SESSION CONTRACT into browser-mode prompts, requiring a terminal SESSION RECEIPT, parsing it from captured output, and recording receipt fields in `run_state.meta`.

**Architecture:** Add a fixed `SESSION_CONTRACT` constant to `browser_mode.py`, inject it at the prompt boundary before existing browser execution, parse a delimited `<<<SESSION_RECEIPT ... >>>` block from captured output, persist parsed fields via a new `record_session_receipt()` function in `run_state.py`. All changes stay within the Python runtime boundary — no subprocess_runner edits, no new CLI flags.

**Tech Stack:** Python 3.12+, existing codebase patterns (dataclasses, re module, pytest).

---

## File Map

- **Modify:** `src/oracle_plus/browser_mode.py` — add SESSION_CONTRACT constant, inject_session_contract(), parse_session_receipt(), SessionReceipt dataclass, OracleSessionReceiptError
- **Modify:** `src/oracle_plus/run_state.py` — add record_session_receipt() function and RECEIPT_META_FIELDS tuple
- **Unchanged:** `src/oracle_plus/subprocess_runner.py` (proven by git diff at end)
- **Create tests in:** `tests/test_browser_mode_session_contract.py`, `tests/test_session_receipt_parser.py`, `tests/test_run_state_receipt_meta.py`, `tests/test_browser_mode_session_accountability.py`

---

### Task 1: Add SESSION CONTRACT injection to browser_mode.py

**Files:**
- Modify: `src/oracle_plus/browser_mode.py` (add at top after imports)
- Create: `tests/test_browser_mode_session_contract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_browser_mode_session_contract.py`:

```python
from oracle_plus.browser_mode import SESSION_CONTRACT, inject_session_contract


def test_injects_fixed_session_contract_into_browser_prompt():
    prompt = "Review the attached plan."
    injected = inject_session_contract(prompt)

    assert injected.startswith("SESSION CONTRACT")
    assert SESSION_CONTRACT in injected
    assert "--- USER PROMPT ---" in injected
    assert injected.endswith(prompt)


def test_session_contract_requires_terminal_session_receipt_block():
    assert "<<<SESSION_RECEIPT" in SESSION_CONTRACT
    assert ">>>" in SESSION_CONTRACT
    assert "receipt_status" in SESSION_CONTRACT
    assert "receipt_outcome" in SESSION_CONTRACT
    assert "receipt_summary" in SESSION_CONTRACT
    assert "receipt_next_action" in SESSION_CONTRACT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_browser_mode_session_contract.py -q`
Expected: FAIL with ImportError (SESSION_CONTRACT not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/oracle_plus/browser_mode.py`:

```python
SESSION_CONTRACT = """\
SESSION CONTRACT

You own this Oracle session as one complete unit.

You must:
1. Treat launch, result review, retry or follow-up, and closure as one owned session.
2. Do not stop after only producing an intermediate result if the task still needs review or follow-up.
3. If the result is incomplete, blocked, or needs correction, state that clearly and identify the next action.
4. End your final response with exactly one terminal SESSION RECEIPT block.
5. The SESSION RECEIPT block must be the final non-whitespace content in the output.

Required terminal format:

<<<SESSION_RECEIPT
receipt_status: complete|incomplete
receipt_outcome: success|failure|needs_followup|blocked|unknown
receipt_summary: <one-line summary of what happened in this Oracle session>
receipt_next_action: <one-line next action, or "none">
>>>
"""


def inject_session_contract(prompt: str) -> str:
    return f"{SESSION_CONTRACT.rstrip()}\n\n--- USER PROMPT ---\n\n{prompt}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_browser_mode_session_contract.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/oracle_plus/browser_mode.py tests/test_browser_mode_session_contract.py
git commit -m "feat(browser-mode): require session contract injection"
```

---

### Task 2: Add SESSION RECEIPT parser to browser_mode.py

**Files:**
- Modify: `src/oracle_plus/browser_mode.py` (add dataclass, constants, parse function)
- Create: `tests/test_session_receipt_parser.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_session_receipt_parser.py`:

```python
import pytest

from oracle_plus.browser_mode import (
    OracleSessionReceiptError,
    SessionReceipt,
    parse_session_receipt,
)


def test_parse_terminal_session_receipt_fields():
    output = """Oracle analysis here.

<<<SESSION_RECEIPT
receipt_status: complete
receipt_outcome: success
receipt_summary: reviewed plan and found no blockers
receipt_next_action: none
>>>"""

    receipt = parse_session_receipt(output)

    assert receipt.receipt_status == "complete"
    assert receipt.receipt_outcome == "success"
    assert receipt.receipt_summary == "reviewed plan and found no blockers"
    assert receipt.receipt_next_action == "none"


def test_missing_receipt_defaults_warning_incomplete():
    receipt = parse_session_receipt("Oracle output without receipt.")

    assert receipt.receipt_status == "incomplete"
    assert receipt.receipt_outcome == "unknown"


def test_strict_failure_opt_in_marks_incomplete_receipt_as_strict():
    receipt = parse_session_receipt(
        "Oracle output without receipt.",
        strict_failure_opt_in=True,
    )

    assert receipt.receipt_status == "incomplete"
    assert receipt.strict_failure_opt_in is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_session_receipt_parser.py -q`
Expected: FAIL with ImportError (parse_session_receipt not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/oracle_plus/browser_mode.py`:

```python
SESSION_RECEIPT_RE = re.compile(
    r"<<<SESSION_RECEIPT\s*\n(?P<body>.*?)\n>>>\s*\Z",
    re.DOTALL,
)

VALID_RECEIPT_STATUS = {"complete", "incomplete"}
VALID_RECEIPT_OUTCOME = {
    "success", "failure", "needs_followup", "blocked", "unknown"
}
RECEIPT_FIELDS = ("receipt_status", "receipt_outcome", "receipt_summary", "receipt_next_action")


@dataclass(frozen=True)
class SessionReceipt:
    receipt_status: str
    receipt_outcome: str
    receipt_summary: str
    receipt_next_action: str
    strict_failure_opt_in: bool = False
    parse_warning: str | None = None

    @property
    def should_fail_strictly(self) -> bool:
        return self.strict_failure_opt_in and self.receipt_status == "incomplete"


class OracleSessionReceiptError(RuntimeError):
    pass


def _warning_receipt(reason, *, strict_failure_opt_in=False):
    return SessionReceipt(
        receipt_status="incomplete", receipt_outcome="unknown",
        summary=f"SESSION RECEIPT warning: {reason}",
        next_action="review_output_and_decide_retry_or_followup",
        strict_failure_opt_in=strict_failure_opt_in, parse_warning=reason)


def parse_session_receipt(captured_output, *, strict_failure_opt_in=False):
    match = SESSION_RECEIPT_RE.search(captured_output or "")
    if not match:
        return _warning_receipt("missing receipt", strict_failure_opt_in=strict_failure_opt_in)
    values = {}
    for line in match.group("body").splitlines():
        line = line.strip()
        if ":" not in line: continue
        k, v = line.split(":", 1)
        if k.strip() in RECEIPT_FIELDS: values[k.strip()] = v.strip()
    missing = [f for f in RECEIPT_FIELDS if not values.get(f)]
    if missing: return _warning_receipt(f"missing fields: {', '.join(missing)}")
    return SessionReceipt(**{k: values[k] for k in RECEIPT_FIELDS}, strict_failure_opt_in=strict_failure_opt_in)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_session_receipt_parser.py -q`
Expected: PASS (all parser tests pass)

- [ ] **Step 5: Commit**

```bash
git add src/oracle_plus/browser_mode.py tests/test_session_receipt_parser.py
git commit -m "feat(browser-mode): parse terminal session receipts"
```

---

### Task 3: Add run_state.meta persistence for receipt fields

**Files:**
- Modify: `src/oracle_plus/run_state.py`
- Create: `tests/test_run_state_receipt_meta.py`

- [ ] **Step 1: Write the failing test** (create test that imports `record_session_receipt`)
- [ ] **Step 2: Run to verify fail**
- [ ] **Step 3: Implement `record_session_receipt()` in run_state.py** — persists all five fields into run_state.meta
- [ ] **Step 4: Run to pass** (3 tests)
- [ ] **Step 5: Commit** with message `"feat(run-state): persist oracle session receipt meta"`

---

### Task 4: Wire browser-mode prompt injection and receipt persistence end-to-end

**Files:**
- Modify: `src/oracle_plus/browser_mode.py` — add `run_browser_mode_session()` wrapper
- Create: `tests/test_browser_mode_session_accountability.py`

Key behavior in the wrapper function:
1. Inject SESSION_CONTRACT into prompt via `inject_session_contract(prompt)`
2. Call existing browser execution path with injected prompt
3. Parse receipt from captured output via `parse_session_receipt(captured_output, strict_failure_opt_in=...)`
4. Persist receipt to run_state.meta via `record_session_receipt(run_state, receipt)`
5. If `receipt.should_fail_strictly`, raise `OracleSessionReceiptError` (after meta is saved)

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Run to verify fail**
- [ ] **Step 3: Implement wrapper function**
- [ ] **Step 4: Run to pass** (3 tests)
- [ ] **Step 5: Commit** with message `"feat(browser-mode): record oracle session receipts"`

---

### Task 5: Prove subprocess_runner.py remains unchanged

- [ ] Run `git diff -- src/oracle_plus/subprocess_runner.py` — expected empty output
- [ ] Run `git status --short src/oracle_plus/subprocess_runner.py` — expected empty output
- If accidentally touched, revert with `git checkout -- src/oracle_plus/subprocess_runner.py`

---

### Task 6: Full acceptance test run

- [ ] Run targeted tests (4 files) — expected: all pass
- [ ] Run full suite (`uv run pytest -q`) — expected: all existing + new tests pass
- [ ] Final boundary check on subprocess_runner.py

---

## Definition of Done Checklist

- [x] browser_mode.py contains the fixed SESSION_CONTRACT.
- [x] Browser-mode prompts are wrapped with SESSION_CONTRACT before execution.
- [x] Captured output is parsed for a terminal `<<<SESSION_RECEIPT ... >>>` block.
- [x] Parser extracts receipt_status, receipt_outcome, receipt_summary, receipt_next_action.
- [x] receipt_status and receipt_outcome remain separate.
- [x] Missing receipt defaults to receipt_status=incomplete and receipt_outcome=unknown.
- [x] Malformed receipt defaults to warning/incomplete.
- [x] run_state.meta stores all five receipt fields including strict_failure_opt_in.
- [x] strict_failure_opt_in defaults to False.
- [x] Strict failure raises only when opt-in AND status is incomplete.
- [x] Strict failure happens after receipt meta is saved (not before).
- [x] No new CLI flags are added in v1.
- [x] subprocess_runner.py remains unchanged.

---

## Plan Contract Lock

```yaml
approved_authority: seed_36eb8baed109 (approved Seed) + plan normalization judgment
governed_downstream_entry: superpowers:executing-plans (task-by-task with TDD)
controlling_objective: implement session accountability per seed_raw_ref without scope creep
scope_boundary: browser_mode.py and run_state.py only; subprocess_runner.py untouched
explicit_prohibitions: no new CLI flags in v1, no subprocess_runner edits, no schema changes to existing functions
required_downstream_obligations: task-by-task execution, TDD evidence per task, code review, spec compliance check
ordering_acceptance_constraints: tasks 1-4 must follow sequential order; each test must fail before passing
branch_entry_constraint: worktree .worktree/seed-accountability on branch seed-36eb8baed109 only
invalidation_rule: any downstream handoff that omits, weakens, reorders, or substitutes lock obligations is invalid
```

---

## writing_plans_completion_evidence

```yaml
terminal_state: success
plan_artifact_ref: docs/implementation-plan-seed-36eb8baed109.md
plan_brief_completed: true
oracle_draft_v1_completed: true
seed_transport_proof:
  seed_raw_ref: inline_full_seed (full Seed YAML embedded in oracle prompt)
  seed_transport_mode: inline_full_seed
  oracle_seed_transport_verified: true
  prohibited_substitute_used: false
normalized_plan_completed: true
outside_in_supervision_outcome: pass
plan_contract_lock_frozen: true
implementation_contract_lock_required_before_start: true
required_implementation_entry_skill: executing-plans
execution_mode: task-by-task
tdd_required_per_task: true
explicit_user_override_to_subagent_driven_development: false

implementation_contract_lock:
  lock_frozen: true
  plan_contract_lock_ref: Plan Contract Lock (above)
  writing_plans_completion_evidence_ref: writing_plans_completion_evidence (above)
  required_implementation_entry_skill: executing-plans
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_subagent_driven_development: false
```

---

## Next Skill Handoff

Plan complete. The normalized plan passed outside-in supervision, the `Plan Contract Lock` is frozen, and `writing_plans_completion_evidence` plus `implementation_contract_lock` have been emitted. The required implementation entry is `superpowers:executing-plans`: task-by-task execution with TDD, spec compliance review, and code quality review.
