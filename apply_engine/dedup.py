"""Apply deduplication -- prevent re-applying to jobs already applied to.

Queries the jobs table to check if a job has already been applied to,
avoiding duplicate applications across sessions and restarts.
"""

from __future__ import annotations


def is_already_applied(dedup_key: str) -> dict | None:
    """Check if a job has already been applied to.

    Queries the jobs table for the given dedup_key and returns the job row
    as a dict if its status indicates an application was submitted.
    Returns None if the job hasn't been applied to (or doesn't exist).

    Applied statuses: applied, phone_screen, technical, final_interview, offer.
    """
    from webapp.db import get_job

    job = get_job(dedup_key)
    if job is None:
        return None

    applied_statuses = {
        "applied",
        "phone_screen",
        "technical",
        "final_interview",
        "offer",
    }
    if job.get("status") in applied_statuses:
        return job
    return None
