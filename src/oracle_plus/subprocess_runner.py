"""Subprocess boundary for invoking the resolved Oracle CLI."""

from __future__ import annotations

import codecs
import os
import select
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable, TextIO


INACTIVITY_TIMEOUT_EXIT_CODE = 124
TERMINATE_GRACE_SECONDS = 5


def _write_stream_chunk(text: str, output_handle: TextIO | None) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()
    if output_handle is not None:
        output_handle.write(text)
        output_handle.flush()


def _emit_timeout_message(message: str, output_handle: TextIO | None) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()
    if output_handle is not None:
        output_handle.write(message + "\n")
        output_handle.flush()


def _terminate_process(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_subprocess(
    command: list[str],
    args: Iterable[str],
    *,
    env: dict[str, str] | None = None,
    output_file: Path | None = None,
    inactivity_timeout_seconds: int | None = None,
) -> int:
    full_cmd = [*command, *list(args)]
    if output_file is None and inactivity_timeout_seconds is None:
        completed = subprocess.run(full_cmd, env=env, close_fds=True)
        return completed.returncode

    output_context = nullcontext(None)
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_context = output_file.open("w", encoding="utf-8")

    with output_context as fh:
        proc = subprocess.Popen(
            full_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        assert proc.stdout is not None
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        while True:
            ready, _, _ = select.select([proc.stdout], [], [], inactivity_timeout_seconds)
            if not ready:
                if proc.poll() is not None:
                    break
                timeout_value = inactivity_timeout_seconds or 0
                message = f"oracle-plus timed out after {timeout_value} seconds with no output"
                _terminate_process(proc)
                _emit_timeout_message(message, fh)
                return INACTIVITY_TIMEOUT_EXIT_CODE

            chunk = os.read(proc.stdout.fileno(), 4096)
            if not chunk:
                break
            text = decoder.decode(chunk)
            if text:
                _write_stream_chunk(text, fh)

        final_text = decoder.decode(b"", final=True)
        if final_text:
            _write_stream_chunk(final_text, fh)
        return proc.wait()
