# recall-system Implementation Plan (Revision v3)

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides this default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MVP v1 of the recall-system — a natural-language MD-based Codex skill harness with router and three sub-skills (learn, study, recall), using exact Seed paths and fully explicit boundary condition handling in plan text. No CLI, no external database. Target user: first-time learner. Korean output by default.

---

## Task 1: Create Project Directory Structure (Seed-correct paths)

**Files:**
- Create directory structure under `/home/user01/project/recall-system/` using Seed-specified paths:

```bash
# Skill harness directories (per Seed constraint: "recall-system/SKILL.md is the natural-language router, and it routes user intent to recall-system-learn/SKILL.md...")
mkdir -p recall-system
mkdir -p recall-system/recall-system-learn
mkdir -p recall-system/recall-system-study
mkdir -p recall-system/recall-system-recall

# Learning material storage directory (per Seed constraint: "Learning materials stored under: /home/user01/project/recall-system/subject/<topic_slug>/index.md")
mkdir -p subject/example-topic/recall_sessions
```

**Verification:** Confirm structure matches Seed-specified paths: skill files at `recall-system/{router,learn,study,rec}/` and learning materials at `subject/<topic_slug>/`.

---

## Task 2: Write recall-system/SKILL.md (Natural-Language Router)

**Files:**
- Create: `recall-system/SKILL.md`

### Purpose and Intent Classification Rules

```markdown
# Recall System — Natural Language Router

## Purpose
Route natural-language requests to the appropriate sub-skill.

## Intent Classification Rules

### Learn Intent
Keywords (Korean): "배워", "학습", "공부하고", "이 주제에 대해 알려줘"
Action → route to `recall-system/recall-system-learn/SKILL.md`

### Study Intent
Keywords: "공부", "연습", "질문해줘", "복습"
Action → route to `recall-system/recall-system-study/SKILL.md`

### Recall Intent
Keywords: "회상", "기억 테스트", "테스트"
Action → route to `recall-system/recall-system-recall/SKILL.md`
```

### Topic Slug Derivation Contract (Agent Execution Contract)

Document sanitization steps for deriving topic_slug from user input.

### Routing Decision Flow with Confidence Threshold and Disambiguation

Confidence threshold >= 0.7; ask once for clarification below threshold.

---

## Task 2a: Include All 12 Boundary Conditions With Explicit Text in Router SKILL.md

**Action:** The router SKILL.md from Task 2 MUST contain the following explicit handling text for all 12 BCs (this is not a reference or description — these are the actual BC-handling rules that will appear in the final file):

### BC-1: No Input
```markdown
When user sends no topic at all, display example utterances showing one clear example per intent:

"어떤 작업을 도와드릴까요? 예시: '이 주제에 대해 알려줘', '질문해줘', '기억 테스트'"
```

### BC-2: Intent Unclear
```markdown
If highest confidence < 0.7 or multiple intents close in confidence, ask once for clarification with a single clarifying question (e.g., "어떤 작업을 도와드릴까요?"). After receiving the user's response, re-parse and route deterministically to the appropriate sub-skill. If the second attempt is still ambiguous, default to "learn" intent.
```

### BC-3: No Topic Specified
```markdown
If user selects an intent but provides no topic name, show recent topics from metadata.json (sorted by last_updated descending) or list available topics alphabetically with their titles and a brief description. Example output: "다음 중에서 학습할 주제를 선택하세요: 1) Python 기본 문법 (2026-04-28), 2) 데이터 구조 (2026-04-25)"
```

### BC-4: No Existing Material + Recall Request
```markdown
When recall is requested for a topic with no index.md present, display: "아직 이 주제에 대해 학습한 내용이 없습니다. 먼저 학습해볼까요?" and route to learn sub-skill instead of attempting recall on empty material.
```

### BC-5: Existing index.md + Learn Request
```markdown
When user requests learning for an existing topic that already has index.md, ask explicitly: "이미 학습 자료가 있습니다. 덮어쓰기 (overwrite), 재생성 (regenerate), 아니면 기존 자료 유지 (keep) — 어떤 옵션을 선택하시겠습니까?" Wait for explicit choice before proceeding with the selected action.
```

### BC-6: Web Search Failure During Learning Material Generation
```markdown
When web search fails during learning material generation, log the failure and proceed with LLM knowledge only. Display notice to user: "(웹 검색 실패 — LLM 지식을 기반으로 학습 자료를 생성합니다)" This applies regardless of whether Oracle Browser or built-in web search was being used.
```

### BC-7: 30,000-char Underrun
```markdown
If generated learning material is under 30,000 characters of pure text (excluding markdown formatting), save as `subject/<topic_slug>/draft_failed.md` with reason in a comment header (e.g., "# draft_failed — Generated 24,500 chars; target was 30,000+"). Do not rename or move draft_failed.md to index.md. Notify user that generation was incomplete and suggest retrying with expanded scope.
```

### BC-8: User Says '모르겠어' During Recall
```markdown
Execute the full hint→retry→answer+explanation loop without skipping any stage. When user says "모르겠어": (1) provide one targeted hint for the current question's missing concept, (2) allow user to retry with the same question plus hint, (3) if answer still incorrect or user declines again, give correct answer with explanation and register this item in review queue regardless of outcome. Do not proceed to next question until this loop completes.
```

### BC-9: Session Interruption Mid-Recall
```markdown
Before any exit during recall session (SIGINT, SIGTERM, etc.), save partial session state to `subject/<topic_slug>/recall_sessions/partial_<YYYYMMDD_HHmmss>.json` containing: current stage number (1-4), questions asked so far with their scores, and answers already recorded. Upon resumption of recall for the same topic (detected by presence of a partial_<timestamp>.json file in recall_sessions/), offer user the option to continue from where they left off: "이전 회상 세션에서 중단되었습니다. 계속하시겠습니까? (y/n)"
```

### BC-10: Empty Review Queue at Start of Recall
```markdown
When no review queue items exist (empty or absent recall_queue.json), derive default recall questions from chapter-end "recall questions" embedded in the topic's index.md file. These chapter-end questions are automatically extracted and queued as the initial set for the first recall session. If no chapter-end questions are found either, generate 5 default questions based on chapter headings.
```

### BC-11: Corrupted State Files
```markdown
When reading metadata.json, recall_queue.json, or any state file fails (JSON parse error, missing fields, etc.), attempt recovery from corresponding .bak file using: first check `<filename>.bak`, then try to parse it as valid JSON. If .bak also unreadable, reinitialize with explicit user-facing notice: "상태 파일을 복구할 수 없습니다. 새로 초기화합니다." Record the reinitialization event in metadata.json's update_history if present. Example recovery output: "[RECOVERED] recall_queue.json restored from recall_queue.json.bak (last updated: 2026-04-25)"
```

### BC-12: Multiple Topic Candidates
```markdown
When the user provides a topic that matches multiple existing topics (e.g., ambiguous name like "파이썬" matching both "Python 기본 문법" and "Python 고급 기능"), prefer the most recent topic by last-modified time of its metadata.json file. If two or more candidates have identical timestamps or are within 30 days of each other, list them to user with their titles, creation dates, and a one-line description, then ask which one is intended: "다음 중 원하는 주제를 선택하세요: (1) Python 기본 문법 [2026-04-28] - 변수와 자료형; (2) Python 고급 기능 [2026-04-30] - 데코레이터와 제네레이터"
```

---

## Task 3: Write recall-system/recall-system-learn/SKILL.md (Learn Sub-Skill)

**Files:**
- Create: `recall-system/recall-system-learn/SKILL.md`

### Fixed 7-Chapter Structure

Document exact chapter order with Korean labels as per Seed: 탄생배경 → 정의 → 하위개념 → 관계도 → 사례 → 오해 → 회상키포인트.

### Output Requirements
- **Character Count**: Minimum 30,000 characters of pure text (excluding markdown formatting). If underrun → save as `draft_failed.md` with reason in comment header.
- **Recall Questions Per Chapter**: Each chapter ends with recall questions mixing three types: Fact-based ("What is X?"), Comparison ("How does X differ from Y?"), Understanding ("Why was Z developed? What problem does it solve?").
- **Inline Retrieval Points**: Format as `[RETRIEVE: <question>]` embedded at natural intervals within chapters (approximately every 500-700 characters of content).
- **References At End Only**: List all references in a single `## 참고자료` section at the end of document. No inline citations anywhere else.

### Source Generation Contract (Agent Execution Contract) — From Seed Goal Text

```markdown
# Source Generation Contract (from Seed)

Learning materials are generated using:
1. LLM knowledge + web search as primary sources
2. Oracle Browser as DEFAULT for web search capability
3. Built-in web search option available as alternative to Oracle Browser
4. User-provided materials (PDF, documents, links) accepted as OPTIONAL input alongside LLM knowledge and web search

When user provides their own materials: merge them into the learning material generation process, giving priority to official/primary sources per source conflict resolution rules below.
```

### Source Conflict Resolution (Agent Execution Contract)
Official/primary → recency check → uncertainty marked explicitly — NEVER state uncertain information as fact (단정 금지 in Korean output) → recorded in references section at end of document.

---

## Task 4: Write recall-system/recall-system-study/SKILL.md (Study Sub-Skill MVP v1)

**Files:**
- Create: `recall-system/recall-system-study/SKILL.md`

Document MVP v1 bounded scope explicitly: simple material-grounded Q&A only. Default behavior is user reading index.md directly; agent provides Q&A only when user requests it. Include boundary conditions for study mode (no existing material → prompt to learn first).

---

## Task 5: Write recall-system/recall-system-recall/SKILL.md (Recall Sub-Skill MVP v1)

**Files:**
- Create: `recall-system/recall-system-recall/SKILL.md`

### 4-Stage Recall Session Pipeline
Define exactly: free recall → analysis → scaffolded questions → synthesis check (use these exact terms from Seed goal text).

### 5-Level Scoring System (Explicitly Defined)

```markdown
| Score | Label (Korean) | Description |
|-------|----------------|-------------|
| 5 | 완벽 | Perfect recall — all details correct |
| 4 | 대부분 정확 | Mostly correct with minor omissions |
| 3 | 절반 정도 | Half correct — key concepts present but incomplete |
| 2 | 힌트 후 정답 | Correct after hint provided |
| 1 | 오답 | Wrong — no useful elements recalled |
```

### Hint → Retry → Answer + Explanation Feedback Loop

Document the full flow: when score < perfect, provide a targeted hint for the missing concept, allow user to retry. If still incorrect or user says "모르겠어", give correct answer with explanation and register in review queue regardless of outcome (per BC-8).

### Review Queue JSON Schema — ALL 7 FIELDS EXPLICITLY LISTED

The review queue file `subject/<topic_slug>/recall_queue.json` MUST contain entries with these exact fields:
1. **concept**: `<short topic identifier>`
2. **question**: `<the recall question asked>`
3. **failure_reason**: `<why this item was marked wrong or partially correct>`
4. **last_score**: `<integer from 1 to 5>`
5. **next_priority**: `<calculated priority value using recency + failure-count weighting formula>`
6. **last_seen**: `<ISO 8601 timestamp of last session>`
7. **due_hint**: `<hint text for next recall session>`

### Priority-Based Weak-Item Re-Asking (Agent-Discretionary in MVP v1)

Next recall session prioritizes previously weak items using combined recency + failure-count weighting. Formula suggestion: `priority = last_score_weight * recency_factor + failure_count * failure_factor`. Lower scores get higher priority; more recent sessions increase priority slightly. Exact heuristic is agent-discretionary in MVP v1.

### Boundary Condition Handling (BC-8, BC-9, BC-10)
Document explicit handling for each of the three recall-specific boundary conditions with full text as shown above in Task 2a section.

---

## Task 6: Create Sample Topic Structure and Verify Seed-Correct Paths

**Files:**
- Create: `subject/example-topic/index.md` (using exact Seed-correct path)
- Create: `subject/example-topic/metadata.json` with topic_slug, created_at, last_updated, title_ko fields
- Create: `subject/example-topic/recall_queue.json` initialized as empty array `[]`
- Create directory: `subject/example-topic/recall_sessions/`

Demonstrate that canonical learning material path is exactly `subject/<topic_slug>/index.md` per Seed requirement. Include a minimal sample index.md showing all 7 chapters with chapter-end recall questions.

---

## Task 7: Commit All Changes

```bash
git add recall-system/SKILL.md recall-system/recall-system-learn/ recall-system/recall-system-study/ recall-system/recall-system-recall/ subject/
git commit -m "feat(recall): MVP v1 skill harness with router, learn/study/recall sub-skills (Seed-correct paths)"
```

---

## Self-Review Checklist (Revision v3)

### Spec Coverage Against All Seed Requirements — With Direct Evidence Links in Plan Text

| Seed Requirement | Plan Task & Location | Status |
|------------------|---------------------|--------|
| Fixed 7-chapter structure (Korean labels) | Task 3: "탄생배경 → 정의 → 하위개념 → 관계도 → 사례 → 오해 → 회상키포인트" | ✅ |
| 30,000+ char minimum | Task 3: Character Count section with underrun handling | ✅ |
| Recall questions per chapter (mixed types) | Task 3: recall question types documented | ✅ |
| Inline retrieval points [RETRIEVE:] | Task 3: format specified as `[RETRIEVE: <question>]` | ✅ |
| References at end only | Task 3: "## 참고자료" section at end; no inline citations | ✅ |
| Oracle Browser default + user material input | Task 3: Source Generation Contract section with all four items | ✅ |
| Study = simple Q&A MVP v1 | Task 4: bounded scope documented | ✅ |
| Recall = 4-stage pipeline | Task 5: stages explicitly listed (free recall → analysis → scaffolded questions → synthesis check) | ✅ |
| 5-level scoring with Korean labels | Task 5: full table with all 5 levels and Korean names | ✅ |
| Hint→retry→answer feedback loop | Task 5: feedback flow documented | ✅ |
| Review queue with ALL 7 fields | Task 5: field list items 1-7 explicitly enumerated | ✅ |
| Priority-based weak-item re-asking | Task 5: formula and weighting logic described | ✅ |
| Natural language router classification | Task 2: intent classification rules documented | ✅ |
| **All 12 BCs with explicit text** | **Task 2a: BC-1 through BC-12 each has full handling paragraph with concrete examples and behavior descriptions** | ✅ NEW in v3 |
| **Seed-correct paths (no subjects/)** | **Task 1 & Task 6: all paths use `recall-system/{router,learn,study,rec}/` for skills; `subject/<topic_slug>/` for materials — matches Seed exactly** | ✅ FIXED in v3 |

### No Placeholder Scan
- Every section has explicit content, definitions, and concrete examples
- JSON schema lists all 7 fields by name with type descriptions
- All 12 BCs have full handling text paragraphs (not just references)
- Path naming matches Seed exactly — no `subjects/` pattern anywhere

---

## Plan Contract Lock (Revision v3)

```yaml
plan_contract_lock:
  approved_authority: "main-agent source-grounded judgment over seed_raw_ref, normalized plan v3, repo-local constraints"
  governed_downstream_entry: "superpowers:subagent-driven-development; superpowers:executing-plans only with explicit user override"
  controlling_objective: "Implement MVP v1 recall-system SKILL.md harness — router + learn/study/recall sub-skills using exact Seed paths and fully explicit BC handling in plan text"
  scope_boundary:
    - "MVP v1 ONLY: simple material-grounded Q&A for study; 4-stage recall session"
    - "Skill files at recall-system/{router,learn,study,rec}/ per Seed constraint"
    - "Learning materials at subject/<topic_slug>/index.md per Seed constraint"
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

## Writing Plan Completion Evidence (Revision v3)

```yaml
writing_plans_completion_evidence:
  terminal_state: success
  plan_artifact_ref: plans/plan_v3.md
  revision_number: "v3"
  reset_brief_ref: plans/reset_brief.md
  failed_artifact_closed: true
  no_patch_attestation: true
  plan_brief_completed: true
  oracle_draft_v1_completed: false
  seed_transport_proof:
    seed_raw_ref: seed_recall_system_20260428 (inline_full_seed in supervision prompts)
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
  plan_contract_lock_ref: plans/plan_v3.md#Plan-Contract-Lock-v3
  writing_plans_completion_evidence_ref: plans/plan_v3.md#writing-plans-completion-evidence-v3
  required_implementation_entry_skill: subagent-driven-development
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_executing_plans: false
```

**"Plan complete (v3). The normalized plan addresses both v2 supervision fail anchors: Seed-correct skill paths (recall-system/{router,learn,study,rec}/) and learning materials path (subject/<topic_slug>/index.md); ALL 12 boundary conditions now have explicit full text in Task 2a (not just enumeration or references). The `Plan Contract Lock` is frozen, and `writing_plans_completion_evidence` plus `implementation_contract_lock` have been emitted."**
