"""Pydantic v2 data models for job search automation."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    SCORED = "scored"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class Job(BaseModel):
    """A job listing extracted from a platform."""

    # Identity
    id: str = ""
    platform: Literal["indeed", "dice", "remoteok"]
    title: str
    company: str
    location: str = ""
    url: str

    # Compensation
    salary: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None

    # Details
    apply_url: str | None = None
    description: str = ""
    posted_date: str | None = None
    tags: list[str] = Field(default_factory=list)
    easy_apply: bool = False

    # Salary normalization
    salary_display: str = ""
    salary_currency: str = "USD"

    # Deduplication
    company_aliases: list[str] = Field(default_factory=list)

    # Scoring & tracking
    score: int | None = Field(default=None, ge=1, le=5)
    status: JobStatus = JobStatus.DISCOVERED
    applied_date: str | None = None
    notes: str | None = None

    @field_validator("salary_max")
    @classmethod
    def salary_max_gte_min(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("salary_min") is not None:
            if v < info.data["salary_min"]:
                raise ValueError("salary_max must be >= salary_min")
        return v

    def dedup_key(self) -> str:
        """Normalized key for cross-platform deduplication."""
        company = (
            self.company.lower()
            .strip()
            .replace(" inc.", "")
            .replace(" inc", "")
            .replace(" llc", "")
            .replace(" ltd", "")
            .replace(",", "")
        )
        title = self.title.lower().strip()
        return f"{company}::{title}"


class SearchQuery(BaseModel):
    """A search query configuration."""

    query: str
    platform: Literal["indeed", "dice", "remoteok"] = "indeed"
    location: str = "Remote"
    max_pages: int = Field(default=5, ge=1, le=10)


class CandidateProfile(BaseModel):
    """Candidate information for form filling and scoring.

    All personal fields default to empty strings.  Actual values are populated
    by ``AppSettings.build_candidate_profile()`` from ``.env`` and config.yaml.
    """

    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    github: str = ""
    github_personal: str = ""
    website: str = ""
    youtube: str = ""
    years_experience: str = ""
    current_title: str = ""
    current_company: str = ""
    work_authorization: str = ""
    willing_to_relocate: str = ""
    desired_salary: str = ""
    desired_salary_usd: int = 200_000
    start_date: str = ""
    education: str = ""
    resume_path: str = "resumes/Patryk_Golabek_Resume_ATS.pdf"

    target_titles: list[str] = Field(default_factory=list)
    tech_keywords: list[str] = Field(default_factory=list)
