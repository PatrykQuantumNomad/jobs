"""Global test fixtures providing isolation between tests.

CRITICAL IMPORT ORDERING:
========================
The ``os.environ`` assignments below MUST execute BEFORE any project imports.
This is because ``webapp/db.py`` runs ``init_db()`` at import time (line 723),
which creates the database.  Setting ``JOBFLOW_TEST_DB=1`` first forces it to
use an in-memory SQLite database instead of ``job_pipeline/jobs.db``.

Similarly, ``ANTHROPIC_API_KEY`` must be set before the ``anthropic`` library
is imported to prevent ``AuthenticationError`` during client instantiation.

The ``# noqa: E402`` comments suppress ruff's "module-level import not at top
of file" warning, which is expected here.
"""

import contextlib
import os

# ── Environment setup (BEFORE any project imports) ────────────────────────
os.environ["JOBFLOW_TEST_DB"] = "1"
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

import pytest  # noqa: E402

import webapp.db as db_module  # noqa: E402
from config import reset_settings  # noqa: E402

# ---------------------------------------------------------------------------
# Autouse fixture 1: Settings isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_settings():
    """Clear the AppSettings singleton before and after each test.

    Prevents config leakage: calling ``get_settings()`` in test A does not
    affect test B.
    """
    reset_settings()
    yield
    reset_settings()


# ---------------------------------------------------------------------------
# Autouse fixture 2: Fresh in-memory database
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_db():
    """Provide a fresh in-memory SQLite database for each test.

    Before each test:  close any existing connection, reset to None,
                       call ``init_db()`` to create schema + run migrations.
    After each test:   close and reset to None again.

    This guarantees zero data leakage between tests.
    """
    # Teardown any leftover connection from a previous test
    if db_module._memory_conn is not None:
        with contextlib.suppress(Exception):
            db_module._memory_conn.close()
    db_module._memory_conn = None

    # Create a fresh database with full schema
    db_module.init_db()

    yield

    # Teardown
    if db_module._memory_conn is not None:
        with contextlib.suppress(Exception):
            db_module._memory_conn.close()
    db_module._memory_conn = None


# ---------------------------------------------------------------------------
# Autouse fixture 3: Block real Anthropic API calls
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _block_anthropic(monkeypatch):
    """Prevent accidental real Anthropic API calls during tests.

    Patches ``Messages.create`` and ``Messages.parse`` to raise
    ``RuntimeError`` with a descriptive message.  Tests that need to
    simulate LLM responses should use the ``mock_anthropic`` fixture
    from ``tests/resume_ai/conftest.py``, which overrides this guard.
    """
    try:
        import anthropic.resources.messages

        def _blocked(*args, **kwargs):
            raise RuntimeError(
                "Test attempted real Anthropic API call to api.anthropic.com "
                "-- use the mock_anthropic fixture instead"
            )

        monkeypatch.setattr(anthropic.resources.messages.Messages, "create", _blocked)
        monkeypatch.setattr(anthropic.resources.messages.Messages, "parse", _blocked)
    except ImportError:
        pass  # anthropic not installed -- nothing to block


# ---------------------------------------------------------------------------
# Opt-in fixture: Seeded database with 10 jobs
# ---------------------------------------------------------------------------


@pytest.fixture
def db_with_jobs(_fresh_db):
    """Seed the database with 10 realistic jobs across all platforms.

    Creates:
    - 3 jobs per platform (indeed, dice, remoteok) with scores cycling 3, 4, 5
    - 1 high-scoring indeed job (score=5, title="Principal Engineer")

    Returns the list of 10 ``Job`` instances.

    Depends explicitly on ``_fresh_db`` to ensure a clean database.
    """
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
            )
            jobs.append(job)

    # 1 high-scoring indeed job
    high_scorer = JobFactory(
        platform="indeed",
        score=5,
        title="Principal Engineer",
        company="TopTech Inc",
    )
    jobs.append(high_scorer)

    # Upsert all into the database
    for job in jobs:
        db_module.upsert_job(job.model_dump(mode="json"))

    return jobs
