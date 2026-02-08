"""Apply engine configuration models.

Defines the operational modes and settings for the one-click apply engine.
Loaded as a sub-model of ``AppSettings`` via ``config.yaml``.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ApplyMode(StrEnum):
    """Operational mode for the apply engine."""

    FULL_AUTO = "full_auto"
    SEMI_AUTO = "semi_auto"
    EASY_APPLY_ONLY = "easy_apply_only"


class ApplyConfig(BaseModel):
    """Configuration for the apply engine.

    Controls how applications are submitted, what safety checks are enabled,
    and browser behavior during the apply flow.
    """

    default_mode: ApplyMode = Field(
        default=ApplyMode.SEMI_AUTO,
        description="Apply mode: full_auto, semi_auto, or easy_apply_only",
    )
    confirm_before_submit: bool = Field(
        default=True,
        description="Require human confirmation before submitting each application",
    )
    max_concurrent_applies: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum number of concurrent apply sessions",
    )
    screenshot_before_submit: bool = Field(
        default=True,
        description="Capture screenshot of filled form before submission",
    )
    headed_mode: bool = Field(
        default=True,
        description="Run browser in headed mode (visible) during apply",
    )
    ats_form_fill_enabled: bool = Field(
        default=True,
        description="Enable automatic form filling on external ATS pages",
    )
    ats_form_fill_timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Timeout in seconds for ATS form fill operations",
    )
