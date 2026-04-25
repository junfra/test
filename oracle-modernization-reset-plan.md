# Oracle-Plus Python CLI Modernization Reset Plan

**Target Artifact:** `oracle-modernization-plan-v2.md`

**Artifact Type:** writing plan

**Revision Number:** `v2`

**Next Draft Owner:** `main agent`

**Goal:** Draft a fresh implementation plan for the Oracle-Plus modernization that preserves the Python 3.12+ `uv` CLI migration, the wrapper-compatible behavior, and the docs/helper updates, while no longer requiring deletion of the legacy shell wrapper as a contract-level outcome.

## Rewrite Map

1. Contract and scope lock
2. File map and ownership
3. Python CLI implementation tasks
4. Helper script and documentation migration tasks
5. Validation and handoff

## Per-Section Instructions

### 1. Contract and scope lock
- State the seed goal exactly: modernize the bash wrapper into a Python `uv` CLI while preserving the browser-mode wrapper contract.
- Preserve the exact port-lock and run-state paths from the current bash wrapper.
- Preserve the Node.js `@steipete/oracle` subprocess model.
- State that the documented entrypoint moves to the Python CLI.
- State that the legacy shell wrapper may remain as a compatibility surface unless explicitly retired later, but it is not a required deletion in this plan.

### 2. File map and ownership
- List the Python package files to create.
- List the source docs and helper scripts to modify.
- Include `skills/oracle-browser/SKILL.md` as part of the source-bearing docs migration scope because it still references the old wrapper.
- Do not list backup or run-history artifacts as source files to be cleaned for success.

### 3. Python CLI implementation tasks
- Keep the task breakdown focused on CLI skeleton, args helpers, host resolution, port probing, lock semantics, run-state writer, Node CLI resolution, browser orchestration, and top-level routing.
- Preserve the seed acceptance criteria exactly.
- Do not introduce SQLite or any new state store.
- Do not require deleting the legacy shell wrapper as a milestone.

### 4. Helper script and documentation migration tasks
- Update `README.md`, `PORT_SELECTION.md`, `live-SKILL.md`, `output/SKILL.md`, and `skills/oracle-browser/SKILL.md` so they point to the Python CLI.
- Update `scripts/oracle-env.sh` and `scripts/oracle-remote-host.sh` to call the Python CLI path.
- Keep `scripts/sync-skill-docs.sh` in the migration scope only if it needs to propagate the repo-local skill copy; otherwise do not invent extra changes.
- Ensure tests cover the migration of source-bearing docs and helper scripts, not historical backups or run artifacts.

### 5. Validation and handoff
- Keep the validation focused on source-bearing paths.
- Exclude backup/history directories from zero-legacy-reference checks unless a future explicit cleanup is requested.
- Require that the final plan and handoff still verify the Python CLI path, the wrapper-compatible behavior, and the seed acceptance criteria.
- Emit a clear implementation handoff that still points to task-by-task TDD execution.

## Explicit Prohibitions

- Do not carry forward any mandatory deletion of `output/oracle-plus.sh`.
- Do not carry forward any repo-wide zero-match search that includes backup or run-history artifacts.
- Do not carry forward any plan that treats wrapper retirement as the only acceptable end state.
- Do not carry forward any SQLite or browser automation rewrite.

## Drafting Checks

- The fresh artifact must preserve every seed requirement.
- The fresh artifact must treat the Python CLI as the documented entrypoint.
- The fresh artifact must keep the legacy wrapper as optional compatibility surface, not as a mandatory removal target.
- The fresh artifact must mention `skills/oracle-browser/SKILL.md` in the docs migration scope.
- The fresh artifact must scope legacy-reference validation to source-bearing paths only.
- The fresh artifact must still support task-by-task TDD and the same lock/run-state semantics.

## Lineage Evidence Inputs

- `failed_artifact_ref`: `oracle-modernization-plan.md`
- `stopping_stalled_retries_ref`: this file's parent reset-stop
- `reset_brief_ref`: `reset-brief.md`
- `writing_reset_plan_ref`: `oracle-modernization-reset-plan.md`
- `Revision Number`: `v2`
- `Next Draft Owner`: `main agent`
- `step2_draft_ref`: `oracle-modernization-plan-v2.md`
- `normalization_ref`: repo-local normalization of `oracle-modernization-plan-v2.md`
- `supervision_submission_ref`: oracle-backed outside-in supervision submission for `oracle-modernization-plan-v2.md`
- `no_patch_attestation`: `true`

## Step 1 Result

This reset plan is complete and ready for Step 2 drafting of `oracle-modernization-plan-v2.md`.
