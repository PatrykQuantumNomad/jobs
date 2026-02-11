---
phase: 17-ai-scoring
plan: 01
subsystem: ai, database
tags: [claude-cli, pydantic, structured-output, sqlite, scoring]

# Dependency graph
requires:
  - phase: 16-cli-wrapper
    provides: claude_cli.run() async subprocess wrapper, CLIError hierarchy, mock_claude_cli fixture
provides:
  - AIScoreResult Pydantic model for structured CLI scoring output
  - score_job_ai() async function calling Claude CLI with scoring rubric
  - Database migration v7 adding ai_score columns to jobs table
  - update_ai_score() function for persisting AI scores with activity logging
  - mock_claude_cli fixture in root conftest (available to all tests)
affects: [17-02-dashboard-endpoint, webapp]

# Tech tracking
tech-stack:
  added: []
  patterns: [CLI structured output for scoring, CLIError->RuntimeError boundary wrapping]

key-files:
  created:
    - ai_scorer.py
    - tests/test_ai_scorer.py
  modified:
    - webapp/db.py
    - tests/conftest.py
    - tests/resume_ai/conftest.py
    - tests/webapp/test_db.py

key-decisions:
  - "Single-module ai_scorer.py at project root (not a package) -- feature is small enough"
  - "mock_claude_cli fixture moved to root conftest for cross-module test availability"
  - "Schema version assertions use db_module.SCHEMA_VERSION instead of hardcoded integers"

patterns-established:
  - "AI scoring follows same pattern as resume_ai/tailor.py: structured output model + async function + CLIError wrapping"
  - "Scoring rubric embedded in SYSTEM_PROMPT with 1-5 scale and explicit evaluation criteria"

# Metrics
duration: 5min
completed: 2026-02-11
---

# Phase 17 Plan 01: AI Scoring Backend Summary

**AIScoreResult structured output model + score_job_ai() async function using Claude CLI, with DB migration v7 for AI score columns and 6 unit/integration tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-11T16:38:05Z
- **Completed:** 2026-02-11T16:43:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- AIScoreResult Pydantic model with constrained score (1-5), reasoning, strengths, and gaps fields with descriptive JSON schema
- Async score_job_ai() function following the established tailor.py pattern (CLI call + CLIError wrapping)
- Database migration v7 adding ai_score, ai_score_breakdown, ai_scored_at columns
- update_ai_score() function persisting scores and logging ai_scored activity events
- mock_claude_cli fixture promoted to root conftest for project-wide test availability
- 6 new tests covering: CLI success flow, error wrapping, score validation, schema constraints, DB persistence, activity logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ai_scorer.py with AIScoreResult model and score_job_ai function** - `8cbb001` (feat)
2. **Task 2: Add database migration v7, update_ai_score function, and unit tests** - `f545cef` (feat)

## Files Created/Modified
- `ai_scorer.py` - AI scoring module: AIScoreResult model, SYSTEM_PROMPT rubric, score_job_ai() async function
- `webapp/db.py` - SCHEMA_VERSION 7, migration v7 (3 AI score columns), update_ai_score() function
- `tests/test_ai_scorer.py` - 6 tests: scorer logic, validation, CLI error wrapping, db persistence, activity logging
- `tests/conftest.py` - mock_claude_cli fixture moved here from resume_ai/conftest.py
- `tests/resume_ai/conftest.py` - Emptied (fixture moved to root conftest)
- `tests/webapp/test_db.py` - Fixed hardcoded schema version assertions to use SCHEMA_VERSION constant

## Decisions Made
- Single-module ai_scorer.py at project root (not a package) -- the AI scoring feature is small enough to fit in one file, paralleling scorer.py
- Moved mock_claude_cli from tests/resume_ai/conftest.py to tests/conftest.py -- needed by both resume_ai and ai_scorer tests
- Schema version test assertions now reference db_module.SCHEMA_VERSION instead of hardcoded integers -- prevents breakage on future migrations

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hardcoded schema version assertions in test_db.py**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** Two tests in tests/webapp/test_db.py hardcoded `assert version == 6`, which broke after SCHEMA_VERSION bump to 7
- **Fix:** Changed both assertions to `assert version == db_module.SCHEMA_VERSION`
- **Files modified:** tests/webapp/test_db.py
- **Verification:** Full test suite passes (569 tests)
- **Committed in:** f545cef (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for test correctness after schema version bump. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AI scoring backend complete: model, function, database storage, tests all verified
- Ready for plan 17-02: dashboard endpoint wiring (POST /jobs/{key}/ai-score, SSE streaming, htmx UI)
- mock_claude_cli fixture available project-wide for 17-02 tests

## Self-Check: PASSED

- ai_scorer.py: FOUND
- tests/test_ai_scorer.py: FOUND (108 lines)
- .planning/phases/17-ai-scoring/17-01-SUMMARY.md: FOUND
- Commit 8cbb001 (Task 1): FOUND
- Commit f545cef (Task 2): FOUND
- Full test suite: 569 passed, 0 failed

---
*Phase: 17-ai-scoring*
*Completed: 2026-02-11*
