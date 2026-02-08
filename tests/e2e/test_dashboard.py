"""E2E tests for dashboard loading and filtering.

Covers:
- E2E-01: Dashboard loads in browser and displays seeded job list
- E2E-02: Filtering by platform, score, and status returns correct subsets
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.enable_socket
class TestDashboardE2E:
    """Browser tests for the main dashboard page."""

    def test_dashboard_loads_with_jobs(self, page, live_server, seeded_db):
        """E2E-01: Dashboard loads in a browser and displays seeded jobs."""
        page.goto(f"{live_server}/")

        # Page title uses em-dash from template
        expect(page).to_have_title("Dashboard \u2014 Job Tracker")

        # Navigation bar is present
        expect(page.locator("nav")).to_be_visible()

        # Stats bar shows "Total Jobs" card
        expect(page.locator("text=Total Jobs")).to_be_visible()

        # Job table has 10 rows (9 scored + 1 saved)
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 10

    def test_filter_by_platform(self, page, live_server, seeded_db):
        """E2E-02: Filtering by platform returns the correct subset of jobs."""
        page.goto(f"{live_server}/")

        # Verify all 10 rows initially
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 10

        # Filter to "indeed" platform
        page.select_option('select[name="platform"]', "indeed")
        page.click('button:has-text("Filter")')
        page.wait_for_load_state("networkidle")

        # 3 scored indeed + 1 saved indeed = 4
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 4

        # All visible rows should contain "indeed" platform badge
        for i in range(rows.count()):
            row_text = rows.nth(i).inner_text()
            assert "indeed" in row_text.lower()

    def test_filter_by_min_score(self, page, live_server, seeded_db):
        """E2E-02: Filtering by minimum score returns jobs scoring at or above threshold."""
        page.goto(f"{live_server}/")

        # Filter to score >= 4
        page.select_option('select[name="score"]', "4")
        page.click('button:has-text("Filter")')
        page.wait_for_load_state("networkidle")

        # Expected: 3 platforms x 2 (score 4 + score 5) + 1 saved (score 4) = 7
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 7

    def test_filter_by_status(self, page, live_server, seeded_db):
        """E2E-02: Filtering by status returns only jobs with that status."""
        page.goto(f"{live_server}/")

        # Filter to "saved" status
        page.select_option('select[name="status"]', "saved")
        page.click('button:has-text("Filter")')
        page.wait_for_load_state("networkidle")

        # Only 1 job has "saved" status
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 1

        # Verify the row contains "saved" status badge
        row_text = rows.first.inner_text()
        assert "saved" in row_text.lower()
