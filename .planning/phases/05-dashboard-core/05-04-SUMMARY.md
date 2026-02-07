---
phase: 05-dashboard-core
plan: 04
subsystem: ui
tags: [bulk-actions, csv-export, json-export, htmx, checkboxes]

# Dependency graph
requires:
  - phase: 05-02
    provides: "partials/job_rows.html, GET /search endpoint"
  - phase: 05-03
    provides: "Activity logging in update_job_status()"
provides:
  - "POST /bulk/status for multi-job status updates"
  - "GET /export/csv and GET /export/json with filter-aware downloads"
  - "Checkbox select-all and bulk action bar on dashboard"
affects: [06-dashboard-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns: [htmx bulk form submission, streaming CSV/JSON export, checkbox state management with htmx swap recovery]

key-files:
  created: []
  modified:
    - webapp/app.py
    - webapp/templates/dashboard.html
    - webapp/templates/partials/job_rows.html

key-decisions:
  - "Annotated[list[str], Form()] for repeated form fields (FastAPI/Starlette pattern for multi-checkbox)"
  - "hx-include merges #bulk-form checkboxes with filter selects outside the form"
  - "Export links use Jinja2 urlencode filter to preserve active filter state in URL params"
  - "bulk_status select lives outside the form (in bulk-bar) so it is included via hx-include, not form nesting"

patterns-established:
  - "Bulk htmx pattern: button with hx-post + hx-include gathers checkboxes from form and filter values from selects"
  - "Export pattern: plain anchor links with query params -- no JS needed, browser handles download via Content-Disposition"
  - "htmx:afterSwap listener resets checkbox/bulk-bar state after any table body replacement"

# Metrics
duration: 3min
completed: 2026-02-07
---

# Phase 5 Plan 04: Bulk Actions & Export Summary

**Multi-select checkboxes with bulk status updates via htmx, plus filter-aware CSV/JSON export downloads with StreamingResponse**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-07T20:58:28Z
- **Completed:** 2026-02-07T21:01:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Dashboard rows have per-job checkboxes with select-all toggle in table header
- Bulk action bar (hidden by default) appears when jobs are selected, showing count and status dropdown
- POST /bulk/status updates all selected jobs and returns refreshed table rows (activity logged per job via existing db.update_job_status)
- Export CSV and Export JSON links in dashboard footer download filtered/searched results with date-stamped filenames
- All export and bulk endpoints respect active search query, score, platform, status, sort, and direction filters

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bulk status update and export endpoints to app.py** - `efe9f4c` (feat)
2. **Task 2: Add checkboxes, bulk action bar, and export buttons to dashboard templates** - `50cdb03` (feat)

## Files Created/Modified
- `webapp/app.py` - Added imports (csv, io, date, Annotated, StreamingResponse), POST /bulk/status, GET /export/csv, GET /export/json endpoints
- `webapp/templates/dashboard.html` - Bulk action bar with status dropdown, select-all checkbox header, form wrapper around table, export links with filter params, JavaScript for checkbox state management
- `webapp/templates/partials/job_rows.html` - Checkbox column as first td with stopPropagation, colspan 7->8 in empty state

## Decisions Made
- [05-04]: Used Annotated[list[str], Form()] for job_keys parameter -- FastAPI/Starlette requires this pattern for repeated form field names from multiple checkboxes
- [05-04]: hx-include on bulk Apply button merges checkbox values from #bulk-form with filter values from named selects outside the form -- avoids nested forms
- [05-04]: Export implemented as plain anchor links with Jinja2-templated query params (no JavaScript) -- browser natively handles Content-Disposition attachment downloads
- [05-04]: bulk_status dropdown placed in bulk-bar div outside the form -- included in htmx request via hx-include selector

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 (Dashboard Core) is now COMPLETE -- all 4 plans executed
- DASH-01 (schema migration), DASH-02 (activity timeline), DASH-03 (bulk actions), DASH-04 (export), DASH-05 (status workflow) all satisfied
- Ready for Phase 6 (Dashboard Analytics)

---
*Phase: 05-dashboard-core*
*Completed: 2026-02-07*
