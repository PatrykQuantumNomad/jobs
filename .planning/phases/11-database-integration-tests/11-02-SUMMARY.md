---
phase: 11-database-integration-tests
plan: "02"
subsystem: database
tags: [fts5, search, activity-log, integration-tests, sqlite]
dependency_graph:
  requires: ["11-01"]
  provides: ["DB-02", "DB-03"]
  affects: ["webapp/db.py", "tests/webapp/test_db.py"]
tech_stack:
  added: []
  patterns: ["FTS5 prefix matching tests", "activity log lifecycle tests", "ORDER BY tiebreaker fix"]
key_files:
  created: []
  modified:
    - tests/webapp/test_db.py
    - webapp/db.py
decisions:
  - "Fixed get_activity_log ORDER BY to use id DESC tiebreaker for same-second events"
  - "Special character FTS5 tests use try/except for known sqlite3.OperationalError limitation"
metrics:
  duration: "4 min"
  completed: "2026-02-08"
  tasks: 2
  tests_added: 22
  total_tests_in_file: 68
  coverage_webapp_db: "91%"
---

# Phase 11 Plan 02: FTS5 Search and Activity Log Tests Summary

FTS5 full-text search integration tests (12) covering prefix matching, multi-column search, sync-after-upsert, combined filters, and special character handling; activity log tests (10) covering auto-discovered events, status chain tracking, notes logging, and full lifecycle trail -- with a bug fix for same-second ordering in get_activity_log.

## Accomplishments

### Task 1: FTS5 Search Tests (DB-02) -- `aeb724f`

Added `TestFts5Search` class with 12 tests:

| Test | Behavior Verified |
|------|-------------------|
| `test_search_by_title_keyword` | Single keyword matches title field |
| `test_search_by_company_keyword` | Company name search returns correct job only |
| `test_search_by_description_keyword` | Description keyword matching |
| `test_search_prefix_matching` | Partial word "kube" matches "kubernetes" |
| `test_search_multi_word_prefix` | Both words get prefix wildcard |
| `test_search_no_match_returns_empty` | Non-matching query returns [] not error |
| `test_search_empty_string_returns_all` | Empty string = no filter |
| `test_search_none_returns_all` | None = no filter |
| `test_fts_sync_after_upsert_update` | FTS index updates when description replaced via upsert (LENGTH comparison) |
| `test_fts_with_combined_filters` | FTS search + score_min returns intersection |
| `test_search_special_chars_no_crash` | C++, node.js, @company handled gracefully |
| `test_fts_operator_passthrough` | Quoted strings bypass prefix wildcard addition |

### Task 2: Activity Log Tests (DB-03) -- `221cc54`

Added `TestActivityLog` class with 10 tests:

| Test | Behavior Verified |
|------|-------------------|
| `test_upsert_new_job_logs_discovered` | Auto "discovered" event on new job |
| `test_upsert_existing_job_no_duplicate_discovered` | Re-upsert doesn't duplicate event |
| `test_status_change_logged` | Status change records old/new values |
| `test_multiple_status_changes_tracked` | 3-step chain with correct old->new links |
| `test_notes_update_logged` | note_added event with detail text |
| `test_activity_log_has_timestamps` | All entries have non-null created_at |
| `test_activity_log_newest_first` | Most recent event at index 0 |
| `test_activity_log_empty_for_nonexistent_key` | Returns [] for unknown key |
| `test_log_activity_direct` | Direct log_activity() with custom fields |
| `test_full_lifecycle_activity_trail` | 5 events across full lifecycle |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed non-deterministic activity log ordering**
- **Found during:** Task 2 -- `test_multiple_status_changes_tracked` and `test_activity_log_newest_first` failed
- **Issue:** `get_activity_log()` used `ORDER BY created_at DESC` but events within the same second (sub-second SQLite precision) had identical timestamps, producing undefined ordering
- **Fix:** Changed to `ORDER BY created_at DESC, id DESC` -- the autoincrement `id` column provides a deterministic tiebreaker for same-second events
- **Files modified:** `webapp/db.py`
- **Commit:** `221cc54`

## Verification Results

- `uv run pytest tests/webapp/test_db.py -v` -- 68 tests pass (46 from 11-01 + 22 from 11-02)
- `uv run pytest tests/webapp/test_db.py -m integration` -- all 68 marked as integration
- `uv run pytest tests/webapp/test_db.py --cov=webapp` -- webapp/db.py at 91% coverage
- `uv run pytest tests/ -v -q` -- 285 total tests pass, zero regressions

## Test Classes in tests/webapp/test_db.py

| Class | Requirement | Tests | Source |
|-------|-------------|-------|--------|
| TestCrudLifecycle | DB-01 | 25 | 11-01 |
| TestBulkOperations | DB-04 | 5 | 11-01 |
| TestRunHistory | DB-01 | 3 | 11-01 |
| TestStats | DB-01 | 3 | 11-01 |
| TestBackfillScoreBreakdowns | DB-04 | 3 | 11-01 |
| TestSchemaInitialization | DB-05 | 7 | 11-01 |
| **TestFts5Search** | **DB-02** | **12** | **11-02** |
| **TestActivityLog** | **DB-03** | **10** | **11-02** |
| **Total** | | **68** | |

## Self-Check: PASSED

All files exist. All commit hashes verified.
