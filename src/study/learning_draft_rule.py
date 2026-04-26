"""SectionStructureValidator — validates section order and presence."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SectionStructureResult:
    passed: bool
    found_sections: list[str]
    errors: list[str] = field(default_factory=list)


SECTION_HEADER_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)


def _normalize_section_title(raw_title: str) -> str:
    """Normalize a section header for comparison against required_sections."""
    title = raw_title.strip()
    # Strip numbering like "1.", "2)", etc.
    title = re.sub(r"^\d+[\.\)]\s*", "", title)
    # Strip parenthesized English text like "(Problem Background)"
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    return title.strip()


def extract_required_section_headers(text: str, required_sections: list[str]) -> list[str]:
    """Return all ## headings in *text* that match one of *required_sections*, in order."""
    found: list[str] = []
    for match in SECTION_HEADER_RE.finditer(text):
        normalized = _normalize_section_title(match.group("title"))
        if normalized in required_sections:
            found.append(normalized)
    return found


def validate_section_structure(
    text: str,
    rule_or_sections,
) -> SectionStructureResult:
    """Validate that a draft contains exactly the required sections in order.

    Accepts either a LearningDraftRule instance or a plain list[str] of required sections.

    Rejects TWO kinds of failure (both are fail anchors from v2):
    1. Missing or mis-ordered required sections
    2. Extra unknown section headers not in required_sections
    """
    # Accept rule object or bare list
    if hasattr(rule_or_sections, "required_sections"):
        required = rule_or_sections.required_sections
    else:
        required = rule_or_sections

    # Collect ALL ## headings to detect extras
    all_headers: list[str] = []
    for match in SECTION_HEADER_RE.finditer(text):
        normalized = _normalize_section_title(match.group("title"))
        if normalized and len(normalized) > 0:
            all_headers.append(normalized)

    # Extract required sections present (in order of appearance)
    found_sections = extract_required_section_headers(text, required)

    # Check 1 — must have exactly the required sections in the expected order
    if found_sections != list(required):
        return SectionStructureResult(
            passed=False,
            found_sections=found_sections,
            errors=[
                "required section order mismatch: expected " + str(list(required)) + ", found " + str(found_sections)
            ],
        )

    # Check 2 — reject extra sections (v2 fail anchor)
    if set(all_headers) != set(required):
        extras = set(all_headers) - set(required)
        return SectionStructureResult(
            passed=False,
            found_sections=found_sections,
            errors=["extra section detected: " + str(extras)],
        )

    return SectionStructureResult(passed=True, found_sections=found_sections, errors=[])


# ---- Body length metric (Task 3) ----
ANY_HEADING_RE = re.compile(r"^#{1,6}\s+.+?$", re.MULTILINE)
REFERENCES_RE = re.compile(
    r"^#{1,6}\s+(References|참고문헌)\s*$.*\Z",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)
TOC_BLOCK_RE = re.compile(
    r"^#{1,6}\s+(목차|Table of Contents|TOC)\s*$.*?(?=^#{1,6}\s+|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)


def _dedupe_repeated_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    seen: dict[str, int] = {}
    kept: list[str] = []
    for line in lines:
        normalized = re.sub(r"\s+", " ", line.strip())
        if not normalized:
            kept.append("")  # preserve blank lines
            continue
        seen[normalized] = seen.get(normalized, 0) + 1
        if seen[normalized] == 1:  # keep only first occurrence
            kept.append(line)
    compact = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", compact).strip()


def _strip_non_body_blocks(text: str) -> str:
    without_references = REFERENCES_RE.sub("", text)
    without_toc = TOC_BLOCK_RE.sub("", without_references)
    without_headings = ANY_HEADING_RE.sub("", without_toc)
    return re.sub(r"\n{3,}", "\n\n", without_headings).strip()


def count_substantive_body_chars(text: str) -> int:
    body = _strip_non_body_blocks(text)
    body = _dedupe_repeated_lines(body)
    return len(body)

