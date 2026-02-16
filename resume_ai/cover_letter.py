"""Cover letter generation via Claude CLI structured outputs.

Uses the ``claude_cli.run()`` async subprocess wrapper to produce a
:class:`CoverLetter` that connects the candidate's real experience to a
specific role and company.
"""

from claude_cli import run as cli_run
from claude_cli.exceptions import CLIError
from resume_ai.models import CoverLetter

# ---------------------------------------------------------------------------
# System prompt for cover letter generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert cover letter writer.  Your task is to create a compelling, \
professional cover letter that connects the candidate's experience to a \
specific job opening.

ABSOLUTE RULES — VIOLATION IS UNACCEPTABLE:
1. You MUST ONLY reference achievements, skills, and experience that appear \
   in the provided resume.  Do NOT fabricate any detail.
2. You MUST NOT invent metrics, percentages, dollar amounts, or results that \
   are not in the resume.
3. You MUST NOT claim experience with technologies or tools not listed in \
   the resume.
4. You MUST NOT fabricate company names, project names, or role titles.

CONTENT GUIDELINES:
- Open with specific interest in the company and the exact role being applied for.
- Highlight 2-3 most relevant achievements with specific metrics from the resume.
- Connect the candidate's experience directly to requirements in the job description.
- Mention open-source contributions (e.g., LangFlow, Kubert) when relevant to \
  the role.
- Reference content creation (YouTube, blog posts) when it demonstrates domain \
  expertise relevant to the role.
- Keep the total letter to approximately 300-400 words (one page).
- Use a professional but personable tone.
- End with a clear call to action expressing enthusiasm for next steps.

FORMATTING:
- The greeting should address the hiring team professionally.
- Use 2-3 body paragraphs, each focused on a different strength.
- The closing should reiterate fit and enthusiasm.
- Sign off professionally.\
"""

# Default model alias for cover letter generation (CLI uses short aliases)
DEFAULT_MODEL = "opus"


async def generate_cover_letter(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = DEFAULT_MODEL,
) -> CoverLetter:
    """Generate a cover letter tailored to a specific job posting via Claude CLI.

    Parameters
    ----------
    resume_text:
        The full text of the candidate's resume (Markdown or plain text).
    job_description:
        The full job description / posting text.
    job_title:
        The target job title (e.g., "Principal Engineer").
    company_name:
        The hiring company name.
    model:
        Claude CLI model alias.  Defaults to 'sonnet'.

    Returns
    -------
    CoverLetter
        Structured cover letter with greeting, paragraphs, and sign-off.

    Raises
    ------
    RuntimeError
        If the Claude CLI is missing, not authenticated, or the call fails.
    """
    user_message = (
        f"## Candidate Resume\n\n{resume_text}\n\n"
        f"## Job Description\n\n{job_description}\n\n"
        f"## Target Role\n\n"
        f"- **Job Title:** {job_title}\n"
        f"- **Company:** {company_name}\n"
    )

    try:
        return await cli_run(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            output_model=CoverLetter,
            model=model,
        )
    except CLIError as exc:
        raise RuntimeError(f"Cover letter generation failed: {exc}") from exc


def format_cover_letter_as_text(letter: CoverLetter, candidate_name: str) -> str:
    """Convert a :class:`CoverLetter` to formatted plain text.

    Produces a ready-to-display cover letter with proper paragraph spacing.
    Used for the diff view in the dashboard and for rendering to PDF.

    Parameters
    ----------
    letter:
        The structured cover letter to format.
    candidate_name:
        Full name of the candidate (appended after the sign-off).

    Returns
    -------
    str
        Formatted cover letter text.
    """
    parts: list[str] = [
        letter.greeting,
        letter.opening_paragraph,
        *letter.body_paragraphs,
        letter.closing_paragraph,
        f"{letter.sign_off}\n{candidate_name}",
    ]
    return "\n\n".join(parts) + "\n"
