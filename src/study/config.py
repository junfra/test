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
