# Architecture Patterns

**Domain:** Automated test suite for FastAPI + Playwright job search application
**Researched:** 2026-02-08
**Confidence:** HIGH (based on codebase analysis, FastAPI/pytest docs, community patterns)

## Recommended Architecture

### Test Pyramid for This Codebase

```
         /  E2E  \           Playwright browser tests (platforms/)
        / --------\          ~10 tests, slow, CI-optional
       / Integration\        FastAPI TestClient + SQLite (webapp/, orchestrator)
      / ------------ \       ~40 tests, moderate speed
     /    Unit Tests    \    Pure logic: models, scorer, dedup, salary, validator
    / __________________ \   ~80 tests, fast (<1s each)
```

The codebase has three natural test boundaries:

1. **Pure logic** (no I/O): models.py, scorer.py, salary.py, dedup.py, resume_ai/validator.py, resume_ai/models.py
2. **HTTP/DB integration** (mockable I/O): webapp/app.py, webapp/db.py, platforms/remoteok.py, config.py
3. **Browser automation** (Playwright): platforms/indeed.py, platforms/dice.py, apply_engine/engine.py, form_filler.py

### Directory Structure

```
tests/
    conftest.py                    # Root: shared fixtures (settings, job factory, db)
    pytest.ini                     # NOT needed -- config in pyproject.toml
    fixtures/
        config.test.yaml           # Minimal valid YAML for test settings
        sample_jobs.json           # Canonical test job data
        sample_remoteok_response.json  # Recorded API response
    unit/
        conftest.py                # Unit-specific: no I/O fixtures
        test_models.py             # Job, SearchQuery, CandidateProfile validation
        test_scorer.py             # JobScorer scoring logic
        test_salary.py             # parse_salary, parse_salary_ints
        test_dedup.py              # fuzzy_deduplicate, _normalize_company
        test_validator.py          # validate_no_fabrication entity extraction
        test_resume_models.py      # TailoredResume, CoverLetter model validation
        test_apply_events.py       # ApplyEvent, ApplyEventType serialization
        test_apply_config.py       # ApplyConfig, ApplyMode defaults
    integration/
        conftest.py                # Integration-specific: TestClient, in-memory DB
        test_db.py                 # SQLite CRUD, migrations, FTS5 search
        test_webapp_dashboard.py   # GET /, /search, /kanban, /analytics
        test_webapp_jobs.py        # GET/POST /jobs/{key}, status, notes
        test_webapp_export.py      # CSV/JSON export endpoints
        test_webapp_import.py      # POST /import pipeline
        test_remoteok_api.py       # RemoteOK with mocked httpx (respx)
        test_config.py             # AppSettings loading, reset, YAML parsing
        test_registry.py           # Platform registry, decorator validation
        test_scheduler.py          # Plist generation (no launchctl calls)
    e2e/
        conftest.py                # E2E-specific: real Playwright browser
        test_indeed_search.py      # Indeed search flow (needs network)
        test_dice_search.py        # Dice search flow (needs network)
```

### Component Boundaries

| Component | Responsibility | Test Layer | Mock Boundary |
|-----------|---------------|------------|---------------|
| `models.py` | Pydantic data validation | Unit | None (pure logic) |
| `scorer.py` | Job scoring against profile | Unit | Mock `get_settings()` |
| `salary.py` | Salary string parsing | Unit | None (pure logic) |
| `dedup.py` | Fuzzy deduplication | Unit | None (pure logic) |
| `resume_ai/validator.py` | Anti-fabrication checks | Unit | None (pure regex) |
| `resume_ai/models.py` | LLM output schemas | Unit | None (pure Pydantic) |
| `webapp/db.py` | SQLite CRUD + FTS5 | Integration | In-memory SQLite |
| `webapp/app.py` | FastAPI HTTP routes | Integration | TestClient + in-memory DB |
| `platforms/remoteok.py` | RemoteOK HTTP API | Integration | respx (mock httpx) |
| `config.py` | Settings loading | Integration | Test YAML + env override |
| `platforms/registry.py` | Platform registration | Integration | None (test real decorator) |
| `platforms/indeed.py` | Browser automation | E2E | Real Playwright (optional) |
| `platforms/dice.py` | Browser automation | E2E | Real Playwright (optional) |
| `apply_engine/engine.py` | Apply orchestration | E2E | Real Playwright (optional) |
| `form_filler.py` | ATS form detection | E2E | Real Playwright (optional) |
| `orchestrator.py` | Full pipeline | Integration | Mock platforms + DB |

### Data Flow for Test Fixtures

```
conftest.py (root)
    |
    |-- job_factory()          -> creates Job instances with configurable fields
    |-- sample_jobs()          -> list of 5-10 representative Job objects
    |-- test_settings()        -> AppSettings from fixtures/config.test.yaml
    |-- candidate_profile()    -> CandidateProfile with known test values
    |
    +-- integration/conftest.py
        |
        |-- test_db()          -> in-memory SQLite, init_db(), yields, resets
        |-- test_client()      -> TestClient(app) with DB override
        |-- respx_mock()       -> from respx pytest fixture
        |
        +-- e2e/conftest.py
            |
            |-- browser()      -> Playwright browser (session-scoped)
            |-- page()         -> Fresh page per test (function-scoped)
```

## Patterns to Follow

### Pattern 1: Settings Override for Tests

**What:** Replace the singleton `get_settings()` with a test-specific `AppSettings` loaded from `tests/fixtures/config.test.yaml` and controlled environment variables.

**Why:** The production `config.py` uses a global `_settings` singleton and reads from `.env` and `config.yaml` in the project root. Tests must not depend on production config files.

**How:** The codebase already has `reset_settings()` in config.py. Use it.

```python
# tests/conftest.py
import os
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(autouse=True)
def isolate_settings():
    """Reset the settings singleton before each test."""
    from config import reset_settings
    reset_settings()
    yield
    reset_settings()

@pytest.fixture
def test_settings(monkeypatch, tmp_path):
    """Load AppSettings from test fixtures, not production config."""
    from config import AppSettings, reset_settings

    # Point to test YAML
    test_yaml = FIXTURES_DIR / "config.test.yaml"
    monkeypatch.setenv("DICE_EMAIL", "test@example.com")
    monkeypatch.setenv("DICE_PASSWORD", "testpass")
    monkeypatch.setenv("INDEED_EMAIL", "test@example.com")

    reset_settings()
    AppSettings.model_config["yaml_file"] = str(test_yaml)
    settings = AppSettings()
    return settings
```

### Pattern 2: In-Memory SQLite with FTS5 for DB Tests

**What:** Use the existing `JOBFLOW_TEST_DB=1` environment variable that `webapp/db.py` already supports to switch to an in-memory SQLite database.

**Why:** The codebase already has this mechanism built in (lines 10-11 of db.py). Tests should activate it and reinitialize the schema for each test.

**How:**

```python
# tests/integration/conftest.py
import os
import pytest

@pytest.fixture(autouse=True)
def test_db(monkeypatch):
    """Use in-memory SQLite for all integration tests."""
    monkeypatch.setenv("JOBFLOW_TEST_DB", "1")

    # Force reimport to pick up the env var
    from webapp import db
    db._USE_MEMORY = True
    db._memory_conn = None  # Reset any existing connection
    db.init_db()

    yield db

    # Cleanup
    if db._memory_conn:
        db._memory_conn.close()
        db._memory_conn = None
```

**FTS5 consideration:** SQLite's FTS5 extension works in `:memory:` databases. The `init_db()` call runs `CREATE TABLE` + `migrate_db()` which creates the FTS5 virtual table and triggers. No special handling needed.

### Pattern 3: Job Factory Fixture

**What:** A factory function that creates `Job` instances with sensible defaults but allows overriding any field.

**Why:** Many tests need Job objects. A factory avoids repetitive construction and makes tests readable.

```python
# tests/conftest.py
from models import Job, JobStatus

@pytest.fixture
def job_factory():
    """Factory for creating Job instances with defaults."""
    _counter = 0

    def _make(**overrides) -> Job:
        nonlocal _counter
        _counter += 1
        defaults = {
            "id": f"test-{_counter}",
            "platform": "indeed",
            "title": "Senior Software Engineer",
            "company": "Test Corp",
            "location": "Remote",
            "url": f"https://example.com/job/{_counter}",
            "description": "Python, Kubernetes, FastAPI, Docker",
            "salary": "$200,000 - $250,000",
            "salary_min": 200_000,
            "salary_max": 250_000,
            "status": JobStatus.DISCOVERED,
        }
        defaults.update(overrides)
        return Job(**defaults)

    return _make
```

### Pattern 4: FastAPI TestClient with DB Override

**What:** Use `TestClient` from `fastapi.testclient` (backed by httpx) with the in-memory database.

**Why:** FastAPI's TestClient makes synchronous HTTP calls to the app without starting a server. Combined with the in-memory SQLite, tests are fast and isolated.

```python
# tests/integration/conftest.py
from fastapi.testclient import TestClient

@pytest.fixture
def test_client(test_db):
    """FastAPI TestClient with in-memory database."""
    from webapp.app import app
    with TestClient(app) as client:
        yield client
```

**Critical note:** The `webapp/app.py` module imports `webapp.db` at module level, which calls `init_db()` on import. The `test_db` fixture must be set up BEFORE importing the app, or the `monkeypatch` for `JOBFLOW_TEST_DB` must be applied before the webapp module is imported. In practice, because pytest imports test modules after fixtures are set up, the `autouse=True` on `test_db` handles this ordering.

### Pattern 5: Mocking httpx with respx for RemoteOK Tests

**What:** Use `respx` to mock `httpx.Client.get()` calls in `RemoteOKPlatform.search()`.

**Why:** RemoteOK uses `httpx.Client` (sync), not `aiohttp`. `respx` is the standard mocking library for httpx and provides a pytest fixture out of the box.

```python
# tests/integration/test_remoteok_api.py
import respx
from httpx import Response

@respx.mock
def test_remoteok_search_filters_by_tags(test_settings, job_factory):
    """RemoteOK search filters API results by tech keyword overlap."""
    mock_response = [
        {"legal": "metadata"},  # Index 0 = metadata
        {
            "id": 1, "position": "Staff Platform Engineer",
            "company": "CloudCo", "url": "/remote-jobs/1",
            "tags": ["python", "kubernetes"], "description": "...",
            "salary_min": 200000, "salary_max": 250000,
            "location": "Remote", "epoch": 1707350400,
        },
    ]
    respx.get("https://remoteok.com/api").mock(
        return_value=Response(200, json=mock_response)
    )

    from platforms.remoteok import RemoteOKPlatform
    from models import SearchQuery

    platform = RemoteOKPlatform()
    platform.init()
    with platform:
        jobs = platform.search(SearchQuery(query="kubernetes", platform="remoteok"))
    assert len(jobs) >= 1
    assert jobs[0].platform == "remoteok"
```

### Pattern 6: Pytest Markers for Test Layers

**What:** Use custom markers to categorize tests so they can be run selectively.

```python
# pyproject.toml additions
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Pure logic tests, no I/O (fast)",
    "integration: Tests with DB, HTTP, or config I/O (moderate)",
    "e2e: Browser tests requiring Playwright (slow)",
    "slow: Tests taking >5 seconds",
]
```

**Usage:**
```bash
pytest -m unit                # Fast: ~80 tests in <5s
pytest -m integration         # Moderate: ~40 tests in <30s
pytest -m "not e2e"           # Everything except browser tests
pytest -m e2e --headed        # E2E with visible browser
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Testing Against Production Config/DB

**What:** Tests that import `config.py` and use the production `config.yaml` and `.env`, or that write to `job_pipeline/jobs.db`.

**Why bad:** Tests become environment-dependent, flaky, and can corrupt production data. CI environments will not have `.env` or `config.yaml`.

**Instead:** Always use `reset_settings()` + test YAML fixture. Always use `JOBFLOW_TEST_DB=1` for in-memory SQLite.

### Anti-Pattern 2: Mocking Playwright for Unit Tests

**What:** Creating mock `Page`, `BrowserContext`, `ElementHandle` objects to test platform code without a real browser.

**Why bad:** Playwright's API surface is enormous. Mock objects will drift from the real API. Tests will pass on mocks but fail on real browsers. The value of testing `indeed.py` is that selectors work against real DOM.

**Instead:** Separate testable logic (scoring, parsing, filtering) from browser interactions. Test pure logic with unit tests. Test browser code only in E2E tests with real Playwright, or skip them in CI.

### Anti-Pattern 3: Importing `webapp.db` Before Setting Test Environment

**What:** Importing db.py triggers `init_db()` at module level (line 723: `init_db()`), which creates the production database file before test fixtures can set `JOBFLOW_TEST_DB=1`.

**Why bad:** Tests create `job_pipeline/jobs.db` on disk, intermingle with production data.

**Instead:** Ensure test fixtures using `monkeypatch.setenv("JOBFLOW_TEST_DB", "1")` run before any import of `webapp.db`. Use the `autouse=True` pattern on the db fixture so it is always initialized first.

### Anti-Pattern 4: Testing LLM Output Directly

**What:** Calling `tailor_resume()` or `generate_cover_letter()` in tests, which requires an Anthropic API key and makes real LLM calls.

**Why bad:** Slow ($$$), non-deterministic, requires API keys in CI, output changes between model versions.

**Instead:** Test the models (`TailoredResume`, `CoverLetter` Pydantic validation), the validator (`validate_no_fabrication`), the diff generator, and the PDF renderer with hardcoded structured output. Mock the LLM call itself.

### Anti-Pattern 5: Singleton State Leaking Between Tests

**What:** Not resetting `config._settings`, `webapp.db._memory_conn`, or `platforms.registry._REGISTRY` between tests.

**Why bad:** Test order dependencies. A test that modifies global state affects subsequent tests.

**Instead:** `autouse=True` fixtures that reset all singletons. The `isolate_settings` fixture handles `config._settings`. The `test_db` fixture handles `db._memory_conn`. The registry does not need resetting (it's populated at import time and should remain stable).

## Integration Points: Existing Code vs Test Code

### What Existing Code Already Provides for Testability

| Mechanism | Location | How Tests Use It |
|-----------|----------|------------------|
| `reset_settings()` | `config.py:314-317` | Reset singleton between tests |
| `JOBFLOW_TEST_DB` env var | `webapp/db.py:10-11` | Switch to in-memory SQLite |
| `_memory_conn` singleton | `webapp/db.py:152-153` | Controllable from fixtures |
| Protocol-based platforms | `platforms/protocols.py` | Can create test implementations |
| `@register_platform` decorator | `platforms/registry.py` | Validate registration logic |
| `init_db()` | `webapp/db.py:203-206` | Initialize fresh schema per test |
| Pydantic models with defaults | `models.py` | Easy factory construction |
| Settings from `__init__` kwargs | `config.py:147` | Bypass YAML/env entirely |

### New Files Required (Test Infrastructure Only)

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Root fixtures: settings reset, job factory, candidate profile |
| `tests/fixtures/config.test.yaml` | Minimal valid YAML for test settings |
| `tests/fixtures/sample_jobs.json` | Canonical job data for integration tests |
| `tests/fixtures/sample_remoteok_response.json` | Recorded RemoteOK API response |
| `tests/unit/conftest.py` | Unit marker auto-application |
| `tests/integration/conftest.py` | DB fixture, TestClient, respx |
| `tests/e2e/conftest.py` | Playwright browser/page fixtures |

### No Modifications Required to Production Code

The existing codebase has sufficient testability hooks:
- `reset_settings()` already exists for test isolation
- `JOBFLOW_TEST_DB` environment variable already switches to in-memory mode
- Settings can be constructed with `__init__` kwargs (bypassing YAML)
- Protocol-based architecture enables test implementations without mocking

## Build Order for Test Layers

The test layers have dependencies that dictate build order:

```
Phase 1: Root conftest.py + fixtures/
    |     (job factory, settings isolation, test YAML)
    |     No tests yet -- just infrastructure.
    v
Phase 2: Unit tests
    |     test_models.py, test_scorer.py, test_salary.py,
    |     test_dedup.py, test_validator.py
    |     These have ZERO dependencies on DB or HTTP.
    v
Phase 3: Integration tests - Database layer
    |     test_db.py (CRUD, migrations, FTS5, activity log)
    |     Requires: in-memory DB fixture from Phase 1
    v
Phase 4: Integration tests - Web endpoints
    |     test_webapp_*.py (dashboard, jobs, export, import)
    |     Requires: TestClient + DB fixture from Phase 3
    v
Phase 5: Integration tests - External APIs + Config
    |     test_remoteok_api.py (respx mocking)
    |     test_config.py (YAML loading, validation)
    |     test_registry.py (platform decorator)
    v
Phase 6: E2E tests (optional for CI)
    |     test_indeed_search.py, test_dice_search.py
    |     Requires: Playwright + network access
    v
Phase 7: CI pipeline integration
          GitHub Actions workflow, coverage reporting
```

**Rationale:** Each phase builds on the previous. Unit tests validate the foundation (models, logic). DB tests validate the data layer. Webapp tests validate the HTTP layer on top of the DB layer. E2E tests are last because they are the most expensive and fragile.

## Scalability Considerations

| Concern | Current (~130 tests) | At 500 tests | At 1000+ tests |
|---------|---------------------|-------------|----------------|
| Speed | All run in <60s | Split unit/integration in CI | Parallel with pytest-xdist |
| Isolation | In-memory SQLite per test | Same approach scales | Consider test-level transactions |
| CI cost | Single runner | Single runner + E2E matrix | Separate unit/integration/e2e jobs |
| Fixtures | Simple factories | Factory-boy for complex objects | Same + fixture composition |
| Coverage | Line coverage | Branch coverage | Mutation testing (mutmut) |

## Sources

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/) -- TestClient patterns, dependency overrides
- [pytest Fixture Documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html) -- Scope, conftest hierarchy, factory pattern
- [Playwright Python Test Runners](https://playwright.dev/python/docs/test-runners) -- pytest-playwright fixtures
- [RESPX User Guide](https://lundberg.github.io/respx/guide/) -- httpx mocking for RemoteOK tests
- [pytest-playwright PyPI](https://pypi.org/project/pytest-playwright/) -- Browser fixtures
- [Pytest Organization Best Practices](https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/) -- Directory structure patterns
- Codebase analysis: `config.py:reset_settings()`, `webapp/db.py:JOBFLOW_TEST_DB`, `platforms/protocols.py`
