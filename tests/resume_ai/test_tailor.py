"""Unit tests for resume_ai/tailor.py -- tailor_resume and format_resume_as_text.

Tests cover:
- Successful resume tailoring via mocked Claude CLI subprocess
- CLI error handling (non-zero exit code)
- CLI not found handling
- Plain-text formatting with ATS section headers
"""

from unittest.mock import patch

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
    """Verify tailor_resume() CLI interaction and error handling."""

    @pytest.mark.asyncio
    async def test_tailor_resume_success(self, mock_claude_cli):
        """tailor_resume returns TailoredResume when CLI succeeds."""
        expected = _make_tailored_resume()
        mock_claude_cli.set_response(expected)

        result = await tailor_resume("resume text", "job desc", "Engineer", "Acme")

        assert result == expected
        assert result.professional_summary == expected.professional_summary
        assert result.tailoring_notes == expected.tailoring_notes

    @pytest.mark.asyncio
    async def test_tailor_resume_cli_error(self, mock_claude_cli):
        """tailor_resume raises RuntimeError when CLI exits with non-zero code."""
        mock_claude_cli.set_error(returncode=1, stderr_text="Something went wrong")

        with pytest.raises(RuntimeError, match="Resume tailoring failed"):
            await tailor_resume("resume", "desc", "title", "company")

    @pytest.mark.asyncio
    async def test_tailor_resume_cli_not_found(self):
        """tailor_resume raises RuntimeError when claude binary is not on PATH."""
        with (
            patch("claude_cli.client.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="Resume tailoring failed"),
        ):
            await tailor_resume("resume", "desc", "title", "company")

    @pytest.mark.asyncio
    async def test_system_prompt_passed(self, mock_claude_cli):
        """Verify the anti-fabrication system prompt is used."""
        expected = _make_tailored_resume()
        mock_claude_cli.set_response(expected)

        await tailor_resume("resume text", "job desc", "Engineer", "Acme")

        # System prompt should contain anti-fabrication rules
        assert "MUST NOT" in SYSTEM_PROMPT
        assert "fabricate" in SYSTEM_PROMPT.lower()


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
