"""Job scoring engine — rates jobs 1-5 against candidate profile."""

from __future__ import annotations

from config import Config
from models import CandidateProfile, Job, JobStatus


class JobScorer:
    """Score jobs 1-5 per the CLAUDE.md rubric.

    Factors (max 6 raw points, mapped to 1-5):
      Title match     0-2
      Tech overlap    0-2
      Location        0-1
      Salary          0-1
    """

    def __init__(self, profile: CandidateProfile | None = None) -> None:
        self.profile = profile or Config.CANDIDATE

    # ── Public API ───────────────────────────────────────────────────────

    def score_job(self, job: Job) -> int:
        raw = (
            self._title_score(job.title)
            + self._tech_score(job)
            + self._location_score(job.location)
            + self._salary_score(job)
        )
        if raw >= 5:
            return 5
        if raw >= 4:
            return 4
        if raw >= 3:
            return 3
        if raw >= 2:
            return 2
        return 1

    def score_batch(self, jobs: list[Job]) -> list[Job]:
        """Score all jobs in-place, sort descending."""
        for job in jobs:
            job.score = self.score_job(job)
            job.status = JobStatus.SCORED
        jobs.sort(key=lambda j: (j.score or 0), reverse=True)
        return jobs

    # ── Scoring factors ──────────────────────────────────────────────────

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

    def _tech_score(self, job: Job) -> int:
        """0-2: strong overlap (5+) = 2, some (2-4) = 1."""
        text = f"{job.description} {' '.join(job.tags)}".lower()
        matches = sum(1 for kw in self.profile.tech_keywords if kw in text)
        if matches >= 5:
            return 2
        if matches >= 2:
            return 1
        return 0

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
