"""Unit tests for resume_ai/cover_letter.py -- generate_cover_letter and
format_cover_letter_as_text.

Tests cover:
- Successful cover letter generation via mocked Anthropic client
- AuthenticationError handling
- No parsed output handling
- Plain-text formatting with candidate name
"""

from unittest.mock import MagicMock

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
    """Verify generate_cover_letter() API interaction and error handling."""

    def test_generate_cover_letter_success(self, mock_anthropic):
        """generate_cover_letter returns CoverLetter when API succeeds."""
        expected = _make_cover_letter()
        mock_response = MagicMock()
        mock_response.parsed_output = expected
        mock_anthropic.messages.parse.return_value = mock_response

        result = generate_cover_letter("resume text", "job desc", "Engineer", "Acme")

        assert result is expected
        mock_anthropic.messages.parse.assert_called_once()
        call_kwargs = mock_anthropic.messages.parse.call_args.kwargs
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["output_format"] is CoverLetter

    def test_generate_cover_letter_auth_error(self, monkeypatch):
        """generate_cover_letter raises RuntimeError on AuthenticationError."""
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
            generate_cover_letter("resume", "desc", "title", "company")

    def test_generate_cover_letter_no_parsed_output(self, mock_anthropic):
        """generate_cover_letter raises RuntimeError when parsed_output is None."""
        mock_response = MagicMock()
        mock_response.parsed_output = None
        mock_anthropic.messages.parse.return_value = mock_response

        with pytest.raises(RuntimeError, match="no parsed output"):
            generate_cover_letter("resume", "desc", "title", "company")


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
