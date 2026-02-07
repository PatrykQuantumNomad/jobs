---
phase: 05-dashboard-core
plan: 01
subsystem: database
tags: [sqlite, fts5, schema-migration, activity-log, status-workflow]

# Dependency graph
requires:
  - phase: 03-discovery-engine
    provides: "Schema v3 with run_history table, delta tracking columns"
provides:
  - "Schema v5 with FTS5 full-text search index on jobs"
  - "activity_log table with log_activity() and get_activity_log() functions"
  - "11-member JobStatus enum with pipeline + user-facing statuses"
  - "Status CSS classes for all 11 states"
affects: [05-dashboard-core, 06-dashboard-analytics]

# Tech tracking
tech-stack:
  added: [sqlite-fts5]
  patterns: [activity-logging-on-mutations, multi-version-schema-migration]

key-files:
  created: []
  modified:
    - webapp/db.py
    - models.py
    - webapp/app.py
    - webapp/templates/base.html

key-decisions:
  - "FTS5 content-sync table with triggers (not standalone) to avoid double-storage"
  - "Activity log uses dedup_key foreign reference (not JOIN-enforced) for simplicity"
  - "Status migration: approved -> saved, skipped -> withdrawn (semantic alignment)"

patterns-established:
  - "Activity logging pattern: mutations to jobs call log_activity() after the UPDATE"
  - "Schema migration idempotency: catch both 'duplicate column name' and 'already exists'"

# Metrics
duration: 3min
completed: 2026-02-07
---

# Phase 5 Plan 01: Schema Migration Summary

**Schema v5 with FTS5 full-text search, activity_log table, and 11-member status vocabulary replacing the original 6-status enum**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-07T20:43:27Z
- **Completed:** 2026-02-07T20:46:50Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- FTS5 virtual table with 3 sync triggers keeps full-text index current on all INSERT/UPDATE/DELETE
- activity_log table records status changes and note additions with automatic backfill of discovery events
- JobStatus enum expanded from 6 to 11 members (2 pipeline + 9 user-facing) with old values migrated
- CSS classes and STATUSES list updated for all 11 status values

## Task Commits

Each task was committed atomically:

1. **Task 1: Schema migration v4 (FTS5 + activity_log) and v5 (status vocabulary)** - `fd1f373` (feat)
2. **Task 2: Update STATUSES list in app.py and CSS classes in base.html** - `ac9c2e8` (feat)

## Files Created/Modified
- `webapp/db.py` - Schema v5 with FTS5, activity_log, log_activity(), get_activity_log(), migration v4+v5
- `models.py` - Expanded JobStatus enum (11 members, removed APPROVED/SKIPPED)
- `webapp/app.py` - Updated STATUSES list from 6 to 11 entries
- `webapp/templates/base.html` - CSS classes for all 11 status values

## Decisions Made
- FTS5 uses content-sync mode (content='jobs') with triggers rather than standalone table to avoid double storage
- Activity log references dedup_key directly without SQL foreign key constraint for flexibility
- Status vocabulary migration maps approved->saved and skipped->withdrawn for semantic clarity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FTS5 index ready for search implementation (05-02)
- activity_log table ready for activity feed UI (05-03/05-04)
- Status vocabulary ready for bulk actions and kanban board

---
*Phase: 05-dashboard-core*
*Completed: 2026-02-07*
