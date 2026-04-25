"""Subprocess boundary for invoking the resolved Oracle CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable


def run_subprocess(
    command: list[str],
    args: Iterable[str],
    *,
    env: dict[str, str] | None = None,
    output_file: Path | None = None,
) -> int:
    full_cmd = [*command, *list(args)]
    if output_file is None:
        completed = subprocess.run(full_cmd, env=env, close_fds=True)
        return completed.returncode

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as fh:
        proc = subprocess.Popen(
            full_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=True,
        )
        assert proc.stdout is not None
        for chunk in proc.stdout:
            sys.stdout.write(chunk)
            fh.write(chunk)
        return proc.wait()
