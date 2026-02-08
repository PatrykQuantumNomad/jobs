"""Post-generation anti-fabrication validation (Layer 3).

Compares entities extracted from a tailored resume against the original to
detect any fabricated companies, skills, or metrics that the LLM may have
introduced despite system prompt constraints.
"""

import re

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Validation result model
# ---------------------------------------------------------------------------


class ValidationResult(BaseModel):
    """Result of comparing a tailored document against the original resume."""

    is_valid: bool = Field(description="True if no fabricated entities were detected.")
    new_companies: list[str] = Field(
        default_factory=list,
        description="Company names found in tailored output but not in original.",
    )
    new_skills: list[str] = Field(
        default_factory=list,
        description="Technology/skill terms found in tailored output but not in original.",
    )
    new_metrics: list[str] = Field(
        default_factory=list,
        description="Numeric metrics found in tailored output but not in original.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Human-readable warning messages for each detected fabrication.",
    )


# ---------------------------------------------------------------------------
# Known tech keywords for skill extraction
# ---------------------------------------------------------------------------

_TECH_KEYWORDS: set[str] = {
    # Cloud & infrastructure
    "kubernetes",
    "k8s",
    "docker",
    "aws",
    "gcp",
    "azure",
    "terraform",
    "terragrunt",
    "atlantis",
    "helm",
    "devspace",
    "calico",
    "linkerd",
    "gke",
    "eks",
    "aks",
    "lambda",
    "sqs",
    "ec2",
    "s3",
    "cloudformation",
    "pulumi",
    "vagrant",
    "ansible",
    "chef",
    "puppet",
    # AI/ML
    "langraph",
    "langchain",
    "langflow",
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "crawl4ai",
    "tensorflow",
    "keras",
    "pytorch",
    "scikit-learn",
    "huggingface",
    "rag",
    "llm",
    "cnn",
    "lstm",
    "bert",
    "gpt",
    # Data
    "airflow",
    "postgresql",
    "postgres",
    "redis",
    "elasticsearch",
    "kafka",
    "mongodb",
    "mysql",
    "sqlite",
    "cassandra",
    "dynamodb",
    "bigquery",
    "snowflake",
    "spark",
    "hadoop",
    "flink",
    # Backend
    "python",
    "fastapi",
    "flask",
    "django",
    "celery",
    "sqlalchemy",
    "java",
    "spring",
    "go",
    "golang",
    "typescript",
    "javascript",
    "node",
    "express",
    "rust",
    "ruby",
    "rails",
    "php",
    "laravel",
    "scala",
    # DevSecOps
    "gitops",
    "github",
    "gitlab",
    "jenkins",
    "circleci",
    "prometheus",
    "grafana",
    "loki",
    "falco",
    "vault",
    "keycloak",
    "datadog",
    "newrelic",
    "splunk",
    "pagerduty",
    "bats",
    "pytest",
    "testcontainers",
    # Frontend
    "react",
    "nextjs",
    "angular",
    "vue",
    "svelte",
    "tailwindcss",
    "webpack",
    "vite",
    "storybook",
    # Misc
    "graphql",
    "grpc",
    "rest",
    "oauth",
    "saml",
    "sso",
    "ci/cd",
    "microservices",
    "etl",
    "iot",
    "blockchain",
}


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Lowercase and strip whitespace for comparison."""
    return text.strip().lower()


def _extract_entities(text: str) -> dict[str, set[str]]:
    """Extract companies, tech skills, and metrics from text.

    Parameters
    ----------
    text:
        Plain text to extract entities from.

    Returns
    -------
    dict
        Keys: ``"companies"``, ``"skills"``, ``"metrics"`` -- each a set of
        normalized (lowercased) strings.
    """
    lower_text = text.lower()

    # --- Companies ---
    companies: set[str] = set()

    # Common English words that start sentences but are not company names.
    # Used to filter false positives from capitalized-word patterns.
    _STOP_WORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "can",
        "could",
        "i",
        "my",
        "me",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "it",
        "they",
        "them",
        "their",
        "this",
        "that",
        "these",
        "those",
        "using",
        "including",
        "such",
        "also",
        "each",
        "every",
        "all",
        "both",
        "any",
        "some",
        "no",
        "not",
        "only",
        "into",
        "about",
        "after",
        "before",
        "between",
        "through",
        "during",
        "under",
        "above",
        "led",
        "built",
        "managed",
        "developed",
        "created",
        "designed",
        "implemented",
        "achieved",
        "delivered",
        "established",
        "maintained",
        "supported",
        "worked",
        "focused",
        "responsible",
    }

    def _is_stop_word(word: str) -> bool:
        return word.lower() in _STOP_WORDS

    # Capitalized multi-word sequences (2+ words starting with uppercase).
    # Filter out sequences where the first word is a common English word.
    company_pattern = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b")
    for match in company_pattern.finditer(text):
        words = match.group(0).split()
        # Keep only if the first word is not a stop word
        if not _is_stop_word(words[0]):
            companies.add(_normalize(match.group(0)))

    # Words/phrases following "at " or "for " (common company reference patterns).
    # Only capture words that start with uppercase (proper nouns = company names).
    at_for_pattern = re.compile(r"(?i:at|for)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)")
    for match in at_for_pattern.finditer(text):
        captured = match.group(1).strip()
        # Filter: first word must not be a stop word
        if captured and not _is_stop_word(captured.split()[0]):
            companies.add(_normalize(captured))

    # --- Skills ---
    skills: set[str] = set()
    # Match known tech keywords
    for keyword in _TECH_KEYWORDS:
        # Word-boundary match on the lowercased text
        if re.search(r"\b" + re.escape(keyword) + r"\b", lower_text):
            skills.add(keyword)

    # CamelCase terms (e.g., LangGraph, FastAPI) -- extract and normalize
    camel_pattern = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b")
    for match in camel_pattern.finditer(text):
        skills.add(_normalize(match.group(0)))

    # ALL_CAPS terms (acronyms like GKE, EKS, AWS) -- 2+ uppercase letters
    caps_pattern = re.compile(r"\b([A-Z]{2,})\b")
    for match in caps_pattern.finditer(text):
        skills.add(_normalize(match.group(0)))

    # --- Metrics ---
    metrics: set[str] = set()

    # Percentages: 50%, 200%
    for match in re.finditer(r"\d+(?:\.\d+)?%", text):
        metrics.add(match.group(0))

    # Dollar amounts: $1.2M, $200,000, $175000
    for match in re.finditer(r"\$[\d,]+(?:\.\d+)?[MmKkBb]?", text):
        metrics.add(_normalize(match.group(0)))

    # USD amounts: USD 224,400.00
    for match in re.finditer(r"USD\s*[\d,]+(?:\.\d+)?", text, re.IGNORECASE):
        metrics.add(_normalize(match.group(0)))

    # Multipliers: 10x, 3x
    for match in re.finditer(r"\b\d+x\b", text, re.IGNORECASE):
        metrics.add(_normalize(match.group(0)))

    # Large standalone numbers (3+ digits) -- likely metrics
    for match in re.finditer(r"\b(\d{3,}(?:,\d{3})*)\b", text):
        metrics.add(match.group(0).replace(",", ""))

    return {
        "companies": companies,
        "skills": skills,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Public validation function
# ---------------------------------------------------------------------------


def validate_no_fabrication(
    original_text: str,
    tailored_text: str,
) -> ValidationResult:
    """Compare entities in tailored output against the original resume.

    Extracts companies, skills/technologies, and numeric metrics from both
    texts and flags any entities that appear in the tailored version but not
    in the original.

    Parameters
    ----------
    original_text:
        The original resume text (before tailoring).
    tailored_text:
        The tailored resume or cover letter text (after LLM processing).

    Returns
    -------
    ValidationResult
        Contains lists of any fabricated entities and human-readable warnings.
    """
    original_entities = _extract_entities(original_text)
    tailored_entities = _extract_entities(tailored_text)

    new_companies = sorted(tailored_entities["companies"] - original_entities["companies"])
    new_skills = sorted(tailored_entities["skills"] - original_entities["skills"])
    new_metrics = sorted(tailored_entities["metrics"] - original_entities["metrics"])

    warnings: list[str] = []
    for company in new_companies:
        warnings.append(f"New company detected: '{company}' not found in original resume")
    for skill in new_skills:
        warnings.append(f"New skill/technology detected: '{skill}' not found in original resume")
    for metric in new_metrics:
        warnings.append(f"New metric detected: '{metric}' not found in original resume")

    is_valid = len(new_companies) == 0 and len(new_skills) == 0 and len(new_metrics) == 0

    return ValidationResult(
        is_valid=is_valid,
        new_companies=new_companies,
        new_skills=new_skills,
        new_metrics=new_metrics,
        warnings=warnings,
    )
