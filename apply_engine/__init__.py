"""Apply engine -- one-click job application automation.

Provides configuration, event streaming, and deduplication for the apply flow.
"""

from apply_engine.config import ApplyConfig, ApplyMode
from apply_engine.dedup import is_already_applied
from apply_engine.events import ApplyEvent, ApplyEventType

__all__ = [
    "ApplyConfig",
    "ApplyEvent",
    "ApplyEventType",
    "ApplyMode",
    "is_already_applied",
]
