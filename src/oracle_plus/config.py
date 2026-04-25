"""Oracle-Plus configuration.

Pure module: reading any symbol must not create files or directories on disk.
The values here are derived from the process environment and standard paths.
"""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_REMOTE_TOKEN = "1234abcd"
CODEX_PROJECT_REMOTE_PORT = 9473
CODEX_PROJECT_CHATGPT_URL = (
    "https://chatgpt.com/g/g-p-69c884607908819182b07cff2d75690a-codex/project"
)
PACKAGE_SPEC = os.environ.get("ORACLE_NPM_SPEC", "@steipete/oracle@0.9.0")
PROBE_TIMEOUT_SECONDS = int(os.environ.get("ORACLE_REMOTE_PROBE_TIMEOUT_SECONDS", "1"))

_cache_root_env = os.environ.get("ORACLE_PLUS_CACHE_DIR") or os.environ.get("ORACLE_PLUS_CACHE")
cache_root: Path = Path(_cache_root_env) if _cache_root_env else Path.home() / ".cache" / "oracle-plus"

port_lock_dir: Path = cache_root / "ports"
run_state_dir: Path = cache_root / "runs"
cache_bin: Path = cache_root / "node_modules" / "@steipete" / "oracle" / "dist" / "bin" / "oracle-cli.js"
candidate_browser_ports: list[int] = list(range(9473, 9480))


def port_lock_file_for(port: int) -> Path:
    """Return the path to a lock file for *port* (no I/O)."""
    return port_lock_dir / f"{port}.lock"


def meta_file_for(slug: str) -> Path:
    """Return the run-state .meta path for *slug* (no I/O)."""
    return run_state_dir / f"{slug}.meta"


def port_meta_file_for(port: int) -> Path:
    """Return the per-port meta sidecar path used by the legacy wrapper."""
    return port_lock_dir / f"{port}.meta"


def get_remote_token() -> str:
    """Return the configured remote token or the legacy default."""
    return os.environ.get("ORACLE_REMOTE_TOKEN", DEFAULT_REMOTE_TOKEN)


def get_oracle_bin() -> str | None:
    """Return ORACLE_BIN if set, else ``None``."""
    return os.environ.get("ORACLE_BIN")


def get_remote_host() -> str | None:
    return os.environ.get("ORACLE_REMOTE_HOST")


def get_remote_port() -> str | None:
    return os.environ.get("ORACLE_REMOTE_PORT")


def get_auto_remote_port_start() -> str | None:
    return os.environ.get("ORACLE_AUTO_REMOTE_PORT_START")


def get_auto_remote_port_end() -> str | None:
    return os.environ.get("ORACLE_AUTO_REMOTE_PORT_END")


def get_chatgpt_auto_remote_port_start() -> str:
    return os.environ.get("ORACLE_CHATGPT_AUTO_REMOTE_PORT_START", "9473")


def get_chatgpt_auto_remote_port_end() -> str:
    return os.environ.get("ORACLE_CHATGPT_AUTO_REMOTE_PORT_END", "9479")


def get_code_project_remote_port() -> int:
    return int(os.environ.get("ORACLE_CODEX_PROJECT_REMOTE_PORT", str(CODEX_PROJECT_REMOTE_PORT)))


def get_code_project_chatgpt_url() -> str:
    return os.environ.get("ORACLE_CODEX_PROJECT_CHATGPT_URL", CODEX_PROJECT_CHATGPT_URL)
