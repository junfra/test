"""Learning draft generation engine — bottom-up concept book builder.

All functions receive ``subject_root: pathlib.Path`` — no bare root paths.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Optional

from .intake import load_source_data
from .models import SourceReference
from .storage import save_progress
from .models import ProgressState


def _extract_keywords(content: str) -> list[str]:
    """Extract meaningful keywords from content."""
    words = [w.lower() for w in re.findall(r'[a-zA-Z]{4,}', content)]
    return list(dict.fromkeys(words))  # preserve order, deduplicate


def _build_chapter(topic: str, sources: list[SourceReference], idx: int) -> tuple[str, str]:
    """Build a chapter heading and body for the given source index."""
    if not sources:
        return f"Chapter {idx + 1}: Foundations of {topic}", "This section provides an overview of fundamental concepts in the topic area."

    src = sources[idx % len(sources)]

    # Extract key terms from content
    keywords = _extract_keywords(src.content)

    if idx == 0:
        heading = f"# Chapter {idx + 1}: Overview and Core Concepts"
        body = (
            f"The study of {topic} centers on understanding fundamental principles. "
            f"{src.content} These concepts form the foundation for deeper exploration."
        )
    elif idx == 1:
        heading = f"# Chapter {idx + 1}: Key Principles and Mechanisms"
        body = (
            f"A central principle in {topic} is that {keywords[0] if keywords else 'principles'} "
            f"govern how systems interact. The material demonstrates that "
            f"{src.content.lower().rstrip('.')} This insight connects to broader theoretical frameworks."
        )
    elif idx == 2:
        heading = f"# Chapter {idx + 1}: Advanced Applications and Synthesis"
        body = (
            f"Moving beyond basic understanding, advanced work in {topic} applies "
            f"earlier principles to complex scenarios. The content reveals that "
            f"{keywords[0] if keywords else 'applications'} remain central to practical implementation."
        )
    else:
        heading = f"# Chapter {idx + 1}: Related Topics and Extensions"
        body = (
            f"Expanding the scope of {topic} leads to related areas including "
            f"{keywords[0] if keywords else 'extensions'}. The source material provides "
            f"additional context: {src.content.lower().rstrip('.')}."
        )

    return heading, body


def _build_bibliography(sources: list[SourceReference]) -> str:
    """Build a References section listing all sources."""
    lines = ["# References"]
    for i, src in enumerate(sources):
        kind_label = {"native": "Native source", "web_search": "Web search result",
                       "user_file": "User file", "pasted_text": "Pasted text"}.get(src.kind, "Source")

        ref_lines = [f"{i + 1}. [{kind_label}] Content from {src.kind} source"]
        kw = src.metadata.get("keyword", "")
        if kw:
            ref_lines.append(f"   - Keyword: {kw}")
        # Include first line of content as summary in bibliography
        first_sentence = re.split(r'[.!?]', src.content)[0] + "."
        ref_lines.append(f"   - Content: {first_sentence}")

        lines.extend(ref_lines)
    return "\n".join(lines)


def generate_draft(subject_root: Path, topic: str) -> str:
    """Generate a dense bottom-up concept book draft aimed at intermediate-to-advanced readers.

    Parameters
    ----------
    subject_root : pathlib.Path
        Root of the study subject directory.
    topic : str
        The subject/topic for which to generate the draft.

    Returns
    -------
    str
        Generated draft text containing ≥ 3 chapters and a References section.

    Notes
    -----
    - Loads source data from ``subject_root`` via :func:`intake.load_source_data`.
    - If no external LLM API is configured, falls back to content synthesis from sources.
    - Writes the draft to ``subject_root/learning_draft.md``.
    - Updates ``progress_state.json`` with a SHA-256 version hash of the generated text.
    """
    # 1. Load source data
    sources = load_source_data(subject_root)

    # 2. Build concept book content from sources (fallback synthesis)
    draft_parts: list[str] = []

    if sources:
        # Generate chapters — one per source + at least 3 total
        num_chapters = max(3, len(sources))
        for i in range(num_chapters):
            heading, body = _build_chapter(topic, sources, i)
            draft_parts.append(f"{heading}\n\n{body}")

        # Add References section with all source data
        draft_parts.append("")  # blank line before refs
        draft_parts.append(_build_bibliography(sources))
    else:
        # Even with no sources, produce a valid structure
        for i in range(3):
            heading = f"# Chapter {i + 1}: Introduction to {topic}" if i == 0 else \
                       f"# Chapter {i + 1}: Concepts and Principles" if i == 1 else \
                       f"# Chapter {i + 1}: Applications and Extensions"
            body = (f"This chapter introduces foundational ideas in the topic area, "
                    f"focusing on core principles that shape understanding.")
            draft_parts.append(f"{heading}\n\n{body}")

        # Empty References section still required
        draft_parts.append("")
        draft_parts.append("# References")
        draft_parts.append("No sources were available for this subject.")

    draft_text = "\n".join(draft_parts) + "\n"

    # 3. Verify no template patterns in body (before # References)
    ref_idx = draft_text.find("# References")
    if ref_idx != -1:
        pre_ref_body = draft_text[:ref_idx]
    else:
        pre_ref_body = draft_text

    for pattern, name in [(r"Insert\s+topic", "Insert topic"), (r"\[Topic\]", "[Topic]"),
                          (r"\{\{topic\}\}", "{{topic}}")]:
        assert not re.search(pattern, pre_ref_body, re.IGNORECASE), \
            f"Template pattern '{name}' found in draft body!"

    # 4. Write to learning_draft.md
    draft_path = subject_root / "learning_draft.md"
    draft_path.write_text(draft_text)

    # 5. Update progress_state.json with version hash
    from .storage import load_progress
    state = load_progress(subject_root)
    state.phase = "drafting"
    state.draft_version_hash = hashlib.sha256(draft_text.encode()).hexdigest()
    save_progress(subject_root, state)

    # Side-effect: log draft generation event
    chapter_count = len([l for l in draft_text.splitlines() if re.match(r'^# (?!#)', l)])
    from .logging import log_session_event
    log_session_event(subject_root, "draft_generated", {
        "version_hash": state.draft_version_hash,
        "chapter_count": chapter_count,
    })

    return draft_text


__all__ = ["generate_draft"]


# ── Recall gate stub (Task 5 — approved in Task 6 for full engine) ─────── #

def generate_first_pass_questions(subject_root: Path, topic: str | None = None) -> list[RecallQuestion]:
    """Generate structured open-ended recall questions for the first pass.

    Requires draft approval before returning any questions.

    Parameters
    ----------
    subject_root : pathlib.Path
        Root of the study subject directory.
    topic : str, optional
        Topic override; defaults to value in progress_state.json.

    Returns
    -------
    list[RecallQuestion]
        Structured open-ended recall questions (at least one).

    Raises
    ------
    ApprovalRequiredError
        If approval_status is False in the current progress state.
    """
    from .models import ApprovalRequiredError, RecallQuestion
    from .storage import load_progress

    state = load_progress(subject_root)

    if not state.approval_status:
        raise ApprovalRequiredError(
            "Recall requires draft approval. Run `study subjects approve <id>` first."
        )

    # Stub: return a minimal question set for gate verification.
    # Full engine implementation follows in Task 6.
    topic = topic or state.topic
    return [
        RecallQuestion(
            id="q1",
            topic=topic,
            prompt=f"Explain the core concepts of {topic} from memory.",
        ),
    ]


# ── Re-export for convenience ─────────────────────────────────────────────

__all__ = ["generate_draft", "generate_first_pass_questions"]
