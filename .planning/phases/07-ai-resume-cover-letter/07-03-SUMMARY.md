---
phase: 07-ai-resume-cover-letter
plan: 03
subsystem: resume-rendering
tags: [weasyprint, jinja2, pdf, difflib, html-templates, ats-formatting]

# Dependency graph
requires:
  - phase: 07-01
    provides: "TailoredResume, CoverLetter, SkillSection, WorkExperience Pydantic models"
provides:
  - "render_resume_pdf() -- WeasyPrint HTML-to-PDF for tailored resumes"
  - "render_cover_letter_pdf() -- WeasyPrint HTML-to-PDF for cover letters"
  - "generate_resume_diff_html() -- difflib side-by-side comparison"
  - "wrap_diff_html() -- styled diff wrapper for dashboard embedding"
  - "ATS-friendly resume HTML template with Calibri font and letter-size pages"
  - "Clean cover letter HTML template with 1-page layout"
affects: [07-04, 08-one-click-apply]

# Tech tracking
tech-stack:
  added: [weasyprint, difflib]
  patterns: [standalone-html-templates-for-pdf, lazy-jinja2-env, type-checking-guard-imports]

key-files:
  created:
    - resume_ai/renderer.py
    - resume_ai/diff.py
    - webapp/templates/resume/resume_template.html
    - webapp/templates/resume/cover_letter_template.html

key-decisions:
  - "Standalone HTML templates (not extending base.html) since WeasyPrint renders to PDF, not browser"
  - "Lazy Jinja2 Environment initialization via module-level _env pattern for efficiency"
  - "TYPE_CHECKING guard for model imports to avoid circular dependencies"
  - "Calibri with Carlito fallback for ATS compatibility (Carlito is the open-source metric-equivalent)"
  - "Context-mode diff with 3 surrounding lines for focused comparison without noise"

patterns-established:
  - "Standalone HTML templates for PDF rendering: full <!DOCTYPE html> with inline CSS and @page rules"
  - "Lazy Jinja2 env pattern: module-level _env with _get_env() initializer"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 7 Plan 3: PDF Rendering and Diff Summary

**WeasyPrint PDF renderer with Jinja2 templates for ATS-friendly resumes/cover letters, plus difflib-based side-by-side comparison for anti-fabrication verification**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T22:37:34Z
- **Completed:** 2026-02-07T22:41:41Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- ATS-friendly resume PDF template with Calibri font, letter-size pages, proper section headers (PROFESSIONAL SUMMARY, TECHNICAL SKILLS, WORK EXPERIENCE), and page-break-inside avoidance for experience entries
- Clean one-page cover letter PDF template with professional sender info block, date, greeting, and body paragraphs
- WeasyPrint-based renderer producing valid PDFs from structured Pydantic model data (~30KB resume, ~21KB cover letter)
- difflib-powered side-by-side HTML diff with color-coded additions/changes/deletions for the anti-fabrication guardrail

## Task Commits

Each task was committed atomically:

1. **Task 1: Resume and cover letter HTML templates** - `f110d71` (feat)
2. **Task 2: PDF renderer and diff generator** - `54c7eb9` (feat)

## Files Created/Modified

- `webapp/templates/resume/resume_template.html` - Standalone HTML template for resume PDF rendering with ATS-friendly formatting
- `webapp/templates/resume/cover_letter_template.html` - Standalone HTML template for cover letter PDF rendering with 1-page layout
- `resume_ai/renderer.py` - WeasyPrint HTML-to-PDF rendering for resume and cover letter (render_resume_pdf, render_cover_letter_pdf)
- `resume_ai/diff.py` - difflib-based HTML diff generation with styled wrapper (generate_resume_diff_html, wrap_diff_html)

## Decisions Made

- **Standalone HTML templates:** These are NOT Jinja2 extends from base.html since they render to PDF via WeasyPrint, not for browser display. Each is a complete HTML document with inline CSS.
- **Lazy Jinja2 Environment:** Module-level `_env` with `_get_env()` avoids creating the environment until first use, but reuses it across calls.
- **TYPE_CHECKING guard for model imports:** `from resume_ai.models import TailoredResume, CoverLetter` under `if TYPE_CHECKING` to prevent circular import issues as the module graph grows.
- **Font stack:** Calibri (ATS-preferred per CLAUDE.md) with Carlito (open-source metric-compatible fallback) and standard sans-serif chain.
- **Context diff mode:** `context=True, numlines=3` in HtmlDiff for focused comparison that shows relevant surrounding lines without overwhelming noise.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - WeasyPrint was already installed in the project virtualenv. No external service configuration required.

## Next Phase Readiness

- Renderer is ready for 07-04 (dashboard integration) to wire up PDF download endpoints
- Diff module is ready for the review/comparison view in the dashboard
- Templates can be refined based on visual review of generated PDFs
- All four exported functions match the interface expected by the plan's must_haves

## Self-Check: PASSED

- [x] `webapp/templates/resume/resume_template.html` -- FOUND
- [x] `webapp/templates/resume/cover_letter_template.html` -- FOUND
- [x] `resume_ai/renderer.py` -- FOUND
- [x] `resume_ai/diff.py` -- FOUND
- [x] Commit `f110d71` -- FOUND
- [x] Commit `54c7eb9` -- FOUND

---
*Phase: 07-ai-resume-cover-letter*
*Completed: 2026-02-07*
