---
phase: 08-one-click-apply
plan: 02
subsystem: apply-engine
tags: [asyncio, threading, playwright, sse, form-fill, ats-iframe]

# Dependency graph
requires:
  - phase: 08-one-click-apply
    plan: 01
    provides: ApplyConfig, ApplyEvent, ApplyEventType, is_already_applied
  - phase: 02-platform-architecture
    provides: Platform registry, BrowserPlatformMixin, get_browser_context
  - phase: 05-dashboard-core
    provides: SQLite jobs table, log_activity, resume_versions table
provides:
  - ApplyEngine class with async apply(), confirm(), cancel(), get_session_queue()
  - Thread-safe event emitter via loop.call_soon_threadsafe
  - ATS iframe detection for Greenhouse, Lever, Ashby, BambooHR, Workday
  - FormFiller cover letter and LinkedIn field support
  - BrowserPlatformMixin.wait_for_confirmation() with dashboard/CLI dual mode
affects: [08-03-dashboard-apply-routes, 08-04-ats-form-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [asyncio.to_thread for sync-in-async execution, loop.call_soon_threadsafe for thread-to-async bridging, threading.Event for cross-thread confirmation]

key-files:
  created:
    - apply_engine/engine.py
  modified:
    - form_filler.py
    - platforms/mixins.py

key-decisions:
  - "asyncio.to_thread bridges sync Playwright to async FastAPI -- emit events via loop.call_soon_threadsafe"
  - "Semaphore(1) enforces single-apply serialization at engine level"
  - "Resume resolution checks resume_versions table for tailored version before falling back to default ATS resume"
  - "ATS iframe detection scans page.frames for 5 known ATS domains"
  - "wait_for_confirmation uses getattr pattern for backward-compatible _dashboard_mode and _confirmation_event"

patterns-established:
  - "Thread bridge pattern: asyncio.to_thread + loop.call_soon_threadsafe for Playwright-to-SSE"
  - "Confirmation gate: threading.Event for dashboard, stdin fallback for CLI"
  - "ATS iframe detection: scan page.frames for known domains before form scanning"

# Metrics
duration: 4min
completed: 2026-02-08
---

# Phase 8 Plan 02: Apply Engine Core Summary

**ApplyEngine with thread-safe event emission via asyncio.to_thread, ATS iframe detection in FormFiller, and event-based confirmation in BrowserPlatformMixin**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-08T00:06:49Z
- **Completed:** 2026-02-08T00:11:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ApplyEngine class orchestrating apply flows in background threads with real-time SSE events
- Thread-safe event bridge: sync Playwright thread emits to async FastAPI queue via loop.call_soon_threadsafe
- Browser apply flow with login, screenshot, confirmation gate, and activity logging
- External ATS form fill for API platforms (RemoteOK apply_url) with iframe detection
- FormFiller enhanced with ATS iframe detection for 5 major ATS providers
- BrowserPlatformMixin.wait_for_confirmation() supporting both dashboard and CLI modes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ApplyEngine with thread bridge and event emission** - `3dacf3a` (feat)
2. **Task 2: Enhance FormFiller with iframe detection and add event-based confirmation** - `69da0d3` (feat)

## Files Created/Modified
- `apply_engine/engine.py` - ApplyEngine with apply(), confirm(), cancel(), get_session_queue() plus _apply_sync, _apply_browser, _fill_external_form, _get_resume_path
- `form_filler.py` - Added _detect_ats_iframe(), cover_letter/linkedin keywords, cover letter file upload, iframe-aware fill_form()
- `platforms/mixins.py` - Added wait_for_confirmation() with dashboard (threading.Event) and CLI (stdin) dual mode

## Decisions Made
- asyncio.to_thread bridges sync Playwright to async FastAPI; emit events via loop.call_soon_threadsafe -- the correct pattern for thread-to-event-loop communication
- Semaphore(1) at engine level enforces single-apply serialization to prevent browser resource conflicts
- Resume resolution checks resume_versions table (tailored) before falling back to default ATS resume path from settings
- ATS iframe detection scans page.frames for 5 known domains (Greenhouse, Lever, Ashby, BambooHR, Workday)
- wait_for_confirmation uses getattr pattern (_dashboard_mode, _confirmation_event) for backward-compatible attribute access, matching existing _unattended pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ApplyEngine ready for dashboard route integration in 08-03
- FormFiller iframe detection ready for ATS form polish in 08-04
- Event streaming infrastructure ready for SSE endpoint implementation
- confirm()/cancel() API ready for dashboard button handlers

## Self-Check: PASSED

All 3 created/modified files verified present. Both task commits (3dacf3a, 69da0d3) verified in git log.

---
*Phase: 08-one-click-apply*
*Completed: 2026-02-08*
