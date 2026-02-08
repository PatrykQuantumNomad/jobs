---
phase: 08-one-click-apply
plan: 03
subsystem: dashboard
tags: [sse, htmx, sse-starlette, fastapi, jinja2, real-time]

# Dependency graph
requires:
  - phase: 08-one-click-apply
    plan: 01
    provides: "ApplyEvent models, ApplyMode enum, is_already_applied dedup check"
  - phase: 08-one-click-apply
    plan: 02
    provides: "ApplyEngine class with apply(), confirm(), cancel(), get_session_queue()"
provides:
  - "POST /jobs/{key}/apply endpoint triggering apply engine with mode selection"
  - "GET /jobs/{key}/apply/stream SSE endpoint with EventSourceResponse"
  - "POST /jobs/{key}/apply/confirm and /cancel for human-in-the-loop"
  - "Apply UI in job detail sidebar with mode dropdown and real-time status"
  - "apply_status.html partial rendering all event types for SSE swap"
affects: [08-04-apply-settings]

# Tech tracking
tech-stack:
  added: [sse-starlette 3.2.0, htmx-ext-sse 2.2.4]
  patterns: [lazy-init singleton for ApplyEngine, asyncio.Queue per session for SSE bridging, server-side Jinja2 rendering of SSE event payloads]

key-files:
  created:
    - webapp/templates/partials/apply_status.html
  modified:
    - webapp/app.py
    - webapp/templates/base.html
    - webapp/templates/job_detail.html

key-decisions:
  - "Lazy-init ApplyEngine singleton with same pattern as resume_ai imports"
  - "Server-side Jinja2 rendering of SSE events (not raw JSON) for htmx swap compatibility"
  - "asyncio.Queue per session stored in engine._sessions for SSE endpoint access"
  - "asyncio.create_task for background apply flow (non-blocking POST response)"
  - "15-second SSE timeout with ping keepalive to prevent connection drop"
  - "Omitted truncate filter for apply_url display (simpler static text instead)"

patterns-established:
  - "SSE streaming: POST starts task + returns sse-connect HTML, GET drains queue via EventSourceResponse"
  - "Apply section placement: between AI Resume Tools and Resume Versions in job detail sidebar"

# Metrics
duration: 5min
completed: 2026-02-08
---

# Phase 8 Plan 3: Dashboard SSE Integration Summary

**SSE-powered apply flow in dashboard with sse-starlette + htmx-ext-sse streaming, mode selection, and real-time progress/confirmation UI**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-08T00:16:11Z
- **Completed:** 2026-02-08T00:21:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Installed sse-starlette and wired 4 apply endpoints (trigger, stream, confirm, cancel) before the catch-all route
- Built Apply section in job detail sidebar with mode dropdown (semi-auto, full-auto, easy-apply-only) and disabled state for already-applied jobs
- Created apply_status.html partial handling all 6 event types (progress, awaiting_confirm, captcha, error, done, fallback) with appropriate styling and action buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Install sse-starlette and add SSE + apply endpoints** - `f1316d7` (feat)
2. **Task 2: Add htmx SSE extension and apply UI** - `6e05e9f` (feat)
3. **Task 3: Create apply_status.html partial** - `088b08e` (feat)

## Files Created/Modified
- `webapp/app.py` - Added _get_apply_engine singleton, _run_apply helper, 4 apply endpoints (trigger, stream, confirm, cancel)
- `webapp/templates/base.html` - Added htmx-ext-sse 2.2.4 script tag after main htmx
- `webapp/templates/job_detail.html` - Added Apply section with mode selector, Apply Now button, spinner, SSE status container
- `webapp/templates/partials/apply_status.html` - New partial for SSE event rendering with progress spinner, confirm/cancel buttons, captcha instructions, error/done states

## Decisions Made
- Lazy-init ApplyEngine singleton follows same pattern as resume_ai lazy imports to avoid startup failures when Playwright or pydantic-settings not installed
- SSE events rendered server-side via Jinja2 (not raw JSON) because htmx-ext-sse swaps HTML content directly into the DOM
- asyncio.Queue stored in engine._sessions dict allows the SSE GET endpoint to access the same queue created by the POST endpoint
- Omitted `| truncate(40)` Jinja2 filter for apply_url display since it may not be available; used static "External application" text instead
- 15-second timeout on queue.get() with ping keepalive prevents browser from treating connection as dead

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Dashboard SSE integration complete, ready for 08-04 (apply settings/configuration UI)
- All apply engine wiring in place: trigger -> background task -> SSE stream -> confirm/cancel
- End-to-end flow ready for testing with live job data

## Self-Check: PASSED

- All 4 files exist (webapp/app.py, base.html, job_detail.html, apply_status.html)
- All 3 task commits verified (f1316d7, 6e05e9f, 088b08e)
- SUMMARY.md created

---
*Phase: 08-one-click-apply*
*Completed: 2026-02-08*
