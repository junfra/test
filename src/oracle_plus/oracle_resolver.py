"""Resolve the underlying Oracle CLI binary."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from oracle_plus import config


def _cached_node_modules() -> Path:
    return config.cache_root / "node_modules"


def _binary_exists(path: str | os.PathLike[str]) -> bool:
    p = Path(path)
    return p.exists() and os.access(p, os.X_OK)


def resolve_oracle_bin_via_npx() -> str | None:
    """Compatibility helper that resolves the system `oracle` command."""
    return shutil.which("oracle")


def resolve_oracle_bin_cached() -> str | None:
    """Return the cached npm install path if present."""
    candidates = [
        config.cache_bin,
        config.cache_root / "node_modules" / "@steipete" / "oracle" / "cli.js",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _bootstrap_cached_cli() -> str | None:
    if config.cache_bin.exists():
        return str(config.cache_bin)

    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        return None

    config.cache_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [npm, "install", "--no-audit", "--no-fund", "--prefix", str(config.cache_root), config.PACKAGE_SPEC],
        check=True,
        capture_output=True,
        text=True,
    )
    if config.cache_bin.exists():
        return str(config.cache_bin)
    return resolve_oracle_bin_cached()


def resolve_oracle_bin() -> str | None:
    """Return the command used to invoke Oracle."""
    oracle_bin = config.get_oracle_bin()
    if oracle_bin:
        return oracle_bin

    system_oracle = shutil.which("oracle")
    if system_oracle:
        return system_oracle

    cached = resolve_oracle_bin_cached()
    if cached:
        return cached

    return _bootstrap_cached_cli()


def resolve_oracle_command() -> list[str]:
    """Return the executable command used to invoke Oracle."""
    oracle_bin = resolve_oracle_bin()
    if oracle_bin is None:
        raise RuntimeError("unable to resolve Oracle binary")
    if oracle_bin == str(config.cache_bin) or oracle_bin.endswith(".js"):
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("node is required to run cached Oracle CLI")
        return [node, oracle_bin]
    return [oracle_bin]
