---
phase: 03-discovery-engine
plan: 03
subsystem: ui, dashboard
tags: [htmx, jinja2, tailwindcss, sqlite, fastapi]

# Dependency graph
requires:
  - phase: 03-discovery-engine/plan-02
    provides: "webapp/db.py with mark_viewed, 7 new columns (first_seen_at, viewed_at, score_breakdown, company_aliases, salary_display, etc.)"
  - phase: 03-discovery-engine/plan-01
    provides: "ScoreBreakdown dataclass, salary.py compact format, dedup.py company aliases"
provides:
  - "Dashboard NEW badges on unviewed jobs (green pill, disappears on click-through)"
  - "Inline score breakdown on dashboard cards: Title +N | Tech +N | Remote +N | Salary +N"
  - "Detail page score breakdown with matched tech keywords: Tech +2 (Kubernetes, Python)"
  - "Compact salary display ($150K-$200K USD/yr) on dashboard and detail"
  - "Company alias merge trail on detail page: Also posted as: Google LLC"
  - "Mark-viewed on job detail access (sets viewed_at, removes NEW badge)"
  - "Robust parse_json Jinja2 filter handling None/empty/invalid JSON"
affects: [05-01-PLAN (dashboard search builds on this UI), 05-02-PLAN (status workflow extends dashboard cards)]

# Tech tracking
tech-stack:
  added: []
  patterns: [jinja2-parse-json-filter, conditional-badge-rendering, compact-salary-display]

key-files:
  created: []
  modified: [webapp/app.py, webapp/templates/dashboard.html, webapp/templates/job_detail.html]

key-decisions:
  - "parse_json filter enhanced to handle None, empty strings, and invalid JSON gracefully (returns {} on failure)"
  - "NEW badge in Score column (not separate column) to keep table compact"
  - "No salary placeholder for missing data -- blank cell, not 'N/A' or dash"
  - "Tech keywords shown only on detail page (not dashboard cards) to avoid clutter"

patterns-established:
  - "Conditional badge pattern: {% if not job.viewed_at %} for NEW indicators"
  - "JSON column rendering: parse_json filter + safe dict access in Jinja2 templates"
  - "Compact salary display: use salary_display column directly, hide when empty"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 3 Plan 3: Dashboard UI Summary

**Dashboard UI with NEW badges, inline score breakdowns, compact salary display, and company alias merge trail**

## Performance

- **Duration:** 4 min (2 min auto tasks + checkpoint wait)
- **Started:** 2026-02-07T18:55:43Z
- **Completed:** 2026-02-07T18:57:27Z (auto tasks)
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 3

## Accomplishments
- Job cards show green "NEW" badge for unviewed jobs; clicking into detail marks viewed and removes badge on next load
- Inline score breakdown renders below score number on dashboard: "Title +N | Tech +N | Remote +N | Salary +N"
- Job detail page shows full breakdown with matched tech keywords (e.g., "Tech +2 (Kubernetes, Python)")
- Salary displays in compact format ($150K-$200K USD/yr) on both dashboard and detail; blank when no salary data
- Company aliases shown on detail page as "Also posted as: ..." when fuzzy dedup merged variant names
- First/last seen timestamps and viewed_at exposed in detail metadata section

## Task Commits

Each task was committed atomically:

1. **Task 1: Update webapp/app.py with mark-viewed and import enhancements** - `7d2db95` (feat)
2. **Task 2: Update dashboard and detail templates with NEW badge, score breakdown, salary display, and aliases** - `0fbe1e9` (feat)
3. **Task 3: Human verification checkpoint** - APPROVED (no commit)

## Files Created/Modified
- `webapp/app.py` - Added mark_viewed call in job_detail route when viewed_at is None; enhanced parse_json filter to handle None/empty/invalid JSON gracefully
- `webapp/templates/dashboard.html` - NEW badge in Score column, inline score breakdown from parsed score_breakdown JSON, salary_display column replacing raw salary, blank cell for missing salary
- `webapp/templates/job_detail.html` - Score breakdown section with matched tech keywords, company aliases merge trail, compact salary badge, first_seen_at/viewed_at metadata

## Decisions Made
- Enhanced parse_json Jinja2 filter to return {} on None, empty string, or invalid JSON -- prevents template rendering errors from malformed DB data
- NEW badge placed inside Score column cell rather than a separate column to keep the table compact
- No placeholder text for missing salary (no "N/A", no dash) -- simply blank, per user decision
- Tech keywords (e.g., "Kubernetes, Python") shown only on detail page breakdown, not dashboard cards, to avoid clutter

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 (Discovery Engine) is fully complete: all 3 plans delivered
- Dashboard displays all Phase 3 data: NEW badges, score breakdowns, salary normalization, company aliases
- Ready for Phase 4 (Scheduled Automation): delta tracking and mark_viewed support unattended re-runs
- Ready for Phase 5 (Dashboard Core): search/filter/bulk actions build on top of this UI foundation

## Self-Check: PASSED

- FOUND: webapp/app.py
- FOUND: webapp/templates/dashboard.html
- FOUND: webapp/templates/job_detail.html
- FOUND: 7d2db95
- FOUND: 0fbe1e9

---
*Phase: 03-discovery-engine*
*Completed: 2026-02-07*
