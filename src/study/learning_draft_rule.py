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

    # 5. format_only_section_compliance — section headers exist but bodies are <100 chars each
    def _check_format_only(text):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) < 3:
            return False
        short_sections = sum(1 for p in paragraphs if len(p) < 100 and not any(kw in p.lower() for kw in ["왜냐하면", "따라서", "실패", "검증"]))
        # If more than half of all paragraphs are very short, it's format-only compliance
        return short_sections > len(paragraphs) / 2

    if _check_format_only(text):
        matches.append("format_only_section_compliance")
        errors.append(
            "section headers present but bodies are too short to support judgment (format-only compliance)"
        )

    # 6. thin_section_body — any ## section with <50 chars of substantive body
    def _check_thin_sections(text):
        section_re = re.compile(r"^##\s+(.+?)$", re.MULTILINE)
        headers = [(m.start(), m.group(1).strip()) for m in section_re.finditer(text)]
        if len(headers) < 3:
            return False
        thin_count = 0
        for i, (pos, _header) in enumerate(headers):
            end_pos = headers[i + 1][0] if i + 1 < len(headers) else len(text)
            body = text[pos:end_pos]
            # Remove the header line itself and blank lines
            body_text = re.sub(r"^##\s+.+?$", "", body, flags=re.MULTILINE).strip()
            if len(body_text) < 50:
                thin_count += 1
        return thin_count >= len(headers) / 2

    if _check_thin_sections(text):
        matches.append("thin_section_body")
        errors.append(
            "multiple sections have insufficient body content relative to header presence"
        )

    # 7. unsupported_advantage_praise — claims of advantage without supporting evidence/basis
    ADVANTAGE_PHRASES_RE = re.compile(r"(장점|유리하다|우수하다|뛰어나다|강점이 있다|메리트가 있다)")
    EVIDENCE_KEYWORDS_RE = re.compile(
        r"(이유|원인|조건|검증|실패|근거|비교|차이|판단|기준|반례|원리|메커니즘)"
    )
    advantage_sections = ADVANTAGE_PHRASES_RE.findall(text)
    evidence_present = EVIDENCE_KEYWORDS_RE.search(text) is not None

    # If there are multiple advantage claims but no supporting evidence keywords
    if len(advantage_sections) >= 2 and not evidence_present:
        matches.append("unsupported_advantage_praise")
        errors.append(
            "multiple advantage claims without supporting evidence or reasoning"
        )

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

        # Must have BOTH structural indicator AND semantic patterns (not just keywords)
        has_structural = bool(re.search(
            r"(왜냐하면|따라서|원인|결과|조건|검증|실패|근거|"  # Korean markers
            r"because|therefore|consequently|caus[ae]|constraint|failure|mechanism)",  # English equivalents
            paragraph, flags=re.IGNORECASE
        ))
        matched = [name for name, pattern in JUDGMENT_FUNCTION_PATTERNS.items()
                   if pattern.search(paragraph)]
        if not (has_structural and matched):
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


# ─── Unified Validator ──────────────────────────────────────────────

def validate_learning_draft_rule(
    text: str,
    rule=None,
) -> dict:
    """Run all individual validators and combine results into a single verdict.

    Returns ``{"passed": bool, "errors": list[str]}``.

    A draft passes only if ALL checks pass:
      - section order matches required_sections exactly
      - no prohibited patterns detected
      - judgment density threshold met (≥8 paragraphs with judgment functions)
      - body length ≥ min_body_length_chars
    """
    errors: list[str] = []
    passed = True

    # 1. Section structure
    sec_result = validate_section_structure(text, rule if rule else None)
    if not sec_result.passed:
        passed = False
        errors.extend(sec_result.errors)

    # 2. Prohibited patterns
    pattern_result = detect_prohibited_patterns(text, rule)
    if not pattern_result.passed:
        passed = False
        errors.extend(pattern_result.errors)

    # 3. Judgment density
    density_result = analyze_judgment_density(text, rule)
    if not density_result.passed:
        passed = False
        errors.extend(density_result.errors)

    # 4. Body length (if rule provides min_body_length_chars)
    if rule is not None and hasattr(rule, 'min_body_length_chars'):
        body_len = count_substantive_body_chars(text)
        if body_len < rule.min_body_length_chars:
            passed = False
            errors.append(
                f"body length {body_len} below minimum {rule.min_body_length_chars}"
            )    # 4b. Recommended range upper bound (Task 3)
    if rule is not None and hasattr(rule, 'recommended_body_length_range'):
        rec_range = rule.recommended_body_length_range
        body_len = count_substantive_body_chars(text)
        if 'max' in rec_range and body_len > rec_range['max']:
            passed = False
            errors.append(
                f"body length {body_len} exceeds recommended max {rec_range['max']} (recommended range: min={rec_range.get('min', '?')}, max={rec_range['max']})"
            )

    # ─── Exit conditions — computed independently from overall `passed` (Task 4) ───
    rule_locked = sec_result.passed and pattern_result.passed and density_result.passed
    no_open_drift = True

    # no_open_drift specifically rejects format-only compliance
    pattern_result_no_drift = detect_prohibited_patterns(text, rule)
    if not pattern_result_no_drift.passed:
        for m in pattern_result_no_drift.matches:
            if m in ("thin_section_body", "format_only_section_compliance"):
                no_open_drift = False

    # Also check body length as an open-drift signal (too short = thin sections)
    if rule is not None and hasattr(rule, 'min_body_length_chars'):
        body_len = count_substantive_body_chars(text)
        if body_len < rule.min_body_length_chars:
            no_open_drift = False

    return {
        "passed": passed,
        "errors": errors,
        "exit_conditions": {
            "rule_locked": rule_locked,
            "no_open_drift": no_open_drift,
        },
        "state": {
            "rule_locked": rule_locked,
            "no_open_drift": no_open_drift,
        },
    }


# ─────────── DraftValidationError (Task 1) ───────────

class DraftValidationError(RuntimeError):
    """Raised when a generated learning draft violates the locked draft rule."""
    pass
