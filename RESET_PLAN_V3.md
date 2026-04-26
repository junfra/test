# Reset Plan v3 — Study Harness Learning Draft Reconstruction Upgrade

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (fresh rewrite)

## Artifact Type
Implementation plan (TDD-driven, bite-sized tasks)

## Revision Number
v3

## Next Draft Owner
oracle

## Goal
Produce an implementation plan where the draft generation engine actually uses the configured LM provider through the full call chain — no hardcoded mock in production code.

## Rewrite Map

1. **Plan Brief** — Restate seed requirements with emphasis on LM provider configuration
2. **Architecture** — Config loading, LM client wiring, prompt building, chapter generation, fallback
3. **Task 0** — Branch baseline
4. **Task 1** — LM config model + failing tests
5. **Task 2** — LM config model implementation
6. **Task 3** — Config loader (env var / file) + failing tests
7. **Task 4** — Config loader implementation
8. **Task 5** — Prompt builder + failing tests
9. **Task 6** — Prompt builder implementation
10. **Task 7** — LM client adapter + failing tests
11. **Task 8** — LM client adapter implementation
12. **Task 9** — Reconstruction engine (drafting.py) with PROPER config wiring + failing tests
13. **Task 10** — Reconstruction engine implementation
14. **Task 11** — Recall section extraction + failing tests
15. **Task 12** — Recall extraction implementation
16. **Task 13** — Integration tests
17. **Task 14** — Full test suite
18. **Task 15** — CLI smoke test
19. **Task 16** — Final verification

## Per-Section Instructions

### 1. Plan Brief
- Exact goal from seed with emphasis on LM-driven reconstruction
- Scope boundaries, constraints, acceptance criteria
- Explicit prohibitions including "no hardcoded mock provider in production code"

### 2. Architecture
- Config loading: `src/study/config.py` that reads from env vars (STUDY_LM_PROVIDER, STUDY_LM_API_KEY, etc.) or config file
- LM client: `src/study/lm_client.py` with OpenAI, Ollama, mock providers
- Prompt builder: `src/study/prompt_builder.py`
- Reconstruction engine: `drafting.py` that uses config-loaded LM
- Models: `models.py` with LMConfig, LearningDraftSystem
- Recall: `recall.py` updated for reconstructed sections

### 3-19. Tasks
Each task follows TDD pattern. Critical: Task 9+ must show that `_build_learning_system` reads config and passes it to LMClient, not hardcoded mock.

## Explicit Prohibitions
- NO hardcoded `LMConfig(provider="mock")` in production code paths
- NO deterministic template-based chapter generation as the primary path
- NO fixed paragraph templates or static prose blocks
- NO keyword-only concept extraction without LM involvement
- NO tests that only check character count and header presence
- NO raw source copy-paste in draft body
- NO template patterns: "Insert topic", "[Topic]", "{{topic}}"
- NO bare root path parameters
- NO weakening of approval gate

## Drafting Checks
1. Every task follows TDD
2. The LM integration is real and wired through config
3. `_build_learning_system` uses config-loaded LM, not hardcoded mock
4. Tests verify LM integration works with mock provider
5. Tests verify config loading from env vars
6. Tests validate conceptual quality
7. No placeholder text
8. Every step contains actual code
9. Exact file paths and commands specified

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`
- stopping_stalled_retries_ref: this skill output
- reset_brief_ref: `/tmp/reset_brief_v3.md`
- writing_reset_plan_ref: this file
- Revision Number: v3
- Next Draft Owner: oracle
- step2_draft_ref: (to be produced by oracle)
- normalization_ref: (to be produced after normalization)
- supervision_submission_ref: (to be produced after supervision)
- no_patch_attestation: true (this plan is not a patch of the failed artifact)
