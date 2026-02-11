# Phase 19: Cover Letter via CLI + SSE & Cleanup - Research

**Researched:** 2026-02-11
**Domain:** SSE streaming for cover letter generation, documentation cleanup, SDK removal verification
**Confidence:** HIGH

## Summary

Phase 19 has two distinct objectives: (1) convert the cover letter endpoint from synchronous request-response to SSE-backed streaming with progress events (same pattern as resume tailoring in Phase 18), and (2) update all documentation to reflect the Claude CLI prerequisite and verify the anthropic SDK is fully removed from runtime.

The cover letter SSE conversion is a near-identical replication of the Phase 18 resume tailoring work. The existing `cover_letter_endpoint` in `webapp/app.py` (line 419) does everything inline: extract resume text, call `generate_cover_letter()` (async via claude_cli.run()), render PDF, save version, return HTML. This needs to be decomposed into a background task with stage events, exactly as `_run_resume_tailor` was built. The cover letter pipeline has fewer stages (no anti-fabrication validation, no diff view) but the same SSE wiring.

The documentation cleanup is straightforward but requires touching multiple files. The CLAUDE.md stack description still says "Anthropic SDK", `docs/architecture.md` references `ANTHROPIC_API_KEY` in multiple places, `.planning/codebase/INTEGRATIONS.md` lists the anthropic SDK as a dependency, and `config.yaml` lists "anthropic" as a tech keyword for scoring (this should stay -- it is a real technology name). The `pyproject.toml` already has the SDK removed from dependencies (done in Phase 16). The `.env.example` already does not include `ANTHROPIC_API_KEY` (was never there). No production Python code imports `anthropic` (verified via grep).

**Primary recommendation:** Split into two plans: (1) SSE cover letter pipeline + tests following Phase 18 pattern exactly, (2) documentation updates and SDK cleanup verification. Plan 1 is the feature work; Plan 2 is housekeeping that can be done independently.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sse-starlette | 3.2.0 | Server-Sent Events for FastAPI | Already in use for resume and apply streams |
| htmx-ext-sse | 2.2.4 | Client-side SSE connection | Already loaded in base.html |
| asyncio (stdlib) | Python 3.14 | Queue, Task, subprocess management | Already used throughout |
| FastAPI | 0.115.0+ | Web framework | Already the app framework |
| WeasyPrint | 68.0+ | Cover letter PDF rendering | Already used in resume_ai/renderer.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pymupdf4llm | 0.2.9+ | PDF text extraction | Extract resume text for LLM context |
| claude_cli | local | CLI subprocess wrapper | Already used by generate_cover_letter() |
| Jinja2 | 3.1+ | Template rendering for SSE events | Already used for all partials |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Replicating resume SSE pattern | Shared SSE utility function | Could DRY up code but adds abstraction for only 2 uses; follow Phase 18 pattern exactly for consistency |
| New cover_letter_status.html partial | Reuse resume_tailor_status.html | Cover letter has no diff/validation; needs different "done" event rendering. New partial is cleaner. |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Existing File Layout (What Changes)
```
webapp/app.py                              # MODIFY: Add _cover_sessions, _cover_tasks, _run_cover_letter, cover_letter_stream
webapp/templates/partials/                  # ADD: cover_letter_status.html (SSE event partial)
webapp/templates/job_detail.html            # MODIFY: Cover Letter button SSE wiring
resume_ai/cover_letter.py                   # UNCHANGED (already async via claude_cli.run())
resume_ai/renderer.py                       # UNCHANGED (render_cover_letter_pdf)
resume_ai/tracker.py                        # UNCHANGED (save_resume_version)
resume_ai/extractor.py                      # UNCHANGED (extract_resume_text)
.claude/CLAUDE.md                           # MODIFY: Stack description, setup commands
docs/architecture.md                        # MODIFY: Remove ANTHROPIC_API_KEY references
.planning/codebase/INTEGRATIONS.md          # MODIFY: Update AI/ML section
```

### Pattern 1: Cover Letter SSE Background Task (from Phase 18)
**What:** Decompose the current inline `cover_letter_endpoint` into a background asyncio.Task that emits stage events to a Queue. The SSE stream endpoint reads events and renders a status partial.
**When to use:** Same pattern as `_run_resume_tailor` from Phase 18.
**Key differences from resume tailoring:**
- Cover letter has 3 stages (not 4): extracting, generating, rendering. There is no anti-fabrication validation step for cover letters (the validator compares entities against the original resume -- less meaningful for a cover letter which is expected to reference the job description).
- The "done" event HTML is simpler: a success message + download link. No diff view (cover letters don't need before/after comparison).
- The cover letter format function (`format_cover_letter_as_text`) could be used to show a preview in the done event, but this is optional.
- Uses emerald-500 spinner color (matching the emerald-600 "Generate Cover Letter" button), not indigo-500.

**Existing code to convert (webapp/app.py lines 419-502):**
```python
# CURRENT: Synchronous inline pattern (will be replaced)
@app.post("/jobs/{dedup_key:path}/cover-letter", response_class=HTMLResponse)
async def cover_letter_endpoint(request: Request, dedup_key: str):
    # ... inline: extract, generate, render PDF, save version, return HTML
```

**Target pattern (parallels _run_resume_tailor):**
```python
_cover_sessions: dict[str, asyncio.Queue] = {}
_cover_tasks: dict[str, asyncio.Task] = {}

async def _run_cover_letter(
    dedup_key: str, job: dict, resume_path: str, queue: asyncio.Queue
) -> None:
    """Background task: run cover letter generation with SSE progress events."""
    from resume_ai.cover_letter import format_cover_letter_as_text, generate_cover_letter
    from resume_ai.extractor import extract_resume_text
    from resume_ai.renderer import render_cover_letter_pdf
    from resume_ai.tracker import save_resume_version

    def _emit(event_type: str, message: str, html: str = "") -> None:
        queue.put_nowait({"type": event_type, "message": message, "html": html})

    try:
        # Stage 1: Extract resume text
        _emit("progress", "Extracting resume text...")
        resume_text = await asyncio.to_thread(extract_resume_text, resume_path)

        # Stage 2: Generate cover letter via Claude CLI
        _emit("progress", "Generating cover letter...")
        letter = await generate_cover_letter(
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Stage 3: Render PDF
        _emit("progress", "Rendering PDF...")
        company_slug = job["company"].replace(" ", "_")[:30]
        filename = f"Patryk_Golabek_CoverLetter_{company_slug}_{date.today().isoformat()}.pdf"
        RESUMES_TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_TAILORED_DIR / filename

        await asyncio.to_thread(
            render_cover_letter_pdf,
            letter,
            "Patryk Golabek",
            "pgolabek@gmail.com",
            "416-708-9839",
            output_path,
        )

        save_resume_version(
            job_dedup_key=dedup_key,
            resume_type="cover_letter",
            file_path=str(output_path),
            original_resume_path=str(resume_path),
            model_used="claude-sonnet-4-5-20250929",
        )
        db.log_activity(
            dedup_key, "cover_letter_generated",
            detail=f"Generated cover letter: {filename}",
        )

        # Build result HTML
        letter_text = format_cover_letter_as_text(letter, "Patryk Golabek")
        result_html = templates.get_template("partials/cover_letter_result.html").render(
            download_url=f"/resumes/tailored/{filename}",
            filename=filename,
            letter_preview=letter_text,
        )
        _emit("done", "Cover letter generated successfully", html=result_html)

    except asyncio.CancelledError:
        _emit("done", "Generation cancelled")
        raise
    except Exception as exc:
        logger.exception("Cover letter generation failed for %s", dedup_key)
        _emit("error", f"Cover letter generation failed: {exc}")
        _emit("done", "")
```

### Pattern 2: SSE Trigger + Stream Endpoints
**What:** Same POST trigger + GET stream pattern as resume tailoring.
**Implementation:** Near-identical to `tailor_resume_endpoint` + `resume_tailor_stream`, with:
- Route paths: `/jobs/{key}/cover-letter` (POST) and `/jobs/{key}/cover-letter/stream` (GET)
- Session dicts: `_cover_sessions` and `_cover_tasks`
- Status partial: `cover_letter_status.html` (new, similar to `resume_tailor_status.html`)
- The stream endpoint MUST be registered before the catch-all `GET /jobs/{dedup_key:path}` route

### Pattern 3: Documentation Update Checklist
**What:** Systematic update of all files that reference Anthropic SDK, ANTHROPIC_API_KEY, or describe the old AI setup.
**Files requiring changes (verified via grep):**

| File | Current Reference | Required Change |
|------|-------------------|-----------------|
| `.claude/CLAUDE.md` line 5 | "Anthropic SDK" in stack description | Change to "Claude CLI" |
| `.claude/CLAUDE.md` line 36 | "Anthropic structured outputs" | Change to "Claude CLI structured outputs" |
| `docs/architecture.md` line 5 | "AI integration via Anthropic's Claude API" | Change to "AI integration via Claude CLI subprocess" |
| `docs/architecture.md` line 28 | "dashboard works without ANTHROPIC_API_KEY" | Change to "dashboard works without Claude CLI" |
| `docs/architecture.md` line 58 | "avoid loading Anthropic SDK at startup" | Change to "avoid loading AI modules at startup" |
| `docs/architecture.md` line 175 | "Uses Anthropic's messages.parse()" | Change to "Uses Claude CLI subprocess with --json-schema" |
| `docs/architecture.md` line 193 | "ANTHROPIC_API_KEY loaded via env" | Remove/rewrite -- no longer applicable |
| `docs/architecture.md` line 228 | "Anthropic API calls" | Change to "Claude CLI calls" |
| `.planning/codebase/INTEGRATIONS.md` lines 24-30 | Anthropic SDK client description | Rewrite to describe Claude CLI subprocess |
| `.planning/codebase/INTEGRATIONS.md` line 96 | "ANTHROPIC_API_KEY" in required env vars | Remove |
| `.planning/PROJECT.md` line 98 | "Anthropic SDK (Claude)" in tech stack | Change to "Claude CLI" |
| `config.yaml` line 110 | "anthropic" in scoring.tech_keywords | KEEP -- this is a legitimate technology keyword |

**Files that do NOT need changes:**
- `pyproject.toml`: Already removed anthropic from dependencies (Phase 16)
- `.env.example`: Never had ANTHROPIC_API_KEY
- `tests/conftest.py`: Already cleaned up (Phase 16 -- no ANTHROPIC_API_KEY reference)
- `resume_ai/*.py`: Already converted to claude_cli (Phase 16)
- Planning docs for completed phases (historical record, do not modify)

### Anti-Patterns to Avoid
- **Modifying historical planning docs:** Phase 7, 9, 16 docs reference Anthropic SDK. These are historical records and should NOT be updated. Only update current-state documentation.
- **Removing "anthropic" from config.yaml tech_keywords:** This is a legitimate technology name used in job matching (e.g., "Experience with Anthropic Claude"). Not an SDK reference.
- **Adding anti-fabrication validation to cover letters:** The validator compares entities against the original resume. Cover letters naturally reference the target company and job requirements, which would trigger false positives. The resume tailoring validator was designed for resume-to-resume comparison only.
- **Creating a shared SSE utility for resume and cover letter:** Two uses do not justify an abstraction. Copy the pattern, adapt for cover letter specifics. If a third SSE pipeline is needed in the future, refactor then.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE transport | Custom response streaming | sse-starlette EventSourceResponse | Already working for resume + apply |
| Client SSE handling | Custom JavaScript | htmx-ext-sse (sse-connect/sse-swap/sse-close) | Already loaded and working |
| Cover letter generation | New LLM call pattern | resume_ai/cover_letter.py generate_cover_letter() | Already async, already uses claude_cli.run() |
| PDF rendering | New PDF pipeline | resume_ai/renderer.py render_cover_letter_pdf() | Already built with HTML template + WeasyPrint |
| Version tracking | New DB logic | resume_ai/tracker.py save_resume_version() | Already handles resume_type="cover_letter" |

**Key insight:** Phase 19 Plan 1 is strictly wiring -- no new business logic. The cover letter generation, PDF rendering, version tracking, and text extraction all exist and work. The only new code is the SSE plumbing (background task, session tracking, stream endpoint, status partial).

## Common Pitfalls

### Pitfall 1: Cover Letter Status Partial Reuse vs New
**What goes wrong:** Reusing `resume_tailor_status.html` for cover letter events, but the "done" event content is different (no diff view, no validation status).
**Why it happens:** DRY instinct -- "both are SSE status partials."
**How to avoid:** Create a new `cover_letter_status.html` partial. The "done" event for cover letters shows a success message + download link + optional preview, not a diff table + validation result. The progress and error states are identical but the done state differs enough to warrant a separate template.
**Warning signs:** Cover letter done event shows empty diff table or validation status.

### Pitfall 2: Forgetting to Wrap render_cover_letter_pdf in to_thread
**What goes wrong:** WeasyPrint PDF rendering blocks the event loop, causing SSE ping events to stall.
**Why it happens:** `render_cover_letter_pdf()` is synchronous (CPU-bound WeasyPrint call).
**How to avoid:** Wrap in `asyncio.to_thread()`, same as resume tailoring does:
```python
await asyncio.to_thread(
    render_cover_letter_pdf, letter, name, email, phone, output_path
)
```
**Warning signs:** SSE connection drops during "Rendering PDF..." stage.

### Pitfall 3: Stream Endpoint Route Ordering
**What goes wrong:** The new `GET /jobs/{key}/cover-letter/stream` endpoint is registered AFTER the catch-all `GET /jobs/{dedup_key:path}` route, so it never matches.
**Why it happens:** FastAPI route registration order matters for path parameters. The catch-all `{dedup_key:path}` matches everything.
**How to avoid:** Register the cover letter stream endpoint in the "Resume AI endpoints" section, alongside the resume tailoring endpoints and BEFORE the catch-all GET route. This is the same requirement Phase 18 had.
**Warning signs:** SSE stream 404s even when session exists.

### Pitfall 4: Cover Letter Button Still Using hx-indicator
**What goes wrong:** The "Generate Cover Letter" button in `job_detail.html` (line 148) currently uses `hx-indicator="#resume-spinner"`. If not updated, the old spinner still shows alongside SSE events.
**Why it happens:** Phase 18 only updated the "Tailor Resume" button, leaving "Generate Cover Letter" with the old indicator pattern.
**How to avoid:** Update the cover letter button to use `hx-disabled-elt="this"` (same pattern as the updated Tailor Resume button) and remove `hx-indicator="#resume-spinner"`. After both buttons are converted, the `#resume-spinner` div can be removed entirely from `job_detail.html`.
**Warning signs:** Both spinner and SSE progress visible simultaneously.

### Pitfall 5: Documentation Updates Missing Files
**What goes wrong:** Updating CLAUDE.md but missing docs/architecture.md or INTEGRATIONS.md, leaving stale Anthropic SDK references.
**Why it happens:** References are scattered across many files.
**How to avoid:** Use the file list in the "Documentation Update Checklist" pattern above. Grep for "anthropic" (case-insensitive) after changes and verify remaining hits are only in historical planning docs or config.yaml tech_keywords.
**Warning signs:** Grep for "ANTHROPIC_API_KEY" or "Anthropic SDK" still returns results in current-state docs.

### Pitfall 6: Removing resume-spinner Prematurely
**What goes wrong:** Removing the `#resume-spinner` div before both buttons are converted to SSE.
**Why it happens:** The Tailor Resume button no longer uses it (Phase 18), so it seems unused.
**How to avoid:** In the same plan that converts the cover letter button, also remove the `#resume-spinner` div since both AI tool buttons will use SSE. Check that the AI Rescore button (in a different sidebar card) uses its own `#ai-score-spinner`, not the resume spinner.
**Warning signs:** Lint or unused element warnings (no actual breakage).

## Code Examples

### Cover Letter SSE Status Partial
```html
{# Cover letter SSE status partial -- rendered per event and swapped via sse-swap="progress" #}

{% if event.type == "progress" %}
<div class="flex items-center gap-2 py-2">
    <div class="animate-spin h-4 w-4 border-2 border-emerald-500 border-t-transparent rounded-full"></div>
    <span class="text-sm text-gray-700">{{ event.message }}</span>
</div>

{% elif event.type == "error" %}
<div class="bg-red-50 border border-red-400 text-red-800 px-4 py-3 rounded">
    <p class="text-sm font-medium">Error</p>
    <p class="text-sm">{{ event.message }}</p>
</div>

{% elif event.type == "done" %}
{% if event.html %}
{{ event.html | safe }}
{% elif event.message %}
<div class="bg-gray-50 border border-gray-300 text-gray-700 px-4 py-3 rounded">
    <p class="text-sm">{{ event.message }}</p>
</div>
{% endif %}

{% else %}
<div class="py-2">
    <span class="text-sm text-gray-500">{{ event.message }}</span>
</div>
{% endif %}
```

### Cover Letter Result Partial (embedded in "done" event HTML)
```html
{# Cover letter result: success message, download link, and optional text preview #}

<div class="bg-green-50 border border-green-400 text-green-800 px-4 py-3 rounded mb-4">
    <p class="text-sm font-medium">Cover letter generated successfully</p>
</div>

<a href="{{ download_url }}"
   class="inline-block bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 mb-4"
   download>Download Cover Letter ({{ filename }})</a>

{% if letter_preview %}
<details class="mt-4 border rounded">
    <summary class="px-4 py-2 bg-gray-50 text-sm font-medium text-gray-700 cursor-pointer">
        Preview Cover Letter
    </summary>
    <div class="px-4 py-3 text-sm text-gray-700 whitespace-pre-line">{{ letter_preview }}</div>
</details>
{% endif %}
```

### Updated Cover Letter Button (job_detail.html)
```html
<!-- Before (current): -->
<button hx-post="/jobs/{{ job.dedup_key | urlencode }}/cover-letter"
        hx-target="#resume-ai-result"
        hx-swap="innerHTML"
        hx-indicator="#resume-spinner"
        class="w-full bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 mb-2">
    Generate Cover Letter
</button>

<!-- After: -->
<button hx-post="/jobs/{{ job.dedup_key | urlencode }}/cover-letter"
        hx-target="#resume-ai-result"
        hx-swap="innerHTML"
        hx-disabled-elt="this"
        class="w-full bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed mb-2">
    Generate Cover Letter
</button>
```

### Test Pattern (from Phase 18 test_resume_sse.py)
```python
@pytest.mark.integration
class TestCoverLetterSSE:
    def test_cover_letter_returns_sse_connect_html(self, client, mock_claude_cli):
        # Same pattern as test_tailor_resume_returns_sse_connect_html
        mock_claude_cli.set_response(_make_cover_letter())
        # ...
        response = client.post(f"/jobs/{key}/cover-letter")
        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "cover-letter/stream" in response.text

    @pytest.mark.asyncio
    async def test_background_task_emits_stage_events(self):
        # Same pattern as test_background_task_emits_stage_events
        # But 3 stages (extracting, generating, rendering) instead of 4
        # And no validation/diff mocks needed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| POST /cover-letter waits 10-15s, returns HTML | POST returns SSE connector, events stream real-time | This phase (Plan 1) | User sees progress instead of frozen spinner |
| CLAUDE.md says "Anthropic SDK" | CLAUDE.md says "Claude CLI" | This phase (Plan 2) | Accurate setup instructions |
| docs/architecture.md references ANTHROPIC_API_KEY | References Claude CLI prerequisite | This phase (Plan 2) | Correct documentation for new developers |
| INTEGRATIONS.md lists anthropic SDK | Lists Claude CLI subprocess | This phase (Plan 2) | Accurate integration map |

**Current state of cover letter generation (what exists):**
- `resume_ai/cover_letter.py`: `generate_cover_letter()` is already async via `claude_cli.run()`, returns `CoverLetter` model
- `resume_ai/cover_letter.py`: `format_cover_letter_as_text()` formats CoverLetter to plain text (useful for preview)
- `resume_ai/renderer.py`: `render_cover_letter_pdf()` is sync (WeasyPrint), takes CoverLetter model + candidate info
- `resume_ai/tracker.py`: `save_resume_version()` already handles `resume_type="cover_letter"`
- `resume_ai/extractor.py`: `extract_resume_text()` is sync (pymupdf4llm), shared with resume tailoring
- `webapp/app.py` line 419: `cover_letter_endpoint()` does everything inline (10-15s blocking)
- `webapp/templates/resume/cover_letter_template.html`: WeasyPrint HTML template for PDF generation
- `webapp/templates/job_detail.html` line 148: Cover Letter button with `hx-indicator="#resume-spinner"`

**What does NOT exist yet:**
- SSE background task for cover letter generation
- SSE stream endpoint for cover letter
- Cover letter SSE status partial template
- Cover letter result partial template (for done event)
- Tests for cover letter SSE endpoints

## Open Questions

1. **Cover letter preview in done event**
   - What we know: `format_cover_letter_as_text()` exists and produces a nice plain-text version. The resume done event shows a diff view. The cover letter has no "original" to diff against.
   - What's unclear: Whether showing a text preview of the generated cover letter is valuable UX, or if a simple success + download link is sufficient.
   - Recommendation: Include a collapsible preview using `<details>/<summary>`. Low effort, good UX for reviewing before downloading. If it clutters the interface, removing it later is trivial.

2. **Removing the #resume-spinner div**
   - What we know: After converting both buttons to SSE, the `#resume-spinner` div in `job_detail.html` (line 155) is unused. The AI Rescore button uses its own `#ai-score-spinner` (line 217) -- separate and unaffected.
   - What's unclear: Whether any other code references `#resume-spinner`.
   - Recommendation: Remove it in Plan 1 alongside the button conversion. Grep for "resume-spinner" to confirm no other references.

3. **Shared SSE status partial vs separate**
   - What we know: `resume_tailor_status.html` handles progress/error/done. Cover letter needs the same progress/error/done but done event HTML differs.
   - What's unclear: Whether the progress and error templates are identical enough to share.
   - Recommendation: Create a separate `cover_letter_status.html`. The templates are <30 lines each. Sharing would require conditional logic (`{% if context == "cover_letter" %}`) that makes the template harder to read for negligible DRY benefit.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis:** `webapp/app.py` lines 247-416 -- existing resume tailoring SSE pattern (Phase 18)
- **Codebase analysis:** `webapp/app.py` lines 419-502 -- current cover letter endpoint (synchronous)
- **Codebase analysis:** `resume_ai/cover_letter.py` -- generate_cover_letter() already async via claude_cli.run()
- **Codebase analysis:** `resume_ai/cover_letter.py` -- format_cover_letter_as_text() for preview
- **Codebase analysis:** `resume_ai/renderer.py` -- render_cover_letter_pdf() sync function
- **Codebase analysis:** `resume_ai/tracker.py` -- save_resume_version() with resume_type="cover_letter"
- **Codebase analysis:** `resume_ai/models.py` -- CoverLetter Pydantic model (greeting, opening, body, closing, sign_off)
- **Codebase analysis:** `webapp/templates/job_detail.html` -- Cover Letter button with hx-indicator (line 148)
- **Codebase analysis:** `webapp/templates/partials/resume_tailor_status.html` -- SSE event partial pattern
- **Codebase analysis:** `webapp/templates/partials/resume_diff.html` -- resume done event partial pattern
- **Codebase analysis:** `tests/webapp/test_resume_sse.py` -- 6 tests as test pattern reference
- **Codebase analysis:** `tests/conftest.py` -- mock_claude_cli fixture, _block_cli guard
- **Grep verification:** No production Python file imports `anthropic` (0 matches)
- **Grep verification:** `pyproject.toml` does not list `anthropic` in dependencies
- **Grep verification:** `.env.example` does not contain `ANTHROPIC_API_KEY`
- **Grep verification:** `tests/conftest.py` does not reference `ANTHROPIC_API_KEY`
- **File inventory:** All documentation files with "anthropic" references catalogued

### Secondary (MEDIUM confidence)
- **Phase 18 RESEARCH.md** -- SSE patterns, pitfalls, and architecture verified during Phase 18 execution
- **Phase 18 01-PLAN.md** -- Exact task structure and verification steps that worked

### Tertiary (LOW confidence)
- None. All findings are from direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies; all libraries already in use and proven
- Architecture: HIGH -- Direct replication of Phase 18 pattern; cover letter endpoint structure is simpler than resume
- Pitfalls: HIGH -- All pitfalls identified in Phase 18 apply here; no new risks
- Documentation cleanup: HIGH -- All files identified via grep; changes are straightforward text updates

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable patterns, no library changes expected)
