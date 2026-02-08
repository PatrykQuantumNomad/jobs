"""E2E tests for CSV and JSON export downloads.

Covers:
- E2E-05: CSV export downloads a valid file with correct headers and data
- E2E-05: JSON export downloads a valid file with correct structure
- E2E-05: Filtered export contains only the filtered subset of jobs
"""

import csv
import io
import json

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.enable_socket
class TestExportE2E:
    """Browser tests for CSV and JSON export downloads."""

    def test_csv_export_downloads_valid_file(self, page, live_server, seeded_db):
        """E2E-05: CSV export link triggers a download with valid content."""
        page.goto(f"{live_server}/")
        page.wait_for_load_state("networkidle")

        # Verify jobs are loaded before exporting
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()

        # Click CSV export link and capture the download
        with page.expect_download() as download_info:
            page.locator("#export-csv-link").click()

        download = download_info.value
        assert download.suggested_filename.endswith(".csv")
        assert "jobs_export_" in download.suggested_filename

        # Read and validate CSV content
        content = download.path().read_text()
        reader = csv.DictReader(io.StringIO(content))
        field_names = reader.fieldnames
        csv_rows = list(reader)

        assert field_names is not None
        assert "title" in field_names
        assert "company" in field_names
        assert "platform" in field_names
        assert "score" in field_names
        assert "status" in field_names

        # seeded_db creates 10 jobs
        assert len(csv_rows) == 10

        # Verify every row has non-empty title and company
        for row in csv_rows:
            assert row["title"], "CSV row must have a title"
            assert row["company"], "CSV row must have a company"

    def test_json_export_downloads_valid_file(self, page, live_server, seeded_db):
        """E2E-05: JSON export link triggers a download with valid content."""
        page.goto(f"{live_server}/")
        page.wait_for_load_state("networkidle")

        # Verify jobs are loaded before exporting
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()

        # Click JSON export link and capture the download
        with page.expect_download() as download_info:
            page.locator("#export-json-link").click()

        download = download_info.value
        assert download.suggested_filename.endswith(".json")
        assert "jobs_export_" in download.suggested_filename

        # Read and validate JSON content
        content = download.path().read_text()
        data = json.loads(content)

        assert isinstance(data, list)
        assert len(data) == 10

        # Verify structure of first entry
        assert "title" in data[0]
        assert "company" in data[0]
        assert "platform" in data[0]
        assert "score" in data[0]
        assert "status" in data[0]

        # Verify every entry has non-empty title and company
        for entry in data:
            assert entry["title"], "JSON entry must have a title"
            assert entry["company"], "JSON entry must have a company"

    def test_filtered_export_contains_subset(self, page, live_server, seeded_db):
        """E2E-05: Filtered CSV export contains only the filtered subset.

        After filtering by platform 'dice', the CSV export should contain only
        dice jobs (3 from seeded_db: 3 scored dice jobs).
        """
        page.goto(f"{live_server}/")
        page.wait_for_load_state("networkidle")

        # Filter by platform "dice"
        page.select_option('select[name="platform"]', "dice")
        page.click('button:has-text("Filter")')
        page.wait_for_load_state("networkidle")

        # Verify filtered table shows 3 dice jobs
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() == 3

        # The export links include query params from the current page URL.
        # After form submit with platform=dice, the page URL has ?platform=dice
        # and the template renders export links with platform=dice in their href.
        with page.expect_download() as download_info:
            page.locator("#export-csv-link").click()

        download = download_info.value

        # Read and validate filtered CSV
        content = download.path().read_text()
        reader = csv.DictReader(io.StringIO(content))
        csv_rows = list(reader)

        # Only dice jobs (3 scored)
        assert len(csv_rows) == 3

        # All rows should be from the dice platform
        for row in csv_rows:
            assert row["platform"] == "dice", f"Expected dice but got {row['platform']}"
