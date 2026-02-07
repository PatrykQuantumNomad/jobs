"""Resume version tracker -- CRUD operations for resume_versions table.

Persists metadata about tailored resumes and cover letters generated for
specific job postings, enabling version history and deduplication.
"""

from __future__ import annotations

from webapp.db import get_conn


def save_resume_version(
    job_dedup_key: str,
    resume_type: str,
    file_path: str,
    original_resume_path: str,
    model_used: str,
    prompt_hash: str | None = None,
) -> int:
    """Insert a new resume version record.

    Parameters
    ----------
    job_dedup_key:
        The dedup_key of the job this resume/cover letter targets.
    resume_type:
        Either ``'resume'`` or ``'cover_letter'``.
    file_path:
        Path to the generated file (PDF or Markdown).
    original_resume_path:
        Path to the base resume used as input.
    model_used:
        LLM model identifier (e.g. ``'claude-sonnet-4-20250514'``).
    prompt_hash:
        Optional hash of the prompt used for deduplication.

    Returns
    -------
    int
        The ``id`` of the newly inserted row.
    """
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO resume_versions
               (job_dedup_key, resume_type, file_path, original_resume_path,
                model_used, prompt_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job_dedup_key, resume_type, file_path, original_resume_path,
             model_used, prompt_hash),
        )
        return cursor.lastrowid


def get_versions_for_job(job_dedup_key: str) -> list[dict]:
    """Return all resume versions for a given job, newest first.

    Parameters
    ----------
    job_dedup_key:
        The dedup_key of the target job.

    Returns
    -------
    list[dict]
        List of resume version records as dictionaries.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM resume_versions WHERE job_dedup_key = ? ORDER BY created_at DESC",
            (job_dedup_key,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_versions(limit: int = 100) -> list[dict]:
    """Return recent resume versions across all jobs, with job metadata.

    Parameters
    ----------
    limit:
        Maximum number of records to return.

    Returns
    -------
    list[dict]
        List of resume version records enriched with job title and company.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT rv.*, j.title, j.company
               FROM resume_versions rv
               LEFT JOIN jobs j ON rv.job_dedup_key = j.dedup_key
               ORDER BY rv.created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
