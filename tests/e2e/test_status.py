"""E2E tests for status change persistence.

Covers:
- E2E-03: Changing a job's status via the detail page UI persists after reload
- E2E-03: Status change is reflected when filtering on the dashboard
"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.enable_socket
class TestStatusUpdateE2E:
    """Browser tests for job status updates via the detail page."""

    def test_status_change_via_detail_page_persists(self, page, live_server, seeded_db):
        """E2E-03: Changing status via the UI persists after page reload."""
        # Navigate to dashboard
        page.goto(f"{live_server}/")

        # Click the first job row to go to its detail page
        page.locator("#job-table-body tr.job-row").first.click()
        page.wait_for_load_state("networkidle")

        # Verify we're on the detail page
        expect(page.locator("h1")).to_be_visible()

        # Change status to "applied"
        page.select_option('select[name="status"]', "applied")

        # Click Update and wait for the htmx POST response
        with page.expect_response(lambda r: "/status" in r.url):
            page.click('button:has-text("Update")')

        # Verify the status display updated (auto-waits for htmx swap)
        expect(page.locator("#status-display")).to_contain_text("Applied")

        # Reload the page and verify persistence
        page.reload()
        page.wait_for_load_state("networkidle")
        expect(page.locator("#status-display")).to_contain_text("Applied")

    def test_status_change_reflected_on_dashboard(self, page, live_server, seeded_db):
        """E2E-03: Status change on detail page is visible when filtering the dashboard."""
        # Navigate to dashboard and click first job
        page.goto(f"{live_server}/")
        page.locator("#job-table-body tr.job-row").first.click()
        page.wait_for_load_state("networkidle")

        # Change status to "applied"
        page.select_option('select[name="status"]', "applied")
        with page.expect_response(lambda r: "/status" in r.url):
            page.click('button:has-text("Update")')
        expect(page.locator("#status-display")).to_contain_text("Applied")

        # Navigate back to dashboard
        page.goto(f"{live_server}/")
        page.wait_for_load_state("networkidle")

        # Filter by status "applied"
        page.select_option('select[name="status"]', "applied")
        page.click('button:has-text("Filter")')
        page.wait_for_load_state("networkidle")

        # At least 1 row should appear with "applied" status
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() >= 1

        # Verify the row contains "applied" badge text
        row_text = rows.first.inner_text()
        assert "applied" in row_text.lower()
