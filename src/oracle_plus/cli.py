"""Top-level Oracle-Plus CLI routing."""

from __future__ import annotations

import argparse
import sys

import oracle_plus.browser_mode as browser_mode

VERSION = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="oracle-plus",
        description="Oracle-Plus Python CLI wrapper for @steipete/oracle.",
    )


def _is_help_request(argv: list[str]) -> bool:
    return not argv or "--help" in argv or "-h" in argv


def _is_version_request(argv: list[str]) -> bool:
    return "--version" in argv or "version" in argv


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if _is_help_request(args):
        _build_parser().print_help()
        return 0
    if _is_version_request(args):
        print(f"oracle-plus {VERSION}")
        return 0
    try:
        return browser_mode.run_browser_cli(args)
    except browser_mode.BrowserModeError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
