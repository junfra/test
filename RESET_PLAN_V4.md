# Reset Plan v4 — Study Harness Learning Draft Reconstruction Upgrade

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (fresh rewrite)

## Artifact Type
Implementation plan (TDD-driven, bite-sized tasks)

## Revision Number
v4

## Next Draft Owner
main agent

## Goal
Produce an implementation plan where LearningDraftSystem preserves the Seed's exact ontology fields (topic, concept_layers, section_structure, recall_hooks, verification_points, bibliography), LMConfig is a separate model, and _build_learning_system wires config-loaded LM to fill the ontology.

## Rewrite Map

1. **Plan Brief** — Restate seed requirements, emphasize LearningDraftSystem ontology preservation
2. **Architecture** — LMConfig (separate), LearningDraftSystem (Seed ontology), config loading, LM client, prompt building, reconstruction engine, recall
3. **Task 0** — Branch baseline
4. **Task 1** — LMConfig model + failing tests (SEPARATE from LearningDraftSystem)
5. **Task 2** — LMConfig implementation
6. **Task 3** — Config loader (env var / file) + failing tests
7. **Task 4** — Config loader implementation
8. **Task 5** — Prompt builder + failing tests
9. **Task 6** — Prompt builder implementation
10. **Task 7** — LM client adapter + failing tests
11. **Task 8** — LM client adapter implementation
12. **Task 9** — LearningDraftSystem ontology (Seed fields) + failing tests
13. **Task 10** — LearningDraftSystem implementation
14. **Task 11** — Reconstruction engine (drafting.py) with config wiring + failing tests
15. **Task 12** — Reconstruction engine implementation
16. **Task 13** — Recall section extraction + failing tests
17. **Task 14** — Recall extraction implementation
18. **Task 15** — Integration tests
19. **Task 16** — Full test suite
20. **Task 17** — CLI smoke test
21. **Task 18** — Final verification

## Per-Section Instructions

### 1. Plan Brief
- Exact goal from seed
- LearningDraftSystem MUST have these exact fields: topic, concept_layers, section_structure, recall_hooks, verification_points, bibliography
- LMConfig is a SEPARATE model

### 2. Architecture
- `src/study/config.py` — config loading from env/file
- `src/study/lm_client.py` — LM client with OpenAI, Ollama, mock
- `src/study/prompt_builder.py` — prompt construction
- `src/study/drafting.py` — reconstruction engine using config-loaded LM
- `src/study/models.py` — LMConfig (separate) + LearningDraftSystem (Seed ontology)
- `src/study/recall.py` — recall extraction

### 3-21. Tasks
Each task follows TDD. Critical: LearningDraftSystem must have the EXACT Seed fields.

## Explicit Prohibitions
- NO redefining LearningDraftSystem with different fields
- NO omitting Seed ontology fields: topic, concept_layers, section_structure, recall_hooks, verification_points, bibliography
- NO hardcoded `LMConfig(provider="mock")` in production code
- NO deterministic template-based chapter generation as primary path
- NO raw source copy-paste in draft body
- NO template patterns: "Insert topic", "[Topic]", "{{topic}}"
- NO bare root path parameters
- NO weakening of approval gate

## Drafting Checks
1. LearningDraftSystem has all 6 Seed fields
2. LMConfig is a separate model
3. _build_learning_system uses config-loaded LM
4. Tests verify LM integration and ontology fields
5. No placeholder text
6. Every step has actual code
7. Exact file paths and commands specified

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`
- stopping_stalled_retries_ref: this skill output
- reset_brief_ref: `/tmp/reset_brief_v4.md`
- writing_reset_plan_ref: this file
- Revision Number: v4
- Next Draft Owner: main agent
- step2_draft_ref: (to be produced by main agent)
- normalization_ref: (to be produced after normalization)
- supervision_submission_ref: (to be produced after supervision)
- no_patch_attestation: true
