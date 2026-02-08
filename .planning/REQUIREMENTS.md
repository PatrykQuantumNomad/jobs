# Requirements: JobFlow v1.1 — Test Web App

**Defined:** 2026-02-08
**Core Value:** From discovery to application in one tool — reliably find relevant jobs, present them clearly, make applying frictionless.

## v1.1 Requirements

Requirements for automated test suite and CI pipeline. Each maps to roadmap phases.

### Test Infrastructure

- [ ] **INFRA-01**: Test suite has root conftest.py with settings isolation (reset_settings after each test)
- [ ] **INFRA-02**: Test suite has in-memory SQLite fixture using JOBFLOW_TEST_DB=1
- [ ] **INFRA-03**: Test suite has job factory fixture producing valid Job/JobRecord instances
- [ ] **INFRA-04**: Test suite has test config YAML with safe defaults (no real credentials)
- [ ] **INFRA-05**: Test suite blocks real API calls (Anthropic, httpx) as safety net
- [ ] **INFRA-06**: pyproject.toml has pytest configuration (testpaths, markers, asyncio_mode)

### Unit Tests

- [ ] **UNIT-01**: Pydantic models validate correctly (Job, SearchQuery, CandidateProfile, enums)
- [ ] **UNIT-02**: Salary normalization handles all formats (hourly/monthly/yearly, USD/CAD, ranges, edge cases)
- [ ] **UNIT-03**: Job scoring produces correct 1-5 scores against candidate profile rubric
- [ ] **UNIT-04**: Score breakdown generates point-by-point explanations matching rubric
- [ ] **UNIT-05**: Cross-platform deduplication detects duplicates by normalized company+title
- [ ] **UNIT-06**: Fuzzy dedup handles company name variations (Inc/LLC, spacing, case)
- [ ] **UNIT-07**: Resume anti-fabrication validator catches hallucinated content
- [ ] **UNIT-08**: Delta detection correctly identifies new vs previously-seen jobs

### Integration Tests — Database

- [ ] **DB-01**: CRUD operations work for all job lifecycle states (insert, update status, delete)
- [ ] **DB-02**: FTS5 full-text search returns relevant results and handles special characters
- [ ] **DB-03**: Activity log records state transitions with timestamps
- [ ] **DB-04**: Bulk status updates apply correctly to multiple jobs
- [ ] **DB-05**: Database migration/initialization creates all required tables and indexes

### Integration Tests — Web

- [ ] **WEB-01**: Job list endpoint returns paginated results with correct filtering (score, platform, status)
- [ ] **WEB-02**: Job detail endpoint returns full description and metadata
- [ ] **WEB-03**: Status update endpoint changes job status and logs activity
- [ ] **WEB-04**: CSV export endpoint produces valid CSV with all job fields
- [ ] **WEB-05**: JSON export endpoint produces valid JSON matching data schema
- [ ] **WEB-06**: Bulk action endpoint handles multi-select status changes
- [ ] **WEB-07**: Job import endpoint loads pipeline JSON into database
- [ ] **WEB-08**: Search endpoint returns FTS5 results through the API layer

### Integration Tests — API/Platform

- [ ] **API-01**: RemoteOK API response parsing extracts all fields correctly (mocked with respx)
- [ ] **API-02**: RemoteOK handles malformed responses and empty results gracefully
- [ ] **API-03**: Platform registry discovers and registers all platform modules
- [ ] **API-04**: Platform protocol compliance verified for all registered platforms

### Integration Tests — Config

- [ ] **CFG-01**: YAML config loads and validates all settings with pydantic-settings
- [ ] **CFG-02**: Config validation rejects invalid values (bad URLs, missing required fields)
- [ ] **CFG-03**: Config defaults are applied when optional fields are omitted
- [ ] **CFG-04**: Environment variable overrides take precedence over YAML values

### CI Pipeline

- [ ] **CI-01**: GitHub Actions workflow runs all tests on push to main and on PR
- [ ] **CI-02**: Coverage report generated and enforces minimum threshold (80%)
- [ ] **CI-03**: CI runs linting (ruff) alongside tests
- [ ] **CI-04**: CI caches Python dependencies and Playwright browsers for speed
- [ ] **CI-05**: E2E tests run as a separate optional CI job (not blocking)

### E2E Tests

- [ ] **E2E-01**: Dashboard loads and displays job list in browser (Playwright)
- [ ] **E2E-02**: Filtering by score/platform/status works end-to-end in browser
- [ ] **E2E-03**: Job status change via UI updates correctly and persists
- [ ] **E2E-04**: Kanban board drag-and-drop updates job status
- [ ] **E2E-05**: Export buttons produce downloadable CSV/JSON files

## Future Requirements

### Performance Testing

- **PERF-01**: Load testing for dashboard with 10K+ jobs in database
- **PERF-02**: Benchmark test suite execution time, alert on regression

### Extended Coverage

- **EXT-01**: AI resume tailoring output quality tests (snapshot-based)
- **EXT-02**: Form filler tests against mock ATS iframes
- **EXT-03**: SSE streaming endpoint tests with async client

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live platform scraping tests | Requires real credentials, fragile selectors, rate limiting — accept lower coverage |
| Playwright mock objects for scraper code | Anti-pattern per research — extract pure parsing functions instead |
| Visual regression testing | Adds screenshot comparison complexity, dashboard is htmx/server-rendered |
| Mutation testing | Valuable but premature — add after baseline coverage established |
| Pre-commit hooks | Separate concern from test suite — can be added as quick task |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 9 | Pending |
| INFRA-02 | Phase 9 | Pending |
| INFRA-03 | Phase 9 | Pending |
| INFRA-04 | Phase 9 | Pending |
| INFRA-05 | Phase 9 | Pending |
| INFRA-06 | Phase 9 | Pending |
| UNIT-01 | Phase 10 | Pending |
| UNIT-02 | Phase 10 | Pending |
| UNIT-03 | Phase 10 | Pending |
| UNIT-04 | Phase 10 | Pending |
| UNIT-05 | Phase 10 | Pending |
| UNIT-06 | Phase 10 | Pending |
| UNIT-07 | Phase 10 | Pending |
| UNIT-08 | Phase 10 | Pending |
| DB-01 | Phase 11 | Pending |
| DB-02 | Phase 11 | Pending |
| DB-03 | Phase 11 | Pending |
| DB-04 | Phase 11 | Pending |
| DB-05 | Phase 11 | Pending |
| WEB-01 | Phase 12 | Pending |
| WEB-02 | Phase 12 | Pending |
| WEB-03 | Phase 12 | Pending |
| WEB-04 | Phase 12 | Pending |
| WEB-05 | Phase 12 | Pending |
| WEB-06 | Phase 12 | Pending |
| WEB-07 | Phase 12 | Pending |
| WEB-08 | Phase 12 | Pending |
| API-01 | Phase 12 | Pending |
| API-02 | Phase 12 | Pending |
| API-03 | Phase 12 | Pending |
| API-04 | Phase 12 | Pending |
| CFG-01 | Phase 13 | Pending |
| CFG-02 | Phase 13 | Pending |
| CFG-03 | Phase 13 | Pending |
| CFG-04 | Phase 13 | Pending |
| CI-01 | Phase 14 | Pending |
| CI-02 | Phase 14 | Pending |
| CI-03 | Phase 14 | Pending |
| CI-04 | Phase 14 | Pending |
| CI-05 | Phase 14 | Pending |
| E2E-01 | Phase 15 | Pending |
| E2E-02 | Phase 15 | Pending |
| E2E-03 | Phase 15 | Pending |
| E2E-04 | Phase 15 | Pending |
| E2E-05 | Phase 15 | Pending |

**Coverage:**
- v1.1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-02-08*
*Last updated: 2026-02-08 after roadmap creation (all 45 requirements mapped to phases 9-15)*
