"""Global test fixtures providing isolation between tests.

CRITICAL IMPORT ORDERING:
========================
The ``os.environ`` assignments below MUST execute BEFORE any project imports.
This is because ``webapp/db.py`` runs ``init_db()`` at import time (line 723),
which creates the database.  Setting ``JOBFLOW_TEST_DB=1`` first forces it to
use an in-memory SQLite database instead of ``job_pipeline/jobs.db``.

The ``# noqa: E402`` comments suppress ruff's "module-level import not at top
of file" warning, which is expected here.
"""

import contextlib
import os

# ── Environment setup (BEFORE any project imports) ────────────────────────
os.environ["JOBFLOW_TEST_DB"] = "1"


import pytest  # noqa: E402

import webapp.db as db_module  # noqa: E402
from core.config import reset_settings  # noqa: E402

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
# Autouse fixture 3: Block real Claude CLI subprocess calls
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _block_cli(monkeypatch):
    """Prevent accidental real Claude CLI subprocess calls during tests.

    Patches ``asyncio.create_subprocess_exec`` to raise ``RuntimeError``.
    Tests that need to simulate CLI responses should use the ``mock_claude_cli``
    fixture from ``tests/resume_ai/conftest.py`` or ``tests/claude_cli/conftest.py``.
    """

    async def _blocked(*args, **kwargs):
        raise RuntimeError(
            "Test attempted real Claude CLI subprocess call "
            "-- use the mock_claude_cli fixture instead"
        )

    monkeypatch.setattr("asyncio.create_subprocess_exec", _blocked)


# ---------------------------------------------------------------------------
# Opt-in fixture: Mock Claude CLI subprocess
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_claude_cli():
    """Provide a mock Claude CLI subprocess that returns controlled responses.

    Overrides the autouse ``_block_cli`` guard for tests that need to simulate
    CLI responses.

    The fixture returns a controller object with two methods:

    - ``set_response(model_instance)`` -- configure the mock to return a
      successful CLI envelope containing the given Pydantic model instance.
    - ``set_error(returncode, stderr_text)`` -- configure the mock to simulate
      a CLI failure with the given exit code and stderr output.

    Usage in tests::

        async def test_tailor(mock_claude_cli):
            mock_claude_cli.set_response(make_some_model())
            result = await tailor_resume(...)
            assert result == ...
    """
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = b"{}"
    mock_proc.stderr = b""

    async def _communicate():
        return mock_proc.stdout, mock_proc.stderr

    mock_proc.communicate = _communicate
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    mock_exec = AsyncMock(return_value=mock_proc)

    class _Controller:
        """Helper to configure mock CLI subprocess responses."""

        def set_response(self, model_instance):
            """Set a successful response from the CLI.

            Serializes the model instance into a CLI envelope with
            ``structured_output`` set to the model's JSON dict.
            """
            envelope = {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "",
                "structured_output": model_instance.model_dump(mode="json"),
                "duration_ms": 500,
                "num_turns": 2,
            }
            mock_proc.stdout = json.dumps(envelope).encode()
            mock_proc.stderr = b""
            mock_proc.returncode = 0

        def set_error(self, returncode, stderr_text="CLI error"):
            """Set an error response from the CLI.

            Configures the mock process to return the given exit code and
            stderr output, simulating a CLI failure.
            """
            mock_proc.stdout = b""
            mock_proc.stderr = stderr_text.encode()
            mock_proc.returncode = returncode

    controller = _Controller()

    with (
        patch(
            "claude_cli.client.asyncio.create_subprocess_exec",
            new=mock_exec,
        ),
        patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
    ):
        yield controller


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
