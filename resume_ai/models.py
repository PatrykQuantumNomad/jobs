"""Pydantic models for LLM-structured resume and cover letter output.

These models define the exact JSON schema that the LLM must produce when
tailoring a resume or generating a cover letter.  Each field includes a
``description`` to guide the LLM toward the desired output format.
"""

from pydantic import BaseModel, Field


class SkillSection(BaseModel):
    """A grouped category of technical skills (e.g., 'Platform & Cloud')."""

    category: str = Field(
        description="Skill category name, e.g. 'Platform & Cloud', 'AI/ML', 'Backend'."
    )
    skills: list[str] = Field(
        description=(
            "Individual skills within this category, ordered by relevance to the target role."
        )
    )


class WorkExperience(BaseModel):
    """A single work experience entry with achievements reordered for relevance."""

    company: str = Field(description="Company name exactly as it appears on the original resume.")
    title: str = Field(description="Job title exactly as it appears on the original resume.")
    period: str = Field(description="Employment period, e.g. '2019 - Present'.")
    achievements: list[str] = Field(
        description=(
            "Achievement bullet points from the original resume, reordered so the most "
            "relevant to the target role appear first.  Do NOT invent new achievements -- "
            "only reorder existing ones."
        ),
    )


class TailoredResume(BaseModel):
    """Structured output for a resume tailored to a specific job posting.

    The LLM reorders skills and achievements to maximize relevance, adjusts the
    professional summary, but does NOT fabricate experience or qualifications.
    """

    professional_summary: str = Field(
        description=(
            "A 3-4 sentence professional summary tailored to the target role.  "
            "Highlight the most relevant experience, skills, and differentiators.  "
            "Include quantified achievements where possible."
        ),
    )
    technical_skills: list[SkillSection] = Field(
        description=(
            "Technical skills grouped by category, reordered so the categories and "
            "individual skills most relevant to the target role appear first."
        ),
    )
    work_experience: list[WorkExperience] = Field(
        description=(
            "Work experience entries in reverse chronological order.  "
            "Achievements within each entry are reordered by relevance to the target role."
        ),
    )
    key_projects: list[str] = Field(
        description=(
            "Selected project highlights most relevant to the target role.  "
            "Each entry is a concise one-liner with project name and key impact."
        ),
    )
    education: str = Field(description="Education section text, unchanged from original resume.")
    tailoring_notes: str = Field(
        description=(
            "Brief explanation of what was changed and why -- which skills were "
            "prioritized, which achievements were promoted, and how the summary "
            "was adjusted for this specific role."
        ),
    )


class CoverLetter(BaseModel):
    """Structured output for a cover letter generated for a specific job posting.

    Produces a professional, one-page cover letter with clear paragraphs that
    connect the candidate's experience to the role requirements.
    """

    greeting: str = Field(
        description=(
            "Professional greeting line, e.g. 'Dear Hiring Manager,' or "
            "'Dear [Company] Engineering Team,'.  Use company name when known."
        ),
    )
    opening_paragraph: str = Field(
        description=(
            "Opening paragraph expressing specific interest in the role and company.  "
            "Mention the exact job title and one compelling reason for interest."
        ),
    )
    body_paragraphs: list[str] = Field(
        description=(
            "2-3 body paragraphs.  Each highlights a relevant achievement with metrics, "
            "connects experience to a specific job requirement, and demonstrates "
            "domain knowledge.  Mention open-source contributions (LangFlow, Kubert) "
            "or content creation (YouTube, blogs) when relevant."
        ),
    )
    closing_paragraph: str = Field(
        description=(
            "Closing paragraph reiterating enthusiasm, summarizing fit, and "
            "including a call to action (e.g., 'I would welcome the opportunity "
            "to discuss...')."
        ),
    )
    sign_off: str = Field(description="Professional sign-off, e.g. 'Sincerely,\\nPatryk Golabek'.")
