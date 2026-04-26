"""Recall session engine — sequential first pass generation."""
from __future__ import annotations

import re
from pathlib import Path

from .models import ApprovalRequiredError, RecallQuestion


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
        if re.match(r"^#\s+", line):
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
# Public API
# --------------------------------------------------------------------------- #

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
# Local imports (avoid circular deps with storage)
# --------------------------------------------------------------------------- #
from .storage import load_progress, save_progress  # noqa: E402 isort: skip

__all__ = ["generate_first_pass_questions", "extract_sections"]
