"""Unit tests for Pydantic models -- UNIT-01.

Tests cover:
- JobStatus enum values and string serialization
- Job model validation (valid/invalid construction, field validators, cross-field
  validators, defaults)
- Job.dedup_key() normalization (7+ parametrized cases)
- SearchQuery bounds validation
- CandidateProfile defaults
"""

import pytest
from pydantic import ValidationError

from models import CandidateProfile, Job, JobStatus, SearchQuery

# ---------------------------------------------------------------------------
# JobStatus enum
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJobStatus:
    """Verify all JobStatus enum values exist and serialize correctly."""

    ALL_STATUSES = [
        ("DISCOVERED", "discovered"),
        ("SCORED", "scored"),
        ("SAVED", "saved"),
        ("APPLIED", "applied"),
        ("PHONE_SCREEN", "phone_screen"),
        ("TECHNICAL", "technical"),
        ("FINAL_INTERVIEW", "final_interview"),
        ("OFFER", "offer"),
        ("REJECTED", "rejected"),
        ("WITHDRAWN", "withdrawn"),
        ("GHOSTED", "ghosted"),
    ]

    def test_all_statuses_accessible(self):
        """All 11 enum values exist and are accessible by name."""
        for name, _ in self.ALL_STATUSES:
            assert hasattr(JobStatus, name), f"JobStatus.{name} missing"

    @pytest.mark.parametrize("name,expected_value", ALL_STATUSES)
    def test_status_string_values(self, name, expected_value):
        """Each enum member's .value matches the expected snake_case string."""
        member = getattr(JobStatus, name)
        assert member.value == expected_value
        # StrEnum members should also compare equal to their string value
        assert member == expected_value


# ---------------------------------------------------------------------------
# Job model validation
# ---------------------------------------------------------------------------

_MINIMAL_JOB: dict = {
    "platform": "indeed",
    "title": "Engineer",
    "company": "ACME",
    "url": "https://example.com",
}


@pytest.mark.unit
class TestJob:
    """Validate Job model construction, field validators, and defaults."""

    def test_valid_minimal_job(self):
        """Minimal required fields construct successfully with defaults."""
        job = Job(**_MINIMAL_JOB)
        assert job.platform == "indeed"
        assert job.title == "Engineer"
        assert job.company == "ACME"
        assert job.url == "https://example.com"

    def test_valid_full_job(self):
        """All fields populated constructs successfully."""
        job = Job(
            id="abc123",
            platform="dice",
            title="Staff Engineer",
            company="BigCorp",
            location="Remote",
            url="https://dice.com/jobs/abc123",
            salary="$150,000 - $200,000",
            salary_min=150000,
            salary_max=200000,
            apply_url="https://dice.com/apply/abc123",
            description="Great role for a staff engineer.",
            posted_date="2026-02-01",
            tags=["python", "kubernetes"],
            easy_apply=True,
            salary_display="$150K-$200K USD/yr",
            salary_currency="USD",
            company_aliases=["Big Corp", "BIGCORP"],
            score=5,
            status=JobStatus.SCORED,
            applied_date=None,
            notes="Top match",
        )
        assert job.score == 5
        assert job.salary_min == 150000
        assert job.salary_max == 200000
        assert job.tags == ["python", "kubernetes"]
        assert job.status == JobStatus.SCORED

    def test_invalid_platform_rejected(self):
        """Platform not in Literal['indeed','dice','remoteok'] raises."""
        with pytest.raises(ValidationError):
            Job(platform="linkedin", title="Eng", company="Co", url="https://x.com")  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("field", ["title", "company", "url"])
    def test_missing_required_fields(self, field):
        """Omitting each required field individually raises ValidationError."""
        data = {**_MINIMAL_JOB}
        del data[field]
        with pytest.raises(ValidationError):
            Job(**data)

    def test_score_lower_bound(self):
        """score=0 rejected (ge=1)."""
        with pytest.raises(ValidationError):
            Job(**_MINIMAL_JOB, score=0)

    def test_score_upper_bound(self):
        """score=6 rejected (le=5)."""
        with pytest.raises(ValidationError):
            Job(**_MINIMAL_JOB, score=6)

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_score_valid_range(self, score):
        """Scores 1-5 all succeed."""
        job = Job(**_MINIMAL_JOB, score=score)
        assert job.score == score

    def test_score_none_allowed(self):
        """score=None (default) is valid."""
        job = Job(**_MINIMAL_JOB)
        assert job.score is None

    def test_salary_max_gte_min_valid(self):
        """salary_min < salary_max passes."""
        job = Job(**_MINIMAL_JOB, salary_min=100000, salary_max=200000)
        assert job.salary_min == 100000
        assert job.salary_max == 200000

    def test_salary_max_gte_min_equal(self):
        """salary_min == salary_max passes."""
        job = Job(**_MINIMAL_JOB, salary_min=150000, salary_max=150000)
        assert job.salary_min == 150000
        assert job.salary_max == 150000

    def test_salary_max_lt_min_rejected(self):
        """salary_max < salary_min raises with descriptive message."""
        with pytest.raises(ValidationError, match="salary_max must be >= salary_min"):
            Job(**_MINIMAL_JOB, salary_min=200000, salary_max=100000)

    def test_salary_min_none_max_set(self):
        """salary_min=None, salary_max set -- validator only checks when both are set."""
        job = Job(**_MINIMAL_JOB, salary_min=None, salary_max=200000)
        assert job.salary_min is None
        assert job.salary_max == 200000

    def test_default_values(self):
        """Verify all default values are correct."""
        job = Job(**_MINIMAL_JOB)
        assert job.id == ""
        assert job.location == ""
        assert job.status == JobStatus.DISCOVERED
        assert job.salary_currency == "USD"
        assert job.easy_apply is False
        assert job.tags == []
        assert job.company_aliases == []
        assert job.salary is None
        assert job.salary_min is None
        assert job.salary_max is None
        assert job.description == ""
        assert job.score is None
        assert job.applied_date is None
        assert job.notes is None


# ---------------------------------------------------------------------------
# Job.dedup_key() normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDedupKey:
    """Verify dedup_key strips Inc/LLC/Ltd suffixes, commas, lowercases."""

    @pytest.mark.parametrize(
        "company,title,expected_key",
        [
            ("Google Inc.", "Staff Engineer", "google::staff engineer"),
            ("Google, Inc", "Staff Engineer", "google::staff engineer"),
            ("GOOGLE LLC", "staff engineer", "google::staff engineer"),
            ("Google Ltd", "Staff Engineer", "google::staff engineer"),
            ("Google", "Staff Engineer", "google::staff engineer"),
            ("  Google  ", "  Staff Engineer  ", "google::staff engineer"),
            # "Corp" is NOT stripped -- only Inc/LLC/Ltd
            ("Acme Corp", "Developer", "acme corp::developer"),
        ],
    )
    def test_dedup_key_normalization(self, company, title, expected_key):
        job = Job(platform="indeed", title=title, company=company, url="https://x.com")
        assert job.dedup_key() == expected_key


# ---------------------------------------------------------------------------
# SearchQuery model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchQuery:
    """Validate SearchQuery construction and bounds."""

    def test_valid_query(self):
        """Minimal construction with defaults."""
        q = SearchQuery(query="python")
        assert q.query == "python"
        assert q.platform == "indeed"
        assert q.location == "Remote"
        assert q.max_pages == 5

    def test_max_pages_lower_bound(self):
        """max_pages=0 rejected (ge=1)."""
        with pytest.raises(ValidationError):
            SearchQuery(query="python", max_pages=0)

    def test_max_pages_upper_bound(self):
        """max_pages=11 rejected (le=10)."""
        with pytest.raises(ValidationError):
            SearchQuery(query="python", max_pages=11)

    @pytest.mark.parametrize("pages", range(1, 11))
    def test_valid_max_pages(self, pages):
        """max_pages 1-10 all succeed."""
        q = SearchQuery(query="python", max_pages=pages)
        assert q.max_pages == pages

    def test_invalid_platform(self):
        """platform='glassdoor' rejected (not in Literal)."""
        with pytest.raises(ValidationError):
            SearchQuery(query="python", platform="glassdoor")  # type: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# CandidateProfile model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCandidateProfile:
    """Validate CandidateProfile defaults and custom values."""

    def test_default_values(self):
        """No-args construction has correct defaults."""
        p = CandidateProfile()
        assert p.first_name == ""
        assert p.last_name == ""
        assert p.email == ""
        assert p.phone == ""
        assert p.location == ""
        assert p.github == ""
        assert p.website == ""
        assert p.desired_salary_usd == 200_000
        assert p.target_titles == []
        assert p.tech_keywords == []
        assert p.resume_path == "resumes/Patryk_Golabek_Resume.pdf"

    def test_custom_values(self):
        """Custom values are stored correctly."""
        p = CandidateProfile(
            first_name="Patryk",
            last_name="Golabek",
            target_titles=["Staff Engineer"],
            tech_keywords=["python", "kubernetes"],
            desired_salary_usd=250_000,
        )
        assert p.first_name == "Patryk"
        assert p.last_name == "Golabek"
        assert p.target_titles == ["Staff Engineer"]
        assert p.tech_keywords == ["python", "kubernetes"]
        assert p.desired_salary_usd == 250_000
