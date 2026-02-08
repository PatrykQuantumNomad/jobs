# Research Summary: JobFlow v1.1 -- Automated Test Suite + CI Pipeline

**Domain:** Automated testing architecture for FastAPI + Playwright + SQLite + Pydantic job search app
**Researched:** 2026-02-08
**Overall confidence:** HIGH

## Executive Summary

The JobFlow codebase (8,200+ lines across 20+ modules) shipped as a v1.0 MVP without any automated tests. This milestone adds a comprehensive test suite and CI pipeline. The research focuses on how tests integrate with the existing architecture -- identifying testability hooks already in the code, defining mock boundaries, and specifying the build order for test layers.

The codebase has excellent testability characteristics despite having no tests. The `config.py` module provides `reset_settings()` for singleton isolation. The `webapp/db.py` module supports `JOBFLOW_TEST_DB=1` for in-memory SQLite. The Protocol-based platform architecture and Pydantic models with sensible defaults make factory fixtures trivial. Most pure logic (scoring, salary parsing, deduplication, anti-fabrication validation) has zero I/O dependencies and can be unit-tested directly.

The primary challenge is managing import-time side effects: `webapp/db.py` runs `init_db()` at import time (creating the production database), and `platforms/__init__.py` auto-discovers all platform modules (importing Playwright). Both must be handled before any test code runs. The secondary challenge is mocking lazy imports in FastAPI endpoint handlers, which defeats standard `@patch` patterns because imports happen inside function bodies.

The recommended approach follows the test pyramid: ~80 unit tests for pure logic, ~40 integration tests for DB/HTTP/config, and ~10 optional E2E tests for Playwright browser automation. No production code modifications are needed -- all existing testability hooks suffice.

## Key Findings

**Stack:** pytest + pytest-cov + respx (httpx mocking) + pytest-playwright. Four new dev dependencies, all mature and well-documented.

**Architecture:** Three-layer test pyramid (unit/integration/e2e) with separate conftest.py per layer. Root conftest provides settings isolation and job factory. Integration conftest provides in-memory SQLite and TestClient.

**Critical pitfall:** Import-time side effects in `webapp/db.py` (creates production database on import) and `platforms/__init__.py` (imports Playwright on import). Must set `JOBFLOW_TEST_DB=1` and control import ordering before any test code runs.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Test Infrastructure** - Root conftest.py, test fixtures, pyproject.toml configuration
   - Addresses: Settings isolation, DB isolation, job factory, test YAML config
   - Avoids: Import-time side effects (PITFALLS #1, #2, #3)
   - Must be built first -- every test depends on it

2. **Unit Tests** - Pure logic modules with zero I/O
   - Addresses: models.py, scorer.py, salary.py, dedup.py, resume_ai/validator.py
   - Avoids: Config singleton leakage (PITFALLS #7)
   - ~80 tests, runs in <5s, highest value-to-effort ratio

3. **Integration Tests - Database** - SQLite CRUD, migrations, FTS5
   - Addresses: webapp/db.py CRUD, migration chain, FTS5 search, activity log
   - Avoids: FTS5 corruption between tests (PITFALLS #5)
   - Requires: In-memory DB fixture from Phase 1

4. **Integration Tests - Web + API** - FastAPI endpoints, RemoteOK mocking
   - Addresses: webapp/app.py routes, export, import; RemoteOK with respx
   - Avoids: TestClient event loop conflicts (PITFALLS #4, #8)
   - Requires: TestClient + DB fixture from Phase 3

5. **Integration Tests - Config + Registry** - Settings loading, platform registration
   - Addresses: config.py YAML loading, platform registry validation
   - Avoids: Missing config files in CI (PITFALLS #10)

6. **CI Pipeline** - GitHub Actions workflow, coverage gates
   - Addresses: Automated test runs on push/PR, coverage reporting
   - Avoids: Playwright browser download slowing unit test CI

7. **E2E Tests (Optional)** - Real Playwright browser tests
   - Addresses: Platform search flows against real sites
   - Avoids: Mocking Playwright (anti-pattern per PITFALLS #9)
   - Should be CI-optional, triggered manually

**Phase ordering rationale:**
- Phase 1 must be first -- every test depends on fixtures and isolation
- Phase 2 before Phase 3 because unit tests validate the data models that DB tests depend on
- Phase 3 before Phase 4 because webapp tests need the DB fixture to be proven correct
- Phase 5 can be parallel with Phase 4 (independent concerns)
- Phase 6 after 1-5 because CI runs the tests that must exist first
- Phase 7 last because it is the most expensive and fragile layer

**Research flags for phases:**
- Phase 1: No additional research needed -- patterns are standard and code hooks already exist
- Phase 4: May need deeper investigation of SSE testing patterns (TestClient vs httpx.AsyncClient)
- Phase 7: Needs investigation of CI browser caching strategies for Playwright in GitHub Actions

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI with active maintenance. pytest/respx/pytest-playwright are industry standard. |
| Features | HIGH | Feature list derived from direct codebase analysis of all 20+ modules. Clear distinction between unit/integration/e2e boundaries. |
| Architecture | HIGH | Test directory structure, fixture hierarchy, and mock boundaries all grounded in codebase analysis. Existing testability hooks (`reset_settings`, `JOBFLOW_TEST_DB`) verified in source code. |
| Pitfalls | HIGH | All pitfalls verified by direct reading of the relevant source code lines. Import-time side effects, singleton leakage, and lazy import patterns confirmed in codebase. |

## Gaps to Address

- **SSE endpoint testing strategy:** The `TestClient` + `EventSourceResponse` interaction model needs careful design. The approach (test components separately, use httpx.AsyncClient for SSE) is sound but needs validation during implementation.
- **Python 3.14 compatibility in CI:** The project targets Python 3.14 (`requires-python = ">=3.14"`). GitHub Actions `actions/setup-python@v5` support for 3.14 should be verified during CI setup.
- **Coverage baseline:** No tests exist yet, so the 70% coverage gate should be applied after Phase 2 (unit tests) to avoid blocking on incomplete integration tests.
- **Playwright browser caching in CI:** Downloading Chromium (~130MB) on every CI run is wasteful. Investigate `actions/cache` for Playwright browsers during Phase 6.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `config.py`, `webapp/db.py`, `webapp/app.py`, `models.py`, `scorer.py`, `salary.py`, `dedup.py`, `platforms/protocols.py`, `platforms/registry.py`, `platforms/__init__.py`, `platforms/stealth.py`, `platforms/remoteok.py`, `resume_ai/validator.py`, `resume_ai/models.py`, `apply_engine/engine.py`, `apply_engine/events.py`, `form_filler.py`, `orchestrator.py`, `scheduler.py`
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/) -- TestClient patterns
- [pytest Fixture Documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html) -- conftest hierarchy, factory pattern
- [RESPX User Guide](https://lundberg.github.io/respx/guide/) -- httpx mocking
- [Playwright Python Test Runners](https://playwright.dev/python/docs/test-runners) -- pytest-playwright fixtures

### Secondary (MEDIUM confidence)
- [Pytest Organization Best Practices](https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/) -- directory structure
- [Patching Pydantic Settings in Pytest](https://rednafi.com/python/patch_pydantic_settings_in_pytest/) -- singleton management
- [BrowserStack Playwright Unit Testing 2026](https://www.browserstack.com/guide/playwright-unit-testing) -- mocking network in Playwright tests

---

*Research completed: 2026-02-08*
*Ready for roadmap: yes*
