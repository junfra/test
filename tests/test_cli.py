"""Tests for the top-level Oracle-Plus CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

import oracle_plus
import pytest


PROJECT_DIR = Path(__file__).resolve().parent.parent


def uv_run(*cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", *cmd],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def test_package_exports_main():
    assert callable(oracle_plus.main)


def test_help_prints_usage():
    result = uv_run("python", "-m", "oracle_plus", "--help")
    assert result.returncode == 0
    assert "oracle-plus" in result.stdout.lower()


def test_version_prints_package_version():
    result = uv_run("oracle-plus", "--version")
    assert result.returncode == 0
    assert "oracle-plus" in result.stdout.lower()


def test_help_bypasses_browser_dispatch(monkeypatch):
    called = []

    def fake_run_browser_cli(args):
        called.append(args)
        return 99

    monkeypatch.setattr("oracle_plus.browser_mode.run_browser_cli", fake_run_browser_cli)
    assert oracle_plus.main(["--help"]) == 0
    assert called == []


def test_non_help_args_are_forwarded_to_browser_dispatch(monkeypatch):
    seen = {}

    def fake_run_browser_cli(args):
        seen["args"] = list(args)
        return 7

    monkeypatch.setattr("oracle_plus.browser_mode.run_browser_cli", fake_run_browser_cli)
    assert oracle_plus.main(["status", "session-1"]) == 7
    assert seen["args"] == ["status", "session-1"]


def test_prompt_file_decode_error_returns_cli_error(tmp_path, capsys):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_bytes(b"\xff\xfe")

    assert oracle_plus.main(["--engine", "api", "--prompt-file", str(prompt_file)]) == 2

    captured = capsys.readouterr()
    assert "UTF-8" in captured.err
    assert "Traceback" not in captured.err
