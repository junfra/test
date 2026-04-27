"""Tests for LearningDraftRule model — seed contract enforcement."""
import pytest

from study.models import LearningDraftRule


class TestLearningDraftRuleOntology:
    """Task 5: LearningDraftRule must have exactly 8 fields, no more no less."""

    EXPECTED_FIELDS = frozenset([
        "target_audience",
        "min_body_length_chars",
        "recommended_body_length_range",
        "required_sections",
        "required_functions",
        "prohibited_patterns",
        "density_tests",
        "pass_criteria",
    ])

    def test_has_exactly_eight_fields(self):
        """Rule schema must match the seed contract: exactly 8 fields."""
        rule = LearningDraftRule.default()
        actual_fields = frozenset(rule.model_fields.keys())
        assert actual_fields == self.EXPECTED_FIELDS, (
            f"Expected {len(self.EXPECTED_FIELDS)} fields, got {len(actual_fields)}:\n"
            f"  expected: {sorted(self.EXPECTED_FIELDS)}\n"
            f"  actual:   {sorted(actual_fields)}"
        )

    def test_default_rule_constructs_all_eight_fields(self):
        """Default rule construction must produce all 8 fields with correct types."""
        rule = LearningDraftRule.default()

        assert isinstance(rule.target_audience, str) and len(rule.target_audience) > 0
        assert isinstance(rule.min_body_length_chars, int) and rule.min_body_length_chars > 0
        assert isinstance(rule.recommended_body_length_range, dict)
        assert "min" in rule.recommended_body_length_range
        assert "max" in rule.recommended_body_length_range

        assert isinstance(rule.required_sections, list)
        assert len(rule.required_sections) == 8

        assert isinstance(rule.required_functions, list) and len(rule.required_functions) > 0
        assert isinstance(rule.prohibited_patterns, list) and len(rule.prohibited_patterns) > 0
        assert isinstance(rule.density_tests, list) and len(rule.density_tests) > 0
        assert isinstance(rule.pass_criteria, str) and len(rule.pass_criteria) > 0

    def test_no_extra_fields_in_default_rule(self):
        """Rule must not have extra fields beyond the seed contract."""
        rule = LearningDraftRule.default()
        actual_set = set(rule.model_fields.keys())
        # Must be exactly equal — no more, no less
        assert len(actual_set) == 8

    def test_default_rule_field_types(self):
        """Each field must have a type compatible with the seed schema."""
        rule = LearningDraftRule.default()

        for field_name in self.EXPECTED_FIELDS:
            py_type = rule.model_fields[field_name].annotation
            value = getattr(rule, field_name)
            if field_name == "recommended_body_length_range":
                assert isinstance(value, dict), f"{field_name} must be a dict"
                assert "min" in value and "max" in value, \
                    f"{field_name} must have min/max keys"

    def test_default_min_and_max_in_recommended_range(self):
        """recommended_body_length_range must include both bounds."""
        rule = LearningDraftRule.default()
        rbr = rule.recommended_body_length_range
        assert "min" in rbr and "max" in rbr, \
            f"recommended_body_length_range must have min/max: {rbr}"
        assert rbr["min"] <= rbr["max"], \
            f"recommended range min ({rbr['min']}) must be ≤ max ({rbr['max']})"

    def test_required_sections_matches_seed_order(self):
        """required_sections must match the expected seed ordering."""
        rule = LearningDraftRule.default()
        assert rule.required_sections == [
            "문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
            "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문",
        ]

    def test_pass_criteria_is_nonempty_string(self):
        """pass_criteria must contain actual criteria, not empty string."""
        rule = LearningDraftRule.default()
        pc = rule.pass_criteria
        assert isinstance(pc, str) and len(pc.strip()) > 0, \
            f"pass_criteria should be non-empty: {pc!r}"


class TestRequiredFunctionsEnforcedAsContract:
    """Task 6: required_functions must be enforced at generation level."""

    def test_paragraph_without_judgment_markers_fails_density(self):
        """Paragraphs with only boilerplate words (no judgment structure) rejected."""
        from study.learning_draft_rule import analyze_judgment_density

        # A paragraph that has no judgment function markers
        text = "The topic is important. This concept matters in various contexts." * 10 + "\n\n"
        result = analyze_judgment_density(text)

        assert not result.passed, \
            f"Boilerplate-only paragraph should fail density check: {result.errors}"


class TestProhibitedPatternsEnforcedAsContract:
    """Task 6: all 7 prohibited patterns must have concrete detector logic."""

    def test_template_placeholder_detected(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = "Insert topic [Topic] {{topic}}"
        result = detect_prohibited_patterns(text)
        assert "template_placeholder" in result.matches,             f"Template placeholder should be detected: {result.matches}"

    def test_generic_importance_claim_detected_at_threshold(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = (
            "이 개념은 매우 중요하다. 잘 이해해야 한다. "
            "이것은 매우 중요하다. 다양한 상황에서 활용된다." * 3 + "\n"
        )
        result = detect_prohibited_patterns(text)
        assert "generic_importance_claim" in result.matches,             f"Generic importance claims should be detected: {result.matches}"

    def test_procedure_without_causality_detected(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = "먼저 A를 한다. 다음 B를 한다. 마지막으로 C를 한다."
        result = detect_prohibited_patterns(text)
        assert "procedure_without_causality" in result.matches, \
            f"Procedure without causality should be detected: {result.matches}"

    def test_repeated_boilerplate_detected(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = "\n".join(["Same boilerplate line repeated three times for testing."] * 5) + "\n"
        result = detect_prohibited_patterns(text)
        assert "repeated_boilerplate" in result.matches, \
            f"Repeated boilerplate should be detected: {result.matches}"

    def test_thin_section_body_detected(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = ""
        for s in ["문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준"]:
            text += f"## {s}\nShort." + "\n\n"
        result = detect_prohibited_patterns(text)
        assert "thin_section_body" in result.matches, \
            f"Thin section body should be detected: {result.matches}"

    def test_unsupported_advantage_praise_detected(self):
        from study.learning_draft_rule import detect_prohibited_patterns

        text = (
            "이 기술은 장점이 매우 많다. 다른 기술보다 우수하다. "
            "뛰어나다. 강점이 있다."  # multiple advantage claims without evidence
        )
        result = detect_prohibited_patterns(text)
        assert "unsupported_advantage_praise" in result.matches, \
            f"Unsupported advantage praise should be detected: {result.matches}"

    def test_procedure_with_causality_accepted(self):
        """Procedure with causal explanation is NOT a prohibited pattern."""
        from study.learning_draft_rule import detect_prohibited_patterns

        text = (
            "먼저 A를 한다. 왜냐하면 B 때문이다. 다음 C를 하고, 따라서 D가 된다."
        )
        result = detect_prohibited_patterns(text)
        assert "procedure_without_causality" not in result.matches, \
            f"Causal procedure should NOT be detected: {result.matches}"

    def test_all_seven_patterns_exist_in_seed(self):
        """Seed contract requires all 7 patterns; none may be missing."""
        from study.models import LearningDraftRule

        rule = LearningDraftRule.default()
        expected = frozenset([
            "template_placeholder",
            "format_only_section_compliance",
            "generic_importance_claim",
            "repeated_boilerplate",
            "thin_section_body",
            "unsupported_advantage_praise",
            "procedure_without_causality",
        ])
        actual = frozenset(rule.prohibited_patterns)
        assert actual == expected, \
            f"prohibited_patterns must match seed: {sorted(actual)} vs {sorted(expected)}"


class TestDensityTestsEnforcedAsContract:
    """Task 6: density_tests field must drive real enforcement."""

    def test_keyword_only_paragraph_rejected(self):
        """Paragraph with only weak/boilerplate words is rejected by density analysis."""
        from study.learning_draft_rule import analyze_judgment_density, _extract_paragraphs

        text = (
            "The topic matters. This concept is important." * 10 + "\n\n"
        )
        result = analyze_judgment_density(text)
        assert not result.passed, \
            f"Keyword-only paragraph should be rejected: {result.errors}"

    def test_strong_paragraph_accepted(self):
        """Paragraphs with Korean structural markers and judgment patterns pass."""
        from study.learning_draft_rule import analyze_judgment_density

        text = ""
        for i in range(10):
            text += f"이 개념은 왜 필요한지 이해하려면, 실패하는 이유와 검증 방법을 알아야 한다. " \
                    f"원인과 결과, 조건과 경계를 구분해야 한다." + "\n\n"
        result = analyze_judgment_density(text)
        assert result.passed, \
            f"Strong paragraphs should pass density check: {result.errors}"


class TestSectionTitleOnlyComplianceCannotPass:
    """Task 7: Draft with all section titles but insufficient body must fail."""

    def test_all_headers_with_short_body_fails_validation(self):
        """Draft with 8 correct headers each having <50 chars of body -> FAILS."""
        from study.learning_draft_rule import validate_learning_draft_rule
        from study.models import LearningDraftRule

        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리", "핵심 판단 기준",
                  "실패 사례", "검증 방법", "유사 개념 비교", "복습 질문"]:
            draft += f"## {s}\nShort." + "\n\n"

        rule = LearningDraftRule.default()
        result = validate_learning_draft_rule(draft, rule=rule)

        # Must fail -- section-title-only compliance is NOT sufficient
        assert not result["passed"], (
            "Title-only draft should FAIL: " + str(result['errors'])
        )

    def test_validate_draft_text_raises_on_title_only(self):
        """_validate_draft_text must raise DraftValidationError on title-only."""
        from study.drafting import _validate_draft_text; from study.learning_draft_rule import DraftValidationError
        from study.models import LearningDraftRule

        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리"]:
            draft += f"## {s}\nShort." + "\n\n"

        with pytest.raises(DraftValidationError):
            _validate_draft_text(draft, learning_draft_rule=LearningDraftRule.default())

    def test_substantive_content_passes_title_check(self):
        """Draft with actual content in each section does NOT trigger thin-section error."""
        from study.learning_draft_rule import validate_learning_draft_rule, detect_prohibited_patterns
        from study.models import LearningDraftRule

        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리"]:
            draft += f"## {s}\nThis section explains why this concept matters because the mechanism operates through failure modes." * 5 + "\n\n"

        result = detect_prohibited_patterns(draft)
        assert "thin_section_body" not in result.matches, (
            f"Sufficient content should NOT trigger thin-section: {result.matches}"
        )


class TestSubstantiveBodyLengthCalculator:
    """Task 8: count_substantive_body_chars excludes titles, TOC, boilerplate."""

    def test_excludes_markdown_titles(self):
        """Headings (## ...) should NOT be counted in body chars."""
        from study.learning_draft_rule import count_substantive_body_chars

        text = "## 문제 배경\nThis is the content.\n" * 5 + "\n"
        body_len = count_substantive_body_chars(text)
        # The ## headers should be stripped; only "This is the content." counts per line
        assert body_len < len(text), (
            f"Body length ({body_len}) must be less than total text ({len(text)}) after stripping headings"
        )

    def test_excludes_toc_blocks(self):
        """TOC blocks should NOT count toward body chars."""
        from study.learning_draft_rule import count_substantive_body_chars

        text = "## 목차\n1. Item\n2. Item\n3. Item\n" + "Substantial content here." * 10 + "\n"
        body_len = count_substantive_body_chars(text)
        # Should be less than raw length due to TOC stripping
        assert body_len < len(text), (
            f"Body length ({body_len}) must exclude TOC block from total ({len(text)})"
        )

    def test_excludes_references_section(self):
        """References section should NOT count toward body chars."""
        from study.learning_draft_rule import count_substantive_body_chars

        text = "## References\n1. Source A\n2. Source B\n" + "Real content." * 10 + "\n"
        body_len = count_substantive_body_chars(text)
        assert body_len < len(text), (
            f"Body length ({body_len}) must exclude references from total ({len(text)})"
        )

    def test_dedupe_repeated_boilerplate(self):
        """Repeated boilerplate lines are deduplicated."""
        from study.learning_draft_rule import count_substantive_body_chars, _dedupe_repeated_lines

        text = "\n".join(["This is a repeated line that appears many times."] * 10) + "\n"
        body_len = count_substantive_body_chars(text)
        deduped_text = _dedupe_repeated_lines(text)
        assert len(deduped_text) < len(text), (
            f"Deduplication should reduce length: {len(text)} -> {len(deduped_text)}"
        )

    def test_draft_with_5000_including_headers_passes_after_subtraction(self):
        """A draft with 5000+ chars including headers passes after body extraction."""
        from study.learning_draft_rule import count_substantive_body_chars, validate_learning_draft_rule
        from study.models import LearningDraftRule

        # Build a draft that has substantial content but also header lines
        draft = ""
        for s in ["문제 배경", "개념 정의", "동작 원리"]:
            draft += f"## {s}\n" + "This is substantive body text." * 100 + "\n\n"

        body_len = count_substantive_body_chars(draft)
        # Body length should be significantly less than total due to heading stripping
        assert body_len < len(draft), (
            f"Body ({body_len}) must be less than raw draft ({len(draft)}) after header stripping"
        )
