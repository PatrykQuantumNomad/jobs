---
phase: 06-dashboard-analytics
plan: 02
subsystem: ui
tags: [sortablejs, kanban, drag-and-drop, htmx, fastapi, jinja2]

# Dependency graph
requires:
  - phase: 06-dashboard-analytics
    provides: "stats_cards.html partial, {% block scripts %} pattern, nav links, /api/analytics endpoint"
  - phase: 05-dashboard-core
    provides: "SQLite database with jobs table, status workflow, htmx templates"
provides:
  - "GET /kanban page with 9 status columns and SortableJS drag-and-drop"
  - "GET /api/stats-cards endpoint for dynamic stats refresh"
  - "HX-Trigger: statsChanged on POST /jobs/{key}/status"
  - "kanban_card.html reusable partial"
  - "KANBAN_STATUSES constant (excludes discovered/scored)"
affects: [08-one-click-apply]

# Tech tracking
tech-stack:
  added: [sortablejs-1.15.6]
  patterns: [sortable-group-cross-column, optimistic-update-with-rollback, hx-trigger-stats-refresh]

key-files:
  created:
    - webapp/templates/kanban.html
    - webapp/templates/partials/kanban_card.html
  modified:
    - webapp/app.py

key-decisions:
  - "SortableJS 1.15.6 via CDN with forceFallback:true for consistent cross-browser drag behavior"
  - "Optimistic column count updates with DOM rollback on POST failure"
  - "KANBAN_STATUSES excludes discovered and scored (user-managed pipeline only)"
  - "Stats cards refresh via HX-Trigger: statsChanged from POST /jobs/{key}/status"
  - "Jinja2 namespace() pattern for cross-loop variable mutation in empty state check"

patterns-established:
  - "SortableJS group: 'kanban' enables cross-column dragging between all lists"
  - "Optimistic update: modify DOM immediately, rollback via evt.from.insertBefore on error"
  - "HX-Trigger response header: server sends statsChanged, body listener auto-refreshes stats panel"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 6 Plan 2: Kanban Board Summary

**Kanban board with SortableJS drag-and-drop across 9 status columns, optimistic count updates, and HX-Trigger-based stats refresh**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T21:48:14Z
- **Completed:** 2026-02-07T21:51:47Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Built /kanban page with 9 user-managed status columns (saved through ghosted)
- SortableJS drag-and-drop persists status changes via htmx.ajax POST with automatic rollback on failure
- Added /api/stats-cards endpoint for reusable stats refresh across kanban and analytics pages
- HX-Trigger: statsChanged on status updates enables real-time stats sync without page reload

## Task Commits

Each task was committed atomically:

1. **Task 1: Kanban endpoint, HX-Trigger on status update, and stats-cards endpoint** - `431cf00` (feat)
2. **Task 2: Kanban board template with SortableJS drag-and-drop** - `c7b5bac` (feat)

## Files Created/Modified
- `webapp/app.py` - Added GET /kanban, GET /api/stats-cards endpoints, KANBAN_STATUSES constant, HX-Trigger header on POST /jobs/{key}/status
- `webapp/templates/kanban.html` - Full kanban board with 9 columns, SortableJS initialization, optimistic updates, rollback, empty state
- `webapp/templates/partials/kanban_card.html` - Reusable card partial with title, company, score badge, platform, and link to detail

## Decisions Made
- SortableJS loaded via CDN synchronously (same pattern as Chart.js in Plan 01) to ensure availability before init script
- forceFallback:true for consistent drag behavior across browsers (avoids native DnD quirks)
- KANBAN_STATUSES is a separate constant from STATUSES -- only shows user-managed pipeline stages
- Optimistic count update pattern: modify DOM counts immediately, rollback both counts and card position on error
- Used Jinja2 namespace() for cross-loop total calculation (Jinja2 scoping prevents simple set in for loops)
- Terminal statuses (rejected, withdrawn, ghosted) get opacity-60 on column headers for visual hierarchy

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Jinja2 sum filter with attribute on dict values**
- **Found during:** Task 2 (Kanban template rendering)
- **Issue:** `columns.values() | sum(attribute='__len__', default=0)` does not work in Jinja2 -- the sum filter does not support `default` keyword and `__len__` attribute on lists
- **Fix:** Replaced with `namespace(total=0)` pattern iterating over statuses and summing lengths manually
- **Files modified:** webapp/templates/kanban.html
- **Verification:** Template renders correctly with both empty and populated databases
- **Committed in:** c7b5bac (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor template syntax fix. No scope creep.

## Issues Encountered
None beyond the Jinja2 template syntax issue documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (Dashboard Analytics) is now COMPLETE
- Analytics engine (Plan 01) + Kanban board (Plan 02) provide full dashboard experience
- HX-Trigger pattern can be reused by future features that modify job state
- /api/stats-cards endpoint available for any page needing live stats
- Ready for Phase 7 (AI Resume & Cover Letter)

## Self-Check: PASSED

All 3 files verified present. Both commit hashes (431cf00, c7b5bac) verified in git log.

---
*Phase: 06-dashboard-analytics*
*Completed: 2026-02-07*
