"""Tests for Oracle CLI resolution."""

from __future__ import annotations

from pathlib import Path


def test_oracle_bin_env_wins(monkeypatch):
    monkeypatch.setenv("ORACLE_BIN", "/tmp/custom-oracle")
    from oracle_plus.oracle_resolver import resolve_oracle_bin

    assert resolve_oracle_bin() == "/tmp/custom-oracle"


def test_system_oracle_is_used_when_available(monkeypatch):
    monkeypatch.delenv("ORACLE_BIN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/oracle" if name == "oracle" else None)
    from oracle_plus.oracle_resolver import resolve_oracle_bin

    assert resolve_oracle_bin() == "/usr/bin/oracle"


def test_cached_resolution_falls_back_to_cache(tmp_path, monkeypatch):
    cache = tmp_path / ".cache" / "oracle-plus" / "node_modules" / "@steipete" / "oracle" / "dist" / "bin"
    cache.mkdir(parents=True)
    script = cache / "oracle-cli.js"
    script.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    monkeypatch.setenv("ORACLE_PLUS_CACHE_DIR", str(tmp_path / ".cache" / "oracle-plus"))
    monkeypatch.delenv("ORACLE_BIN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    import importlib
    import oracle_plus.config as config

    importlib.reload(config)
    from oracle_plus.oracle_resolver import resolve_oracle_bin, resolve_oracle_command

    assert resolve_oracle_bin() == str(script)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/node" if name == "node" else None)
    assert resolve_oracle_command() == ["/usr/bin/node", str(script)]


def test_binary_exists_false_for_missing_path():
    from oracle_plus.oracle_resolver import _binary_exists

    assert _binary_exists("/nonexistent/path/oracle") is False


def test_cached_node_modules_uses_config(monkeypatch):
    monkeypatch.setenv("ORACLE_PLUS_CACHE_DIR", "/tmp/test-cache")
    from oracle_plus.oracle_resolver import _cached_node_modules

    assert str(_cached_node_modules()).endswith("node_modules")
