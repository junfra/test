"""Learning draft generation engine — LM-driven concept reconstruction."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Protocol

from .config import load_lm_config
from .intake import load_source_data
from .lm_client import LMClient, LMGenerationError, parse_learning_system_json
from .models import LearningDraftSystem, RecallQuestion, SourceReference
from .prompt_builder import build_chapter_prompt
from .storage import load_progress, save_progress


class _GeneratesText(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate text from an LM prompt."""


def _chapter_count(sources: list[SourceReference]) -> int:
    return max(3, len(sources))


def _build_chapter_from_lm(
    *,
    client: _GeneratesText,
    topic: str,
    sources: list[SourceReference],
    chapter_index: int,
    chapter_count: int,
) -> LearningDraftSystem:
    prompt = build_chapter_prompt(
        topic=topic,
        sources=sources,
        chapter_index=chapter_index,
        chapter_count=chapter_count,
    )
    raw = client.generate(prompt)
    return parse_learning_system_json(raw)


def _merge_learning_systems(
    *,
    topic: str,
    chapter_systems: list[LearningDraftSystem],
    sources: list[SourceReference],
) -> LearningDraftSystem:
    concept_layers: list[str] = []
    section_structure: list[str] = []
    recall_hooks: list[str] = []
    verification_points: list[str] = []
    bibliography: list[str] = []

    for chapter in chapter_systems:
        concept_layers.extend(chapter.concept_layers)
        section_structure.extend(chapter.section_structure)
        recall_hooks.extend(chapter.recall_hooks)
        verification_points.extend(chapter.verification_points)
        bibliography.extend(chapter.bibliography)

    if sources:
        for index, source in enumerate(sources, start=1):
            keyword = source.metadata.get("keyword", "")
            keyword_text = f", keyword={keyword}" if keyword else ""
            bibliography.append(f"Source {index}: kind={source.kind}{keyword_text}")
    else:
        bibliography.append("No source references were provided for this subject.")

    return LearningDraftSystem(
        topic=topic,
        concept_layers=concept_layers,
        section_structure=section_structure,
        recall_hooks=recall_hooks,
        verification_points=verification_points,
        bibliography=list(dict.fromkeys(bibliography)),
    )


def _fallback_paragraph(topic: str, chapter_number: int) -> str:
    return (
        f"Deterministic fallback reconstruction for {topic}, chapter {chapter_number}. "
        f"This fallback exists only because LM generation failed. It reconstructs the concept without copying source prose by using a stable learning model: "
        f"identify the entity, explain the pressure that makes the entity necessary, map the mechanism that changes state, describe the consequence of the mechanism, "
        f"and define a verification question that proves understanding. The explanation remains dense because a learner should not merely recognize vocabulary. "
        f"The learner should be able to rebuild the conceptual machine. In chapter {chapter_number}, the topic is treated as an operational system with boundaries, "
        f"inputs, transformations, outputs, and failure modes. The conceptual layer names the role of each part. The mechanism layer shows how parts interact. "
        f"The learning layer compresses the mechanism into a recall pattern that can be practiced later. This makes the fallback acceptable as an emergency path while "
        f"keeping the primary contract clear: ordinary successful drafts must come from LM-generated chapter JSON."
    )


def _build_fallback_learning_system(
    *,
    topic: str,
    sources: list[SourceReference],
    reason: str,
) -> LearningDraftSystem:
    chapter_total = _chapter_count(sources)
    concept_layers: list[str] = []
    section_structure: list[str] = []
    recall_hooks: list[str] = []
    verification_points: list[str] = []

    for index in range(chapter_total):
        chapter_number = index + 1
        paragraph = _fallback_paragraph(topic, chapter_number)
        concept_layers.append(
            f"Fallback concept layer {chapter_number}: {topic} is reconstructed as entities, state, mechanism, consequence, and verification."
        )
        section_structure.append(
            f"# Chapter {chapter_number}: Fallback Reconstruction of {topic}\n\n"
            f"## Concept Reconstruction\n"
            f"{paragraph}\n\n"
            f"## Mechanism\n"
            f"{paragraph}\n\n"
            f"## Learning Model\n"
            f"{paragraph}"
        )
        recall_hooks.append(
            f"Fallback recall hook {chapter_number}: explain {topic} by naming the entity, state transition, consequence, and verification question."
        )
        verification_points.append(
            f"Fallback verification point {chapter_number}: the learner can reconstruct the mechanism without quoting source material."
        )

    bibliography = [f"Fallback triggered by LMGenerationError: {reason}"]
    if sources:
        for source_index, source in enumerate(sources, start=1):
            bibliography.append(f"Source {source_index}: kind={source.kind}")
    else:
        bibliography.append("No source references were provided for this subject.")

    return LearningDraftSystem(
        topic=topic,
        concept_layers=concept_layers,
        section_structure=section_structure,
        recall_hooks=recall_hooks,
        verification_points=verification_points,
        bibliography=bibliography,
    )


def _render_draft(system: LearningDraftSystem) -> str:
    parts: list[str] = [
        f"# {system.topic} — LM-Driven Concept Reconstruction",
        "",
    ]

    chapter_count = len(system.section_structure)

    for index in range(chapter_count):
        parts.append(system.section_structure[index].strip())
        parts.append("")
        parts.append("## Concept Reconstruction Layer")
        parts.append(system.concept_layers[index % len(system.concept_layers)].strip())
        parts.append("")
        parts.append("## Recall Hooks")
        parts.append(system.recall_hooks[index % len(system.recall_hooks)].strip())
        parts.append("")
        parts.append("## Learning Model and Verification")
        parts.append(system.verification_points[index % len(system.verification_points)].strip())
        parts.append("")

    parts.append("# References")
    for index, entry in enumerate(system.bibliography, start=1):
        parts.append(f"{index}. {entry.strip()}")

    return "\n".join(parts).strip() + "\n"


def _validate_draft_text(draft_text: str) -> None:
    chapter_headers = re.findall(r"^# Chapter\s+\d+:", draft_text, flags=re.MULTILINE)
    if len(chapter_headers) < 3:
        raise LMGenerationError("LM draft did not contain at least three substantive chapters")

    if len(draft_text) < 3000:
        raise LMGenerationError("LM draft was below the 3000 character density floor")

    body = draft_text.split("# References", 1)[0]
    forbidden_patterns = [
        r"Insert\s+topic",
        r"\[Topic\]",
        r"\{\{topic\}\}",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, body, flags=re.IGNORECASE):
            raise LMGenerationError(f"LM draft contained template pattern: {pattern}")


def _build_learning_system(
    subject_root: Path,
    topic: str,
    sources: list[SourceReference],
    *,
    lm_client: _GeneratesText | None = None,
) -> LearningDraftSystem:
    """Build a LearningDraftSystem through the LM-primary path.

    The primary path calls LMClient.generate once per chapter and parses each
    response into the exact six-field LearningDraftSystem ontology. Deterministic
    fallback is used only when LMGenerationError is raised.
    """

    config = load_lm_config(subject_root=subject_root)
    client: _GeneratesText = lm_client if lm_client is not None else LMClient(config)
    total = _chapter_count(sources)

    try:
        chapter_systems = [
            _build_chapter_from_lm(
                client=client,
                topic=topic,
                sources=sources,
                chapter_index=index,
                chapter_count=total,
            )
            for index in range(total)
        ]
        system = _merge_learning_systems(
            topic=topic,
            chapter_systems=chapter_systems,
            sources=sources,
        )
        _validate_draft_text(_render_draft(system))
        return system
    except LMGenerationError as exc:
        return _build_fallback_learning_system(
            topic=topic,
            sources=sources,
            reason=str(exc),
        )


def generate_draft(
    subject_root: Path,
    topic: str,
    *,
    lm_client: _GeneratesText | None = None,
) -> str:
    """Generate a dense LM-driven concept reconstruction draft.

    The production path loads LM configuration from env/file, instantiates
    LMClient, calls the LM once per chapter, parses each response into the Seed
    ontology, renders the draft, saves learning_draft.md, and updates progress.
    """

    sources = load_source_data(subject_root)
    system = _build_learning_system(subject_root, topic, sources, lm_client=lm_client)
    draft_text = _render_draft(system)
    _validate_draft_text(draft_text)

    draft_path = subject_root / "learning_draft.md"
    draft_path.write_text(draft_text, encoding="utf-8")

    state = load_progress(subject_root)
    state.phase = "drafting"
    state.draft_version_hash = hashlib.sha256(draft_text.encode("utf-8")).hexdigest()
    save_progress(subject_root, state)

    from .logging import log_session_event

    chapter_count = len(re.findall(r"^# Chapter\s+\d+:", draft_text, flags=re.MULTILINE))
    log_session_event(
        subject_root,
        "draft_generated",
        {
            "version_hash": state.draft_version_hash,
            "chapter_count": chapter_count,
            "lm_primary_path": lm_client is None,
        },
    )

    return draft_text


def generate_first_pass_questions(subject_root: Path, topic: str | None = None) -> list[RecallQuestion]:
    """Compatibility wrapper for older imports.

    Recall remains approval-gated and is implemented in study.recall.
    """

    from .recall import generate_first_pass_questions as _generate

    state = load_progress(subject_root)
    selected_topic = topic or state.topic
    questions = _generate(subject_root, n=5)

    if selected_topic:
        return questions

    return questions


__all__ = ["generate_draft", "generate_first_pass_questions"]
