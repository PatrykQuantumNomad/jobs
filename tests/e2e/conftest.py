"""E2E test fixtures for Playwright browser tests against a live FastAPI server.

Provides:
- ``live_server``: Session-scoped fixture starting uvicorn on 127.0.0.1:8765
- ``browser_context_args``: Playwright context with viewport and download support
- ``seeded_db``: Function-scoped fixture seeding 10 jobs into the in-memory database

CDN dependency note:
    The dashboard loads htmx and Tailwind CSS from CDN (unpkg.com, cdn.tailwindcss.com).
    If CDN loading becomes flaky in CI, add a guard like:
        page.wait_for_function("typeof htmx !== 'undefined'", timeout=10000)
    before interacting with htmx-powered elements.
"""

import socket
import threading
import time

import pytest
from uvicorn import Config, Server

from core.models import JobStatus
from webapp.app import app


def _port_is_open(host: str, port: int) -> bool:
    """Check if a port is accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def live_server():
    """Start uvicorn serving the FastAPI app in a background daemon thread.

    Uses port 8765 (non-standard) to avoid conflicts with the dev server on 8000.
    Polls for readiness with a 10-second deadline before yielding the base URL.
    """
    host, port = "127.0.0.1", 8765
    config = Config(app=app, host=host, port=port, log_level="warning")
    server = Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server readiness
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if _port_is_open(host, port):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Live server failed to start within 10 seconds")

    yield f"http://{host}:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override pytest-playwright's browser context with viewport and download support."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "accept_downloads": True,
    }


def _make_dedup_key(company: str, title: str) -> str:
    """Replicate the dedup_key logic from webapp.db.upsert_job."""
    normalized = (
        company.lower()
        .strip()
        .replace(" inc.", "")
        .replace(" inc", "")
        .replace(" llc", "")
        .replace(" ltd", "")
        .replace(",", "")
    )
    return f"{normalized}::{title.lower().strip()}"


@pytest.fixture
def seeded_db(_fresh_db):
    """Seed the in-memory database with 10 jobs for E2E tests.

    Creates:
    - 9 jobs: 3 per platform (indeed, dice, remoteok) with scores cycling 3, 4, 5,
      all with status ``scored``
    - 1 additional indeed job with status ``saved`` (score=4, title="Saved Test Job")

    Returns the list of 10 Job instances.
    """
    import webapp.db as db_module
    from tests.conftest_factories import JobFactory

    jobs = []

    # 3 jobs per platform, scores cycling 3, 4, 5
    scores = [3, 4, 5]
    for platform in ("indeed", "dice", "remoteok"):
        for i, score in enumerate(scores):
            job = JobFactory(
                platform=platform,
                score=score,
                title=f"Test {platform.title()} Engineer {i + 1}",
                status=JobStatus.SCORED,
            )
            db_module.upsert_job(job.model_dump(mode="json"))
            jobs.append(job)

    # 1 saved job for status update testing
    saved_job = JobFactory(
        platform="indeed",
        score=4,
        title="Saved Test Job",
        status=JobStatus.SAVED,
    )
    db_module.upsert_job(saved_job.model_dump(mode="json"))
    jobs.append(saved_job)

    # Ensure the saved job has "saved" status and an activity log entry
    saved_key = _make_dedup_key(saved_job.company, saved_job.title)
    db_module.update_job_status(saved_key, "saved")

    return jobs
