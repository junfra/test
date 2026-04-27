# Recall System — Study Sub-Skill (MVP v1)

## Purpose
Provide material-grounded Q&A based on previously generated learning materials. MVP v1 scope is limited to simple Q&A only.

---

# Default Behavior
Study mode defaults to the user reading `subject/<topic_slug>/index.md` directly in their editor. The agent provides Q&A **only when the user explicitly requests help or questions**.

## MVP v1 Scope Limitation
MVP v1 is limited to simple material-grounded Q&A only:
- ✅ Basic Q&A from index.md content ("What was X?" — Answer from index.md)
- ❌ Not required in MVP v1: Deep analogies, extended explanations, multi-step reasoning verification

Richer explanation, analogy, and verification features are allowed but NOT required beyond the Q&A scope.

---

# Q&A Contract (MVP v1: Simple Scope)

When the user requests Q&A or help studying:
1. Read the relevant `index.md` for the topic from `subject/<topic_slug>/index.md`
2. Generate 3–5 questions based on the material content
3. Accept the user's answers and evaluate them against the source material
4. Provide brief feedback (correct/incorrect with reference to the source)

## Example Flow
**User:** "이 주제에 대해 질문해줄래?"  
**Agent:** "물론입니다! 먼저 index.md의 내용을 기반으로 몇 가지 질문을 준비하겠습니다." [Reads and generates questions]  
**User:** "질문 1: ~"  
**Agent:** "맞습니다! (index.md Chapter 2 참조)"

---

# Boundary Conditions for Study Mode

## No Existing Material
If no existing learning material is found for the topic, prompt user to learn first: "학습 자료가 없습니다. 먼저 학습해볼까요?"

## Topic Ambiguity
When the topic is ambiguous, ask once for clarification (per router BC-2), then proceed with Q&A based on the clarified topic.
