"""Integration tests for apply_engine/dedup.py -- is_already_applied.

Tests use the _fresh_db autouse fixture for in-memory SQLite isolation.
"""

import pytest

import webapp.db as db_module
from apply_engine.dedup import is_already_applied


def _make_job_dict(company: str, title: str, **kwargs) -> dict:
    """Build a minimal job dict suitable for upsert_job()."""
    defaults = {
        "id": f"{company.lower()}-{title.lower().replace(' ', '-')}",
        "platform": "indeed",
        "title": title,
        "company": company,
        "url": f"https://example.com/{company.lower()}",
        "location": "Remote",
        "description": f"{title} at {company}",
        "status": "discovered",
    }
    defaults.update(kwargs)
    return defaults


def _compute_dedup_key(company: str, title: str) -> str:
    """Replicate dedup_key logic from webapp/db.py."""
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


@pytest.mark.integration
class TestIsAlreadyApplied:
    """Verify is_already_applied correctly detects application status."""

    def test_no_job_returns_none(self):
        """is_already_applied returns None for nonexistent job."""
        result = is_already_applied("nonexistent::key")
        assert result is None

    def test_discovered_status_returns_none(self):
        """is_already_applied returns None for job with 'discovered' status."""
        db_module.upsert_job(_make_job_dict("TestCo", "Engineer"))
        key = _compute_dedup_key("TestCo", "Engineer")
        result = is_already_applied(key)
        assert result is None

    def test_scored_status_returns_none(self):
        """is_already_applied returns None for job with 'scored' status."""
        db_module.upsert_job(_make_job_dict("TestCo", "Engineer", status="scored"))
        key = _compute_dedup_key("TestCo", "Engineer")
        result = is_already_applied(key)
        assert result is None

    def test_applied_status_returns_dict(self):
        """is_already_applied returns dict for job with 'applied' status."""
        db_module.upsert_job(_make_job_dict("TestCo", "Engineer"))
        key = _compute_dedup_key("TestCo", "Engineer")
        db_module.update_job_status(key, "applied")
        result = is_already_applied(key)
        assert result is not None
        assert result["status"] == "applied"

    def test_phone_screen_status_returns_dict(self):
        """is_already_applied returns dict for job with 'phone_screen' status."""
        db_module.upsert_job(_make_job_dict("TestCo", "Lead"))
        key = _compute_dedup_key("TestCo", "Lead")
        db_module.update_job_status(key, "phone_screen")
        result = is_already_applied(key)
        assert result is not None
        assert result["status"] == "phone_screen"

    def test_offer_status_returns_dict(self):
        """is_already_applied returns dict for job with 'offer' status."""
        db_module.upsert_job(_make_job_dict("TestCo", "Architect"))
        key = _compute_dedup_key("TestCo", "Architect")
        db_module.update_job_status(key, "offer")
        result = is_already_applied(key)
        assert result is not None
        assert result["status"] == "offer"

    def test_saved_status_returns_none(self):
        """is_already_applied returns None for 'saved' status (not applied)."""
        db_module.upsert_job(_make_job_dict("TestCo", "Manager"))
        key = _compute_dedup_key("TestCo", "Manager")
        db_module.update_job_status(key, "saved")
        result = is_already_applied(key)
        assert result is None
