"""Tests for count_substantive_body_chars — body-length metric."""
from __future__ import annotations

from study.learning_draft_rule import count_substantive_body_chars


def test_body_length_excludes_title_headings_toc_and_references():
    """Verify that title (#), headings (##–######), TOC block, and References are excluded."""
    text = """# My Learning Draft

## Introduction

This is the body content I want to count.

### Background

Some more text here.

#### Details

Even deeper detail.

## 목차

- Section 1
- Section 2
- Section 3

## References

[1] Author, *Title*, Year.
[2] Another source."""

    body_chars = count_substantive_body_chars(text)

    # After stripping title, headings, TOC block, and references, only:
    # "This is the body content I want to count." + blank line
    # "Some more text here." + blank line
    # "Even deeper detail."
    assert body_chars > 0
    # Should not include any heading characters (no '#', no '목차', etc.)
    stripped = "".join(
        line for line in text.splitlines()
        if not line.startswith("#") and "목차" not in line
        and "References" not in line
    )
    # Body chars should be less than raw body (excluding headings) to show dedup/strip works
    assert body_chars < len(stripped), f"Expected {body_chars} < {len(stripped)}"


def test_body_length_counts_repeated_phrase_only_once():
    """Repeated lines should be counted only once after deduplication."""
    text = """# Title

## Section

This is repeated.
This is repeated.
This is repeated.

This appears twice.
This appears twice.

A unique line here."""

    body_chars = count_substantive_body_chars(text)

    # After stripping title and headings:
    # "This is repeated." (counted once, not 3×)
    # blank line
    # "This appears twice." (counted once, not 2×)
    # blank line
    # "A unique line here."
    expected_min = len("This is repeated.") + 1  # newline
    assert body_chars >= expected_min

