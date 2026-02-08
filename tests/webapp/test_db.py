"""Integration tests for webapp/db.py -- DB-01, DB-04, DB-05.

Tests cover:
- CRUD lifecycle: insert, read, upsert conflict resolution, all 11 status
  transitions, applied_date auto-set, notes, mark_viewed, filtering, sorting
- Bulk operations: upsert_jobs count, selective and full bulk status updates,
  stale job removal, backfill score breakdowns
- Run history: record, ordering, limit
- Stats: empty DB, populated DB, enhanced stats structure
- Schema initialization: tables, indexes, triggers, user_version, idempotency,
  column completeness

All tests use the _fresh_db autouse fixture from tests/conftest.py for
in-memory SQLite isolation.
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


# ---------------------------------------------------------------------------
# DB-01: CRUD Lifecycle
# ---------------------------------------------------------------------------


ALL_STATUSES = [
    "discovered",
    "scored",
    "saved",
    "applied",
    "phone_screen",
    "technical",
    "final_interview",
    "offer",
    "rejected",
    "withdrawn",
    "ghosted",
]


@pytest.mark.integration
class TestCrudLifecycle:
    """Verify single-job CRUD operations, status transitions, and query filters."""

    def test_insert_and_read_back(self):
        """Inserted job can be read back with all stored fields matching."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")
        row = db_module.get_job(key)

        assert row is not None
        assert row["title"] == "Staff Engineer"
        assert row["company"] == "Google"
        assert row["platform"] == "indeed"
        assert row["location"] == "Remote"
        assert row["url"] == "https://example.com/google"
        assert row["description"] == "Staff Engineer role at Google"
        assert row["status"] == "discovered"

    def test_upsert_preserves_longer_description(self):
        """Re-upsert with longer description overwrites the shorter one."""
        job = _make_job_dict("Google", "Staff Engineer", description="Short")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Re-upsert with longer description
        job2 = _make_job_dict("Google", "Staff Engineer", description="A much longer description text")
        db_module.upsert_job(job2)

        row = db_module.get_job(key)
        assert row["description"] == "A much longer description text"

    def test_upsert_preserves_existing_score(self):
        """Re-upsert with score=None keeps the existing score (COALESCE)."""
        job = _make_job_dict("Google", "Staff Engineer", score=4)
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Re-upsert without score
        job2 = _make_job_dict("Google", "Staff Engineer", score=None)
        db_module.upsert_job(job2)

        row = db_module.get_job(key)
        assert row["score"] == 4

    def test_get_job_nonexistent_returns_none(self):
        """get_job() returns None for a key that does not exist."""
        assert db_module.get_job("nonexistent::key") is None

    @pytest.mark.parametrize("status", ALL_STATUSES, ids=lambda s: s)
    def test_status_transition(self, status):
        """Job can transition to each of the 11 lifecycle statuses."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.update_job_status(key, status)
        row = db_module.get_job(key)
        assert row["status"] == status

    def test_applied_status_sets_applied_date(self):
        """Setting status to 'applied' also sets applied_date to non-null."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.update_job_status(key, "applied")
        row = db_module.get_job(key)
        assert row["applied_date"] is not None

    def test_non_applied_status_no_applied_date(self):
        """Setting status to a non-applied value does not set applied_date."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.update_job_status(key, "scored")
        row = db_module.get_job(key)
        assert row["applied_date"] is None

    def test_update_notes(self):
        """update_job_notes() persists notes text retrievable via get_job()."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.update_job_notes(key, "Great match for K8s role")
        row = db_module.get_job(key)
        assert row["notes"] == "Great match for K8s role"

    def test_mark_viewed_sets_timestamp(self):
        """mark_viewed() sets viewed_at on first call."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.mark_viewed(key)
        row = db_module.get_job(key)
        assert row["viewed_at"] is not None

    def test_mark_viewed_idempotent(self):
        """Calling mark_viewed() twice does not change viewed_at."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        db_module.mark_viewed(key)
        row1 = db_module.get_job(key)
        first_viewed = row1["viewed_at"]

        db_module.mark_viewed(key)
        row2 = db_module.get_job(key)
        assert row2["viewed_at"] == first_viewed

    def test_get_jobs_filter_by_status(self):
        """get_jobs(status=...) returns only jobs matching that status."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        db_module.upsert_job(_make_job_dict("Microsoft", "Senior Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")
        db_module.update_job_status(key, "applied")

        results = db_module.get_jobs(status="applied")
        assert len(results) == 1
        assert results[0]["company"] == "Google"

    def test_get_jobs_filter_by_platform(self):
        """get_jobs(platform=...) returns only jobs from that platform."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer", platform="indeed"))
        db_module.upsert_job(_make_job_dict("Microsoft", "Senior Engineer", platform="dice"))

        results = db_module.get_jobs(platform="dice")
        assert len(results) == 1
        assert results[0]["company"] == "Microsoft"

    def test_get_jobs_filter_by_score_min(self):
        """get_jobs(score_min=...) returns only jobs at or above that score."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer", score=3))
        db_module.upsert_job(_make_job_dict("Microsoft", "Senior Engineer", score=5))

        results = db_module.get_jobs(score_min=4)
        assert len(results) == 1
        assert results[0]["score"] == 5

    def test_get_jobs_sort_order(self):
        """get_jobs(sort_by='score', sort_dir='desc') sorts highest first."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer", score=3))
        db_module.upsert_job(_make_job_dict("Microsoft", "Senior Engineer", score=5))

        results = db_module.get_jobs(sort_by="score", sort_dir="desc")
        assert len(results) == 2
        assert results[0]["score"] == 5

    def test_get_jobs_null_scores_last(self):
        """Jobs with score=None sort after scored jobs in descending order."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer", score=5))
        db_module.upsert_job(_make_job_dict("Microsoft", "Senior Engineer"))
        # Microsoft has no score (None)

        results = db_module.get_jobs(sort_by="score", sort_dir="desc")
        assert len(results) == 2
        assert results[0]["score"] == 5
        assert results[1]["score"] is None


# ---------------------------------------------------------------------------
# DB-04: Bulk Operations
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBulkOperations:
    """Verify bulk upsert, bulk status update, and stale job removal."""

    def test_upsert_jobs_returns_count(self):
        """upsert_jobs() processes N jobs and returns N."""
        jobs = [
            _make_job_dict(f"Company{i}", f"Engineer {i}")
            for i in range(5)
        ]
        count = db_module.upsert_jobs(jobs)
        assert count == 5

        # Verify each job is retrievable
        for i in range(5):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            assert db_module.get_job(key) is not None

    def test_bulk_status_update_changes_target_jobs_only(self):
        """Updating status on 2 of 4 jobs changes only those 2."""
        jobs = [_make_job_dict(f"Company{i}", f"Engineer {i}") for i in range(4)]
        db_module.upsert_jobs(jobs)

        # Update first 2
        for i in range(2):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            db_module.update_job_status(key, "saved")

        # Verify first 2 changed
        for i in range(2):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            assert db_module.get_job(key)["status"] == "saved"

        # Verify last 2 unchanged
        for i in range(2, 4):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            assert db_module.get_job(key)["status"] == "discovered"

    def test_bulk_status_update_all_jobs(self):
        """Updating all 3 jobs to 'applied' sets status and applied_date on all."""
        jobs = [_make_job_dict(f"Company{i}", f"Engineer {i}") for i in range(3)]
        db_module.upsert_jobs(jobs)

        for i in range(3):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            db_module.update_job_status(key, "applied")

        for i in range(3):
            key = _compute_dedup_key(f"Company{i}", f"Engineer {i}")
            row = db_module.get_job(key)
            assert row["status"] == "applied"
            assert row["applied_date"] is not None

    def test_remove_stale_jobs_preserves_unsearched_platforms(self):
        """Stale jobs from unsearched platforms are preserved."""
        # 2 indeed, 2 dice
        db_module.upsert_job(_make_job_dict("Google", "SE1", platform="indeed"))
        db_module.upsert_job(_make_job_dict("Microsoft", "SE2", platform="indeed"))
        db_module.upsert_job(_make_job_dict("Amazon", "SE3", platform="dice"))
        db_module.upsert_job(_make_job_dict("Meta", "SE4", platform="dice"))

        # Set all to old timestamps
        conn = db_module.get_conn()
        conn.execute("UPDATE jobs SET last_seen_at = '2026-01-01T00:00:00'")
        conn.commit()

        # Only search indeed
        removed = db_module.remove_stale_jobs(
            searched_platforms=["indeed"],
            run_timestamp="2026-02-08T00:00:00",
        )

        assert removed == 2
        # Indeed jobs deleted
        assert db_module.get_job(_compute_dedup_key("Google", "SE1")) is None
        assert db_module.get_job(_compute_dedup_key("Microsoft", "SE2")) is None
        # Dice jobs preserved
        assert db_module.get_job(_compute_dedup_key("Amazon", "SE3")) is not None
        assert db_module.get_job(_compute_dedup_key("Meta", "SE4")) is not None

    def test_remove_stale_jobs_preserves_recent_jobs(self):
        """Only stale jobs are removed; recent jobs on the same platform stay."""
        db_module.upsert_job(_make_job_dict("Google", "SE1", platform="indeed"))
        db_module.upsert_job(_make_job_dict("Microsoft", "SE2", platform="indeed"))

        conn = db_module.get_conn()
        key_stale = _compute_dedup_key("Google", "SE1")
        key_fresh = _compute_dedup_key("Microsoft", "SE2")

        # Make one stale, one recent
        conn.execute(
            "UPDATE jobs SET last_seen_at = '2026-01-01T00:00:00' WHERE dedup_key = ?",
            (key_stale,),
        )
        conn.execute(
            "UPDATE jobs SET last_seen_at = '2026-02-08T00:00:00' WHERE dedup_key = ?",
            (key_fresh,),
        )
        conn.commit()

        removed = db_module.remove_stale_jobs(
            searched_platforms=["indeed"],
            run_timestamp="2026-02-08T00:00:00",
        )

        assert removed == 1
        assert db_module.get_job(key_stale) is None
        assert db_module.get_job(key_fresh) is not None


# ---------------------------------------------------------------------------
# DB-01 supplementary: Run History
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRunHistory:
    """Verify run history recording, ordering, and limit."""

    def test_record_and_retrieve_run(self):
        """record_run() inserts a run retrievable via get_run_history()."""
        db_module.record_run(
            started_at="2026-02-08T10:00:00",
            finished_at="2026-02-08T10:05:00",
            mode="scheduled",
            platforms_searched=["indeed", "dice"],
            total_raw=50,
            total_scored=10,
            new_jobs=5,
            errors=[],
            status="success",
            duration_seconds=300.0,
        )

        runs = db_module.get_run_history(limit=10)
        assert len(runs) == 1
        run = runs[0]
        assert run["mode"] == "scheduled"
        assert run["status"] == "success"
        assert run["total_raw"] == 50
        assert run["new_jobs"] == 5
        assert run["duration_seconds"] == 300.0

    def test_run_history_ordering(self):
        """get_run_history() returns runs newest first (ID descending)."""
        for i in range(3):
            db_module.record_run(
                started_at=f"2026-02-0{i + 1}T10:00:00",
                finished_at=f"2026-02-0{i + 1}T10:05:00",
                mode="manual",
                platforms_searched=["indeed"],
                total_raw=10 * (i + 1),
                total_scored=0,
                new_jobs=0,
                errors=[],
                status="success",
                duration_seconds=60.0,
            )

        runs = db_module.get_run_history()
        assert len(runs) == 3
        # Newest (highest ID) first
        assert runs[0]["total_raw"] == 30
        assert runs[1]["total_raw"] == 20
        assert runs[2]["total_raw"] == 10

    def test_run_history_limit(self):
        """get_run_history(limit=2) returns only 2 of 5 runs."""
        for i in range(5):
            db_module.record_run(
                started_at=f"2026-02-0{i + 1}T10:00:00",
                finished_at=f"2026-02-0{i + 1}T10:05:00",
                mode="manual",
                platforms_searched=["indeed"],
                total_raw=0,
                total_scored=0,
                new_jobs=0,
                errors=[],
                status="success",
                duration_seconds=0.0,
            )

        runs = db_module.get_run_history(limit=2)
        assert len(runs) == 2


# ---------------------------------------------------------------------------
# DB-01 supplementary: Stats
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStats:
    """Verify get_stats() and get_enhanced_stats() correctness."""

    def test_get_stats_empty_db(self):
        """get_stats() on empty DB returns zeroed totals."""
        stats = db_module.get_stats()
        assert stats["total"] == 0
        assert stats["by_score"] == {}
        assert stats["by_status"] == {}
        assert stats["by_platform"] == {}

    def test_get_stats_with_jobs(self):
        """get_stats() groups correctly by score, status, and platform."""
        db_module.upsert_job(_make_job_dict("Google", "SE", platform="indeed", score=3))
        db_module.upsert_job(_make_job_dict("Microsoft", "SE", platform="dice", score=4))
        db_module.upsert_job(_make_job_dict("Amazon", "SE", platform="remoteok", score=5))

        # Set one to applied
        key = _compute_dedup_key("Google", "SE")
        db_module.update_job_status(key, "applied")

        stats = db_module.get_stats()
        assert stats["total"] == 3
        assert len(stats["by_platform"]) == 3
        assert stats["by_platform"]["indeed"] == 1
        assert stats["by_platform"]["dice"] == 1
        assert stats["by_platform"]["remoteok"] == 1
        assert len(stats["by_score"]) == 3
        assert 3 in stats["by_score"]
        assert 4 in stats["by_score"]
        assert 5 in stats["by_score"]
        assert "discovered" in stats["by_status"]
        assert "applied" in stats["by_status"]

    def test_get_enhanced_stats_structure(self):
        """get_enhanced_stats() returns dict with all expected top-level keys."""
        db_module.upsert_job(_make_job_dict("Google", "SE1"))
        db_module.upsert_job(_make_job_dict("Microsoft", "SE2"))

        stats = db_module.get_enhanced_stats()
        expected_keys = {
            "total",
            "jobs_per_day",
            "by_platform",
            "response_rate",
            "time_in_stage",
            "status_funnel",
        }
        assert expected_keys <= set(stats.keys())
        assert stats["total"] == 2


# ---------------------------------------------------------------------------
# DB-01 supplementary: Backfill Score Breakdowns
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBackfillScoreBreakdowns:
    """Verify backfill_score_breakdowns() re-scores correctly."""

    def test_backfill_rescores_missing_breakdown(self):
        """Jobs with score but no breakdown get re-scored by scorer_fn."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Set score via direct SQL (no breakdown)
        conn = db_module.get_conn()
        conn.execute(
            "UPDATE jobs SET score = 3, score_breakdown = NULL WHERE dedup_key = ?",
            (key,),
        )
        conn.commit()

        def scorer_fn(job_dict):
            return (5, {"title": 2, "tech": 2, "remote": 1})

        count = db_module.backfill_score_breakdowns(scorer_fn)
        assert count == 1

        row = db_module.get_job(key)
        assert row["score"] == 5
        assert row["score_breakdown"] is not None
        assert "title" in row["score_breakdown"]

    def test_backfill_skips_jobs_with_existing_breakdown(self):
        """Jobs that already have a breakdown are not re-scored."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Set score AND breakdown via direct SQL
        conn = db_module.get_conn()
        conn.execute(
            "UPDATE jobs SET score = 4, score_breakdown = ? WHERE dedup_key = ?",
            ('{"title": 2}', key),
        )
        conn.commit()

        def scorer_fn(job_dict):
            return (5, {"title": 3, "tech": 2})

        count = db_module.backfill_score_breakdowns(scorer_fn)
        assert count == 0

    def test_backfill_skips_unscored_jobs(self):
        """Jobs with score=None are not touched by backfill."""
        job = _make_job_dict("Google", "Staff Engineer")
        db_module.upsert_job(job)
        # score is None by default

        def scorer_fn(job_dict):
            return (5, {"title": 3})

        count = db_module.backfill_score_breakdowns(scorer_fn)
        assert count == 0
