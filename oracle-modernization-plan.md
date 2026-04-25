# implementation-plan: Oracle-Plus Python CLI Modernization

## Goal

Modernize `/home/user01/project/oracle/output/oracle-plus.sh` into a Python 3.12+ `uv`-managed CLI while preserving the existing wrapper behavior exactly at the user-visible contract level.

The new CLI must continue to invoke Node.js `@steipete/oracle` internally through subprocess execution. It must not redesign browser automation, port locking, run-state storage, or the remote serve model.

## Contract lock

The implementation must preserve these behaviors from the current bash wrapper:

1. Browser-mode auto-selection over ports `9473-9479`, starting at `9473`.
2. Exact local lock location and semantics:

   * `~/.cache/oracle-plus/ports/<port>.lock`
   * non-blocking `flock`
   * one local run per selected port
   * lock meta cleanup on exit
3. Exact run-state location and line-oriented `.meta` format:

   * `~/.cache/oracle-plus/runs/<slug>.meta`
   * no SQLite
   * no JSON replacement
   * append-style `key: value` records
4. Busy fallback:

   * unreachable ports are skipped
   * locally locked ports are skipped
   * remote `busy` failures release the lock and try the next candidate port
5. Host IP auto-detection using the current wrapper order:

   * `getent ahostsv4 host.docker.internal`
   * `/etc/hosts`
   * `ip route show default`
   * `/etc/resolv.conf`
6. Browser-mode detection:

   * `--engine browser`
   * `--mode browser`
   * no explicit engine/mode and no `OPENAI_API_KEY`
7. API-mode exclusion:

   * `--engine api`
   * `--mode api`
8. Control-command bypass:

   * `serve`
   * `status`
   * `session`
   * `help`
   * `--help`
   * `-h`
   * `--version`
   * `version`
   * `completion`
   * `--render`
   * `--render=*`
   * `--render-markdown`
   * `--render-markdown=*`
9. Remote token injection:

   * inject `--remote-token` only when missing
   * use `ORACLE_REMOTE_TOKEN`
   * default to `1234abcd`
10. Codex Project URL injection:

* only for selected/effective remote port `9473`
* skip if `--chatgpt-url`, `--chatgpt-url=...`, `--browser-url`, or `--browser-url=...` already exists

11. Auto `--write-output` injection:

* browser auto-selection runs only
* skip when user already provided `--write-output`
* skip preview/control-style requests such as `--dry-run`, `--preview`, `--render`, and `--render-markdown`

12. Child process lock-fd cleanup:

* Node `@steipete/oracle` subprocess must not inherit the local port lock fd.

13. CLI resolution order:

* `ORACLE_BIN`
* system `oracle`
* cached npm install under `~/.cache/oracle-plus/node_modules/@steipete/oracle/dist/bin/oracle-cli.js`

14. Package bootstrap:

* default package spec remains `@steipete/oracle@0.9.0`
* override remains `ORACLE_NPM_SPEC`

15. No change to Node.js Playwright automation internals.

## Explicit prohibitions

* Do not introduce SQLite, Redis, JSON DB files, lock daemons, or any new state store.
* Do not replace `flock` semantics with PID-file-only locking.
* Do not change the run-state `.meta` file format.
* Do not rewrite `@steipete/oracle`, Playwright, browser automation, or Windows serve logic.
* Do not route browser automation through Python Playwright.
* Do not make `status`, `session`, `serve`, `help`, or render commands acquire port locks.
* Do not let explicit `host:port` remote hosts enter auto-selection.
* Do not pass portless `--remote-host host` directly to the Node CLI.
* Do not leave docs pointing to `/home/user01/project/oracle/output/oracle-plus.sh`.
* Do not keep the bash wrapper as the documented agent-facing entrypoint.

---

## File map

### Create

* `/home/user01/project/oracle/pyproject.toml`
* `/home/user01/project/oracle/src/oracle_plus/__init__.py`
* `/home/user01/project/oracle/src/oracle_plus/__main__.py`
* `/home/user01/project/oracle/src/oracle_plus/cli.py`
* `/home/user01/project/oracle/src/oracle_plus/args.py`
* `/home/user01/project/oracle/src/oracle_plus/config.py`
* `/home/user01/project/oracle/src/oracle_plus/host.py`
* `/home/user01/project/oracle/src/oracle_plus/ports.py`
* `/home/user01/project/oracle/src/oracle_plus/locks.py`
* `/home/user01/project/oracle/src/oracle_plus/run_state.py`
* `/home/user01/project/oracle/src/oracle_plus/node_cli.py`
* `/home/user01/project/oracle/src/oracle_plus/browser_run.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_args.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_browser_mode.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_host_resolution.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_ports.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_locks.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_run_state.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_node_cli.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_browser_fallback.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_codex_url.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_write_output.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_control_bypass.py`
* `/home/user01/project/oracle/tests/oracle_plus/test_docs_no_legacy_wrapper.py`

### Modify

* `/home/user01/project/oracle/README.md`
* `/home/user01/project/oracle/PORT_SELECTION.md`
* `/home/user01/project/oracle/live-SKILL.md`
* `/home/user01/project/oracle/output/SKILL.md`
* `/home/user01/project/oracle/skills/oracle-browser/SKILL.md`
* `/home/user01/project/oracle/scripts/oracle-env.sh`
* `/home/user01/project/oracle/scripts/oracle-remote-host.sh`
* `/home/user01/project/oracle/scripts/sync-skill-docs.sh`
* `/home/user01/project/oracle/tests/oracle-plus-browser-remote-guard.sh`

### Remove or retire

* `/home/user01/project/oracle/output/oracle-plus.sh`

Retirement rule: remove it only after all docs, helpers, and tests use the Python CLI. If a compatibility shim is temporarily needed during migration, it must not remain the documented entrypoint and must be removed before final handoff unless the seed explicitly requires backward compatibility.

### Generated, not hand-authored

* `/home/user01/project/oracle/uv.lock`

---

## New CLI entrypoint

The new installed CLI name must be:

`oracle-plus`

The stable project-local agent-facing path after `uv sync` must be:

`/home/user01/project/oracle/.venv/bin/oracle-plus`

Docs may also mention:

`cd /home/user01/project/oracle && uv run oracle-plus ...`

But skill docs should prefer the fixed executable path:

`ORACLE_CLI="/home/user01/project/oracle/.venv/bin/oracle-plus"`

Do not keep `ORACLE_WRAPPER="/home/user01/project/oracle/output/oracle-plus.sh"` in updated docs.

---

## Task 1: Establish Python project skeleton

### Files

Create:

* `pyproject.toml`
* `src/oracle_plus/__init__.py`
* `src/oracle_plus/__main__.py`
* `src/oracle_plus/cli.py`

### Requirements

`pyproject.toml` must specify:

* Python `>=3.12`
* `uv`-compatible project metadata
* console script:

  * `oracle-plus = "oracle_plus.cli:main"`
* test dependency:

  * `pytest`

Avoid unnecessary runtime dependencies. Prefer the Python standard library for subprocess, file locking, sockets, tempfile, pathlib, datetime, and argument handling.

### Tests first

Add a minimal CLI smoke test in:

* `tests/oracle_plus/test_browser_mode.py`

It should verify that the package entrypoint can be imported and that `main` is callable without invoking Node.

### Validation

Run:

* `cd /home/user01/project/oracle`
* `uv sync`
* `uv run pytest tests/oracle_plus/test_browser_mode.py`

---

## Task 2: Port bash argument helpers into Python

### Files

Create:

* `src/oracle_plus/args.py`

### Behavior to preserve

Implement pure argument utility functions equivalent to the bash helpers:

* detect exact flags
* detect prefixed flags
* extract flag values from both `--flag value` and `--flag=value`
* strip a flag and its value
* detect chatgpt/browser URL overrides
* detect preview requests
* sanitize run-state slugs
* detect control commands
* detect browser engine usage

### Tests first

Add coverage in:

* `tests/oracle_plus/test_args.py`
* `tests/oracle_plus/test_control_bypass.py`

Required assertions:

* `status <slug>` is control.
* `session <slug>` is control.
* `serve` is control.
* `help`, `--help`, `-h`, `version`, `--version`, and `completion` are control.
* `--render` and `--render=...` are control.
* `--render-markdown` and `--render-markdown=...` are control.
* `--engine browser` selects browser.
* `--mode browser` selects browser.
* omitted engine/mode with no `OPENAI_API_KEY` selects browser.
* omitted engine/mode with `OPENAI_API_KEY` does not select browser.
* `--engine api` and `--mode api` do not select browser.
* portless `--remote-host host` can be stripped before forwarding.
* `--remote-host=host` can be stripped before forwarding.
* existing `--remote-token` prevents token injection.
* existing `--remote-token=...` prevents token injection.
* existing `--chatgpt-url`, `--chatgpt-url=...`, `--browser-url`, and `--browser-url=...` prevent Codex Project URL injection.
* slug sanitization preserves only `A-Z`, `a-z`, `0-9`, `.`, `_`, and `-`.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_args.py tests/oracle_plus/test_control_bypass.py`

---

## Task 3: Implement environment-backed config

### Files

Create:

* `src/oracle_plus/config.py`

### Behavior to preserve

Centralize all current bash defaults:

* `ORACLE_REMOTE_PORT`
* `ORACLE_AUTO_REMOTE_PORT_START`
* `ORACLE_AUTO_REMOTE_PORT_END`
* `ORACLE_CHATGPT_AUTO_REMOTE_PORT_START`, default `9473`
* `ORACLE_CHATGPT_AUTO_REMOTE_PORT_END`, default `9479`
* `ORACLE_REMOTE_TOKEN`, default `1234abcd`
* `ORACLE_CODEX_PROJECT_REMOTE_PORT`, default `9473`
* `ORACLE_CODEX_PROJECT_CHATGPT_URL`, default current Codex Project URL
* `ORACLE_REMOTE_PROBE_TIMEOUT_SECONDS`, default `1`
* `ORACLE_PLUS_CACHE_DIR`, default `~/.cache/oracle-plus`
* `ORACLE_PLUS_LOCK_DIR`, default `<cache>/ports`
* `ORACLE_PLUS_RUN_STATE_DIR`, default `<cache>/runs`
* cached Node CLI path:

  * `<cache>/node_modules/@steipete/oracle/dist/bin/oracle-cli.js`
* `ORACLE_NPM_SPEC`, default `@steipete/oracle@0.9.0`
* `ORACLE_LOG_DIR`, default current working directory for capture files
* `ORACLE_PLUS_VERBOSE`, default off

### Tests first

Add coverage in:

* `tests/oracle_plus/test_ports.py`
* `tests/oracle_plus/test_run_state.py`

Required assertions:

* default port range is `9473-9479`.
* explicit `ORACLE_REMOTE_PORT` overrides range with a single candidate.
* explicit `ORACLE_AUTO_REMOTE_PORT_START/END` overrides defaults.
* invalid ports are rejected.
* start greater than end is rejected.
* cache, lock, and run-state roots match current bash defaults.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_ports.py tests/oracle_plus/test_run_state.py`

---

## Task 4: Implement host IP resolution

### Files

Create:

* `src/oracle_plus/host.py`

### Behavior to preserve

Use the wrapper’s exact resolution order:

1. `getent ahostsv4 host.docker.internal`
2. `/etc/hosts`
3. `ip route show default`
4. `/etc/resolv.conf`

Do not use the helper script’s different order as the CLI behavior. The new Python CLI must match `output/oracle-plus.sh`.

### Tests first

Add coverage in:

* `tests/oracle_plus/test_host_resolution.py`

Required assertions:

* `getent` result wins when present.
* `/etc/hosts` result is used only when `getent` fails or is unavailable.
* default route gateway is used only after `getent` and `/etc/hosts` fail.
* resolver nameserver is used only as final fallback.
* failure to resolve host returns the same high-level failure path as the bash wrapper: unable to resolve Windows host IP and asks user to set `ORACLE_REMOTE_HOST`.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_host_resolution.py`

---

## Task 5: Implement port candidate and probe logic

### Files

Create:

* `src/oracle_plus/ports.py`

### Behavior to preserve

Implement:

* valid port checking
* explicit `ORACLE_REMOTE_PORT`
* auto range resolution
* candidate port description
* remote host port extraction
* fixed `host:port` validation
* probe timeout from `ORACLE_REMOTE_PROBE_TIMEOUT_SECONDS`

Observable behavior must match the bash wrapper:

* explicit `host:port` is fixed-port execution.
* portless host triggers auto-selection.
* no host triggers auto-selection using resolved host IP.
* candidate order is ascending and starts at `9473` by default.
* no reachable endpoints returns status code path `10`.

### Tests first

Add coverage in:

* `tests/oracle_plus/test_ports.py`
* `tests/oracle_plus/test_browser_fallback.py`

Required assertions:

* default candidates are `9473` through `9479`.
* explicit single port produces one candidate.
* invalid ports fail before probing.
* portless remote host does not get forwarded directly.
* fixed `host:port` bypasses auto-selection.
* unreachable ports record fallback reasons and eventually produce no-reachable failure.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_ports.py tests/oracle_plus/test_browser_fallback.py`

---

## Task 6: Implement exact flock-based lock semantics

### Files

Create:

* `src/oracle_plus/locks.py`

### Behavior to preserve

Implement real local file locks using `flock` semantics on:

* `~/.cache/oracle-plus/ports/<port>.lock`

Meta file path:

* `~/.cache/oracle-plus/ports/<port>.meta`

Meta file content must preserve the existing line-oriented fields:

* `pid: <pid>`
* `slug: <session_slug>`
* `started_at: <UTC timestamp>`
* `remote_host: <host:port>`

Lifecycle:

* create lock root if needed
* open lock file
* acquire non-blocking exclusive flock
* write meta only after lock succeeds
* if lock fails, close fd and return unavailable
* on release, remove meta file and close fd
* on process exit, cleanup must run
* on busy fallback, release the lock before trying the next port

### Tests first

Add coverage in:

* `tests/oracle_plus/test_locks.py`
* `tests/oracle_plus/test_browser_fallback.py`

Required assertions:

* lock file is created under `<lock_root>/<port>.lock`.
* meta file is created under `<lock_root>/<port>.meta`.
* second local lock attempt fails while first is held.
* failed lock does not overwrite active meta.
* release removes meta.
* release closes fd.
* cleanup is idempotent.
* a locally reserved `9473` causes fallback to `9474`.
* fallback state records `fallback_reason: 9473=local_lock_reserved`.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_locks.py tests/oracle_plus/test_browser_fallback.py`

---

## Task 7: Implement run-state `.meta` writer

### Files

Create:

* `src/oracle_plus/run_state.py`

### Behavior to preserve

Run state must stay at:

* `~/.cache/oracle-plus/runs/<slug>.meta`

Or overridden by:

* `ORACLE_PLUS_RUN_STATE_DIR`

Initial write must preserve these fields:

* `pid: <pid>`
* `slug: <session_slug>`
* `started_at: <UTC timestamp>`
* `status: selecting_port`
* `host: <host_ip>`
* `candidate_ports: <comma-separated candidates>`

Append records must preserve current `key: value` format.

Required appended keys:

* `selected_port`
* `selected_remote_host`
* `capture_path`
* `fallback_reason`
* `status`
* `exit_code`

Status values to preserve:

* `selecting_port`
* `completed`
* `failed`
* `no_reachable_endpoint`
* `all_reachable_endpoints_reserved`
* `all_reachable_endpoints_busy`
* `no_candidate_selected`

### Tests first

Add coverage in:

* `tests/oracle_plus/test_run_state.py`

Required assertions:

* state file path is exactly `<run_state_root>/<sanitized_slug>.meta`.
* empty slug falls back to generated `oracle-run-<timestamp>-<pid>` style slug.
* initial file starts with the same field names as bash.
* later records append instead of rewriting the whole file.
* fallback reasons can appear multiple times.
* no JSON or SQLite files are created.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_run_state.py`

---

## Task 8: Implement Node CLI resolution and subprocess runner

### Files

Create:

* `src/oracle_plus/node_cli.py`

### Behavior to preserve

Resolve the internal Oracle CLI in this order:

1. `ORACLE_BIN`

   * must exist and be executable
2. system `oracle`
3. cached npm installation:

   * install `ORACLE_NPM_SPEC` into `ORACLE_PLUS_CACHE_DIR`
   * require `npm`
   * require `node`
   * execute cached JS through `node`

Subprocess behavior:

* support normal run passthrough
* support captured run for busy detection
* combine stdout and stderr for busy detection
* still stream output to the current process while capturing
* preserve Node exit code
* ensure child processes do not inherit local port lock fds

### Tests first

Add coverage in:

* `tests/oracle_plus/test_node_cli.py`
* `tests/oracle_plus/test_locks.py`

Required assertions:

* `ORACLE_BIN` wins over system `oracle`.
* non-executable `ORACLE_BIN` fails.
* system `oracle` is used when available.
* npm bootstrap is attempted only when no `ORACLE_BIN` and no system `oracle` exist.
* cached JS path is invoked with `node`.
* child subprocess cannot see the held lock fd.
* captured run preserves the child exit code.
* captured run exposes output for busy matching.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_node_cli.py tests/oracle_plus/test_locks.py`

---

## Task 9: Implement browser auto-selection orchestration

### Files

Create:

* `src/oracle_plus/browser_run.py`
* Update `src/oracle_plus/cli.py`

### Behavior to preserve

This is the core behavior currently in `run_browser_with_busy_fallback`.

The orchestrator must:

1. Resolve host IP or use portless host override.
2. Build candidate ports.
3. Initialize run state.
4. For each candidate:

   * probe endpoint
   * record `fallback_reason: <port>=unreachable` when unreachable
   * acquire local port lock
   * record `fallback_reason: <port>=local_lock_reserved` when lock fails
   * record selected port and remote host when lock succeeds
   * build forwarded args:

     * `--remote-host <host:port>`
     * `--remote-token <token>` when needed
     * `--chatgpt-url <Codex Project URL>` only for selected port `9473` and only when no URL override exists
     * auto `--write-output <capture>` only when needed
     * original browser args
   * run Node CLI with capture
   * on exit `0`, record `status: completed`
   * on busy output, record `fallback_reason: <port>=remote_busy`, release lock, try next port
   * on non-busy failure, record `status: failed` and `exit_code`
5. After all candidates:

   * no reachable endpoint → status `no_reachable_endpoint`, exit path `10`
   * reachable but all locally reserved → status `all_reachable_endpoints_reserved`, exit path `11`
   * any remote busy and none succeeded → status `all_reachable_endpoints_busy`, exit path `13`
   * otherwise → status `no_candidate_selected`, exit path `12`

Busy detection must preserve current patterns:

* `ERROR: busy`
* `User error (browser-automation): busy`

### Tests first

Add coverage in:

* `tests/oracle_plus/test_browser_fallback.py`
* `tests/oracle_plus/test_codex_url.py`
* `tests/oracle_plus/test_write_output.py`

Required assertions:

* auto-selection starts at `9473`.
* unreachable `9473` falls through to reachable `9474`.
* locally locked `9473` falls through to `9474`.
* remote busy on `9473` releases lock and falls through to `9474`.
* non-busy failure does not continue to next port.
* selected port is written to run state.
* selected remote host is written to run state.
* fallback reasons are written exactly in `port=reason` format.
* `--remote-token` is injected when missing.
* existing `--remote-token` is not duplicated.
* Codex Project URL is injected only for port `9473`.
* Codex Project URL is not injected for port `9474+`.
* Codex Project URL is not injected when URL override exists.
* auto `--write-output` is injected when omitted.
* auto `--write-output` is not injected for `--dry-run`.
* auto `--write-output` is not injected for `--preview`.
* explicit `--write-output` is preserved and recorded as capture path.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_browser_fallback.py tests/oracle_plus/test_codex_url.py tests/oracle_plus/test_write_output.py`

---

## Task 10: Implement top-level CLI routing

### Files

Modify:

* `src/oracle_plus/cli.py`

### Behavior to preserve

The top-level CLI must match current `main()` routing:

1. Resolve Node CLI before execution.
2. Extract `--slug`.
3. If control command:

   * bypass browser auto-selection
   * do not resolve host
   * do not probe ports
   * do not acquire local locks
   * do not write run state
   * forward args directly to Node CLI
4. If browser mode:

   * inspect explicit `--remote-host`
   * inspect `ORACLE_REMOTE_HOST`
   * distinguish fixed `host:port` from portless `host`
   * fixed `host:port` bypasses auto-selection
   * portless host enables auto-selection using that host
   * no host enables auto-selection using resolved host IP
   * inject token for fixed remote host when missing
   * inject Codex Project URL for fixed port `9473` when applicable
5. If auto-selection is enabled:

   * call browser fallback orchestration
   * map failure statuses to current user-facing error messages
6. If auto-selection is not enabled:

   * forward args directly to Node CLI with any injected fixed-run args

### Tests first

Add coverage in:

* `tests/oracle_plus/test_browser_mode.py`
* `tests/oracle_plus/test_control_bypass.py`
* `tests/oracle_plus/test_browser_fallback.py`

Required assertions:

* `status` with no API key still bypasses browser auto-selection.
* `session` with no API key still bypasses browser auto-selection.
* `--render` with no API key still bypasses browser auto-selection.
* explicit `--remote-host host:9473` does not acquire local lock.
* explicit `ORACLE_REMOTE_HOST=host:9473` does not acquire local lock.
* portless `--remote-host host` enters auto-selection.
* portless `ORACLE_REMOTE_HOST=host` enters auto-selection.
* no `--remote-host`, no `ORACLE_REMOTE_HOST`, no API key enters auto-selection.
* `--engine api` does not enter auto-selection.
* `--mode api` does not enter auto-selection.
* all no-reachable endpoints maps to the current failure message.
* all locally reserved endpoints maps to the current failure message.
* all busy endpoints maps to the current failure message.
* unable host resolution maps to the current failure message.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_browser_mode.py tests/oracle_plus/test_control_bypass.py tests/oracle_plus/test_browser_fallback.py`

---

## Task 11: Update helper scripts to call Python CLI

### Files

Modify:

* `scripts/oracle-env.sh`
* `scripts/oracle-remote-host.sh`

### Required changes

`scripts/oracle-env.sh`:

* export the new Python CLI path:

  * `/home/user01/project/oracle/.venv/bin/oracle-plus`
* stop printing `ORACLE_WRAPPER=/home/user01/project/oracle/output/oracle-plus.sh`.
* either print `ORACLE_CLI=...` or preserve `ORACLE_WRAPPER` as a backward-compatible environment variable pointing to the Python CLI.
* Do not change fixed-port semantics unless explicitly needed.

`scripts/oracle-remote-host.sh`:

* set its executable target to:

  * `/home/user01/project/oracle/.venv/bin/oracle-plus`
* keep the helper’s existing host-only behavior:

  * `--host host` exports portless `ORACLE_REMOTE_HOST=host`
  * Python CLI performs `9473-9479` auto-selection
* keep fixed port behavior:

  * `--host host --port 9473`
  * `--host host:9473`
* keep `--cwd` behavior.

### Tests first

Update or replace:

* `tests/oracle-plus-browser-remote-guard.sh`

Add equivalent Python pytest assertions where possible. The helper script smoke test should verify:

* helper host-only path invokes the Python CLI target.
* helper fixed-port path exports fixed `host:port`.
* `oracle-env.sh` prints the Python CLI path, not `output/oracle-plus.sh`.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_docs_no_legacy_wrapper.py`
* `bash tests/oracle-plus-browser-remote-guard.sh`

---

## Task 12: Update README and port-selection docs

### Files

Modify:

* `README.md`
* `PORT_SELECTION.md`

### Required documentation changes

Replace references to:

* `/home/user01/project/oracle/output/oracle-plus.sh`

With:

* `/home/user01/project/oracle/.venv/bin/oracle-plus`

or:

* `cd /home/user01/project/oracle && uv run oracle-plus ...`

Required README updates:

* Components list must mention the Python CLI package.
* Components list must no longer describe `output/oracle-plus.sh` as the wrapper.
* Env examples must use the Python CLI.
* `oracle-env.sh` output example must print the new Python CLI path.
* ChatGPT browser auto-selection examples must use the new CLI.
* Notes must preserve current behavior statements:

  * auto-selection `9473-9479`
  * control-command bypass
  * run-state path
  * write-output injection
  * lock-fd cleanup
  * durable output pruning

Required `PORT_SELECTION.md` updates:

* Title can remain the same.
* Replace wrapper path with Python CLI path.
* Preserve all policy text for:

  * candidate order
  * lock paths
  * meta paths
  * run-state paths
  * failure conditions
  * manual overrides
  * helper behavior
* Do not weaken “single local run per port” language.

### Tests first

Add coverage in:

* `tests/oracle_plus/test_docs_no_legacy_wrapper.py`

Required assertions:

* README does not reference `output/oracle-plus.sh`.
* PORT_SELECTION does not reference `output/oracle-plus.sh`.
* README references `.venv/bin/oracle-plus` or `uv run oracle-plus`.
* PORT_SELECTION references `.venv/bin/oracle-plus` or `uv run oracle-plus`.
* docs still mention:

  * `~/.cache/oracle-plus/ports/<port>.lock`
  * `~/.cache/oracle-plus/runs/<slug>.meta`
  * `9473`
  * `9479`
  * `busy`
  * `status`
  * `session`
  * `--render`

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_docs_no_legacy_wrapper.py`

---

## Task 13: Update oracle-browser skill docs

### Files

Modify:

* `live-SKILL.md`
* `output/SKILL.md`
* `skills/oracle-browser/SKILL.md`
* `scripts/sync-skill-docs.sh`

### Required skill changes

In both skill docs, replace the old wrapper variable:

* old: `ORACLE_WRAPPER="/home/user01/project/oracle/output/oracle-plus.sh"`

With the new CLI variable:

* new: `ORACLE_CLI="/home/user01/project/oracle/.venv/bin/oracle-plus"`

Then update every command example to invoke:

* `"$ORACLE_CLI"`

not:

* `"$ORACLE_WRAPPER"`

Preserve all operational policy text unless it explicitly names the bash wrapper.

Required preserved content:

* port auto-selection from `9473-9479`
* same-run busy fallback
* host-only `--remote-host` behavior
* control-command bypass behavior
* run-state file path
* `--write-output` auto-injection behavior
* lock-fd cleanup behavior
* no raw `npx -y @steipete/oracle` usage
* `--browser-model-strategy current`
* completion checks using session meta
* recovery flow
* render fallback

Update language from “wrapper” to “Python CLI” where appropriate, but do not change the skill’s execution contract.

### Sync behavior

`scripts/sync-skill-docs.sh` must continue to sync `live-SKILL.md` into:

* `output/SKILL.md`
* optional installed Codex skill path

If the installed path is `/home/user01/.codex/skills/oracle-browser/SKILL.md`, update it only through the sync script unless the existing repo convention says otherwise.

### Tests first

Extend:

* `tests/oracle_plus/test_docs_no_legacy_wrapper.py`

Required assertions:

* `live-SKILL.md` does not reference `output/oracle-plus.sh`.
* `output/SKILL.md` does not reference `output/oracle-plus.sh`.
* `skills/oracle-browser/SKILL.md` does not reference `output/oracle-plus.sh` if the repo-local copy remains present.
* both skill docs reference `.venv/bin/oracle-plus`.
* both skill docs use `ORACLE_CLI`.
* both skill docs still prohibit raw `npx -y @steipete/oracle`.
* both skill docs still mention run-state `.meta`.
* both skill docs still mention control-command bypass.

### Validation

Run:

* `uv run pytest tests/oracle_plus/test_docs_no_legacy_wrapper.py`
* `/home/user01/project/oracle/scripts/sync-skill-docs.sh`
* rerun the docs test after sync.

---

## Task 14: Replace or retire bash guard test

### Files

Modify or retire:

* `tests/oracle-plus-browser-remote-guard.sh`

### Required outcome

The migration must not leave a test suite whose main contract still assumes the implementation is `output/oracle-plus.sh`.

Acceptable paths:

1. Convert the shell guard into a thin black-box smoke test that invokes:

   * `/home/user01/project/oracle/.venv/bin/oracle-plus`
2. Or retire the shell guard after equivalent pytest coverage exists.

The preferred path is to keep a small black-box smoke guard and move detailed behavior into pytest.

### Required black-box coverage if retained

* control command bypass
* portless host auto-selection
* fixed host:port bypass
* write-output injection
* lock-fd cleanup
* fallback from locally locked `9473` to `9474`

### Validation

Run:

* `bash tests/oracle-plus-browser-remote-guard.sh`
* `uv run pytest`

---

## Task 15: Remove legacy bash wrapper reference surface

### Files

Remove or update:

* `output/oracle-plus.sh`
* any stale docs/tests/scripts referencing it

### Required checks

Run repository-wide search for stale references:

* `rg -n "oracle-plus\.sh|output/oracle-plus\.sh|ORACLE_WRAPPER" /home/user01/project/oracle`

Allowed remaining references only if intentionally documented as migration history. For final handoff, prefer zero matches for `output/oracle-plus.sh`.

The repository-wide source search should include source-bearing paths only:

* `README.md`
* `PORT_SELECTION.md`
* `live-SKILL.md`
* `output/SKILL.md`
* `skills/oracle-browser/SKILL.md`
* `scripts`
* `tests`

If `ORACLE_WRAPPER` remains only as a backward-compatible env var pointing to the Python CLI, document it explicitly. Otherwise remove it entirely in favor of `ORACLE_CLI`.

### Validation

Run:

* `rg -n "output/oracle-plus\.sh" README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md skills scripts tests`

Expected result:

* no matches

---

## Task 16: Full test and behavior validation

### Required commands

From `/home/user01/project/oracle`:

1. `uv sync`
2. `uv run pytest`
3. `bash tests/oracle-plus-browser-remote-guard.sh`
4. `rg -n "output/oracle-plus\.sh" README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md skills scripts tests`
5. `rg -n "SQLite|sqlite|database|db\.sqlite|\.db" src tests README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md`
6. `python -m compileall src`
7. `git diff --check`

### Expected results

* All pytest tests pass.
* Shell smoke guard passes if retained.
* No docs point to `output/oracle-plus.sh`.
* No SQLite/database design appears.
* Python files compile.
* No whitespace errors.

---

## Task 17: Optional live smoke validation

This task is optional because it requires the external Windows serve pool.

Preconditions:

* Windows serve pool is running on ports `9473-9479`.
* token is available or defaults to `1234abcd`.
* Python CLI has been installed with `uv sync`.

Suggested smoke cases:

1. Control command smoke:

   * `oracle-plus status <slug>`
   * verify no lock files are created.

2. Browser dry-run smoke:

   * browser mode
   * host-only remote host
   * verify selected `host:port` starts at `9473`.

3. Browser run smoke:

   * `--engine browser`
   * `--browser-model-strategy current`
   * `--wait`
   * explicit `--slug`
   * explicit `--write-output`
   * verify run-state `.meta` contains selected port and capture path.

4. Busy fallback smoke:

   * reserve or force busy on `9473`
   * verify fallback to next reachable port.
   * verify run-state records `fallback_reason`.

Do not make live smoke a prerequisite for unit-test completion unless the external serve pool is guaranteed available.

---

## Testing matrix

| Area                    | Test file                                          |
| ----------------------- | -------------------------------------------------- |
| Argument parsing        | `tests/oracle_plus/test_args.py`                   |
| Browser-mode detection  | `tests/oracle_plus/test_browser_mode.py`           |
| Control bypass          | `tests/oracle_plus/test_control_bypass.py`         |
| Host resolution         | `tests/oracle_plus/test_host_resolution.py`        |
| Port candidates/probing | `tests/oracle_plus/test_ports.py`                  |
| Flock behavior          | `tests/oracle_plus/test_locks.py`                  |
| Run-state `.meta`       | `tests/oracle_plus/test_run_state.py`              |
| Node CLI resolution     | `tests/oracle_plus/test_node_cli.py`               |
| Busy fallback           | `tests/oracle_plus/test_browser_fallback.py`       |
| Codex URL injection     | `tests/oracle_plus/test_codex_url.py`              |
| Write-output injection  | `tests/oracle_plus/test_write_output.py`           |
| Docs/helper migration   | `tests/oracle_plus/test_docs_no_legacy_wrapper.py` |
| Black-box smoke         | `tests/oracle-plus-browser-remote-guard.sh`        |

---

## Self-review checklist

Before handoff, verify:

* Python requirement is `>=3.12`.
* CLI is managed by `uv`.
* Node `@steipete/oracle` is still invoked through subprocess.
* No Python Playwright rewrite exists.
* No SQLite or alternate state store exists.
* Port locks still use `~/.cache/oracle-plus/ports/*.lock`.
* Port meta files still use `~/.cache/oracle-plus/ports/*.meta`.
* Run state still uses `~/.cache/oracle-plus/runs/<slug>.meta`.
* Run state is line-oriented `key: value`.
* Auto-selection still starts at `9473`.
* Auto-selection still ends at `9479`.
* Portless host still enters auto-selection.
* Fixed `host:port` still bypasses local lock and fallback.
* Control commands do not probe, lock, or write run state.
* Busy output releases lock and tries the next candidate.
* Non-busy Node failures do not continue to the next port.
* Codex Project URL injection happens only at port `9473`.
* Existing URL overrides prevent Codex Project URL injection.
* Existing `--remote-token` prevents duplicate token injection.
* Missing `--remote-token` gets default `1234abcd`.
* Missing `--write-output` gets auto capture only for real browser auto-selection runs.
* Child Node process cannot inherit lock fd.
* Skill docs point to the Python CLI.
* README and PORT_SELECTION point to the Python CLI.
* No final docs instruct agents to call `oracle-plus.sh`.

---

## Frozen handoff section

### Final deliverable

A Python 3.12+ `uv` project in:

`/home/user01/project/oracle`

with installed CLI:

`/home/user01/project/oracle/.venv/bin/oracle-plus`

The CLI must be behaviorally equivalent to the current bash wrapper for browser remote selection, local port locking, run-state tracking, fallback behavior, token injection, Codex URL injection, and control-command bypasses.

### Final validation commands

Run from `/home/user01/project/oracle`:

1. `uv sync`
2. `uv run pytest`
3. `bash tests/oracle-plus-browser-remote-guard.sh`
4. `rg -n "output/oracle-plus\.sh" README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md skills scripts tests`
5. `rg -n "SQLite|sqlite|database|db\.sqlite|\.db" src tests README.md PORT_SELECTION.md live-SKILL.md output/SKILL.md`
6. `python -m compileall src`
7. `git diff --check`

### Required final state

* All tests pass.
* No SQLite/database redesign appears.
* No browser automation rewrite appears.
* Docs and skill files point to the Python CLI.
* The old bash wrapper is not the documented entrypoint.
* The lock and run-state paths remain exactly compatible with existing operations.
* The implementation remains a wrapper around Node.js `@steipete/oracle`, not a replacement for it.
