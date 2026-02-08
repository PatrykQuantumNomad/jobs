"""Unit tests for anti-fabrication validation -- UNIT-07.

Tests cover:
- _extract_entities() for companies (multi-word capitalized, at/for patterns,
  stop word filtering), skills (known keywords, CamelCase, ALL_CAPS), and
  metrics (percentages, dollars, multipliers, large numbers)
- validate_no_fabrication() for identical text, new entity detection, warnings,
  reordering tolerance, and multiple fabrication types
- ValidationResult Pydantic model structure
"""

import pytest

from resume_ai.validator import ValidationResult, _extract_entities, validate_no_fabrication

# ---------------------------------------------------------------------------
# UNIT-07: Entity extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractEntities:
    """Verify _extract_entities() extracts companies, skills, and metrics."""

    # --- Companies ---

    def test_multi_word_company(self):
        """Multi-word capitalized sequence is extracted as a company."""
        text = "Worked at Translucent Computing for 5 years building cloud systems"
        entities = _extract_entities(text)
        assert "translucent computing" in entities["companies"]

    def test_at_pattern_single_word(self):
        """Single capitalized word after 'at' is extracted as a company."""
        text = "Worked at Google for 3 years on infrastructure projects"
        entities = _extract_entities(text)
        assert "google" in entities["companies"]

    def test_stop_words_filtered(self):
        """Common English action verbs are not extracted as companies."""
        text = "Led Built Managed"
        entities = _extract_entities(text)
        # These are stop words -- should NOT appear in companies
        assert "led" not in entities["companies"]
        assert "built" not in entities["companies"]
        assert "managed" not in entities["companies"]

    def test_for_pattern(self):
        """Capitalized phrase after 'for' is extracted as a company."""
        text = "Developed microservices for Stripe Solutions over two years"
        entities = _extract_entities(text)
        assert "stripe solutions" in entities["companies"]

    # --- Skills ---

    def test_known_keywords(self):
        """Known tech keywords in _TECH_KEYWORDS are extracted from text."""
        text = "Experience with python, kubernetes, and terraform for infrastructure"
        entities = _extract_entities(text)
        assert {"python", "kubernetes", "terraform"}.issubset(entities["skills"])

    def test_camelcase(self):
        """CamelCase terms are extracted as skills."""
        text = "Built APIs with FastAPI and LangGraph for orchestration"
        entities = _extract_entities(text)
        assert "fastapi" in entities["skills"]
        assert "langgraph" in entities["skills"]

    def test_allcaps_acronyms(self):
        """ALL_CAPS acronyms (2+ letters) are extracted as skills."""
        text = "Deployed to AWS, GKE, and EKS clusters across regions"
        entities = _extract_entities(text)
        assert "aws" in entities["skills"]
        assert "gke" in entities["skills"]
        assert "eks" in entities["skills"]

    def test_empty_text(self):
        """Empty string returns all empty sets."""
        entities = _extract_entities("")
        assert len(entities["companies"]) == 0
        assert len(entities["skills"]) == 0
        assert len(entities["metrics"]) == 0

    # --- Metrics ---

    def test_percentages(self):
        """Percentage values are extracted as metrics."""
        text = "Achieved 50% improvement in latency and 200% growth in throughput"
        entities = _extract_entities(text)
        assert "50%" in entities["metrics"]
        assert "200%" in entities["metrics"]

    def test_dollar_amounts(self):
        """Dollar amounts are extracted as metrics."""
        text = "Saved $1.2M in infrastructure costs and managed $200,000 budget"
        entities = _extract_entities(text)
        assert "$1.2m" in entities["metrics"]
        assert "$200,000" in entities["metrics"]

    def test_multipliers(self):
        """Multiplier values (Nx) are extracted as metrics."""
        text = "Achieved 10x performance improvement over previous system"
        entities = _extract_entities(text)
        assert "10x" in entities["metrics"]

    def test_large_numbers(self):
        """Large standalone numbers (3+ digits) are extracted as metrics."""
        text = "Processed 500 million records across 1000 nodes daily"
        entities = _extract_entities(text)
        assert "500" in entities["metrics"]
        assert "1000" in entities["metrics"]


# ---------------------------------------------------------------------------
# UNIT-07: Anti-fabrication validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAntiFabrication:
    """Verify validate_no_fabrication() detects new entities correctly."""

    def test_identical_text_is_valid(self):
        """Same text for original and tailored -> is_valid=True, all lists empty."""
        text = (
            "Worked at Translucent Computing using Python and Kubernetes. Achieved 50% improvement."
        )
        result = validate_no_fabrication(text, text)
        assert result.is_valid is True
        assert result.new_companies == []
        assert result.new_skills == []
        assert result.new_metrics == []
        assert result.warnings == []

    def test_empty_texts_valid(self):
        """Both empty strings -> is_valid=True."""
        result = validate_no_fabrication("", "")
        assert result.is_valid is True

    def test_new_company_detected(self):
        """Tailored text with new company -> is_valid=False, company in new_companies."""
        original = "Worked at Translucent Computing building cloud infrastructure for 5 years"
        tailored = (
            "Worked at Translucent Computing and at Stripe"
            " building cloud infrastructure for 5 years"
        )
        result = validate_no_fabrication(original, tailored)
        assert result.is_valid is False
        assert "stripe" in result.new_companies

    def test_new_skill_detected(self):
        """Tailored text with new skill -> is_valid=False, skill in new_skills."""
        original = "Experience with Python and Kubernetes for container orchestration"
        tailored = "Experience with Python and Kubernetes and Terraform for container orchestration"
        result = validate_no_fabrication(original, tailored)
        assert result.is_valid is False
        assert "terraform" in result.new_skills

    def test_new_metric_detected(self):
        """Tailored text with new metric -> is_valid=False, metric in new_metrics."""
        original = "Achieved 50% improvement in system latency over baseline"
        tailored = (
            "Achieved 50% improvement in system latency and 300% growth in throughput over baseline"
        )
        result = validate_no_fabrication(original, tailored)
        assert result.is_valid is False
        assert "300%" in result.new_metrics

    def test_warnings_generated(self):
        """When fabrications detected, warnings list is non-empty and human-readable."""
        original = "Worked at Google using Python for backend services"
        tailored = "Worked at Google using Python and Terraform for backend services"
        result = validate_no_fabrication(original, tailored)
        assert len(result.warnings) > 0
        # Each warning should be a human-readable string
        for warning in result.warnings:
            assert isinstance(warning, str)
            assert len(warning) > 10  # Not trivially short

    def test_skill_in_original_not_flagged(self):
        """Skill present in both original and tailored is NOT flagged as new."""
        original = "Experience with python and kubernetes for cloud infrastructure"
        tailored = "Deep experience with python and kubernetes for modern cloud infrastructure"
        result = validate_no_fabrication(original, tailored)
        assert "python" not in result.new_skills
        assert "kubernetes" not in result.new_skills

    def test_reordered_text_valid(self):
        """Same entities in different order -> is_valid=True."""
        original = (
            "Experience with python, kubernetes, and terraform at Google. Achieved 50% improvement."
        )
        tailored = (
            "Achieved 50% improvement at Google. Experience with terraform, kubernetes, and python."
        )
        result = validate_no_fabrication(original, tailored)
        assert result.is_valid is True

    def test_multiple_fabrication_types(self):
        """Tailored adds new company + skill + metric -> all three lists populated."""
        original = "Worked at Google using Python for backend systems"
        tailored = (
            "Worked at Google and at Stripe using Python and Terraform. "
            "Achieved 500% growth in throughput"
        )
        result = validate_no_fabrication(original, tailored)
        assert result.is_valid is False
        assert len(result.new_companies) > 0
        assert len(result.new_skills) > 0
        assert len(result.new_metrics) > 0


# ---------------------------------------------------------------------------
# UNIT-07: ValidationResult model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationResult:
    """Verify ValidationResult Pydantic model structure."""

    def test_result_is_pydantic_model(self):
        """ValidationResult is a Pydantic BaseModel."""
        from pydantic import BaseModel

        assert issubclass(ValidationResult, BaseModel)

    def test_result_explicit_values(self):
        """ValidationResult constructed with explicit is_valid=True has correct defaults."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.new_companies == []
        assert result.new_skills == []
        assert result.new_metrics == []
        assert result.warnings == []
