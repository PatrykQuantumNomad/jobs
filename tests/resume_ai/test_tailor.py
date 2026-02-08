"""Unit tests for resume_ai/tailor.py -- tailor_resume and format_resume_as_text.

Tests cover:
- Successful resume tailoring via mocked Anthropic client
- AuthenticationError and APIError handling
- No parsed output handling
- Plain-text formatting with ATS section headers
"""

from unittest.mock import MagicMock

import pytest

from resume_ai.models import SkillSection, TailoredResume, WorkExperience
from resume_ai.tailor import SYSTEM_PROMPT, format_resume_as_text, tailor_resume


def _make_tailored_resume() -> TailoredResume:
    """Create a minimal TailoredResume for testing."""
    return TailoredResume(
        professional_summary="Expert cloud engineer with 10 years experience.",
        technical_skills=[
            SkillSection(category="Platform & Cloud", skills=["Kubernetes", "AWS", "Terraform"]),
            SkillSection(category="Backend", skills=["Python", "Go"]),
        ],
        work_experience=[
            WorkExperience(
                company="Acme Corp",
                title="Staff Engineer",
                period="2020 - Present",
                achievements=["Led migration to Kubernetes", "Reduced costs by 30%"],
            ),
        ],
        key_projects=["Open-source CLI tool for cluster management"],
        education="BSc Computer Science, University of Toronto",
        tailoring_notes="Reordered skills to emphasize cloud expertise.",
    )


@pytest.mark.unit
class TestTailorResume:
    """Verify tailor_resume() API interaction and error handling."""

    def test_tailor_resume_success(self, mock_anthropic):
        """tailor_resume returns TailoredResume when API succeeds."""
        expected = _make_tailored_resume()
        mock_response = MagicMock()
        mock_response.parsed_output = expected
        mock_anthropic.messages.parse.return_value = mock_response

        result = tailor_resume("resume text", "job desc", "Engineer", "Acme")

        assert result is expected
        mock_anthropic.messages.parse.assert_called_once()
        call_kwargs = mock_anthropic.messages.parse.call_args.kwargs
        assert call_kwargs["max_tokens"] == 4096
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["system"] == SYSTEM_PROMPT
        assert call_kwargs["output_format"] is TailoredResume

    def test_tailor_resume_auth_error_on_client_init(self, monkeypatch):
        """tailor_resume raises RuntimeError with ANTHROPIC_API_KEY on AuthenticationError."""
        import anthropic

        monkeypatch.setattr(
            anthropic,
            "Anthropic",
            MagicMock(
                side_effect=anthropic.AuthenticationError(
                    message="bad key",
                    response=MagicMock(status_code=401),
                    body=None,
                )
            ),
        )
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            tailor_resume("resume", "desc", "title", "company")

    def test_tailor_resume_api_error(self, mock_anthropic):
        """tailor_resume raises RuntimeError on APIError during parse."""
        import anthropic

        mock_anthropic.messages.parse.side_effect = anthropic.APIError(
            message="server error",
            request=MagicMock(),
            body=None,
        )
        with pytest.raises(RuntimeError, match="Anthropic API error"):
            tailor_resume("resume", "desc", "title", "company")

    def test_tailor_resume_no_parsed_output(self, mock_anthropic):
        """tailor_resume raises RuntimeError when parsed_output is None."""
        mock_response = MagicMock()
        mock_response.parsed_output = None
        mock_anthropic.messages.parse.return_value = mock_response

        with pytest.raises(RuntimeError, match="no parsed output"):
            tailor_resume("resume", "desc", "title", "company")


@pytest.mark.unit
class TestFormatResumeAsText:
    """Verify format_resume_as_text produces ATS-friendly plain text."""

    def test_contains_all_section_headers(self):
        """Output contains all five ATS section headers."""
        tailored = _make_tailored_resume()
        text = format_resume_as_text(tailored)

        assert "PROFESSIONAL SUMMARY" in text
        assert "TECHNICAL SKILLS" in text
        assert "WORK EXPERIENCE" in text
        assert "KEY PROJECTS" in text
        assert "EDUCATION" in text

    def test_contains_specific_content(self):
        """Output contains specific resume data from the model."""
        tailored = _make_tailored_resume()
        text = format_resume_as_text(tailored)

        assert "Expert cloud engineer" in text
        assert "Kubernetes" in text
        assert "Acme Corp" in text
        assert "Staff Engineer" in text
        assert "Led migration to Kubernetes" in text
        assert "BSc Computer Science" in text

    def test_skills_formatted_with_category(self):
        """Skills sections include category and comma-separated skills."""
        tailored = _make_tailored_resume()
        text = format_resume_as_text(tailored)

        assert "Platform & Cloud: Kubernetes, AWS, Terraform" in text
        assert "Backend: Python, Go" in text
