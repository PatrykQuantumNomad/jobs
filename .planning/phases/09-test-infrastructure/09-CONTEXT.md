# Phase 9: Test Infrastructure - Context

**Gathered:** 2026-02-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Pytest configuration, shared fixtures, and isolation guards so every test module can run without touching production data, real APIs, or leaking state between tests. Browser/Playwright fixtures are out of scope (deferred to Phase 15: E2E Tests).

</domain>

<decisions>
## Implementation Decisions

### Test organization
- Mirror source tree: `tests/test_scorer.py` for `scorer.py`, `tests/platforms/test_indeed.py` for `platforms/indeed.py` — 1:1 mapping
- Test directory at repo root: `tests/`
- Pytest markers: `unit`, `integration`, `e2e`, `slow` — four tiers defined upfront
- Layered conftest files: root `tests/conftest.py` for global fixtures (settings, DB, HTTP guards), sub-directory conftest for domain-specific fixtures (e.g., `tests/platforms/conftest.py`)

### Fixture design
- Factory Boy with Faker for Job/JobRecord factories — realistic test data generation
- DB isolation level: Claude's discretion (fresh per test vs per module with rollback — pick based on actual DB layer implementation)
- Both empty and seeded DB fixtures available: empty DB as default, plus optional seed fixtures (`db_with_jobs`) for integration tests needing realistic data sets
- Async mode: pytest-asyncio strict mode — require explicit `@pytest.mark.asyncio` on each async test

### Isolation enforcement
- Both layers for HTTP: pytest-socket as autouse safety net (blocks all real network), plus respx for tests needing mock HTTP responses
- Anthropic API guard: dummy `ANTHROPIC_API_KEY` env var as safety net + monkeypatched client in autouse fixture — calls never leave the process
- Settings singleton: autouse fixture that resets/recreates the singleton before each test — zero chance of config leakage
- Playwright browser fixtures: deferred to Phase 15

### Developer experience
- Default `pytest` runs all non-e2e tests (unit + integration). E2E requires explicit `pytest -m e2e`.
- Default output: short/dots (standard pytest) — no verbose override in config
- Coverage: configure pytest-cov in this phase so `pytest --cov` works immediately
- Guard error messages: descriptive — e.g., "Test attempted real HTTP request to api.anthropic.com — use the mock_anthropic fixture instead"

### Claude's Discretion
- DB fixture isolation level (per-test vs per-module rollback)
- Exact Factory Boy model definitions and default field values
- Coverage source/omit configuration details
- pytest.ini vs pyproject.toml for pytest config (whichever fits the project better)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint from research: import-time side effects in `webapp/db.py` must be handled via `JOBFLOW_TEST_DB=1` before imports.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-test-infrastructure*
*Context gathered: 2026-02-08*
