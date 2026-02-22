"""Interview question generation via Claude CLI structured outputs.

Uses the ``claude_cli.run()`` async subprocess wrapper to produce an
:class:`InterviewQuestions` result with tailored technical, behavioral,
and company-specific questions derived from a job posting.
"""

from pydantic import BaseModel, Field

from claude_cli import run as cli_run
from claude_cli.exceptions import CLIError

# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class InterviewQuestions(BaseModel):
    """Structured interview preparation result returned by Claude CLI.

    The field descriptions become the JSON schema that guides the LLM,
    so they are intentionally detailed and prescriptive.
    """

    technical_questions: list[str] = Field(
        description=(
            "5-7 technical interview questions specific to the technologies, tools, "
            "and skills mentioned in the job description. Each question should be "
            "detailed and reference a concrete technology or architecture pattern "
            "from the posting (e.g., 'How would you design a distributed caching "
            "layer for a high-throughput API?' not 'Tell me about caching')."
        ),
    )
    behavioral_questions: list[str] = Field(
        description=(
            "3-5 behavioral or situational interview questions based on the role's "
            "responsibilities and team dynamics described in the posting. Each question "
            "should reference an actual responsibility from the job description "
            "(e.g., 'Describe a time you led a cross-functional team through a "
            "critical production incident')."
        ),
    )
    company_specific_questions: list[str] = Field(
        description=(
            "2-3 thoughtful questions the candidate should ask the interviewer that "
            "demonstrate genuine research into the company, its products, and the "
            "specific role. These should go beyond generic questions and show "
            "understanding of the company's domain and challenges."
        ),
    )
    key_topics: list[str] = Field(
        description=(
            "5-8 key technical topics, technologies, or concepts the candidate "
            "should review before the interview, derived directly from the job "
            "description requirements and preferred qualifications."
        ),
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert interview coach and technical recruiter. Your task is to \
analyze a job description and generate tailored interview preparation \
materials for the candidate.

YOUR APPROACH:
1. Carefully analyze the job description for required skills, technologies, \
   responsibilities, and team dynamics.
2. Generate questions that a real interviewer at this specific company would \
   likely ask, based on the actual requirements in the posting.
3. Make technical questions specific to the stack and architecture mentioned \
   in the job description — not generic textbook questions.
4. Make behavioral questions reference the actual responsibilities and \
   challenges described in the posting.
5. Suggest candidate questions that demonstrate genuine interest and \
   understanding of the company's domain.

IMPORTANT RULES:
1. Every technical question must reference a specific technology, tool, or \
   pattern from the job description.
2. Every behavioral question must tie to a real responsibility listed in the \
   posting.
3. Candidate questions should show the interviewer that the candidate has \
   read and understood the role deeply.
4. Key topics must be directly derived from the required and preferred \
   qualifications in the posting.
5. Be practical and realistic — these should feel like real interview \
   questions, not academic exercises.\
"""

# Default model alias for interview prep (CLI uses short aliases)
DEFAULT_MODEL = "sonnet"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_interview_questions(
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = DEFAULT_MODEL,
) -> InterviewQuestions:
    """Generate tailored interview questions from a job posting using Claude CLI.

    Parameters
    ----------
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
    InterviewQuestions
        Structured interview prep with technical questions, behavioral questions,
        candidate questions to ask, and key topics to review.

    Raises
    ------
    RuntimeError
        If the Claude CLI is missing, not authenticated, or the call fails.
    """
    user_message = (
        f"## Job Description\n\n{job_description}\n\n"
        f"## Target Role\n\n"
        f"- **Job Title:** {job_title}\n"
        f"- **Company:** {company_name}\n"
    )

    try:
        return await cli_run(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            output_model=InterviewQuestions,
            model=model,
        )
    except CLIError as exc:
        raise RuntimeError(f"Interview question generation failed: {exc}") from exc
