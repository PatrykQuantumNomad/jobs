# Phase 17: AI Scoring - Research

**Researched:** 2026-02-11
**Domain:** AI-powered semantic job-fit scoring via Claude CLI, SQLite schema migration, htmx interactive UI
**Confidence:** HIGH

## Summary

Phase 17 adds an on-demand "AI Rescore" feature to the job detail page. When the user clicks a button, the system sends the full job description and candidate resume text to Claude CLI via the `claude_cli.run()` wrapper built in Phase 16, receives a structured AI score (1-5) with reasoning, strengths, and gaps, stores it in new database columns, and displays it alongside the existing keyword-based score.

This is a well-scoped phase because all the hard infrastructure already exists: the `claude_cli` package handles subprocess execution, error handling, and structured output parsing. The `resume_ai/extractor.py` handles PDF-to-text extraction. The `webapp/db.py` has a proven migration system. The `job_detail.html` template has an established pattern for htmx-powered buttons (see "Tailor Resume" and "Generate Cover Letter" buttons). This phase needs: (1) a new Pydantic model for AI score output, (2) an async scorer function using `claude_cli.run()`, (3) a database migration adding AI score columns, (4) a db function to store/retrieve AI scores, (5) a FastAPI endpoint wiring it together, and (6) a template update showing the button and results.

The pattern is nearly identical to `resume_ai/tailor.py` -- define a Pydantic output model, write a system prompt, call `cli_run()`, catch `CLIError` and wrap in `RuntimeError`. The key difference is that AI scoring needs to persist results to the database (new columns on the `jobs` table, per prior decision), whereas resume tailoring writes to the filesystem.

**Primary recommendation:** Follow the exact `resume_ai/tailor.py` pattern -- new Pydantic model, system prompt, async function calling `cli_run()`, `CLIError -> RuntimeError` wrapping. Add three columns to jobs table (`ai_score INTEGER`, `ai_score_breakdown TEXT`, `ai_scored_at TEXT`) via migration version 7. Wire into webapp with htmx POST button targeting a result div, same pattern as the existing "Tailor Resume" button.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| claude_cli (internal) | Phase 16 | Subprocess wrapper for Claude CLI with structured output | Already built and tested, handles all error paths |
| pydantic | >=2.0.0 | Define AIScoreResult model for structured CLI output | Project standard for all domain models |
| sqlite3 (stdlib) | Python 3.14 | Store AI score results in existing jobs table | Project database layer |
| FastAPI | >=0.115.0 | POST endpoint for AI rescore trigger | Project web framework |
| Jinja2 | >=3.1.0 | Template partial for AI score display | Project template engine |
| htmx | 2.0.4 (CDN) | Button click triggers async scoring, swaps result HTML | Already loaded in base.html |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pymupdf4llm | >=0.2.9 | Extract resume text from PDF for AI context | When building the prompt with resume text |
| json (stdlib) | Python 3.14 | Serialize AI score breakdown for storage | Storing structured data in TEXT column |
| logging (stdlib) | Python 3.14 | Log AI scoring calls and errors | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New columns on jobs table | Separate ai_scores table | Prior decision: new columns on jobs table (simpler queries, no JOINs) |
| Synchronous scoring | Batch scoring queue | Deferred to v2+ (EHAI-01). Single job on-demand is the v1.2 scope |
| Full resume text in prompt | Summary/excerpt only | Full text gives better semantic analysis; token cost is acceptable for on-demand |

**Installation:**
No new packages needed. All functionality uses existing dependencies + stdlib.

## Architecture Patterns

### Recommended Project Structure
```
scorer_ai/                      # New package (mirrors resume_ai/ naming convention)
    __init__.py                 # Public API: score_job_ai()
    models.py                   # AIScoreResult Pydantic model
    scorer.py                   # Async scoring function using claude_cli.run()

webapp/
    db.py                       # Migration v7 + update_ai_score() + get AI score in get_job()
    app.py                      # POST endpoint /jobs/{key}/ai-rescore
    templates/
        partials/
            ai_score_result.html  # htmx partial for AI score display
        job_detail.html           # Add AI Rescore button + AI score display section
```

**Alternative structure (simpler):** Place the scorer module directly alongside the existing `scorer.py`:
```
ai_scorer.py                    # Single module (no package needed -- it's just one function + model)
```

**Recommendation:** Use a single `ai_scorer.py` file at the project root level, matching the existing `scorer.py` pattern. The AI scoring feature is small enough (one model, one function, one system prompt) that a full package is overengineering. If it grows later, it can be promoted to a package.

### Pattern 1: Async AI Scorer Function (following resume_ai/tailor.py)
**What:** An async function that takes job description + resume text, calls `claude_cli.run()` with a Pydantic output model, and returns the validated result.
**When to use:** When the user clicks "AI Rescore" on the job detail page.
**Example:**
```python
# Source: Pattern from resume_ai/tailor.py (verified in codebase)
from claude_cli import run as cli_run
from claude_cli.exceptions import CLIError
from pydantic import BaseModel, Field

class AIScoreResult(BaseModel):
    """Structured output from AI job-fit analysis."""
    score: int = Field(ge=1, le=5, description="Job fit score 1-5")
    reasoning: str = Field(description="2-3 sentence explanation of the score")
    strengths: list[str] = Field(description="Matched strengths between candidate and role")
    gaps: list[str] = Field(description="Skill or experience gaps for this role")

SYSTEM_PROMPT = """\
You are an expert job-fit analyst. Score how well the candidate matches ...
"""

async def score_job_ai(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = "sonnet",
) -> AIScoreResult:
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
```

### Pattern 2: Database Migration (following existing MIGRATIONS dict)
**What:** Add AI score columns to the jobs table via migration version 7.
**When to use:** On application startup, `init_db()` -> `migrate_db()` runs automatically.
**Example:**
```python
# Source: Pattern from webapp/db.py MIGRATIONS dict (verified in codebase)
# Add to MIGRATIONS dict, increment SCHEMA_VERSION to 7
7: [
    "ALTER TABLE jobs ADD COLUMN ai_score INTEGER",
    "ALTER TABLE jobs ADD COLUMN ai_score_breakdown TEXT",
    "ALTER TABLE jobs ADD COLUMN ai_scored_at TEXT",
],
```

### Pattern 3: htmx POST Button with Loading Indicator
**What:** Button that sends a POST request, shows a spinner, and swaps the result into a target div.
**When to use:** For the "AI Rescore" button on the job detail page.
**Example:**
```html
<!-- Source: Pattern from job_detail.html "Tailor Resume" button (verified in codebase) -->
<button hx-post="/jobs/{{ job.dedup_key | urlencode }}/ai-rescore"
        hx-target="#ai-score-result"
        hx-swap="innerHTML"
        hx-indicator="#ai-score-spinner"
        class="w-full bg-amber-600 text-white px-4 py-2 rounded text-sm hover:bg-amber-700">
    AI Rescore
</button>
<div id="ai-score-spinner" class="htmx-indicator text-center py-4">
    <span class="text-sm text-gray-500">Analyzing job fit... this may take 10-15 seconds</span>
</div>
<div id="ai-score-result"></div>
```

### Pattern 4: Webapp Endpoint (following tailor_resume_endpoint)
**What:** A POST endpoint that loads the job, extracts resume text, calls the AI scorer, stores results, and returns an htmx partial.
**When to use:** Handles the AI Rescore button click.
**Example:**
```python
# Source: Pattern from webapp/app.py tailor_resume_endpoint (verified in codebase)
@app.post("/jobs/{dedup_key:path}/ai-rescore", response_class=HTMLResponse)
async def ai_rescore_endpoint(request: Request, dedup_key: str):
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)
    try:
        # Lazy imports (same pattern as tailor_resume_endpoint)
        from ai_scorer import score_job_ai
        from resume_ai.extractor import extract_resume_text
        # ... extract resume, call score_job_ai, store result, return partial
    except Exception as exc:
        logger.exception("AI scoring failed for %s", dedup_key)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-400 text-red-800 px-4 py-3 rounded">'
            f'<p class="font-bold">Error</p>'
            f'<p class="text-sm">{exc}</p>'
            f'</div>'
        )
```

### Anti-Patterns to Avoid
- **Running AI scoring on pipeline import:** AI scoring is expensive and on-demand only. Never auto-score during the discovery pipeline (per Out of Scope: "Auto-rescore on import -- Too expensive for bulk pipeline").
- **Replacing the keyword score:** AI score is SEPARATE from the rule-based score. Never overwrite `jobs.score` or `jobs.score_breakdown`. The AI score has its own columns.
- **Blocking the event loop:** The `claude_cli.run()` call is already async (uses `asyncio.create_subprocess_exec`). Never wrap it in `asyncio.to_thread`.
- **Not handling missing resume:** If the resume PDF does not exist or is unreadable, return a clear error rather than crashing. Check before calling the CLI.
- **Storing raw LLM output as the score:** Always validate through the Pydantic model (AIScoreResult) before storing. The `claude_cli.run()` already does this via `model_validate()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI subprocess management | Custom subprocess code | `claude_cli.run()` | Already built, handles timeout/auth/retry/parsing |
| JSON Schema for AI output | Manual dict construction | `AIScoreResult.model_json_schema()` | Pydantic generates correct schema automatically |
| Resume PDF extraction | Custom PDF parser | `resume_ai.extractor.extract_resume_text()` | Already handles pymupdf4llm, FileNotFoundError |
| Database migration | Manual ALTER TABLE scripts | Add to `webapp/db.py` MIGRATIONS dict | Existing migration system handles idempotency |
| Loading indicator UX | Custom JavaScript spinner | htmx `hx-indicator` attribute | Already used by Tailor Resume and Cover Letter buttons |
| Error display | Custom error handling UI | Same HTML error div pattern used by tailor_resume_endpoint | Consistent UX, proven pattern |

**Key insight:** Every building block already exists in the codebase. This phase is primarily wiring existing components together with a new Pydantic model and system prompt.

## Common Pitfalls

### Pitfall 1: Endpoint Ordering in FastAPI (Catch-All Route Conflict)
**What goes wrong:** The new `/jobs/{dedup_key:path}/ai-rescore` POST endpoint gets swallowed by the existing catch-all `GET /jobs/{dedup_key:path}` route if registered after it.
**Why it happens:** FastAPI routes with `:path` converters are greedy. POST vs GET method difference helps, but the endpoint MUST be registered BEFORE the catch-all GET route (line 578 in current `app.py`).
**How to avoid:** Register the AI rescore endpoint in the same block as the other pre-catch-all endpoints (tailor-resume, cover-letter, apply). The existing code already has a comment: "Resume AI endpoints (must be registered BEFORE the catch-all /jobs/{path} GET)".
**Warning signs:** 404 errors when clicking the AI Rescore button, or the job detail page loading instead of the scoring action.

### Pitfall 2: Score Validation Range Mismatch
**What goes wrong:** The AI returns a score outside 1-5, or the Pydantic model allows 0, causing inconsistency with the keyword scorer's 1-5 range.
**Why it happens:** The LLM might generate 0 for a poor match. The existing `Job.score` field has `Field(ge=1, le=5)`.
**How to avoid:** Define `score: int = Field(ge=1, le=5)` on the Pydantic output model. The CLI's `--json-schema` validation will enforce this. Also add clear instructions in the system prompt: "Score MUST be between 1 and 5 inclusive."
**Warning signs:** Pydantic `ValidationError` during CLI response parsing.

### Pitfall 3: Missing Job Description
**What goes wrong:** Some jobs have empty descriptions (scraping failed to load the full page, or the job is from RemoteOK with minimal info).
**Why it happens:** Not all jobs have complete descriptions scraped.
**How to avoid:** Check `job["description"]` before calling the AI scorer. If empty or very short (<50 chars), return an error to the user: "Job description is too short for AI analysis. Try refreshing the job listing first."
**Warning signs:** AI returns a meaningless score because it had no description to analyze.

### Pitfall 4: Resume Path Resolution
**What goes wrong:** The candidate resume path from config doesn't exist, or the default path is wrong.
**Why it happens:** Config comes from `.env` or defaults. The PDF might not be in the expected location.
**How to avoid:** Use the same try/except pattern from `tailor_resume_endpoint` (lines 265-272 in app.py) for resolving the resume path. Call `extract_resume_text()` which raises `FileNotFoundError` on missing PDF.
**Warning signs:** `FileNotFoundError` on clicking AI Rescore.

### Pitfall 5: Re-scoring Overwrites Previous AI Score Without Warning
**What goes wrong:** User clicks "AI Rescore" multiple times. Each click overwrites the previous AI score silently.
**Why it happens:** The UPDATE query replaces the existing ai_score columns.
**How to avoid:** This is acceptable behavior for v1.2 (single score column, not versioned). Log the activity so the user can see in the timeline when rescoring happened. Optionally, if an AI score already exists, show the existing score and provide "Rescore" as the button text instead of "AI Rescore".
**Warning signs:** User confusion about why scores changed.

### Pitfall 6: Timeout on Long Job Descriptions
**What goes wrong:** Very long job descriptions (10K+ characters) combined with resume text exceed normal response times.
**Why it happens:** The combined prompt (resume + description + system prompt) can be large. Claude's response time scales with input+output tokens.
**How to avoid:** Use a reasonable timeout (120s is the default in `claude_cli.run()`). This should be sufficient. If needed, truncate very long descriptions to first 8000 characters. The system prompt should instruct Claude to focus on key requirements.
**Warning signs:** `CLITimeoutError` for certain jobs with very long descriptions.

### Pitfall 7: PEP 695 Type Parameter Syntax Required
**What goes wrong:** Using old-style generic syntax (`list[str]` is fine, but type parameters on functions need PEP 695 syntax) causes ruff UP047 violations.
**Why it happens:** `target-version = "py314"` in ruff config enables UP047 which requires PEP 695 type parameter syntax.
**How to avoid:** This is not actually a concern for this phase since we're not writing generic functions with type parameters. The Pydantic models use standard `list[str]` which is fine. Only `claude_cli/client.py` uses `def run[T: BaseModel]()` syntax (PEP 695). The AI scorer function returns a concrete type, not a generic.
**Warning signs:** Ruff lint failures on type syntax.

## Code Examples

Verified patterns from the existing codebase:

### AIScoreResult Pydantic Model
```python
# Pattern: resume_ai/models.py (verified in codebase)
from pydantic import BaseModel, Field

class AIScoreResult(BaseModel):
    """Structured output from Claude CLI for semantic job-fit analysis.

    The LLM evaluates the candidate's resume against a job description
    and produces a holistic score with detailed reasoning.
    """

    score: int = Field(
        ge=1,
        le=5,
        description=(
            "Overall job-fit score from 1 (poor match) to 5 (excellent match). "
            "Consider skills alignment, experience level, domain relevance, "
            "and location/remote compatibility."
        ),
    )
    reasoning: str = Field(
        description=(
            "2-3 sentence explanation of why this score was assigned. "
            "Reference specific skills, experience, or requirements that "
            "influenced the score."
        ),
    )
    strengths: list[str] = Field(
        description=(
            "3-5 specific strengths where the candidate matches or exceeds "
            "the role requirements. Each item should reference a concrete "
            "skill, technology, or experience from the resume."
        ),
    )
    gaps: list[str] = Field(
        description=(
            "0-5 specific gaps where the candidate's resume does not match "
            "the role requirements. Each item should reference a specific "
            "requirement from the job description. Empty list if no gaps."
        ),
    )
```

### Database Update Function
```python
# Pattern: webapp/db.py update_job_status (verified in codebase)
import json
from datetime import datetime

def update_ai_score(dedup_key: str, score: int, breakdown: dict) -> None:
    """Store AI score results for a job."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE jobs
               SET ai_score = ?, ai_score_breakdown = ?, ai_scored_at = ?, updated_at = ?
               WHERE dedup_key = ?""",
            (score, json.dumps(breakdown), now, now, dedup_key),
        )
    log_activity(dedup_key, "ai_scored", new_value=str(score))
```

### System Prompt for AI Scoring
```python
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
```

### htmx Partial for AI Score Display
```html
<!-- Pattern: webapp/templates/partials/resume_diff.html (verified in codebase) -->
<div class="bg-blue-50 border border-blue-300 rounded-lg p-4">
    <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-blue-900">AI Analysis</h3>
        <span class="text-2xl score-{{ score }}">{{ score }}</span>
    </div>
    <p class="text-sm text-gray-700 mb-3">{{ reasoning }}</p>
    {% if strengths %}
    <div class="mb-2">
        <p class="text-xs font-semibold text-green-700 mb-1">Strengths</p>
        <ul class="text-xs text-gray-600 list-disc list-inside">
            {% for s in strengths %}
            <li>{{ s }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
    {% if gaps %}
    <div>
        <p class="text-xs font-semibold text-red-700 mb-1">Gaps</p>
        <ul class="text-xs text-gray-600 list-disc list-inside">
            {% for g in gaps %}
            <li>{{ g }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
    <p class="text-xs text-gray-400 mt-2">Scored at {{ scored_at }}</p>
</div>
```

### Displaying Persisted AI Score on Page Load
```html
<!-- In job_detail.html, show existing AI score if present -->
{% if job.ai_score %}
{% set ai_bd = job.ai_score_breakdown | parse_json %}
<div class="bg-blue-50 border border-blue-300 rounded-lg p-4">
    <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-blue-900">AI Analysis</h3>
        <span class="text-2xl score-{{ job.ai_score }}">{{ job.ai_score }}</span>
    </div>
    <p class="text-sm text-gray-700 mb-3">{{ ai_bd.reasoning }}</p>
    <!-- strengths and gaps from ai_bd -->
    <p class="text-xs text-gray-400 mt-2">Scored {{ job.ai_scored_at }}</p>
</div>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based scoring only (scorer.py) | Rule-based + on-demand AI scoring | Phase 17 (this phase) | Semantic understanding of job fit, catches keyword misses |
| Score stored as single `score` column | Keyword score in `score`, AI score in `ai_score` | Phase 17 (this phase) | Two independent scoring dimensions |
| No AI in scoring pipeline | Claude CLI for semantic analysis | Phase 17 (this phase) | Better match quality for individual job review |

**Deprecated/outdated:**
- Nothing deprecated in this phase. The keyword scorer remains the primary scoring mechanism for bulk pipeline runs. AI scoring supplements it for on-demand deep analysis.

## File Change Map

### New Files
| File | Purpose |
|------|---------|
| `ai_scorer.py` | Pydantic model (AIScoreResult) + system prompt + async `score_job_ai()` function |
| `webapp/templates/partials/ai_score_result.html` | htmx partial showing AI score, reasoning, strengths, gaps |
| `tests/test_ai_scorer.py` | Unit tests for the AI scorer module |

### Modified Files
| File | Change |
|------|--------|
| `webapp/db.py` | Migration v7 (ai_score, ai_score_breakdown, ai_scored_at columns), `update_ai_score()` function, increment SCHEMA_VERSION |
| `webapp/app.py` | POST `/jobs/{key}/ai-rescore` endpoint (before catch-all GET), lazy imports |
| `webapp/templates/job_detail.html` | AI Rescore button + AI score display section (persisted + live) |

### Unchanged Files (context only)
| File | Why Referenced |
|------|---------------|
| `claude_cli/client.py` | Called by `ai_scorer.py` -- no changes needed |
| `resume_ai/extractor.py` | Used to extract resume text -- no changes needed |
| `scorer.py` | Existing keyword scorer -- NOT modified, AI score is separate |
| `config.py` | Used to resolve resume path -- no changes needed |

## Open Questions

1. **System prompt calibration**
   - What we know: The prompt should produce consistent 1-5 scores with detailed reasoning.
   - What's unclear: Whether the prompt wording produces well-calibrated scores (not too generous, not too harsh). This can only be validated with real job descriptions.
   - Recommendation: Start with the proposed prompt. Can be tuned based on real usage without code changes (just edit the prompt string).

2. **AI score display location on job detail page**
   - What we know: It should be "alongside" the keyword score per requirements.
   - What's unclear: Best UX placement -- in the header next to the keyword score? In a separate sidebar card? Below the score breakdown?
   - Recommendation: New sidebar card in the sidebar column, placed between the "AI Resume Tools" card and the "Apply" card. This groups AI features together and keeps the header focused on the keyword score. The AI score card shows both the button (or existing score) and the results.

3. **Token cost per AI rescore**
   - What we know: Resume text is typically 1-2K tokens, job descriptions 500-2K tokens, system prompt ~300 tokens. Output is ~200-500 tokens. Total ~3-5K tokens per call.
   - What's unclear: Exact cost at current pricing. Estimated at ~$0.01-0.03 per rescore with Sonnet.
   - Recommendation: Acceptable for on-demand use. The CLI envelope includes `total_cost_usd` which is logged but not displayed (deferred to EHAI-05).

## Sources

### Primary (HIGH confidence)
- `claude_cli/client.py` -- verified async subprocess wrapper with structured output
- `claude_cli/parser.py` -- verified resilient JSON parser
- `claude_cli/exceptions.py` -- verified typed exception hierarchy
- `resume_ai/tailor.py` -- verified async pattern with CLIError -> RuntimeError wrapping
- `resume_ai/models.py` -- verified Pydantic model pattern with Field descriptions
- `webapp/db.py` -- verified migration system (MIGRATIONS dict, SCHEMA_VERSION, idempotent ALTER TABLE)
- `webapp/app.py` -- verified endpoint patterns (lazy imports, htmx partials, error handling)
- `webapp/templates/job_detail.html` -- verified htmx button/indicator/result pattern
- `tests/resume_ai/conftest.py` -- verified mock_claude_cli fixture pattern
- `scorer.py` -- verified existing keyword scoring (ScoreBreakdown, 1-5 range)

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- SCR-01, SCR-02, SCR-03 requirement definitions
- `.planning/STATE.md` -- Prior decisions about AI score storage (columns on jobs table)
- `.planning/phases/16-cli-wrapper-foundation/16-RESEARCH.md` -- CLI behavior, pitfalls

### Tertiary (LOW confidence)
- System prompt calibration -- untested against real job descriptions, will need tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 100% existing dependencies, no new packages
- Architecture: HIGH -- follows established patterns from resume_ai and webapp
- Database migration: HIGH -- follows exact pattern of migrations 2-6
- Pitfalls: HIGH -- based on verified codebase patterns and known issues
- System prompt quality: MEDIUM -- reasonable prompt but uncalibrated against real data

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable; all patterns from existing codebase)
