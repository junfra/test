"""Tests for config loading from env/file."""
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
