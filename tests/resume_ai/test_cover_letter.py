"""Unit tests for resume_ai/cover_letter.py -- generate_cover_letter and
format_cover_letter_as_text.

Tests cover:
- Successful cover letter generation via mocked Claude CLI subprocess
- CLI error handling (non-zero exit code)
- CLI not found handling
- Plain-text formatting with candidate name
"""

from unittest.mock import patch

import pytest

from resume_ai.cover_letter import format_cover_letter_as_text, generate_cover_letter
from resume_ai.models import CoverLetter


def _make_cover_letter() -> CoverLetter:
    """Create a minimal CoverLetter for testing."""
    return CoverLetter(
        greeting="Dear Hiring Manager,",
        opening_paragraph="I am excited to apply for the Staff Engineer position at Acme.",
        body_paragraphs=[
            "With 10 years of cloud engineering experience, I have led Kubernetes migrations.",
            "My open-source contributions to LangFlow demonstrate my commitment to the community.",
        ],
        closing_paragraph="I would welcome the opportunity to discuss how I can contribute.",
        sign_off="Sincerely,",
    )


@pytest.mark.unit
class TestGenerateCoverLetter:
    """Verify generate_cover_letter() CLI interaction and error handling."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(self, mock_claude_cli):
        """generate_cover_letter returns CoverLetter when CLI succeeds."""
        expected = _make_cover_letter()
        mock_claude_cli.set_response(expected)

        result = await generate_cover_letter("resume text", "job desc", "Engineer", "Acme")

        assert result == expected
        assert result.greeting == expected.greeting
        assert result.opening_paragraph == expected.opening_paragraph

    @pytest.mark.asyncio
    async def test_generate_cover_letter_cli_error(self, mock_claude_cli):
        """generate_cover_letter raises RuntimeError when CLI exits with non-zero code."""
        mock_claude_cli.set_error(returncode=1, stderr_text="Something went wrong")

        with pytest.raises(RuntimeError, match="Cover letter generation failed"):
            await generate_cover_letter("resume", "desc", "title", "company")

    @pytest.mark.asyncio
    async def test_generate_cover_letter_cli_not_found(self):
        """generate_cover_letter raises RuntimeError when claude binary is not on PATH."""
        with (
            patch("claude_cli.client.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="Cover letter generation failed"),
        ):
            await generate_cover_letter("resume", "desc", "title", "company")


@pytest.mark.unit
class TestFormatCoverLetterAsText:
    """Verify format_cover_letter_as_text produces properly formatted text."""

    def test_contains_all_parts(self):
        """Output contains greeting, opening, body paragraphs, closing, and sign-off."""
        letter = _make_cover_letter()
        text = format_cover_letter_as_text(letter, "John Doe")

        assert "Dear Hiring Manager," in text
        assert "I am excited to apply" in text
        assert "Kubernetes migrations" in text
        assert "LangFlow" in text
        assert "I would welcome the opportunity" in text
        assert "Sincerely," in text
        assert "John Doe" in text

    def test_paragraphs_separated_by_double_newlines(self):
        """Paragraphs are separated by double newlines."""
        letter = _make_cover_letter()
        text = format_cover_letter_as_text(letter, "John Doe")

        # The greeting and opening paragraph should be separated by \n\n
        assert "Dear Hiring Manager,\n\n" in text
        # Body paragraphs should be separated
        assert "Kubernetes migrations.\n\n" in text

    def test_candidate_name_after_sign_off(self):
        """Candidate name appears after sign-off line."""
        letter = _make_cover_letter()
        text = format_cover_letter_as_text(letter, "Jane Smith")

        signoff_pos = text.index("Sincerely,")
        name_pos = text.index("Jane Smith")
        assert name_pos > signoff_pos
