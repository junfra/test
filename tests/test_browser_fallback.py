"""Tests for browser-mode selection and fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_select_oracle_port_tries_ports_in_order(monkeypatch):
    from oracle_plus.browser_mode import LockBusyError, select_oracle_port

    attempts: list[int] = []

    def acquire(port):
        attempts.append(port)
        if port == 9474:
            lock = MagicMock()
            lock.release = MagicMock()
            return lock
        raise LockBusyError("busy")

    monkeypatch.setattr("oracle_plus.browser_mode.acquire_port_lock", acquire)
    assert select_oracle_port(None) == 9474
    assert attempts[:2] == [9473, 9474]


def test_select_oracle_port_respects_env_override(monkeypatch):
    from oracle_plus.browser_mode import select_oracle_port

    monkeypatch.setenv("ORACLE_REMOTE_PORT", "9501")
    attempts: list[int] = []

    def acquire(port):
        attempts.append(port)
        lock = MagicMock()
        lock.release = MagicMock()
        return lock

    monkeypatch.setattr("oracle_plus.browser_mode.acquire_port_lock", acquire)
    assert select_oracle_port(None) == 9501
    assert attempts == [9501]


def test_build_oracle_args_preserves_passthrough():
    from oracle_plus.browser_mode import build_oracle_args

    args = build_oracle_args(
        url="https://example.com",
        port=9473,
        passthrough=("--flag-a", "--flag-b"),
        remote_host="127.0.0.1:9473",
        remote_token="token",
    )
    assert args[:4] == ["--remote-host", "127.0.0.1:9473", "--remote-token", "token"]
    assert "--flag-a" in args and "--flag-b" in args


def test_run_browser_mode_uses_runner(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import run_browser_mode

    monkeypatch.setattr("oracle_plus.browser_mode.detect_host_ip", lambda: "127.0.0.1")
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])
    captured = {}

    def runner(command, args, *, output_file=None):
        captured["command"] = command
        captured["args"] = list(args)
        captured["output_file"] = output_file
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_subprocess", runner)
    rc = run_browser_mode(
        url="https://example.com",
        port=9473,
        passthrough=("--write-output", str(tmp_path / "capture.md")),
        oracle_bin="/usr/bin/oracle",
        host_ip="127.0.0.1",
        remote_host="127.0.0.1:9473",
        remote_token="token",
        session_slug="run-1",
    )
    assert rc == 0
    assert captured["command"] == ["/usr/bin/oracle"]
    assert "--write-output" in captured["args"]


def test_busy_fallback_scans_next_port(monkeypatch):
    from oracle_plus.browser_mode import LockBusyError, run_browser_with_busy_fallback

    monkeypatch.setattr("oracle_plus.browser_mode.detect_host_ip", lambda: "127.0.0.1")
    monkeypatch.setattr("oracle_plus.browser_mode.probe_port", lambda host, port: port == 9474)

    class Lock:
        def __init__(self, port):
            self.port = port
            self.released = False

        def release(self):
            self.released = True

    def acquire(port, *args, **kwargs):
        if port == 9474:
            return Lock(port)
        raise LockBusyError("busy")

    monkeypatch.setattr("oracle_plus.browser_mode.acquire_port_lock", acquire)
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])
    monkeypatch.setattr("oracle_plus.browser_mode.run_browser_mode", lambda **kwargs: 0)

    assert (
        run_browser_with_busy_fallback(
            url="https://example.com",
            passthrough=tuple(),
            oracle_bin="/usr/bin/oracle",
            host_ip="127.0.0.1",
            session_slug="run-2",
        )
        == 0
    )


@pytest.mark.parametrize(
    "busy_text",
    [
        "ERROR: busy\n",
        "User error (browser-automation): busy\n",
    ],
)
def test_busy_fallback_uses_busy_output_patterns(monkeypatch, tmp_path, busy_text):
    from oracle_plus.browser_mode import run_browser_with_busy_fallback

    monkeypatch.setattr("oracle_plus.browser_mode.detect_host_ip", lambda: "127.0.0.1")
    monkeypatch.setattr("oracle_plus.browser_mode.probe_port", lambda host, port: True)
    monkeypatch.setattr("oracle_plus.browser_mode.acquire_port_lock", lambda port, *args, **kwargs: MagicMock())
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    attempts: list[int] = []

    def fake_run_browser_mode(**kwargs):
        capture_output_file = kwargs["capture_output_file"]
        attempts.append(kwargs["port"])
        if kwargs["port"] == 9473:
            capture_output_file.write_text(busy_text, encoding="utf-8")
            return 1
        capture_output_file.write_text("ok\n", encoding="utf-8")
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_browser_mode", fake_run_browser_mode)

    assert (
        run_browser_with_busy_fallback(
            url="https://example.com",
            passthrough=tuple(),
            oracle_bin="/usr/bin/oracle",
            host_ip="127.0.0.1",
            session_slug="run-busy-text",
        )
        == 0
    )
    assert attempts[:2] == [9473, 9474]


def test_run_browser_cli_rewrites_prompt_file_to_prompt(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review this change.\n", encoding="utf-8")
    captured = {}

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    def fake_run_subprocess(command, args, *, output_file=None):
        captured["command"] = command
        captured["args"] = list(args)
        captured["output_file"] = output_file
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_subprocess", fake_run_subprocess)

    rc = run_browser_cli(["--engine", "api", "--prompt-file", str(prompt_file), "--model", "gpt-5.2"])

    assert rc == 0
    assert captured["command"] == ["/usr/bin/oracle"]
    assert captured["args"] == ["--engine", "api", "-p", "Review this change.\n", "--model", "gpt-5.2"]


def test_run_browser_cli_rejects_prompt_file_with_prompt(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review this change.\n", encoding="utf-8")

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    with pytest.raises(BrowserModeError, match="cannot be used together"):
        run_browser_cli(["--engine", "api", "-p", "inline prompt", "--prompt-file", str(prompt_file)])


def test_run_browser_cli_rewrites_prompt_file_equals_syntax(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review equals syntax.\n", encoding="utf-8")
    captured = {}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    def fake_run_subprocess(command, args, *, output_file=None):
        captured["command"] = command
        captured["args"] = list(args)
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_subprocess", fake_run_subprocess)

    rc = run_browser_cli(["--prompt-file=" + str(prompt_file), "--model", "gpt-5.2"])

    assert rc == 0
    assert captured["command"] == ["/usr/bin/oracle"]
    assert captured["args"] == ["-p", "Review equals syntax.\n", "--model", "gpt-5.2"]


def test_run_browser_cli_rejects_missing_prompt_file_path():
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    with pytest.raises(BrowserModeError, match="requires a file path"):
        run_browser_cli(["--engine", "api", "--prompt-file"])


def test_run_browser_cli_rejects_duplicate_prompt_file(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review duplicates.\n", encoding="utf-8")

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    with pytest.raises(BrowserModeError, match="can only be specified once"):
        run_browser_cli(["--engine", "api", "--prompt-file", str(prompt_file), f"--prompt-file={prompt_file}"])


def test_run_browser_cli_rejects_missing_prompt_file(monkeypatch):
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    with pytest.raises(BrowserModeError, match="path does not exist"):
        run_browser_cli(["--engine", "api", "--prompt-file", "/tmp/does-not-exist-prompt.md"])


def test_run_browser_cli_rejects_unreadable_prompt_file(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review unreadable file.\n", encoding="utf-8")

    def fake_read_text(self, *, encoding):
        raise PermissionError("permission denied")

    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    with pytest.raises(BrowserModeError, match="unable to read --prompt-file"):
        run_browser_cli(["--engine", "api", "--prompt-file", str(prompt_file)])


def test_run_browser_cli_rejects_non_utf8_prompt_file(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import BrowserModeError, run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_bytes(b"\xff\xfe")

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    with pytest.raises(BrowserModeError, match="UTF-8"):
        run_browser_cli(["--engine", "api", "--prompt-file", str(prompt_file)])


def test_run_browser_cli_control_command_bypasses_prompt_file_normalization(monkeypatch):
    from oracle_plus.browser_mode import run_browser_cli

    captured = {}

    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])

    def fake_run_subprocess(command, args, *, output_file=None):
        captured["command"] = command
        captured["args"] = list(args)
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_subprocess", fake_run_subprocess)

    rc = run_browser_cli(["status", "session-1", "--prompt-file", "/tmp/does-not-exist-prompt.md"])

    assert rc == 0
    assert captured["command"] == ["/usr/bin/oracle"]
    assert captured["args"] == ["status", "session-1", "--prompt-file", "/tmp/does-not-exist-prompt.md"]


def test_run_browser_cli_browser_autoselect_normalizes_prompt_file(monkeypatch, tmp_path):
    from oracle_plus.browser_mode import run_browser_cli

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Review browser path.\n", encoding="utf-8")
    captured = {}

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("oracle_plus.browser_mode.resolve_oracle_command", lambda: ["/usr/bin/oracle"])
    monkeypatch.setattr("oracle_plus.browser_mode.detect_host_ip", lambda: "127.0.0.1")

    def fake_run_browser_with_busy_fallback(**kwargs):
        captured["kwargs"] = kwargs
        return 0

    monkeypatch.setattr("oracle_plus.browser_mode.run_browser_with_busy_fallback", fake_run_browser_with_busy_fallback)

    rc = run_browser_cli(["--prompt-file", str(prompt_file), "--model", "gpt-5.2"])

    assert rc == 0
    assert captured["kwargs"]["passthrough"] == ("-p", "Review browser path.\n", "--model", "gpt-5.2")
