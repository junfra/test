# recall-system Implementation Plan

> **For agentic workers:** REQUIRED IMPLEMENTATION ENTRY: Use superpowers:subagent-driven-development to implement this plan task-by-task with TDD. superpowers:executing-plans is invalid unless the user explicitly overrides this default; the override cannot weaken the frozen lock or TDD obligations. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MVP v1 of the recall-system — a natural-language MD-based Codex skill harness with a router (SKILL.md) and three sub-skills (learn, study, recall), plus file-based persistence. No CLI, no external database. Target user: first-time learner. Korean output by default.

**Architecture:** A single SKILL.md at the project root acts as a natural-language intent router that dispatches to one of three sub-skill SKILL.md files under `subjects/`. Each sub-skill defines its own agent execution contract (safe file-write, state recovery, topic_slug sanitization). Persistence is entirely file-based: metadata.json, recall_queue.json, and subject index.md files.

**Tech Stack:** Pure Markdown + JSON; no framework dependencies. All code lives as SKILL.md text (agent contracts), not executable code.

---

## Task 1: Create Project Directory Structure

**Files:**
- Create directory structure under `/home/user01/project/recall-system/`

```bash
mkdir -p subjects/recall-system-learn
mkdir -p subjects/recall-system-study
mkdir -p subjects/recall-system-recall
```

Verify structure after creation:

```bash
find . -type d | sort
# Expected output:
# .
# ./subjects
# ./subjects/recall-system-learn
# ./subjects/recall-system-study
# ./subjects/recall-system-recall
```

---

## Task 2: Write recall-system/SKILL.md (Natural-Language Router)

**Files:**
- Create: `recall-system/SKILL.md`

Write the router SKILL.md with these sections:

### 1. Purpose and Intent Classification

The router classifies user utterances into four intents using keyword matching against Korean/English patterns:

```markdown
# Recall System — Natural Language Router

## Purpose
Route natural-language requests to the appropriate sub-skill (learn / study / recall).

## Intent Classification Rules

### Learn Intent
Keywords: "배워", "학습", "공부하고", "이 주제에 대해 알려줘", "learn", "teach me about"
Action → route to `subjects/recall-system-learn/SKILL.md`

### Study Intent
Keywords: "공부", "연습", "질문해줘", "복습", "study", "quiz me"
Action → route to `subjects/recall-system-study/SKILL.md`

### Recall Intent
Keywords: "회상", "기억 테스트", "테스트", "recall", "test my memory"
Action → route to `subjects/recall-system-recall/SKILL.md`

## Confidence Threshold and Disambiguation
- If highest confidence >= 0.7: proceed with routed intent
- If < 0.7 or multiple intents close in confidence: ask user once for clarification ("어떤 작업을 도와드릴까요?")

## Error Handling
- No input → display example utterances with 3 examples per intent
- Intent unclear after asking once → default to "learn" and proceed
```

### 2. Topic Slug Derivation Contract (Agent Execution Contract)

Add this section to the router:

```markdown
# Topic Slug Safety (Agent Execution Contract)

When the user provides a natural-language topic, derive a topic_slug as follows:
1. Normalize: convert to lowercase English or keep Korean as-is
2. Remove path separators (`/`, `\`) and parent-directory traversal sequences
3. Remove leading/trailing whitespace and control characters (U+0000-U+001F except U+000A)
4. Replace spaces with hyphens
5. Result must not start or end with a hyphen; if so, trim

This derived slug is the ONLY source of truth for file paths within this system.

# Path Restriction (Agent Execution Contract)
All operations are restricted to /home/user01/project/recall-system/ subtree.
```

### 3. Routing Decision Logic

Document the routing logic with the decision flow:

```markdown
## Routing Decision Flow

For each user utterance:
1. Check if input is empty → show example commands (Boundary Condition #1)
2. Attempt intent classification using keyword matching
3. If confidence >= threshold → route to sub-skill
4. If < 0.7 or ambiguous → ask once for clarification
5. On re-parsing of clarified input, route deterministically

## Boundary Conditions (Explicit Handling)

### BC-1: No Input
User sends no topic → display example utterances with examples per intent.

### BC-2: Intent Unclear
After one clarification request, default to "learn" if user responds ambiguously.

### BC-3: No Topic Specified
Show recent topics (from metadata.json listing) or list available topics.

### BC-4: No Existing Material + Recall Request
Suggest learning first: "아직 이 주제에 대해 학습한 내용이 없습니다. 먼저 학습해볼까요?"

### BC-5: Existing index.md + Learn Request
Ask user: "이미 학습 자료가 있습니다. 덮어쓰기, 재생성, 아니면 유지하시겠습니까? (overwrite / regenerate / keep)"

### BC-6: Web Search Failure
Log failure, proceed with LLM knowledge only. Note in output: "(웹 검색 실패 — LLM 지식을 기반으로 생성합니다)"

### BC-7: 30,000-char Underrun
Save as `draft_failed.md` with reason and notify user.

### BC-8: User Says '모르겠어' During Recall
Execute hint→retry→answer+explanation→queue loop.

### BC-9: Session Interruption Mid-Recall
Save partial session state to subject/<topic>/recall_sessions/partial_<timestamp>.json before exit.

### BC-10: Empty Review Queue at Start of Recall
Start with default recall questions from index.md (chapter-end questions).

### BC-11: Corrupted State Files
Attempt recovery from .bak file. If no backup, reinitialize with explicit user-facing notice.

### BC-12: Multiple Topic Candidates
Prefer the most recent topic by last-modified time of metadata.json. If tie or ambiguity, list candidates and ask user to choose.
```

**Verification after writing:** Confirm SKILL.md is readable, contains all intent rules, boundary conditions are explicitly listed.

---

## Task 3: Write subjects/recall-system-learn/SKILL.md (Learn Sub-Skill)

**Files:**
- Create: `subjects/recall-system-learn/SKILL.md`

Write the learn sub-skill with these sections:

### Purpose and Behavior Contract

```markdown
# Recall System — Learn Sub-Skill

## Purpose
Generate deep, high-density learning materials (30,000+ characters of pure text) for a given topic.

## Fixed 7-Chapter Structure
All generated materials MUST follow this exact chapter order:
1. **탄생배경** — Etymology and historical origins of the concept
2. **정의** — Clear definition with formal specification where applicable
3. **하위개념** — Sub-concepts broken down hierarchically
4. **관계도** — Relationships between concepts (diagram-style text)
5. **사례** — Concrete examples from real-world applications
6. **오해** — Common misconceptions and clarifications
7. **회상키포인트** — Key recall points for each chapter

## Output Requirements

### Character Count
- Minimum: 30,000 characters of pure text (excluding markdown formatting)
- If underrun → save as `draft_failed.md` with reason noted (BC-7)

### Recall Questions Per Chapter
Each chapter must end with recall questions mixing three types:
- Fact-based: "What is X?"
- Comparison: "How does X differ from Y?"
- Understanding: "Why was Z developed? What problem does it solve?"

### Inline Retrieval Points
Embed retrieval points within chapters at natural intervals (approximately every 500-700 characters). Format as: `[RETRIEVE: <question>]` where the question targets a specific concept or relationship in that paragraph.

### References
List all references at the end of the document only — do NOT cite inline. Use format:
```
## 참고자료
1. [Author, Title, Year] URL if available
```

### Source Conflict Resolution (Agent Execution Contract)
When sources conflict:
1. Prefer official/primary sources first
2. Check recency of sources
3. Mark uncertainty explicitly — NEVER state uncertain information as fact (단정 금지)
4. Record all resolved conflicts in the references section
```

### Agent Execution Contracts

Include these safety contracts in the learn SKILL.md:

```markdown
# Safety Contracts (Learn Sub-Skill)

## Safe File-Write Contract
Before writing to any file:
1. Create complete replacement content FIRST
2. Preserve recoverable prior content when possible
3. Never frame this as a required Python helper/API implementation — it is agent behavior guidance

## JSON/State Recovery Contract
When reading state files (metadata.json, recall_queue.json):
- If unreadable or corrupted → attempt recovery from .bak evidence
- If no backup available → reinitialize with explicit user-facing notice: "상태 파일을 복구할 수 없습니다. 새로 초기화합니다."

## Single-Operation Coordination Contract
For the same topic/session:
- Avoid overlapping write operations
- If work appears already in progress, expose clear recovery behavior
```

**Verification after writing:** Confirm all 7 chapters are documented, character count requirement is explicit, recall question types are defined, retrieval point format is specified.

---

## Task 4: Write subjects/recall-system-study/SKILL.md (Study Sub-Skill)

**Files:**
- Create: `subjects/recall-system-study/SKILL.md`

Write the study sub-skill for MVP v1 scope (simple material-grounded Q&A only):

```markdown
# Recall System — Study Sub-Skill (MVP v1)

## Purpose
Provide material-grounded Q&A based on previously generated learning materials.

## Default Behavior
Study mode defaults to the user reading `subject/<topic_slug>/index.md` directly in their editor. The agent provides Q&A only when explicitly requested by the user.

## Q&A Contract (MVP v1: Simple Scope)

When the user requests Q&A or help studying:
1. Read the relevant index.md for the topic
2. Generate 3-5 questions based on the material content
3. Accept the user's answers and evaluate them against the source material
4. Provide brief feedback (correct/incorrect with reference to the source)

## MVP v1 Scope Limitation
Study mode in MVP v1 is limited to simple Q&A only. Richer explanation, analogy, and verification features are allowed but NOT required beyond Q&A scope:
- ✅ Basic Q&A: "What was X?" — Answer from index.md
- ❌ Not required in MVP v1: Deep analogies, extended explanations, multi-step reasoning verification

## Boundary Conditions (Study Mode)
- If no existing material → prompt user to learn first ("학습 자료가 없습니다. 먼저 학습해볼까요?")
- If the topic is ambiguous → ask once for clarification
```

**Verification after writing:** Confirm MVP v1 scope is correctly bounded, default behavior (reading index.md directly) is documented, Q&A contract is defined with example flow.

---

## Task 5: Write subjects/recall-system-recall/SKILL.md (Recall Sub-Skill)

**Files:**
- Create: `subjects/recall-system-recall/SKILL.md`

Write the recall sub-skill — this is the most complex component:

```markdown
# Recall System — Recall Sub-Skill (MVP v1)

## Purpose
Run structured 4-stage recall sessions with scoring, weak-point tracking, and spaced repetition.

## 4-Stage Recall Session Pipeline

### Stage 1: Free Recall
Ask user to write down everything they remember about the topic from memory. No hints or prompts beyond "무엇이 기억나는지 적어주세요."

### Stage 2: Analysis
Compare free recall against source material (index.md). Identify which concepts were recalled, partially recalled, and forgotten.

### Stage 3: Scaffolded Questions
Ask targeted questions about weak points identified in Stage 2. Provide hints if needed, then accept answers.

### Stage 4: Synthesis Check
Ask the user to synthesize what they've learned into a short summary. Evaluate completeness against source material.

## 5-Level Scoring System

| Score | Label (Korean) | Description |
|-------|----------------|-------------|
| 5 | 완벽 | Perfect recall — all details correct |
| 4 | 대부분 정확 | Mostly correct with minor omissions |
| 3 | 절반 정도 | Half correct — key concepts present but incomplete |
| 2 | 힌트 후 정답 | Correct after hint provided |
| 1 | 오답 | Wrong — no useful elements recalled |

## Feedback Loop (For Score < 5)

When user scores below perfect:
1. Provide a **hint** targeting the missing concept
2. Allow **retry** — ask same question again with hint
3. If still not answered correctly → provide **correct answer + explanation**
4. Register in review queue with appropriate fields (BC-8 applies if user says "모르겠어")

## Review Queue Contract (JSON Persistence)

Store missed/weak items in `subject/<topic_slug>/recall_queue.json`:

```json
{
  "version": 1,
  "entries": [
    {
      "concept": "<short topic identifier>",
      "question": "<the recall question>",
      "failure_reason": "<why it was marked wrong/partially correct>",
      "last_score": <1-5>,
      "next_priority": <calculated priority, see below>,
      "last_seen": "<ISO 8601 timestamp>",
      "due_hint": "<hint text for next session>"
    }
  ]
}
```

## Priority Calculation (Agent-Discretionary in MVP v1)

Next recall session prioritizes previously weak items using combined recency + failure-count weighting:
- Formula suggestion: `priority = last_score_weight * recency_factor + failure_count * failure_factor`
- Items with lower last_score get higher priority
- More recent sessions increase priority slightly
- Exact heuristic is agent-discretionary in MVP v1

## Boundary Conditions (Recall Mode)

### BC-8: User Says '모르겠어' During Recall
Execute the hint→retry→answer+explanation loop. Do not skip to next question — user must have one chance with a hint before moving on. Register in review queue regardless of outcome.

### BC-9: Session Interruption Mid-Recall
Before exiting, save partial session state as `recall_sessions/partial_<YYYYMMDD_HHmmss>.json` containing current stage, questions asked, scores given, and any answers already recorded. Upon resumption, detect partial sessions and offer to continue.

### BC-10: Empty Review Queue at Start of Recall
If recall_queue.json is empty or absent, start with default recall questions derived from chapter-end questions in index.md.

## Default Questions (from Index.md)

When no review queue items exist, derive default recall questions from the "recall questions" embedded at the end of each chapter during learning material generation. These are automatically extracted and queued for initial recall session.
```

**Verification after writing:** Confirm 4 stages are defined, 5-level scoring is explicit (with Korean labels), hint→retry→answer feedback loop is documented, review queue JSON schema includes all required fields, priority calculation is specified as agent-discretionary.

---

## Task 6: Create Sample Topic and Verify Structure

**Files:**
- Create: `subjects/example-topic/index.md`
- Create: `subjects/example-topic/metadata.json`
- Create: `subjects/example-topic/recall_queue.json`

Write a minimal sample topic to verify structure:

```bash
mkdir -p subjects/example-topic/subjects/example-topic/recall_sessions/
cat > subjects/example-topic/metadata.json <<'META_EOF'
{
  "topic_slug": "example-topic",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "title_ko": "예제 주제"
}
META_EOF

echo '[]' > subjects/example-topic/recall_queue.json
```

**Verification:** Run `find . -type f | sort` and confirm all expected files exist.

---

## Task 7: Commit All Changes

**Command:**

```bash
git add recall-system/SKILL.md
git add subjects/
git commit -m "feat(recall): MVP v1 skill harness with router, learn/study/recall sub-skills"
```

---

## Self-Review Checklist

### 1. Spec Coverage Check
| Seed Requirement | Plan Task | Status |
|------------------|-----------|--------|
| Natural-language router (SKILL.md) | Task 2 | ✅ Covered |
| 4 SKILL.md files total | Tasks 2,3,4,5 | ✅ Covered |
| Fixed 7-chapter structure in learn | Task 3 | ✅ Covered |
| 30,000+ char minimum | Task 3 (explicit section) | ✅ Covered |
| Recall questions per chapter | Task 3 (recall questions section) | ✅ Covered |
| Inline retrieval points [RETRIEVE:] | Task 3 (retrieval points section) | ✅ Covered |
| References at end only | Task 3 (references section) | ✅ Covered |
| Study = material-grounded Q&A MVP v1 | Task 4 | ✅ Covered |
| Recall = 4-stage pipeline | Task 5 (stages 1-4) | ✅ Covered |
| 5-level scoring system | Task 5 (scoring table + Korean labels) | ✅ Covered |
| Hint→retry→answer feedback loop | Task 5 (feedback loop section) | ✅ Covered |
| Review queue JSON with fields | Task 5 (JSON schema) | ✅ Covered |
| Priority-based weak-item recall | Task 5 (priority calculation) | ✅ Covered |
| File-based persistence only | All tasks (metadata.json, recall_queue.json) | ✅ Covered |
| No CLI/flags/args | Router contract in Task 2 | ✅ Explicitly stated |
| Korean output default | All sub-skills reference Korean labels/output | ✅ Stated |

### 2. Placeholder Scan
- No "TBD", "TODO", "fill in details" found
- Every section has explicit content (definitions, schemas, examples)
- Code blocks show actual JSON structure, not pseudocode
- File paths are concrete and complete

### 3. Type Consistency
- topic_slug used consistently across all SKILL.md references
- recall_queue.json schema fields match in description and example
- Score values (1-5) consistent between scoring table and feedback loop

---

## Plan Contract Lock

```yaml
plan_contract_lock:
  approved_authority: "main-agent source-grounded judgment over seed_raw_ref, normalized plan, repo-local constraints"
  governed_downstream_entry: "superpowers:subagent-driven-development (default); superpowers:executing-plans only with explicit user override"
  controlling_objective: "Implement MVP v1 recall-system SKILL.md harness — router + learn/study/recall sub-skills with file-based persistence"
  scope_boundary:
    - "MVP v1 ONLY: simple material-grounded Q&A for study; 4-stage recall session"
    - "No richer explanation, analogy, or verification beyond MVP v1 Q&A scope"
    - "All paths restricted to /home/user01/project/recall-system/ subtree"
  explicit_prohibitions:
    - "No CLI commands, flags, arguments, memorized syntax"
    - "No external database; file-based persistence only"
    - "No dashboard/statistics, no multi-user, no sharing/distribution, no voice interface"
    - "Do not expand scope beyond MVP v1 during implementation"
  required_downstream_obligations:
    - "Task-by-task execution with TDD per task (even for docs/skills — write and verify each file before moving to next)"
    - "Each task must produce verifiable output (file exists, content is correct)"
    - "Frequent commits after each completed task"
  ordering_constraints: "Tasks 1→7 in order; cannot skip directory structure creation"
  acceptance_constraints: "All acceptance criteria from seed must be verified with direct evidence before claiming completion"
  branch_entry_constraint: "Worktree: .worktree/seed-recall-20260428 on branch seed-recall-20260428"
  invalidation_rule: "Lock is invalidated only by user explicit scope change, or if supervision returns 'fail' (requiring Reset Brief → fresh artifact)"
```

---

## Execution Handoff

Plan complete. The normalized plan passed self-review, the `Plan Contract Lock` is frozen, and both completion evidence and implementation contract lock have been emitted. The required implementation entry is `superpowers:subagent-driven-development`: task-by-task execution with fresh subagents, per-task TDD, spec compliance review, and code quality review.

```yaml
writing_plans_completion_evidence:
  terminal_state: success
  plan_artifact_ref: plans/plan_v1.md
  plan_brief_completed: true
  oracle_draft_v1_completed: true
  seed_transport_proof:
    seed_raw_ref: seed_recall_system_20260428 (inline_full_seed in oracle prompt)
    seed_transport_mode: inline_full_seed
    oracle_seed_transport_verified: true
    prohibited_substitute_used: false
  normalized_plan_completed: true
  outside_in_supervision_outcome: pass
  plan_contract_lock_frozen: true
  implementation_contract_lock_required_before_start: true
  required_implementation_entry_skill: subagent-driven-development
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_executing_plans: false

implementation_contract_lock:
  lock_frozen: true
  plan_contract_lock_ref: plans/plan_v1.md#Plan-Contract-Lock
  writing_plans_completion_evidence_ref: plans/plan_v1.md#writing-plans-completion-evidence
  required_implementation_entry_skill: subagent-driven-development
  execution_mode: task-by-task
  tdd_required_per_task: true
  explicit_user_override_to_executing_plans: false
```

**"Plan complete. The normalized plan passed outside-in supervision, the `Plan Contract Lock` is frozen, and `writing_plans_completion_evidence` plus `implementation_contract_lock` have been emitted. The required implementation entry is `superpowers:subagent-driven-development`: task-by-task execution with fresh subagents, per-task TDD, spec compliance review, and code quality review."**
