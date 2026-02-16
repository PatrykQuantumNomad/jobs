"""RemoteOK platform -- pure HTTP API, no browser needed."""

import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

from core.config import get_settings
from core.models import Job, SearchQuery
from platforms.registry import register_platform


@register_platform(
    "remoteok",
    name="RemoteOK",
    platform_type="api",
)
class RemoteOKPlatform:
    """RemoteOK API client.  No authentication, no browser automation."""

    API_URL = "https://remoteok.com/api"
    platform_name = "remoteok"

    def __init__(self) -> None:
        self.client: httpx.Client | None = None

    def init(self) -> None:
        """Initialize the sync HTTP client."""
        self.client = httpx.Client(
            headers={
                "User-Agent": "JobSearchBot/1.0 (pgolabek@gmail.com)",
            },
            timeout=30.0,
        )

    def __enter__(self) -> RemoteOKPlatform:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    # -- Public API ------------------------------------------------------------

    def search(self, query: SearchQuery) -> list[Job]:
        """Fetch all jobs from the API and filter by tag overlap."""
        settings = get_settings()
        try:
            assert self.client is not None, "Call init() before search()"
            resp = self.client.get(self.API_URL)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"  RemoteOK API error: {exc}")
            return []

        # Index 0 is legal/metadata -- real jobs start at 1
        raw_jobs = data[1:] if len(data) > 1 else []

        filter_terms = self._filter_terms(query.query)
        jobs: list[Job] = []
        for entry in raw_jobs:
            if not self._matches(entry, filter_terms):
                continue
            # Skip jobs whose known salary is below the minimum threshold.
            # Jobs with no salary data are kept (benefit of the doubt).
            sal_max = entry.get("salary_max")
            if sal_max and int(sal_max) < settings.search.min_salary:
                continue
            job = self._parse(entry)
            if job is not None:
                jobs.append(job)

        print(f"  RemoteOK: {len(jobs)} jobs matched for '{query.query}'")
        return jobs

    def get_job_details(self, job: Job) -> Job:
        """API already provides full descriptions -- nothing extra to fetch."""
        return job

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        """RemoteOK has no built-in apply; jobs redirect to external ATS."""
        print(f"  RemoteOK: external application required -- {job.apply_url or job.url}")
        return False

    # -- Private helpers -------------------------------------------------------

    def _filter_terms(self, query: str) -> list[str]:
        """Extract candidate tech keywords that appear in the query string."""
        tokens = re.findall(r"[a-z0-9/+#.-]+", query.lower())
        tech = {kw.lower() for kw in get_settings().scoring.tech_keywords}
        return [t for t in tokens if t in tech]

    def _matches(self, entry: dict, terms: list[str]) -> bool:
        """Return True if any term appears in tags, position, or description."""
        if not terms:
            return True
        # Build a searchable text blob from tags + position + description
        parts = [t.lower() for t in entry.get("tags", [])]
        parts.append(entry.get("position", "").lower())
        parts.append(entry.get("description", "").lower())
        blob = " ".join(parts)
        return any(term in blob for term in terms)

    def _parse(self, entry: dict) -> Job | None:
        """Convert a single RemoteOK API object into a Job."""
        position = entry.get("position", "").strip()
        company = entry.get("company", "").strip()
        url = entry.get("url", "")
        if not (position and company and url):
            return None

        # Ensure url is absolute
        if url.startswith("/"):
            url = f"https://remoteok.com{url}"

        posted_date: str | None = None
        if epoch := entry.get("epoch"):
            posted_date = datetime.fromtimestamp(int(epoch), tz=UTC).isoformat()

        return Job(
            id=str(entry.get("id", "")),
            platform="remoteok",
            title=position,
            company=company,
            location=entry.get("location", "Remote"),
            url=url,
            apply_url=entry.get("apply_url"),
            description=entry.get("description", ""),
            posted_date=posted_date,
            tags=entry.get("tags", []),
            salary_min=entry.get("salary_min") or None,
            salary_max=entry.get("salary_max") or None,
        )
