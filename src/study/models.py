"""Pydantic models for the study harness."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, field_validator


class SubjectId(str):
    """Custom newtype wrapping str for subject identifiers."""


class SourceReference(BaseModel):
    kind: Literal["native", "web_search", "user_file", "pasted_text"]
    content: str
    metadata: dict = {}


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
    def validate_weakness_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"weakness_score must be in [0, 1], got {v}")
        return v


class ProgressState(BaseModel):
    subject_id: str
    topic: str
    phase: Literal["intake", "drafting", "draft_approved", "recall_first_pass", "recall_adaptive"] = "intake"
    approval_status: bool = False
    draft_version_hash: str | None = None
    first_pass_complete: bool = False
    next_recursors_cursor: int = 0
    weak_points: list[WeakPoint] = []
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
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid ISO-8601 timestamp: {v}")
        return v
