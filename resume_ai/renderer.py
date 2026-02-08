"""HTML-to-PDF rendering for tailored resumes and cover letters.

Uses Jinja2 templates with WeasyPrint to produce ATS-friendly PDF documents
from structured :class:`TailoredResume` and :class:`CoverLetter` model data.
"""

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

if TYPE_CHECKING:
    from resume_ai.models import CoverLetter, TailoredResume

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "webapp" / "templates" / "resume"

_env: Environment | None = None


def _get_env() -> Environment:
    """Return a lazily-initialized Jinja2 environment for resume templates."""
    global _env  # noqa: PLW0603
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )
    return _env


def render_resume_pdf(
    tailored: TailoredResume,
    candidate_name: str,
    contact_info: str,
    output_path: Path,
) -> Path:
    """Render a tailored resume as a professional PDF.

    Parameters
    ----------
    tailored:
        Structured resume data produced by the LLM tailoring engine.
    candidate_name:
        Full name for the resume header.
    contact_info:
        Contact line (e.g. ``"email | phone | location"``).
    output_path:
        Destination path for the generated PDF file.

    Returns
    -------
    Path
        The *output_path* after the PDF has been written.
    """
    env = _get_env()
    template = env.get_template("resume_template.html")

    html_content = template.render(
        name=candidate_name,
        contact_info=contact_info,
        summary=tailored.professional_summary,
        skills=tailored.technical_skills,
        experience=tailored.work_experience,
        projects=tailored.key_projects,
        education=tailored.education,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(output_path))
    return output_path


def render_cover_letter_pdf(
    letter: CoverLetter,
    candidate_name: str,
    candidate_email: str,
    candidate_phone: str,
    output_path: Path,
) -> Path:
    """Render a cover letter as a clean one-page PDF.

    Parameters
    ----------
    letter:
        Structured cover letter data produced by the LLM.
    candidate_name:
        Full name for the letterhead and signature.
    candidate_email:
        Email address for the sender info block.
    candidate_phone:
        Phone number for the sender info block.
    output_path:
        Destination path for the generated PDF file.

    Returns
    -------
    Path
        The *output_path* after the PDF has been written.
    """
    env = _get_env()
    template = env.get_template("cover_letter_template.html")

    html_content = template.render(
        date=date.today().strftime("%B %d, %Y"),
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        greeting=letter.greeting,
        opening_paragraph=letter.opening_paragraph,
        body_paragraphs=letter.body_paragraphs,
        closing_paragraph=letter.closing_paragraph,
        sign_off=letter.sign_off,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(output_path))
    return output_path
