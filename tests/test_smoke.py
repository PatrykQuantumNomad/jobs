"""Smoke tests for test infrastructure.

These tests verify that the fixtures and isolation guards from conftest.py
work correctly. They should be the first tests to pass in the suite.
"""

import os

import pytest

from core.models import Job


class TestFactorySmoke:
    """Verify JobFactory produces valid Pydantic models."""

    def test_factory_produces_valid_job(self):
        from tests.conftest_factories import JobFactory

        job = JobFactory()
        assert isinstance(job, Job)
        assert job.platform in ("indeed", "dice", "remoteok")
        assert 1 <= job.score <= 5
        assert isinstance(job.description, str)
        assert len(job.description) > 0

    def test_factory_salary_constraint(self):
        from tests.conftest_factories import JobFactory

        for _ in range(20):  # Run multiple times to catch random failures
            job = JobFactory()
            if job.salary_min is not None and job.salary_max is not None:
                assert job.salary_max >= job.salary_min

    def test_factory_override(self):
        from tests.conftest_factories import JobFactory

        job = JobFactory(
            platform="dice",
            title="Staff Engineer",
            score=5,
            company="TestCorp",
        )
        assert job.platform == "dice"
        assert job.title == "Staff Engineer"
        assert job.score == 5
        assert job.company == "TestCorp"


class TestSettingsIsolation:
    """Verify settings singleton resets between tests."""

    def test_settings_clean_a(self):
        import core.config as config_mod

        # _settings should be None at the start of each test
        # (autouse _reset_settings clears it)
        assert config_mod._settings is None

    def test_settings_clean_b(self):
        import core.config as config_mod

        # Even after test_a ran, test_b should start clean
        assert config_mod._settings is None


class TestDatabaseIsolation:
    """Verify each test gets a fresh in-memory database."""

    def test_db_is_empty(self):
        import webapp.db as db_module

        conn = db_module.get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        assert count == 0, "Fresh DB should have no jobs"

    def test_db_insert_does_not_leak(self):
        import webapp.db as db_module

        # Insert a job
        db_module.upsert_job(
            {
                "id": "test-leak",
                "platform": "indeed",
                "title": "Leak Test",
                "company": "LeakCo",
                "url": "https://example.com/leak",
                "status": "scored",
            }
        )
        conn = db_module.get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        assert cursor.fetchone()[0] == 1

    def test_db_previous_insert_not_visible(self):
        # The job inserted in test_db_insert_does_not_leak should NOT be here
        import webapp.db as db_module

        conn = db_module.get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        assert count == 0, "Previous test's data should not leak"


class TestDbWithJobsFixture:
    """Verify the db_with_jobs fixture works."""

    def test_seeded_db(self, db_with_jobs):
        import webapp.db as db_module

        conn = db_module.get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        assert count == len(db_with_jobs)
        assert count == 10  # 3 platforms * 3 + 1 high-scoring


class TestCLIGuard:
    """Verify Claude CLI subprocess calls are blocked."""

    @pytest.mark.asyncio
    async def test_cli_blocked(self):
        import asyncio

        with pytest.raises(RuntimeError, match="real Claude CLI subprocess call"):
            await asyncio.create_subprocess_exec("claude", "-p", "test")


class TestNoAnthropicSDKInProduction:
    """Verify no production module imports anthropic at module level."""

    def test_no_anthropic_sdk_in_production(self):
        import importlib
        import sys

        mods_before = set(sys.modules.keys())
        importlib.import_module("resume_ai.tailor")
        importlib.import_module("resume_ai.cover_letter")
        new_mods = set(sys.modules.keys()) - mods_before
        assert not any("anthropic" in m for m in new_mods)


class TestNetworkBlocked:
    """Verify real network access is blocked by pytest-socket."""

    def test_socket_blocked(self):
        from pytest_socket import SocketBlockedError

        with pytest.raises(SocketBlockedError):
            import socket

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("1.1.1.1", 80))


class TestEnvironment:
    """Verify test environment is correctly configured."""

    def test_jobflow_test_db_set(self):
        assert os.environ.get("JOBFLOW_TEST_DB") == "1"
