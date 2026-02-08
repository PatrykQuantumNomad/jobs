"""Unit tests for the job scoring engine (UNIT-03 and UNIT-04).

Tests cover:
- Title scoring: exact match (2pts), keyword match (1pt), no match (0pts)
- Tech scoring: threshold boundaries (5+ -> 2, 2-4 -> 1, 0-1 -> 0), tags, matched list
- Location scoring: remote variants, on-site, empty
- Salary scoring: above/below/at target, no salary
- Overall score mapping: raw -> 1-5 boundaries
- Batch scoring: in-place mutation, status setting, sort order
- Custom weights: zero out a factor, double a factor
- ScoreBreakdown: display_inline, display_with_keywords, to_dict, tuple return

All tests use explicit CandidateProfile and ScoringWeights to ensure deterministic
scoring without relying on config.yaml values.
"""

import pytest

from config import ScoringWeights
from models import CandidateProfile, Job, JobStatus
from scorer import JobScorer, ScoreBreakdown

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scorer(
    target_titles=None,
    tech_keywords=None,
    desired_salary_usd=200_000,
    weights=None,
):
    """Build a scorer with explicit profile and weights (no config file dependency)."""
    profile = CandidateProfile(
        target_titles=target_titles
        or [
            "Senior Software Engineer",
            "Principal Engineer",
            "Staff Engineer",
            "Platform Engineering Lead",
            "DevOps Lead",
        ],
        tech_keywords=tech_keywords
        or [
            "python",
            "kubernetes",
            "terraform",
            "docker",
            "aws",
        ],
        desired_salary_usd=desired_salary_usd,
    )
    return JobScorer(profile=profile, weights=weights or ScoringWeights())


def _make_job(**kwargs) -> Job:
    """Build a Job with sensible defaults for scoring tests."""
    defaults: dict = {
        "platform": "indeed",
        "title": "Software Developer",
        "company": "TestCo",
        "url": "https://example.com/job",
        "location": "",
        "description": "",
    }
    defaults.update(kwargs)
    return Job(**defaults)


# ---------------------------------------------------------------------------
# UNIT-03: Scoring Correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTitleScoring:
    """Title factor: 0 (no match), 1 (keyword), 2 (exact target title)."""

    def test_exact_target_title_scores_2(self):
        scorer = _make_scorer()
        job = _make_job(title="Principal Engineer")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 2

    def test_target_title_substring_scores_2(self):
        scorer = _make_scorer()
        job = _make_job(title="Senior Principal Engineer at Google")
        # "Principal Engineer" is a substring of the title
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 2

    def test_keyword_match_scores_1(self):
        scorer = _make_scorer()
        job = _make_job(title="Lead Data Scientist")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 1

    def test_keyword_case_insensitive(self):
        scorer = _make_scorer()
        job = _make_job(title="SENIOR Developer")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 1

    @pytest.mark.parametrize(
        "keyword",
        [
            "senior",
            "principal",
            "staff",
            "lead",
            "manager",
            "architect",
            "devops",
            "platform",
            "infrastructure",
            "sre",
        ],
    )
    def test_keyword_parametrized(self, keyword):
        scorer = _make_scorer()
        job = _make_job(title=f"{keyword} Analyst Role")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 1, f"Keyword '{keyword}' should score 1"

    def test_no_match_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(title="Junior Analyst")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 0

    def test_empty_title_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(title="")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 0


@pytest.mark.unit
class TestTechScoring:
    """Tech factor: 0 (0-1 keywords), 1 (2-4 keywords), 2 (5+ keywords)."""

    def test_five_plus_keywords_scores_2(self):
        scorer = _make_scorer()
        job = _make_job(description="python kubernetes terraform docker aws gcp")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.tech_points == 2
        assert len(breakdown.tech_matched) >= 5

    def test_two_to_four_keywords_scores_1(self):
        scorer = _make_scorer()
        job = _make_job(description="python kubernetes")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.tech_points == 1

    def test_one_keyword_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(description="python")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.tech_points == 0

    def test_no_keywords_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(description="no matching technologies here")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.tech_points == 0

    def test_tags_contribute(self):
        scorer = _make_scorer()
        job = _make_job(
            description="",
            tags=["python", "kubernetes", "terraform", "docker", "aws"],
        )
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.tech_points == 2, "Tags should be included in the search text"

    def test_tech_matched_list(self):
        scorer = _make_scorer()
        job = _make_job(description="python kubernetes terraform")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert set(breakdown.tech_matched) == {"python", "kubernetes", "terraform"}


@pytest.mark.unit
class TestLocationScoring:
    """Location factor: 0 (on-site/empty), 1 (remote or Ontario/Canada)."""

    @pytest.mark.parametrize(
        "location",
        [
            "Remote",
            "remote",
            "Anywhere",
            "Work from home",
            "Ontario, Canada",
            "Toronto, ON",
            "Canada",
        ],
    )
    def test_remote_variants_score_1(self, location):
        scorer = _make_scorer()
        job = _make_job(location=location)
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.remote_points == 1, f"Location '{location}' should score 1"

    def test_onsite_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(location="San Francisco, CA")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.remote_points == 0

    def test_empty_location_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(location="")
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.remote_points == 0


@pytest.mark.unit
class TestSalaryScoring:
    """Salary factor: 0 (below target/missing), 1 (at or above target)."""

    def test_max_above_target_scores_1(self):
        scorer = _make_scorer()
        job = _make_job(salary_max=250_000)
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.salary_points == 1

    def test_min_above_target_scores_1(self):
        scorer = _make_scorer()
        job = _make_job(salary_min=200_000)
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.salary_points == 1

    def test_max_exactly_target_scores_1(self):
        scorer = _make_scorer()
        job = _make_job(salary_max=200_000)
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.salary_points == 1

    def test_below_target_scores_0(self):
        scorer = _make_scorer()
        job = _make_job(salary_max=150_000)
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.salary_points == 0

    def test_no_salary_scores_0(self):
        scorer = _make_scorer()
        job = _make_job()
        _, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.salary_points == 0


@pytest.mark.unit
class TestOverallScoring:
    """Verify the raw-to-final score mapping at each boundary (1-5).

    With default weights (title=2.0, tech=2.0, remote=1.0, salary=1.0):
      raw = title_pts * 2.0/2.0 + tech_pts * 2.0/2.0 + remote_pts * 1.0 + salary_pts * 1.0
          = title_pts + tech_pts + remote_pts + salary_pts

    Mapping: raw >= 5 -> 5, >= 4 -> 4, >= 3 -> 3, >= 2 -> 2, else -> 1
    """

    def test_perfect_match_scores_5(self):
        """title(2) + tech(2) + remote(1) + salary(1) = raw 6 -> score 5."""
        scorer = _make_scorer()
        job = _make_job(
            title="Principal Engineer",
            description="python kubernetes terraform docker aws gcp",
            location="Remote",
            salary_max=250_000,
        )
        score = scorer.score_job(job)
        assert score == 5

    def test_minimal_match_scores_1(self):
        """title(0) + tech(0) + remote(0) + salary(0) = raw 0 -> score 1."""
        scorer = _make_scorer()
        job = _make_job(
            title="Intern",
            description="no match",
            location="office",
        )
        score = scorer.score_job(job)
        assert score == 1

    def test_score_2_boundary(self):
        """title(2) + tech(0) + remote(0) + salary(0) = raw 2 -> score 2."""
        scorer = _make_scorer()
        job = _make_job(
            title="Principal Engineer",
            description="no matching tech",
            location="San Francisco, CA",
        )
        score, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 2
        assert breakdown.tech_points == 0
        assert breakdown.remote_points == 0
        assert breakdown.salary_points == 0
        assert score == 2

    def test_score_3_boundary(self):
        """title(2) + tech(1) + remote(0) + salary(0) = raw 3 -> score 3."""
        scorer = _make_scorer()
        job = _make_job(
            title="Principal Engineer",
            description="python kubernetes",
            location="San Francisco, CA",
        )
        score, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 2
        assert breakdown.tech_points == 1
        assert breakdown.remote_points == 0
        assert breakdown.salary_points == 0
        assert score == 3

    def test_score_4_boundary(self):
        """title(2) + tech(2) + remote(0) + salary(0) = raw 4 -> score 4."""
        scorer = _make_scorer()
        job = _make_job(
            title="Principal Engineer",
            description="python kubernetes terraform docker aws",
            location="San Francisco, CA",
        )
        score, breakdown = scorer.score_job_with_breakdown(job)
        assert breakdown.title_points == 2
        assert breakdown.tech_points == 2
        assert breakdown.remote_points == 0
        assert breakdown.salary_points == 0
        assert score == 4


@pytest.mark.unit
class TestScoreBatch:
    """Verify score_batch() scores all jobs in-place, sets status, and sorts."""

    def test_batch_scores_all_jobs(self):
        scorer = _make_scorer()
        jobs = [
            _make_job(title="Principal Engineer", description="python kubernetes"),
            _make_job(title="Intern", description="no match"),
            _make_job(
                title="DevOps Lead",
                description="python kubernetes terraform docker aws",
                location="Remote",
                salary_max=250_000,
            ),
        ]
        result = scorer.score_batch(jobs)
        for job in result:
            assert job.score is not None

    def test_batch_sets_status_scored(self):
        scorer = _make_scorer()
        jobs = [
            _make_job(title="Principal Engineer"),
            _make_job(title="Developer"),
        ]
        scorer.score_batch(jobs)
        for job in jobs:
            assert job.status == JobStatus.SCORED

    def test_batch_sorts_descending(self):
        scorer = _make_scorer()
        jobs = [
            _make_job(title="Intern", description="nothing"),
            _make_job(
                title="Principal Engineer",
                description="python kubernetes terraform docker aws",
                location="Remote",
                salary_max=250_000,
            ),
            _make_job(title="Senior Software Engineer", description="python kubernetes"),
        ]
        result = scorer.score_batch(jobs)
        scores = [j.score for j in result]
        assert all(s is not None for s in scores)
        assert scores == sorted(scores, reverse=True)  # type: ignore[reportArgumentType]


@pytest.mark.unit
class TestCustomWeights:
    """Verify custom ScoringWeights change the final score."""

    def test_zero_salary_weight_ignores_salary(self):
        """Zeroing salary weight removes salary influence."""
        job = _make_job(
            title="Principal Engineer",
            description="python kubernetes",
            location="Remote",
            salary_max=300_000,
        )
        # With default weights: title(2) + tech(1) + remote(1) + salary(1) = 5 -> score 5
        scorer_default = _make_scorer()
        score_default, bd_default = scorer_default.score_job_with_breakdown(job)

        # With zero salary weight: salary should not contribute
        scorer_zero = _make_scorer(weights=ScoringWeights(salary=0.0))
        score_zero, bd_zero = scorer_zero.score_job_with_breakdown(job)

        # Salary factor still detected (raw points), but final score should differ
        assert bd_default.salary_points == 1
        assert bd_zero.salary_points == 1  # Raw points still computed
        # raw without salary: 2 + 1 + 1 = 4 -> score 4
        # raw with salary:    2 + 1 + 1 + 1 = 5 -> score 5
        assert score_default == 5
        assert score_zero == 4

    def test_doubled_title_weight(self):
        """Doubling title_match weight amplifies title contribution."""
        job = _make_job(
            title="Principal Engineer",
            description="no matching tech",
            location="San Francisco, CA",
        )
        # Default weights: title raw = 2 * 2.0 / 2.0 = 2.0 -> score 2
        scorer_default = _make_scorer()
        score_default = scorer_default.score_job(job)

        # Double title weight: title raw = 2 * 4.0 / 2.0 = 4.0 -> score 4
        scorer_double = _make_scorer(weights=ScoringWeights(title_match=4.0))
        score_double = scorer_double.score_job(job)

        assert score_double > score_default
        assert score_default == 2
        assert score_double == 4


# ---------------------------------------------------------------------------
# UNIT-04: Score Breakdown
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoreBreakdown:
    """Verify ScoreBreakdown data, display, and serialization."""

    def test_breakdown_fields(self):
        bd = ScoreBreakdown(
            title_points=2,
            tech_points=1,
            tech_matched=["python"],
            remote_points=1,
            salary_points=0,
            total=4,
        )
        assert bd.title_points == 2
        assert bd.tech_points == 1
        assert bd.tech_matched == ["python"]
        assert bd.remote_points == 1
        assert bd.salary_points == 0
        assert bd.total == 4

    def test_display_inline_format(self):
        bd = ScoreBreakdown(
            title_points=2,
            tech_points=1,
            remote_points=1,
            salary_points=0,
            total=4,
        )
        expected = "Title +2 | Tech +1 | Remote +1 | Salary +0 = 4"
        assert bd.display_inline() == expected

    def test_display_with_keywords(self):
        bd = ScoreBreakdown(
            title_points=2,
            tech_points=2,
            tech_matched=["python", "kubernetes"],
            remote_points=1,
            salary_points=1,
            total=5,
        )
        result = bd.display_with_keywords()
        assert "(python, kubernetes)" in result
        assert "Tech +2" in result

    def test_to_dict_keys(self):
        bd = ScoreBreakdown(
            title_points=1,
            tech_points=2,
            tech_matched=["python"],
            remote_points=0,
            salary_points=1,
            total=3,
        )
        d = bd.to_dict()
        assert set(d.keys()) == {"title", "tech", "tech_matched", "remote", "salary", "total"}
        assert d["title"] == 1
        assert d["tech"] == 2
        assert d["tech_matched"] == ["python"]
        assert d["remote"] == 0
        assert d["salary"] == 1
        assert d["total"] == 3

    def test_score_job_with_breakdown_returns_tuple(self):
        scorer = _make_scorer()
        job = _make_job(
            title="Principal Engineer",
            description="python kubernetes",
            location="Remote",
        )
        result = scorer.score_job_with_breakdown(job)
        assert isinstance(result, tuple)
        assert len(result) == 2
        score, breakdown = result
        assert isinstance(score, int)
        assert isinstance(breakdown, ScoreBreakdown)
        assert score == breakdown.total

    def test_breakdown_matches_individual_factors(self):
        """Verify breakdown fields agree with what the public API computes."""
        scorer = _make_scorer()
        job = _make_job(
            title="Staff Engineer",
            description="python kubernetes terraform docker aws",
            location="Remote",
            salary_max=250_000,
        )
        score, breakdown = scorer.score_job_with_breakdown(job)
        # Staff Engineer is a target title -> title_points=2
        assert breakdown.title_points == 2
        # 5 tech keywords -> tech_points=2
        assert breakdown.tech_points == 2
        # Remote -> remote_points=1
        assert breakdown.remote_points == 1
        # $250K > $200K target -> salary_points=1
        assert breakdown.salary_points == 1
        # raw = 2+2+1+1 = 6 -> score 5
        assert score == 5
        assert breakdown.total == 5
