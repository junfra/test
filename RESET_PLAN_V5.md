# Reset Plan v5 — Study Harness LM Reconstruction Upgrade

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (fresh rewrite)

## Artifact Type
Implementation plan (TDD-driven, bite-sized tasks)

## Revision Number
v5

## Next Draft Owner
oracle

## Goal
Produce an implementation plan where the LM genuinely generates chapter content — not enriched templates. The primary path must be LM-driven; deterministic templates are only fallback on LM errors.

## Rewrite Map

1. **Plan Brief** — Restate seed requirements with emphasis on LM-driven chapter generation
2. **Architecture** — LMConfig, LearningDraftSystem (Seed ontology), config loading, LM client, prompt building, LM-driven chapter generation, fallback, recall
3. **Task 0** — Branch baseline
4. **Task 1** — LMConfig model + failing tests
5. **Task 2** — LMConfig implementation
6. **Task 3** — Config loader + failing tests
7. **Task 4** — Config loader implementation
8. **Task 5** — Prompt builder + failing tests
9. **Task 6** — Prompt builder implementation
10. **Task 7** — LM client adapter + failing tests
11. **Task 8** — LM client adapter implementation
12. **Task 9** — LearningDraftSystem ontology (Seed fields) + failing tests
13. **Task 10** — LearningDraftSystem implementation
14. **Task 11** — LM-driven chapter generation + failing tests
15. **Task 12** — LM-driven chapter generation implementation
16. **Task 13** — Fallback on LM errors + failing tests
17. **Task 14** — Fallback implementation
18. **Task 15** — Recall extraction + failing tests
19. **Task 16** — Recall extraction implementation
20. **Task 17** — Integration tests
21. **Task 18** — Full test suite
22. **Task 19** — CLI smoke test
23. **Task 20** — Final verification

## Per-Section Instructions

### 1. Plan Brief
- Exact goal from seed: "LM-driven concept reconstruction, not source paraphrase"
- LearningDraftSystem MUST have all 6 Seed fields
- LMConfig is separate
- **CRITICAL**: The LM must generate the actual chapter content, not enrich templates

### 2. Architecture
- `config.py` — env/file config loading
- `lm_client.py` — OpenAI, Ollama, mock providers
- `prompt_builder.py` — prompts for chapter generation
- `drafting.py` — LM-driven chapter generation (primary path), deterministic fallback (error only)
- `models.py` — LMConfig (separate) + LearningDraftSystem (Seed ontology)
- `recall.py` — recall extraction

### 3-23. Tasks
Each task follows TDD. **Critical**: Task 11-14 must show that the LM generates chapter content, not just enriches fields.

## Explicit Prohibitions
- NO deterministic _generate_* functions as the primary chapter generation path
- NO calling the LM only once for enrichment
- NO using LM output only to rewrite a single field
- NO claiming "LM-driven" while producing chapters from templates
- NO hardcoded `LMConfig(provider="mock")` in production code
- NO raw source copy-paste in draft body
- NO template patterns: "Insert topic", "[Topic]", "{{topic}}"
- NO bare root path parameters
- NO weakening of approval gate

## Drafting Checks
1. LearningDraftSystem has all 6 Seed fields
2. LMConfig is a separate model
3. _build_learning_system calls LM for each chapter
4. LM output fills the ontology fields
5. Fallback only on LM errors
6. Tests verify LM integration
7. No placeholder text
8. Every step has actual code

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`
- stopping_stalled_retries_ref: this skill output
- reset_brief_ref: `/tmp/reset_brief_v5.md`
- writing_reset_plan_ref: this file
- Revision Number: v5
- Next Draft Owner: oracle
- step2_draft_ref: (to be produced by oracle)
- normalization_ref: (to be produced after normalization)
- supervision_submission_ref: (to be produced after supervision)
- no_patch_attestation: true
