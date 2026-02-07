"""Job scoring engine -- rates jobs 1-5 against candidate profile.

Provides both a backward-compatible ``score_job() -> int`` and a new
``score_job_with_breakdown() -> tuple[int, ScoreBreakdown]`` that captures
per-factor points and matched keywords.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import ScoringWeights, get_settings
from models import CandidateProfile, Job, JobStatus


# ---------------------------------------------------------------------------
# Score breakdown
# ---------------------------------------------------------------------------


@dataclass
class ScoreBreakdown:
    """Point-by-point scoring explanation.

    Captures the raw factor points (before weighting) and the final
    mapped 1-5 total.
    """

    title_points: int = 0  # 0-2
    tech_points: int = 0  # 0-2
    tech_matched: list[str] = field(default_factory=list)
    remote_points: int = 0  # 0-1
    salary_points: int = 0  # 0-1
    total: int = 0  # 1-5 (mapped from weighted raw)

    def display_inline(self) -> str:
        """Compact format for job cards.

        Example: ``"Title +2 | Tech +2 | Remote +1 | Salary +0 = 5"``
        """
        return (
            f"Title +{self.title_points} | "
            f"Tech +{self.tech_points} | "
            f"Remote +{self.remote_points} | "
            f"Salary +{self.salary_points} = {self.total}"
        )

    def display_with_keywords(self) -> str:
        """Verbose format for job detail view.

        Example: ``"Title +2 | Tech +2 (Kubernetes, Python) | Remote +1 | Salary +0 = 5"``
        """
        tech_part = f"Tech +{self.tech_points}"
        if self.tech_matched:
            tech_part += f" ({', '.join(self.tech_matched[:5])})"
        return (
            f"Title +{self.title_points} | "
            f"{tech_part} | "
            f"Remote +{self.remote_points} | "
            f"Salary +{self.salary_points} = {self.total}"
        )

    def to_dict(self) -> dict:
        """Serialise for JSON storage in SQLite."""
        return {
            "title": self.title_points,
            "tech": self.tech_points,
            "tech_matched": self.tech_matched,
            "remote": self.remote_points,
            "salary": self.salary_points,
            "total": self.total,
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class JobScorer:
    """Score jobs 1-5 per the CLAUDE.md rubric.

    Factors (max 6 raw points, mapped to 1-5):
      Title match     0-2
      Tech overlap    0-2
      Location        0-1
      Salary          0-1

    Weights are configurable via ``ScoringWeights`` (default values reproduce
    the original hardcoded scoring exactly).
    """

    def __init__(
        self,
        profile: CandidateProfile | None = None,
        weights: ScoringWeights | None = None,
    ) -> None:
        settings = get_settings()
        self.profile = profile or settings.build_candidate_profile()
        self.weights = weights or settings.scoring.weights

    # -- Public API --------------------------------------------------------

    def score_job(self, job: Job) -> int:
        """Return an integer score 1-5 (backward-compatible)."""
        total, _ = self._compute(job)
        return total

    def score_job_with_breakdown(self, job: Job) -> tuple[int, ScoreBreakdown]:
        """Return ``(score, breakdown)`` with per-factor detail."""
        return self._compute(job)

    def score_batch(self, jobs: list[Job]) -> list[Job]:
        """Score all jobs in-place, sort descending."""
        for job in jobs:
            job.score = self.score_job(job)
            job.status = JobStatus.SCORED
        jobs.sort(key=lambda j: (j.score or 0), reverse=True)
        return jobs

    def score_batch_with_breakdown(
        self, jobs: list[Job]
    ) -> list[tuple[Job, ScoreBreakdown]]:
        """Score all jobs and return ``(job, breakdown)`` pairs, sorted descending."""
        results: list[tuple[Job, ScoreBreakdown]] = []
        for job in jobs:
            score, breakdown = self._compute(job)
            job.score = score
            job.status = JobStatus.SCORED
            results.append((job, breakdown))
        results.sort(key=lambda pair: (pair[0].score or 0), reverse=True)
        return results

    # -- Internal computation ----------------------------------------------

    def _compute(self, job: Job) -> tuple[int, ScoreBreakdown]:
        """Compute score and breakdown in a single pass."""
        w = self.weights

        title_pts = self._title_score(job.title)
        tech_pts, tech_matched = self._tech_score_with_keywords(job)
        remote_pts = self._location_score(job.location)
        salary_pts = self._salary_score(job)

        raw = (
            title_pts * w.title_match / 2.0
            + tech_pts * w.tech_overlap / 2.0
            + remote_pts * w.remote
            + salary_pts * w.salary
        )

        if raw >= 5:
            total = 5
        elif raw >= 4:
            total = 4
        elif raw >= 3:
            total = 3
        elif raw >= 2:
            total = 2
        else:
            total = 1

        breakdown = ScoreBreakdown(
            title_points=title_pts,
            tech_points=tech_pts,
            tech_matched=tech_matched,
            remote_points=remote_pts,
            salary_points=salary_pts,
            total=total,
        )
        return total, breakdown

    # -- Scoring factors ---------------------------------------------------

    def _title_score(self, title: str) -> int:
        """0-2: exact target title match = 2, keyword match = 1."""
        lower = title.lower()
        for target in self.profile.target_titles:
            if target.lower() in lower:
                return 2

        keywords = [
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
        ]
        if any(kw in lower for kw in keywords):
            return 1
        return 0

    def _tech_score_with_keywords(self, job: Job) -> tuple[int, list[str]]:
        """0-2 score + list of matched tech keywords."""
        text = f"{job.description} {' '.join(job.tags)}".lower()
        matched = [kw for kw in self.profile.tech_keywords if kw in text]
        count = len(matched)
        if count >= 5:
            return 2, matched
        if count >= 2:
            return 1, matched
        return 0, matched

    def _location_score(self, location: str) -> int:
        """0-1: remote or Ontario = 1."""
        lower = location.lower()
        if any(kw in lower for kw in ("remote", "anywhere", "work from home")):
            return 1
        if any(kw in lower for kw in ("ontario", "toronto", "canada")):
            return 1
        return 0

    def _salary_score(self, job: Job) -> int:
        """0-1: overlaps $200K+ target = 1."""
        target = self.profile.desired_salary_usd
        if job.salary_max is not None and job.salary_max >= target:
            return 1
        if job.salary_min is not None and job.salary_min >= target:
            return 1
        return 0
