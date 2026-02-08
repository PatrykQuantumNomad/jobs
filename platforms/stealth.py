"""Playwright stealth configuration and persistent browser context factory."""

import contextlib
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright, ViewportSize, sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()


def get_browser_context(
    platform: str,
    headless: bool = True,
    viewport: ViewportSize | None = None,
) -> tuple[Playwright, BrowserContext]:
    """Launch a persistent browser context with stealth patches.

    Args:
        platform: Platform name used to isolate the session directory.
        headless: Run in headless mode (True) or visible (False).
        viewport: Custom viewport. Defaults to 1280x720.

    Returns:
        (Playwright instance, BrowserContext) — caller must close both.
    """
    if viewport is None:
        viewport = ViewportSize(width=1280, height=720)

    user_data_dir = Path(f"./browser_sessions/{platform.lower()}")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    pw = sync_playwright().start()

    context = pw.chromium.launch_persistent_context(
        str(user_data_dir),
        channel="chrome",
        headless=headless,
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/Toronto",
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
    )

    # Apply stealth to existing pages and all future ones
    for page in context.pages:
        _stealth.apply_stealth_sync(page)
    context.on("page", lambda page: _stealth.apply_stealth_sync(page))

    return pw, context


def close_browser(pw: Playwright, context: BrowserContext) -> None:
    """Gracefully close browser context and Playwright instance."""
    with contextlib.suppress(Exception):
        context.close()
    with contextlib.suppress(Exception):
        pw.stop()
