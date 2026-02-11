"""AI job-fit scorer via Claude CLI structured outputs.

Uses the ``claude_cli.run()`` async subprocess wrapper to produce an
:class:`AIScoreResult` with a calibrated 1-5 score, reasoning, matched
strengths, and identified gaps for a candidate resume against a job posting.
"""

from pydantic import BaseModel, Field

from claude_cli import run as cli_run
from claude_cli.exceptions import CLIError

# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class AIScoreResult(BaseModel):
    """Structured AI scoring result returned by Claude CLI.

    The field descriptions become the JSON schema that guides the LLM,
    so they are intentionally detailed and prescriptive.
    """

    score: int = Field(
        ge=1,
        le=5,
        description=(
            "Overall job-fit score from 1 (poor match) to 5 (excellent match) "
            "based on how well the candidate's resume aligns with the job requirements."
        ),
    )
    reasoning: str = Field(
        description=(
            "2-3 sentence explanation of the score, referencing specific technologies, "
            "experience levels, and domain alignment between the resume and job description."
        ),
    )
    strengths: list[str] = Field(
        description=(
            "3-5 concrete skills, technologies, or achievements from the resume that "
            "directly match job requirements. Each item must cite a specific skill or "
            "accomplishment from the resume."
        ),
    )
    gaps: list[str] = Field(
        description=(
            "0-5 specific requirements from the job description that the candidate's "
            "resume does not clearly demonstrate. Each item must cite a specific "
            "requirement from the job posting."
        ),
    )


# ---------------------------------------------------------------------------
# System prompt (scoring rubric for the LLM)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert job-fit analyst. Your task is to evaluate how well a \
candidate's resume matches a specific job description and produce a \
structured score with detailed reasoning.

SCORING RUBRIC (1-5 scale):
5 = Excellent match: Candidate meets 90%+ of requirements, has relevant \
    domain experience, and brings additional valuable skills.
4 = Strong match: Candidate meets 70-90% of requirements with relevant \
    experience in the domain.
3 = Moderate match: Candidate meets 50-70% of requirements. Some relevant \
    skills but notable gaps.
2 = Weak match: Candidate meets 30-50% of requirements. Significant skill \
    or experience gaps.
1 = Poor match: Candidate meets <30% of requirements. Major misalignment \
    in skills, experience, or domain.

EVALUATION CRITERIA:
- Technical skills alignment (languages, frameworks, tools, cloud platforms)
- Experience level match (years, seniority, leadership scope)
- Domain relevance (industry, problem space, scale of systems)
- Location/remote compatibility
- Soft skills and cultural indicators

IMPORTANT RULES:
1. Be honest and calibrated. Do not inflate scores.
2. Reference specific technologies and requirements in your reasoning.
3. Each strength must cite a concrete skill or achievement from the resume.
4. Each gap must cite a specific requirement from the job description.
5. Score MUST be between 1 and 5 inclusive.\
"""

# Default model alias for AI scoring (CLI uses short aliases)
DEFAULT_MODEL = "sonnet"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_job_ai(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = DEFAULT_MODEL,
) -> AIScoreResult:
    """Score a job posting against a candidate resume using Claude CLI structured outputs.

    Parameters
    ----------
    resume_text:
        The full text of the candidate's resume (Markdown or plain text).
    job_description:
        The full job description / posting text.
    job_title:
        The target job title (e.g., "Senior Platform Engineer").
    company_name:
        The hiring company name.
    model:
        Claude CLI model alias.  Defaults to 'sonnet'.

    Returns
    -------
    AIScoreResult
        Structured scoring output with score (1-5), reasoning, strengths, and gaps.

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
            output_model=AIScoreResult,
            model=model,
        )
    except CLIError as exc:
        raise RuntimeError(f"AI scoring failed: {exc}") from exc
