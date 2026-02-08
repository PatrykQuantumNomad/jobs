"""Unit tests for resume_ai/renderer.py -- render_resume_pdf and render_cover_letter_pdf.

Tests cover:
- Resume PDF rendering with mocked Jinja2 env and WeasyPrint
- Cover letter PDF rendering with mocked Jinja2 env and WeasyPrint
- Output directory creation
"""

from unittest.mock import MagicMock, patch

import jinja2
import pytest

from resume_ai.models import CoverLetter, SkillSection, TailoredResume, WorkExperience


def _make_tailored_resume() -> TailoredResume:
    """Create a TailoredResume for testing."""
    return TailoredResume(
        professional_summary="Expert engineer with cloud experience.",
        technical_skills=[SkillSection(category="Cloud", skills=["AWS", "GCP"])],
        work_experience=[
            WorkExperience(
                company="TestCorp",
                title="Lead Engineer",
                period="2020-2024",
                achievements=["Built scalable infra"],
            )
        ],
        key_projects=["CLI tool"],
        education="BSc CS",
        tailoring_notes="Focused on cloud.",
    )


def _make_cover_letter() -> CoverLetter:
    """Create a CoverLetter for testing."""
    return CoverLetter(
        greeting="Dear Team,",
        opening_paragraph="I am applying for the role.",
        body_paragraphs=["I have relevant experience."],
        closing_paragraph="Looking forward to hearing from you.",
        sign_off="Best,",
    )


def _mock_env():
    """Create a Jinja2 environment with inline test templates."""
    return jinja2.Environment(
        loader=jinja2.DictLoader(
            {
                "resume_template.html": (
                    "<html>{{ name }} {{ summary }} "
                    "{% for s in skills %}{{ s.category }}{% endfor %}</html>"
                ),
                "cover_letter_template.html": (
                    "<html>{{ candidate_name }} {{ greeting }} {{ opening_paragraph }}</html>"
                ),
            }
        ),
        autoescape=True,
    )


@pytest.mark.unit
class TestRenderResumePdf:
    """Verify render_resume_pdf calls Jinja2 and WeasyPrint correctly."""

    def test_render_resume_pdf_calls_write_pdf(self, tmp_path):
        """render_resume_pdf renders template and calls HTML.write_pdf."""
        import resume_ai.renderer as renderer_mod

        tailored = _make_tailored_resume()
        output_path = tmp_path / "out" / "resume.pdf"

        mock_html_instance = MagicMock()
        mock_html_cls = MagicMock(return_value=mock_html_instance)

        with (
            patch.object(renderer_mod, "_get_env", return_value=_mock_env()),
            patch.object(renderer_mod, "HTML", mock_html_cls),
        ):
            result = renderer_mod.render_resume_pdf(
                tailored, "John Doe", "email | phone", output_path
            )

        assert result == output_path
        mock_html_cls.assert_called_once()
        mock_html_instance.write_pdf.assert_called_once()
        # Output directory should have been created
        assert output_path.parent.exists()

    def test_render_resume_pdf_template_receives_data(self, tmp_path):
        """The Jinja2 template receives correct context variables."""
        import resume_ai.renderer as renderer_mod

        tailored = _make_tailored_resume()
        output_path = tmp_path / "resume.pdf"

        rendered_html = None

        def capture_html(string=None, base_url=None):
            nonlocal rendered_html
            rendered_html = string
            return MagicMock()

        with (
            patch.object(renderer_mod, "_get_env", return_value=_mock_env()),
            patch.object(renderer_mod, "HTML", side_effect=capture_html),
        ):
            renderer_mod.render_resume_pdf(tailored, "John Doe", "email", output_path)

        assert rendered_html is not None
        assert "John Doe" in rendered_html


@pytest.mark.unit
class TestRenderCoverLetterPdf:
    """Verify render_cover_letter_pdf calls Jinja2 and WeasyPrint correctly."""

    def test_render_cover_letter_pdf_calls_write_pdf(self, tmp_path):
        """render_cover_letter_pdf renders template and calls HTML.write_pdf."""
        import resume_ai.renderer as renderer_mod

        letter = _make_cover_letter()
        output_path = tmp_path / "out" / "letter.pdf"

        mock_html_instance = MagicMock()
        mock_html_cls = MagicMock(return_value=mock_html_instance)

        with (
            patch.object(renderer_mod, "_get_env", return_value=_mock_env()),
            patch.object(renderer_mod, "HTML", mock_html_cls),
        ):
            result = renderer_mod.render_cover_letter_pdf(
                letter, "Jane Smith", "jane@test.com", "555-1234", output_path
            )

        assert result == output_path
        mock_html_cls.assert_called_once()
        mock_html_instance.write_pdf.assert_called_once()
        assert output_path.parent.exists()

    def test_render_cover_letter_pdf_template_receives_data(self, tmp_path):
        """The Jinja2 template receives correct context variables."""
        import resume_ai.renderer as renderer_mod

        letter = _make_cover_letter()
        output_path = tmp_path / "letter.pdf"

        rendered_html = None

        def capture_html(string=None, base_url=None):
            nonlocal rendered_html
            rendered_html = string
            return MagicMock()

        with (
            patch.object(renderer_mod, "_get_env", return_value=_mock_env()),
            patch.object(renderer_mod, "HTML", side_effect=capture_html),
        ):
            renderer_mod.render_cover_letter_pdf(
                letter, "Jane Smith", "jane@test.com", "555-1234", output_path
            )

        assert rendered_html is not None
        assert "Jane Smith" in rendered_html
        assert "Dear Team," in rendered_html
