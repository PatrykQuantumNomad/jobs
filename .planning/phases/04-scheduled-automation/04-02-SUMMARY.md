---
phase: 04-scheduled-automation
plan: 02
subsystem: infra
tags: [sqlite, run-history, dashboard, observability, fastapi]

requires:
  - phase: 04-scheduled-automation/01
    provides: "--scheduled flag and unattended pipeline mode"
  - phase: 03-discovery-engine
    provides: "SQLite database layer, migration system, web dashboard"
provides:
  - "run_history table tracking every pipeline execution"
  - "record_run() and get_run_history() database functions"
  - "/runs dashboard page showing pipeline execution log"
  - "Error tracking in orchestrator for login and search failures"
  - "busy_timeout=5000 on all SQLite connections for concurrent access"
affects: [dashboard-core, dashboard-analytics]

tech-stack:
  added: []
  patterns:
    - "try/finally in pipeline run() to always record history even on crash"
    - "busy_timeout PRAGMA for concurrent SQLite access (dashboard + scheduler)"

key-files:
  created:
    - "webapp/templates/run_history.html"
  modified:
    - "webapp/db.py"
    - "webapp/app.py"
    - "webapp/templates/base.html"
    - "orchestrator.py"

key-decisions:
  - "Error tracking via self._run_errors list populated in _login_platform and _search_platform"
  - "try/finally wraps entire pipeline so crashes still produce a run_history entry"
  - "record_run protected by its own try/except to avoid masking pipeline errors"

patterns-established:
  - "Pipeline observability: every run produces a database record regardless of outcome"
  - "Status enum: success/partial/failed based on error count and discovered jobs"

duration: 4min
completed: 2026-02-07
---

# Phase 4 Plan 2: Run History Summary

**SQLite run_history table recording every pipeline execution with /runs dashboard page for observability**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T19:56:01Z
- **Completed:** 2026-02-07T19:59:36Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- run_history table created via SCHEMA_VERSION 3 migration with 10 tracked fields
- busy_timeout=5000 on all SQLite connections prevents "database is locked" errors during concurrent dashboard + scheduler access
- Every pipeline run (manual and scheduled) records timing, job counts, errors, and status
- Pipeline crashes still produce a run_history entry via try/finally
- Partial failures (some platforms error, others succeed) recorded as status='partial'
- /runs dashboard page with color-coded status badges, expandable error details, and duration formatting

## Task Commits

Each task was committed atomically:

1. **Task 1: Add run_history table, busy_timeout, and query functions** - `48512a7` (feat)
2. **Task 2: Record run history in orchestrator and /runs dashboard** - `7880f5b` (feat)

## Files Created/Modified
- `webapp/db.py` - SCHEMA_VERSION=3, run_history table, busy_timeout, record_run(), get_run_history()
- `orchestrator.py` - try/finally run recording, _run_errors tracking in login and search
- `webapp/app.py` - /runs endpoint serving run history template
- `webapp/templates/run_history.html` - Run history table with mode/status badges, expandable errors
- `webapp/templates/base.html` - "Run History" nav link

## Decisions Made
- Error tracking uses instance attribute `self._run_errors` populated incrementally during login/search failures
- try/finally wraps entire pipeline body so even unhandled crashes produce a run history entry
- record_run call itself is wrapped in try/except to avoid masking the original pipeline error
- JSON decode errors in raw file counting are silently caught (non-critical for history)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 4 (Scheduled Automation) is now complete
- All three success criteria met: schedule config, unattended runs, run history logging
- Ready for Phase 5 (Dashboard Core): search, extended status workflow, bulk actions, export, activity log

## Self-Check: PASSED

All 5 files verified present. Both task commits (48512a7, 7880f5b) verified in git log.

---
*Phase: 04-scheduled-automation*
*Completed: 2026-02-07*
