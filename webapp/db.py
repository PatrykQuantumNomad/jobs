"""SQLite database layer for job tracker."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Support test mode: in-memory database when JOBFLOW_TEST_DB=1
if os.environ.get("JOBFLOW_TEST_DB") == "1":
    DB_PATH = Path(":memory:")
    _USE_MEMORY = True
else:
    DB_PATH = Path(__file__).parent.parent / "job_pipeline" / "jobs.db"
    _USE_MEMORY = False

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT NOT NULL,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT DEFAULT '',
    url TEXT NOT NULL,
    salary TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    apply_url TEXT,
    description TEXT DEFAULT '',
    posted_date TEXT,
    tags TEXT DEFAULT '[]',
    easy_apply BOOLEAN DEFAULT 0,
    score INTEGER,
    status TEXT DEFAULT 'discovered',
    applied_date TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    dedup_key TEXT UNIQUE,
    PRIMARY KEY (dedup_key)
);
"""

# Migrations keyed by target version.
# Version 1: original schema (CREATE TABLE above).
# Version 2: Phase 3 discovery engine columns.
MIGRATIONS: dict[int, list[str]] = {
    1: [],  # Original schema, applied by CREATE TABLE IF NOT EXISTS
    2: [
        "ALTER TABLE jobs ADD COLUMN first_seen_at TEXT",
        "ALTER TABLE jobs ADD COLUMN last_seen_at TEXT",
        "ALTER TABLE jobs ADD COLUMN viewed_at TEXT",
        "ALTER TABLE jobs ADD COLUMN score_breakdown TEXT",
        "ALTER TABLE jobs ADD COLUMN company_aliases TEXT",
        "ALTER TABLE jobs ADD COLUMN salary_display TEXT",
        "ALTER TABLE jobs ADD COLUMN salary_currency TEXT DEFAULT 'USD'",
        # Backfill existing rows
        "UPDATE jobs SET first_seen_at = created_at WHERE first_seen_at IS NULL",
        "UPDATE jobs SET last_seen_at = updated_at WHERE last_seen_at IS NULL",
    ],
    3: [
        """CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'manual',
            platforms_searched TEXT NOT NULL DEFAULT '[]',
            total_raw INTEGER DEFAULT 0,
            total_scored INTEGER DEFAULT 0,
            new_jobs INTEGER DEFAULT 0,
            errors TEXT DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'success',
            duration_seconds REAL DEFAULT 0.0
        )""",
    ],
}

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

# Singleton connection for in-memory databases (shared across calls)
_memory_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _memory_conn
    if _USE_MEMORY:
        if _memory_conn is None:
            _memory_conn = sqlite3.connect(":memory:")
            _memory_conn.row_factory = sqlite3.Row
            _memory_conn.execute("PRAGMA journal_mode=WAL")
            _memory_conn.execute("PRAGMA busy_timeout = 5000")
        return _memory_conn
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def migrate_db(conn: sqlite3.Connection) -> None:
    """Run pending schema migrations based on PRAGMA user_version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]

    for version in range(current + 1, SCHEMA_VERSION + 1):
        statements = MIGRATIONS.get(version, [])
        for sql in statements:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as exc:
                # Idempotency: ignore "duplicate column name" errors
                if "duplicate column name" in str(exc).lower():
                    continue
                raise
        conn.commit()

    if current < SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        migrate_db(conn)


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


def upsert_job(job: dict) -> None:
    """Insert or update a job. Uses dedup_key for conflict resolution."""
    company = (
        job.get("company", "")
        .lower()
        .strip()
        .replace(" inc.", "")
        .replace(" inc", "")
        .replace(" llc", "")
        .replace(" ltd", "")
        .replace(",", "")
    )
    title = job.get("title", "").lower().strip()
    dedup_key = f"{company}::{title}"

    tags = job.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)

    # JSON-serialize complex fields if needed
    score_breakdown = job.get("score_breakdown")
    if isinstance(score_breakdown, dict):
        score_breakdown = json.dumps(score_breakdown)

    company_aliases = job.get("company_aliases")
    if isinstance(company_aliases, list):
        company_aliases = json.dumps(company_aliases)

    now = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, platform, title, company, location, url,
                salary, salary_min, salary_max, apply_url,
                description, posted_date, tags, easy_apply,
                score, status, applied_date, notes,
                created_at, updated_at, dedup_key,
                first_seen_at, last_seen_at, viewed_at,
                score_breakdown, company_aliases,
                salary_display, salary_currency
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?
            )
            ON CONFLICT(dedup_key) DO UPDATE SET
                description = CASE
                    WHEN LENGTH(excluded.description) > LENGTH(jobs.description)
                    THEN excluded.description ELSE jobs.description END,
                score = COALESCE(excluded.score, jobs.score),
                salary = COALESCE(excluded.salary, jobs.salary),
                salary_min = COALESCE(excluded.salary_min, jobs.salary_min),
                salary_max = COALESCE(excluded.salary_max, jobs.salary_max),
                updated_at = excluded.updated_at,
                last_seen_at = excluded.last_seen_at,
                score_breakdown = COALESCE(excluded.score_breakdown, jobs.score_breakdown),
                company_aliases = COALESCE(excluded.company_aliases, jobs.company_aliases),
                salary_display = COALESCE(excluded.salary_display, jobs.salary_display),
                salary_currency = COALESCE(excluded.salary_currency, jobs.salary_currency)
            """,
            (
                job.get("id", ""),
                job.get("platform", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("url", ""),
                job.get("salary"),
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("apply_url"),
                job.get("description", ""),
                job.get("posted_date"),
                tags,
                job.get("easy_apply", False),
                job.get("score"),
                job.get("status", "discovered"),
                job.get("applied_date"),
                job.get("notes"),
                now,
                now,
                dedup_key,
                now,  # first_seen_at
                now,  # last_seen_at
                job.get("viewed_at"),
                score_breakdown,
                company_aliases,
                job.get("salary_display"),
                job.get("salary_currency", "USD"),
            ),
        )


def upsert_jobs(jobs: list[dict]) -> int:
    """Bulk upsert. Returns count of jobs processed."""
    for job in jobs:
        upsert_job(job)
    return len(jobs)


# ---------------------------------------------------------------------------
# Delta tracking
# ---------------------------------------------------------------------------


def mark_viewed(dedup_key: str) -> None:
    """Set viewed_at timestamp for a job that hasn't been viewed yet."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET viewed_at = ? WHERE dedup_key = ? AND viewed_at IS NULL",
            (now, dedup_key),
        )


def remove_stale_jobs(searched_platforms: list[str], run_timestamp: str) -> int:
    """Remove jobs from searched platforms that were not seen in this run.

    CRITICAL: Only deletes from platforms that were actually searched this run,
    not all platforms. This prevents deleting jobs from platforms that were
    skipped (e.g., due to login failure).

    Returns the count of deleted rows.
    """
    if not searched_platforms:
        return 0

    placeholders = ",".join("?" for _ in searched_platforms)
    with get_conn() as conn:
        cursor = conn.execute(
            f"""
            DELETE FROM jobs
            WHERE platform IN ({placeholders})
              AND (last_seen_at IS NULL OR last_seen_at < ?)
            """,
            (*searched_platforms, run_timestamp),
        )
        return cursor.rowcount


def backfill_score_breakdowns(scorer_fn) -> int:
    """Re-score jobs that have a score but no breakdown.

    Args:
        scorer_fn: Callable that takes a dict of job fields and returns
                   a (score, breakdown_dict) tuple.

    Returns the count of backfilled rows.
    """
    count = 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE score IS NOT NULL AND score_breakdown IS NULL"
        ).fetchall()

        for row in rows:
            job_dict = dict(row)
            try:
                score, breakdown = scorer_fn(job_dict)
                conn.execute(
                    "UPDATE jobs SET score = ?, score_breakdown = ? WHERE dedup_key = ?",
                    (score, json.dumps(breakdown) if isinstance(breakdown, dict) else breakdown, job_dict["dedup_key"]),
                )
                count += 1
            except Exception:
                continue  # Skip jobs that can't be scored

        conn.commit()
    return count


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


def get_jobs(
    score_min: int | None = None,
    platform: str | None = None,
    status: str | None = None,
    sort_by: str = "score",
    sort_dir: str = "desc",
) -> list[dict]:
    """Query jobs with optional filters."""
    where_clauses = []
    params: list = []

    if score_min is not None:
        where_clauses.append("score >= ?")
        params.append(score_min)
    if platform:
        where_clauses.append("platform = ?")
        params.append(platform)
    if status:
        where_clauses.append("status = ?")
        params.append(status)

    where = ""
    if where_clauses:
        where = "WHERE " + " AND ".join(where_clauses)

    allowed_sorts = {"score", "company", "title", "created_at", "salary_min"}
    if sort_by not in allowed_sorts:
        sort_by = "score"
    direction = "DESC" if sort_dir == "desc" else "ASC"

    query = f"SELECT * FROM jobs {where} ORDER BY {sort_by} {direction} NULLS LAST"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_job(dedup_key: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE dedup_key = ?", (dedup_key,)
        ).fetchone()
    return dict(row) if row else None


def update_job_status(dedup_key: str, status: str) -> None:
    now = datetime.now().isoformat()
    applied_date = now if status == "applied" else None
    with get_conn() as conn:
        if applied_date:
            conn.execute(
                "UPDATE jobs SET status = ?, applied_date = ?, updated_at = ? WHERE dedup_key = ?",
                (status, applied_date, now, dedup_key),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE dedup_key = ?",
                (status, now, dedup_key),
            )


def update_job_notes(dedup_key: str, notes: str) -> None:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET notes = ?, updated_at = ? WHERE dedup_key = ?",
            (notes, now, dedup_key),
        )


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_score = {}
        for row in conn.execute(
            "SELECT score, COUNT(*) as cnt FROM jobs GROUP BY score ORDER BY score DESC"
        ):
            by_score[row["score"]] = row["cnt"]
        by_status = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ):
            by_status[row["status"]] = row["cnt"]
        by_platform = {}
        for row in conn.execute(
            "SELECT platform, COUNT(*) as cnt FROM jobs GROUP BY platform"
        ):
            by_platform[row["platform"]] = row["cnt"]
    return {
        "total": total,
        "by_score": by_score,
        "by_status": by_status,
        "by_platform": by_platform,
    }


# ---------------------------------------------------------------------------
# Run history
# ---------------------------------------------------------------------------


def record_run(
    started_at: str,
    finished_at: str,
    mode: str,
    platforms_searched: list[str],
    total_raw: int,
    total_scored: int,
    new_jobs: int,
    errors: list[str],
    status: str,
    duration_seconds: float,
) -> None:
    """Record a pipeline run in the run_history table."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO run_history
               (started_at, finished_at, mode, platforms_searched,
                total_raw, total_scored, new_jobs, errors, status, duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                started_at, finished_at, mode,
                json.dumps(platforms_searched),
                total_raw, total_scored, new_jobs,
                json.dumps(errors), status, duration_seconds,
            ),
        )


def get_run_history(limit: int = 50) -> list[dict]:
    """Return recent pipeline runs, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM run_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


# Initialize on import
init_db()
