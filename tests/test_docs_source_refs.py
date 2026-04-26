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


def test_skill_docs_use_prompt_file_examples():
    for relpath in [Path("live-SKILL.md"), Path("skills/oracle-browser/SKILL.md"), Path("output/SKILL.md")]:
        text = relpath.read_text(encoding="utf-8")
        assert "Use `-p` for short inline prompts." in text
        assert "Use `--file` for actual file attachments, source files, review targets, or context globs." in text
        assert "--prompt-file" in text
        assert "`--prompt-file` is convenience sugar over `-p`" in text
        assert "--file /tmp/oracle_prompt.md" not in text


def test_skill_docs_describe_prompt_file_limits_and_encoding():
    for relpath in [Path("live-SKILL.md"), Path("skills/oracle-browser/SKILL.md"), Path("output/SKILL.md")]:
        text = relpath.read_text(encoding="utf-8")
        assert "UTF-8" in text
        assert "argument length" in text


def test_skill_docs_describe_browser_inactivity_wait_limit():
    for relpath in [Path("live-SKILL.md"), Path("skills/oracle-browser/SKILL.md"), Path("output/SKILL.md")]:
        text = relpath.read_text(encoding="utf-8")
        assert "30 minutes" in text


def test_skill_docs_require_inlining_file_contents_for_oracle_review():
    for relpath in [Path("live-SKILL.md"), Path("skills/oracle-browser/SKILL.md"), Path("output/SKILL.md")]:
        text = relpath.read_text(encoding="utf-8")
        assert "Do not use `--prompt-file` as a replacement for upstream `--file`" in text
        assert "A path mentioned inside prompt text is only prose unless the file is also supplied via `--file`." in text
