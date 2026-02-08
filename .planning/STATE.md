# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-08)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** Phase 10 -- Unit Tests (v1.1 Test Web App)

## Current Position

Phase: 10 of 15 (Unit Tests)
Plan: 1 of 3 in current phase
Status: Plan 01 complete
Last activity: 2026-02-08 -- Completed 10-01-PLAN.md (models and salary unit tests)

Progress: [###########################.........] 77% (27/39 total plans -- 24 v1.0 + 3 v1.1 complete, 12 v1.1 TBD)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 24 (+ 6 docs/verification)
- Average duration: 4.2 min per plan
- Total execution time: ~126 min

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-config-externalization | 3/3 | 16 min | 5.3 min |
| 02-platform-architecture | 2/2 | 9 min | 4.5 min |
| 03-discovery-engine | 3/3 | 15 min | 5.0 min |
| 04-scheduled-automation | 2/2 | 8 min | 4.0 min |
| 05-dashboard-core | 4/4 | 12 min | 3.0 min |
| 06-dashboard-analytics | 2/2 | 8 min | 4.0 min |
| 07-ai-resume-cover-letter | 4/4 | 22 min | 5.5 min |
| 08-one-click-apply | 4/4 | 15 min | 3.8 min |

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 09-test-infrastructure | 2/2 | -- | -- |
| 10-unit-tests | 1/3 | 3 min | 3.0 min |

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.
v1.1-relevant from research:
- Import-time side effects in webapp/db.py must be handled via JOBFLOW_TEST_DB=1 before imports
- No Playwright mocking for scraper tests -- extract pure parsing functions instead
- E2E tests CI-optional (separate job, not blocking)

From 09-01:
- Strict asyncio mode (force explicit @pytest.mark.asyncio on async tests)
- Socket disabled by default (--allow-unix-socket for SQLite)
- E2e excluded from default run (-m "not e2e")
- Browser platform files omitted from coverage
- test_config.yaml loaded via AppSettings.model_config['yaml_file'] override + reset_settings()

From 09-02:
- JOBFLOW_TEST_DB=1 and ANTHROPIC_API_KEY set before any imports in conftest.py
- Factory-boy Meta.model=Job triggers Pydantic validation automatically
- salary_max uses LazyAttribute to reference salary_min for cross-field guarantee
- Anthropic guard patches Messages.create/parse at method level (not constructor)

From 10-01:
- Unit test files mirror source: tests/test_{module}.py
- All unit tests marked @pytest.mark.unit at class level
- Parametrize tables use explicit IDs for readable output
- 100% coverage on models.py and salary.py (141 statements, 0 missed)

### Pending Todos

None.

### Blockers/Concerns

- Python 3.14 compatibility in CI: verify `actions/setup-python@v5` supports it
- SSE endpoint testing: TestClient + EventSourceResponse interaction needs careful design

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Fix technical debt: remove Config shim, dead static mount, update arch docs | 2026-02-08 | 9f7f3de | [001-fix-technical-debt](./quick/001-fix-technical-debt/) |

## Session Continuity

Last session: 2026-02-08
Stopped at: Completed 10-01-PLAN.md (models and salary unit tests). Ready for 10-02.
Resume file: .planning/phases/10-unit-tests/10-02-PLAN.md
