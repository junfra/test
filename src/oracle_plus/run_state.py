"""Run-state .meta file handling for Oracle-Plus."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import os
import re
from pathlib import Path

from oracle_plus import config


def _sanitize_slug(slug: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", (slug or "").strip())
    clean = clean.strip("-")
    if not clean:
        clean = datetime.now(timezone.utc).strftime("oracle-run-%Y%m%dT%H%M%SZ")
    return clean


def _meta_path(slug: str, base_dir: Path | None = None) -> Path:
    root = (base_dir or config.cache_root) / "runs"
    return root / f"{_sanitize_slug(slug)}.meta"


def _parse_meta(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def read_run_meta(slug: str, *, base_dir: Path | None = None) -> dict[str, str]:
    path = _meta_path(slug, base_dir)
    if not path.exists():
        return {}
    return _parse_meta(path.read_text(encoding="utf-8"))


def _append_meta(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for key, value in data.items():
            fh.write(f"{key}: {value}\n")


def write_run_meta(slug: str, data: dict[str, str], *, base_dir: Path | None = None) -> Path:
    path = _meta_path(slug, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": str(os.getpid()),
        "slug": slug,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **{k: str(v) for k, v in data.items()},
    }
    path.write_text("".join(f"{k}: {v}\n" for k, v in payload.items()), encoding="utf-8")
    return path


def update_run_meta(
    slug: str,
    updater: Callable[[dict[str, str]], dict[str, str]],
    *,
    base_dir: Path | None = None,
) -> dict[str, str]:
    current = read_run_meta(slug, base_dir=base_dir)
    updated = updater(dict(current))
    path = _meta_path(slug, base_dir)
    _append_meta(path, {k: str(v) for k, v in updated.items()})
    return updated


def initialize_run_state(
    slug: str,
    host_ip: str,
    candidate_ports: str,
    *,
    base_dir: Path | None = None,
) -> Path:
    return write_run_meta(
        slug,
        {
            "host": host_ip,
            "candidate_ports": candidate_ports,
            "status": "selecting_port",
        },
        base_dir=base_dir,
    )


def record_run_state(
    slug: str,
    key: str,
    value: str,
    *,
    base_dir: Path | None = None,
) -> None:
    update_run_meta(slug, lambda current: {**current, key: value}, base_dir=base_dir)

