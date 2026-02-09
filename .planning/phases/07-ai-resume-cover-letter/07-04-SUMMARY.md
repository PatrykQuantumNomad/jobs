---
phase: 07-ai-resume-cover-letter
plan: 04
subsystem: dashboard-integration
tags: [fastapi, htmx, asyncio, anthropic, resume-tailoring, cover-letter, diff-view, anti-fabrication]

# Dependency graph
requires:
  - phase: 07-02
    provides: "tailor_resume, generate_cover_letter, format_resume_as_text, format_cover_letter_as_text"
  - phase: 07-03
    provides: "render_resume_pdf, render_cover_letter_pdf, generate_resume_diff_html, wrap_diff_html"
provides:
  - "POST /jobs/{key}/tailor-resume endpoint with LLM tailoring + diff view + validation"
  - "POST /jobs/{key}/cover-letter endpoint with LLM generation + PDF download"
  - "GET /resumes/tailored/{filename} PDF download endpoint"
  - "GET /jobs/{key}/resume-versions version history endpoint"
  - "AI Resume Tools UI section on job detail page with htmx integration"
  - "Anti-fabrication validation banner (green pass / amber warning)"
affects: [08-one-click-apply]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-imports-for-optional-deps, asyncio-to-thread-for-llm, route-ordering-before-catch-all]

key-files:
  modified:
    - webapp/app.py
    - webapp/templates/job_detail.html
  created:
    - webapp/templates/partials/resume_diff.html
    - webapp/templates/partials/resume_versions.html

key-decisions:
  - "Lazy imports for resume_ai modules inside endpoint functions to avoid startup failure when AI deps not installed"
  - "AI endpoints registered before catch-all /jobs/{path} GET route (FastAPI path ordering matters)"
  - "asyncio.to_thread for all LLM calls to avoid blocking the event loop"
  - "Post-generation validate_no_fabrication() runs automatically before returning diff view"

patterns-established:
  - "Lazy import pattern for optional heavy dependencies: import inside function body, catch ImportError gracefully"
  - "asyncio.to_thread wrapper for synchronous LLM SDK calls in async FastAPI endpoints"

# Metrics
duration: 8min
completed: 2026-02-07
---

# Phase 7 Plan 4: Dashboard Integration Summary

**FastAPI endpoints for AI resume tailoring and cover letter generation with htmx UI, anti-fabrication validation banner, diff view, and version tracking**

## Performance

- **Duration:** 8 min
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 2
- **Files created:** 2

## Accomplishments

- Four new FastAPI endpoints wiring the resume_ai module into the web dashboard: tailor-resume (POST), cover-letter (POST), PDF download (GET), resume-versions (GET)
- AI Resume Tools section on job detail sidebar with "Tailor Resume" and "Generate Cover Letter" buttons using htmx for async interaction
- Anti-fabrication validation banner displayed automatically after generation: green confirmation when clean, amber warning listing specific suspect entities when fabrication detected
- Side-by-side diff view showing exactly what changed between original and tailored resume, with download link and tailoring notes
- Resume version history lazy-loaded on job detail page via htmx, showing all generated documents per job
- Activity timeline integration for resume_tailored and cover_letter_generated events

## Task Commits

Each task was committed atomically:

1. **Task 1: API endpoints for resume tailoring and cover letter generation** - `c25f62d` (feat)
2. **Task 2: Dashboard UI integration (buttons, diff view, version list)** - `b47aeeb` (feat)
3. **Task 3: Human verification checkpoint** - approved by user (no commit)

## Files Created/Modified

- `webapp/app.py` - 4 new endpoints: POST tailor-resume, POST cover-letter, GET resume download, GET resume-versions. Lazy imports for resume_ai modules. asyncio.to_thread for non-blocking LLM calls.
- `webapp/templates/job_detail.html` - AI Resume Tools section with buttons, loading spinner, result container. Resume Versions section with lazy-load. Activity timeline entries for resume events.
- `webapp/templates/partials/resume_diff.html` - htmx partial showing validation banner (green/amber), tailoring notes, download link, side-by-side diff table, regenerate button.
- `webapp/templates/partials/resume_versions.html` - htmx partial listing resume versions with type badge, date, download link, and model info.

## Decisions Made

- **Lazy imports for resume_ai:** Modules like `tailor.py`, `cover_letter.py`, `renderer.py` are imported inside endpoint function bodies rather than at module level. This prevents the dashboard from failing to start if optional AI dependencies (anthropic, weasyprint) are not installed.
- **Route ordering:** AI endpoints registered before the catch-all `/jobs/{dedup_key:path}` GET route, since FastAPI matches routes in registration order and the catch-all would intercept paths like `/jobs/{key}/tailor-resume`.
- **asyncio.to_thread:** All synchronous Anthropic SDK calls wrapped in `asyncio.to_thread()` to keep the FastAPI event loop responsive during the 10-15 second LLM generation time.
- **Automatic validation:** `validate_no_fabrication()` runs on every tailored resume before the diff view is returned. Users see immediate feedback on whether the AI stayed factual.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Changed from top-level imports to lazy imports**
- **Found during:** Task 1 (API endpoints)
- **Issue:** Top-level imports of resume_ai modules would cause ImportError at startup if anthropic or weasyprint packages are not installed, breaking the entire dashboard
- **Fix:** Moved all resume_ai imports inside endpoint function bodies (lazy import pattern)
- **Files modified:** webapp/app.py
- **Verification:** Dashboard starts successfully without AI dependencies installed
- **Committed in:** c25f62d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for robustness -- dashboard must work even without optional AI dependencies. No scope creep.

## Issues Encountered

None.

## User Setup Required

To use the AI resume features, users need:
1. `ANTHROPIC_API_KEY` set in `.env` file
2. WeasyPrint system dependency installed (`brew install weasyprint` or `brew install pango` on macOS)
3. A base resume PDF at the path configured in `config.yaml` (default: `resumes/Patryk_Golabek_Resume.pdf`)

Without these, the dashboard still works normally -- AI buttons will return clear error messages.

## Next Phase Readiness

- Phase 7 is now COMPLETE. All four plans delivered: foundation models (07-01), LLM tailoring engine (07-02), PDF renderer (07-03), and dashboard integration (07-04).
- Phase 8 (One-Click Apply) can proceed. It depends on Phase 2 (platform architecture), Phase 5 (dashboard core), and Phase 7 (AI resume). All are complete.
- The resume_ai module is fully integrated and accessible from the dashboard UI.
- ATS form diversity research is still needed before Phase 8 planning (noted in STATE.md blockers).

## Self-Check: PASSED

- [x] `webapp/app.py` -- FOUND
- [x] `webapp/templates/job_detail.html` -- FOUND
- [x] `webapp/templates/partials/resume_diff.html` -- FOUND
- [x] `webapp/templates/partials/resume_versions.html` -- FOUND
- [x] Commit `c25f62d` -- FOUND
- [x] Commit `b47aeeb` -- FOUND

---
*Phase: 07-ai-resume-cover-letter*
*Completed: 2026-02-07*
