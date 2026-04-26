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



# ────────────────────────────────────────────
# ProhibitedPatternDetector — hollow writing detection
# ────────────────────────────────────────────

from collections import Counter as _Counter


@dataclass(frozen=True)
class ProhibitedPatternResult:
    passed: bool
    matches: list[str]  # which patterns were detected
    errors: list[str]   # error messages for each match


TEMPLATE_PLACEHOLDER_RE = re.compile(r"(Insert topic|\[Topic\]|\{\{topic\}\})", re.IGNORECASE)

GENERIC_IMPORTANCE_RE = re.compile(
    r"(이 개념은 매우 중요하다|이것은 매우 중요하다|잘 이해해야 한다|다양한 상황에서 활용된다)"
)

PROCEDURE_WITHOUT_CAUSALITY_RE = re.compile(r"(먼저.+다음.+마지막으로)", re.DOTALL)

# Causal words that make a procedural description acceptable
CAUSAL_WORDS_RE = re.compile(
    r"왜냐하면|따라서|원인|결과|조건|검증|실패",
)


def _has_causality_in_span(text: str, span_match: "re.Match[str]") -> bool:
    """Return True if a causal word appears within the matched span."""
    return bool(CAUSAL_WORDS_RE.search(span_match.group(0)))


def detect_prohibited_patterns(text: str, rule=None) -> ProhibitedPatternResult:
    """Detect hollow writing patterns in a draft.

    Checks four categories of prohibited pattern and returns a result with
    ``passed=False`` when any pattern is detected.
    """
    matches: list[str] = []
    errors: list[str] = []

    # 1. Template placeholders
    if TEMPLATE_PLACEHOLDER_RE.search(text):
        matches.append("template_placeholder")
        errors.append("prohibited template placeholder detected in draft")

    # 2. Generic importance claims — trigger only at 2+ occurrences
    generic_count = len(GENERIC_IMPORTANCE_RE.findall(text))
    if generic_count >= 2:
        matches.append("generic_importance_claim")
        errors.append(
            f"detected {generic_count} generic importance claims (need specific reasoning)"
        )

    # 3. Procedure without causality — match procedural sequence, then check
    proc_match = PROCEDURE_WITHOUT_CAUSALITY_RE.search(text)
    if proc_match and not _has_causality_in_span(text, proc_match):
        matches.append("procedure_without_causality")
        errors.append("procedural description lacks causal explanation")

    # 4. Repeated boilerplate (any line >= 20 chars appearing 3+ times)
    lines = [line.rstrip() for line in text.splitlines()]
    long_lines = [l for l in lines if len(l) >= 20]
    freq = _Counter(long_lines)
    repeated = any(count >= 3 for count in freq.values())
    if repeated:
        matches.append("repeated_boilerplate")
        errors.append("repeated boilerplate detected (same line ≥ 3 times)")

    return ProhibitedPatternResult(
        passed=not bool(matches),
        matches=matches,
        errors=errors,
    )


# ─── Judgment Density Analysis ─────────────────────────────

@dataclass(frozen=True)
class JudgmentDensityResult:
    """Result of analyzing judgment function density in a learning draft."""
    passed: bool
    paragraph_count: int
    weak_paragraph_indexes: list[int]  # paragraphs without judgment functions
    errors: list[str]


JUDGMENT_FUNCTION_PATTERNS: dict[str, re.Pattern] = {
    "necessity_judgment": re.compile(r"(필요|이유|문제|부재|붕괴|왜냐하면)"),
    "boundary_judgment": re.compile(r"(정의|경계|포함|제외|구분|다르다|아니다)"),
    "mechanism_judgment": re.compile(r"(작동|동작|원리|흐름|상태|인과|조건|결과)"),
    "correctness_judgment": re.compile(r"(판단|기준|올바른|잘못된|정확|오해)"),
    "failure_diagnosis": re.compile(r"(실패|오류|무너|잘못|원인|증상)"),
    "verification_judgment": re.compile(r"(검증|확인|테스트|판별|증명|반례)"),
    "similarity_boundary_judgment": re.compile(r"(유사|비교|차이|다름)"),
}


def _extract_paragraphs(text: str) -> list[str]:
    """Extract paragraphs by splitting text on blank lines (double newline)."""
    paragraphs = []
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(stripped)

    if current:
        paragraphs.append("\n".join(current))

    return paragraphs


def analyze_judgment_density(text: str, rule: LearningDraftRule | None = None) -> JudgmentDensityResult:
    """Analyze the density of judgment functions in a learning draft.

    Returns a result indicating whether each substantive paragraph contains at
    least one Korean-language pattern expressing necessity, boundary, mechanism,
    correctness, failure diagnosis, verification, or similarity-boundary reasoning.

    A valid pass requires BOTH no weak paragraphs AND >= 8 paragraphs total.
    """
    paragraphs = _extract_paragraphs(text)
    weak_indexes: list[int] = []

    for i, paragraph in enumerate(paragraphs):
        if len(paragraph) < 30:
            # Paragraphs below the length threshold are automatically "weak"
            weak_indexes.append(i)
            continue

        matched = [name for name, pattern in JUDGMENT_FUNCTION_PATTERNS.items()
                   if pattern.search(paragraph)]
        if not matched:
            weak_indexes.append(i)

    errors: list[str] = []
    if weak_indexes:
        # THIS FORMAT IS THE FIX FROM V2 — must match test expectations exactly
        errors.append(
            f"judgment density failed: {len(weak_indexes)} of {len(paragraphs)} paragraphs lack judgment functions"
        )

    return JudgmentDensityResult(
        passed=not weak_indexes and len(paragraphs) >= 8,
        paragraph_count=len(paragraphs),
        weak_paragraph_indexes=weak_indexes,
        errors=errors,
    )
