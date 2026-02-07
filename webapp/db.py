"""SQLite database layer for job tracker."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "job_pipeline" / "jobs.db"

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


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


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

    now = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, platform, title, company, location, url,
                salary, salary_min, salary_max, apply_url,
                description, posted_date, tags, easy_apply,
                score, status, applied_date, notes,
                created_at, updated_at, dedup_key
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?
            )
            ON CONFLICT(dedup_key) DO UPDATE SET
                description = CASE
                    WHEN LENGTH(excluded.description) > LENGTH(jobs.description)
                    THEN excluded.description ELSE jobs.description END,
                score = COALESCE(excluded.score, jobs.score),
                salary = COALESCE(excluded.salary, jobs.salary),
                salary_min = COALESCE(excluded.salary_min, jobs.salary_min),
                salary_max = COALESCE(excluded.salary_max, jobs.salary_max),
                updated_at = ?
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
                now,
            ),
        )


def upsert_jobs(jobs: list[dict]) -> int:
    """Bulk upsert. Returns count of jobs processed."""
    for job in jobs:
        upsert_job(job)
    return len(jobs)


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


# Initialize on import
init_db()
