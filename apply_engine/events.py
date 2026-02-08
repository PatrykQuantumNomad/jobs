"""Apply engine event models for SSE streaming.

Events are emitted by the apply engine during application submission and
consumed by the web dashboard via Server-Sent Events for real-time progress.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ApplyEventType(str, Enum):
    """Types of events emitted during an apply flow."""

    PROGRESS = "progress"
    AWAITING_CONFIRM = "awaiting_confirm"
    CONFIRMED = "confirmed"
    CAPTCHA = "captcha"
    ERROR = "error"
    DONE = "done"
    PING = "ping"


class ApplyEvent(BaseModel):
    """A single event emitted during an apply flow.

    Serialized to JSON and sent as an SSE message to the dashboard.
    """

    type: ApplyEventType = Field(description="Event type discriminator")
    message: str = Field(default="", description="Human-readable status message")
    html: str = Field(default="", description="Optional HTML fragment for dashboard rendering")
    screenshot_path: str | None = Field(
        default=None, description="Path to screenshot if captured"
    )
    fields_filled: dict[str, str] = Field(
        default_factory=dict,
        description="Map of form field names to filled values",
    )
    job_dedup_key: str = Field(
        default="", description="Dedup key of the job being applied to"
    )


def make_progress_event(
    message: str,
    *,
    html: str = "",
    job_dedup_key: str = "",
) -> ApplyEvent:
    """Create a PROGRESS event with the given message."""
    return ApplyEvent(
        type=ApplyEventType.PROGRESS,
        message=message,
        html=html,
        job_dedup_key=job_dedup_key,
    )


def make_done_event(
    message: str = "Application submitted successfully",
    *,
    job_dedup_key: str = "",
) -> ApplyEvent:
    """Create a DONE event indicating successful submission."""
    return ApplyEvent(
        type=ApplyEventType.DONE,
        message=message,
        job_dedup_key=job_dedup_key,
    )
