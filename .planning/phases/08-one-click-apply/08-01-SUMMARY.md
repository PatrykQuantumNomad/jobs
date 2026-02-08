---
phase: 08-one-click-apply
plan: 01
subsystem: apply-engine
tags: [pydantic, sse, dedup, config, apply-automation]

# Dependency graph
requires:
  - phase: 01-config-externalization
    provides: AppSettings with YAML config loading
  - phase: 05-dashboard-core
    provides: SQLite jobs table with status tracking
provides:
  - ApplyMode enum (FULL_AUTO, SEMI_AUTO, EASY_APPLY_ONLY)
  - ApplyConfig model integrated into AppSettings
  - ApplyEvent/ApplyEventType for SSE streaming
  - is_already_applied() dedup check
  - make_progress_event() and make_done_event() helpers
affects: [08-02-apply-engine, 08-03-dashboard-apply, 08-04-ats-form-fill]

# Tech tracking
tech-stack:
  added: []
  patterns: [SSE event model with typed enum discriminator, lazy db import for dedup]

key-files:
  created:
    - apply_engine/__init__.py
    - apply_engine/config.py
    - apply_engine/events.py
    - apply_engine/dedup.py
  modified:
    - config.py
    - config.yaml
    - config.example.yaml

key-decisions:
  - "Lazy import of webapp.db in dedup.py to avoid circular dependencies at package level"
  - "Applied statuses set includes post-application pipeline stages (phone_screen, technical, etc.)"
  - "ApplyEvent.fields_filled uses dict[str, str] for flexible form field tracking"

patterns-established:
  - "SSE event pattern: typed enum + BaseModel with discriminator field"
  - "Dedup pattern: lazy DB query with status-set check"

# Metrics
duration: 3min
completed: 2026-02-08
---

# Phase 8 Plan 01: Apply Engine Foundation Summary

**Apply engine package with config enums, SSE event models, and dedup check integrated into AppSettings via config.yaml**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-08T00:00:14Z
- **Completed:** 2026-02-08T00:03:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created `apply_engine/` package with config, events, and dedup modules
- ApplyMode enum with 3 modes: full_auto, semi_auto, easy_apply_only
- ApplyEvent model with 7 event types for SSE streaming (PROGRESS, AWAITING_CONFIRM, CONFIRMED, CAPTCHA, ERROR, DONE, PING)
- Dedup check queries jobs table for applied statuses to prevent re-applications
- Integrated ApplyConfig into AppSettings with config.yaml and documented config.example.yaml

## Task Commits

Each task was committed atomically:

1. **Task 1: Create apply_engine package** - `69e84d3` (feat)
2. **Task 2: Integrate ApplyConfig into AppSettings** - `cd38ed1` (feat)

## Files Created/Modified
- `apply_engine/__init__.py` - Package exports: ApplyMode, ApplyConfig, ApplyEvent, ApplyEventType, is_already_applied
- `apply_engine/config.py` - ApplyMode enum and ApplyConfig Pydantic model with 7 settings fields
- `apply_engine/events.py` - ApplyEventType enum, ApplyEvent model, make_progress_event/make_done_event helpers
- `apply_engine/dedup.py` - is_already_applied() queries jobs table for post-application statuses
- `config.py` - Added ApplyConfig import and apply field to AppSettings
- `config.yaml` - Added apply: section with all 7 fields
- `config.example.yaml` - Added documented apply: section with detailed comments

## Decisions Made
- Lazy import of webapp.db in dedup.py to avoid circular dependencies at package import time
- Applied statuses set includes all post-application pipeline stages (applied, phone_screen, technical, final_interview, offer) for comprehensive dedup
- ApplyEvent.fields_filled uses dict[str, str] for flexible form field value tracking across different ATS systems

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- apply_engine package ready for consumption by 08-02 (apply orchestrator)
- ApplyConfig loadable via get_settings().apply for all downstream plans
- Event model ready for SSE streaming in 08-03 (dashboard integration)

## Self-Check: PASSED

All 7 created/modified files verified present. Both task commits (69e84d3, cd38ed1) verified in git log.

---
*Phase: 08-one-click-apply*
*Completed: 2026-02-08*
