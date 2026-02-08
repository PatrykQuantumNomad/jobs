"""Unit tests for delta detection logic -- UNIT-08.

Tests cover:
- Timestamp assignment on new job insert (first_seen_at, last_seen_at)
- Timestamp preservation on re-upsert (first_seen_at kept, last_seen_at updated)
- Stale job removal (searched vs unsearched platforms, empty platforms, mixed)
- Full delta detection cycle simulating two pipeline runs

All tests use explicit timestamps to avoid flakiness from datetime.now().
The _fresh_db autouse fixture provides in-memory SQLite isolation.
"""

import pytest

import webapp.db as db_module


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_job_dict(
    company: str,
    title: str,
    platform: str = "indeed",
    **kwargs,
) -> dict:
    """Build a minimal job dict suitable for upsert_job()."""
    defaults = {
        "id": f"{company.lower().replace(' ', '-')}-{title.lower().replace(' ', '-')}",
        "platform": platform,
        "title": title,
        "company": company,
        "url": f"https://example.com/{company.lower().replace(' ', '-')}",
        "location": "Remote",
        "description": f"{title} role at {company}",
        "status": "discovered",
    }
    defaults.update(kwargs)
    return defaults


def _compute_dedup_key(company: str, title: str) -> str:
    """Replicate the dedup_key logic from webapp/db.py upsert_job."""
    c = (
        company.lower()
        .strip()
        .replace(" inc.", "")
        .replace(" inc", "")
        .replace(" llc", "")
        .replace(" ltd", "")
        .replace(",", "")
    )
    t = title.lower().strip()
    return f"{c}::{t}"


def _set_last_seen(dedup_key: str, timestamp: str) -> None:
    """Override last_seen_at for a job (test helper)."""
    conn = db_module.get_conn()
    conn.execute(
        "UPDATE jobs SET last_seen_at = ? WHERE dedup_key = ?",
        (timestamp, dedup_key),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# UNIT-08: New job timestamps
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNewJobTimestamps:
    """Verify timestamp assignment on new job insert."""

    def test_new_job_gets_first_seen_at(self):
        """Inserted job has a non-null first_seen_at."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        row = db_module.get_job(key)
        assert row is not None
        assert row["first_seen_at"] is not None

    def test_new_job_gets_last_seen_at(self):
        """Inserted job has a non-null last_seen_at."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        row = db_module.get_job(key)
        assert row is not None
        assert row["last_seen_at"] is not None

    def test_first_seen_preserved_on_update(self):
        """Re-upserting same dedup_key preserves original first_seen_at."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        row1 = db_module.get_job(key)
        original_first_seen = row1["first_seen_at"]

        # Upsert again
        db_module.upsert_job(job)
        row2 = db_module.get_job(key)
        assert row2["first_seen_at"] == original_first_seen

    def test_last_seen_updated_on_re_upsert(self):
        """Re-upserting updates last_seen_at to a newer timestamp."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Set last_seen_at to an old time
        _set_last_seen(key, "2026-01-01T00:00:00")
        row_before = db_module.get_job(key)
        assert row_before["last_seen_at"] == "2026-01-01T00:00:00"

        # Re-upsert (sets last_seen_at = datetime.now())
        db_module.upsert_job(job)
        row_after = db_module.get_job(key)
        assert row_after["last_seen_at"] > "2026-01-01T00:00:00"


# ---------------------------------------------------------------------------
# UNIT-08: Stale job removal
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveStaleJobs:
    """Verify remove_stale_jobs() deletes correctly based on platform and timestamp."""

    def test_stale_job_removed(self):
        """Job with old last_seen_at on searched platform is removed."""
        job = _make_job_dict("Google", "Staff Engineer", platform="indeed")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        _set_last_seen(key, "2026-01-01T00:00:00")

        removed = db_module.remove_stale_jobs(["indeed"], "2026-02-01T00:00:00")
        assert removed == 1
        assert db_module.get_job(key) is None

    def test_fresh_job_not_removed(self):
        """Job with recent last_seen_at is NOT removed."""
        job = _make_job_dict("Google", "Staff Engineer", platform="indeed")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        _set_last_seen(key, "2026-02-01T00:00:00")

        removed = db_module.remove_stale_jobs(["indeed"], "2026-01-15T00:00:00")
        assert removed == 0
        assert db_module.get_job(key) is not None

    def test_unsearched_platform_preserved(self):
        """Job from unsearched platform is NOT removed even if stale."""
        job = _make_job_dict("Google", "Staff Engineer", platform="dice")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        _set_last_seen(key, "2026-01-01T00:00:00")

        # Only indeed was searched -- dice should be untouched
        removed = db_module.remove_stale_jobs(["indeed"], "2026-02-01T00:00:00")
        assert removed == 0
        assert db_module.get_job(key) is not None

    def test_empty_platforms_removes_nothing(self):
        """Empty searched_platforms list removes nothing."""
        job = _make_job_dict("Google", "Staff Engineer", platform="indeed")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        _set_last_seen(key, "2026-01-01T00:00:00")

        removed = db_module.remove_stale_jobs([], "2026-02-01T00:00:00")
        assert removed == 0

    def test_multiple_platforms_searched(self):
        """Stale jobs from multiple searched platforms are all removed."""
        job1 = _make_job_dict("Google", "Staff Engineer", platform="indeed")
        job2 = _make_job_dict("Microsoft", "Senior Engineer", platform="dice")
        db_module.upsert_job(job1)
        db_module.upsert_job(job2)

        key1 = _compute_dedup_key("Google", "Staff Engineer")
        key2 = _compute_dedup_key("Microsoft", "Senior Engineer")
        _set_last_seen(key1, "2026-01-01T00:00:00")
        _set_last_seen(key2, "2026-01-01T00:00:00")

        removed = db_module.remove_stale_jobs(["indeed", "dice"], "2026-02-01T00:00:00")
        assert removed == 2

    def test_mixed_fresh_and_stale(self):
        """Only stale jobs are removed; fresh ones remain."""
        job1 = _make_job_dict("Google", "Staff Engineer", platform="indeed")
        job2 = _make_job_dict("Microsoft", "Senior Engineer", platform="indeed")
        job3 = _make_job_dict("Amazon", "Principal Engineer", platform="indeed")
        db_module.upsert_job(job1)
        db_module.upsert_job(job2)
        db_module.upsert_job(job3)

        key1 = _compute_dedup_key("Google", "Staff Engineer")
        key2 = _compute_dedup_key("Microsoft", "Senior Engineer")
        key3 = _compute_dedup_key("Amazon", "Principal Engineer")

        # Make jobs 1 and 2 stale, keep job 3 fresh
        _set_last_seen(key1, "2026-01-01T00:00:00")
        _set_last_seen(key2, "2026-01-01T00:00:00")
        _set_last_seen(key3, "2026-02-05T00:00:00")

        removed = db_module.remove_stale_jobs(["indeed"], "2026-02-01T00:00:00")
        assert removed == 2
        assert db_module.get_job(key1) is None
        assert db_module.get_job(key2) is None
        assert db_module.get_job(key3) is not None


# ---------------------------------------------------------------------------
# UNIT-08: Full delta detection cycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeltaDetectionFlow:
    """Verify the complete delta detection lifecycle across two pipeline runs."""

    def test_full_delta_cycle(self):
        """Simulate two pipeline runs with one job going stale.

        Run 1: insert 3 jobs, all get timestamps.
        Run 2: re-upsert 2 of 3 jobs. Set 3rd job's last_seen_at to old time.
        remove_stale_jobs removes the 3rd job. 2 remain with preserved first_seen_at.
        """
        # --- Run 1: discover 3 jobs ---
        jobs = [
            _make_job_dict("Google", "Staff Engineer", platform="indeed"),
            _make_job_dict("Microsoft", "Senior Engineer", platform="indeed"),
            _make_job_dict("Amazon", "Principal Engineer", platform="indeed"),
        ]
        for job in jobs:
            db_module.upsert_job(job)

        keys = [
            _compute_dedup_key("Google", "Staff Engineer"),
            _compute_dedup_key("Microsoft", "Senior Engineer"),
            _compute_dedup_key("Amazon", "Principal Engineer"),
        ]

        # All 3 should have timestamps
        for key in keys:
            row = db_module.get_job(key)
            assert row["first_seen_at"] is not None
            assert row["last_seen_at"] is not None

        # Record first_seen_at values
        first_seen_values = {key: db_module.get_job(key)["first_seen_at"] for key in keys}

        # --- Run 2: re-upsert 2 of 3, make 3rd stale ---
        # Set the 3rd job's last_seen_at to an old time (simulates not being in search results)
        _set_last_seen(keys[2], "2026-01-01T00:00:00")

        # Re-upsert the first two (simulates them still being listed)
        db_module.upsert_job(jobs[0])
        db_module.upsert_job(jobs[1])

        # Run delta removal with a timestamp after the stale job but before re-upserted ones
        run_timestamp = "2026-02-01T00:00:00"
        removed = db_module.remove_stale_jobs(["indeed"], run_timestamp)

        # --- Verify ---
        assert removed == 1
        assert db_module.get_job(keys[0]) is not None
        assert db_module.get_job(keys[1]) is not None
        assert db_module.get_job(keys[2]) is None  # stale, removed

        # Remaining jobs have preserved first_seen_at from Run 1
        for key in keys[:2]:
            row = db_module.get_job(key)
            assert row["first_seen_at"] == first_seen_values[key]
            # last_seen_at was updated by re-upsert (newer than the stale timestamp)
            assert row["last_seen_at"] > "2026-01-01T00:00:00"
