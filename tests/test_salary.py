"""Unit tests for salary normalization -- UNIT-02.

Tests cover:
- parse_salary() with all 14 documented formats (Indeed range, hourly, Dice
  verbose, K-notation, CAD suffix, monthly, None/empty, unparseable, GBP/EUR)
- Sub-1000 heuristic (small numbers treated as K-shorthand)
- parse_salary_ints() with RemoteOK quirk (max=0 when min>0)
- NormalizedSalary.display compact format
- Raw field preservation
"""

import pytest

from core.salary import parse_salary, parse_salary_ints

# ---------------------------------------------------------------------------
# parse_salary -- all documented formats
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseSalary:
    """Parametrized tests covering all documented salary string formats."""

    @pytest.mark.parametrize(
        "text, expected_min, expected_max, expected_currency",
        [
            # Indeed range
            ("$150,000 - $200,000", 150000, 200000, "USD"),
            # Hourly to annual (85 * 2080 = 176800)
            ("$85/hr", 176800, 176800, "USD"),
            # Hourly alt format
            ("$85 an hour", 176800, 176800, "USD"),
            # Dice verbose
            ("USD 224,400.00 - 283,800.00 per year", 224400, 283800, "USD"),
            # Single value
            ("$175000", 175000, 175000, "USD"),
            # K-notation range
            ("$150K - $200K", 150000, 200000, "USD"),
            # K-notation single
            ("$175K", 175000, 175000, "USD"),
            # CAD suffix
            ("150000-180000 CAD", 150000, 180000, "CAD"),
            # Monthly (15000 * 12 = 180000)
            ("$15,000/month", 180000, 180000, "USD"),
            # GBP currency
            ("GBP 100,000", 100000, 100000, "GBP"),
            # EUR currency
            ("EUR 120,000", 120000, 120000, "EUR"),
            # None input
            (None, None, None, "USD"),
            # Empty string
            ("", None, None, "USD"),
            # Whitespace only
            ("   ", None, None, "USD"),
        ],
        ids=[
            "indeed_range",
            "hourly_slash",
            "hourly_an_hour",
            "dice_verbose",
            "single_value",
            "k_range",
            "k_single",
            "cad_suffix",
            "monthly",
            "gbp",
            "eur",
            "none_input",
            "empty_string",
            "whitespace_only",
        ],
    )
    def test_parse_salary_formats(self, text, expected_min, expected_max, expected_currency):
        result = parse_salary(text)
        assert result.min_annual == expected_min
        assert result.max_annual == expected_max
        assert result.currency == expected_currency

    def test_unparseable_returns_raw(self):
        """Unparseable text returns NormalizedSalary with raw set but no values."""
        result = parse_salary("Competitive")
        assert result.min_annual is None
        assert result.max_annual is None
        assert result.raw == "Competitive"


# ---------------------------------------------------------------------------
# Sub-1000 heuristic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseSalarySmallNumbers:
    """Test the sub-1000 K-shorthand heuristic separately.

    When multiplier == 1 (no hourly/monthly marker) and the extracted number
    is < 1000, the parser treats it as K-shorthand (e.g. "150" -> 150000).
    """

    @pytest.mark.parametrize(
        "text, expected_min, expected_max",
        [
            # Small number treated as K (150 -> 150000)
            ("150", 150000, 150000),
            # Above 1000 -- NOT treated as K
            ("1500", 1500, 1500),
            # Small number treated as K (85 -> 85000)
            ("85", 85000, 85000),
        ],
        ids=["150_as_k", "1500_literal", "85_as_k"],
    )
    def test_small_number_heuristic(self, text, expected_min, expected_max):
        result = parse_salary(text)
        assert result.min_annual == expected_min
        assert result.max_annual == expected_max


# ---------------------------------------------------------------------------
# parse_salary_ints (RemoteOK API)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseSalaryInts:
    """Test parse_salary_ints with RemoteOK-specific edge cases."""

    @pytest.mark.parametrize(
        "min_val, max_val, currency, expected_min, expected_max",
        [
            # Normal range
            (200000, 300000, "USD", 200000, 300000),
            # RemoteOK quirk: max=0 -> effective_max=min
            (200000, 0, "USD", 200000, 200000),
            # Both None
            (None, None, "USD", None, None),
            # Both zero (0 or None = None)
            (0, 0, "USD", None, None),
            # Same min/max, CAD currency
            (150000, 150000, "CAD", 150000, 150000),
        ],
        ids=[
            "normal_range",
            "remoteok_max_zero",
            "both_none",
            "both_zero",
            "same_min_max_cad",
        ],
    )
    def test_parse_salary_ints(self, min_val, max_val, currency, expected_min, expected_max):
        result = parse_salary_ints(min_val, max_val, currency)
        assert result.min_annual == expected_min
        assert result.max_annual == expected_max
        assert result.currency == currency


# ---------------------------------------------------------------------------
# Display format
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSalaryDisplay:
    """Verify NormalizedSalary.display produces compact format."""

    @pytest.mark.parametrize(
        "text, expected_display",
        [
            ("$150,000 - $200,000", "$150K-$200K USD/yr"),
            ("$175000", "$175K USD/yr"),
            ("150000-180000 CAD", "C$150K-C$180K CAD/yr"),
        ],
        ids=["usd_range", "usd_single", "cad_range"],
    )
    def test_parse_salary_display(self, text, expected_display):
        result = parse_salary(text)
        assert result.display == expected_display

    def test_none_display_empty(self):
        """None input produces empty display string."""
        result = parse_salary(None)
        assert result.display == ""

    def test_parse_salary_ints_display(self):
        """parse_salary_ints also produces correct display."""
        result = parse_salary_ints(200000, 300000)
        assert result.display == "$200K-$300K USD/yr"


# ---------------------------------------------------------------------------
# Raw field preservation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSalaryRawPreserved:
    """Verify the raw field stores the original input text."""

    def test_raw_preserved(self):
        result = parse_salary("$150K - $200K")
        assert result.raw == "$150K - $200K"

    def test_raw_empty_for_none(self):
        """None input produces empty raw string."""
        result = parse_salary(None)
        assert result.raw == ""

    def test_raw_stripped(self):
        """Leading/trailing whitespace is stripped from raw."""
        result = parse_salary("  $175000  ")
        assert result.raw == "$175000"
