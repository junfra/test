"""Tests for the subprocess runner boundary."""

from __future__ import annotations

from pathlib import Path


def test_run_subprocess_forwards_command(monkeypatch, tmp_path):
    from oracle_plus.subprocess_runner import run_subprocess

    captured = {}

    class Stdout:
        def fileno(self):
            return 99

    class Proc:
        def __init__(self):
            self.stdout = Stdout()

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return Proc()

    reads = iter([b"hello\n", b""])

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("select.select", lambda r, w, x, timeout=None: (r, [], []))
    monkeypatch.setattr("os.read", lambda fd, size: next(reads))
    monkeypatch.setattr("sys.stdout.write", lambda text: None)
    output = tmp_path / "capture.md"
    rc = run_subprocess(["/usr/bin/oracle"], ["--help"], output_file=output)
    assert rc == 0
    assert captured["cmd"] == ["/usr/bin/oracle", "--help"]
    assert captured["kwargs"]["close_fds"] is True
    assert output.exists()


def test_run_subprocess_times_out_after_inactivity(monkeypatch, capsys):
    from oracle_plus.subprocess_runner import run_subprocess

    class Stdout:
        def fileno(self):
            return 99

    class Proc:
        def __init__(self):
            self.stdout = Stdout()
            self.terminated = False
            self.killed = False
            self.wait_timeouts = []

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            self.wait_timeouts.append(timeout)
            return 124

    proc = Proc()

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr("select.select", lambda r, w, x, timeout=None: ([], [], []))
    monkeypatch.setattr("sys.stdout.write", lambda text: None)

    rc = run_subprocess(["/usr/bin/oracle"], ["--wait"], inactivity_timeout_seconds=1800)

    assert rc == 124
    assert proc.terminated is True
    assert proc.killed is False
    assert proc.wait_timeouts == [5]
    captured = capsys.readouterr()
    assert "1800" in captured.err


def test_run_subprocess_resets_inactivity_timeout_after_output(monkeypatch, tmp_path):
    from oracle_plus.subprocess_runner import run_subprocess

    timeouts = []

    class Stdout:
        def fileno(self):
            return 99

    class Proc:
        def __init__(self):
            self.stdout = Stdout()

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

    reads = iter([b"first line\n", b"second line\n", b""])

    def fake_select(r, w, x, timeout=None):
        timeouts.append(timeout)
        return (r, [], [])

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: Proc())
    monkeypatch.setattr("select.select", fake_select)
    monkeypatch.setattr("os.read", lambda fd, size: next(reads))
    monkeypatch.setattr("sys.stdout.write", lambda text: None)
    output = tmp_path / "capture.md"

    rc = run_subprocess(
        ["/usr/bin/oracle"],
        ["--wait"],
        output_file=output,
        inactivity_timeout_seconds=1800,
    )

    assert rc == 0
    assert timeouts == [1800, 1800, 1800]
    assert output.read_text(encoding="utf-8") == "first line\nsecond line\n"
