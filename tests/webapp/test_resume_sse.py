"""Integration tests for SSE resume tailoring endpoints.

Tests cover:
- POST /jobs/{key}/tailor-resume returns SSE-connect HTML (not blocking)
- POST returns 404 for missing job
- Double-click protection returns "already in progress"
- GET /jobs/{key}/tailor-resume/stream returns 404 without active session
- Background task emits 4 stage progress events + done
- Background task emits error event on failure
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import webapp.db as db_module
from resume_ai.models import SkillSection, TailoredResume, WorkExperience
from webapp.app import _resume_sessions, _run_resume_tailor

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


def _make_tailored_resume() -> TailoredResume:
    """Build a minimal TailoredResume for mocking."""
    return TailoredResume(
        professional_summary="Experienced engineer",
        technical_skills=[SkillSection(category="Cloud", skills=["Kubernetes", "Docker"])],
        work_experience=[
            WorkExperience(
                company="TestCo",
                title="Engineer",
                period="2020 - Present",
                achievements=["Built systems"],
            )
        ],
        key_projects=["Project Alpha"],
        education="BSc Computer Science",
        tailoring_notes="Reordered skills for relevance",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestResumeSSE:
    """Verify SSE resume tailoring endpoints and background task."""

    def test_tailor_resume_returns_sse_connect_html(self, client, mock_claude_cli):
        """POST /jobs/{key}/tailor-resume returns SSE-connect div immediately."""
        mock_claude_cli.set_response(_make_tailored_resume())

        db_module.upsert_job(_make_job_dict("SSECo", "SSE Engineer"))
        key = _compute_dedup_key("SSECo", "SSE Engineer")

        with (
            patch("resume_ai.extractor.extract_resume_text", return_value="Original resume text"),
            patch("resume_ai.renderer.render_resume_pdf"),
            patch("resume_ai.tracker.save_resume_version"),
        ):
            response = client.post(f"/jobs/{key}/tailor-resume")

        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "tailor-resume/stream" in response.text

        # Clean up session state
        _resume_sessions.pop(key, None)

    def test_tailor_resume_404_for_missing_job(self, client):
        """POST with a nonexistent dedup_key returns 404."""
        response = client.post("/jobs/nonexistent::key/tailor-resume")
        assert response.status_code == 404

    def test_tailor_resume_already_in_progress(self, client):
        """Double-click returns 'already in progress' message."""
        db_module.upsert_job(_make_job_dict("DupCo", "Dup Engineer"))
        key = _compute_dedup_key("DupCo", "Dup Engineer")

        # Manually inject a session
        _resume_sessions[key] = asyncio.Queue()
        try:
            response = client.post(f"/jobs/{key}/tailor-resume")
            assert response.status_code == 200
            assert "already in progress" in response.text
        finally:
            _resume_sessions.pop(key, None)

    def test_stream_404_for_no_session(self, client):
        """GET /jobs/{key}/tailor-resume/stream without active session returns 404."""
        response = client.get("/jobs/nonexistent::key/tailor-resume/stream")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_background_task_emits_stage_events(self):
        """_run_resume_tailor emits 4 progress events + 1 done event."""
        queue: asyncio.Queue = asyncio.Queue()
        job = {
            "title": "Test Engineer",
            "company": "TestCo",
            "description": "A detailed job description for testing purposes",
        }

        tailored = _make_tailored_resume()
        mock_validation = MagicMock(is_valid=True, warnings=[])

        with (
            patch(
                "resume_ai.extractor.extract_resume_text",
                return_value="Original resume text",
            ),
            patch(
                "resume_ai.tailor.tailor_resume",
                return_value=tailored,
            ),
            patch(
                "resume_ai.validator.validate_no_fabrication",
                return_value=mock_validation,
            ),
            patch("resume_ai.renderer.render_resume_pdf"),
            patch("resume_ai.tracker.save_resume_version"),
            patch("webapp.db.log_activity"),
            patch(
                "resume_ai.tailor.format_resume_as_text",
                return_value="Tailored resume text",
            ),
            patch(
                "resume_ai.diff.generate_resume_diff_html",
                return_value="<table>diff</table>",
            ),
            patch(
                "resume_ai.diff.wrap_diff_html",
                return_value="<div>styled diff</div>",
            ),
        ):
            await _run_resume_tailor("test::key", job, "fake/resume.pdf", queue)

        # Collect all events
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        # Should have at least 4 progress events + 1 done event
        progress_events = [e for e in events if e["type"] == "progress"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(progress_events) >= 4, f"Expected 4+ progress events, got {len(progress_events)}"

        # Check stage keywords
        messages = [e["message"] for e in progress_events]
        assert any("Extracting" in m for m in messages), "Missing 'Extracting' stage"
        assert any("Generating" in m for m in messages), "Missing 'Generating' stage"
        assert any("Validating" in m for m in messages), "Missing 'Validating' stage"
        assert any("Rendering" in m for m in messages), "Missing 'Rendering' stage"

        # Done event should be last and have HTML content
        assert len(done_events) == 1, "Expected exactly 1 done event"
        assert events[-1]["type"] == "done"
        assert events[-1]["html"], "Done event should have non-empty HTML"

    @pytest.mark.asyncio
    async def test_background_task_emits_error_on_failure(self):
        """_run_resume_tailor emits error + done events on failure."""
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
                "resume_ai.tailor.tailor_resume",
                side_effect=RuntimeError("LLM call failed"),
            ),
        ):
            await _run_resume_tailor("test::key", job, "fake/resume.pdf", queue)

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
