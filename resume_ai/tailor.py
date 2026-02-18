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

KEYWORD EXTRACTION (do this first):
1. Read the job description carefully and identify the top 10-15 keywords and \
phrases that represent core requirements (technologies, methodologies, \
domain terms, soft skills like "cross-functional collaboration").
2. Note which keywords already appear in the original resume (these just need \
emphasis via reordering) and which do NOT appear but have equivalent \
experience (these need rephrasing to bridge the gap).
3. List the keywords you addressed in the keyword_alignment output field.

PROFESSIONAL SUMMARY — ROLE-SPECIFIC, NOT GENERIC:
- Write the summary specifically for this role at this company.
- Open with the candidate's most relevant title/identity that matches the JD \
(e.g., "Platform engineering leader" not just "experienced engineer").
- Reference the company by name and connect the candidate's specific \
strengths to what the role demands.
- Weave in 3-5 top JD keywords naturally — never keyword-stuff.
- Include one quantified achievement from the resume that is most relevant.
- BAD: "Experienced engineer with a passion for technology."
- GOOD: "Platform engineering leader with 10+ years building Kubernetes-native \
infrastructure at scale, bringing deep GKE and Terraform expertise to \
{company_name}'s cloud modernization mission."

BULLET POINT OPTIMIZATION:
- For each achievement bullet, ask: "Does this use the JD's language?"
- Where the candidate has equivalent experience, rephrase the bullet to use \
the JD's terminology while preserving the factual claim. \
Example: If JD says "observability" and resume says "monitoring" for the \
same concept, rephrase to "observability" (this is allowed rephrasing, \
NOT fabrication).
- Front-load bullets with action verbs that match the JD's tone.
- Prioritize bullets that demonstrate the JD's stated requirements.

WHAT YOU MAY ALSO DO:
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
        f"- **Company:** {company_name}\n\n"
        f"## Instructions\n\n"
        f"Tailor this resume for the {job_title} role at {company_name}. "
        f"Follow the KEYWORD EXTRACTION, PROFESSIONAL SUMMARY, and BULLET POINT "
        f"OPTIMIZATION instructions from your system prompt. "
        f"Populate the keyword_alignment field with the JD keywords you addressed."
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
