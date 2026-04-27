# Recall System — Natural Language Router

## Purpose
Route natural-language requests to the appropriate sub-skill (learn / study / recall) based on user intent. All operations occur within `/home/user01/project/recall-system/`.

---

## Intent Classification Rules

### Learn Intent
Keywords: "배워", "학습", "공부하고", "이 주제에 대해 알려줘"  
Action → route to `recall-system/recall-system-learn/SKILL.md`

### Study Intent
Keywords: "공부", "연습", "질문해줘", "복습"  
Action → route to `recall-system/recall-system-study/SKILL.md`

### Recall Intent
Keywords: "회상", "기억 테스트", "테스트"  
Action → route to `recall-system/recall-system-recall/SKILL.md`

---

## Confidence Threshold and Disambiguation
- If highest intent confidence ≥ 0.7: proceed with routed intent
- If < 0.7 or multiple intents close in confidence: ask once for clarification ("어떤 작업을 도와드릴까요?")
- After re-parsing clarified input, route deterministically
- If second attempt is still ambiguous, default to "learn"

---

# Topic Slug Safety (Agent Execution Contract)

When the user provides a natural-language topic, derive a `topic_slug` as follows:
1. Normalize: convert to lowercase or keep Korean as-is
2. Remove path separators (`/`, `\`) and parent-directory traversal sequences (`..`)
3. Remove leading/trailing whitespace and control characters (U+0000-U+000F, U+007F)
4. Replace spaces with hyphens
5. Result must not start or end with a hyphen; trim if so

This derived slug is the ONLY source of truth for file paths within this system.

# Path Restriction (Agent Execution Contract)
All operations are restricted to `/home/user01/project/recall-system/` subtree only.

---

# Boundary Conditions — Explicit Handling (All 12 BCs)

## BC-1: No Input
When user sends no topic at all, display example utterances showing one clear example per intent:

"어떤 작업을 도와드릴까요? 예시: '이 주제에 대해 알려줘', '질문해줘', '기억 테스트'"

## BC-2: Intent Unclear
If highest confidence < 0.7 or multiple intents close in confidence, ask once for clarification ("어떤 작업을 도와드릴까요?"). After receiving the user's response, re-parse and route deterministically to the appropriate sub-skill. If the second attempt is still ambiguous, default to "learn" intent.

## BC-3: No Topic Specified
If user selects an intent but provides no topic name, show recent topics from `metadata.json` (sorted by last_updated descending) or list available topics alphabetically with their titles and a brief description. Example output: "다음 중에서 학습할 주제를 선택하세요: 1) Python 기본 문법 [2026-04-28], 2) 데이터 구조 [2026-04-25]"

## BC-4: No Existing Material + Recall Request
When recall is requested for a topic with no `index.md` present, display: "아직 이 주제에 대해 학습한 내용이 없습니다. 먼저 학습해볼까요?" and route to learn sub-skill instead of attempting recall on empty material.

## BC-5: Existing index.md + Learn Request
When user requests learning for an existing topic that already has `index.md`, ask explicitly: "이미 학습 자료가 있습니다. 덮어쓰기 (overwrite), 재생성 (regenerate), 아니면 기존 자료 유지 (keep) — 어떤 옵션을 선택하시겠습니까?" Wait for explicit choice before proceeding with the selected action.

## BC-6: Web Search Failure During Learning Material Generation
When web search fails during learning material generation, log the failure and proceed with LLM knowledge only. Display notice to user: "(웹 검색 실패 — LLM 지식을 기반으로 학습 자료를 생성합니다)" This applies regardless of whether Oracle Browser or built-in web search was being used.

## BC-7: 30,000-char Underrun
If generated learning material is under 30,000 characters of pure text (excluding markdown formatting), save as `subject/<topic_slug>/draft_failed.md` with reason in a comment header (e.g., "# draft_failed — Generated 24,500 chars; target was 30,000+"). Do not rename or move `draft_failed.md` to `index.md`. Notify user that generation was incomplete and suggest retrying with expanded scope.

## BC-8: User Says '모르겠어' During Recall
Execute the full hint→retry→answer+explanation loop without skipping any stage. When user says "모르겠어": (1) provide one targeted hint for the current question's missing concept, (2) allow user to retry with the same question plus hint, (3) if answer still incorrect or user declines again, give correct answer with explanation and register this item in review queue regardless of outcome. Do not proceed to next question until this loop completes.

## BC-9: Session Interruption Mid-Recall
Before any exit during recall session (SIGINT, SIGTERM), save partial session state to `subject/<topic_slug>/recall_sessions/partial_<YYYYMMDD_HHmmss>.json` containing: current stage number (1–4), questions asked so far with their scores, and answers already recorded. Upon resumption of recall for the same topic (detected by presence of a `partial_<timestamp>.json` file in `recall_sessions/`), offer user the option to continue from where they left off: "이전 회상 세션에서 중단되었습니다. 계속하시겠습니까? (y/n)"

## BC-10: Empty Review Queue at Start of Recall
When no review queue items exist (empty or absent `recall_queue.json`), derive default recall questions from chapter-end "recall questions" embedded in the topic's `index.md` file. These chapter-end questions are automatically extracted and queued as the initial set for the first recall session. If no chapter-end questions are found either, generate 5 default questions based on chapter headings (e.g., "탄생배경", "정의").

## BC-11: Corrupted State Files
When reading `metadata.json`, `recall_queue.json`, or any state file fails (JSON parse error, missing fields), attempt recovery from corresponding `.bak` file using: first check `<filename>.bak`, then try to parse it as valid JSON. If .bak also unreadable, reinitialize with explicit user-facing notice: "상태 파일을 복구할 수 없습니다. 새로 초기화합니다." Record the reinitialization event in `metadata.json`'s update_history if present. Example recovery output: "[RECOVERED] recall_queue.json restored from recall_queue.json.bak (last updated: 2026-04-25)"

## BC-12: Multiple Topic Candidates
When the user provides a topic that matches multiple existing topics (e.g., ambiguous name like "파이썬" matching both "Python 기본 문법" and "Python 고급 기능"), prefer the most recent topic by last-modified time of its `metadata.json` file. If two or more candidates have identical timestamps or are within 30 days of each other, list them to user with their titles, creation dates, and a one-line description, then ask which one is intended: "다음 중 원하는 주제를 선택하세요: (1) Python 기본 문법 [2026-04-28] - 변수와 자료형; (2) Python 고급 기능 [2026-04-30] - 데코레이터와 제네레이터"
