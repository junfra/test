"""Host IP auto-detection for Oracle-Plus browser mode."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


def _first_ipv4(text: str) -> str | None:
    """Extract the first dotted-quad IPv4 address from *text*.

    Scans all tokens so it works for both getent output (IP in column 0)
    and `ip route` output where gateway is buried mid-line.
    """
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        # Scan every token — ip route has the IP after "via".
        for part in parts:
            if len(part) > 5 and part.count(".") == 3 and all(
                x.isdigit() for x in part.split(".")
            ):
                return part
    return None


def _read_first_host_ip(hosts_path: Path) -> str | None:
    """Return the first dotted-quad associated with host.docker.internal in /etc/hosts."""
    if not hosts_path.exists():
        return None
    for line in hosts_path.read_text(encoding="utf-8").splitlines():
        if "host.docker.internal" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        # IP is always first column in /etc/hosts.
        ip_candidate = parts[0]
        if len(ip_candidate) > 5 and ip_candidate.count(".") == 3 and all(
            x.isdigit() for x in ip_candidate.split(".")
        ):
            return ip_candidate
    return None


def detect_host_ip(
    *,
    hosts_path: Path = Path("/etc/hosts"),
    resolv_path: Path = Path("/etc/resolv.conf"),
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    """Return a usable host IP using the legacy lookup order.

    Order:
    - getent ahostsv4 host.docker.internal
    - /etc/hosts
    - ip route show default (gateway)
    - /etc/resolv.conf nameserver
    """

    # 1) getent
    try:
        result = runner(
            ["getent", "ahostsv4", "host.docker.internal"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None
    else:
        if result.returncode == 0:
            ip = _first_ipv4(result.stdout or "")
            if ip:
                return ip

    # 2) /etc/hosts
    ip = _read_first_host_ip(hosts_path)
    if ip:
        return ip

    # 3) ip route show default → gateway (uses _first_ipv4 which scans all tokens)
    try:
        result = runner(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None
    else:
        if result.returncode == 0:
            ip = _first_ipv4(result.stdout or "")
            if ip:
                return ip

    # 4) /etc/resolv.conf nameserver
    if resolv_path.exists():
        for line in resolv_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("nameserver "):
                _, ip = line.split(maxsplit=1)
                if ip:
                    return ip.strip()

    raise RuntimeError("unable to resolve Windows host IP; set ORACLE_REMOTE_HOST explicitly")
