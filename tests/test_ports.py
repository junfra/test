"""Tests for port probing and lock lifecycle."""

from __future__ import annotations

import importlib
import socket

import pytest


def test_probe_port_success(monkeypatch):
    from oracle_plus.ports import probe_port

    class Dummy:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("socket.create_connection", lambda *a, **k: Dummy())
    assert probe_port("127.0.0.1", 9473) is True


def test_probe_port_failure(monkeypatch):
    from oracle_plus.ports import probe_port

    def fail(*args, **kwargs):
        raise socket.error("refused")

    monkeypatch.setattr("socket.create_connection", fail)
    assert probe_port("127.0.0.1", 9473) is False


def test_acquire_release_lock(tmp_path):
    from oracle_plus.ports import acquire_port_lock

    lock = acquire_port_lock(9473, tmp_path, slug="run-1", remote_host="127.0.0.1:9473")
    assert lock.meta_path.exists()
    lock.release()
    assert not lock.meta_path.exists()


def test_acquire_lock_busy(tmp_path):
    from oracle_plus.ports import LockBusyError, acquire_port_lock

    lock1 = acquire_port_lock(9473, tmp_path)
    try:
        with pytest.raises(LockBusyError):
            acquire_port_lock(9473, tmp_path)
    finally:
        lock1.release()


def test_find_free_port(tmp_path):
    from oracle_plus.ports import find_free_port

    assert find_free_port([9473, 9474], tmp_path) in {9473, 9474}


def test_build_candidate_ports_uses_explicit_remote_port(monkeypatch):
    monkeypatch.setenv("ORACLE_REMOTE_PORT", "9501")
    monkeypatch.delenv("ORACLE_AUTO_REMOTE_PORT_START", raising=False)
    monkeypatch.delenv("ORACLE_AUTO_REMOTE_PORT_END", raising=False)

    import oracle_plus.ports as ports

    importlib.reload(ports)
    assert ports.build_candidate_ports() == [9501]


def test_build_candidate_ports_uses_auto_range_override(monkeypatch):
    monkeypatch.delenv("ORACLE_REMOTE_PORT", raising=False)
    monkeypatch.setenv("ORACLE_AUTO_REMOTE_PORT_START", "9501")
    monkeypatch.setenv("ORACLE_AUTO_REMOTE_PORT_END", "9503")

    import oracle_plus.ports as ports

    importlib.reload(ports)
    assert ports.build_candidate_ports() == [9501, 9502, 9503]


def test_build_candidate_ports_rejects_inverted_range(monkeypatch):
    monkeypatch.delenv("ORACLE_REMOTE_PORT", raising=False)
    monkeypatch.setenv("ORACLE_AUTO_REMOTE_PORT_START", "9503")
    monkeypatch.setenv("ORACLE_AUTO_REMOTE_PORT_END", "9501")

    import oracle_plus.ports as ports

    importlib.reload(ports)
    with pytest.raises(ValueError, match="auto remote port start must be <= auto remote port end"):
        ports.build_candidate_ports()
