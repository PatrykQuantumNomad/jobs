"""Resume tailoring via Claude CLI structured outputs.

Uses the ``claude_cli.run()`` async subprocess wrapper to produce a
:class:`TailoredResume` that reorders skills and achievements for a target role
while strictly forbidding fabrication of any fact not present in the original resume.
"""

from claude_cli import run as cli_run
from claude_cli.exceptions import CLIError
from resume_ai.models import TailoredResume

# ---------------------------------------------------------------------------
# Anti-fabrication system prompt (Layer 1: prompt-level guardrail)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert resume tailoring assistant.  Your task is to reorganize and \
rephrase an existing resume so it best matches a target job description.

ABSOLUTE RULES — VIOLATION IS UNACCEPTABLE:
1. You MUST NOT add any skill, technology, company, role, metric, percentage, \
dollar amount, or achievement that does not already appear in the original resume.
2. You MUST NOT invent certifications, awards, patents, publications, or \
education credentials.
3. You MUST NOT change employment dates, company names, or job titles.
4. You MUST NOT fabricate quantified results (e.g., "reduced costs by 40%") \
unless that exact metric appears in the original.

WHAT YOU MAY DO:
- Reorder sections to put the most relevant content first.
- Reorder bullet points within a section by relevance to the target role.
- Rephrase bullet points for clarity, conciseness, and keyword alignment \
  while preserving the original meaning and all factual claims.
- Adjust the professional summary to emphasize the skills and experience \
  most relevant to the target role.
- Reorder the skills list so the most relevant categories and individual \
  skills appear first.
- Expand acronyms from the job description on first use \
  (e.g., "Google Kubernetes Engine (GKE)").

FORMATTING:
- Keep the resume to a maximum of 2 pages.
- Use standard ATS-friendly section headers: PROFESSIONAL SUMMARY, \
  TECHNICAL SKILLS, WORK EXPERIENCE, KEY PROJECTS, EDUCATION.
- Use clear, concise language.  Avoid jargon the ATS may not recognize.

In your tailoring_notes field, explain what you changed and why.\
"""

# Default model alias for resume tailoring (CLI uses short aliases)
DEFAULT_MODEL = "opus"


async def tailor_resume(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = DEFAULT_MODEL,
) -> TailoredResume:
    """Tailor a resume to a specific job posting using Claude CLI structured outputs.

    Parameters
    ----------
    resume_text:
        The full text of the original resume (Markdown or plain text).
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
    TailoredResume
        Structured resume output with reordered skills and achievements.

    Raises
    ------
    RuntimeError
        If the Claude CLI is missing, not authenticated, or the call fails.
    """
    user_message = (
        f"## Original Resume\n\n{resume_text}\n\n"
        f"## Target Job Description\n\n{job_description}\n\n"
        f"## Target Role\n\n"
        f"- **Job Title:** {job_title}\n"
        f"- **Company:** {company_name}\n"
    )

    try:
        return await cli_run(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            output_model=TailoredResume,
            model=model,
        )
    except CLIError as exc:
        raise RuntimeError(f"Resume tailoring failed: {exc}") from exc


def format_resume_as_text(tailored: TailoredResume) -> str:
    """Convert a :class:`TailoredResume` to plain text with ATS section headers.

    Useful for diff comparison against the original resume and for rendering
    to PDF or other output formats.

    Parameters
    ----------
    tailored:
        The structured resume to format.

    Returns
    -------
    str
        Plain-text resume with standard ATS section headers.
    """
    sections: list[str] = []

    # Professional Summary
    sections.append(f"PROFESSIONAL SUMMARY\n\n{tailored.professional_summary}")

    # Technical Skills
    skill_lines: list[str] = []
    for section in tailored.technical_skills:
        skill_lines.append(f"{section.category}: {', '.join(section.skills)}")
    sections.append("TECHNICAL SKILLS\n\n" + "\n".join(skill_lines))

    # Work Experience
    exp_blocks: list[str] = []
    for exp in tailored.work_experience:
        header = f"{exp.title} - {exp.company} ({exp.period})"
        bullets = "\n".join(f"  - {a}" for a in exp.achievements)
        exp_blocks.append(f"{header}\n{bullets}")
    sections.append("WORK EXPERIENCE\n\n" + "\n\n".join(exp_blocks))

    # Key Projects
    project_lines = "\n".join(f"- {p}" for p in tailored.key_projects)
    sections.append(f"KEY PROJECTS\n\n{project_lines}")

    # Education
    sections.append(f"EDUCATION\n\n{tailored.education}")

    return "\n\n".join(sections) + "\n"
