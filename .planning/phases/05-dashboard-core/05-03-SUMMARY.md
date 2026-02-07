---
phase: 05-dashboard-core
plan: 03
subsystem: ui
tags: [activity-log, timeline, htmx, jinja2, sqlite, status-workflow]

# Dependency graph
requires:
  - phase: 05-dashboard-core
    provides: activity_log table, log_activity(), get_activity_log(), 11-status vocabulary
provides:
  - Activity timeline UI on job detail page
  - Human-readable status labels in dropdown and badges
  - "Discovered" activity logging on new job upsert
  - "Viewed" activity logging on first job view
affects: [05-dashboard-core]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Color-coded timeline dots per event type (Tailwind utility classes)"
    - "Jinja2 replace/title filters for human-readable enum display"

key-files:
  created: []
  modified:
    - webapp/app.py
    - webapp/db.py
    - webapp/templates/job_detail.html

key-decisions:
  - "Log 'discovered' event in upsert_job() for new jobs (not just migration backfill)"
  - "Human-readable status labels via Jinja2 filters (replace + title) instead of lookup dict"
  - "Activity timeline placed between Notes and Metadata in sidebar"

patterns-established:
  - "Status display: always use {{ status | replace('_', ' ') | title }} for human-readable labels"
  - "Activity event colors: status_change=indigo, discovered=green, note_added=yellow, viewed=gray, applied=purple, scored=blue"

# Metrics
duration: 3min
completed: 2026-02-07
---

# Phase 5 Plan 3: Activity Timeline and Status Labels Summary

**Per-job activity timeline with color-coded events and human-readable status labels across dropdown, badges, and HTMX responses**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-07T20:51:44Z
- **Completed:** 2026-02-07T20:54:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Job detail page shows full activity timeline (discovered, status changes, notes, viewed) in reverse chronological order
- Status dropdown and badge display use human-readable labels (e.g., "Phone Screen" not "phone_screen")
- New job inserts automatically log a "discovered" activity event
- First-time job views log a "viewed" activity event

## Task Commits

Each task was committed atomically:

1. **Task 1: Pass activity log to job detail template and add mark-viewed activity** - `709acc7` (feat)
2. **Task 2: Add activity timeline section to job detail template** - `96ac79b` (feat)

## Files Created/Modified
- `webapp/app.py` - Added activity log fetch + pass to template, "viewed" event logging, human-readable status in update_status response
- `webapp/db.py` - Added "discovered" activity logging in upsert_job() for new jobs
- `webapp/templates/job_detail.html` - Activity timeline section with color-coded dots, human-readable status labels in badge and dropdown

## Decisions Made
- [05-03]: Log "discovered" activity in upsert_job() for new inserts (migration backfill only covers existing jobs at migration time)
- [05-03]: Use Jinja2 `replace('_', ' ') | title` filters for human-readable status display (lightweight, no server-side mapping needed)
- [05-03]: Human-readable labels also applied to update_status() HTMX response for consistency after status changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added "discovered" activity logging in upsert_job()**
- **Found during:** Task 1 (verification test)
- **Issue:** New jobs inserted via upsert_job() had no "discovered" activity event. The migration backfill only covers jobs that existed at migration time. Any job inserted after migration would have an empty activity timeline.
- **Fix:** Added is_new check before upsert and log_activity() call after insert for new jobs
- **Files modified:** webapp/db.py
- **Verification:** Test confirms discovered/status_change/note_added events all present after upsert + status change + notes
- **Committed in:** 709acc7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for correctness -- without this fix, newly discovered jobs would have empty activity timelines. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Activity timeline and status workflow complete (DASH-02 + DASH-05 satisfied)
- Ready for Plan 04 (remaining dashboard core features)

---
*Phase: 05-dashboard-core*
*Completed: 2026-02-07*
