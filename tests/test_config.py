"""Tests for oracle_plus.config."""

from __future__ import annotations

import importlib
from pathlib import Path


def reload_config(monkeypatch, *, cache_dir: str | None = None):
    if cache_dir is None:
        monkeypatch.delenv("ORACLE_PLUS_CACHE_DIR", raising=False)
        monkeypatch.delenv("ORACLE_PLUS_CACHE", raising=False)
    else:
        monkeypatch.setenv("ORACLE_PLUS_CACHE_DIR", cache_dir)
    import oracle_plus.config as config
    return importlib.reload(config)


def test_cache_root_default(monkeypatch):
    config = reload_config(monkeypatch)
    assert str(config.cache_root).endswith(".cache/oracle-plus")


def test_cache_root_override(monkeypatch):
    config = reload_config(monkeypatch, cache_dir="/tmp/my-cache")
    assert str(config.cache_root) == "/tmp/my-cache"


def test_derived_paths(monkeypatch):
    config = reload_config(monkeypatch)
    assert config.port_lock_dir == config.cache_root / "ports"
    assert config.run_state_dir == config.cache_root / "runs"
    assert config.port_lock_file_for(9473) == config.port_lock_dir / "9473.lock"
    assert config.meta_file_for("run-1") == config.run_state_dir / "run-1.meta"


def test_candidate_ports(monkeypatch):
    config = reload_config(monkeypatch)
    assert config.candidate_browser_ports == list(range(9473, 9480))


def test_config_read_is_pure(tmp_path, monkeypatch):
    config = reload_config(monkeypatch, cache_dir=str(tmp_path / "oracle"))
    _ = config.cache_root
    _ = config.port_lock_dir
    _ = config.run_state_dir
    _ = config.port_lock_file_for(9473)
    _ = config.meta_file_for("slug")
    assert not (tmp_path / "oracle").exists()


def test_env_helpers(monkeypatch):
    monkeypatch.setenv("ORACLE_REMOTE_TOKEN", "token-123")
    monkeypatch.setenv("ORACLE_BIN", "/opt/oracle")
    import oracle_plus.config as config
    importlib.reload(config)
    assert config.get_remote_token() == "token-123"
    assert config.get_oracle_bin() == "/opt/oracle"
