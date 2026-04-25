"""Port probing and flock-backed lock lifecycle for Oracle-Plus."""

from __future__ import annotations

import errno
import fcntl
import os
import socket
from dataclasses import dataclass
from pathlib import Path

from oracle_plus import config


class LockBusyError(RuntimeError):
    """Raised when a port lock is already held locally."""


@dataclass
class PortLock:
    port: int
    lock_path: Path
    meta_path: Path
    fd: int
    slug: str
    remote_host: str | None = None

    def release(self) -> None:
        if self.fd < 0:
            return
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = -1
            if self.meta_path.exists():
                self.meta_path.unlink()

    def __enter__(self) -> "PortLock":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def _parse_port(value: int | str, *, label: str) -> int:
    if isinstance(value, int):
        port = value
    else:
        if not value.isdigit():
            raise ValueError(f"invalid {label}: {value}")
        port = int(value)

    if not 1 <= port <= 65535:
        raise ValueError(f"invalid {label}: {value}")
    return port


def build_candidate_ports(start_port: int | None = None) -> list[int]:
    """Return the effective browser candidate pool after env overrides."""
    if start_port is not None:
        return [_parse_port(start_port, label="start port")]

    explicit_remote_port = config.get_remote_port()
    if explicit_remote_port:
        return [_parse_port(explicit_remote_port, label="ORACLE_REMOTE_PORT")]

    explicit_start = config.get_auto_remote_port_start()
    explicit_end = config.get_auto_remote_port_end()
    if explicit_start is not None or explicit_end is not None:
        start = _parse_port(
            explicit_start or config.get_chatgpt_auto_remote_port_start(),
            label="auto remote port start",
        )
        end = _parse_port(
            explicit_end or config.get_chatgpt_auto_remote_port_end(),
            label="auto remote port end",
        )
    else:
        start = _parse_port(
            config.get_chatgpt_auto_remote_port_start(),
            label="auto remote port start",
        )
        end = _parse_port(
            config.get_chatgpt_auto_remote_port_end(),
            label="auto remote port end",
        )

    if start > end:
        raise ValueError("auto remote port start must be <= auto remote port end")
    return list(range(start, end + 1))


def probe_port(host: str, port: int, timeout: float | None = None) -> bool:
    """Return True when the host:port accepts a TCP connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout or config.PROBE_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def _lock_paths(port: int, base_dir: Path | None = None) -> tuple[Path, Path]:
    lock_root = (base_dir or config.port_lock_dir)
    return lock_root / f"{port}.lock", lock_root / f"{port}.meta"


def acquire_port_lock(
    port: int,
    base_dir: Path | None = None,
    *,
    slug: str = "oracle-run",
    remote_host: str | None = None,
) -> PortLock:
    """Acquire a non-blocking flock lock for *port*."""
    lock_path, meta_path = _lock_paths(port, base_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(fd)
        if exc.errno in {errno.EACCES, errno.EAGAIN}:
            raise LockBusyError(f"port {port} is already reserved locally") from exc
        raise

    lock = PortLock(port=port, lock_path=lock_path, meta_path=meta_path, fd=fd, slug=slug, remote_host=remote_host)
    _write_lock_meta(lock)
    return lock


def acquire_candidate_lock(
    port: int,
    base_dir: Path | None = None,
    *,
    slug: str = "oracle-run",
    remote_host: str | None = None,
) -> tuple[int, Path]:
    """Compatibility helper returning the fd and meta path."""
    lock = acquire_port_lock(port, base_dir, slug=slug, remote_host=remote_host)
    return lock.fd, lock.meta_path


def release_candidate_lock(fd: int) -> None:
    """Compatibility helper closing the file descriptor."""
    if fd >= 0:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _write_lock_meta(lock: PortLock) -> None:
    from datetime import datetime, timezone

    lock.meta_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lock.meta_path.write_text(
        "\n".join(
            [
                f"pid: {os.getpid()}",
                f"slug: {lock.slug}",
                f"started_at: {started_at}",
                f"port: {lock.port}",
                f"remote_host: {lock.remote_host or ''}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def find_free_port(ports: list[int] | tuple[int, ...], base_dir: Path | None = None) -> int:
    """Return the first port that can be locally reserved."""
    for port in ports:
        try:
            lock = acquire_port_lock(port, base_dir)
        except LockBusyError:
            continue
        else:
            lock.release()
            return port
    raise LockBusyError("all candidate ports are busy")
