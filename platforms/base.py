"""Abstract base class for job platform automation."""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from config import DEBUG_SCREENSHOTS_DIR, get_settings

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

    from models import Job, SearchQuery


class BasePlatform(ABC):
    """Interface that every browser-based platform module implements."""

    platform_name: str = ""

    def __init__(self, context: BrowserContext) -> None:
        self.context = context
        self.page: Page = context.pages[0] if context.pages else context.new_page()

    # ── Abstract methods ─────────────────────────────────────────────────

    @abstractmethod
    def login(self) -> bool:
        """Authenticate. Return True on success.

        Raises:
            ValueError: credentials missing.
            RuntimeError: CAPTCHA / verification required (human needed).
        """
        ...

    @abstractmethod
    def is_logged_in(self) -> bool: ...

    @abstractmethod
    def search(self, query: SearchQuery) -> list[Job]: ...

    @abstractmethod
    def get_job_details(self, job: Job) -> Job: ...

    @abstractmethod
    def apply(self, job: Job, resume_path: Path) -> bool:
        """Submit application. MUST pause for human confirmation before final submit."""
        ...

    # ── Utility methods ──────────────────────────────────────────────────

    def human_delay(self, delay_type: str = "nav") -> None:
        """Randomised delay — *nav* (2-5 s) or *form* (1-2 s)."""
        timing = get_settings().timing
        if delay_type == "nav":
            time.sleep(random.uniform(timing.nav_delay_min, timing.nav_delay_max))
        else:
            time.sleep(random.uniform(timing.form_delay_min, timing.form_delay_max))

    def screenshot(self, name: str) -> Path:
        """Save a full-page screenshot to debug_screenshots/."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.platform_name}_{name}_{timestamp}.png"
        filepath = DEBUG_SCREENSHOTS_DIR / filename
        self.page.screenshot(path=str(filepath), full_page=True)
        print(f"  Screenshot saved: {filepath}")
        return filepath

    def wait_for_human(self, message: str) -> str:
        """Block and wait for human input at a checkpoint."""
        print(f"\n{'=' * 60}")
        print(f"  HUMAN INPUT REQUIRED — {self.platform_name.upper()}")
        print(f"{'=' * 60}")
        print(f"  {message}")
        return input("  > ").strip()

    def element_exists(self, selector: str, timeout: int = 5000) -> bool:
        """Non-throwing check for an element on the page."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
