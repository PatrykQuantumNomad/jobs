"""Unit tests for deduplication engine -- UNIT-05 and UNIT-06.

Tests cover:
- _normalize_company() with 15+ suffix/case/whitespace/trailing-comma variants
- Exact dedup (Pass 1): identical dedup_key merging, winner selection by date
  and description length, alias recording, empty/single input
- Fuzzy dedup (Pass 2): LLC/Inc/Corp/Co variant merging, cross-platform,
  three-way merge, sorted aliases
- Exact vs fuzzy boundary: Corp not stripped in dedup_key() but merged by
  _normalize_company() in Pass 2
"""

import pytest

from dedup import _normalize_company, fuzzy_deduplicate
from models import Job


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_job(company: str, title: str, platform: str = "indeed", **kwargs) -> Job:
    """Build a Job with minimal required fields for dedup tests."""
    defaults = {
        "url": f"https://example.com/{company.lower().replace(' ', '-')}",
    }
    defaults.update(kwargs)
    return Job(platform=platform, title=title, company=company, **defaults)


# ---------------------------------------------------------------------------
# UNIT-05 / UNIT-06: _normalize_company
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeCompany:
    """Verify _normalize_company strips suffixes, whitespace, case, and commas."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("Google Inc.", "google"),
            ("Google Inc", "google"),
            ("Google LLC", "google"),
            ("Google Ltd.", "google"),
            ("Google Ltd", "google"),
            ("Google Corp.", "google"),
            ("Google Corp", "google"),
            ("Google Corporation", "google"),
            ("Google Incorporated", "google"),
            ("Google Company", "google"),
            ("Google Co.", "google"),
            ("GOOGLE", "google"),  # case only
            ("  Google  ", "google"),  # whitespace
            ("Google,", "google"),  # trailing comma
            ("Acme", "acme"),  # no suffix
        ],
    )
    def test_normalize(self, input_name, expected):
        assert _normalize_company(input_name) == expected


# ---------------------------------------------------------------------------
# UNIT-05: Exact dedup (Pass 1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExactDedup:
    """Verify Pass 1 exact dedup_key matching behavior."""

    def test_identical_jobs_dedup_to_one(self):
        """Two jobs with same company+title -> 1 result."""
        j1 = _make_job("Google", "Staff Engineer")
        j2 = _make_job("Google", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_different_titles_not_deduped(self):
        """Same company, different titles -> 2 results."""
        j1 = _make_job("Google", "Staff Engineer")
        j2 = _make_job("Google", "Senior Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 2

    def test_different_companies_not_deduped(self):
        """Different companies, same title -> 2 results."""
        j1 = _make_job("Google", "Staff Engineer")
        j2 = _make_job("Microsoft", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 2

    def test_case_insensitive(self):
        """'Google' vs 'google' same title -> 1 result."""
        j1 = _make_job("Google", "Staff Engineer")
        j2 = _make_job("google", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_inc_suffix_stripped(self):
        """'Google Inc.' vs 'Google' same title -> 1 result (dedup_key strips ' inc.')."""
        j1 = _make_job("Google Inc.", "Staff Engineer")
        j2 = _make_job("Google", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_winner_has_more_recent_date(self):
        """Two duplicates with different posted_date -> winner is more recent."""
        j1 = _make_job("Google", "Staff Engineer", posted_date="2026-01-01")
        j2 = _make_job("Google", "Staff Engineer", posted_date="2026-02-01")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1
        assert result[0].posted_date == "2026-02-01"

    def test_winner_has_longer_description(self):
        """Same date, different description lengths -> winner is longer."""
        j1 = _make_job(
            "Google", "Staff Engineer", posted_date="2026-01-01", description="short"
        )
        j2 = _make_job(
            "Google",
            "Staff Engineer",
            posted_date="2026-01-01",
            description="a much longer description with more details about the role",
        )
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1
        assert "much longer" in result[0].description

    def test_alias_recorded(self):
        """When two companies merge, loser's name appears in winner.company_aliases."""
        j1 = _make_job("Google Inc.", "Staff Engineer", posted_date="2026-01-01")
        j2 = _make_job("Google", "Staff Engineer", posted_date="2026-02-01")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1
        # j2 (newer) wins; j1's company name should be in aliases
        assert "Google Inc." in result[0].company_aliases

    def test_empty_list(self):
        """fuzzy_deduplicate([]) -> []."""
        assert fuzzy_deduplicate([]) == []

    def test_single_job(self):
        """fuzzy_deduplicate([job]) -> [job]."""
        job = _make_job("Google", "Staff Engineer")
        result = fuzzy_deduplicate([job])
        assert len(result) == 1
        assert result[0] is job


# ---------------------------------------------------------------------------
# UNIT-06: Fuzzy dedup (Pass 2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFuzzyDedup:
    """Verify Pass 2 fuzzy company-name matching behavior."""

    def test_llc_vs_inc_merges(self):
        """'Google LLC' and 'Google Inc.' same title -> 1 result."""
        # dedup_key: "google" for Inc., "google" for LLC -> same key, so Pass 1 merges.
        # But if dedup_key doesn't catch it, Pass 2 would.
        j1 = _make_job("Google LLC", "Staff Engineer")
        j2 = _make_job("Google Inc.", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_corp_variants_merge(self):
        """'Acme Corp.' and 'Acme Corporation' same title -> 1 result."""
        j1 = _make_job("Acme Corp.", "Developer")
        j2 = _make_job("Acme Corporation", "Developer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_co_variant_merges(self):
        """'Tech Co.' and 'Tech Company' same title -> 1 result."""
        j1 = _make_job("Tech Co.", "Developer")
        j2 = _make_job("Tech Company", "Developer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_completely_different_companies_not_merged(self):
        """'Google' and 'Microsoft' same title -> 2 results."""
        j1 = _make_job("Google", "Staff Engineer")
        j2 = _make_job("Microsoft", "Staff Engineer")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 2

    def test_three_way_merge(self):
        """'Google Inc', 'Google LLC', 'Google Corp' all same title -> 1 result with 2 aliases."""
        j1 = _make_job("Google Inc", "Staff Engineer", posted_date="2026-02-01")
        j2 = _make_job("Google LLC", "Staff Engineer", posted_date="2026-01-15")
        j3 = _make_job("Google Corp", "Staff Engineer", posted_date="2026-01-01")
        result = fuzzy_deduplicate([j1, j2, j3])
        assert len(result) == 1
        # Winner is j1 (most recent). j2 and j3 names are aliases.
        assert len(result[0].company_aliases) == 2

    def test_cross_platform_dedup(self):
        """Same company+title from 'indeed' and 'dice' -> 1 result."""
        j1 = _make_job("Google", "Staff Engineer", platform="indeed")
        j2 = _make_job("Google", "Staff Engineer", platform="dice")
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1

    def test_fuzzy_aliases_sorted(self):
        """After fuzzy merge, company_aliases list is sorted alphabetically."""
        j1 = _make_job("Zeta Corp", "Developer", posted_date="2026-02-01")
        j2 = _make_job("Zeta Company", "Developer", posted_date="2026-01-15")
        j3 = _make_job("Zeta Co.", "Developer", posted_date="2026-01-01")
        result = fuzzy_deduplicate([j1, j2, j3])
        assert len(result) == 1
        aliases = result[0].company_aliases
        assert aliases == sorted(aliases)

    def test_corp_not_in_exact_pass(self):
        """'Google Corp' and 'Google' same title -- merged by fuzzy pass (not exact).

        dedup_key() does NOT strip ' corp' -> different exact keys.
        _normalize_company() DOES strip ' corp' -> same normalized name in Pass 2.
        After full dedup: exactly 1 result.
        """
        j1 = _make_job("Google Corp", "Staff Engineer")
        j2 = _make_job("Google", "Staff Engineer")
        # Verify they have DIFFERENT dedup_keys (exact pass keeps both)
        assert j1.dedup_key() != j2.dedup_key()
        # But fuzzy dedup merges them
        result = fuzzy_deduplicate([j1, j2])
        assert len(result) == 1
