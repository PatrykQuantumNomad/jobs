# Phase 7: AI Resume & Cover Letter - Research

**Researched:** 2026-02-07
**Domain:** LLM-powered document generation (resume tailoring, cover letters, PDF output, anti-fabrication guardrails)
**Confidence:** HIGH

## Summary

This phase adds AI-powered resume tailoring and cover letter generation to the job tracker dashboard. The core workflow is: extract text from the user's existing PDF resume, send it along with a job description to Claude via the Anthropic SDK, receive a restructured resume (reordered sections, emphasized keywords) with guaranteed JSON output via structured outputs, render the result as a professional PDF, and track all versions in SQLite.

The Anthropic Python SDK (v0.79.0) with structured outputs (`output_config.format`) is the locked LLM choice. For PDF text extraction, `pymupdf4llm` (v0.2.9) is the standard -- it extracts PDF content as Markdown, which is ideal for feeding to an LLM. For PDF generation, WeasyPrint (v68.1) combined with Jinja2 templates converts HTML/CSS to professional PDFs -- the project already uses Jinja2 for dashboard templates, so this is a natural fit. For diff visualization, Python's built-in `difflib` module provides HTML side-by-side comparison with no extra dependencies.

**Primary recommendation:** Use the Anthropic SDK's structured outputs (`client.messages.parse()` with Pydantic models) to guarantee valid JSON resume/cover letter data. Feed the structured output into Jinja2 HTML templates rendered to PDF via WeasyPrint. Use `difflib.HtmlDiff` for the diff view. Store resume version metadata in a new SQLite `resume_versions` table.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | >=0.79.0 | LLM API calls for resume tailoring and cover letter generation | Locked decision from roadmap. Supports structured outputs with Pydantic models via `client.messages.parse()` |
| `pymupdf4llm` | >=0.2.9 | Extract text from existing PDF resume as Markdown | Outputs Markdown optimized for LLM consumption. Auto-installs PyMuPDF. No system dependencies beyond Python. |
| `weasyprint` | >=68.0 | Render HTML/CSS to PDF for resume and cover letter output | Supports CSS flexbox, grid, `@page` rules, custom fonts. Produces professional print-quality PDFs. |
| `jinja2` | >=3.1.0 | HTML template rendering for resume/cover letter layout | Already in project dependencies. Same engine used for dashboard templates. |
| `difflib` | stdlib | Generate side-by-side HTML diff of original vs. tailored resume | Built-in Python module. `HtmlDiff.make_table()` produces inline HTML suitable for embedding in dashboard. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | >=2.0.0 | Define structured output schemas for LLM responses | Already in project. Use with `client.messages.parse()` for guaranteed schema compliance. |
| `python-dotenv` | >=1.0.0 | Load `ANTHROPIC_API_KEY` from `.env` | Already in project. The Anthropic client auto-reads `ANTHROPIC_API_KEY` from environment. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | fpdf2 2.8.5 | fpdf2 is pure Python (no system deps) but requires manual layout positioning. WeasyPrint leverages HTML/CSS which the team already knows from Jinja2 templates. WeasyPrint requires Pango (system dependency -- `brew install weasyprint` on macOS). |
| WeasyPrint | ReportLab | ReportLab is more powerful for complex layouts but has a steep learning curve. HTML/CSS via WeasyPrint is more maintainable and faster to iterate. |
| pymupdf4llm | pypdf | pypdf is pure Python but produces lower-quality text extraction. pymupdf4llm outputs Markdown with structure preserved, which is significantly better for LLM prompts. |
| difflib.HtmlDiff | lxml.html.diff | lxml provides semantic HTML diff but adds a heavy dependency. difflib is stdlib and sufficient for text-based resume comparison. |

**Installation:**
```bash
pip install anthropic pymupdf4llm weasyprint
# macOS system dependency:
brew install weasyprint
# OR if Pango is already installed:
brew install pango
```

## Architecture Patterns

### Recommended Project Structure
```
project-root/
├── resume_ai/
│   ├── __init__.py
│   ├── extractor.py          # PDF text extraction (pymupdf4llm)
│   ├── tailor.py             # Resume tailoring logic (Anthropic SDK)
│   ├── cover_letter.py       # Cover letter generation (Anthropic SDK)
│   ├── renderer.py           # HTML-to-PDF rendering (WeasyPrint + Jinja2)
│   ├── diff.py               # Resume diff generation (difflib)
│   ├── models.py             # Pydantic models for LLM structured output
│   └── tracker.py            # Resume version tracking (SQLite)
├── webapp/
│   └── templates/
│       ├── resume/
│       │   ├── resume_template.html    # Jinja2 template for PDF resume
│       │   └── cover_letter_template.html  # Jinja2 template for cover letter
│       └── partials/
│           └── resume_diff.html        # Diff view partial for htmx
├── resumes/
│   ├── Patryk_Golabek_Resume_ATS.pdf   # Original (source of truth)
│   └── tailored/
│       └── Patryk_Golabek_Resume_CompanyName_2026-02-07.pdf
└── .env                                # ANTHROPIC_API_KEY added here
```

### Pattern 1: Structured Output with Pydantic Models
**What:** Define the exact JSON structure the LLM must return using Pydantic models, then use `client.messages.parse()` for guaranteed schema compliance.
**When to use:** Every LLM call -- resume tailoring and cover letter generation.
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from pydantic import BaseModel
from anthropic import Anthropic

class TailoredResume(BaseModel):
    professional_summary: str
    skills_sections: list[SkillSection]
    work_experience: list[WorkExperience]
    key_projects: list[Project]
    education: str
    reasoning: str  # Why these changes were made

client = Anthropic()  # Reads ANTHROPIC_API_KEY from env

response = client.messages.parse(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    output_format=TailoredResume,
    system="You are a resume optimization expert. ...",
    messages=[
        {"role": "user", "content": f"Original resume:\n{resume_text}\n\nJob description:\n{job_desc}\n\nTailor this resume..."}
    ],
)

tailored = response.parsed_output  # TailoredResume instance
```

### Pattern 2: Anti-Fabrication Guardrail Architecture
**What:** A multi-layered approach ensuring the LLM never invents experience, skills, or qualifications.
**When to use:** Every resume tailoring call. This is the critical safety requirement (Success Criteria #2).
**Layers:**
1. **System prompt constraint:** Explicitly instruct the LLM it may ONLY reorder, emphasize, and rephrase -- never add new facts.
2. **Structured output schema:** The output schema forces the LLM to cite which original section each item came from.
3. **Post-generation validation:** Compare extracted facts from the tailored resume against the original to flag any additions.
4. **Diff view:** Show the user exactly what changed so they can verify before downloading.

### Pattern 3: Template-Based PDF Rendering
**What:** Use Jinja2 HTML templates with CSS styling, rendered to PDF via WeasyPrint.
**When to use:** Generating the final resume and cover letter PDFs.
**Example:**
```python
# Source: WeasyPrint + Jinja2 pattern from official docs
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

env = Environment(loader=FileSystemLoader("webapp/templates/resume"))
template = env.get_template("resume_template.html")

html_content = template.render(
    name="Patryk Golabek",
    summary=tailored.professional_summary,
    skills=tailored.skills_sections,
    experience=tailored.work_experience,
    projects=tailored.key_projects,
    education=tailored.education,
)

HTML(string=html_content).write_pdf("resumes/tailored/output.pdf")
```

### Pattern 4: Database-Tracked Resume Versions
**What:** Store metadata about each generated resume version in SQLite.
**When to use:** Every time a tailored resume or cover letter is generated.
**Schema:**
```sql
CREATE TABLE IF NOT EXISTS resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_dedup_key TEXT NOT NULL,
    resume_type TEXT NOT NULL,  -- 'resume' or 'cover_letter'
    file_path TEXT NOT NULL,
    original_resume_path TEXT NOT NULL,
    model_used TEXT NOT NULL,
    prompt_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (job_dedup_key) REFERENCES jobs(dedup_key)
);
```

### Anti-Patterns to Avoid
- **Generating resumes without showing a diff first:** Users MUST be able to verify no fabrication occurred before downloading. Never auto-save without review.
- **Using temperature > 0 for resume tailoring:** Higher temperature increases creativity, which for resumes means increased risk of fabrication. Use `temperature=0` or very low values.
- **Storing full LLM responses in the database:** Store only metadata (file path, model, timestamp). The PDF file itself goes to `resumes/tailored/`.
- **Hard-coding the candidate profile in prompts:** Always load from `CandidateProfile` model via `config.get_settings().build_candidate_profile()`.
- **Calling the LLM synchronously in the request handler:** Use `async` Anthropic client or run in a background thread to avoid blocking the web server.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | `pymupdf4llm.to_markdown()` | PDF parsing is extraordinarily complex (fonts, encoding, layout). pymupdf4llm handles multi-column, tables, headers. |
| PDF generation | Manual coordinate-based drawing | WeasyPrint + Jinja2 HTML | HTML/CSS is declarative, maintainable, and produces professional output. Manual positioning is error-prone and hard to iterate. |
| JSON output validation | Regex/manual JSON parsing of LLM output | Anthropic structured outputs (`output_config.format`) | Structured outputs guarantee valid JSON matching your Pydantic schema. No retry loops for malformed JSON needed. |
| Text diffing | Custom string comparison | `difflib.HtmlDiff.make_table()` | stdlib, battle-tested, produces highlighted HTML tables with intra-line change detection. |
| ATS-friendly resume formatting | Custom CSS from scratch | Proven HTML resume templates with standard section headers | ATS systems expect specific section names (PROFESSIONAL SUMMARY, WORK EXPERIENCE, etc.) and simple formatting. |

**Key insight:** The entire pipeline chains well-established tools: `pymupdf4llm` (extract) -> `Anthropic structured outputs` (transform) -> `Jinja2 + WeasyPrint` (render). Each step has a clear, well-supported library. Building any of these from scratch would be a multi-month project.

## Common Pitfalls

### Pitfall 1: LLM Fabricating Resume Content
**What goes wrong:** The LLM adds skills, experience, or metrics the candidate doesn't actually have.
**Why it happens:** LLMs naturally try to be "helpful" and may interpolate or extrapolate beyond provided facts.
**How to avoid:**
1. System prompt explicitly forbids adding any fact not in the original resume.
2. Use structured outputs so each section maps back to original content.
3. Post-generation diff shows exactly what changed.
4. Temperature set to 0 to minimize creative variance.
**Warning signs:** Diff shows additions (green text) that aren't rephrasings of existing content. New skills or company names appear.

### Pitfall 2: WeasyPrint System Dependency Issues
**What goes wrong:** `pip install weasyprint` succeeds but PDF generation fails with Pango/Cairo errors.
**Why it happens:** WeasyPrint requires Pango (a C library) for text rendering. It's not bundled with the Python package.
**How to avoid:** Run `brew install weasyprint` (or `brew install pango`) on macOS before pip install. Document this in README.
**Warning signs:** `OSError: cannot load library 'libpango-1.0'` or similar errors at runtime.

### Pitfall 3: PDF Text Extraction Losing Structure
**What goes wrong:** Extracted text from the PDF resume loses section headers, bullet points, or ordering.
**Why it happens:** PDFs store text as positioned glyphs, not semantic structure. Multi-column layouts are especially tricky.
**How to avoid:** Use `pymupdf4llm.to_markdown()` which preserves structure as Markdown. Verify extraction quality against the specific resume PDF before building the full pipeline.
**Warning signs:** Jumbled text, merged columns, missing headers in extracted output.

### Pitfall 4: Anthropic API Key Not Configured
**What goes wrong:** LLM calls fail silently or with unhelpful errors.
**Why it happens:** `ANTHROPIC_API_KEY` not added to `.env` file.
**How to avoid:** Check for the key at startup. The `Anthropic()` client reads from `ANTHROPIC_API_KEY` env var automatically. If missing, raise a clear error message. Add graceful degradation in the UI (disable "Tailor Resume" button if no API key).
**Warning signs:** `AuthenticationError` from the Anthropic SDK.

### Pitfall 5: Resume PDF Exceeding Two Pages
**What goes wrong:** Generated PDF is 3+ pages, violating the 2-page preference noted in CLAUDE.md.
**Why it happens:** LLM generates verbose content, or CSS doesn't constrain page breaks.
**How to avoid:** Include "keep to 2 pages maximum" in the system prompt. Use CSS `@page` rules with `size: letter` and test output length. Truncate or summarize if needed.
**Warning signs:** PDF file is noticeably larger than the original. `page-break` CSS rules not set.

### Pitfall 6: Blocking the Event Loop with Synchronous LLM Calls
**What goes wrong:** Dashboard becomes unresponsive while waiting for Claude API response (can take 5-15 seconds).
**Why it happens:** FastAPI is async but the default `Anthropic()` client is synchronous.
**How to avoid:** Use `anthropic.AsyncAnthropic()` client for async calls within FastAPI route handlers, OR use `asyncio.to_thread()` to wrap synchronous calls.
**Warning signs:** Other dashboard requests queue up while a tailoring request is in progress.

## Code Examples

Verified patterns from official sources:

### PDF Text Extraction
```python
# Source: https://pypi.org/project/pymupdf4llm/
import pymupdf4llm

def extract_resume_text(pdf_path: str) -> str:
    """Extract resume text as Markdown for LLM consumption."""
    md_text = pymupdf4llm.to_markdown(pdf_path)
    return md_text
```

### Resume Tailoring with Structured Output
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from pydantic import BaseModel, Field
from anthropic import Anthropic

class SkillSection(BaseModel):
    category: str = Field(description="e.g., 'Platform & Cloud', 'AI/ML'")
    skills: list[str] = Field(description="List of skills in this category")

class WorkExperience(BaseModel):
    company: str
    title: str
    period: str
    achievements: list[str] = Field(
        description="Bullet points, reordered to emphasize relevance to target job"
    )

class TailoredResume(BaseModel):
    professional_summary: str = Field(
        description="Rewritten summary emphasizing relevance to the target role"
    )
    technical_skills: list[SkillSection] = Field(
        description="Skills reordered by relevance to the job description"
    )
    work_experience: list[WorkExperience] = Field(
        description="Same companies/roles, achievements reordered by relevance"
    )
    key_projects: list[str] = Field(
        description="Project highlights, reordered by relevance"
    )
    education: str
    tailoring_notes: str = Field(
        description="Explanation of what was changed and why"
    )

SYSTEM_PROMPT = """You are a resume optimization expert. You tailor resumes to match
specific job descriptions by reordering and emphasizing existing content.

CRITICAL RULES:
1. You may ONLY use facts, skills, companies, titles, dates, and metrics that appear
   in the original resume. NEVER invent or fabricate any detail.
2. You may reorder sections, reorder bullet points within sections, and rephrase
   for clarity -- but the underlying facts must remain identical.
3. You may adjust the professional summary to emphasize relevant experience.
4. You may reorder the skills list to put the most relevant skills first.
5. You may reorder work experience bullet points to lead with the most relevant.
6. You MUST NOT add any skill, technology, company, role, metric, or achievement
   that does not appear in the original resume.
7. Keep the resume to 2 pages maximum.
8. Use standard ATS-friendly section headers: PROFESSIONAL SUMMARY, TECHNICAL SKILLS,
   WORK EXPERIENCE, KEY PROJECTS, EDUCATION.
9. Expand all acronyms from the job description on first use."""

def tailor_resume(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
) -> TailoredResume:
    client = Anthropic()
    response = client.messages.parse(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0,
        system=SYSTEM_PROMPT,
        output_format=TailoredResume,
        messages=[{
            "role": "user",
            "content": (
                f"## Original Resume\n\n{resume_text}\n\n"
                f"## Target Job\n\n"
                f"**Title:** {job_title}\n"
                f"**Company:** {company_name}\n\n"
                f"**Job Description:**\n{job_description}\n\n"
                f"Tailor this resume for the target job. Remember: ONLY use facts "
                f"from the original resume. Reorder and emphasize, never fabricate."
            ),
        }],
    )
    return response.parsed_output
```

### Cover Letter Generation
```python
# Source: Anthropic structured outputs docs
from pydantic import BaseModel, Field
from anthropic import Anthropic

class CoverLetter(BaseModel):
    greeting: str = Field(description="e.g., 'Dear Hiring Manager,'")
    opening_paragraph: str = Field(
        description="Express interest in the specific role and company"
    )
    body_paragraphs: list[str] = Field(
        description="2-3 paragraphs highlighting relevant achievements with metrics"
    )
    closing_paragraph: str = Field(
        description="Call to action and availability"
    )
    sign_off: str = Field(description="e.g., 'Sincerely,'")

COVER_LETTER_SYSTEM = """You are a cover letter writer. Create targeted, compelling
cover letters that connect the candidate's real experience to the job requirements.

RULES:
1. ONLY reference achievements, skills, and experience from the provided resume.
2. Highlight 2-3 most relevant achievements with specific metrics.
3. Reference the company name and specific role.
4. Mention open-source contributions if relevant.
5. Keep to one page (approximately 300-400 words total).
6. Professional but personable tone."""

def generate_cover_letter(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
) -> CoverLetter:
    client = Anthropic()
    response = client.messages.parse(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        temperature=0.3,  # Slightly higher for natural writing
        system=COVER_LETTER_SYSTEM,
        output_format=CoverLetter,
        messages=[{
            "role": "user",
            "content": (
                f"## Candidate Resume\n\n{resume_text}\n\n"
                f"## Target Position\n\n"
                f"**Title:** {job_title}\n"
                f"**Company:** {company_name}\n\n"
                f"**Job Description:**\n{job_description}\n\n"
                f"Write a cover letter for this position."
            ),
        }],
    )
    return response.parsed_output
```

### Diff Generation
```python
# Source: https://docs.python.org/3/library/difflib.html
import difflib

def generate_resume_diff_html(original_text: str, tailored_text: str) -> str:
    """Generate an HTML table showing side-by-side diff of original vs tailored."""
    original_lines = original_text.splitlines()
    tailored_lines = tailored_text.splitlines()

    differ = difflib.HtmlDiff(tabsize=2, wrapcolumn=80)
    html_table = differ.make_table(
        fromlines=original_lines,
        tolines=tailored_lines,
        fromdesc="Original Resume",
        todesc="Tailored Resume",
        context=True,
        numlines=3,
    )
    return html_table
```

### WeasyPrint PDF Rendering
```python
# Source: https://doc.courtbouillon.org/weasyprint/stable/
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pathlib import Path

def render_resume_pdf(
    tailored: "TailoredResume",
    candidate_name: str,
    output_path: Path,
) -> Path:
    """Render a tailored resume as a PDF."""
    env = Environment(
        loader=FileSystemLoader("webapp/templates/resume"),
        autoescape=True,
    )
    template = env.get_template("resume_template.html")

    html_content = template.render(
        name=candidate_name,
        summary=tailored.professional_summary,
        skills=tailored.technical_skills,
        experience=tailored.work_experience,
        projects=tailored.key_projects,
        education=tailored.education,
    )

    HTML(string=html_content, base_url=str(Path("webapp/templates/resume"))).write_pdf(
        str(output_path)
    )
    return output_path
```

### Dashboard Integration (htmx pattern)
```python
# FastAPI endpoint for resume tailoring
from fastapi import Request
from fastapi.responses import HTMLResponse, FileResponse

@app.post("/jobs/{dedup_key:path}/tailor-resume", response_class=HTMLResponse)
async def tailor_resume_endpoint(request: Request, dedup_key: str):
    """Generate tailored resume for a job listing."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<p>Job not found</p>", status_code=404)

    # Extract original resume text
    settings = get_settings()
    resume_text = extract_resume_text(settings.candidate_resume_path)

    # Tailor via LLM
    tailored = await asyncio.to_thread(
        tailor_resume,
        resume_text=resume_text,
        job_description=job["description"],
        job_title=job["title"],
        company_name=job["company"],
    )

    # Generate diff HTML
    tailored_text = format_resume_as_text(tailored)
    diff_html = generate_resume_diff_html(resume_text, tailored_text)

    # Render PDF
    company_slug = job["company"].replace(" ", "_")[:30]
    filename = f"Patryk_Golabek_Resume_{company_slug}_{date.today().isoformat()}.pdf"
    output_path = RESUMES_TAILORED_DIR / filename
    render_resume_pdf(tailored, "Patryk Golabek", output_path)

    # Track version
    db.save_resume_version(
        job_dedup_key=dedup_key,
        resume_type="resume",
        file_path=str(output_path),
        model_used="claude-sonnet-4-5-20250929",
    )

    # Return diff view with download link
    return templates.TemplateResponse(
        "partials/resume_diff.html",
        {
            "request": request,
            "diff_html": diff_html,
            "download_path": f"/resumes/tailored/{filename}",
            "tailoring_notes": tailored.tailoring_notes,
        },
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON parsing of LLM output | Anthropic structured outputs (`output_config.format`) | Late 2025 (GA Jan 2026) | Zero JSON parsing errors. No retry loops. Pydantic model integration via `client.messages.parse()`. |
| `output_format` parameter | `output_config.format` parameter | Jan 2026 | Old `output_format` still works but deprecated. Use `output_config` for new code. |
| Beta headers for structured outputs | No headers needed (GA) | Jan 2026 | Remove `anthropic-beta` headers. Python/TS SDKs handle this automatically. |
| Text-based PDF extraction (pypdf) | pymupdf4llm Markdown extraction | 2025 | Structure-preserving extraction as Markdown. Tables, headers, bullets preserved. |

**Deprecated/outdated:**
- `output_format` parameter: Moved to `output_config.format`. Still works temporarily but will be removed.
- Beta header `structured-outputs-2025-11-13`: No longer needed now that structured outputs are GA.
- `stealth_sync(page)` for playwright-stealth: Old API, use `Stealth().apply_stealth_sync(page)` (already noted in project MEMORY.md, not directly relevant to this phase but good to know).

## Open Questions

1. **WeasyPrint Font Selection for ATS Compliance**
   - What we know: CLAUDE.md specifies Calibri font, 10-12pt body, 14-16pt headers. WeasyPrint can use system fonts.
   - What's unclear: Whether Calibri (a Microsoft font) is available on macOS by default, or if we need to bundle a similar font (e.g., Carlito, a metric-compatible alternative).
   - Recommendation: Test with the actual macOS system. If Calibri is not available, use Carlito (open-source metric-compatible replacement) or a similar sans-serif font. Bundle the font file in the project if needed.

2. **Optimal Claude Model for Resume Tailoring**
   - What we know: `claude-sonnet-4-5-20250929` is fast and cost-effective. `claude-opus-4-6` is the most capable.
   - What's unclear: Whether Sonnet is sufficient quality for resume tailoring, or if the task warrants Opus.
   - Recommendation: Start with Sonnet (faster, cheaper). Make the model configurable via `config.yaml` so users can upgrade to Opus if they want higher quality output.

3. **Async vs Sync Anthropic Client**
   - What we know: FastAPI is async. The default `Anthropic()` client is synchronous. `AsyncAnthropic()` exists.
   - What's unclear: Whether the extra complexity of the async client is worth it for this use case (one-off resume generation, not high-throughput).
   - Recommendation: Use `asyncio.to_thread()` to wrap the synchronous client, avoiding the need for a separate async client while still not blocking the event loop. This is simpler and sufficient for low-volume usage.

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Full API reference for `output_config.format`, `client.messages.parse()`, Pydantic integration, JSON schema limitations
- [Anthropic Python SDK PyPI](https://pypi.org/project/anthropic/) - v0.79.0, Feb 7, 2026
- [pymupdf4llm PyPI](https://pypi.org/project/pymupdf4llm/) - v0.2.9, Jan 10, 2026
- [WeasyPrint PyPI](https://pypi.org/project/weasyprint/) - v68.1, Feb 6, 2026
- [WeasyPrint Installation Docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) - System dependencies (Pango required)
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) - HtmlDiff class, make_table(), make_file()
- [fpdf2 PyPI](https://pypi.org/project/fpdf2/) - v2.8.5 (alternative considered)

### Secondary (MEDIUM confidence)
- [Anthropic SDK GitHub api.md](https://github.com/anthropics/anthropic-sdk-python/blob/main/api.md) - client.messages.create() method signature
- [PyMuPDF Features Comparison](https://pymupdf.readthedocs.io/en/latest/about.html) - Performance benchmarks vs alternatives
- Multiple WeasyPrint + Jinja2 tutorials confirming the HTML template -> PDF pattern

### Tertiary (LOW confidence)
- LLM anti-fabrication guardrail patterns from multiple blog posts - general best practices, not specific to resume tailoring. Validated against Anthropic's own prompt engineering docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified on PyPI with current versions, API patterns confirmed from official docs
- Architecture: HIGH - Patterns based on official Anthropic structured outputs docs + established WeasyPrint/Jinja2 workflow
- Pitfalls: HIGH - WeasyPrint system deps confirmed from official install docs; LLM fabrication risk is well-documented
- Anti-fabrication: MEDIUM - Multi-layered approach based on general LLM guardrail best practices; specific resume tailoring anti-fabrication is novel application

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (30 days -- stack is stable, Anthropic SDK moves fast but structured outputs are GA)
