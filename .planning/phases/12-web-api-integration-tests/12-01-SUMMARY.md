---
phase: 12-web-api-integration-tests
plan: 01
subsystem: testing
tags: [fastapi, pytest, integration-tests, htmx, sqlite, fts5, testclient]

# Dependency graph
requires:
  - phase: 09-test-infrastructure
    provides: conftest fixtures (_fresh_db, client, db_with_jobs), pytest config
  - phase: 11-database-integration-tests
    provides: DB layer test patterns (_make_job_dict, _compute_dedup_key)
provides:
  - WEB-01 dashboard endpoint tests with filtering (score, platform, status)
  - WEB-02 job detail endpoint tests with description, activity log, viewed_at
  - WEB-03 status update and notes update endpoint tests with HX-Trigger
  - WEB-08 search endpoint tests with FTS5 query filtering
  - TestClient threading fix for async FastAPI + in-memory SQLite
affects: [12-02, 12-03, 15-e2e-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TestClient(app) with check_same_thread=False for async endpoint testing"
    - "Form data via data= kwarg (not json=) for FastAPI Form(...) endpoints"
    - "response.text assertions for HTML endpoint testing"
    - "Partial HTML detection (no <!DOCTYPE) for htmx fragment endpoints"

key-files:
  created:
    - tests/webapp/test_endpoints.py
  modified:
    - webapp/db.py

key-decisions:
  - "Added check_same_thread=False to in-memory SQLite connection for TestClient thread safety"
  - "POST endpoints tested with data= (form encoding) not json= to match FastAPI Form(...) parameter declarations"
  - "All 30 tests written in single file with 5 test classes matching endpoint groups"

patterns-established:
  - "Endpoint test pattern: seed DB via db_module.upsert_job(), call via client.get/post, assert response.text"
  - "Status badge assertion: check 'status-badge' class and title-cased label in response HTML"
  - "HX-Trigger header assertion: response.headers.get('HX-Trigger') == 'statsChanged'"

# Metrics
duration: 4min
completed: 2026-02-08
---

# Phase 12 Plan 01: Dashboard, Detail, Status, and Search Endpoint Tests Summary

**30 integration tests for FastAPI web endpoints covering dashboard filtering, job detail rendering, status/notes updates with htmx triggers, and FTS5 search through the API layer**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-08T17:36:38Z
- **Completed:** 2026-02-08T17:40:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- TestDashboardEndpoint: 9 tests verifying empty DB, job visibility, score/platform/status filtering, wrong filters return empty (not errors), sort ordering, filter controls in HTML
- TestSearchEndpoint: 5 tests verifying 200 response, partial HTML (no full page), FTS5 query filtering, combined search+score filter, empty query returns all
- TestJobDetailEndpoint: 6 tests verifying detail rendering, description display, activity log visibility, viewed_at auto-set, 404 for nonexistent, special chars in dedup key
- TestStatusUpdateEndpoint: 6 tests verifying 200 response, DB persistence, badge HTML, HX-Trigger header, activity logging, applied_date auto-set
- TestNotesUpdateEndpoint: 4 tests verifying 200 response, notes persistence, confirmation HTML, activity logging
- Fixed SQLite thread safety for TestClient async endpoint testing

## Task Commits

Each task was committed atomically:

1. **Task 1: Dashboard + search endpoint tests (WEB-01, WEB-08) + detail/status/notes tests (WEB-02, WEB-03)** - `51c82d6` (test)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `tests/webapp/test_endpoints.py` - 30 integration tests across 5 test classes (WEB-01, WEB-02, WEB-03, WEB-08)
- `webapp/db.py` - Added check_same_thread=False to in-memory SQLite connection for cross-thread TestClient access

## Decisions Made
- **check_same_thread=False for test DB:** FastAPI's TestClient runs async endpoints in a worker thread, but the in-memory SQLite connection was created in the main test thread. Added `check_same_thread=False` only for the in-memory (test) path since the singleton connection pattern already prevents concurrent writes.
- **Form data encoding:** All POST endpoint tests use `data=` kwarg (not `json=`) because the FastAPI routes use `Form(...)` parameter declarations, which expect form-encoded bodies.
- **Single commit for both tasks:** Since Task 2 ("append to file") and Task 1 ("create file") targeted the same file, all 30 tests were written in the initial file creation for efficiency. Both tasks share one commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed SQLite cross-thread access for TestClient**
- **Found during:** Task 1 (initial test run)
- **Issue:** All 30 tests failed with `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` because FastAPI's TestClient runs async route handlers in a separate thread, but the in-memory SQLite singleton was created in the main test thread.
- **Fix:** Added `check_same_thread=False` to `sqlite3.connect(":memory:", check_same_thread=False)` in `webapp/db.py` get_conn(). This only affects the test-mode in-memory path (when `JOBFLOW_TEST_DB=1`), not production file-based connections.
- **Files modified:** webapp/db.py (line 159)
- **Verification:** All 30 endpoint tests pass; all 315 tests in full suite pass (zero regressions)
- **Committed in:** 51c82d6 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for TestClient to work with the async endpoint + in-memory SQLite pattern. No scope creep.

## Issues Encountered
- Pyright flagged 5 instances of `db_module.get_job(key)["field"]` as potentially subscripting None. Fixed by adding explicit `assert row is not None` before subscript access.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Endpoint test pattern established and reusable for 12-02 (export, bulk, import endpoints)
- check_same_thread fix ensures all future FastAPI endpoint tests work correctly
- No blockers for Phase 12 Plan 02

---
*Phase: 12-web-api-integration-tests*
*Completed: 2026-02-08*
