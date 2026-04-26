# Implementation Plan v5 — Study Harness LM Reconstruction Upgrade

Target artifact: `/home/user01/project/study/my-study/.worktree/study-harness/PLAN.md`

This v5 plan fixes the v4 failure directly: the LM must generate each chapter’s actual content, not merely enrich a deterministic template. The reset brief explicitly rejects one-call LM enrichment and requires `_build_learning_system` to call `LMClient.generate()` for each chapter, parse each response into the Seed ontology, and use deterministic fallback only on `LMGenerationError`. 

The current `drafting.py` is still template-centered through `_build_chapter()` and `_build_bibliography()`, while `generate_draft()` assembles deterministic chapter bodies from sources.  The current `models.py` also lacks both `LMConfig` and the exact six-field `LearningDraftSystem` ontology.  This plan replaces that path.

---

## Header

**Revision:** v5
**Owner:** oracle
**Repo:** `/home/user01/project/study/my-study/.worktree/study-harness`
**Target branch:** `study-harness-impl`
**Primary files:**

```text
src/study/models.py
src/study/config.py
src/study/lm_client.py
src/study/prompt_builder.py
src/study/drafting.py
src/study/recall.py
tests/test_lm_models.py
tests/test_config.py
tests/test_prompt_builder.py
tests/test_lm_client.py
tests/test_lm_drafting.py
tests/test_recall_lm_sections.py
tests/test_integration_lm_draft.py
```

## Goal

Upgrade draft generation so every generated learning draft is an **LM-driven concept reconstruction**, not source paraphrase and not deterministic template output. The primary path is:

```text
load sources
→ load LMConfig from env/file
→ instantiate LMClient
→ call LMClient.generate() once per chapter
→ parse each LM response into LearningDraftSystem
→ merge chapter systems into one LearningDraftSystem
→ render dense draft from LM-generated ontology fields
→ save learning_draft.md and progress state
```

The deterministic path is allowed only here:

```text
LMClient.generate() or LM output parsing raises LMGenerationError
→ build deterministic fallback LearningDraftSystem
→ render fallback draft
```

## Non-negotiable contract

`LearningDraftSystem` must have exactly these six Seed fields:

```text
topic
concept_layers
section_structure
recall_hooks
verification_points
bibliography
```

`LMConfig` must be a separate model.

`_build_learning_system()` must call `LMClient.generate()` for each chapter. It must not call the LM once for enrichment. It must not produce primary chapter bodies from `_generate_*` or `_build_chapter` templates.

---

# Task 0 — Baseline branch and failing-test posture

## Commands

```bash
cd /home/user01/project/study/my-study/.worktree/study-harness
git status --short
git branch --show-current
python -m pytest
```

Expected: current suite may pass before changes. New tests below must fail before implementation.

---

# Task 1 — Add failing tests for separate `LMConfig` and exact `LearningDraftSystem`

## Create `tests/test_lm_models.py`

```python
from pydantic import ValidationError

from study.models import LearningDraftSystem, LMConfig


def test_learning_draft_system_has_exact_seed_fields() -> None:
    assert set(LearningDraftSystem.model_fields) == {
        "topic",
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    }


def test_learning_draft_system_requires_dense_non_empty_arrays() -> None:
    system = LearningDraftSystem(
        topic="Operating Systems",
        concept_layers=["Processes become understandable when scheduling, isolation, and resource ownership are reconstructed together."],
        section_structure=["# Chapter 1: Process Model\n\n## Concept Reconstruction\nA process is not just a running program; it is an owned execution context."],
        recall_hooks=["Explain why a process needs both an address space and scheduler-visible state."],
        verification_points=["The learner can distinguish program text, process state, and scheduler behavior."],
        bibliography=["Source 1: pasted_text"],
    )

    assert system.topic == "Operating Systems"
    assert len(system.concept_layers) == 1


def test_learning_draft_system_rejects_blank_items() -> None:
    try:
        LearningDraftSystem(
            topic="Operating Systems",
            concept_layers=[""],
            section_structure=["# Chapter 1"],
            recall_hooks=["hook"],
            verification_points=["check"],
            bibliography=["Source 1"],
        )
    except ValidationError as exc:
        assert "blank" in str(exc).lower()
    else:
        raise AssertionError("blank ontology item should fail validation")


def test_lm_config_is_separate_from_learning_draft_system() -> None:
    config = LMConfig(provider="mock", model="mock-dense-reconstruction")

    assert config.provider == "mock"
    assert "provider" not in LearningDraftSystem.model_fields
    assert "model" not in LearningDraftSystem.model_fields
```

## Run

```bash
python -m pytest tests/test_lm_models.py
```

Expected: fails because neither model exists yet.

---

# Task 2 — Implement `LMConfig` and exact `LearningDraftSystem`

## Replace `src/study/models.py` with this full code

```python
"""Pydantic models for the study harness."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SubjectId(str):
    """Custom newtype wrapping str for subject identifiers."""


class ApprovalRequiredError(Exception):
    """Raised when recall functions are called without draft approval."""


class LMConfig(BaseModel):
    """Configuration for the language model provider.

    This model is intentionally separate from LearningDraftSystem so the Seed
    ontology remains exactly six fields.
    """

    provider: Literal["mock", "openai", "ollama"] = "mock"
    model: str = "mock-dense-reconstruction"
    base_url: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 60

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model must not be blank")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value


class LearningDraftSystem(BaseModel):
    """Seed ontology for LM-generated learning drafts.

    This class must keep exactly the six fields from the Seed ontology.
    """

    topic: str
    concept_layers: list[str] = Field(min_length=1)
    section_structure: list[str] = Field(min_length=1)
    recall_hooks: list[str] = Field(min_length=1)
    verification_points: list[str] = Field(min_length=1)
    bibliography: list[str] = Field(min_length=1)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("topic must not be blank")
        return value.strip()

    @field_validator(
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    )
    @classmethod
    def validate_non_blank_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("LearningDraftSystem arrays must not contain blank items")
        return cleaned


class SourceReference(BaseModel):
    kind: Literal["native", "web_search", "user_file", "pasted_text"]
    content: str
    metadata: dict = Field(default_factory=dict)


class RecallQuestion(BaseModel):
    id: str
    topic: str
    prompt: str
    answer: str | None = None
    score: float | None = None


class WeakPoint(BaseModel):
    topic: str
    misconception_explanation: str
    weakness_score: float
    retest_count: int = 0

    @field_validator("weakness_score")
    @classmethod
    def validate_weakness_score(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"weakness_score must be in [0, 1], got {value}")
        return value


class ProgressState(BaseModel):
    subject_id: str
    topic: str
    phase: Literal[
        "intake",
        "drafting",
        "draft_approved",
        "recall_first_pass",
        "recall_adaptive",
    ] = "intake"
    approval_status: bool = False
    draft_version_hash: str | None = None
    first_pass_complete: bool = False
    next_recursors_cursor: int = 0
    weak_points: list[WeakPoint] = Field(default_factory=list)
    source_manifest_count: int = 0


class RecallSessionEntry(BaseModel):
    session_id: str
    questions: list[RecallQuestion]
    answers: list[str] | None = None
    scores: list[float] | None = None
    outcome: Literal["pass", "fail", "partial"]
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid ISO-8601 timestamp: {value}")
        return value


__all__ = [
    "ApprovalRequiredError",
    "LearningDraftSystem",
    "LMConfig",
    "ProgressState",
    "RecallQuestion",
    "RecallSessionEntry",
    "SourceReference",
    "SubjectId",
    "WeakPoint",
]
```

## Run

```bash
python -m pytest tests/test_lm_models.py
```

Expected: pass.

---

# Task 3 — Add failing tests for env/file config loading

## Create `tests/test_config.py`

```python
import json

from study.config import load_lm_config


def test_load_lm_config_defaults_to_mock_without_hardcoding_in_drafting(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STUDY_LM_PROVIDER", raising=False)
    monkeypatch.delenv("STUDY_LM_MODEL", raising=False)
    monkeypatch.delenv("STUDY_LM_BASE_URL", raising=False)
    monkeypatch.delenv("STUDY_LM_API_KEY", raising=False)
    monkeypatch.delenv("STUDY_LM_TIMEOUT_SECONDS", raising=False)

    config = load_lm_config(workspace_root=tmp_path)

    assert config.provider == "mock"
    assert config.model == "mock-dense-reconstruction"


def test_load_lm_config_from_workspace_file(tmp_path) -> None:
    (tmp_path / "study_lm.json").write_text(
        json.dumps(
            {
                "provider": "ollama",
                "model": "llama3.1",
                "base_url": "http://localhost:11434",
                "timeout_seconds": 45,
            }
        ),
        encoding="utf-8",
    )

    config = load_lm_config(workspace_root=tmp_path)

    assert config.provider == "ollama"
    assert config.model == "llama3.1"
    assert config.base_url == "http://localhost:11434"
    assert config.timeout_seconds == 45


def test_env_overrides_file_config(tmp_path, monkeypatch) -> None:
    (tmp_path / "study_lm.json").write_text(
        json.dumps(
            {
                "provider": "mock",
                "model": "mock-dense-reconstruction",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STUDY_LM_PROVIDER", "openai")
    monkeypatch.setenv("STUDY_LM_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("STUDY_LM_BASE_URL", "https://api.openai.com/v1/chat/completions")
    monkeypatch.setenv("STUDY_LM_API_KEY", "test-key")
    monkeypatch.setenv("STUDY_LM_TIMEOUT_SECONDS", "30")

    config = load_lm_config(workspace_root=tmp_path)

    assert config.provider == "openai"
    assert config.model == "gpt-4.1-mini"
    assert config.base_url == "https://api.openai.com/v1/chat/completions"
    assert config.api_key == "test-key"
    assert config.timeout_seconds == 30
```

## Run

```bash
python -m pytest tests/test_config.py
```

Expected: fails because `study.config` does not exist.

---

# Task 4 — Implement config loading

## Create `src/study/config.py`

```python
"""LM configuration loading from workspace files and environment variables."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import LMConfig


def _read_json_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"LM config file must contain a JSON object: {path}")
    return data


def _candidate_config_paths(
    *,
    subject_root: Path | None,
    workspace_root: Path | None,
) -> list[Path]:
    paths: list[Path] = []

    if workspace_root is not None:
        paths.append(workspace_root / "study_lm.json")
        paths.append(workspace_root / ".study_lm.json")

    if subject_root is not None:
        paths.append(subject_root / "lm_config.json")
        if subject_root.parent.name == "subjects":
            inferred_workspace = subject_root.parent.parent
            paths.append(inferred_workspace / "study_lm.json")
            paths.append(inferred_workspace / ".study_lm.json")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            deduped.append(path)
            seen.add(resolved)

    return deduped


def _env_config() -> dict[str, Any]:
    mapping = {
        "STUDY_LM_PROVIDER": "provider",
        "STUDY_LM_MODEL": "model",
        "STUDY_LM_BASE_URL": "base_url",
        "STUDY_LM_API_KEY": "api_key",
        "STUDY_LM_TIMEOUT_SECONDS": "timeout_seconds",
    }

    values: dict[str, Any] = {}
    for env_name, field_name in mapping.items():
        raw = os.environ.get(env_name)
        if raw is not None and raw.strip():
            values[field_name] = raw.strip()

    return values


def load_lm_config(
    *,
    subject_root: Path | None = None,
    workspace_root: Path | None = None,
) -> LMConfig:
    """Load LMConfig from config files, then environment overrides.

    The default provider comes from LMConfig itself. Drafting code must call this
    loader rather than instantiate LMConfig(provider="mock") directly.
    """

    merged: dict[str, Any] = {}

    for path in _candidate_config_paths(subject_root=subject_root, workspace_root=workspace_root):
        merged.update(_read_json_config(path))

    merged.update(_env_config())

    return LMConfig.model_validate(merged)


__all__ = ["load_lm_config"]
```

## Run

```bash
python -m pytest tests/test_config.py
```

Expected: pass.

---

# Task 5 — Add failing tests for chapter prompt construction

## Create `tests/test_prompt_builder.py`

```python
from study.models import SourceReference
from study.prompt_builder import build_chapter_prompt


def test_build_chapter_prompt_demands_exact_seed_json_fields() -> None:
    prompt = build_chapter_prompt(
        topic="Distributed Systems",
        sources=[
            SourceReference(
                kind="pasted_text",
                content="Consensus coordinates replicas under failure without relying on shared memory.",
                metadata={"keyword": "consensus"},
            )
        ],
        chapter_index=0,
        chapter_count=3,
    )

    assert "Return only valid JSON" in prompt
    assert '"topic"' in prompt
    assert '"concept_layers"' in prompt
    assert '"section_structure"' in prompt
    assert '"recall_hooks"' in prompt
    assert '"verification_points"' in prompt
    assert '"bibliography"' in prompt


def test_build_chapter_prompt_forbids_source_copy_paste_body() -> None:
    prompt = build_chapter_prompt(
        topic="Databases",
        sources=[
            SourceReference(
                kind="pasted_text",
                content="Indexes trade write cost for read-path selectivity and access-path control.",
                metadata={},
            )
        ],
        chapter_index=1,
        chapter_count=3,
    )

    assert "Do not copy source paragraphs into the chapter body" in prompt
    assert "bibliography" in prompt.lower()
    assert "Chapter 2 of 3" in prompt
```

## Run

```bash
python -m pytest tests/test_prompt_builder.py
```

Expected: fails because `prompt_builder.py` does not exist.

---

# Task 6 — Implement prompt builder

## Create `src/study/prompt_builder.py`

```python
"""Prompt construction for LM-driven chapter generation."""
from __future__ import annotations

from .models import SourceReference


def _compact_text(text: str, limit: int = 700) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _source_packet(sources: list[SourceReference]) -> str:
    if not sources:
        return "No source material was provided. Build a conceptual primer from general domain knowledge."

    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        keyword = source.metadata.get("keyword", "")
        keyword_text = f", keyword={keyword}" if keyword else ""
        lines.append(
            f"Source {index}: kind={source.kind}{keyword_text}\n"
            f"Digest: {_compact_text(source.content)}"
        )

    return "\n\n".join(lines)


def build_chapter_prompt(
    *,
    topic: str,
    sources: list[SourceReference],
    chapter_index: int,
    chapter_count: int,
) -> str:
    chapter_number = chapter_index + 1

    return f"""You are generating an LM-driven concept reconstruction chapter.

Topic: {topic}
Chapter: Chapter {chapter_number} of {chapter_count}

Source digests:
{_source_packet(sources)}

Hard requirements:
- The LM must generate the actual chapter content.
- Do not copy source paragraphs into the chapter body.
- Use sources as evidence and bibliography material, not as body prose.
- Write dense Red Hat-style explanatory structure: concept, mechanism, consequence, recall hook, verification point.
- Make this chapter substantive enough that three chapters together exceed 3000 characters.
- Each major section must surface concept reconstruction, recall hooks, and the learning model.
- Return only valid JSON.
- The JSON object must contain exactly these fields:
  "topic": string
  "concept_layers": array of strings
  "section_structure": array of strings
  "recall_hooks": array of strings
  "verification_points": array of strings
  "bibliography": array of strings

The "section_structure" value must contain the actual markdown chapter body for this chapter.
The chapter body must start with "# Chapter {chapter_number}:" and include "## Concept Reconstruction", "## Mechanism", and "## Learning Model".
"""


__all__ = ["build_chapter_prompt"]
```

## Run

```bash
python -m pytest tests/test_prompt_builder.py
```

Expected: pass.

---

# Task 7 — Add failing tests for LM client providers and mock dense output

## Create `tests/test_lm_client.py`

```python
from study.lm_client import LMClient, LMGenerationError, parse_learning_system_json
from study.models import LMConfig, LearningDraftSystem
from study.prompt_builder import build_chapter_prompt


def test_mock_lm_generates_parseable_learning_draft_system() -> None:
    prompt = build_chapter_prompt(
        topic="Operating Systems",
        sources=[],
        chapter_index=0,
        chapter_count=3,
    )

    client = LMClient(LMConfig(provider="mock", model="mock-dense-reconstruction"))
    raw = client.generate(prompt)
    system = parse_learning_system_json(raw)

    assert isinstance(system, LearningDraftSystem)
    assert set(system.model_fields) == {
        "topic",
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    }
    assert system.topic == "Operating Systems"
    assert "# Chapter 1:" in system.section_structure[0]
    assert len(system.section_structure[0]) > 700
    assert len(system.concept_layers[0]) > 200


def test_parse_learning_system_json_rejects_non_json() -> None:
    try:
        parse_learning_system_json("not json")
    except LMGenerationError as exc:
        assert "valid json" in str(exc).lower()
    else:
        raise AssertionError("invalid LM output should raise LMGenerationError")


def test_lm_client_rejects_unknown_provider() -> None:
    try:
        LMClient(LMConfig.model_validate({"provider": "unknown", "model": "x"}))
    except Exception as exc:
        assert "provider" in str(exc).lower()
    else:
        raise AssertionError("unknown provider should fail validation")
```

## Run

```bash
python -m pytest tests/test_lm_client.py
```

Expected: fails because `lm_client.py` does not exist.

---

# Task 8 — Implement LM client and parser

## Create `src/study/lm_client.py`

````python
"""Language model client adapters for study draft generation."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from pydantic import ValidationError

from .models import LMConfig, LearningDraftSystem


class LMGenerationError(RuntimeError):
    """Raised when an LM provider fails or returns invalid ontology output."""


def _extract_topic(prompt: str) -> str:
    match = re.search(r"^Topic:\s*(.+)$", prompt, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled Topic"


def _extract_chapter_number(prompt: str) -> int:
    match = re.search(r"Chapter\s+(\d+)\s+of\s+\d+", prompt)
    if match:
        return int(match.group(1))
    return 1


def _mock_dense_response(prompt: str) -> str:
    topic = _extract_topic(prompt)
    chapter_number = _extract_chapter_number(prompt)

    section = (
        f"# Chapter {chapter_number}: {topic} Concept Reconstruction\n\n"
        f"## Concept Reconstruction\n"
        f"This chapter reconstructs {topic} from the bottom up instead of repeating source wording. "
        f"The central move is to identify the object being studied, the forces acting on it, the decisions "
        f"the learner must make, and the consequences that follow from those decisions. A dense explanation "
        f"does not begin with a definition alone. It begins with the reason the definition exists, the pressure "
        f"that makes the concept necessary, and the boundary that separates this concept from nearby ideas. "
        f"For {topic}, the learner should treat each term as part of a working system: a name points to a role, "
        f"a role participates in a mechanism, and the mechanism creates observable behavior.\n\n"
        f"## Mechanism\n"
        f"The mechanism in this chapter is built as a chain. First, the learner isolates the primitive entities. "
        f"Second, the learner asks what state each entity owns. Third, the learner follows how state changes when "
        f"the system receives input, pressure, conflict, or failure. Fourth, the learner explains why the resulting "
        f"behavior is useful, risky, or limited. This is Red Hat-style learning because it favors operational clarity: "
        f"what exists, what it does, how it changes, how to inspect it, and how to know whether the explanation is "
        f"working. The point is not to memorize a paragraph. The point is to rebuild the system until the learner can "
        f"predict the next consequence.\n\n"
        f"## Learning Model\n"
        f"The learning model for this chapter is reconstruction, compression, and verification. Reconstruction means "
        f"the learner can rebuild {topic} without looking at the source. Compression means the learner can express the "
        f"core mechanism in a smaller form without losing causal detail. Verification means the learner can answer a "
        f"question that changes the surface wording while preserving the same underlying structure. If the learner can "
        f"explain the primitive entity, the state transition, the failure mode, and the practical check, the chapter has "
        f"done its job."
    )

    concept = (
        f"Chapter {chapter_number} concept layer for {topic}: the learner reconstructs the concept as a system of "
        f"entities, owned state, mechanisms, consequences, and checks. This layer is deliberately generative rather "
        f"than derivative; it explains why the concept must exist and how its parts interact."
    )

    recall = (
        f"Recall hook for chapter {chapter_number}: explain {topic} by naming the primitive entity, the state it owns, "
        f"the mechanism that changes the state, the consequence of that change, and the inspection question that proves "
        f"you understand it."
    )

    verification = (
        f"Verification point for chapter {chapter_number}: the learner can reconstruct the chapter without source text, "
        f"can distinguish mechanism from definition, and can predict what would break if one part of the mechanism were "
        f"removed or inverted."
    )

    payload = {
        "topic": topic,
        "concept_layers": [concept],
        "section_structure": [section],
        "recall_hooks": [recall],
        "verification_points": [verification],
        "bibliography": [f"Chapter {chapter_number} uses source digests as references rather than body prose."],
    }

    return json.dumps(payload)


def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise LMGenerationError("LM output was not valid JSON for LearningDraftSystem")

    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LMGenerationError("LM output was not valid JSON for LearningDraftSystem") from exc

    if not isinstance(data, dict):
        raise LMGenerationError("LM output JSON must be an object")

    return data


def parse_learning_system_json(raw: str) -> LearningDraftSystem:
    data = _extract_json_object(raw)

    allowed = {
        "topic",
        "concept_layers",
        "section_structure",
        "recall_hooks",
        "verification_points",
        "bibliography",
    }

    extra = set(data) - allowed
    missing = allowed - set(data)

    if extra:
        raise LMGenerationError(f"LM output contained non-Seed fields: {sorted(extra)}")
    if missing:
        raise LMGenerationError(f"LM output missed Seed fields: {sorted(missing)}")

    try:
        return LearningDraftSystem.model_validate(data)
    except ValidationError as exc:
        raise LMGenerationError("LM output did not satisfy LearningDraftSystem ontology") from exc


class LMClient:
    """Provider-dispatching LM client."""

    def __init__(self, config: LMConfig):
        self.config = config

    def generate(self, prompt: str) -> str:
        if self.config.provider == "mock":
            return _mock_dense_response(prompt)
        if self.config.provider == "openai":
            return self._generate_openai(prompt)
        if self.config.provider == "ollama":
            return self._generate_ollama(prompt)
        raise LMGenerationError(f"Unsupported LM provider: {self.config.provider}")

    def _generate_openai(self, prompt: str) -> str:
        if not self.config.api_key:
            raise LMGenerationError("OpenAI provider requires STUDY_LM_API_KEY or api_key in config")

        url = self.config.base_url or "https://api.openai.com/v1/chat/completions"
        body = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LMGenerationError("OpenAI generation failed") from exc

        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LMGenerationError("OpenAI response did not contain message content") from exc

    def _generate_ollama(self, prompt: str) -> str:
        url = self.config.base_url or "http://localhost:11434/api/generate"
        body = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LMGenerationError("Ollama generation failed") from exc

        try:
            return payload["response"]
        except (KeyError, TypeError) as exc:
            raise LMGenerationError("Ollama response did not contain generated text") from exc


__all__ = ["LMClient", "LMGenerationError", "parse_learning_system_json"]
````

## Run

```bash
python -m pytest tests/test_lm_client.py
```

Expected: pass.

---

# Task 9 — Add failing tests that prove drafting calls the LM once per chapter

## Create `tests/test_lm_drafting.py`

```python
import json
from pathlib import Path

from study.drafting import _build_learning_system, generate_draft
from study.lm_client import LMGenerationError
from study.models import ProgressState, SourceReference
from study.storage import save_progress


class TrackingLMClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        chapter_number = len(self.calls)
        return json.dumps(
            {
                "topic": "Distributed Systems",
                "concept_layers": [
                    f"LM_UNIQUE_CONCEPT_LAYER_{chapter_number}: Distributed systems are reconstructed through nodes, messages, time, failure, coordination, and verification."
                ],
                "section_structure": [
                    (
                        f"# Chapter {chapter_number}: LM_UNIQUE_CHAPTER_BODY_{chapter_number}\n\n"
                        f"## Concept Reconstruction\n"
                        f"LM_UNIQUE_CHAPTER_BODY_{chapter_number} reconstructs the topic as a causal system rather than a copied source. "
                        f"The learner identifies the entity, its state, its message boundary, and the failure pressure that makes coordination necessary. "
                        f"This generated body is intentionally long enough to be substantive and proves the chapter came from the LM response.\n\n"
                        f"## Mechanism\n"
                        f"The mechanism connects local decisions to system-wide behavior. A node observes a partial view, sends messages, waits under uncertainty, "
                        f"and must still preserve an invariant. The explanation emphasizes how the learner can rebuild the mechanism without memorizing source text.\n\n"
                        f"## Learning Model\n"
                        f"The learning model asks the learner to reconstruct the primitive entity, compress the mechanism, and verify the invariant under a changed scenario."
                    )
                ],
                "recall_hooks": [
                    f"LM_UNIQUE_RECALL_HOOK_{chapter_number}: explain node state, message uncertainty, and invariant preservation."
                ],
                "verification_points": [
                    f"LM_UNIQUE_VERIFICATION_{chapter_number}: predict what breaks when messages arrive late or contradictory state is observed."
                ],
                "bibliography": [f"LM bibliography entry {chapter_number}"],
            }
        )


class FailingLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        raise LMGenerationError("forced provider failure")


def _subject_root(tmp_path: Path) -> Path:
    root = tmp_path / "subjects" / "dist-sys"
    root.mkdir(parents=True)
    (root / "source_reference_data").mkdir()
    (root / "session_logs").mkdir()
    save_progress(
        root,
        ProgressState(
            subject_id="dist-sys",
            topic="Distributed Systems",
            phase="intake",
            approval_status=False,
        ),
    )
    return root


def test_build_learning_system_calls_lm_for_each_chapter(tmp_path) -> None:
    root = _subject_root(tmp_path)
    sources = [
        SourceReference(kind="pasted_text", content="Consensus handles replicated agreement under failure.", metadata={}),
        SourceReference(kind="pasted_text", content="Replication improves availability but introduces consistency boundaries.", metadata={}),
    ]
    client = TrackingLMClient()

    system = _build_learning_system(root, "Distributed Systems", sources, lm_client=client)

    assert len(client.calls) == 3
    assert len(system.section_structure) == 3
    assert "LM_UNIQUE_CHAPTER_BODY_1" in system.section_structure[0]
    assert "LM_UNIQUE_CONCEPT_LAYER_2" in system.concept_layers[1]
    assert "LM_UNIQUE_RECALL_HOOK_3" in system.recall_hooks[2]


def test_generate_draft_renders_lm_generated_chapter_content(tmp_path) -> None:
    root = _subject_root(tmp_path)
    client = TrackingLMClient()

    draft = generate_draft(root, "Distributed Systems", lm_client=client)

    assert len(client.calls) == 3
    assert "LM_UNIQUE_CHAPTER_BODY_1" in draft
    assert "LM_UNIQUE_CHAPTER_BODY_2" in draft
    assert "LM_UNIQUE_CHAPTER_BODY_3" in draft
    assert "LM_UNIQUE_RECALL_HOOK_1" in draft
    assert "# References" in draft
    assert len(draft) >= 3000


def test_lm_generation_error_is_the_only_fallback_path(tmp_path) -> None:
    root = _subject_root(tmp_path)
    client = FailingLMClient()

    draft = generate_draft(root, "Distributed Systems", lm_client=client)

    assert client.calls == 1
    assert "Deterministic fallback reconstruction" in draft
    assert "# References" in draft
    assert len(draft) >= 3000
```

## Run

```bash
python -m pytest tests/test_lm_drafting.py
```

Expected: fails because current `drafting.py` still uses deterministic `_build_chapter()`. 

---

# Task 10 — Replace drafting with LM-primary chapter generation

## Replace `src/study/drafting.py` with this full code

```python
"""Learning draft generation engine — LM-driven concept reconstruction.

All public functions receive ``subject_root: pathlib.Path`` — no bare root paths.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol

from .config import load_lm_config
from .intake import load_source_data
from .lm_client import LMClient, LMGenerationError, parse_learning_system_json
from .models import LearningDraftSystem, ProgressState, RecallQuestion, SourceReference
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
```

## Run

```bash
python -m pytest tests/test_lm_drafting.py
```

Expected: pass.

---

# Task 11 — Add tests proving mock LM fills ontology and generates dense drafts

## Create `tests/test_integration_lm_draft.py`

```python
from pathlib import Path

from study.drafting import generate_draft
from study.intake import add_sources
from study.models import ProgressState, SourceReference
from study.storage import load_progress, save_progress


def _make_subject(tmp_path: Path) -> Path:
    root = tmp_path / "subjects" / "os"
    root.mkdir(parents=True)
    (root / "source_reference_data").mkdir()
    (root / "session_logs").mkdir()
    save_progress(
        root,
        ProgressState(
            subject_id="os",
            topic="Operating Systems",
            phase="intake",
            approval_status=False,
        ),
    )
    return root


def test_mock_lm_draft_is_dense_sectioned_and_non_derivative(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STUDY_LM_PROVIDER", "mock")
    monkeypatch.setenv("STUDY_LM_MODEL", "mock-dense-reconstruction")

    root = _make_subject(tmp_path)
    copied_sentence = "THIS EXACT SOURCE SENTENCE SHOULD NOT DRIVE THE BODY."
    add_sources(
        root,
        [
            SourceReference(
                kind="pasted_text",
                content=f"{copied_sentence} Processes isolate execution state and scheduling state.",
                metadata={"keyword": "process"},
            )
        ],
    )

    draft = generate_draft(root, "Operating Systems")

    assert len(draft) >= 3000
    assert draft.count("# Chapter ") >= 3
    assert "## Concept Reconstruction" in draft
    assert "## Recall Hooks" in draft
    assert "## Learning Model" in draft
    assert "# References" in draft
    assert copied_sentence not in draft.split("# References", 1)[0]

    state = load_progress(root)
    assert state.phase == "drafting"
    assert state.draft_version_hash is not None
    assert len(state.draft_version_hash) == 64
```

## Run

```bash
python -m pytest tests/test_integration_lm_draft.py
```

Expected: pass.

---

# Task 12 — Add recall extraction tests for LM section structure

The existing recall engine preserves approval gating, but its section parser currently checks generic markdown headers before `##` section headers, which can hide intended sections in LM-generated drafts. Recall must continue to work with approval gates and generated section structure. 

## Create `tests/test_recall_lm_sections.py`

```python
from pathlib import Path

from study.models import ProgressState
from study.recall import extract_sections, generate_first_pass_questions
from study.storage import save_progress


def test_extract_sections_reads_lm_generated_chapter_subsections() -> None:
    draft = """# Operating Systems — LM-Driven Concept Reconstruction

# Chapter 1: Process Reconstruction

## Concept Reconstruction
A process is an owned execution context.

## Mechanism
The scheduler changes observable execution.

## Learning Model
The learner reconstructs state, transition, and check.

# References
1. Source 1
"""

    sections = extract_sections(draft)

    titles = [title for _chapter, title, _content in sections]
    assert "Concept Reconstruction" in titles
    assert "Mechanism" in titles
    assert "Learning Model" in titles


def test_recall_questions_remain_approval_gated_for_lm_draft(tmp_path) -> None:
    root = tmp_path / "subjects" / "os"
    root.mkdir(parents=True)
    save_progress(
        root,
        ProgressState(
            subject_id="os",
            topic="Operating Systems",
            phase="draft_approved",
            approval_status=True,
            draft_version_hash="a" * 64,
        ),
    )
    (root / "learning_draft.md").write_text(
        """# Operating Systems — LM-Driven Concept Reconstruction

# Chapter 1: Process Reconstruction

## Concept Reconstruction
A process is an owned execution context.

## Mechanism
The scheduler changes observable execution.

## Learning Model
The learner reconstructs state, transition, and check.

# References
1. Source 1
""",
        encoding="utf-8",
    )

    questions = generate_first_pass_questions(root, n=3)

    assert len(questions) == 3
    assert questions[0].topic == "Concept Reconstruction"
```

## Run

```bash
python -m pytest tests/test_recall_lm_sections.py
```

Expected: parser test may fail until recall is fixed.

---

# Task 13 — Fix recall extraction for LM-generated sections

## Patch `extract_sections()` in `src/study/recall.py`

Replace the current `extract_sections()` function with:

```python
def extract_sections(draft_text: str) -> list[tuple[str, str, str]]:
    """Parse a markdown draft into (chapter, section_title, content) tuples.

    Sections are identified by ``##`` headers inside ``# Chapter`` blocks.
    Top-level title and references are ignored.
    """

    lines = draft_text.splitlines()
    sections: list[tuple[str, str, str]] = []

    current_chapter: str | None = None
    current_title: str | None = None
    section_lines: list[str] = []

    def flush() -> None:
        nonlocal section_lines, current_title, current_chapter
        if current_chapter and current_title:
            sections.append((current_chapter, current_title, "\n".join(section_lines).strip()))
        section_lines = []

    for line in lines:
        if re.match(r"^#\s+References\s*$", line):
            flush()
            break

        if re.match(r"^#\s+Chapter\s+\d+:", line):
            flush()
            current_chapter = line.strip().lstrip("# ").strip()
            current_title = None
            section_lines = []
            continue

        if re.match(r"^##\s+", line):
            flush()
            current_title = line.strip().lstrip("# ").strip()
            section_lines = [line]
            continue

        if current_title:
            section_lines.append(line)

    flush()
    return sections
```

## Run

```bash
python -m pytest tests/test_recall_lm_sections.py
```

Expected: pass.

---

# Task 14 — Run targeted LM suite

## Command

```bash
python -m pytest \
  tests/test_lm_models.py \
  tests/test_config.py \
  tests/test_prompt_builder.py \
  tests/test_lm_client.py \
  tests/test_lm_drafting.py \
  tests/test_recall_lm_sections.py \
  tests/test_integration_lm_draft.py
```

Expected: pass.

---

# Task 15 — Run full suite and protect existing behavior

The CLI still calls `generate_draft(subject_dir, state.topic)` and does not need to know about providers; configuration is loaded behind the drafting boundary. The current CLI’s draft command already loads progress state and invokes `generate_draft`.  Subject creation, approval, storage, and intake paths remain file-backed and subject-root based.   

## Command

```bash
python -m pytest
```

Expected: pass.

If old tests assert deterministic source text appears in the body, update those tests to assert the opposite: source material belongs in `# References`, while the body is reconstructed synthesis.

---

# Task 16 — CLI smoke test with mock LM provider

## Commands

```bash
cd /home/user01/project/study/my-study/.worktree/study-harness
tmpdir="$(mktemp -d)"
cd "$tmpdir"

STUDY_LM_PROVIDER=mock study subjects new os "Operating Systems"
STUDY_LM_PROVIDER=mock study intake os --text "Processes isolate memory, scheduler-visible state, and resource ownership."
STUDY_LM_PROVIDER=mock study draft os

test -f subjects/os/learning_draft.md
python - <<'PY'
from pathlib import Path
draft = Path("subjects/os/learning_draft.md").read_text()
assert len(draft) >= 3000
assert draft.count("# Chapter ") >= 3
assert "## Concept Reconstruction" in draft
assert "## Recall Hooks" in draft
assert "## Learning Model" in draft
assert "# References" in draft
print("cli smoke passed")
PY
```

Expected: `cli smoke passed`.

---

# Task 17 — Final static checks against v5 drift

Run these checks before treating the plan as implemented.

```bash
python - <<'PY'
from study.models import LearningDraftSystem

expected = {
    "topic",
    "concept_layers",
    "section_structure",
    "recall_hooks",
    "verification_points",
    "bibliography",
}
actual = set(LearningDraftSystem.model_fields)
assert actual == expected, actual
print("LearningDraftSystem exact Seed fields verified")
PY

grep -R "LMConfig(provider=\"mock\")" -n src/study && exit 1 || true
grep -R "def _generate_" -n src/study/drafting.py && exit 1 || true
grep -R "def _build_chapter" -n src/study/drafting.py && exit 1 || true
grep -R "client.generate" -n src/study/drafting.py
```

Expected:

```text
LearningDraftSystem exact Seed fields verified
```

`grep -R "client.generate"` must show the per-chapter call inside `_build_chapter_from_lm()`.

---

# Acceptance checklist

* `LearningDraftSystem` has exactly six Seed fields.
* `LMConfig` is separate.
* `config.py` loads provider settings from env/file.
* `drafting.py` does not instantiate `LMConfig(provider="mock")`.
* `_build_learning_system()` calls `LMClient.generate()` once per chapter.
* LM output is parsed into `LearningDraftSystem`.
* The rendered chapter body comes from `section_structure` returned by the LM.
* Deterministic fallback is reached only through `LMGenerationError`.
* Mock LM generates dense structured content that passes ontology, density, and chapter checks.
* Drafts have at least three substantive chapters and exceed 3000 characters.
* Source material appears in references rather than driving body copy.
* Approval-gated recall continues to work.
