# Oracle-Plus Python CLI Modernization Plan v2

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: use `superpowers:subagent-driven-development` to implement this plan task-by-task with TDD. `superpowers:executing-plans` is invalid unless the user explicitly overrides the default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Oracle browser wrapper into a Python 3.12+ `uv` CLI while preserving the existing browser-mode behavior, lock semantics, run-state format, and Node.js `@steipete/oracle` subprocess model.

**Architecture:** The new implementation should be a small Python package with a single CLI entrypoint and focused helper modules for argument parsing, config, host resolution, port selection, locking, run-state writes, and browser orchestration. The documented agent-facing entrypoint moves to the Python CLI path, while the legacy shell wrapper remains only as an optional compatibility surface if it is still needed during migration.

**Tech Stack:** Python 3.12+, `uv`, standard library `argparse`/`subprocess`/`pathlib`/`fcntl`/`tempfile`, `pytest`, existing Node package `@steipete/oracle`.

---

## Contract Lock

- Preserve browser auto-selection over `9473-9479`, starting at `9473`.
- Preserve the exact local port-lock semantics on `~/.cache/oracle-plus/ports/<port>.lock` with `flock`.
- Preserve the exact run-state path and line-oriented `.meta` format under `~/.cache/oracle-plus/runs/<slug>.meta`.
- Preserve the current host IP resolution order, busy fallback behavior, remote token injection, Codex Project URL injection at port `9473`, and control-command bypasses.
- Move the documented agent-facing entrypoint to `/home/user01/project/oracle/.venv/bin/oracle-plus`.
- Do not introduce SQLite, a database, or Python Playwright automation.
- Do not require deleting `output/oracle-plus.sh` as part of the modernization contract.
- If `output/oracle-plus.sh` is retained, it may only exist as a compatibility surface or thin forwarder and must not remain the documented entrypoint.
- Source-bearing docs and helper scripts must stop pointing at `output/oracle-plus.sh`.

---

## File Map

### Create

- `pyproject.toml`
- `src/oracle_plus/__init__.py`
- `src/oracle_plus/__main__.py`
- `src/oracle_plus/cli.py`
- `src/oracle_plus/args.py`
- `src/oracle_plus/config.py`
- `src/oracle_plus/host.py`
- `src/oracle_plus/ports.py`
- `src/oracle_plus/locks.py`
- `src/oracle_plus/run_state.py`
- `src/oracle_plus/node_cli.py`
- `src/oracle_plus/browser_run.py`
- `tests/oracle_plus/test_args.py`
- `tests/oracle_plus/test_browser_mode.py`
- `tests/oracle_plus/test_control_bypass.py`
- `tests/oracle_plus/test_host_resolution.py`
- `tests/oracle_plus/test_ports.py`
- `tests/oracle_plus/test_locks.py`
- `tests/oracle_plus/test_run_state.py`
- `tests/oracle_plus/test_node_cli.py`
- `tests/oracle_plus/test_browser_fallback.py`
- `tests/oracle_plus/test_codex_url.py`
- `tests/oracle_plus/test_write_output.py`
- `tests/oracle_plus/test_docs_no_legacy_wrapper.py`

### Modify

- `README.md`
- `PORT_SELECTION.md`
- `live-SKILL.md`
- `output/SKILL.md`
- `skills/oracle-browser/SKILL.md`
- `scripts/oracle-env.sh`
- `scripts/oracle-remote-host.sh`
- `scripts/sync-skill-docs.sh` if the repo-local skill copy is added there or the installed-path targets need to be extended
- `tests/oracle-plus-browser-remote-guard.sh`
- `output/oracle-plus.sh` only if a thin compatibility shim is still needed

### Keep Out of Scope for Source Validation

- `backups/`
- `runs/`
- `local-agent-runs/`

Those directories may contain historical references and should not be used as the source-bearing zero-legacy check.

---

## Task 1: Establish the Python package skeleton

### Files

- Create: `pyproject.toml`
- Create: `src/oracle_plus/__init__.py`
- Create: `src/oracle_plus/__main__.py`
- Create: `src/oracle_plus/cli.py`

### Requirements

- `pyproject.toml` must declare Python `>=3.12`.
- The CLI should be installable as `oracle-plus`.
- Use `uv`-compatible metadata and keep runtime dependencies minimal.
- Prefer the standard library unless a dependency is clearly justified.

### Tests first

- Add a smoke test in `tests/oracle_plus/test_browser_mode.py` that imports the package entrypoint and verifies `main` is callable.

### Validation

- `cd /home/user01/project/oracle`
- `uv sync`
- `uv run pytest tests/oracle_plus/test_browser_mode.py`

---

## Task 2: Port shared argument/config helpers into Python

### Files

- Create: `src/oracle_plus/args.py`
- Create: `src/oracle_plus/config.py`

### Requirements

- Preserve bash-equivalent flag detection, prefixed-flag detection, value extraction, strip logic, preview detection, slug sanitization, control-command detection, and browser-engine detection.
- Centralize environment defaults for remote port selection, token defaults, cache roots, lock roots, run-state roots, and probe timeouts.

### Tests first

- Expand `tests/oracle_plus/test_args.py`
- Expand `tests/oracle_plus/test_control_bypass.py`

### Validation

- `uv run pytest tests/oracle_plus/test_args.py tests/oracle_plus/test_control_bypass.py`

---

## Task 3: Implement host, port, lock, and run-state primitives

### Files

- Create: `src/oracle_plus/host.py`
- Create: `src/oracle_plus/ports.py`
- Create: `src/oracle_plus/locks.py`
- Create: `src/oracle_plus/run_state.py`

### Requirements

- Match the current host IP resolution order.
- Keep the candidate port range and fixed-port validation semantics.
- Preserve `flock`-based lock acquisition on `~/.cache/oracle-plus/ports/<port>.lock`.
- Preserve the `.meta` line-oriented run-state format.
- Preserve append-only fallback/status logging.

### Tests first

- Expand `tests/oracle_plus/test_host_resolution.py`
- Expand `tests/oracle_plus/test_ports.py`
- Expand `tests/oracle_plus/test_locks.py`
- Expand `tests/oracle_plus/test_run_state.py`

### Validation

- `uv run pytest tests/oracle_plus/test_host_resolution.py tests/oracle_plus/test_ports.py tests/oracle_plus/test_locks.py tests/oracle_plus/test_run_state.py`

---

## Task 4: Implement Node CLI resolution and browser orchestration

### Files

- Create: `src/oracle_plus/node_cli.py`
- Create: `src/oracle_plus/browser_run.py`
- Modify: `src/oracle_plus/cli.py`

### Requirements

- Resolve the internal Oracle CLI in the order `ORACLE_BIN`, system `oracle`, cached npm install.
- Keep browser-mode orchestration responsible for host resolution, port probing, lock acquisition, busy fallback, Codex URL injection at port `9473`, remote-token injection, and auto `--write-output`.
- Preserve the current busy-output patterns and exit-code mapping.
- Ensure the child process does not inherit the local port lock fd.

### Tests first

- Expand `tests/oracle_plus/test_node_cli.py`
- Expand `tests/oracle_plus/test_browser_fallback.py`
- Expand `tests/oracle_plus/test_codex_url.py`
- Expand `tests/oracle_plus/test_write_output.py`

### Validation

- `uv run pytest tests/oracle_plus/test_node_cli.py tests/oracle_plus/test_browser_fallback.py tests/oracle_plus/test_codex_url.py tests/oracle_plus/test_write_output.py`

---

## Task 5: Wire top-level CLI routing and compatibility behavior

### Files

- Modify: `src/oracle_plus/cli.py`
- Optionally modify: `output/oracle-plus.sh` if it is still needed as a thin compatibility surface

### Requirements

- Preserve the current control-command bypass path.
- Preserve the current browser vs. api routing rules.
- Preserve fixed `host:port` handling and portless host auto-selection.
- Preserve the current failure messages for unreachable, reserved, busy, and host-resolution failures.
- If `output/oracle-plus.sh` remains, make it forward to the Python CLI and keep it out of the documented entrypoint path.

### Tests first

- Expand `tests/oracle_plus/test_browser_mode.py`
- Expand `tests/oracle_plus/test_control_bypass.py`
- Expand `tests/oracle_plus/test_browser_fallback.py`

### Validation

- `uv run pytest tests/oracle_plus/test_browser_mode.py tests/oracle_plus/test_control_bypass.py tests/oracle_plus/test_browser_fallback.py`

---

## Task 6: Update helper scripts and source docs to point to the Python CLI

### Files

- Modify: `scripts/oracle-env.sh`
- Modify: `scripts/oracle-remote-host.sh`
- Modify: `README.md`
- Modify: `PORT_SELECTION.md`

### Requirements

- Move examples and environment output to `/home/user01/project/oracle/.venv/bin/oracle-plus` or `uv run oracle-plus`.
- Preserve the existing remote-host and port-selection behavior in the helper scripts.
- Keep the docs aligned with the current port-lock, run-state, fallback, and write-output behavior.

### Tests first

- Expand `tests/oracle_plus/test_docs_no_legacy_wrapper.py`
- Keep `tests/oracle-plus-browser-remote-guard.sh` as the black-box helper smoke test or replace it with equivalent coverage.

### Validation

- `uv run pytest tests/oracle_plus/test_docs_no_legacy_wrapper.py`
- `bash tests/oracle-plus-browser-remote-guard.sh`

---

## Task 7: Update the skill docs, including the repo-local copy

### Files

- Modify: `live-SKILL.md`
- Modify: `output/SKILL.md`
- Modify: `skills/oracle-browser/SKILL.md`
- Modify: `scripts/sync-skill-docs.sh` only if the repo-local skill copy or installed-path targets need to be synchronized

### Requirements

- Replace the old wrapper variable with `ORACLE_CLI="/home/user01/project/oracle/.venv/bin/oracle-plus"`.
- Update command examples to use `"$ORACLE_CLI"`.
- Preserve the current operational contract for auto-selection, busy fallback, control-command bypass, lock cleanup, and recovery.
- Keep the skill docs from pointing agents at `output/oracle-plus.sh`.

### Tests first

- Expand `tests/oracle_plus/test_docs_no_legacy_wrapper.py`

### Validation

- `uv run pytest tests/oracle_plus/test_docs_no_legacy_wrapper.py`
- `/home/user01/project/oracle/scripts/sync-skill-docs.sh`
- rerun the docs test after sync

---

## Task 8: Keep the legacy wrapper out of the documented contract without requiring its deletion

### Files

- `output/oracle-plus.sh` only if it must be converted into a thin compatibility forwarder

### Requirements

- The plan must not require deletion of the shell wrapper.
- The shell wrapper must not remain the documented agent-facing entrypoint.
- Any remaining shell wrapper behavior must be compatibility-only and must not weaken the Python CLI contract.

### Validation

- Source-bearing docs and helper scripts should not reference `output/oracle-plus.sh`.
- Historical backups and run artifacts are out of scope for this check.

---

## Task 9: Full source-bearing validation

### Required commands

From `/home/user01/project/oracle`:

1. `uv sync`
2. `uv run pytest`
3. `bash tests/oracle-plus-browser-remote-guard.sh`
4. `rg -n "output/oracle-plus\.sh" README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md skills scripts tests`
5. `rg -n "SQLite|sqlite|database|db\.sqlite|\.db" src tests README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md skills`
6. `python -m compileall src`
7. `git diff --check`

### Expected results

- All pytest tests pass.
- The shell guard passes if retained.
- No source-bearing docs or helper scripts point to `output/oracle-plus.sh`.
- No SQLite/database redesign appears.
- Python files compile.
- No whitespace errors.

---

## Self-review checklist

- The plan preserves the seed goal exactly.
- The plan preserves the lock/run-state semantics exactly.
- The plan moves the documented entrypoint to the Python CLI.
- The plan does not require deleting `output/oracle-plus.sh`.
- The plan keeps source-bearing legacy-reference validation realistic.
- The plan includes `skills/oracle-browser/SKILL.md` in the docs migration scope.
- The plan still supports task-by-task TDD and final supervision.

---

## Frozen handoff

This reset plan is complete. The next step is drafting `oracle-modernization-plan-v2.md` from this reset plan, then normalizing that fresh artifact before supervision.
