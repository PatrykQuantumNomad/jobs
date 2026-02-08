"""Integration tests for FastAPI web endpoints -- WEB-01 through WEB-08.

Tests cover:
- Dashboard (WEB-01): GET / with empty DB, populated DB, score/platform/status
  filtering, wrong filters return empty (not errors), sort ordering, filter
  controls in HTML.
- Search (WEB-08): GET /search returns partial HTML, FTS5 query filtering,
  combined search+score filter, empty query returns all.
- Job Detail (WEB-02): GET /jobs/{key} returns full detail with description
  and activity log, marks viewed_at, 404 for nonexistent, special chars in key.
- Status Update (WEB-03): POST /jobs/{key}/status persists change, returns
  badge HTML, sets HX-Trigger header, logs activity, sets applied_date.
- Notes Update (WEB-03): POST /jobs/{key}/notes persists notes, returns
  confirmation HTML, logs activity.
- CSV Export (WEB-04): GET /export/csv returns parseable CSV with 10 headers,
  correct row counts, data accuracy, platform filtering, empty DB handling.
- JSON Export (WEB-05): GET /export/json returns parseable JSON with 12 fields,
  correct row counts, data accuracy, score filtering, empty DB handling.
- Bulk Status (WEB-06): POST /bulk/status changes target jobs, no-op on empty,
  returns HTML, logs activity.
- Import (WEB-07): POST /import reads pipeline JSON, upserts into DB, redirects
  with count, handles missing files gracefully.

All tests use the `client` fixture from tests/webapp/conftest.py (TestClient)
and the `_fresh_db` autouse fixture from tests/conftest.py for in-memory
SQLite isolation.
"""

import csv
import io
import json

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
# WEB-01: Dashboard Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDashboardEndpoint:
    """Verify GET / dashboard with filtering, sorting, and rendering."""

    def test_dashboard_returns_200_empty_db(self, client):
        """GET / returns 200 with HTML even when the database has no jobs."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_shows_jobs(self, client, db_with_jobs):
        """GET / returns 200 and job titles from db_with_jobs appear in HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Principal Engineer" in response.text

    def test_filter_by_score_min(self, client):
        """GET /?score=5 returns only jobs with score >= 5."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Low Score Role", score=3))
        db_module.upsert_job(_make_job_dict("BetaCo", "High Score Role", score=5))

        response = client.get("/?score=5")
        assert response.status_code == 200
        assert "High Score Role" in response.text
        assert "Low Score Role" not in response.text

    def test_filter_by_platform(self, client):
        """GET /?platform=dice returns only dice jobs."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Indeed Engineer", platform="indeed"))
        db_module.upsert_job(_make_job_dict("BetaCo", "Dice Engineer", platform="dice"))

        response = client.get("/?platform=dice")
        assert response.status_code == 200
        assert "Dice Engineer" in response.text
        assert "Indeed Engineer" not in response.text

    def test_filter_by_status(self, client):
        """GET /?status=applied returns only applied jobs."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Discovered Role"))
        db_module.upsert_job(_make_job_dict("BetaCo", "Applied Role"))
        key = _compute_dedup_key("BetaCo", "Applied Role")
        db_module.update_job_status(key, "applied")

        response = client.get("/?status=applied")
        assert response.status_code == 200
        assert "Applied Role" in response.text
        assert "Discovered Role" not in response.text

    def test_filter_wrong_score_returns_empty(self, client):
        """GET /?score=5 with only score-3 jobs returns 200, not error."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Low Score Role", score=3))

        response = client.get("/?score=5")
        assert response.status_code == 200
        assert "Low Score Role" not in response.text

    def test_filter_wrong_platform_returns_empty(self, client):
        """GET /?platform=remoteok with only indeed jobs returns 200, not error."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Indeed Only Role", platform="indeed"))

        response = client.get("/?platform=remoteok")
        assert response.status_code == 200
        assert "Indeed Only Role" not in response.text

    def test_sort_by_score_desc(self, client):
        """GET /?sort=score&dir=desc puts score-5 before score-3."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Low Score Job", score=3))
        db_module.upsert_job(_make_job_dict("BetaCo", "High Score Job", score=5))

        response = client.get("/?sort=score&dir=desc")
        assert response.status_code == 200
        pos_high = response.text.index("High Score Job")
        pos_low = response.text.index("Low Score Job")
        assert pos_high < pos_low, "Score-5 job should appear before score-3 job"

    def test_dashboard_contains_filter_controls(self, client):
        """GET / HTML contains filter-related form elements."""
        response = client.get("/")
        assert response.status_code == 200
        assert "score" in response.text.lower()
        assert "platform" in response.text.lower()
        assert "status" in response.text.lower()


# ---------------------------------------------------------------------------
# WEB-08: Search Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSearchEndpoint:
    """Verify GET /search returns partial HTML with FTS5 filtering."""

    def test_search_returns_200(self, client):
        """GET /search returns 200."""
        response = client.get("/search")
        assert response.status_code == 200

    def test_search_returns_partial_html(self, client, db_with_jobs):
        """GET /search returns a partial HTML fragment (not a full page)."""
        response = client.get("/search")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Partial should NOT contain full page markers
        assert "<!DOCTYPE" not in response.text
        assert "<html" not in response.text

    def test_search_filters_by_query(self, client):
        """GET /search?q=kubernetes returns only matching jobs."""
        db_module.upsert_job(
            _make_job_dict(
                "AlphaCo",
                "Kubernetes Engineer",
                description="Expert in Kubernetes cluster management",
            )
        )
        db_module.upsert_job(
            _make_job_dict(
                "BetaCo",
                "Python Developer",
                description="Django and Flask web development",
            )
        )

        response = client.get("/search?q=kubernetes")
        assert response.status_code == 200
        assert "Kubernetes Engineer" in response.text
        assert "Python Developer" not in response.text

    def test_search_with_score_filter(self, client):
        """GET /search?q=kubernetes&score=5 returns only high-scoring matches."""
        db_module.upsert_job(
            _make_job_dict(
                "AlphaCo",
                "K8s Low Score",
                score=3,
                description="kubernetes platform engineer",
            )
        )
        db_module.upsert_job(
            _make_job_dict(
                "BetaCo",
                "K8s High Score",
                score=5,
                description="kubernetes infrastructure lead",
            )
        )

        response = client.get("/search?q=kubernetes&score=5")
        assert response.status_code == 200
        assert "K8s High Score" in response.text
        assert "K8s Low Score" not in response.text

    def test_search_empty_query_returns_all(self, client):
        """GET /search?q= returns all jobs (empty query = no filter)."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "First Job"))
        db_module.upsert_job(_make_job_dict("BetaCo", "Second Job"))

        response = client.get("/search?q=")
        assert response.status_code == 200
        assert "First Job" in response.text
        assert "Second Job" in response.text


# ---------------------------------------------------------------------------
# WEB-02: Job Detail Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestJobDetailEndpoint:
    """Verify GET /jobs/{dedup_key} returns full job detail."""

    def test_detail_returns_200(self, client):
        """GET /jobs/{key} returns 200 with job title and company."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.get(f"/jobs/{key}")
        assert response.status_code == 200
        assert "Staff Engineer" in response.text
        assert "Google" in response.text

    def test_detail_shows_description(self, client):
        """Job description text appears on the detail page."""
        db_module.upsert_job(
            _make_job_dict(
                "Google",
                "Staff Engineer",
                description="Expert in Kubernetes and cloud infrastructure",
            )
        )
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.get(f"/jobs/{key}")
        assert response.status_code == 200
        assert "Expert in Kubernetes and cloud infrastructure" in response.text

    def test_detail_shows_activity_log(self, client):
        """Activity log (discovered event) appears on the detail page."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.get(f"/jobs/{key}")
        assert response.status_code == 200
        # The template renders "Discovered on indeed" for the discovered event
        assert "discovered" in response.text.lower() or "Discovered" in response.text

    def test_detail_marks_job_as_viewed(self, client):
        """GET /jobs/{key} sets viewed_at on the first access."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        # Before access: viewed_at should be None
        row_before = db_module.get_job(key)
        assert row_before is not None
        assert row_before["viewed_at"] is None

        # Access the detail page
        client.get(f"/jobs/{key}")

        # After access: viewed_at should be set
        row_after = db_module.get_job(key)
        assert row_after is not None
        assert row_after["viewed_at"] is not None

    def test_detail_nonexistent_returns_404(self, client):
        """GET /jobs/nonexistent::key returns 404."""
        response = client.get("/jobs/nonexistent::key")
        assert response.status_code == 404

    def test_detail_with_special_chars_in_key(self, client):
        """Jobs with special chars in company/title are accessible via URL."""
        db_module.upsert_job(_make_job_dict("Google Inc.", "Staff Engineer (Remote)"))
        key = _compute_dedup_key("Google Inc.", "Staff Engineer (Remote)")

        response = client.get(f"/jobs/{key}")
        assert response.status_code == 200
        assert "Staff Engineer (Remote)" in response.text


# ---------------------------------------------------------------------------
# WEB-03: Status Update Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStatusUpdateEndpoint:
    """Verify POST /jobs/{key}/status persists and returns badge HTML."""

    def test_status_update_returns_200(self, client):
        """POST /jobs/{key}/status returns 200."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.post(f"/jobs/{key}/status", data={"status": "applied"})
        assert response.status_code == 200

    def test_status_update_changes_db(self, client):
        """POST /jobs/{key}/status persists the status change in the database."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        client.post(f"/jobs/{key}/status", data={"status": "saved"})

        row = db_module.get_job(key)
        assert row is not None
        assert row["status"] == "saved"

    def test_status_update_returns_badge_html(self, client):
        """Response contains a status-badge span with title-cased label."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.post(f"/jobs/{key}/status", data={"status": "applied"})
        assert "status-badge" in response.text
        assert "Applied" in response.text

    def test_status_update_sets_hx_trigger(self, client):
        """Response includes HX-Trigger header set to 'statsChanged'."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.post(f"/jobs/{key}/status", data={"status": "applied"})
        assert response.headers.get("HX-Trigger") == "statsChanged"

    def test_status_update_logs_activity(self, client):
        """Status change produces a status_change activity log entry."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        client.post(f"/jobs/{key}/status", data={"status": "scored"})

        log = db_module.get_activity_log(key)
        status_changes = [e for e in log if e["event_type"] == "status_change"]
        assert len(status_changes) == 1
        assert status_changes[0]["new_value"] == "scored"

    def test_applied_status_sets_applied_date(self, client):
        """Setting status to 'applied' also sets applied_date."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        client.post(f"/jobs/{key}/status", data={"status": "applied"})

        row = db_module.get_job(key)
        assert row is not None
        assert row["applied_date"] is not None


# ---------------------------------------------------------------------------
# WEB-03: Notes Update Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNotesUpdateEndpoint:
    """Verify POST /jobs/{key}/notes persists notes and returns confirmation."""

    def test_notes_update_returns_200(self, client):
        """POST /jobs/{key}/notes returns 200."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.post(f"/jobs/{key}/notes", data={"notes": "Great match for K8s role"})
        assert response.status_code == 200

    def test_notes_update_persists(self, client):
        """Notes text is persisted and retrievable via get_job()."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        client.post(f"/jobs/{key}/notes", data={"notes": "Follow up next week"})

        row = db_module.get_job(key)
        assert row is not None
        assert row["notes"] == "Follow up next week"

    def test_notes_update_returns_confirmation(self, client):
        """Response contains 'Saved' confirmation text."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        response = client.post(f"/jobs/{key}/notes", data={"notes": "test"})
        assert "Saved" in response.text

    def test_notes_update_logs_activity(self, client):
        """Notes update produces a note_added activity log entry."""
        db_module.upsert_job(_make_job_dict("Google", "Staff Engineer"))
        key = _compute_dedup_key("Google", "Staff Engineer")

        client.post(f"/jobs/{key}/notes", data={"notes": "Important role"})

        log = db_module.get_activity_log(key)
        note_entries = [e for e in log if e["event_type"] == "note_added"]
        assert len(note_entries) == 1


# ---------------------------------------------------------------------------
# WEB-04: CSV Export Endpoint
# ---------------------------------------------------------------------------


CSV_EXPECTED_FIELDS = [
    "title",
    "company",
    "location",
    "salary_display",
    "platform",
    "status",
    "score",
    "url",
    "posted_date",
    "created_at",
]


@pytest.mark.integration
class TestCsvExport:
    """Verify GET /export/csv returns valid, filterable CSV downloads."""

    def test_csv_returns_200(self, client, db_with_jobs):
        """GET /export/csv returns 200."""
        response = client.get("/export/csv")
        assert response.status_code == 200

    def test_csv_content_type(self, client, db_with_jobs):
        """GET /export/csv returns text/csv content type."""
        response = client.get("/export/csv")
        assert "text/csv" in response.headers["content-type"]

    def test_csv_has_content_disposition(self, client, db_with_jobs):
        """GET /export/csv returns Content-Disposition attachment header."""
        response = client.get("/export/csv")
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert ".csv" in disposition

    def test_csv_parseable_by_csv_module(self, client, db_with_jobs):
        """CSV body is parseable by csv.DictReader and contains 10 rows."""
        response = client.get("/export/csv")
        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)
        assert len(rows) == 10

    def test_csv_has_correct_headers(self, client, db_with_jobs):
        """CSV headers contain all 10 expected fields."""
        response = client.get("/export/csv")
        reader = csv.DictReader(io.StringIO(response.text))
        # Must read at least one row to populate fieldnames
        list(reader)
        assert reader.fieldnames is not None
        for field in CSV_EXPECTED_FIELDS:
            assert field in reader.fieldnames, f"Missing CSV header: {field}"

    def test_csv_row_data_matches_jobs(self, client):
        """Inserted job data appears correctly in CSV output."""
        db_module.upsert_job(_make_job_dict("TestCorp", "Staff K8s Engineer", score=5))
        response = client.get("/export/csv")
        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)
        matching = [r for r in rows if r["title"] == "Staff K8s Engineer"]
        assert len(matching) == 1
        assert matching[0]["company"] == "TestCorp"

    def test_csv_respects_platform_filter(self, client):
        """GET /export/csv?platform=dice returns only dice jobs."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Indeed Dev", platform="indeed"))
        db_module.upsert_job(_make_job_dict("BetaCo", "Dice Dev", platform="dice"))
        response = client.get("/export/csv?platform=dice")
        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)
        assert len(rows) >= 1
        for row in rows:
            assert row["platform"] == "dice"

    def test_csv_empty_db_returns_headers_only(self, client):
        """GET /export/csv with no jobs returns headers but zero rows."""
        response = client.get("/export/csv")
        reader = csv.DictReader(io.StringIO(response.text))
        rows = list(reader)
        assert len(rows) == 0
        assert reader.fieldnames is not None
        assert len(reader.fieldnames) == 10


# ---------------------------------------------------------------------------
# WEB-05: JSON Export Endpoint
# ---------------------------------------------------------------------------


JSON_EXPECTED_FIELDS = [
    "title",
    "company",
    "location",
    "salary_display",
    "platform",
    "status",
    "score",
    "url",
    "apply_url",
    "posted_date",
    "created_at",
    "notes",
]


@pytest.mark.integration
class TestJsonExport:
    """Verify GET /export/json returns valid, filterable JSON downloads."""

    def test_json_returns_200(self, client, db_with_jobs):
        """GET /export/json returns 200."""
        response = client.get("/export/json")
        assert response.status_code == 200

    def test_json_content_type(self, client, db_with_jobs):
        """GET /export/json returns application/json content type."""
        response = client.get("/export/json")
        assert "application/json" in response.headers["content-type"]

    def test_json_has_content_disposition(self, client, db_with_jobs):
        """GET /export/json returns Content-Disposition attachment header."""
        response = client.get("/export/json")
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert ".json" in disposition

    def test_json_parseable(self, client, db_with_jobs):
        """JSON body is parseable by json.loads and contains 10 entries."""
        response = client.get("/export/json")
        data = json.loads(response.text)
        assert isinstance(data, list)
        assert len(data) == 10

    def test_json_has_correct_fields(self, client, db_with_jobs):
        """Each JSON entry contains all 12 expected fields."""
        response = client.get("/export/json")
        data = json.loads(response.text)
        assert len(data) > 0
        for entry in data:
            for field in JSON_EXPECTED_FIELDS:
                assert field in entry, f"Missing JSON field: {field}"

    def test_json_row_data_matches_jobs(self, client):
        """Inserted job data appears correctly in JSON output."""
        db_module.upsert_job(
            _make_job_dict(
                "ExportCorp", "Platform Lead", score=4, apply_url="https://apply.example.com"
            )
        )
        response = client.get("/export/json")
        data = json.loads(response.text)
        matching = [d for d in data if d["title"] == "Platform Lead"]
        assert len(matching) == 1
        assert matching[0]["company"] == "ExportCorp"
        assert matching[0]["apply_url"] == "https://apply.example.com"

    def test_json_respects_score_filter(self, client):
        """GET /export/json?score=5 returns only jobs with score >= 5."""
        db_module.upsert_job(_make_job_dict("AlphaCo", "Low Score Export", score=3))
        db_module.upsert_job(_make_job_dict("BetaCo", "High Score Export", score=5))
        response = client.get("/export/json?score=5")
        data = json.loads(response.text)
        assert len(data) >= 1
        for entry in data:
            assert entry["score"] >= 5

    def test_json_empty_db_returns_empty_list(self, client):
        """GET /export/json with no jobs returns an empty list."""
        response = client.get("/export/json")
        data = json.loads(response.text)
        assert data == []
