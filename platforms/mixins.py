"""Shared utility mixin for browser-based platform adapters.

``BrowserPlatformMixin`` provides the four utility methods previously in
``BasePlatform``: human_delay, screenshot, wait_for_human, element_exists.

Consuming classes must set ``self.page`` (Playwright Page) and
``self.platform_name`` (str) before calling any mixin method.  These are
typically set in the platform's ``init()`` or ``__init__``.

Usage::

    from platforms.mixins import BrowserPlatformMixin
    from platforms.registry import register_platform

    @register_platform("indeed", platform_type="browser")
    class IndeedPlatform(BrowserPlatformMixin):
        platform_name = "indeed"

        def init(self, context):
            self.context = context
            self.page = context.pages[0] if context.pages else context.new_page()
        ...
"""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from core.config import DEBUG_SCREENSHOTS_DIR, get_settings

if TYPE_CHECKING:
    from playwright.sync_api import Page


class BrowserPlatformMixin:
    """Shared browser utilities for platform adapters.

    Expects the consuming class to provide:
    - ``self.page`` -- a Playwright ``Page`` instance
    - ``self.platform_name`` -- platform identifier string (e.g., ``"indeed"``)
    """

    page: Page
    platform_name: str

    def human_delay(self, delay_type: str = "nav") -> None:
        """Randomised delay -- *nav* (2-5 s) or *form* (1-2 s).

        Reads timing configuration from ``get_settings().timing`` to respect
        user-configured delay ranges.
        """
        timing = get_settings().timing
        if delay_type == "nav":
            time.sleep(random.uniform(timing.nav_delay_min, timing.nav_delay_max))
        else:
            time.sleep(random.uniform(timing.form_delay_min, timing.form_delay_max))

    def screenshot(self, name: str) -> Path:
        """Save a full-page screenshot to ``debug_screenshots/``.

        Returns the path to the saved screenshot file.  Filename format:
        ``{platform_name}_{name}_{timestamp}.png``
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.platform_name}_{name}_{timestamp}.png"
        filepath = DEBUG_SCREENSHOTS_DIR / filename
        self.page.screenshot(path=str(filepath), full_page=True)
        print(f"  Screenshot saved: {filepath}")
        return filepath

    def wait_for_human(self, message: str) -> str:
        """Block and wait for human input at a checkpoint.

        Displays a prominent banner with the platform name and the message,
        then waits for user input on stdin.

        Raises ``RuntimeError`` if the platform is running in unattended mode
        (``_unattended`` flag set by the orchestrator in ``--scheduled`` mode).
        """
        if getattr(self, "_unattended", False):
            raise RuntimeError(f"Human input required but running in unattended mode: {message}")
        print(f"\n{'=' * 60}")
        print(f"  HUMAN INPUT REQUIRED — {self.platform_name.upper()}")
        print(f"{'=' * 60}")
        print(f"  {message}")
        return input("  > ").strip()

    def element_exists(self, selector: str, timeout: int = 5000) -> bool:
        """Non-throwing check for an element on the page.

        Returns ``True`` if the element matching *selector* appears within
        *timeout* milliseconds, ``False`` otherwise.
        """
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for_confirmation(self, message: str, timeout: int = 300) -> bool:
        """Wait for user confirmation -- event-based when in dashboard mode.

        In dashboard mode (``_dashboard_mode=True``), blocks on a
        ``threading.Event`` that is set by ``ApplyEngine.confirm()``.

        In CLI mode, falls back to ``wait_for_human()`` which prompts on
        stdin and always returns True on any input.

        Parameters
        ----------
        message:
            Prompt to display (used in CLI fallback).
        timeout:
            Maximum seconds to wait for confirmation.

        Returns
        -------
        True if confirmed within timeout, False if timed out.
        """
        if getattr(self, "_dashboard_mode", False):
            confirmation_event = getattr(self, "_confirmation_event", None)
            if confirmation_event is not None:
                return confirmation_event.wait(timeout=timeout)
            return False

        # CLI fallback -- wait_for_human returns a string, treat any input as confirm
        try:
            self.wait_for_human(message)
            return True
        except RuntimeError:
            # Unattended mode -- cannot confirm
            return False
