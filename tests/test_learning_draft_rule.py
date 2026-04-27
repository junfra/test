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
