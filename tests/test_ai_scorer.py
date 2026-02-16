"""Tests for the AI job-fit scorer module."""

import pytest
from pydantic import ValidationError

from core.ai_scorer import AIScoreResult, score_job_ai
from webapp import db as db_module


@pytest.mark.unit
class TestAIScorer:
    """Unit tests for AI scorer function and model."""

    @pytest.mark.asyncio
    async def test_score_job_ai_success(self, mock_claude_cli):
        mock_claude_cli.set_response(
            AIScoreResult(
                score=4,
                reasoning="Good match for the role.",
                strengths=["Python", "AWS"],
                gaps=["Kubernetes"],
            )
        )
        result = await score_job_ai(
            resume_text="Expert in Python and AWS...",
            job_description="Looking for Python developer with K8s...",
            job_title="Senior Engineer",
            company_name="Acme Corp",
        )
        assert result.score == 4
        assert "Good match" in result.reasoning
        assert len(result.strengths) == 2
        assert len(result.gaps) == 1

    @pytest.mark.asyncio
    async def test_score_job_ai_cli_error_wraps_in_runtime_error(self, mock_claude_cli):
        mock_claude_cli.set_error(returncode=1, stderr_text="auth failed")
        with pytest.raises(RuntimeError, match="AI scoring failed"):
            await score_job_ai(
                resume_text="...",
                job_description="...",
                job_title="Engineer",
                company_name="Acme",
            )

    def test_ai_score_result_validates_score_range(self):
        with pytest.raises(ValidationError):
            AIScoreResult(score=0, reasoning="x", strengths=["a"], gaps=["b"])
        with pytest.raises(ValidationError):
            AIScoreResult(score=6, reasoning="x", strengths=["a"], gaps=["b"])
        result = AIScoreResult(score=3, reasoning="ok", strengths=["a"], gaps=[])
        assert result.score == 3

    def test_ai_score_result_schema_has_constraints(self):
        schema = AIScoreResult.model_json_schema()
        score_props = schema["properties"]["score"]
        assert score_props.get("minimum") == 1
        assert score_props.get("maximum") == 5


@pytest.mark.integration
class TestUpdateAIScore:
    """Integration tests for AI score database storage."""

    def test_update_ai_score_persists(self):
        db_module.upsert_job(
            {
                "id": "test-123",
                "platform": "indeed",
                "title": "Test Engineer",
                "company": "Test Corp",
                "url": "https://example.com/job",
                "description": "A test job",
            }
        )
        dedup_key = "test corp::test engineer"
        db_module.update_ai_score(
            dedup_key,
            score=4,
            breakdown={"reasoning": "test", "strengths": ["a"], "gaps": ["b"]},
        )
        job = db_module.get_job(dedup_key)
        assert job is not None
        assert job["ai_score"] == 4
        assert '"reasoning"' in job["ai_score_breakdown"]
        assert job["ai_scored_at"] is not None

    def test_update_ai_score_logs_activity(self):
        db_module.upsert_job(
            {
                "id": "test-456",
                "platform": "dice",
                "title": "Dev",
                "company": "Acme",
                "url": "https://example.com/job2",
                "description": "Another test",
            }
        )
        dedup_key = "acme::dev"
        db_module.update_ai_score(
            dedup_key,
            score=5,
            breakdown={"reasoning": "great", "strengths": ["x"], "gaps": []},
        )
        events = db_module.get_activity_log(dedup_key)
        ai_events = [e for e in events if e["event_type"] == "ai_scored"]
        assert len(ai_events) == 1
        assert ai_events[0]["new_value"] == "5"
