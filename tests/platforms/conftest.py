"""Platform test fixtures -- mocked API responses."""

import httpx
import pytest
import respx


@pytest.fixture
def mock_remoteok_api():
    """Mock the RemoteOK API with a realistic sample response.

    Index 0 is metadata (skipped by parser). Index 1+ are jobs.
    """
    sample_response = [
        {"legal": "https://remoteok.com/legal"},
        {
            "id": 12345,
            "slug": "test-senior-platform-engineer",
            "epoch": "1707350400",
            "date": "2026-02-08T00:00:00+00:00",
            "company": "TestCorp",
            "company_logo": "https://example.com/logo.png",
            "position": "Senior Platform Engineer",
            "tags": ["python", "kubernetes", "docker"],
            "description": "<p>We need a platform engineer with Kubernetes experience.</p>",
            "location": "Remote",
            "salary_min": 200000,
            "salary_max": 300000,
            "apply_url": "https://testcorp.com/careers/12345",
            "url": "https://remoteok.com/remote-jobs/12345",
        },
        {
            "id": 12346,
            "slug": "test-devops-lead",
            "epoch": "1707264000",
            "date": "2026-02-07T00:00:00+00:00",
            "company": "AnotherCo",
            "company_logo": "",
            "position": "DevOps Lead",
            "tags": ["terraform", "aws", "python"],
            "description": "<p>Lead our DevOps team.</p>",
            "location": "Worldwide",
            "salary_min": 180000,
            "salary_max": 250000,
            "apply_url": "https://anotherco.com/apply",
            "url": "https://remoteok.com/remote-jobs/12346",
        },
    ]
    with respx.mock:
        respx.get("https://remoteok.com/api").mock(
            return_value=httpx.Response(200, json=sample_response)
        )
        yield sample_response
