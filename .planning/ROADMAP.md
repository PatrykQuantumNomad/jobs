# Roadmap: JobFlow

## Milestones

- SHIPPED **v1.0 MVP** -- Phases 1-8 (shipped 2026-02-08)
- IN PROGRESS **v1.1 Test Web App** -- Phases 9-15

## Phases

<details>
<summary>SHIPPED v1.0 MVP (Phases 1-8) -- SHIPPED 2026-02-08</summary>

- [x] Phase 1: Config Externalization (3/3 plans) -- completed 2026-02-07
- [x] Phase 2: Platform Architecture (2/2 plans) -- completed 2026-02-07
- [x] Phase 3: Discovery Engine (3/3 plans) -- completed 2026-02-07
- [x] Phase 4: Scheduled Automation (2/2 plans) -- completed 2026-02-07
- [x] Phase 5: Dashboard Core (4/4 plans) -- completed 2026-02-07
- [x] Phase 6: Dashboard Analytics (2/2 plans) -- completed 2026-02-07
- [x] Phase 7: AI Resume & Cover Letter (4/4 plans) -- completed 2026-02-07
- [x] Phase 8: One-Click Apply (4/4 plans) -- completed 2026-02-08

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

### v1.1 Test Web App (In Progress)

**Milestone Goal:** Comprehensive automated test suite with CI pipeline covering all application layers -- unit/integration (pytest) + E2E (Playwright) for scoring, deduplication, dashboard, platform scrapers (mocked), and apply flow. 80%+ coverage target, CI-ready on GitHub Actions.

- [x] **Phase 9: Test Infrastructure** - Fixtures, isolation, and pytest configuration -- completed 2026-02-08
- [ ] **Phase 10: Unit Tests** - Pure logic modules with zero I/O dependencies
- [ ] **Phase 11: Database Integration Tests** - SQLite CRUD, FTS5, migrations
- [ ] **Phase 12: Web & API Integration Tests** - FastAPI routes, RemoteOK mocking, platform registry
- [ ] **Phase 13: Config Integration Tests** - YAML loading, validation, env overrides
- [ ] **Phase 14: CI Pipeline** - GitHub Actions workflow, coverage gates, linting
- [ ] **Phase 15: E2E Tests** - Playwright browser tests for critical dashboard flows

## Phase Details

### Phase 9: Test Infrastructure
**Goal**: Every test module can run in complete isolation without touching production data, real APIs, or leaking state between tests
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. Running `pytest` from repo root discovers the test directory and applies correct markers and asyncio mode
  2. Every test starts with a clean settings singleton -- no config leakage between tests
  3. Tests using the database fixture operate on an in-memory SQLite instance, never touching `job_pipeline/jobs.db`
  4. Any test that accidentally calls the Anthropic API or makes a real HTTP request fails immediately with a clear error
  5. Job factory fixture produces valid `Job` and `JobRecord` instances that pass Pydantic validation
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md — Dependencies, pytest/coverage config, test directory structure, test config YAML
- [x] 09-02-PLAN.md — Root conftest with isolation fixtures, factories, sub-directory conftest files, smoke tests

### Phase 10: Unit Tests
**Goal**: All pure logic modules (models, scoring, salary, dedup, anti-fabrication, delta detection) have passing tests that verify correctness without any I/O
**Depends on**: Phase 9
**Requirements**: UNIT-01, UNIT-02, UNIT-03, UNIT-04, UNIT-05, UNIT-06, UNIT-07, UNIT-08
**Success Criteria** (what must be TRUE):
  1. Invalid Pydantic model inputs (wrong types, missing fields, bad enums) are rejected with clear validation errors
  2. Salary normalization converts all supported formats (hourly, monthly, yearly, USD, CAD, ranges, bare numbers) to comparable annual USD values
  3. Job scoring produces deterministic 1-5 scores for known inputs and the breakdown explains each point awarded or withheld
  4. Deduplication detects same job across platforms when company names differ by case, suffix (Inc/LLC), or spacing
  5. Delta detection correctly distinguishes new jobs from previously-seen jobs based on normalized identifiers
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD
- [ ] 10-03: TBD

### Phase 11: Database Integration Tests
**Goal**: All database operations (CRUD lifecycle, FTS5 search, activity log, bulk updates, schema initialization) work correctly against an in-memory SQLite instance
**Depends on**: Phase 9
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05
**Success Criteria** (what must be TRUE):
  1. A job can be inserted, read back, updated through all 9 lifecycle statuses, and deleted -- and each state transition is persisted correctly
  2. FTS5 search returns relevant results for partial matches, handles special characters without crashing, and returns empty results (not errors) for no-match queries
  3. Activity log entries are automatically created on status transitions and include accurate timestamps
  4. Bulk status update applied to N jobs changes exactly those N jobs and no others
  5. Database initialization creates all required tables, indexes, and FTS5 virtual tables from a blank database
**Plans**: TBD

Plans:
- [ ] 11-01: TBD
- [ ] 11-02: TBD

### Phase 12: Web & API Integration Tests
**Goal**: All FastAPI endpoints return correct responses, and platform integration code (RemoteOK parsing, platform registry) works correctly with mocked external dependencies
**Depends on**: Phase 9, Phase 11
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-07, WEB-08, API-01, API-02, API-03, API-04
**Success Criteria** (what must be TRUE):
  1. Job list endpoint returns paginated results and correctly filters by score, platform, and status -- wrong filters return empty results, not errors
  2. Export endpoints produce valid CSV (parseable by csv module) and valid JSON (matching data schema) containing all expected job fields
  3. Status update and bulk action endpoints change job states, log activity, and return updated data to the client
  4. RemoteOK API response parser correctly extracts all fields from mocked JSON and gracefully handles malformed or empty responses
  5. Platform registry discovers all registered platform modules and each one satisfies the Platform protocol contract
**Plans**: TBD

Plans:
- [ ] 12-01: TBD
- [ ] 12-02: TBD
- [ ] 12-03: TBD

### Phase 13: Config Integration Tests
**Goal**: YAML configuration loading, validation, defaults, and environment variable overrides all work correctly
**Depends on**: Phase 9
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04
**Success Criteria** (what must be TRUE):
  1. A valid YAML config file loads successfully and all settings are accessible with correct types
  2. Invalid config values (bad URLs, wrong types, missing required fields) produce clear validation errors, not silent failures
  3. Optional fields that are omitted from YAML get their documented default values
  4. Environment variables override YAML values when both are present, following pydantic-settings precedence rules
**Plans**: TBD

Plans:
- [ ] 13-01: TBD

### Phase 14: CI Pipeline
**Goal**: All tests run automatically on every push and PR via GitHub Actions, with coverage enforcement and fast feedback
**Depends on**: Phase 10, Phase 11, Phase 12, Phase 13
**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05
**Success Criteria** (what must be TRUE):
  1. Pushing to main or opening a PR triggers a GitHub Actions workflow that runs the full test suite and reports pass/fail
  2. Coverage report is generated and the workflow fails if coverage drops below 80%
  3. Ruff linting runs alongside tests and blocks merge on lint errors
  4. Python dependencies and Playwright browsers are cached between CI runs, keeping total CI time reasonable
  5. E2E tests run as a separate optional job that does not block the main test/lint workflow
**Plans**: TBD

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

### Phase 15: E2E Tests
**Goal**: Critical dashboard user flows are verified end-to-end in a real browser, confirming that the full stack (FastAPI + SQLite + Jinja2 + htmx + JS) works together
**Depends on**: Phase 11, Phase 12
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05
**Success Criteria** (what must be TRUE):
  1. Dashboard loads in a Playwright browser and displays a list of jobs from the test database
  2. Filtering by score, platform, and status in the browser UI returns the correct subset of jobs
  3. Changing a job's status via the UI persists the change -- reloading the page shows the updated status
  4. Kanban board drag-and-drop moves a job card between columns and the new status persists in the database
  5. Export buttons trigger file downloads that contain valid CSV/JSON data matching the displayed jobs
**Plans**: TBD

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15
(Phase 11 and 13 can run in parallel after Phase 9; Phase 12 depends on 11)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Config Externalization | v1.0 | 3/3 | Complete | 2026-02-07 |
| 2. Platform Architecture | v1.0 | 2/2 | Complete | 2026-02-07 |
| 3. Discovery Engine | v1.0 | 3/3 | Complete | 2026-02-07 |
| 4. Scheduled Automation | v1.0 | 2/2 | Complete | 2026-02-07 |
| 5. Dashboard Core | v1.0 | 4/4 | Complete | 2026-02-07 |
| 6. Dashboard Analytics | v1.0 | 2/2 | Complete | 2026-02-07 |
| 7. AI Resume & Cover Letter | v1.0 | 4/4 | Complete | 2026-02-07 |
| 8. One-Click Apply | v1.0 | 4/4 | Complete | 2026-02-08 |
| 9. Test Infrastructure | v1.1 | 2/2 | Complete | 2026-02-08 |
| 10. Unit Tests | v1.1 | 0/3 | Not started | - |
| 11. Database Integration Tests | v1.1 | 0/2 | Not started | - |
| 12. Web & API Integration Tests | v1.1 | 0/3 | Not started | - |
| 13. Config Integration Tests | v1.1 | 0/1 | Not started | - |
| 14. CI Pipeline | v1.1 | 0/2 | Not started | - |
| 15. E2E Tests | v1.1 | 0/2 | Not started | - |
