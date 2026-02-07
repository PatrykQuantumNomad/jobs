"""Application settings loaded from config.yaml (non-sensitive) and .env (sensitive/personal).

Replaces the legacy ``Config`` class with a validated, multi-source settings model
powered by pydantic-settings.  Non-sensitive operational parameters (search queries,
scoring weights, platform toggles, timing) live in ``config.yaml``.  Credentials and
personal profile data load from ``.env``.

Usage::

    from config import get_settings, ensure_directories

    settings = get_settings()
    queries  = settings.get_search_queries("indeed")
    profile  = settings.build_candidate_profile()

    ensure_directories()
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.main import YamlConfigSettingsSource

from models import CandidateProfile, SearchQuery

# -- Directory constants -----------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
BROWSER_SESSIONS_DIR = PROJECT_ROOT / "browser_sessions"
DEBUG_SCREENSHOTS_DIR = PROJECT_ROOT / "debug_screenshots"
JOB_PIPELINE_DIR = PROJECT_ROOT / "job_pipeline"
JOB_DESCRIPTIONS_DIR = JOB_PIPELINE_DIR / "descriptions"
RESUMES_DIR = PROJECT_ROOT / "resumes"
RESUMES_TAILORED_DIR = RESUMES_DIR / "tailored"


# -- Sub-models (search) ----------------------------------------------------


class SearchQueryConfig(BaseModel):
    """A single search query template that expands per-platform."""

    title: str
    keywords: list[str] = Field(default_factory=list)
    location: str = ""
    platforms: list[str] = Field(default_factory=list)
    max_pages: int = Field(default=5, ge=1, le=10)


class SearchConfig(BaseModel):
    """Top-level ``search:`` section of config.yaml."""

    queries: list[SearchQueryConfig]
    min_salary: int = 150_000


# -- Sub-models (scoring) ---------------------------------------------------


class ScoringWeights(BaseModel):
    """Relative weights for each scoring dimension."""

    title_match: float = Field(default=2.0, ge=0)
    tech_overlap: float = Field(default=2.0, ge=0)
    remote: float = Field(default=1.0, ge=0)
    salary: float = Field(default=1.0, ge=0)


class ScoringConfig(BaseModel):
    """Top-level ``scoring:`` section of config.yaml."""

    target_titles: list[str]
    tech_keywords: list[str]
    weights: ScoringWeights = Field(default_factory=ScoringWeights)


# -- Sub-models (platforms) --------------------------------------------------


class PlatformToggle(BaseModel):
    """Per-platform on/off toggle."""

    enabled: bool = True


class PlatformsConfig(BaseModel):
    """Top-level ``platforms:`` section of config.yaml."""

    indeed: PlatformToggle = Field(default_factory=PlatformToggle)
    dice: PlatformToggle = Field(default_factory=PlatformToggle)
    remoteok: PlatformToggle = Field(default_factory=PlatformToggle)


# -- Sub-models (timing / schedule) -----------------------------------------


class TimingConfig(BaseModel):
    """Top-level ``timing:`` section of config.yaml."""

    nav_delay_min: float = 2.0
    nav_delay_max: float = 5.0
    form_delay_min: float = 1.0
    form_delay_max: float = 2.0
    page_load_timeout: int = 30_000


class ScheduleConfig(BaseModel):
    """Top-level ``schedule:`` section of config.yaml."""

    enabled: bool = False
    hour: int = Field(default=8, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    weekdays: list[int] | None = Field(
        default=None,
        description="Days of week to run (0=Sun, 1=Mon, ..., 6=Sat). None = daily.",
    )

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for day in v:
                if not (0 <= day <= 6):
                    raise ValueError(f"Weekday must be 0-6, got {day}")
        return v


# -- Root settings model -----------------------------------------------------


class AppSettings(BaseSettings):
    """Root application settings.

    Non-sensitive operational parameters are loaded from ``config.yaml``.
    Credentials and personal profile fields are loaded from ``.env``.

    Instantiation order (highest wins):
      1. Init kwargs
      2. Environment variables
      3. ``.env`` file (DotEnvSettingsSource)
      4. ``config.yaml`` (YamlConfigSettingsSource)
    """

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── YAML sections ──────────────────────────────────────────────────────
    search: SearchConfig
    scoring: ScoringConfig
    platforms: PlatformsConfig = Field(default_factory=PlatformsConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)

    # ── .env credentials ───────────────────────────────────────────────────
    indeed_email: str | None = None
    dice_email: str | None = None
    dice_password: str | None = None

    # ── .env personal profile ──────────────────────────────────────────────
    candidate_first_name: str = ""
    candidate_last_name: str = ""
    candidate_email: str = ""
    candidate_phone: str = ""
    candidate_location: str = ""
    candidate_github: str = ""
    candidate_github_personal: str = ""
    candidate_website: str = ""
    candidate_youtube: str = ""
    candidate_years_experience: str = ""
    candidate_current_title: str = ""
    candidate_current_company: str = ""
    candidate_work_authorization: str = ""
    candidate_willing_to_relocate: str = ""
    candidate_desired_salary: str = ""
    candidate_desired_salary_usd: int = 200_000
    candidate_start_date: str = ""
    candidate_education: str = ""
    candidate_resume_path: str = "resumes/Patryk_Golabek_Resume_ATS.pdf"

    # ── Platform names (class-level constant) ──────────────────────────────
    _PLATFORM_NAMES: ClassVar[list[str]] = ["indeed", "dice", "remoteok"]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
        **kwargs,
    ):
        """Register YAML as an explicit config source.

        Without this override, ``yaml_file`` in ``SettingsConfigDict`` is NOT
        automatically loaded -- ``YamlConfigSettingsSource`` must be returned
        explicitly.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    # ── Public helpers ─────────────────────────────────────────────────────

    def build_candidate_profile(self) -> CandidateProfile:
        """Construct a ``CandidateProfile`` from .env fields and scoring config."""
        return CandidateProfile(
            first_name=self.candidate_first_name,
            last_name=self.candidate_last_name,
            email=self.candidate_email,
            phone=self.candidate_phone,
            location=self.candidate_location,
            github=self.candidate_github,
            github_personal=self.candidate_github_personal,
            website=self.candidate_website,
            youtube=self.candidate_youtube,
            years_experience=self.candidate_years_experience,
            current_title=self.candidate_current_title,
            current_company=self.candidate_current_company,
            work_authorization=self.candidate_work_authorization,
            willing_to_relocate=self.candidate_willing_to_relocate,
            desired_salary=self.candidate_desired_salary,
            desired_salary_usd=self.candidate_desired_salary_usd,
            start_date=self.candidate_start_date,
            education=self.candidate_education,
            resume_path=self.candidate_resume_path,
            target_titles=list(self.scoring.target_titles),
            tech_keywords=list(self.scoring.tech_keywords),
        )

    def get_search_queries(self, platform: str) -> list[SearchQuery]:
        """Convert ``SearchQueryConfig`` list to domain ``SearchQuery`` objects.

        For each query config:
        - Skip if ``qcfg.platforms`` is non-empty and *platform* is not in it.
        - Build query string as ``'"title"' + ' '.join(keywords)``.
        - Create ``SearchQuery`` with the given *platform*.
        """
        result: list[SearchQuery] = []
        for qcfg in self.search.queries:
            if qcfg.platforms and platform not in qcfg.platforms:
                continue
            parts = [f'"{qcfg.title}"']
            if qcfg.keywords:
                parts.extend(qcfg.keywords)
            query_str = " ".join(parts)
            result.append(
                SearchQuery(
                    query=query_str,
                    platform=platform,
                    location=qcfg.location or "",
                    max_pages=qcfg.max_pages,
                )
            )
        return result

    def validate_platform_credentials(self, platform: str) -> bool:
        """Return ``True`` if credentials exist for *platform*."""
        platform = platform.lower()
        if platform == "indeed":
            return True  # session-based Google auth -- no credentials required
        if platform == "dice":
            return bool(self.dice_email and self.dice_password)
        return platform == "remoteok"  # public API -- no auth required

    def enabled_platforms(self) -> list[str]:
        """Return list of platform names where ``enabled=True``."""
        mapping = {
            "indeed": self.platforms.indeed,
            "dice": self.platforms.dice,
            "remoteok": self.platforms.remoteok,
        }
        return [name for name, toggle in mapping.items() if toggle.enabled]


# -- Lazy singleton ----------------------------------------------------------

_settings: AppSettings | None = None


def get_settings(config_path: str = "config.yaml") -> AppSettings:
    """Return the cached ``AppSettings`` singleton.

    On first call, creates the instance (pydantic-settings reads ``yaml_file``
    from ``SettingsConfigDict``).  Subsequent calls return the cached object.

    Parameters
    ----------
    config_path:
        Path to the YAML config file.  Defaults to ``config.yaml`` (project root).
        If a non-default path is passed, the YAML source is updated accordingly.
    """
    global _settings  # noqa: PLW0603
    if _settings is None:
        if config_path != "config.yaml":
            # Override yaml_file before creating the instance
            AppSettings.model_config["yaml_file"] = config_path
        _settings = AppSettings()
    return _settings


def reset_settings() -> None:
    """Clear the cached singleton (useful for testing)."""
    global _settings  # noqa: PLW0603
    _settings = None


# -- Directory creation ------------------------------------------------------


def ensure_directories() -> None:
    """Create all required output directories.

    Uses ``PROJECT_ROOT`` as the base.  This function is NOT called at import
    time -- callers (e.g. ``orchestrator.py``) invoke it explicitly.
    """
    for dir_path in (
        BROWSER_SESSIONS_DIR,
        DEBUG_SCREENSHOTS_DIR,
        JOB_PIPELINE_DIR,
        JOB_DESCRIPTIONS_DIR,
        RESUMES_DIR,
        RESUMES_TAILORED_DIR,
    ):
        dir_path.mkdir(parents=True, exist_ok=True)


# -- Backward compatibility shim (temporary) ---------------------------------
# Other modules (orchestrator, scorer, platforms) still import ``Config``.
# Plans 01-02 and 01-03 will migrate them.  Until then, this shim avoids
# breaking imports.


class Config:
    """Legacy compatibility shim -- delegates to ``AppSettings``.

    .. deprecated::
        Use ``get_settings()`` directly.  This class will be removed after
        all consumers are migrated (Phase 1, Plan 02-03).
    """

    PROJECT_ROOT = PROJECT_ROOT
    BROWSER_SESSIONS_DIR = BROWSER_SESSIONS_DIR
    DEBUG_SCREENSHOTS_DIR = DEBUG_SCREENSHOTS_DIR
    JOB_PIPELINE_DIR = JOB_PIPELINE_DIR
    JOB_DESCRIPTIONS_DIR = JOB_DESCRIPTIONS_DIR
    RESUMES_DIR = RESUMES_DIR
    RESUMES_TAILORED_DIR = RESUMES_TAILORED_DIR
    RESUME_ATS_PATH = RESUMES_DIR / "Patryk_Golabek_Resume_ATS.pdf"
    RESUME_STANDARD_PATH = RESUMES_DIR / "Patryk_Golabek_Resume.pdf"

    # Credentials -- loaded lazily from settings
    @classmethod
    def _settings(cls) -> AppSettings:
        return get_settings()

    @classmethod
    @property
    def INDEED_EMAIL(cls) -> str | None:
        return cls._settings().indeed_email

    @classmethod
    @property
    def DICE_EMAIL(cls) -> str | None:
        return cls._settings().dice_email

    @classmethod
    @property
    def DICE_PASSWORD(cls) -> str | None:
        return cls._settings().dice_password

    @classmethod
    @property
    def CANDIDATE(cls) -> CandidateProfile:
        return cls._settings().build_candidate_profile()

    # Timing
    NAV_DELAY_MIN = 2.0
    NAV_DELAY_MAX = 5.0
    FORM_DELAY_MIN = 1.0
    FORM_DELAY_MAX = 2.0
    PAGE_LOAD_TIMEOUT = 30_000
    MIN_SALARY = 150_000

    @classmethod
    def validate_platform_credentials(cls, platform: str) -> bool:
        """Delegate to ``AppSettings``."""
        return cls._settings().validate_platform_credentials(platform)

    @classmethod
    def ensure_directories(cls) -> None:
        """Delegate to module-level ``ensure_directories()``."""
        ensure_directories()

    @classmethod
    def get_search_queries(cls, platform: str = "indeed") -> list[SearchQuery]:
        """Delegate to ``AppSettings``."""
        return cls._settings().get_search_queries(platform)
