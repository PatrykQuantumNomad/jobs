# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-08)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** Phase 12 -- Web & API Integration Tests (v1.1 Test Web App)

## Current Position

Phase: 12 of 15 (Web & API Integration Tests)
Plan: 3 of 3 in current phase
Status: In progress
Last activity: 2026-02-08 -- Completed 12-03-PLAN.md (RemoteOK parsing/error handling + platform registry/protocol tests).

Progress: [################################....] 90% (34/39 total plans -- 24 v1.0 + 10 v1.1 complete, 5 v1.1 TBD)

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
| 10-unit-tests | 3/3 | 11 min | 3.7 min |
| 11-database-integration-tests | 2/2 | 8 min | 4.0 min |
| 12-web-api-integration-tests | 2/3 | 11 min | 5.5 min |

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

From 10-02:
- Scorer tests use explicit CandidateProfile/ScoringWeights (no config.yaml dependency)
- Default weights formula: raw = title_pts + tech_pts + remote_pts + salary_pts
- 92% coverage of scorer.py (uncovered: score_batch_with_breakdown only)
- Tags concatenated into search text for tech keyword matching

From 10-03:
- Reordered text validator test uses lowercase skill names to avoid regex false positives
- Delta tests use direct SQL UPDATE (_set_last_seen helper) for deterministic timestamps
- dedup.py 96% coverage, resume_ai/validator.py 98% coverage
- 67 new tests across 3 files (33 + 23 + 11)

From 11-01:
- All DB integration tests marked @pytest.mark.integration (not unit -- they touch SQLite)
- Direct SQL for score/breakdown manipulation in backfill tests (bypasses COALESCE in upsert)
- Schema tests use set comparison against sqlite_master for order-independent verification
- 46 new tests in 1 file, 85% webapp/db.py coverage

From 11-02:
- Fixed get_activity_log ORDER BY to use id DESC tiebreaker for same-second events
- Special character FTS5 tests use try/except for known sqlite3.OperationalError limitation
- FTS sync test uses short-then-long description to trigger LENGTH comparison in ON CONFLICT
- 22 new tests (12 FTS5 + 10 activity log), 91% webapp/db.py coverage, 68 total in file

From 12-01:
- Added check_same_thread=False to in-memory SQLite for TestClient thread safety
- POST endpoints tested with data= (form encoding) not json= for FastAPI Form(...) parameters
- Partial HTML detection: assert no <!DOCTYPE or <html> for htmx fragment endpoints
- 30 new tests (9 dashboard + 5 search + 6 detail + 6 status + 4 notes)

From 12-03:
- Fixed registry.py inspect.signature() for Python 3.14: use Format.FORWARDREF to avoid resolving TYPE_CHECKING annotations
- Fixed except clause from Python 2 comma syntax to proper tuple syntax in registry.py
- RemoteOK tests use local remoteok_platform fixture (loads test config + calls init())
- Registry tests import platforms package for auto-discovery, test metadata without calling init()
- 42 new tests (17 parsing + 5 error handling + 11 registry + 9 protocol compliance)

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
Stopped at: Completed 12-03-PLAN.md (RemoteOK parsing/error handling + platform registry/protocol tests). Ready for 12-02.
Resume file: .planning/phases/12-web-api-integration-tests/
