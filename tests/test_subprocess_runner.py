"""Tests for the subprocess runner boundary."""

from __future__ import annotations

from pathlib import Path


def test_run_subprocess_forwards_command(monkeypatch, tmp_path):
    from oracle_plus.subprocess_runner import run_subprocess

    captured = {}

    class Proc:
        def __init__(self):
            self.stdout = iter(["hello\n"])

        def wait(self):
            return 0

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return Proc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("sys.stdout.write", lambda text: None)
    output = tmp_path / "capture.md"
    rc = run_subprocess(["/usr/bin/oracle"], ["--help"], output_file=output)
    assert rc == 0
    assert captured["cmd"] == ["/usr/bin/oracle", "--help"]
    assert captured["kwargs"]["close_fds"] is True
    assert output.exists()
