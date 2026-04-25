"""Tests for src/oracle_plus/host.py — Task 3a."""

from __future__ import annotations

from pathlib import Path


class _FakeResult:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout; self.returncode = returncode


def _r(stdout=""):
    """Helper for a successful run with empty stderr."""
    return _FakeResult(stdout=stdout)

def _r_fail():
    """Helper for a failed run (rc=1, no stdout)."""
    return _FakeResult(returncode=1)


# --- detect_host_ip branches (legacy order) using runner kwarg ---

def test_detects_via_getent():
    from oracle_plus.host import detect_host_ip

    def run(cmd, **kw):
        assert cmd == ["getent", "ahostsv4", "host.docker.internal"]
        return _r("192.168.1.5 STREAM\n")  # IP in column 0

    assert detect_host_ip(runner=run) == "192.168.1.5"


def test_falls_back_to_etc_hosts():
    from oracle_plus.host import detect_host_ip

    def run(cmd, **kw): return _r_fail()  # getent fails → empty stdout
    p = Path("/tmp/fake-hosts"); p.write_text("10.20.30.40 host.docker.internal\n", encoding="utf-8")

    assert detect_host_ip(runner=run, hosts_path=p, resolv_path=Path("/nonexistent")) == "10.20.30.40"


def test_falls_back_to_default_route():
    from oracle_plus.host import detect_host_ip

    def run(cmd, **kw):
        if cmd[:3] == ["getent", "ahostsv4", "host.docker.internal"]: return _r_fail()
        return _r("default via 192.168.56.1 dev eth0\n")

    assert detect_host_ip(runner=run, hosts_path=Path("/nonexistent"), resolv_path=Path("/nonexistent")) == "192.168.56.1"


def test_falls_back_to_resolv_conf():
    from oracle_plus.host import detect_host_ip

    def run(cmd, **kw): return _r_fail()  # all subprocess calls fail
    p = Path("/tmp/fake-resolv"); p.write_text("# gen\nnameserver 8.8.8.8\n", encoding="utf-8")

    assert detect_host_ip(runner=run, hosts_path=Path("/nonexistent"), resolv_path=p) == "8.8.8.8"


def test_raises_when_unresolved():
    from oracle_plus.host import detect_host_ip

    def fail(*a, **kw): return _r_fail()  # empty stdout = no IP found anywhere
    try:
        detect_host_ip(runner=fail, hosts_path=Path("/nonexistent"), resolv_path=Path("/nonexistent"))
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert len(e.args[0]) > 0


# --- internal helpers (pure functions) ---

def test_first_ipv4():
    from oracle_plus.host import _first_ipv4
    assert _first_ipv4("192.168.1.5 STREAM\n") == "192.168.1.5"


def test_first_ipv4_skips_non_dotted():
    from oracle_plus.host import _first_ipv4
    assert _first_ipv4("not-an-ip\n") is None

