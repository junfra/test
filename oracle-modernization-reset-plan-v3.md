# Oracle-Plus Python CLI Modernization Reset Plan v3

**Target Artifact:** `oracle-modernization-plan-v3.md`

**Artifact Type:** writing plan

**Revision Number:** `v3`

**Next Draft Owner:** `oracle`

**Goal:** Draft a fresh implementation plan for the Oracle-Plus modernization that keeps the Python CLI migration, the wrapper compatibility policy, and the source-bearing docs/helper updates, while ending with a true implementation handoff instead of a reset-plan-style closing note.

## Rewrite Map

1. Contract and scope lock
2. File map and ownership
3. Task breakdown for the Python CLI migration
4. Docs/helper migration and source-bearing validation
5. Final implementation handoff

## Per-Section Instructions

### 1. Contract and scope lock
- Preserve the seed goal and the exact lock/run-state semantics.
- Preserve the Python CLI entrypoint path and the Node subprocess model.
- State that the legacy shell wrapper is not required to be deleted.
- State that if the shell wrapper remains, it is only compatibility surface and is not the documented entrypoint.

### 2. File map and ownership
- List the Python package files, tests, docs, helper scripts, and source skill-doc copies that must change.
- Include `skills/oracle-browser/SKILL.md`.
- Keep backup/run-history directories out of source-validation scope.

### 3. Task breakdown for the Python CLI migration
- Preserve the task coverage for args/config, host/ports/locks/run-state, Node CLI resolution, browser orchestration, and top-level CLI routing.
- Keep the tests-first structure.
- Preserve the seed acceptance criteria exactly.
- Keep compatibility-surface handling for `output/oracle-plus.sh` optional, not mandatory.

### 4. Docs/helper migration and source-bearing validation
- Update README, port-selection docs, helper scripts, and the source skill docs to point at the Python CLI.
- Include `skills/oracle-browser/SKILL.md` in the doc migration scope.
- Make the legacy-reference search cover only source-bearing paths.
- Do not require cleaning backup/run-history artifacts.

### 5. Final implementation handoff
- The fresh artifact must end with a real implementation handoff.
- The handoff must say the required implementation entry is `superpowers:subagent-driven-development`.
- The handoff must not refer back to the reset plan or say the artifact is itself a reset plan.
- The handoff must preserve the task-by-task TDD obligation.

## Explicit Prohibitions

- Do not carry forward any terminal note that says “this reset plan is complete.”
- Do not carry forward any backward-looking handoff to another reset step.
- Do not carry forward any mandatory deletion of `output/oracle-plus.sh`.
- Do not carry forward any repo-wide zero-match legacy search that includes backup or run-history artifacts.

## Drafting Checks

- The fresh artifact must preserve every seed requirement.
- The fresh artifact must keep the legacy wrapper as optional compatibility surface, not as a required deletion target.
- The fresh artifact must include `skills/oracle-browser/SKILL.md` in the docs migration scope.
- The fresh artifact must end with a real implementation handoff to `superpowers:subagent-driven-development`.
- The fresh artifact must not describe itself as a reset plan.
- The fresh artifact must keep source-bearing validation realistic and bounded.

## Lineage Evidence Inputs

- `failed_artifact_ref`: `oracle-modernization-plan-v2.md`
- `stopping_stalled_retries_ref`: `stopping-stalled-retries-v3.md`
- `reset_brief_ref`: `reset-brief-v3.md`
- `writing_reset_plan_ref`: `oracle-modernization-reset-plan-v3.md`
- `Revision Number`: `v3`
- `Next Draft Owner`: `oracle`
- `step2_draft_ref`: `oracle-modernization-plan-v3.md`
- `oracle_draft_session_ref`: fresh `oracle-browser` session for the Step 2 draft
- `normalization_ref`: repo-local normalization of `oracle-modernization-plan-v3.md`
- `supervision_submission_ref`: oracle-backed outside-in supervision submission for `oracle-modernization-plan-v3.md`
- `no_patch_attestation`: `true`

## Step 1 Result

This reset plan is complete and ready for the oracle Step 2 draft of `oracle-modernization-plan-v3.md`.
