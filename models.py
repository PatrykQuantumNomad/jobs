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
    """Candidate information for form filling and scoring."""

    first_name: str = "Patryk"
    last_name: str = "Golabek"
    email: str = "pgolabek@gmail.com"
    phone: str = "416-708-9839"
    location: str = "Springwater, ON, Canada"
    github: str = "https://github.com/TranslucentComputing"
    github_personal: str = "https://github.com/PatrykQuantumNomad"
    website: str = "https://mykubert.com"
    youtube: str = "https://www.youtube.com/@TranslucentComputing"
    years_experience: str = "17+"
    current_title: str = "Co-Founder & CTO"
    current_company: str = "Translucent Computing Inc."
    work_authorization: str = (
        "Authorized to work in Canada. May require sponsorship for US roles."
    )
    willing_to_relocate: str = "No (remote preferred)"
    desired_salary: str = "$200,000+ USD"
    desired_salary_usd: int = 200_000
    start_date: str = "Available immediately / 2 weeks notice"
    education: str = "Bachelor's degree in Computer Science"
    resume_path: str = "resumes/Patryk_Golabek_Resume_ATS.pdf"

    target_titles: list[str] = Field(
        default_factory=lambda: [
            "Senior Software Engineer",
            "Principal Engineer",
            "Staff Engineer",
            "Platform Engineering Lead",
            "DevOps Lead",
            "Engineering Manager",
        ]
    )

    tech_keywords: list[str] = Field(
        default_factory=lambda: [
            "kubernetes",
            "k8s",
            "gke",
            "eks",
            "aks",
            "terraform",
            "terragrunt",
            "helm",
            "devspace",
            "python",
            "fastapi",
            "go",
            "golang",
            "java",
            "typescript",
            "langchain",
            "langgraph",
            "langflow",
            "llm",
            "ai/ml",
            "agentic",
            "prometheus",
            "grafana",
            "observability",
            "airflow",
            "kafka",
            "postgresql",
            "redis",
            "docker",
            "gitops",
            "ci/cd",
            "cloud native",
            "microservices",
            "platform engineering",
        ]
    )
