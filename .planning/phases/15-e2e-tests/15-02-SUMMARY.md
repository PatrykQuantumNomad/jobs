---
phase: 15-e2e-tests
plan: 02
subsystem: testing
tags: [e2e, playwright, kanban, export, csv, json, drag-and-drop, ci]
dependency_graph:
  requires: [tests.e2e.conftest, webapp.app, webapp.db, webapp.templates.kanban, webapp.templates.dashboard]
  provides: [tests.e2e.test_kanban, tests.e2e.test_export]
  affects: [.github/workflows/ci.yml]
tech_stack:
  added: []
  patterns: [htmx-ajax-simulation, seeded-kanban-fixture, expect-download, csv-validation]
key_files:
  created:
    - tests/e2e/test_kanban.py
    - tests/e2e/test_export.py
  modified:
    - .github/workflows/ci.yml
key_decisions:
  - "htmx.ajax fallback for SortableJS drag-and-drop (forceFallback: true makes native drag_to unreliable)"
  - "seeded_kanban_db fixture creates 5 jobs in saved/applied statuses for kanban-specific tests"
  - "CSV/JSON validation reads downloaded file content and parses with stdlib csv/json modules"
  - "CI E2E command uses -p no:socket to disable pytest-socket plugin entirely"
metrics:
  duration: "3 min"
  completed: "2026-02-08"
  tests_added: 5
  files_created: 2
  files_modified: 1
---

# Phase 15 Plan 02: Kanban & Export E2E Tests Summary

Kanban drag-and-drop persistence via htmx ajax simulation and CSV/JSON export download validation in Playwright, plus CI E2E socket fix.

## Performance

| Metric | Value |
|--------|-------|
| Duration | 3 min |
| Tests added | 5 |
| Tests passing | 11/11 (full E2E suite) |
| Files created | 2 |
| Files modified | 1 |

## Accomplishments

1. **Kanban column layout test (E2E-04)** -- Verifies all 9 kanban status columns render correctly, "saved" column has 3 cards, "applied" has 2, and empty columns have 0 cards.

2. **Kanban drag-and-drop persistence test (E2E-04)** -- Simulates what SortableJS's `onEnd` handler does by calling `htmx.ajax('POST', '/jobs/{key}/status', {values: {status: 'applied'}})` directly via `page.evaluate()`. Verifies the card moves from saved (3->2) to applied (2->3) and persists after full page reload. Used htmx ajax fallback because SortableJS `forceFallback: true` makes native Playwright `drag_to()` unreliable.

3. **CSV export download test (E2E-05)** -- Clicks `#export-csv-link`, captures download via `page.expect_download()`, validates filename pattern (`jobs_export_*.csv`), parses with `csv.DictReader`, asserts 10 rows with correct headers (title, company, platform, score, status).

4. **JSON export download test (E2E-05)** -- Same approach for JSON: validates filename, parses with `json.loads()`, asserts 10 objects with correct field structure.

5. **Filtered export test (E2E-05)** -- Filters dashboard by platform "dice", then exports CSV. Validates that all 3 rows have `platform == "dice"` (the 3 scored dice jobs from seeded_db).

6. **CI E2E command fix** -- Added `-p no:socket` to the CI E2E pytest command to prevent `SocketBlockedError` from pytest-socket's `--disable-socket` addopt. E2E tests need real network access for Playwright browser automation.

## Task Commits

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Kanban drag-and-drop E2E tests | d7cf1e8 | tests/e2e/test_kanban.py |
| 2 | CSV/JSON export download E2E tests | e8f8b7e | tests/e2e/test_export.py |
| 3 | CI E2E socket plugin fix | 6ceedf7 | .github/workflows/ci.yml |

## Files Created/Modified

### Created
- `tests/e2e/test_kanban.py` -- TestKanbanE2E class with 2 tests + seeded_kanban_db fixture
- `tests/e2e/test_export.py` -- TestExportE2E class with 3 tests

### Modified
- `.github/workflows/ci.yml` -- Added `-p no:socket` to E2E pytest command

## Decisions Made

1. **htmx ajax fallback for drag-and-drop** -- SortableJS uses `forceFallback: true` which bypasses native drag events. Instead of brittle manual mouse events, we simulate the exact `htmx.ajax()` call from `kanban.html` line 77 via `page.evaluate()`. This tests the same full-stack persistence path (POST /jobs/{key}/status -> DB update -> reload verification).

2. **seeded_kanban_db fixture** -- Separate from `seeded_db` because kanban only shows jobs with pipeline statuses (saved, applied, etc.), not "scored" status. Creates 3 saved + 2 applied = 5 jobs.

3. **CSV/JSON validation via stdlib** -- Downloaded files are read from Playwright's download path and parsed with Python's `csv.DictReader` and `json.loads` for structural validation.

4. **`-p no:socket` in CI** -- Disables the pytest-socket plugin entirely for E2E runs, which is cleaner than relying on per-test `@pytest.mark.enable_socket` markers in combination with `--allow-unix-socket`.

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None. All 11 E2E tests (6 from plan 01 + 5 from plan 02) pass reliably in headless Chromium. Full non-E2E test suite (417 tests) continues to pass with E2E tests excluded.

## Next Phase Readiness

This is the final plan of v1.1 Test Web App. All 15 phases and 39 plans are complete.

**E2E test coverage summary:**
- E2E-01: Dashboard loads with jobs (test_dashboard.py)
- E2E-02: Filtering by platform/score/status (test_dashboard.py)
- E2E-03: Status change persistence (test_status.py)
- E2E-04: Kanban drag-and-drop persistence (test_kanban.py)
- E2E-05: CSV/JSON export downloads (test_export.py)

**Total test suite:** 417 unit/integration + 11 E2E = 428 tests

## Self-Check: PASSED

All 2 created files verified on disk. All 3 task commits verified in git log. CI YAML validated.
