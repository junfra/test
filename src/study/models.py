"""Pydantic models for the study harness."""
from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal

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
    "LearningDraftRule",
]


class LearningDraftRule(BaseModel):
    """Validation rules for generated learning drafts."""

    DEFAULT_REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
        "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문",
    ]

    target_audience: str = Field(default="first-time learners")
    min_body_length_chars: int = Field(default=5000)
    recommended_body_length_range: dict[str, int] = Field(
        default_factory=lambda: {"min": 5000, "max": 7000}
    )
    required_sections: list[str] = Field(
        default_factory=lambda: LearningDraftRule.DEFAULT_REQUIRED_SECTIONS.copy()
    )
    required_functions: list[str] = Field(default_factory=lambda: [
        "necessity_judgment", "boundary_judgment", "mechanism_judgment",
        "correctness_judgment", "failure_diagnosis", "verification_judgment",
        "similarity_boundary_judgment", "self_explanation_prompt",
        "judgment_function_per_paragraph",
    ])
    prohibited_patterns: list[str] = Field(default_factory=lambda: [
        "template_placeholder", "format_only_section_compliance",
        "generic_importance_claim", "repeated_boilerplate",
        "thin_section_body", "unsupported_advantage_praise",
        "procedure_without_causality",
    ])
    density_tests: list[str] = Field(default_factory=lambda: [
        "body_length_excludes_title_toc_references",
        "strict_required_section_order", "minimum_section_body_length",
        "judgment_function_per_paragraph", "low_repetition_ratio",
        "format_only_section_compliance", "causal_linkage_across_core_sections",
    ])
    pass_criteria: str = Field(
        default="Pass only when the draft has 5000+ body characters, all 8 required sections in strict order..."
    )

    @classmethod
    def default(cls) -> "LearningDraftRule":
        return cls()

    def with_overrides(self, **overrides: Any) -> "LearningDraftRule":
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        data.update(overrides)
        return type(self)(**data)
