---
phase: 15-e2e-tests
plan: 01
subsystem: testing
tags: [e2e, playwright, dashboard, filtering, status, live-server]
dependency_graph:
  requires: [webapp.app, webapp.db, tests.conftest, tests.conftest_factories]
  provides: [tests.e2e.conftest, tests.e2e.test_dashboard, tests.e2e.test_status]
  affects: [webapp.app]
tech_stack:
  added: [pytest-playwright]
  patterns: [live-server-fixture, seeded-db-fixture, htmx-response-waiting]
key_files:
  created:
    - tests/e2e/__init__.py
    - tests/e2e/conftest.py
    - tests/e2e/test_dashboard.py
    - tests/e2e/test_status.py
  modified:
    - pyproject.toml
    - webapp/app.py
key_decisions:
  - "Live server on port 8765 via uvicorn in daemon thread (session-scoped)"
  - "seeded_db fixture creates 10 jobs: 9 scored (3 per platform) + 1 saved"
  - "Fixed score parameter type from int|None to str|None with _parse_score helper"
  - "Use page.expect_response() context manager for htmx POST waiting"
  - "E2E tests require -p no:socket -o addopts= to override pytest-socket blocking"
metrics:
  duration: "11 min"
  completed: "2026-02-08"
  tests_added: 6
  files_created: 4
  files_modified: 2
---

# Phase 15 Plan 01: E2E Test Infrastructure & Dashboard Tests Summary

Playwright-based E2E test suite with live FastAPI server fixture, seeded database, and 6 browser tests covering dashboard load, filtering, and status persistence.

## Performance

| Metric | Value |
|--------|-------|
| Duration | 11 min |
| Tests added | 6 |
| Tests passing | 6/6 |
| Files created | 4 |
| Files modified | 2 |

## Accomplishments

1. **E2E test infrastructure** -- Created `tests/e2e/` package with `conftest.py` containing session-scoped `live_server` fixture (uvicorn on port 8765 in daemon thread), `browser_context_args` override (1280x800 viewport, downloads enabled), and function-scoped `seeded_db` fixture (10 jobs across 3 platforms).

2. **Dashboard load test (E2E-01)** -- Verifies page title, nav bar, stats cards, and 10 job rows visible in a real Chromium browser.

3. **Filtering tests (E2E-02)** -- Three tests verifying platform filter (4 indeed jobs), score filter (7 jobs with score >= 4), and status filter (1 saved job).

4. **Status persistence tests (E2E-03)** -- Two tests: status change via detail page persists after reload, and status change is reflected in dashboard filtering.

5. **Bug fix: empty score parameter** -- Fixed FastAPI 422 error when HTML form submits `score=` (empty string). Changed `score: int | None` to `str | None` with `_parse_score()` helper across all 5 endpoints (dashboard, search, bulk, CSV export, JSON export).

## Task Commits

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | E2E infrastructure + conftest | 464a644 | pyproject.toml, tests/e2e/conftest.py |
| 2 | Dashboard load + filtering tests | 39fdda5 | tests/e2e/test_dashboard.py, webapp/app.py |
| 3 | Status persistence tests | 2322837 | tests/e2e/test_status.py |

## Files Created/Modified

### Created
- `tests/e2e/__init__.py` -- Package marker
- `tests/e2e/conftest.py` -- live_server, browser_context_args, seeded_db fixtures
- `tests/e2e/test_dashboard.py` -- TestDashboardE2E class with 4 tests
- `tests/e2e/test_status.py` -- TestStatusUpdateE2E class with 2 tests

### Modified
- `pyproject.toml` -- Added pytest-playwright>=0.6.0 to dev dependencies
- `webapp/app.py` -- Added `_parse_score()` helper, changed score param type in 5 endpoints

## Decisions Made

1. **Port 8765 for live server** -- Non-standard port avoids conflicts with dev server on 8000
2. **Session-scoped server, function-scoped DB** -- Server stays running across tests; `_fresh_db` autouse fixture resets the in-memory SQLite singleton between tests; seeded_db re-seeds each test
3. **_parse_score() helper** -- Converts empty string to None, invalid strings to None, valid strings to int. Applied to all 5 endpoints that accept score parameter
4. **expect_response() for htmx** -- Used Playwright's `page.expect_response()` context manager to wait for htmx POST completion before asserting DOM changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Empty string score parameter causes FastAPI 422 error**
- **Found during:** Task 2
- **Issue:** HTML form `<select name="score">` with `<option value="">All</option>` sends `score=` in query string. FastAPI's `score: int | None = Query(None)` cannot parse empty string as int, returning 422 validation error. This broke all filter operations in real browser (not caught by TestClient because TestClient doesn't submit forms via HTML).
- **Fix:** Changed `score` parameter type from `int | None` to `str | None` in 5 endpoints (dashboard, search, bulk_status, export_csv, export_json). Added `_parse_score()` helper that converts empty string to None and parses valid strings to int.
- **Files modified:** webapp/app.py
- **Commit:** 39fdda5

**2. [Rule 1 - Bug] page.wait_for_response() does not exist in Playwright sync API**
- **Found during:** Task 3
- **Issue:** Plan referenced `page.wait_for_response()` which is not a valid Playwright sync API method. The correct API is `page.expect_response()` used as a context manager.
- **Fix:** Changed to `with page.expect_response(lambda r: "/status" in r.url): page.click(...)` pattern
- **Files modified:** tests/e2e/test_status.py
- **Commit:** 2322837

## Issues Encountered

None beyond the deviations documented above. All 6 tests pass reliably in headless Chromium.

## Next Phase Readiness

Plan 15-02 (kanban drag-and-drop, export downloads, CI command fix) can proceed. The live_server and seeded_db fixtures from this plan provide the foundation. Additional fixtures for kanban-specific data may be needed.

## Self-Check: PASSED

All 4 created files verified on disk. All 3 task commits verified in git log.
