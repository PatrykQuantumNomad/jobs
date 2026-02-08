---
phase: 12-web-api-integration-tests
plan: 02
subsystem: testing
tags: [fastapi, pytest, integration-tests, csv-export, json-export, bulk-status, import, testclient]

requires:
  - phase: 09-test-infrastructure
    provides: conftest fixtures (_fresh_db, client, db_with_jobs), pytest config
  - phase: 11-database-integration-tests
    provides: DB layer test patterns (_make_job_dict, _compute_dedup_key)
  - phase: 12-01
    provides: TestClient threading fix, existing test_endpoints.py with 30 tests
provides:
  - WEB-04 CSV export endpoint tests with parseability and 10-field header verification
  - WEB-05 JSON export endpoint tests with 12-field schema and filtering
  - WEB-06 bulk status endpoint tests with selective changes and no-op edge cases
  - WEB-07 import endpoint tests with pipeline JSON reading and redirect behavior
  - Complete WEB-* endpoint coverage (all 8 requirements tested across 12-01 + 12-02)
affects: [12-03, 15-e2e-tests]

tech-stack:
  added: []
  patterns:
    - "csv.DictReader(io.StringIO(response.text)) for CSV StreamingResponse testing"
    - "json.loads(response.text) for JSON StreamingResponse testing (not response.json())"
    - "Pipeline file backup/restore pattern for import endpoint tests without monkeypatching"
    - "Explicit None-check assertions before dict subscript for pyright compatibility"

key-files:
  created: []
  modified:
    - tests/webapp/test_endpoints.py

key-decisions:
  - "Used real pipeline directory with backup/restore instead of monkeypatching for import tests -- simpler and more realistic"
  - "CSV parsed via csv.DictReader, JSON via json.loads(response.text) since both use StreamingResponse"
  - "All get_job() results checked for None before subscripting to satisfy pyright strict mode"

duration: 4min
completed: 2026-02-08
---

# Phase 12 Plan 02: Export, Bulk Status, and Import Endpoint Tests Summary

**26 integration tests for CSV/JSON export (WEB-04/05), bulk status (WEB-06), and pipeline import (WEB-07) endpoints using TestClient with in-memory SQLite**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-08T17:50:07Z
- **Completed:** 2026-02-08T17:54:07Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- TestCsvExport: 8 tests verifying CSV structure, csv.DictReader parseability, 10-field headers, data accuracy, platform filtering, and empty DB
- TestJsonExport: 8 tests verifying JSON structure, json.loads parseability, 12-field schema, data accuracy, score filtering, and empty DB
- TestBulkStatusEndpoint: 6 tests verifying selective status changes, no-op on missing/empty keys, HTML response, and activity logging
- TestImportEndpoint: 4 tests verifying pipeline JSON import, 303 redirect with count, raw platform file import, and redirect following
- All 56 endpoint tests pass (30 from Plan 12-01 + 26 new), completing full WEB-* requirement coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: CSV and JSON export endpoint tests (WEB-04, WEB-05)** - `1258a64` (test)
2. **Task 2: Bulk status and import endpoint tests (WEB-06, WEB-07)** - `0505957` (test)

## Files Created/Modified
- `tests/webapp/test_endpoints.py` - Added 26 tests in 4 new classes (TestCsvExport, TestJsonExport, TestBulkStatusEndpoint, TestImportEndpoint) plus csv/io/json imports and helper functions

## Decisions Made
- Used real `job_pipeline/` directory with backup/restore for import tests instead of monkeypatching the route handler -- this tests the actual code path and avoids reimplementing the import logic in the test
- Parsed CSV via `csv.DictReader(io.StringIO(response.text))` and JSON via `json.loads(response.text)` since both endpoints return `StreamingResponse` (not `JSONResponse`)
- Added explicit `assert ... is not None` before every `get_job()` subscript access to satisfy pyright strict type checking

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Linter (ruff) auto-removed `csv`, `io`, `json` imports when they were added before the test code that uses them -- resolved by adding the imports in the same edit that added the test classes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 12 is now complete: all 3 plans (12-01, 12-02, 12-03) are done
- 56 endpoint tests + 42 platform tests = 98 total web/API integration tests
- Ready for Phase 13 (Config Integration Tests) and Phase 14 (CI Pipeline)

---
*Phase: 12-web-api-integration-tests*
*Completed: 2026-02-08*
