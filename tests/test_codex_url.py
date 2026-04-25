"""Tests for Codex Project URL injection."""

from __future__ import annotations


def test_codex_url_read_from_env(monkeypatch):
    monkeypatch.setenv("CODEX_PROJECT_URL", "http://localhost:3000")
    from oracle_plus.browser_mode import get_codex_url

    assert get_codex_url() == "http://localhost:3000"


def test_codex_url_injected_for_port_9473(monkeypatch):
    monkeypatch.setenv("CODEX_PROJECT_URL", "http://localhost:3000")
    from oracle_plus.browser_mode import build_oracle_args

    args = build_oracle_args(
        url="https://example.com",
        port=9473,
        passthrough=tuple(),
        remote_host="127.0.0.1:9473",
        remote_token="token",
    )
    assert "--chatgpt-url" in args
    assert "http://localhost:3000" in args


def test_codex_url_not_injected_for_other_ports(monkeypatch):
    monkeypatch.setenv("CODEX_PROJECT_URL", "http://localhost:3000")
    from oracle_plus.browser_mode import should_inject_codex_project_url

    assert should_inject_codex_project_url("127.0.0.1:9474", tuple()) is False
