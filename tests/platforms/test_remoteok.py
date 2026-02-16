"""Integration tests for RemoteOK API response parsing and error handling.

API-01: RemoteOK response parsing -- verifies all Job field mappings,
        metadata skipping, URL prefix, zero salary handling, missing fields.
API-02: RemoteOK error handling -- verifies graceful empty-list return on
        HTTP error, connection error, malformed JSON, empty response,
        metadata-only response.
"""

import httpx
import pytest
import respx

from core.config import get_settings
from core.models import SearchQuery
from platforms.remoteok import RemoteOKPlatform


@pytest.fixture
def remoteok_platform():
    """Provide a configured RemoteOKPlatform instance with test config loaded."""
    get_settings("tests/fixtures/test_config.yaml")
    platform = RemoteOKPlatform()
    platform.init()
    return platform


def _find_job_by_id(jobs, job_id: str):
    """Find a job by its id in a list of jobs."""
    for job in jobs:
        if job.id == str(job_id):
            return job
    return None


@pytest.mark.integration
class TestRemoteOKParsing:
    """API-01: RemoteOK response parsing tests."""

    def test_search_returns_jobs(self, mock_remoteok_api, remoteok_platform):
        """Search returns a list with at least 1 job."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        result = remoteok_platform.search(query)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_parsed_job_has_correct_title(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has title 'Senior Platform Engineer'."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None, "Job with id 12345 not found"
        assert job.title == "Senior Platform Engineer"

    def test_parsed_job_has_correct_company(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has company 'TestCorp'."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.company == "TestCorp"

    def test_parsed_job_has_correct_platform(self, mock_remoteok_api, remoteok_platform):
        """All returned jobs have platform 'remoteok'."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        assert len(jobs) > 0
        for job in jobs:
            assert job.platform == "remoteok"

    def test_parsed_job_has_correct_location(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has location 'Remote'."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.location == "Remote"

    def test_parsed_job_has_salary(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has salary_min=200000 and salary_max=300000."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.salary_min == 200000
        assert job.salary_max == 300000

    def test_parsed_job_has_url(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has the correct RemoteOK URL."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.url == "https://remoteok.com/remote-jobs/12345"

    def test_parsed_job_has_apply_url(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has the correct apply URL."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.apply_url == "https://testcorp.com/careers/12345"

    def test_parsed_job_has_tags(self, mock_remoteok_api, remoteok_platform):
        """Job with id 12345 has the correct tags."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.tags == ["python", "kubernetes", "docker"]

    def test_parsed_job_has_posted_date(self, mock_remoteok_api, remoteok_platform):
        """Job has a valid ISO-format posted_date derived from epoch."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert job.posted_date is not None
        # Epoch 1707350400 -> 2024-02-08T00:00:00+00:00
        assert "2024" in job.posted_date
        # Verify ISO format: contains 'T' separator and timezone offset
        assert "T" in job.posted_date

    def test_parsed_job_has_description(self, mock_remoteok_api, remoteok_platform):
        """Job description contains expected text from the HTML description."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        job = _find_job_by_id(jobs, "12345")
        assert job is not None
        assert "platform engineer" in job.description.lower()

    def test_skips_metadata_at_index_zero(self, mock_remoteok_api, remoteok_platform):
        """Metadata entry at index 0 is not included in search results."""
        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = remoteok_platform.search(query)
        # All returned jobs should have valid titles, none should be metadata
        for job in jobs:
            assert job.title != ""
            assert "legal" not in job.title.lower()

    def test_relative_url_gets_prefix(self, remoteok_platform):
        """A relative URL is prefixed with 'https://remoteok.com'."""
        entry = {
            "id": 99999,
            "position": "Test Engineer",
            "company": "TestCo",
            "url": "/remote-jobs/99999",
            "tags": [],
        }
        job = remoteok_platform._parse(entry)
        assert job is not None
        assert job.url.startswith("https://remoteok.com")
        assert job.url == "https://remoteok.com/remote-jobs/99999"

    def test_zero_salary_becomes_none(self, remoteok_platform):
        """salary_min=0 and salary_max=0 are treated as None."""
        entry = {
            "id": 88888,
            "position": "Zero Salary Job",
            "company": "NoPay Inc",
            "url": "https://remoteok.com/remote-jobs/88888",
            "salary_min": 0,
            "salary_max": 0,
            "tags": [],
        }
        job = remoteok_platform._parse(entry)
        assert job is not None
        assert job.salary_min is None
        assert job.salary_max is None

    def test_missing_position_returns_none(self, remoteok_platform):
        """Entry with empty position returns None from _parse."""
        entry = {
            "id": 77777,
            "position": "",
            "company": "SomeCo",
            "url": "https://remoteok.com/remote-jobs/77777",
            "tags": [],
        }
        result = remoteok_platform._parse(entry)
        assert result is None

    def test_missing_company_returns_none(self, remoteok_platform):
        """Entry with empty company returns None from _parse."""
        entry = {
            "id": 66666,
            "position": "Some Job",
            "company": "",
            "url": "https://remoteok.com/remote-jobs/66666",
            "tags": [],
        }
        result = remoteok_platform._parse(entry)
        assert result is None

    def test_missing_url_returns_none(self, remoteok_platform):
        """Entry with empty url returns None from _parse."""
        entry = {
            "id": 55555,
            "position": "Some Job",
            "company": "SomeCo",
            "url": "",
            "tags": [],
        }
        result = remoteok_platform._parse(entry)
        assert result is None


@pytest.mark.integration
class TestRemoteOKErrorHandling:
    """API-02: RemoteOK error handling tests."""

    def test_http_error_returns_empty_list(self, remoteok_platform):
        """HTTP 500 error returns empty list (not exception)."""
        with respx.mock:
            respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(500))
            query = SearchQuery(query="python", platform="remoteok")
            result = remoteok_platform.search(query)
            assert result == []

    def test_connection_error_returns_empty_list(self, remoteok_platform):
        """Connection error returns empty list (not exception)."""
        with respx.mock:
            respx.get("https://remoteok.com/api").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            query = SearchQuery(query="python", platform="remoteok")
            result = remoteok_platform.search(query)
            assert result == []

    def test_malformed_json_returns_empty_list(self, remoteok_platform):
        """Non-JSON response body returns empty list."""
        with respx.mock:
            respx.get("https://remoteok.com/api").mock(
                return_value=httpx.Response(200, text="not json")
            )
            query = SearchQuery(query="python", platform="remoteok")
            result = remoteok_platform.search(query)
            assert result == []

    def test_empty_response_returns_empty_list(self, remoteok_platform):
        """Empty JSON array returns empty list."""
        with respx.mock:
            respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=[]))
            query = SearchQuery(query="python", platform="remoteok")
            result = remoteok_platform.search(query)
            assert result == []

    def test_metadata_only_response_returns_empty_list(self, remoteok_platform):
        """Response with only metadata (no jobs) returns empty list."""
        with respx.mock:
            respx.get("https://remoteok.com/api").mock(
                return_value=httpx.Response(200, json=[{"legal": "https://remoteok.com/legal"}])
            )
            query = SearchQuery(query="python", platform="remoteok")
            result = remoteok_platform.search(query)
            assert result == []
