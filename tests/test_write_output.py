"""Tests for auto write-output handling."""

from __future__ import annotations

from pathlib import Path


def test_handle_write_output_unset(monkeypatch):
    monkeypatch.delenv("WRITE_OUTPUT", raising=False)
    from oracle_plus.browser_mode import handle_write_output

    assert handle_write_output(None, None) == (None, None)


def test_handle_write_output_empty(monkeypatch):
    monkeypatch.setenv("WRITE_OUTPUT", "")
    from oracle_plus.browser_mode import handle_write_output

    assert handle_write_output(None, None) == ("", None)


def test_handle_write_output_absolute_path(tmp_path, monkeypatch):
    out = tmp_path / "nested" / "capture.md"
    monkeypatch.setenv("WRITE_OUTPUT", str(out))
    from oracle_plus.browser_mode import handle_write_output

    path, argv = handle_write_output(None, None)
    assert isinstance(path, Path)
    assert path.is_absolute()
    assert argv == ["--write-output", str(path)]


def test_build_oracle_command_appends_output_file(tmp_path):
    from oracle_plus.browser_mode import build_oracle_command

    out = tmp_path / "capture.md"
    cmd = build_oracle_command("/usr/bin/oracle", ["--help"], output_file=out)
    assert str(out) in cmd
