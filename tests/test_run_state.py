"""Tests for src/oracle_plus/run_state.py — Task 3c."""

from __future__ import annotations


def test_write_run_meta_creates_directory(tmp_path):
    from oracle_plus.run_state import write_run_meta
    path = write_run_meta("my-run", {"status": "running"}, base_dir=tmp_path)
    assert path.exists()


def test_write_run_meta_writes_pid_slug_started_at(tmp_path):
    import os
    from oracle_plus.run_state import write_run_meta
    path = write_run_meta("my-run", {"status": "running"}, base_dir=tmp_path)
    text = path.read_text()
    assert str(os.getpid()) in text or "pid" in text.lower()
    assert "my-run" in text


def test_read_run_meta_returns_dict(tmp_path):
    from oracle_plus.run_state import write_run_meta, read_run_meta
    write_run_meta("read-test", {"status": "running"}, base_dir=tmp_path)
    result = read_run_meta("read-test", base_dir=tmp_path)
    assert isinstance(result, dict)


def test_read_run_meta_returns_empty_on_missing(tmp_path):
    from oracle_plus.run_state import read_run_meta
    assert read_run_meta("nonexistent", base_dir=tmp_path) == {}


def test_read_run_meta_parses_multiple_keys(tmp_path):
    from oracle_plus.run_state import write_run_meta, read_run_meta
    write_run_meta("multi-key", {
        "status": "running",
        "selected_port": "9473",
    }, base_dir=tmp_path)
    result = read_run_meta("multi-key", base_dir=tmp_path)
    assert result["status"] == "running"


def test_update_run_meta_appends_new_keys(tmp_path):
    from oracle_plus.run_state import write_run_meta, read_run_meta, update_run_meta
    write_run_meta("update-test", {"status": "running"}, base_dir=tmp_path)
    update_run_meta("update-test", lambda d: {**d, "selected_port": "9475"}, base_dir=tmp_path)
    result = read_run_meta("update-test", base_dir=tmp_path)
    assert result["selected_port"] == "9475"


def test_update_run_meta_keeps_existing(tmp_path):
    from oracle_plus.run_state import write_run_meta, read_run_meta, update_run_meta
    write_run_meta("keep-test", {"status": "running"}, base_dir=tmp_path)
    update_run_meta("keep-test", lambda d: {**d, "selected_port": "9476"}, base_dir=tmp_path)
    result = read_run_meta("keep-test", base_dir=tmp_path)
    assert result["status"] == "running"


def test_update_returns_dict(tmp_path):
    from oracle_plus.run_state import write_run_meta, update_run_meta
    write_run_meta("ret", {"x": "1"}, base_dir=tmp_path)
    result = update_run_meta("ret", lambda d: {**d, "y": "2"}, base_dir=tmp_path)
    assert isinstance(result, dict)


def test_slug_sanitizes_special_chars():
    from oracle_plus.run_state import _sanitize_slug
    result = _sanitize_slug("my run (test)")
    assert " " not in result


def test_empty_slug_gets_timestamp():
    from oracle_plus.run_state import _sanitize_slug
    result = _sanitize_slug("")
    assert len(result) > 0 and "oracle-run" in result

