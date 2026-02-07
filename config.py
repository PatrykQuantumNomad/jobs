"""Environment loading, platform configuration, and search queries."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from models import CandidateProfile, SearchQuery

# Load .env at import time
load_dotenv()


class Config:
    """Global configuration loaded from environment and CLAUDE.md constants."""

    # ── Directories ──────────────────────────────────────────────────────
    PROJECT_ROOT = Path(__file__).parent
    BROWSER_SESSIONS_DIR = PROJECT_ROOT / "browser_sessions"
    DEBUG_SCREENSHOTS_DIR = PROJECT_ROOT / "debug_screenshots"
    JOB_PIPELINE_DIR = PROJECT_ROOT / "job_pipeline"
    JOB_DESCRIPTIONS_DIR = JOB_PIPELINE_DIR / "descriptions"
    RESUMES_DIR = PROJECT_ROOT / "resumes"
    RESUMES_TAILORED_DIR = RESUMES_DIR / "tailored"

    # ── Credentials ──────────────────────────────────────────────────────
    INDEED_EMAIL: str | None = os.getenv("INDEED_EMAIL")
    INDEED_PASSWORD: str | None = os.getenv("INDEED_PASSWORD")
    DICE_EMAIL: str | None = os.getenv("DICE_EMAIL")
    DICE_PASSWORD: str | None = os.getenv("DICE_PASSWORD")

    # ── Resume paths ─────────────────────────────────────────────────────
    RESUME_ATS_PATH = RESUMES_DIR / "Patryk_Golabek_Resume_ATS.pdf"
    RESUME_STANDARD_PATH = RESUMES_DIR / "Patryk_Golabek_Resume.pdf"

    # ── Timing (seconds) ─────────────────────────────────────────────────
    NAV_DELAY_MIN = 2.0
    NAV_DELAY_MAX = 5.0
    FORM_DELAY_MIN = 1.0
    FORM_DELAY_MAX = 2.0
    PAGE_LOAD_TIMEOUT = 30_000  # milliseconds for Playwright

    # ── Salary filter ─────────────────────────────────────────────────────
    MIN_SALARY = 150_000  # USD — used by platform scrapers for filtering

    # ── Search queries ────────────────────────────────────────────────────
    # "remote" is NOT included — each platform applies its own remote filter
    # via URL parameters.  Queries are kept broad to maximise results.
    DEFAULT_SEARCH_QUERIES: list[str] = [
        # Core software engineering
        '"senior software engineer"',
        '"staff software engineer"',
        '"principal engineer"',
        '"software developer"',
        '"full stack engineer"',
        '"backend engineer"',
        '"devops engineer"',
        '"platform engineer"',
        # Architecture
        '"software architect"',
        '"solutions architect"',
        '"cloud architect"',
        # AI/ML
        '"AI engineer"',
        '"machine learning engineer"',
        '"LLM engineer"',
        # Infrastructure/SRE
        '"site reliability engineer"',
        '"cloud engineer"',
        '"infrastructure engineer"',
        '"kubernetes engineer"',
        # Leadership
        '"engineering manager" software',
        '"technical lead"',
        '"engineering director"',
        '"head of engineering"',
    ]

    # ── Candidate profile ────────────────────────────────────────────────
    CANDIDATE = CandidateProfile()

    # ── Class methods ────────────────────────────────────────────────────

    @classmethod
    def validate_platform_credentials(cls, platform: str) -> bool:
        """Return True if credentials exist for *platform*."""
        platform = platform.lower()
        if platform == "indeed":
            return True  # session-based Google auth — no credentials required
        if platform == "dice":
            return bool(cls.DICE_EMAIL and cls.DICE_PASSWORD)
        if platform == "remoteok":
            return True  # no auth required
        return False

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required output directories."""
        for dir_path in (
            cls.BROWSER_SESSIONS_DIR,
            cls.DEBUG_SCREENSHOTS_DIR,
            cls.JOB_PIPELINE_DIR,
            cls.JOB_DESCRIPTIONS_DIR,
            cls.RESUMES_DIR,
            cls.RESUMES_TAILORED_DIR,
        ):
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_search_queries(cls, platform: str = "indeed") -> list[SearchQuery]:
        """Convert default query strings into SearchQuery objects.

        Remote filtering is handled by URL params, so the location field is
        left empty for Indeed/Dice.  RemoteOK is inherently remote.
        """
        location = "" if platform in ("indeed", "dice") else "Remote"
        return [
            SearchQuery(query=q, platform=platform, location=location)
            for q in cls.DEFAULT_SEARCH_QUERIES
        ]


# Create directories on import
Config.ensure_directories()
