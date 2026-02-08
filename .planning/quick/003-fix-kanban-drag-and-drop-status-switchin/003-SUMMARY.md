---
phase: quick-003
plan: 01
subsystem: ui
tags: [kanban, drag-and-drop, htmx, fetch, sortablejs, javascript]

# Dependency graph
requires:
  - phase: v1.1 (webapp)
    provides: Kanban board with SortableJS drag-and-drop and htmx integration
provides:
  - Working kanban drag-and-drop that persists status without destroying the board
  - Regression E2E test preventing reintroduction of htmx swap bug
affects: [webapp, kanban, e2e-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Use fetch() instead of htmx.ajax() for fire-and-forget POST requests where no DOM swap is desired"
    - "Manually dispatch custom events (statsChanged) after fetch to trigger htmx listeners"

key-files:
  created: []
  modified:
    - webapp/templates/kanban.html
    - tests/e2e/test_kanban.py

key-decisions:
  - "Replaced htmx.ajax with fetch() to avoid unintended DOM swapping on fire-and-forget status updates"

patterns-established:
  - "fetch() for non-swap AJAX: When an endpoint returns HTML meant for a different context, use fetch() instead of htmx.ajax() to avoid htmx default swap behavior"

# Metrics
duration: 2min
completed: 2026-02-08
---

# Quick Task 003: Fix Kanban Drag-and-Drop Status Switching Summary

**Replaced htmx.ajax with fetch() in SortableJS onEnd handler to prevent response HTML from destroying the Kanban board**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-08T23:29:37Z
- **Completed:** 2026-02-08T23:32:17Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed critical bug where dragging a card between Kanban columns destroyed the entire board
- Root cause: htmx.ajax defaulted to swapping the response (a status badge `<span>`) into `document.body` as innerHTML
- Replaced with plain `fetch()` which ignores the response HTML entirely
- Added manual `statsChanged` event dispatch so htmx-driven stats cards still refresh
- Added regression E2E test verifying the board survives a drag-and-drop operation

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix htmx.ajax swap behavior in Kanban drag handler** - `6c187fb` (fix)
2. **Task 2: Update E2E test to use fetch instead of htmx.ajax** - `31dc69b` (test)

## Files Created/Modified
- `webapp/templates/kanban.html` - Replaced htmx.ajax with fetch() in SortableJS onEnd handler, added statsChanged event dispatch
- `tests/e2e/test_kanban.py` - Updated existing drag test to use fetch(), added board-destruction regression test

## Decisions Made
- Used `fetch()` instead of `htmx.ajax` with `swap: "none"` because the status update is genuinely fire-and-forget with no DOM interaction needed. fetch() gives cleaner error handling via `response.ok` and avoids any htmx swap edge cases.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Quick Task: 003-fix-kanban-drag-and-drop-status-switchin*
*Completed: 2026-02-08*
