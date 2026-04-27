# Recall System — Recall Sub-Skill (MVP v1)

## Purpose
Run structured 4-stage recall sessions with scoring, weak-point tracking, and spaced repetition to strengthen long-term memory through retrieval practice.

---

# 4-Stage Recall Session Pipeline

The recall session follows exactly these four stages in order:

### Stage 1: Free Recall
Ask user to write down everything they remember about the topic from memory. No hints or prompts beyond "무엇이 기억나는지 적어주세요." (Write down what you can remember.)

### Stage 2: Analysis
Compare free recall against source material (`index.md`). Identify which concepts were recalled, partially recalled, and forgotten.

### Stage 3: Scaffolded Questions
Ask targeted questions about weak points identified in Stage 2. Provide hints if needed, then accept answers.

### Stage 4: Synthesis Check
Ask the user to synthesize what they've learned into a short summary. Evaluate completeness against source material.

---

# 5-Level Scoring System (Explicitly Defined)

| Score | Label (Korean) | Description |
|-------|----------------|-------------|
| 5 | 완벽 | Perfect recall — all details correct |
| 4 | 대부분 정확 | Mostly correct with minor omissions |
| 3 | 절반 정도 | Half correct — key concepts present but incomplete |
| 2 | 힌트 후 정답 | Correct after hint provided |
| 1 | 오답 | Wrong — no useful elements recalled |

---

# Hint → Retry → Answer + Explanation Feedback Loop

When user scores below perfect:
1. Provide a **hint** targeting the missing concept
2. Allow **retry** — ask same question again with hint
3. If still not answered correctly or user says "모르겠어" (per BC-8) → give **correct answer + explanation**
4. Register in review queue with appropriate fields

Do not proceed to next question until this loop completes for the current item.

---

# Review Queue JSON Schema — ALL 7 FIELDS EXPLICITLY LISTED

The review queue file `subject/<topic_slug>/recall_queue.json` MUST contain entries with these exact fields:

1. **concept**: `<short topic identifier>`
2. **question**: `<the recall question asked>`
3. **failure_reason**: `<why this item was marked wrong or partially correct>`
4. **last_score**: `<integer from 1 to 5>`
5. **next_priority**: `<calculated priority value using recency + failure-count weighting formula>`
6. **last_seen**: `<ISO 8601 timestamp of last session>`
7. **due_hint**: `<hint text for next recall session>`

### Example Entry
```json
{
  "concept": "deep-learning-layers",
  "question": "What do deep learning layers progressively capture?",
  "failure_reason": "Could not distinguish between early and late layer representations",
  "last_score": 3,
  "next_priority": 0.72,
  "last_seen": "2026-04-28T08:00:00Z",
  "due_hint": "Recall that early layers capture simple features (edges) while late layers capture complex patterns."
}
```

---

# Priority-Based Weak-Item Re-Asking (Agent-Discretionary in MVP v1)

Next recall session prioritizes previously weak items using combined recency + failure-count weighting:

**Formula suggestion:** `priority = last_score_weight * recency_factor + failure_count * failure_factor`
- Lower scores → higher priority
- More recent sessions → slightly increased priority
- Exact heuristic is agent-discretionary in MVP v1

---

# Boundary Condition Handling (BC-8, BC-9, BC-10)

## BC-8: User Says '모르겠어' During Recall
Execute the full hint→retry→answer+explanation loop without skipping any stage. When user says "모르겠어": (1) provide one targeted hint for the current question's missing concept, (2) allow user to retry with the same question plus hint, (3) if answer still incorrect or user declines again, give correct answer with explanation and register this item in review queue regardless of outcome. Do not proceed to next question until this loop completes.

## BC-9: Session Interruption Mid-Recall
Before any exit during recall session (SIGINT, SIGTERM), save partial session state to `subject/<topic_slug>/recall_sessions/partial_<YYYYMMDD_HHmmss>.json` containing: current stage number (1–4), questions asked so far with their scores, and answers already recorded. Upon resumption of recall for the same topic (detected by presence of a `partial_<timestamp>.json` file in `recall_sessions/`), offer user the option to continue from where they left off: "이전 회상 세션에서 중단되었습니다. 계속하시겠습니까? (y/n)"

## BC-10: Empty Review Queue at Start of Recall
When no review queue items exist (empty or absent `recall_queue.json`), derive default recall questions from chapter-end "recall questions" embedded in the topic's `index.md` file. These chapter-end questions are automatically extracted and queued as the initial set for the first recall session. If no chapter-end questions are found either, generate 5 default questions based on chapter headings (e.g., "탄생배경", "정의").
