"""Integration tests for SSE cover letter generation endpoints.

Tests cover:
- POST /jobs/{key}/cover-letter returns SSE-connect HTML (not blocking)
- POST returns 404 for missing job
- Double-click protection returns "already in progress"
- GET /jobs/{key}/cover-letter/stream returns 404 without active session
- Background task emits 3 stage progress events + done
- Background task emits error event on failure
"""

import asyncio
from unittest.mock import patch

import pytest

import webapp.db as db_module
from resume_ai.models import CoverLetter
from webapp.app import _cover_sessions, _run_cover_letter

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
        "description": f"{title} role at {company} with extensive responsibilities",
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


def _make_cover_letter() -> CoverLetter:
    """Build a minimal CoverLetter for mocking."""
    return CoverLetter(
        greeting="Dear Hiring Manager,",
        opening_paragraph="I am excited to apply for this role.",
        body_paragraphs=["I have extensive experience in cloud infrastructure and DevOps."],
        closing_paragraph="Thank you for considering my application.",
        sign_off="Sincerely,",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCoverLetterSSE:
    """Verify SSE cover letter generation endpoints and background task."""

    def test_cover_letter_returns_sse_connect_html(self, client, mock_claude_cli):
        """POST /jobs/{key}/cover-letter returns SSE-connect div immediately."""
        mock_claude_cli.set_response(_make_cover_letter())

        db_module.upsert_job(_make_job_dict("CoverCo", "Cover Engineer"))
        key = _compute_dedup_key("CoverCo", "Cover Engineer")

        with (
            patch("resume_ai.extractor.extract_resume_text", return_value="Original resume text"),
            patch("resume_ai.renderer.render_cover_letter_pdf"),
            patch("resume_ai.tracker.save_resume_version"),
        ):
            response = client.post(f"/jobs/{key}/cover-letter")

        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "cover-letter/stream" in response.text

        # Clean up session state
        _cover_sessions.pop(key, None)

    def test_cover_letter_404_for_missing_job(self, client):
        """POST with a nonexistent dedup_key returns 404."""
        response = client.post("/jobs/nonexistent::key/cover-letter")
        assert response.status_code == 404

    def test_cover_letter_already_in_progress(self, client):
        """Double-click returns 'already in progress' message."""
        db_module.upsert_job(_make_job_dict("DupCoverCo", "Dup Cover Engineer"))
        key = _compute_dedup_key("DupCoverCo", "Dup Cover Engineer")

        # Manually inject a session
        _cover_sessions[key] = asyncio.Queue()
        try:
            response = client.post(f"/jobs/{key}/cover-letter")
            assert response.status_code == 200
            assert "already in progress" in response.text
        finally:
            _cover_sessions.pop(key, None)

    def test_stream_404_for_no_session(self, client):
        """GET /jobs/{key}/cover-letter/stream without active session returns 404."""
        response = client.get("/jobs/nonexistent::key/cover-letter/stream")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_background_task_emits_stage_events(self):
        """_run_cover_letter emits 3 progress events + 1 done event."""
        queue: asyncio.Queue = asyncio.Queue()
        job = {
            "title": "Test Engineer",
            "company": "TestCo",
            "description": "A detailed job description for testing purposes",
        }

        letter = _make_cover_letter()

        with (
            patch(
                "resume_ai.extractor.extract_resume_text",
                return_value="Original resume text",
            ),
            patch(
                "resume_ai.cover_letter.generate_cover_letter",
                return_value=letter,
            ),
            patch("resume_ai.renderer.render_cover_letter_pdf"),
            patch("resume_ai.tracker.save_resume_version"),
            patch("webapp.db.log_activity"),
            patch(
                "resume_ai.cover_letter.format_cover_letter_as_text",
                return_value="Dear Hiring Manager,\n\nFormatted letter text",
            ),
        ):
            await _run_cover_letter("test::key", job, "fake/resume.pdf", queue)

        # Collect all events
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        # Should have at least 3 progress events + 1 done event
        progress_events = [e for e in events if e["type"] == "progress"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(progress_events) >= 3, f"Expected 3+ progress events, got {len(progress_events)}"

        # Check stage keywords
        messages = [e["message"] for e in progress_events]
        assert any("Extracting" in m for m in messages), "Missing 'Extracting' stage"
        assert any("Generating" in m for m in messages), "Missing 'Generating' stage"
        assert any("Rendering" in m for m in messages), "Missing 'Rendering' stage"

        # Done event should be last and have HTML content
        assert len(done_events) == 1, "Expected exactly 1 done event"
        assert events[-1]["type"] == "done"
        assert events[-1]["html"], "Done event should have non-empty HTML"

    @pytest.mark.asyncio
    async def test_background_task_emits_error_on_failure(self):
        """_run_cover_letter emits error + done events on failure."""
        queue: asyncio.Queue = asyncio.Queue()
        job = {
            "title": "Test Engineer",
            "company": "TestCo",
            "description": "A detailed job description",
        }

        with (
            patch(
                "resume_ai.extractor.extract_resume_text",
                return_value="Original resume text",
            ),
            patch(
                "resume_ai.cover_letter.generate_cover_letter",
                side_effect=RuntimeError("LLM call failed"),
            ),
        ):
            await _run_cover_letter("test::key", job, "fake/resume.pdf", queue)

        # Collect all events
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        # Should have progress (extracting, generating attempt) + error + done
        error_events = [e for e in events if e["type"] == "error"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(error_events) >= 1, "Expected at least 1 error event"
        assert "failed" in error_events[0]["message"].lower()
        assert len(done_events) == 1, "Expected exactly 1 done event"
