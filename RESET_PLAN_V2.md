# Reset Plan v2 — Study Harness Learning Draft Reconstruction Upgrade

## Target Artifact
`/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md` (fresh rewrite)

## Artifact Type
Implementation plan (TDD-driven, bite-sized tasks)

## Revision Number
v2

## Next Draft Owner
main agent

## Goal
Produce an implementation plan for upgrading the study-harness `drafting.py` to use a real LM API (configurable, with OpenAI as default) that performs genuine concept extraction and reconstruction from source material, producing dense multi-chapter guides with per-chapter concept reconstruction, learning model, recall hooks, and verification points — with tests that validate non-derivative synthesis quality.

## Rewrite Map

1. **Plan Brief** — Restate seed requirements, scope, constraints, and acceptance criteria
2. **Architecture** — LM integration layer, prompt engineering, structured output parsing, fallback
3. **Task 0** — Branch baseline
4. **Task 1** — LM config model + failing tests
5. **Task 2** — LM config model implementation
6. **Task 3** — Prompt builder for concept extraction + failing tests
7. **Task 4** — Prompt builder implementation
8. **Task 5** — LM client adapter + failing tests
9. **Task 6** — LM client adapter implementation
10. **Task 7** — Reconstruction engine (drafting.py rewrite) + failing tests
11. **Task 8** — Reconstruction engine implementation
12. **Task 9** — Recall section extraction update + failing tests
13. **Task 10** — Recall extraction implementation
14. **Task 11** — Integration tests
15. **Task 12** — Full test suite
16. **Task 13** — CLI smoke test
17. **Task 14** — Final verification

## Per-Section Instructions

### 1. Plan Brief
- Exact goal from seed: "Upgrade so every generated learning draft is an LM-driven concept reconstruction, not source paraphrase, and consistently delivers Red Hat-style structure and dense explanations"
- Scope boundaries: target repo, branch, primary files
- Constraints: subject_root API, click CLI, pydantic v2, approval gate, 3000+ chars, no raw source in body
- Acceptance criteria: 3+ substantive chapters, per-chapter structure (Concept Reconstruction, Learning Model, Recall Hooks, Verification Points), density, bibliography-only source references, approval gate preserved, tests
- Explicit prohibitions: no template patterns, no bare root paths, no weakening approval gate, no CLI signature changes

### 2. Architecture
- LM integration layer: `src/study/lm_client.py` with configurable provider (OpenAI default, mock for testing)
- Prompt builder: `src/study/prompt_builder.py` that constructs concept extraction prompts from source content
- Structured output parser: parses LM response into `LearningDraftSystem` ontology
- Reconstruction engine: `drafting.py` rewritten to use LM for concept extraction + chapter generation
- Fallback: graceful degradation when LM unavailable (use deterministic extraction as last resort)
- Models: `LearningDraftSystem` ontology in `models.py`
- Recall: `recall.py` updated to extract reconstructed sections

### 3-17. Tasks
Each task must follow TDD pattern:
- Write failing test first
- Run test to verify failure
- Write minimal implementation
- Run test to verify pass
- Commit

## Explicit Prohibitions
- NO deterministic template-based chapter generation (the v1 failure)
- NO fixed paragraph templates or static prose blocks
- NO keyword-only concept extraction without LM involvement
- NO tests that only check character count and header presence
- NO assumption that string concatenation constitutes "concept reconstruction"
- NO raw source copy-paste in draft body
- NO template patterns: "Insert topic", "[Topic]", "{{topic}}"
- NO bare root path parameters
- NO weakening of approval gate

## Drafting Checks
Before submitting for supervision, verify:
1. Every task follows TDD (test → fail → implement → pass → commit)
2. The LM integration is real (OpenAI API call or equivalent), not simulated
3. Tests validate conceptual quality (non-derivative synthesis), not just structure
4. The plan addresses all seed acceptance criteria
5. No placeholder text ("TBD", "TODO", "implement later")
6. Every step contains actual code, not descriptions
7. Exact file paths and commands are specified
8. The architecture includes fallback behavior

## Lineage Evidence Inputs
- failed_artifact_ref: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN_RECONSTRUCTION.md`
- stopping_stalled_retries_ref: this skill output
- reset_brief_ref: `/tmp/reset_brief.md`
- writing_reset_plan_ref: this file
- Revision Number: v2
- Next Draft Owner: main agent
- step2_draft_ref: (to be produced after this plan)
- normalization_ref: (to be produced after normalization)
- supervision_submission_ref: (to be produced after supervision)
- no_patch_attestation: true (this plan is not a patch of the failed artifact)
