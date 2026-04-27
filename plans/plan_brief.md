# Plan Brief: Recall System (Seed v1)

## Goal
Build an MD-based Codex skill harness system ("recall-system") that routes natural-language user requests into learn, study, and recall sub-skills. MVP v1 scope:
- Learn: Generate 30,000+ char learning material with fixed 7-chapter structure (탄생배경 → 정의 → 하위개념 → 관계도 → 사례 → 오해 → 회상키포인트), recall questions per chapter, inline retrieval points
- Study: Material-grounded Q&A
- Recall: 4-stage session (free recall → analysis → scaffolded questions → synthesis check) with hint→retry→answer+explanation loop and 5-level scoring

## Scope Boundary
- Natural-language router (SKILL.md only; no CLI/flags/args)
- Sub-skill SKILL.md files for learn/study/recall
- File-based persistence: `subject/<topic_slug>/index.md`, metadata.json, recall_queue.json
- Subject directory structure under `/home/user01/project/recall-system/subjects/`

## Explicit Prohibitions (Non-Goals)
- No CLI commands, flags, arguments, or memorized syntax
- No external database; file-based persistence only
- No dashboard/statistics, no multi-user, no sharing/distribution, no voice interface
- No rich explanation, analogy, and verification beyond MVP v1 Q&A scope

## Repo-Local Constraints
- Project root: `/home/user01/project/recall-system/`
- All paths restricted to this subtree
- topic_slug must be sanitized (no path separators, traversal, whitespace, control chars)
- Korean language as default output
- SKILL.md files define safe file-write behavior as agent execution contracts
- JSON/state recovery: recover from .bak when available, reinitialize with notice otherwise
- Single-operation coordination for same topic/session

## Required Files
1. `recall-system/SKILL.md` — Natural-language router
2. `recall-system/subjects/recall-system-learn/SKILL.md` — Learn sub-skill
3. `recall-system/subjects/recall-system-study/SKILL.md` — Study sub-skill
4. `recall-system/subjects/recall-system-recall/SKILL.md` — Recall sub-skill

## 12 Boundary Conditions (confirmed)
1. No input → show example commands
2. Intent unclear → ask once for clarification
3. No topic → show recent or list topics
4. No existing material + recall request → suggest learn first
5. Existing index.md + learn request → ask overwrite/regenerate/keep
6. Web search failure → log failure, proceed with LLM knowledge
7. 30,000-char underrun → save as draft_failed.md with reason
8. User says '모르겠어' during recall → hint→retry→answer+explanation→queue
9. Session interruption mid-recall → save as partial session
10. Empty review queue → start with index.md default recall questions
11. Corrupted state files → restore from .bak or reinitialize
12. Multiple topic candidates → prefer recent, list if ambiguous
