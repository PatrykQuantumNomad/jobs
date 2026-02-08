---
phase: 09-test-infrastructure
plan: 02
subsystem: testing
tags: [pytest, conftest, factory-boy, isolation-fixtures, smoke-tests, anthropic-guard]

# Dependency graph
requires:
  - phase: 09-test-infrastructure
    plan: 01
    provides: pytest config, test directory structure, test_config.yaml
  - phase: 01-config-externalization
    provides: AppSettings singleton with reset_settings()
provides:
  - Root conftest.py with 3 autouse fixtures (settings reset, fresh DB, Anthropic guard) and 1 opt-in fixture (db_with_jobs)
  - conftest_factories.py with JobFactory producing valid Pydantic v2 Job instances
  - Sub-directory conftest files for webapp (TestClient), platforms (mock_remoteok_api), resume_ai (mock_anthropic)
  - 13 smoke tests validating the entire test infrastructure
affects: [all future test plans in phases 10-15]

# Tech tracking
tech-stack:
  added: []
  patterns: [autouse fixture isolation, JOBFLOW_TEST_DB env guard, factory-boy with Pydantic v2, monkeypatch Anthropic guard]

key-files:
  created:
    - tests/conftest.py
    - tests/conftest_factories.py
    - tests/webapp/conftest.py
    - tests/platforms/conftest.py
    - tests/resume_ai/conftest.py
    - tests/test_smoke.py
  modified: []

key-decisions:
  - "JOBFLOW_TEST_DB=1 and ANTHROPIC_API_KEY set as first executable lines before any project imports"
  - "Factory-boy Meta.model=Job works because it calls Job(field=val) triggering Pydantic validation"
  - "salary_max uses LazyAttribute (not LazyFunction) to access obj.salary_min for cross-field guarantee"
  - "Anthropic guard patches Messages.create and Messages.parse, not the client constructor"

patterns-established:
  - "Pattern: conftest.py env vars before imports to control import-time side effects"
  - "Pattern: _fresh_db fixture closes/nulls _memory_conn, calls init_db() for clean schema each test"
  - "Pattern: JobFactory(platform=X, score=Y) for controlled test data with Pydantic validation"
  - "Pattern: mock_anthropic fixture overrides autouse _block_anthropic for resume_ai tests"

# Metrics
duration: 2min
completed: 2026-02-08
---

# Phase 9 Plan 2: Test Fixtures and Smoke Tests Summary

**Root conftest.py with settings/DB/Anthropic isolation fixtures, Factory Boy JobFactory, 3 sub-directory conftest files, and 13 passing smoke tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-08T14:16:39Z
- **Completed:** 2026-02-08T14:19:20Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Root conftest.py with 3 autouse fixtures providing per-test isolation (settings singleton reset, fresh in-memory SQLite, Anthropic API guard) plus db_with_jobs opt-in fixture seeding 10 jobs
- conftest_factories.py with JobFactory that produces valid Pydantic v2 Job instances with guaranteed salary_max >= salary_min
- Sub-directory conftest files: TestClient for webapp, mock_remoteok_api with respx for platforms, mock_anthropic for resume_ai
- 13 smoke tests all passing: factory validation, settings isolation, DB isolation, seeded DB, Anthropic guard, socket blocking, environment vars

## Task Commits

Each task was committed atomically:

1. **Task 1: Create root conftest.py with isolation fixtures and conftest_factories.py** - `fb33826` (feat)
2. **Task 2: Create sub-directory conftest files and smoke tests** - `8dcb184` (feat)

## Files Created/Modified
- `tests/conftest.py` - Global autouse fixtures (settings reset, fresh DB, Anthropic guard) and db_with_jobs opt-in fixture
- `tests/conftest_factories.py` - Factory Boy JobFactory with Pydantic v2 cross-field validation
- `tests/webapp/conftest.py` - FastAPI TestClient fixture backed by in-memory DB
- `tests/platforms/conftest.py` - mock_remoteok_api fixture with respx and realistic sample response
- `tests/resume_ai/conftest.py` - mock_anthropic fixture overriding autouse guard
- `tests/test_smoke.py` - 13 smoke tests validating the entire test infrastructure

## Decisions Made
- Set `JOBFLOW_TEST_DB=1` and `ANTHROPIC_API_KEY` as first executable lines in conftest.py (before any project imports) to control import-time side effects in webapp/db.py
- Used `factory.LazyAttribute` (not `LazyFunction`) for salary_max so it can reference `obj.salary_min` to guarantee the cross-field Pydantic constraint
- Patched `anthropic.resources.messages.Messages.create` and `.parse` (the method level) rather than the client constructor, so the guard catches calls regardless of how the client was instantiated
- Used `import config` and checked `config._settings` directly in settings isolation tests to verify the singleton is properly reset

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All test infrastructure is in place for writing actual tests
- Fixtures provide: settings isolation, fresh DB per test, blocked network, blocked Anthropic, mock APIs
- 13 smoke tests confirm infrastructure works -- any regression will surface immediately
- Ready for Phase 10+ test implementation plans

## Self-Check: PASSED

All 6 files verified present. Both task commits (fb33826, 8dcb184) verified in git log.

---
*Phase: 09-test-infrastructure*
*Completed: 2026-02-08*
