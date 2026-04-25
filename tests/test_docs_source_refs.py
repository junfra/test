"""Tests for source-bearing doc references."""

from __future__ import annotations

from pathlib import Path


SOURCE_PATHS = [
    Path("README.md"),
    Path("PORT_SELECTION.md"),
    Path("live-SKILL.md"),
    Path("output/SKILL.md"),
    Path("skills/oracle-browser/SKILL.md"),
    Path("scripts/oracle-env.sh"),
    Path("scripts/oracle-remote-host.sh"),
    Path("scripts/sync-skill-docs.sh"),
]


def test_source_bearing_docs_point_to_python_cli():
    for relpath in SOURCE_PATHS:
        text = relpath.read_text(encoding="utf-8")
        matches = [line.strip() for line in text.splitlines() if "oracle-plus.sh" in line]
        if relpath == Path("PORT_SELECTION.md"):
            assert matches == [
                "`output/oracle-plus.sh`, if it exists, is compatibility surface only and is not the documented entry point."
            ]
        else:
            assert matches == []


def test_skill_docs_use_oracle_cli_path():
    text = Path("skills/oracle-browser/SKILL.md").read_text(encoding="utf-8")
    assert "ORACLE_CLI" in text
    assert "oracle-plus" in text
