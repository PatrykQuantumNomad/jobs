---
phase: 03-discovery-engine
plan: 02
subsystem: database, pipeline
tags: [sqlite, migration, delta-tracking, salary-normalization, fuzzy-dedup, score-breakdown]

# Dependency graph
requires:
  - phase: 03-discovery-engine/plan-01
    provides: salary.py, dedup.py, scorer.py ScoreBreakdown, models.py new fields
  - phase: 01-config-externalization
    provides: AppSettings, ScoringWeights, CandidateProfile, get_settings()
provides:
  - "webapp/db.py: versioned schema migration (PRAGMA user_version), delta tracking (mark_viewed, remove_stale_jobs, backfill_score_breakdowns)"
  - "webapp/db.py: upsert_job with 7 new columns (first_seen_at, last_seen_at, viewed_at, score_breakdown, company_aliases, salary_display, salary_currency)"
  - "orchestrator.py: wired pipeline using salary.parse_salary, dedup.fuzzy_deduplicate, scorer.score_batch_with_breakdown"
  - "orchestrator.py: delta cleanup (remove_stale_jobs scoped to searched platforms)"
affects: [03-03-PLAN (dashboard UI uses new columns), 04-01-PLAN (scheduled runs use delta tracking)]

# Tech tracking
tech-stack:
  added: []
  patterns: [pragma-user-version-migration, idempotent-alter-table, platform-scoped-stale-removal, in-memory-test-db]

key-files:
  created: []
  modified: [webapp/db.py, orchestrator.py]

key-decisions:
  - "JOBFLOW_TEST_DB=1 env var for in-memory SQLite in tests -- avoids touching production DB"
  - "Singleton connection for in-memory DBs to share state across get_conn() calls"
  - "ON CONFLICT preserves first_seen_at (not in SET clause), updates last_seen_at"
  - "backfill_score_breakdowns filters Job fields to model_fields to avoid SQLite column names breaking Pydantic"
  - "Removed old _deduplicate method entirely -- fuzzy_deduplicate is the sole dedup path"

patterns-established:
  - "PRAGMA user_version migration: read version, run pending ALTER TABLEs, set new version"
  - "Idempotent ALTER TABLE: catch 'duplicate column name' OperationalError, re-raise others"
  - "Platform-scoped stale removal: only delete from platforms that were actually searched this run"

# Metrics
duration: 5min
completed: 2026-02-07
---

# Phase 3 Plan 2: DB Migration and Orchestrator Wiring Summary

**Versioned SQLite schema migration (v0->v2) with 7 new columns, and orchestrator pipeline wired to use salary normalization, fuzzy dedup, score breakdowns, and platform-scoped stale job removal**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-07T18:45:10Z
- **Completed:** 2026-02-07T18:50:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- webapp/db.py migrates schema from v0 to v2 idempotently via PRAGMA user_version, adding 7 new columns with backfill
- upsert_job preserves first_seen_at on conflict while updating last_seen_at, score_breakdown, company_aliases, salary_display, salary_currency
- orchestrator.phase_3_score now uses salary.parse_salary for normalization, dedup.fuzzy_deduplicate for dedup, scorer.score_batch_with_breakdown for scoring, and webdb.upsert_job for persistence
- remove_stale_jobs is scoped to searched platforms only -- skipped platforms (e.g., login failure) keep their jobs intact
- backfill_score_breakdowns re-scores legacy jobs that have a score but no breakdown

## Task Commits

Each task was committed atomically:

1. **Task 1: Add versioned schema migration and new DB functions to webapp/db.py** - `2893bc3` (feat)
2. **Task 2: Wire new modules into orchestrator.py phase_3_score and add delta tracking** - `de9518b` (feat)

## Files Created/Modified
- `webapp/db.py` - Versioned schema migration (SCHEMA_VERSION=2), upsert_job with 7 new columns, mark_viewed, remove_stale_jobs, backfill_score_breakdowns, JOBFLOW_TEST_DB support
- `orchestrator.py` - Imports salary/dedup/scorer/webdb, salary normalization in phase_3_score, fuzzy_deduplicate replaces _deduplicate, score_batch_with_breakdown replaces score_batch, delta cleanup after scoring, backfill breakdowns, salary_display in tracker/descriptions/apply

## Decisions Made
- Added JOBFLOW_TEST_DB=1 env var for in-memory SQLite testing -- plan's verification used it and it's a clean pattern for test isolation
- Used singleton connection pattern for in-memory DBs to maintain shared state across get_conn() calls
- ON CONFLICT clause deliberately excludes first_seen_at from SET -- original insert timestamp preserved forever
- backfill_score_breakdowns filters dict keys through Job.model_fields to avoid passing SQLite-only column names to Pydantic constructor
- Removed old _deduplicate method entirely rather than keeping it as fallback -- fuzzy_deduplicate subsumes all its behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added JOBFLOW_TEST_DB env var support to webapp/db.py**
- **Found during:** Task 1
- **Issue:** Plan verification code used `os.environ['JOBFLOW_TEST_DB'] = '1'` but db.py had no test DB support. Module-level `init_db()` would always connect to the production SQLite file.
- **Fix:** Added `_USE_MEMORY` flag and singleton `_memory_conn` for in-memory SQLite when JOBFLOW_TEST_DB=1
- **Files modified:** webapp/db.py
- **Verification:** All test assertions pass with in-memory DB
- **Committed in:** 2893bc3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for test isolation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 new DB columns ready for dashboard UI (plan 03-03): first_seen_at for NEW badges, score_breakdown for inline display, salary_display for formatted salaries, company_aliases for tooltip
- Delta tracking (remove_stale_jobs, mark_viewed) ready for scheduled automation (phase 4)
- End-to-end pipeline flow verified: raw jobs -> salary normalize -> fuzzy dedup -> score with breakdown -> persist to DB -> remove stale

---
*Phase: 03-discovery-engine*
*Completed: 2026-02-07*
