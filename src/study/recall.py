"""Recall session engine — sequential first pass generation + scoring."""
from __future__ import annotations

import re
from pathlib import Path

from .models import (
    ApprovalRequiredError,
    RecallQuestion,
    RecallSessionEntry,
    WeakPoint,
)


def extract_sections(draft_text: str) -> list[tuple[str, str, str]]:
    """Parse a markdown draft into (chapter, section_title, content) tuples.

    Sections are identified by ``## headers`` within each ``# Chapter`` block.
    The content spans from the header line up to the next ## or EOF.

    Returns an empty list if no sections are found.
    """
    lines = draft_text.splitlines()
    sections: list[tuple[str, str, str]] = []
    current_chapter: str | None = None
    section_lines: list[str] = []
    current_title: str | None = None

    for line in lines:
        # New top-level chapter resets context
        if re.match(r"^[#]+", line):
            _flush_section(sections, current_chapter, current_title, "\n".join(section_lines))
            current_chapter = line.strip().lstrip("# ").strip()
            current_title = None
            section_lines = []

        # Section header starts a new section
        elif re.match(r"^##\s+", line):
            _flush_section(sections, current_chapter, current_title, "\n".join(section_lines))
            current_title = line.strip().lstrip("# ").strip()
            section_lines = [line]  # keep header in content for context

        else:
            section_lines.append(line)

    _flush_section(sections, current_chapter, current_title, "\n".join(section_lines))
    return sections


def _flush_section(
    sections: list[tuple[str, str, str]],
    chapter: str | None,
    title: str | None,
    content: str,
) -> None:
    """Append a section if we have a valid chapter + title."""
    if chapter and title and content.strip():
        sections.append((chapter, title, content))


# --------------------------------------------------------------------------- #
# Prompt templates — open-ended, no MC options
# --------------------------------------------------------------------------- #

_PROMPT_TEMPLATES = [
    "Explain in your own words: {topic}",
    "Based on the draft, what is the key concept behind {topic}?",
    "Summarize the main idea of {topic}.",
]


def generate_prompt_template(topic: str) -> str:
    """Return a structured open-ended prompt for *topic*."""
    template = _PROMPT_TEMPLATES[hash(topic) % len(_PROMPT_TEMPLATES)]
    return template.format(topic=topic)


# --------------------------------------------------------------------------- #
# Chapter-level fallback for drafts without ## headers  
# --------------------------------------------------------------------------- #
def _extract_chapters_as_fallback(draft_text: str) -> list[tuple[str, str, str]]:
    """Fallback for drafts without ## headers — use # Chapter headers as sections."""
    lines = draft_text.splitlines()
    chapters: list[tuple[str, str, str]] = []
    current_title = None
    section_lines: list[str] = []

    for line in lines:
        if re.match(r"^# (References|# Bibliography)", line):
            # Flush last chapter before stopping
            _flush_section(chapters, current_title, current_title, "\n".join(section_lines))
            break
        
        if line.startswith("#") and not line.startswith("##"):
            title = line.strip().lstrip("# ").strip()
            # If we have a previous chapter with content, flush it first
            if current_title:
                _flush_section(chapters, current_title, current_title, "\n".join(section_lines))
            current_title = title
            section_lines = []
        else:
            if line.strip():  # skip blank lines
                section_lines.append(line)

    return chapters


def generate_first_pass_questions(
    subject_root: Path,
    n: int = 5,
) -> list[RecallQuestion]:
    """Generate structured open-ended prompts covering the approved draft sequentially.

    Parameters
    ----------
    subject_root : pathlib.Path
        Path to the subject directory containing ``progress_state.json`` and ``learning_draft.md``.
    n : int
        Maximum number of questions to generate (defaults to 5).

    Returns
    -------
    list[RecallQuestion]
        Ordered *RecallQuestion* instances corresponding to draft sections in order.

    Raises
    ------
    ApprovalRequiredError
        If the draft has not yet been approved (*approval_status* is ``False``).
    FileNotFoundError
        If required files are missing from *subject_root*.
    """
    # 1. Check approval status first — gate recall until draft is approved
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before recall")

    # 2. Read learning_draft.md and walk sequentially by ## headers
    draft_path = subject_root / "learning_draft.md"
    if not draft_path.exists():
        raise FileNotFoundError(f"{draft_path} does not exist in {subject_root}")

    draft_text = draft_path.read_text(encoding="utf-8")
    sections = extract_sections(draft_text)
    
    # Fallback: if no ## headers, try extracting from # Chapter headers
    if not sections:
        sections = _extract_chapters_as_fallback(draft_text)


    # 3. Generate structured open-ended prompts per section (up to n)
    questions: list[RecallQuestion] = []
    for i, (chapter, title, _content) in enumerate(sections[:n]):
        q = RecallQuestion(
            id=f"q_{i + 1}",
            topic=title,
            prompt=(
                f"Based on the draft '{title}' under '{chapter}', "
                f"explain in your own words: {generate_prompt_template(title)}"
            ),
        )
        questions.append(q)

    # 4. Update progress_state.json — phase and cursor
    state = load_progress(subject_root)
    state.phase = "recall_first_pass"
    state.next_recursors_cursor = len(questions)
    save_progress(subject_root, state)

    return questions


# --------------------------------------------------------------------------- #
# Scoring helpers
# --------------------------------------------------------------------------- #

def _tokenize(text: str) -> set[str]:
    """Simple whitespace/token-based tokenization."""
    return set(text.lower().split())


def score_answer(question: RecallQuestion, answer: str, draft_content: str) -> float:
    """Score the quality of an answer against expected content.

    Returns a float clamped to [0, 1].  Uses simple overlap heuristic between
    answer tokens and the expected draft content.
    """
    if not draft_content or not answer:
        return 0.0

    q_tokens = _tokenize(answer)
    d_tokens = _tokenize(draft_content)

    # Overlap ratio — simple Jaccard-inspired measure
    intersection = len(q_tokens & d_tokens)
    union = max(len(q_tokens | d_tokens), 1)
    overlap_ratio = intersection / union

    # Scale to [0, 1] range (raw overlap is typically small because vocab differs)
    score = min(overlap_ratio * 5.0, 1.0)  # heuristic multiplier

    return max(0.0, min(score, 1.0))


def decompose_misconceptions(answer: str, expected_content: str) -> dict:
    """Analyze an answer for misconceptions versus the expected content.

    Returns a dictionary with two keys:
        - "misconception": str — explanation of any misconception detected
        - "correct_points": list[str] — bullet points that were correct
    """
    if not answer or not expected_content:
        return {
            "misconception": "Answer is empty, cannot evaluate.",
            "correct_points": [],
        }

    # Simple heuristic: check for negation patterns and contradictions
    negations = {"not", "never", "no ", "wrong", "incorrect", "false"}
    answer_lower = answer.lower()
    has_negation = any(neg in answer_lower for neg in negations)

    if has_negation and expected_content.strip():
        misconception_text = (
            f"The answer contradicts the expected content by denying key concepts. "
            f"Expected: '{expected_content[:60].strip()}'"
        )
    else:
        misconception_text = ""  # no obvious misconception

    correct_points = []
    if answer_lower.strip():
        correct_points.append(f"The user provided an answer on the topic.")

    return {
        "misconception": misconception_text or "No clear misconception detected.",
        "correct_points": correct_points,
    }


# --------------------------------------------------------------------------- #
# Session recording — populates ALL recovery state fields
# --------------------------------------------------------------------------- #

def record_session(
    subject_root: Path,
    questions: list[RecallQuestion],
    answers: list[str],
    scores: list[float],
) -> RecallSessionEntry:
    """Record a recall session and update all recovery state in ProgressState.

    This is the key function that populates ALL recovery fields per seed requirement.

    Raises
    ------
    ApprovalRequiredError
        If the draft has not yet been approved (*approval_status* is ``False``).
    """
    import uuid as _uuid
    from datetime import datetime, timezone

    # 1. Check approval_status first — gate recall until draft is approved
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before recall")

    # 2. Determine outcome based on average score
    avg_score = sum(scores) / max(len(scores), 1) if scores else 0.0
    if avg_score >= 0.7:
        outcome = "pass"
    elif avg_score < 0.4:
        outcome = "fail"
    else:
        outcome = "partial"

    # 3. Create session entry and append to recall_history.jsonl
    entry = RecallSessionEntry(
        session_id=str(_uuid.uuid4()),
        questions=questions,
        answers=list(answers),
        scores=[float(s) for s in scores],
        outcome=outcome,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    append_recalls(subject_root, [entry])

    # 4. Update ProgressState — THIS IS CRITICAL: all fields must be populated correctly
    state = load_progress(subject_root)

    # a. Phase → "recall_adaptive" (per seed requirement for recovery)
    state.phase = "recall_adaptive"

    # b. approval_status stays True (already checked above, do not change it)
    assert state.approval_status is True, "approval_status must remain True after scoring"

    # c. draft_version_hash — verify it exists from Task 4 generate_draft; do NOT overwrite
    assert (
        state.draft_version_hash is not None and len(state.draft_version_hash) > 0
    ), "draft_version_hash must exist before recording session"

    # d. next_recursors_cursor advances by 1 per session
    state.next_recursors_cursor += 1

    # e. weak_points populated from low-score answers (< 0.5 = weak)
    for question, score in zip(questions, scores):
        if isinstance(score, float) and score < 0.5:
            existing_topics = [wp.topic for wp in state.weak_points]
            if question.topic not in existing_topics:
                explanation = decompose_misconceptions(
                    answers[questions.index(question)], "expected content"
                )["misconception"]
                state.weak_points.append(
                    WeakPoint(
                        topic=question.topic,
                        misconception_explanation=explanation,
                        weakness_score=float(score),
                        retest_count=0,  # reset for first tracking
                    )
                )

    # f. Save updated ProgressState
    save_progress(subject_root, state)

    return entry


def _generate_retest_prompt(topic: str, misconception_explanation: str) -> str:
    """Generate a focused retest question targeting the identified misconception."""
    return f"Based on your previous weak understanding of '{topic}': {misconception_explanation}. Explain this concept clearly now."


def select_next_questions_weak(
    subject_root: Path,
    n: int = 3,
) -> list[RecallQuestion]:
    """Generate targeted questions prioritizing weak areas with weighted random selection.

    Parameters
    ----------
    subject_root : pathlib.Path
        Path to the subject directory containing progress_state.json and learning_draft.md.
    n : int
        Maximum number of adaptive retest questions to generate (defaults to 3).

    Returns
    -------
    list[RecallQuestion]
        Ordered *RecallQuestion* instances targeting weak topics, or an empty list
        when there are no recorded weak points.

    Raises
    ------
    ApprovalRequiredError
        If the draft has not yet been approved (*approval_status* is False).
    """
    # 1. Check approval status first — gate recall until draft is approved
    state = load_progress(subject_root)
    if not state.approval_status:
        raise ApprovalRequiredError("Draft must be approved before adaptive retest")

    weak_points = list(state.weak_points)
    if not weak_points:
        return []

    # 2. Weighted random selection — lower weakness_score means weaker topic → higher weight
    import random as _random

    def weight_for_wp(wp):
        return 1.0 / max(0.01, wp.weakness_score + 1.0 - wp.retest_count * 0.1)

    topics = [wp.topic for wp in weak_points]
    weights = [weight_for_wp(wp) for wp in weak_points]

    # Weighted random selection without replacement (Fisher-Yates / reservoir style)
    selected_indices: list[int] = []
    available_idx = list(range(len(weak_points)))
    avail_w = list(weights)

    while len(selected_indices) < min(n, len(available_idx)):
        total_weight = sum(avail_w) if avail_w else 1.0
        r = _random.random() * total_weight
        cumulative = 0.0
        chosen_i = None
        for i in range(len(available_idx)):
            cumulative += avail_w[i]
            if r <= cumulative:
                chosen_i = i
                break

        if chosen_i is not None:
            topic_idx = available_idx[chosen_i]
            selected_indices.append(topic_idx)
            del available_idx[chosen_i]
            del avail_w[chosen_i]

    # 3. Generate targeted questions for selected weak topics
    draft_text = (subject_root / "learning_draft.md").read_text(encoding="utf-8")
    questions: list[RecallQuestion] = []
    for idx in sorted(selected_indices):
        wp = weak_points[idx]
        q = RecallQuestion(
            id=f"ret_{len(questions) + 1}",
            topic=wp.topic,
            prompt=_generate_retest_prompt(wp.topic, wp.misconception_explanation),
        )
        questions.append(q)

    # 4. Update retest_count for selected weak points
    state = load_progress(subject_root)
    for idx in sorted(selected_indices):
        for i, existing_wp in enumerate(state.weak_points):
            if existing_wp.topic == weak_points[idx].topic:
                state.weak_points[i].retest_count += 1
                break
    save_progress(subject_root, state)

    return questions


# --------------------------------------------------------------------------- #
# Local imports (avoid circular deps with storage)
# --------------------------------------------------------------------------- #
from .storage import load_progress, save_progress  # noqa: E402 isort: skip
from .storage import append_recalls  # noqa: F811 isort: skip

__all__ = ["generate_first_pass_questions", "extract_sections", "select_next_questions_weak"]
