"""Tests for LearningDraftRule Pydantic model."""
from study.models import LearningDraftRule


class TestLearningDraftRuleModel:

    def test_learning_draft_rule_has_exactly_8_seed_fields(self):
        """Verify exactly 8 field names from the seed ontology."""
        expected = {
            "target_audience",
            "min_body_length_chars",
            "recommended_body_length_range",
            "required_sections",
            "required_functions",
            "prohibited_patterns",
            "density_tests",
            "pass_criteria",
        }
        assert set(LearningDraftRule.model_fields.keys()) == expected

    def test_learning_draft_rule_defaults_to_full_standard(self):
        """Check default values match the seed specification."""
        rule = LearningDraftRule.default()

        # String fields
        assert rule.target_audience == "first-time learners"
        assert (
            rule.pass_criteria
            == "Pass only when the draft has 5000+ body characters, all 8 required sections in strict order..."
        )

        # Integer / dict fields
        assert rule.min_body_length_chars == 5000
        assert rule.recommended_body_length_range == {"min": 5000, "max": 7000}

        # List defaults — must be independent instances (no shared mutation)
        assert rule.required_sections == LearningDraftRule.DEFAULT_REQUIRED_SECTIONS
        required_fns = [
            "necessity_judgment",
            "boundary_judgment",
            "mechanism_judgment",
            "correctness_judgment",
            "failure_diagnosis",
            "verification_judgment",
            "similarity_boundary_judgment",
            "self_explanation_prompt",
            "judgment_function_per_paragraph",
        ]
        assert rule.required_functions == required_fns

        prohibited = [
            "template_placeholder",
            "format_only_section_compliance",
            "generic_importance_claim",
            "repeated_boilerplate",
            "thin_section_body",
            "unsupported_advantage_praise",
            "procedure_without_causality",
        ]
        assert rule.prohibited_patterns == prohibited

        density = [
            "body_length_excludes_title_toc_references",
            "strict_required_section_order",
            "minimum_section_body_length",
            "judgment_function_per_paragraph",
            "low_repetition_ratio",
            "format_only_section_compliance",
            "causal_linkage_across_core_sections",
        ]
        assert rule.density_tests == density

    def test_learning_draft_rule_with_overrides(self):
        """Ensure with_overrides returns a new instance, mutates only overrides."""
        original = LearningDraftRule.default()
        overridden = original.with_overrides(
            min_body_length_chars=6000,
            target_audience="advanced learners",
        )

        # Original must be untouched
        assert original.min_body_length_chars == 5000
        assert original.target_audience == "first-time learners"

        # Overridden instance reflects changes
        assert overridden.min_body_length_chars == 6000
        assert overridden.target_audience == "advanced learners"

        # Non-overridden fields remain unchanged
        assert overridden.required_functions == original.required_functions

    def test_learning_draft_rule_required_sections_copy_isolation(self):
        """required_sections must not mutate on shared DEFAULT_REQUIRED_SECTIONS."""
        a = LearningDraftRule()
        b = LearningDraftRule()
        a.required_sections.append("extra")
        assert "extra" not in b.required_sections

    def test_learning_draft_rule_default_classmethod_exists(self):
        """Verify the default classmethod returns an instance."""
        rule = LearningDraftRule.default()
        assert isinstance(rule, LearningDraftRule)
