# Oracle-Plus Python CLI Modernization Implementation Plan v3

## Plan Contract Lock

### Target Artifact

`oracle-modernization-plan-v3.md`

### Implementation Goal

Modernize Oracle-Plus from the current bash-centered wrapper into a Python 3.12+ `uv`-managed CLI application while preserving the existing Oracle-Plus runtime contract.

The Python CLI must continue to invoke Node.js `@steipete/oracle` through subprocess execution. The modernization must not rewrite the Node/Playwright internals.

### Required Modernization Scope

The implementation must preserve:

1. Python 3.12+ CLI managed through `uv`.

2. Node.js `@steipete/oracle` invocation through Python subprocess wrapping only.

3. Exact local port-lock semantics on:

   ```text
   ~/.cache/oracle-plus/ports/*.lock
   ```

4. Exact run-state tracking on:

   ```text
   ~/.cache/oracle-plus/runs/<slug>.meta
   ```

5. Browser-mode auto-selection across ports `9473-9479`.

6. Busy-port fallback behavior.

7. Host IP auto-detection.

8. Codex Project URL injection for port `9473`.

9. Control-command bypass behavior.

10. Source-bearing documentation and helper migration from the shell entrypoint to the Python CLI.

### Compatibility Surface Policy

`output/oracle-plus.sh` is not required to be deleted.

If it remains, it is compatibility surface only. It must not remain the documented primary entrypoint, and new source-bearing docs/helpers must point to the Python CLI.

The shell wrapper may be left in place as a thin compatibility shim only if doing so does not violate the source-bearing documentation migration or the Python CLI contract.

### Explicit Non-Goals

Do not:

* Rewrite `@steipete/oracle`.
* Replace Node subprocess invocation with Python browser automation.
* Replace the lock/run-state contract with SQLite or any different persistence model.
* Require deletion of `output/oracle-plus.sh`.
* Treat backup directories, generated run history, cached artifacts, or historical outputs as source-bearing validation targets.
* Run a repo-wide zero-legacy search that includes backup/run-history artifacts.

---

## File Map and Ownership

### Python CLI Project Files

Create or modify the Python CLI project files under the implementation repo:

```text
pyproject.toml
src/oracle_plus/__init__.py
src/oracle_plus/__main__.py
src/oracle_plus/cli.py
src/oracle_plus/config.py
src/oracle_plus/oracle_resolver.py
src/oracle_plus/ports.py
src/oracle_plus/run_state.py
src/oracle_plus/host.py
src/oracle_plus/browser_mode.py
src/oracle_plus/subprocess_runner.py
```

The package layout may be adjusted only if the same ownership boundaries remain clear:

* `cli.py`: argument parsing, top-level routing, control-command bypass.
* `config.py`: constants, cache paths, environment-derived configuration.
* `oracle_resolver.py`: Node CLI resolution.
* `ports.py`: port probing and flock-backed lock lifecycle.
* `run_state.py`: `.meta` run-state read/write/update behavior.
* `host.py`: local host IP detection.
* `browser_mode.py`: browser-mode orchestration and browser-specific argument shaping.
* `subprocess_runner.py`: subprocess invocation of Node `@steipete/oracle`.

### Tests

Add or update tests under the repo test tree:

```text
tests/test_cli.py
tests/test_config.py
tests/test_oracle_resolver.py
tests/test_ports.py
tests/test_run_state.py
tests/test_host.py
tests/test_browser_mode.py
tests/test_subprocess_runner.py
tests/test_docs_source_refs.py
```

Tests must be written before implementation for each behavior-bearing task.

### Source-Bearing Documentation and Helper Paths

Update source-bearing docs and helpers that currently instruct users or agents to call the shell wrapper directly.

The source-bearing migration scope must include:

```text
README.md
docs/
helpers/
scripts/
skills/oracle-browser/SKILL.md
```

Also update any repo-local source copy of the Oracle browser skill if present, including:

```text
/home/user01/.codex/skills/oracle-browser/SKILL.md
```

when that file is part of the active source-bearing skill surface for this repo workflow.

### Compatibility Path

The following file may remain:

```text
output/oracle-plus.sh
```

It must not be treated as a required deletion target.

If retained, it should either:

* delegate to the Python CLI, or
* remain untouched as legacy compatibility surface while source-bearing docs/helpers no longer present it as the primary path.

### Excluded from Source Validation

Do not include these in zero-legacy validation searches:

```text
backup/
backups/
run-history/
runs/
output/
.cache/
tmp/
dist/
build/
node_modules/
```

Generated artifacts, historical run outputs, backups, and previous failed plan artifacts are not part of the source-bearing validation boundary.

---

## Acceptance Criteria

The completed implementation must satisfy all of the following:

1. `uv` manages a Python 3.12+ CLI project.

2. The Python CLI provides the documented Oracle-Plus entrypoint.

3. The Python CLI invokes Node.js `@steipete/oracle` through subprocess execution.

4. Existing Oracle binary resolution behavior is preserved:

   * `ORACLE_BIN`
   * system `oracle`
   * npm-installed `@steipete/oracle`

5. Port probing and locking preserve the existing `flock`-based lock semantics on:

   ```text
   ~/.cache/oracle-plus/ports/*.lock
   ```

6. Browser-mode port selection preserves ports:

   ```text
   9473-9479
   ```

7. Busy-port fallback behavior is preserved.

8. Run-state tracking preserves the `.meta` file contract under:

   ```text
   ~/.cache/oracle-plus/runs/<slug>.meta
   ```

9. Browser-mode host IP auto-detection is preserved.

10. Codex Project URL injection for port `9473` is preserved.

11. Control commands bypass browser-mode orchestration.

12. Source-bearing docs/helpers point to the Python CLI as the primary entrypoint.

13. `skills/oracle-browser/SKILL.md` is migrated to the Python CLI entrypoint.

14. Validation of legacy shell references is bounded to source-bearing paths only.

15. `output/oracle-plus.sh` is not required to be deleted.

---

## Task 1 — Lock the Python CLI Project Skeleton

### Objective

Create the Python 3.12+ `uv` project structure and define the CLI entrypoint without implementing behavior yet.

### Files

Create or modify:

```text
pyproject.toml
src/oracle_plus/__init__.py
src/oracle_plus/__main__.py
src/oracle_plus/cli.py
tests/test_cli.py
```

### Required Test-First Work

Write failing tests that prove:

1. The package exposes a runnable CLI entrypoint.
2. The CLI can be invoked through the configured `pyproject.toml` script.
3. The CLI accepts passthrough arguments without losing ordering.
4. The CLI does not invoke browser-mode orchestration for explicit control commands.

### Implementation Requirements

`pyproject.toml` must specify:

* Python `>=3.12`.
* `uv`-compatible project metadata.
* A console script entrypoint for the Oracle-Plus Python CLI.
* Test dependencies required for the implementation.

The CLI skeleton must separate:

* argument parsing,
* routing decisions,
* browser-mode orchestration,
* Node subprocess invocation.

### Validation

Run:

```text
uv run pytest tests/test_cli.py
uv run python -m oracle_plus --help
```

---

## Task 2 — Implement Configuration and Cache Path Contracts

### Objective

Centralize constants and filesystem paths used by port locks and run-state metadata.

### Files

Create or modify:

```text
src/oracle_plus/config.py
tests/test_config.py
```

### Required Test-First Work

Write failing tests that prove:

1. The Oracle-Plus cache root resolves to:

   ```text
   ~/.cache/oracle-plus
   ```

2. Port lock files resolve under:

   ```text
   ~/.cache/oracle-plus/ports/
   ```

3. Run-state files resolve under:

   ```text
   ~/.cache/oracle-plus/runs/
   ```

4. Browser-mode candidate ports are exactly:

   ```text
   9473, 9474, 9475, 9476, 9477, 9478, 9479
   ```

5. Configuration creation does not mutate runtime state by itself.

### Implementation Requirements

The configuration module must provide:

* cache root path,
* port lock directory,
* run-state directory,
* candidate browser ports,
* default remote token behavior if already part of the current shell contract,
* environment lookup helpers.

Do not create lock files or run-state files during passive config loading.

### Validation

Run:

```text
uv run pytest tests/test_config.py
```

---

## Task 3 — Preserve Node Oracle CLI Resolution

### Objective

Implement Oracle CLI resolution in Python while preserving the legacy resolution order.

### Files

Create or modify:

```text
src/oracle_plus/oracle_resolver.py
tests/test_oracle_resolver.py
```

### Required Test-First Work

Write failing tests for resolution order:

1. `ORACLE_BIN` wins when set.
2. System `oracle` command is used when available and `ORACLE_BIN` is absent.
3. npm-installed `@steipete/oracle` fallback is used when system command is absent.
4. Resolution failure produces an operator-readable error.
5. Resolution does not execute browser orchestration.

### Implementation Requirements

The resolver must return the command used by `subprocess_runner.py`.

It must not:

* import Playwright,
* implement browser automation,
* mutate port locks,
* write run-state metadata.

### Validation

Run:

```text
uv run pytest tests/test_oracle_resolver.py
```

---

## Task 4 — Preserve Port Probing and Flock Lock Semantics

### Objective

Implement port probing and ownership using the same lock-file semantics as the shell wrapper.

### Files

Create or modify:

```text
src/oracle_plus/ports.py
tests/test_ports.py
```

### Required Test-First Work

Write failing tests that prove:

1. Candidate ports are evaluated in order from `9473` through `9479`.

2. Lock files are located at:

   ```text
   ~/.cache/oracle-plus/ports/<port>.lock
   ```

3. Lock acquisition uses non-overlapping ownership semantics equivalent to `flock`.

4. A busy locked port is skipped.

5. The next available port is selected.

6. If all ports are busy, the failure is explicit and operator-readable.

7. Lock release happens on normal subprocess completion.

8. Lock release happens when subprocess execution fails.

9. Lock files are not replaced by SQLite or a different persistence system.

### Implementation Requirements

Use Python file locking that preserves the existing `flock` behavior.

The lock lifecycle must be owned by the Python CLI process around the browser-mode subprocess invocation.

Do not change the path, naming, or port range.

### Validation

Run:

```text
uv run pytest tests/test_ports.py
```

---

## Task 5 — Preserve Run-State `.meta` Tracking

### Objective

Implement run-state tracking compatible with the existing `.meta` contract.

### Files

Create or modify:

```text
src/oracle_plus/run_state.py
tests/test_run_state.py
```

### Required Test-First Work

Write failing tests that prove:

1. Run-state files are written under:

   ```text
   ~/.cache/oracle-plus/runs/<slug>.meta
   ```

2. Metadata preserves the existing field names and value format.

3. `pid` tracking is preserved.

4. `status` tracking is preserved.

5. Fallback reasons are preserved.

6. Run-state is updated on successful completion.

7. Run-state is updated on failure.

8. Malformed or missing prior state does not corrupt the current run.

9. The implementation does not introduce SQLite.

### Implementation Requirements

The `.meta` format must stay compatible with the legacy shell wrapper.

The run-state module must support:

* create/start state,
* fallback state,
* success state,
* failure state,
* cleanup/final state when applicable.

Do not change the file naming convention.

### Validation

Run:

```text
uv run pytest tests/test_run_state.py
```

---

## Task 6 — Preserve Host IP Auto-Detection

### Objective

Implement host IP detection used by browser-mode remote routing.

### Files

Create or modify:

```text
src/oracle_plus/host.py
tests/test_host.py
```

### Required Test-First Work

Write failing tests that prove host detection preserves the legacy strategy order when applicable, including available strategies such as:

1. `getent`
2. `/etc/hosts`
3. default route inspection
4. resolver configuration fallback
5. explicit operator-readable failure when no host can be resolved

### Implementation Requirements

Host detection must be deterministic and testable.

It must not:

* invoke Node Oracle,
* acquire port locks,
* write run-state files,
* require network access in unit tests.

### Validation

Run:

```text
uv run pytest tests/test_host.py
```

---

## Task 7 — Preserve Browser-Mode Selection and Argument Injection

### Objective

Implement browser-mode orchestration behavior in Python.

### Files

Create or modify:

```text
src/oracle_plus/browser_mode.py
tests/test_browser_mode.py
```

### Required Test-First Work

Write failing tests that prove:

1. Browser mode is selected when the legacy shell would have selected browser mode.
2. Browser mode is not selected for control commands.
3. Ports `9473-9479` are tried in order.
4. Busy ports trigger fallback to the next candidate.
5. Selected port is injected into the Node Oracle invocation.
6. Host IP is injected when browser-mode routing requires it.
7. Codex Project URL injection occurs for port `9473`.
8. Existing user-provided arguments are not reordered or dropped.
9. Existing explicit remote-host or equivalent user intent is not overwritten unless legacy behavior requires it.
10. Run-state fallback reasons are written when fallback occurs.

### Implementation Requirements

Browser orchestration must coordinate:

* config,
* port lock acquisition,
* host detection,
* run-state metadata,
* subprocess invocation.

It must not embed Playwright logic.

The only browser automation implementation remains Node `@steipete/oracle`.

### Validation

Run:

```text
uv run pytest tests/test_browser_mode.py
```

---

## Task 8 — Implement Subprocess Runner for Node Oracle

### Objective

Create the subprocess boundary that invokes resolved Node Oracle commands safely and transparently.

### Files

Create or modify:

```text
src/oracle_plus/subprocess_runner.py
tests/test_subprocess_runner.py
```

### Required Test-First Work

Write failing tests that prove:

1. The runner receives the resolved Oracle command.
2. The runner preserves argument ordering.
3. Environment variables are passed through unless intentionally overridden by the CLI contract.
4. Exit codes propagate correctly.
5. Standard output and standard error behavior remain operator-visible.
6. Subprocess failure updates run-state through the caller-owned lifecycle.
7. The runner does not acquire locks by itself.

### Implementation Requirements

The subprocess runner is a boundary module.

It must not:

* choose browser ports,
* detect host IP,
* parse high-level CLI mode,
* write `.meta` files directly unless explicitly passed a callback by orchestration.

### Validation

Run:

```text
uv run pytest tests/test_subprocess_runner.py
```

---

## Task 9 — Wire the Top-Level CLI Routing

### Objective

Connect argument parsing, mode selection, Oracle resolution, browser orchestration, and subprocess execution.

### Files

Create or modify:

```text
src/oracle_plus/cli.py
src/oracle_plus/__main__.py
tests/test_cli.py
```

### Required Test-First Work

Extend failing CLI tests that prove:

1. Control commands bypass browser orchestration.
2. Browser-mode commands enter the browser orchestration path.
3. Non-browser commands invoke Node Oracle directly.
4. Oracle resolution happens before subprocess invocation.
5. Port locks are held only for the intended browser subprocess lifecycle.
6. Exit codes match the subprocess result.
7. Operator-facing errors are clear when resolution, lock acquisition, or host detection fails.

### Implementation Requirements

The top-level CLI must remain an orchestrator.

It must not collapse all behavior into one file.

Routing decisions must remain testable without launching real browser automation.

### Validation

Run:

```text
uv run pytest tests/test_cli.py
uv run pytest tests/test_oracle_resolver.py tests/test_ports.py tests/test_run_state.py tests/test_host.py tests/test_browser_mode.py tests/test_subprocess_runner.py
```

---

## Task 10 — Optional Compatibility Handling for `output/oracle-plus.sh`

### Objective

Decide whether to leave the legacy shell wrapper untouched or convert it into a compatibility shim.

### Files

Optional source modification:

```text
output/oracle-plus.sh
```

### Required Test-First Work

Only add tests for this file if it is modified.

If modified, tests must prove:

1. The wrapper delegates to the Python CLI.
2. Argument ordering is preserved.
3. Exit code propagation is preserved.
4. The wrapper does not reimplement Python CLI logic.

### Implementation Requirements

This file is not a required deletion target.

Acceptable outcomes:

1. Leave `output/oracle-plus.sh` in place as compatibility surface.
2. Convert `output/oracle-plus.sh` into a minimal shim that delegates to the Python CLI.

Unacceptable outcomes:

1. Require deleting `output/oracle-plus.sh`.
2. Keep source-bearing docs pointing to it as the primary entrypoint.
3. Maintain duplicate behavior in shell after the Python CLI owns the implementation.

### Validation

If modified, run the wrapper-specific tests plus:

```text
uv run pytest tests/test_cli.py
```

---

## Task 11 — Migrate Source-Bearing Docs and Helpers

### Objective

Update active source-bearing docs, helper scripts, and skill documentation so the Python CLI is the documented entrypoint.

### Files

Modify source-bearing references in:

```text
README.md
docs/
helpers/
scripts/
skills/oracle-browser/SKILL.md
```

Also update the active source skill copy if applicable:

```text
/home/user01/.codex/skills/oracle-browser/SKILL.md
```

### Required Test-First Work

Create or update:

```text
tests/test_docs_source_refs.py
```

Tests must check only source-bearing paths.

They must prove:

1. Source-bearing docs do not present `output/oracle-plus.sh` as the primary entrypoint.
2. Source-bearing helper scripts invoke the Python CLI where applicable.
3. `skills/oracle-browser/SKILL.md` points to the Python CLI.
4. Legacy shell references are allowed only when explicitly labeled as compatibility surface.
5. Backup/run-history/generated artifacts are not included in this validation.

### Implementation Requirements

Documentation updates must cover:

* CLI installation through `uv`,
* Python CLI invocation,
* browser-mode behavior,
* port selection behavior,
* run-state location,
* compatibility note for the shell wrapper if retained,
* skill usage instructions.

The source-bearing docs must not imply that users should continue using the shell wrapper as the main path.

### Bounded Legacy-Reference Search

Use a bounded source-bearing search such as:

```text
rg -n "oracle-plus\.sh|output/oracle-plus\.sh" README.md docs helpers scripts skills/oracle-browser/SKILL.md
```

This search is allowed to return matches only when the text clearly identifies the shell wrapper as optional compatibility surface.

Do not run the zero-legacy check across backup/run-history/generated artifacts.

### Validation

Run:

```text
uv run pytest tests/test_docs_source_refs.py
rg -n "oracle-plus\.sh|output/oracle-plus\.sh" README.md docs helpers scripts skills/oracle-browser/SKILL.md
```

Review any matches manually and confirm they are compatibility-only.

---

## Task 12 — End-to-End Validation

### Objective

Validate the complete Python CLI migration without expanding the validation boundary into generated or historical artifacts.

### Required Commands

Run the full Python test suite:

```text
uv run pytest
```

Run CLI help:

```text
uv run python -m oracle_plus --help
```

Run packaging or script-entry validation:

```text
uv run oracle-plus --help
```

Run source-bearing legacy reference validation:

```text
rg -n "oracle-plus\.sh|output/oracle-plus\.sh" README.md docs helpers scripts skills/oracle-browser/SKILL.md
```

Run formatting/static checks if configured in the repo:

```text
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Only run configured tools that exist in the project.

### Validation Boundary

Do not treat matches in the following as failures:

```text
backup/
backups/
run-history/
runs/
output/
.cache/
tmp/
dist/
build/
node_modules/
```

### Required Success Conditions

Before completion, confirm:

1. All tests pass.
2. Python CLI is the documented primary entrypoint.
3. Node `@steipete/oracle` remains the browser automation implementation.
4. Lock files remain under `~/.cache/oracle-plus/ports/*.lock`.
5. Run-state files remain under `~/.cache/oracle-plus/runs/<slug>.meta`.
6. Port range remains `9473-9479`.
7. Browser-mode fallback behavior is covered by tests.
8. Control-command bypass behavior is covered by tests.
9. `skills/oracle-browser/SKILL.md` is migrated.
10. `output/oracle-plus.sh` is not required to be deleted.

---

## Explicit Prohibitions

The implementation must not:

1. Delete `output/oracle-plus.sh` as a required step.
2. Replace flock lock files with SQLite.
3. Replace `.meta` run-state files with SQLite or JSON unless the existing `.meta` contract already requires that exact format.
4. Rewrite Node/Playwright internals in Python.
5. Treat generated run history as source documentation.
6. Run repo-wide zero-legacy validation across backup or run-history artifacts.
7. Leave `skills/oracle-browser/SKILL.md` pointing to the shell wrapper as the primary entrypoint.
8. Present the shell wrapper as the main supported entrypoint after migration.
9. Merge implementation before tests cover lock lifecycle, run-state lifecycle, browser fallback, CLI routing, and docs migration.

---

## Self-Review Checklist

Before handing off for implementation, verify this plan requires:

* Python 3.12+ through `uv`.
* Python CLI as the primary entrypoint.
* Node `@steipete/oracle` subprocess wrapping only.
* Exact lock-file path preservation.
* Exact run-state path preservation.
* Browser ports `9473-9479`.
* Busy fallback behavior.
* Host IP detection.
* Codex Project URL injection at port `9473`.
* Control-command bypass.
* Source-bearing docs/helper migration.
* `skills/oracle-browser/SKILL.md` migration.
* Optional compatibility treatment for `output/oracle-plus.sh`.
* Bounded source-bearing validation only.
* Task-by-task TDD.

---

## Implementation Handoff

Required implementation entry:

```text
superpowers:subagent-driven-development
```

Implement this plan task by task using TDD:

1. Write the failing tests for the current task.
2. Implement only the minimum behavior needed for that task.
3. Run the task-specific validation.
4. Run the relevant regression tests before moving to the next task.
5. Keep commits aligned to completed, validated task boundaries.

The implementation is complete only after the full validation in Task 12 passes and the source-bearing docs/helpers identify the Python CLI as the primary Oracle-Plus entrypoint while preserving `output/oracle-plus.sh` as optional compatibility surface only.
