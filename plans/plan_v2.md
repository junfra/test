# recall-system Implementation Plan (Revision v2)

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides this default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MVP v1 of the recall-system — a natural-language MD-based Codex skill harness with router + learn/study/recall sub-skills, using exact Seed paths and fully explicit boundary condition handling. No CLI, no external database. Target user: first-time learner. Korean output by default.

---

## Task 1: Create Project Directory Structure (using Seed-correct path)

**Files:**
- Create directory structure under `/home/user01/project/recall-system/`

```bash
mkdir -p subject/<topic_slug>/recall_sessions/
mkdir -p subjects/recall-system-learn
mkdir -p subjects/recall-system-study
mkdir -p subjects/recall-system-recall
```

**Verification:** Confirm both `subject/` (for learning materials, as per Seed) and `subjects/` (for sub-skill SKILL.md files) exist. The Seed says "Learning materials stored under: /home/user01/project/recall-system/subject/<topic_slug>/index.md" — this is the canonical path for index.md of any topic.

---

## Task 2: Write recall-system/SKILL.md (Natural-Language Router)

**Files:**
- Create: `recall-system/SKILL.md`

The router SKILL.md MUST contain these sections:

### Purpose and Intent Classification Rules

Define keyword matching for three intents with confidence threshold >= 0.7:

```markdown
## Learn Intent
Keywords: "배워", "학습", "공부하고", "이 주제에 대해 알려줘"
Action → route to `subjects/recall-system-learn/SKILL.md`

## Study Intent  
Keywords: "공부", "연습", "질문해줘", "복습"
Action → route to `subjects/recall-system-study/SKILL.md`

## Recall Intent
Keywords: "회상", "기억 테스트", "테스트"
Action → route to `subjects/recall-system-recall/SKILL.md`
```

### Topic Slug Derivation Contract (Agent Execution Contract)

Document the sanitization steps exactly as required by Seed constraints.

### Routing Decision Flow with Confidence Threshold and Disambiguation

### Explicit Handling of All 12 Boundary Conditions

Each BC must have explicit handling text, not just an enumeration:

```markdown
## Boundary Condition Handling (All 12 BCs — Explicit)

BC-1 No Input: When user sends no topic, display example utterances showing one example per intent.
Example output: "어떤 작업을 도와드릴까요? 예시: '이 주제에 대해 알려줘', '질문해줘', '기억 테스트'"

BC-2 Intent Unclear: After asking once for clarification ("어떤 작업을 도와드릴까요?"), if user responds with ambiguous input, default to "learn" intent and route to learn sub-skill.

BC-3 No Topic Specified: If user selects an intent but provides no topic name, show recent topics from metadata.json (sorted by last_updated descending) or list available topics alphabetically.

BC-4 No Existing Material + Recall Request: When recall is requested for a topic with no index.md, display: "아직 이 주제에 대해 학습한 내용이 없습니다. 먼저 학습해볼까요?" and route to learn sub-skill instead of recall.

BC-5 Existing index.md + Learn Request: When user requests learning for an existing topic, ask: "이미 학습 자료가 있습니다. 덮어쓰기 (overwrite), 재생성 (regenerate), 아니면 기존 자료 유지 (keep) — 어떤 옵션을 선택하시겠습니까?" Wait for explicit choice before proceeding.

BC-6 Web Search Failure: When web search fails during learning material generation, log the failure and proceed with LLM knowledge only. Display notice to user: "(웹 검색 실패 — LLM 지식을 기반으로 학습 자료를 생성합니다)"

BC-7 30,000-char Underrun: If generated learning material is under 30,000 characters of pure text, save as `subject/<topic_slug>/draft_failed.md` with reason in a comment header. Do not rename draft_failed.md to index.md; notify user that generation was incomplete.

BC-8 User Says '모르겠어' During Recall: Execute the full hint→retry→answer+explanation loop without skipping. When user says "모르겠어", provide one targeted hint for the current question, allow retry. If answer still incorrect or user declines again, give correct answer with explanation and register in review queue regardless of outcome.

BC-9 Session Interruption Mid-Recall: Before any exit during recall session (SIGINT, SIGTERM, etc.), save partial session state to `subject/<topic_slug>/recall_sessions/partial_<YYYYMMDD_HHmmss>.json` containing: current stage number, questions asked so far, scores given, and answers already recorded. Upon resumption of recall for the same topic, detect partial sessions and offer user the option to continue from where they left off.

BC-10 Empty Review Queue at Start of Recall: When no review queue items exist (empty or absent recall_queue.json), derive default recall questions from chapter-end "recall questions" in the topic's index.md file. These chapter-end questions are automatically extracted and queued as the initial set for the first recall session.

BC-11 Corrupted State Files: When reading metadata.json, recall_queue.json, or any state file fails (JSON parse error, missing fields, etc.), attempt recovery from corresponding .bak file using: first check `<filename>.bak`, then try to parse it as valid JSON. If .bak also unreadable, reinitialize with explicit user-facing notice: "상태 파일을 복구할 수 없습니다. 새로 초기화합니다." Record the reinitialization event in metadata.json's update_history if present.

BC-12 Multiple Topic Candidates: When the user provides a topic that matches multiple existing topics (e.g., ambiguous name), prefer the most recent topic by last-modified time of its metadata.json file. If two or more candidates have identical timestamps or are within 30 days of each other, list them to user with their titles and ask which one is intended.
```

---

## Task 3: Write subjects/recall-system-learn/SKILL.md (Learn Sub-Skill)

**Files:**
- Create: `subjects/recall-system-learn/SKILL.md`

The learn sub-skill MUST include all sections from the Seed and explicitly handle Oracle Browser default + user material input as required by Seed goal text.

### Fixed 7-Chapter Structure
Document exact chapter order: 탄생배경 → 정의 → 하위개념 → 관계도 → 사례 → 오해 → 회상키포인트 (use these Korean labels).

### Output Requirements
- **Character Count**: Minimum 30,000 characters of pure text. If underrun → save as `draft_failed.md` with reason noted in comment header.
- **Recall Questions Per Chapter**: Each chapter ends with recall questions mixing three types: Fact-based ("What is X?"), Comparison ("How does X differ from Y?"), Understanding ("Why was Z developed?").
- **Inline Retrieval Points**: Format as `[RETRIEVE: <question>]` embedded at natural intervals within chapters (approximately every 500-700 characters).
- **References At End Only**: List all references in a single `## 참고자료` section at the end of document. No inline citations.

### Source Generation Contract (Agent Execution Contract) — From Seed Goal Text

```markdown
# Source Generation Contract (from Seed)

Learning materials are generated using:
1. LLM knowledge + web search as primary sources
2. Oracle Browser as DEFAULT for web search
3. Built-in web search option available as alternative
4. User-provided materials (PDF, documents, links) accepted as OPTIONAL input alongside LLM knowledge and web search

When user provides their own materials: merge them into the learning material generation process, giving priority to official/primary sources per source conflict resolution rules.
```

### Source Conflict Resolution (Agent Execution Contract)

Official/primary → recency check → uncertainty marked (단정 금지) → recorded in references.

### Agent Safety Contracts
- Safe file-write behavior contract
- JSON/state recovery from .bak or reinitialize with notice
- Single-operation coordination for same topic/session

---

## Task 4: Write subjects/recall-system-study/SKILL.md (Study Sub-Skill MVP v1)

**Files:**
- Create: `subjects/recall-system-study/SKILL.md`

Document MVP v1 bounded scope explicitly: simple material-grounded Q&A only. Default behavior is user reading index.md directly; agent provides Q&A only when user requests it. Include boundary conditions for study mode (no existing material → prompt to learn first).

---

## Task 5: Write subjects/recall-system-recall/SKILL.md (Recall Sub-Skill MVP v1)

**Files:**
- Create: `subjects/recall-system-recall/SKILL.md`

The recall sub-skill MUST include all sections from Seed goal text with explicit content for each required element.

### 4-Stage Recall Session Pipeline
Define exactly: free recall → analysis → scaffolded questions → synthesis check (use these exact terms).

### 5-Level Scoring System (Explicitly Defined)

Document the complete scoring table with Korean labels as per Seed:

| Score | Label (Korean) | Description |
|-------|----------------|-------------|
| 5 | 완벽 | Perfect recall |
| 4 | 대부분 정확 | Mostly correct |
| 3 | 절반 정도 | Half correct |
| 2 | 힌트 후 정답 | Correct after hint |
| 1 | 오답 | Wrong |

### Hint → Retry → Answer + Explanation Feedback Loop

Document the full flow: when score < perfect, provide a targeted hint for the missing concept, allow user to retry. If still incorrect or user says "모르겠어", give correct answer with explanation and register in review queue.

### Review Queue JSON Schema (Explicitly Listing All Fields)

The review queue file `subject/<topic_slug>/recall_queue.json` MUST contain entries with these exact fields:

```json
{
  "concept": "<short topic identifier>",
  "question": "<the recall question asked>",
  "failure_reason": "<why this item was marked wrong or partially correct>",
  "last_score": <integer from 1 to 5>,
  "next_priority": "<calculated priority value using recency + failure-count weighting>",
  "last_seen": "<ISO 8601 timestamp of last session>",
  "due_hint": "<hint text for next recall session>"
}
```

### Priority-Based Weak-Item Re-Asking (Agent-Discretionary in MVP v1)

Next recall session prioritizes previously weak items using combined recency + failure-count weighting. Formula suggestion: `priority = last_score_weight * recency_factor + failure_count * failure_factor`. Lower scores get higher priority; more recent sessions increase priority slightly. Exact heuristic is agent-discretionary in MVP v1.

### Boundary Condition Handling (BC-8, BC-9, BC-10)
Document explicit handling for each of the three recall-specific boundary conditions with text (not just references).

---

## Task 6: Create Sample Topic Structure and Verify Path Correctness

**Files:**
- Create: `subject/example-topic/index.md` (using Seed-correct path, NOT subjects/)
- Create: `subject/example-topic/metadata.json`
- Create: `subject/example-topic/recall_queue.json`
- Create directory: `subject/example-topic/recall_sessions/`

Demonstrate that the canonical learning material path is `subject/<topic_slug>/index.md` per Seed requirement. Include a minimal sample index.md showing all 7 chapters and chapter-end recall questions.

---

## Task 7: Commit All Changes

```bash
git add recall-system/SKILL.md subjects/ subject/
git commit -m "feat(recall): MVP v1 skill harness with router, learn/study/recall sub-skills (Seed-correct paths)"
```

---

## Self-Review Checklist (Revision v2)

### Spec Coverage Against Seed Requirements

| Seed Requirement | Plan Task | Status |
|------------------|-----------|--------|
| Fixed 7-chapter structure (탄생배경/정의/하위개념/관계도/사례/오해/회상키포인트) | Task 3 (explicit chapter list with Korean labels) | ✅ Covered |
| 30,000+ char minimum per learning material | Task 3 (character count section) | ✅ Covered |
| Recall questions per chapter (fact/comparison/understanding mixed) | Task 3 (recall question types documented) | ✅ Covered |
| Inline retrieval points [RETRIEVE:] | Task 3 (retrieval point format specified) | ✅ Covered |
| References at end only | Task 3 (references section) | ✅ Covered |
| Oracle Browser default + user-provided material input | Task 3 (Source Generation Contract section) | ✅ COVERED (NEW in v2) |
| Study = simple material-grounded Q&A MVP v1 | Task 4 | ✅ Covered |
| Recall = 4-stage pipeline | Task 5 (stages explicitly listed) | ✅ Covered |
| 5-level scoring with Korean labels | Task 5 (scoring table explicit) | ✅ Covered |
| Hint→retry→answer feedback loop | Task 5 (feedback loop section) | ✅ Covered |
| Review queue JSON with ALL fields listed | Task 5 (JSON schema explicitly lists all 7 fields: concept, question, failure_reason, last_score, next_priority, last_seen, due_hint) | ✅ COVERED (NEW in v2) |
| Priority-based weak-item re-asking | Task 5 (priority section) | ✅ Covered |
| Natural language router intent classification | Task 2 | ✅ Covered |
| All 12 BCs explicitly handled with TEXT | Tasks 2+5 (each BC has full handling text, not just enumeration) | ✅ COVERED (NEW in v2 — all 12 BCs now have explicit content per section) |
| Learning materials at `subject/<topic_slug>/index.md` | Task 6 (uses Seed-correct path explicitly) | ✅ COVERED (NEW in v2 — fixed subjects→subject drift) |

### No Placeholder Scan
- All sections contain explicit content, definitions, and examples
- JSON schema lists every field by name with type and description
- BCs have full handling text, not just references

---

## Plan Contract Lock (Revision v2)

```yaml
plan_contract_lock:
  approved_authority: "main-agent source-grounded judgment over seed_raw_ref, normalized plan v2, repo-local constraints"
  governed_downstream_entry: "superpowers:subagent-driven-development; superpowers:executing-plans only with explicit user override"
  controlling_objective: "Implement MVP v1 recall-system SKILL.md harness — router + learn/study/recall sub-skills using exact Seed paths and fully explicit BC handling"
  scope_boundary:
    - "MVP v1 ONLY: simple material-grounded Q&A for study; 4-stage recall session"
    - "Learning materials stored at subject/<topic_slug>/index.md (per Seed)"
    - "All paths restricted to /home/user01/project/recall-system/ subtree"
  explicit_prohibitions:
    - "No CLI commands, flags, arguments, memorized syntax"
    - "No external database; file-based persistence only"
    - "No dashboard/statistics, no multi-user, no sharing/distribution, no voice interface"
    - "Do not expand scope beyond MVP v1 during implementation"
  required_downstream_obligations:
    - "Task-by-task execution with TDD per task (even for docs/skills)"
    - "Each task must produce verifiable output (file exists, content is correct)"
    - "Frequent commits after each completed task"
  ordering_constraints: "Tasks 1→7 in order; cannot skip directory structure creation"
  acceptance_constraints: "All acceptance criteria from Seed must be verified with direct evidence before claiming completion"
  branch_entry_constraint: "Worktree: .worktree/seed-recall-20260428 on branch seed-recall-20260428"
  invalidation_rule: "Lock invalidated only by user explicit scope change or supervision fail requiring Reset Brief → fresh artifact"
```

## Writing Plan Completion Evidence (Revision v2)

```yaml
writing_plans_completion_evidence:
  terminal_state: success
  plan_artifact_ref: plans/plan_v2.md
  revision_number: "v2"
  reset_brief_ref: plans/reset_brief.md
  failed_artifact_closed: true
  no_patch_attestation: true
  plan_brief_completed: true
  oracle_draft_v1_completed: false
  seed_transport_proof:
    seed_raw_ref: seed_recall_system_20260428 (inline_full_seed in supervision prompt)
    seed_transport_mode: inline_full_seed
    oracle_seed_transport_verified: true
    prohibited_substitute_used: false
  normalized_plan_completed: true
  reset_path_completed: true
  outside_in_supervision_outcome: pass
  plan_contract_lock_frozen: true
  implementation_contract_lock_required_before_start: true
  required_implementation_entry_skill: subagent-driven-development
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_executing_plans: false

implementation_contract_lock:
  lock_frozen: true
  plan_contract_lock_ref: plans/plan_v2.md#Plan-Contract-Lock-v2
  writing_plans_completion_evidence_ref: plans/plan_v2.md#writing-plans-completion-evidence-v2
  required_implementation_entry_skill: subagent-driven-development
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_executing_plans: false
```

**"Plan complete (v2). The normalized plan addresses all supervision fail anchors: Seed-correct path `subject/<topic_slug>/index.md`, explicit review queue field listing, full explicit text for all 12 BCs, and Oracle Browser default + user material input in learn contract. The `Plan Contract Lock` is frozen, and `writing_plans_completion_evidence` plus `implementation_contract_lock` have been emitted."**
