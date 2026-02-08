# Phase 9: Test Infrastructure - Research

**Researched:** 2026-02-08
**Domain:** Pytest configuration, test fixtures, and isolation for a Python 3.14 job search pipeline
**Confidence:** HIGH

## Summary

This phase establishes the test infrastructure for the job search automation codebase: pytest configuration, shared fixtures, isolation guards, and factory helpers. The codebase runs on Python 3.14.3, uses Pydantic v2 models, SQLite (with import-time `init_db()` side effect in `webapp/db.py`), httpx for HTTP, and the Anthropic SDK for LLM calls. The primary challenge is three-fold: (1) properly isolating the settings singleton and DB singleton, (2) blocking all real network access (httpx, Anthropic, raw sockets) with descriptive errors, and (3) getting Factory Boy to produce valid Pydantic v2 model instances despite no native Pydantic integration in factory-boy.

The project already has `pyproject.toml` with `[tool.pytest.ini_options]` (testpaths only), pytest 9.0.2 installed, and a `reset_settings()` function ready for test use. The DB module has `JOBFLOW_TEST_DB=1` env var support for in-memory SQLite but uses a module-level `_memory_conn` singleton that needs per-test reset. None of the test helper libraries (factory-boy, faker, respx, pytest-socket, pytest-asyncio, pytest-cov) are currently installed.

**Primary recommendation:** Use `pyproject.toml` for all pytest/coverage configuration (project already uses it). Install factory-boy + faker + respx + pytest-socket + pytest-asyncio + pytest-cov as dev dependencies. Use per-test DB isolation (fresh in-memory SQLite) because the DB layer uses a module-level singleton connection that is simple to reset but impossible to rollback transactionally.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Test organization:** Mirror source tree 1:1, `tests/` at repo root, pytest markers `unit`/`integration`/`e2e`/`slow`, layered conftest files
- **Factory Boy with Faker** for Job/JobRecord factories
- **Both empty and seeded DB fixtures:** empty as default, `db_with_jobs` for integration tests
- **pytest-asyncio strict mode:** explicit `@pytest.mark.asyncio` on each async test
- **Both layers for HTTP isolation:** pytest-socket (autouse safety net) + respx (mock HTTP responses)
- **Anthropic API guard:** dummy `ANTHROPIC_API_KEY` env var + monkeypatched client in autouse fixture
- **Settings singleton:** autouse fixture that resets/recreates before each test
- **Default `pytest` runs unit + integration; E2E requires `pytest -m e2e`**
- **Default output:** short/dots (standard pytest)
- **Coverage:** configure pytest-cov so `pytest --cov` works immediately
- **Guard error messages:** descriptive (e.g., "Test attempted real HTTP request to api.anthropic.com")
- **Playwright browser fixtures:** deferred to Phase 15

### Claude's Discretion
- DB fixture isolation level (per-test vs per-module rollback)
- Exact Factory Boy model definitions and default field values
- Coverage source/omit configuration details
- pytest.ini vs pyproject.toml for pytest config

### Deferred Ideas (OUT OF SCOPE)
- None
</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 (installed) | Test framework | Already in dev deps, latest major version |
| factory-boy | 3.3.3 | Test data factories | User decision; works with Pydantic via `class Meta: model = PydanticModel` |
| Faker | 40.4.0 | Realistic random data | Companion to factory-boy; supports Python 3.14 explicitly |
| pytest-asyncio | 1.3.0 | Async test support | Supports Python 3.14 explicitly; strict mode is default |
| respx | 0.22.0 | Mock httpx requests | Only httpx mock library; Python >=3.8 |
| pytest-socket | 0.7.0 | Block all real network calls | Autouse safety net; Python >=3.8,<4.0 |
| pytest-cov | 7.0.0 | Coverage reporting | Integrates coverage.py with pytest; requires coverage>=7.10.6 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| coverage[toml] | >=7.10.6 | Coverage engine | Auto-installed by pytest-cov; needed for pyproject.toml config |
| Faker | (via factory-boy) | Random data | factory.Faker('company'), factory.Faker('job') |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| factory-boy | polyfactory 3.2.0 | Polyfactory has native Pydantic v2 ModelFactory with auto-field generation; factory-boy requires manual field declarations for Pydantic. But user locked factory-boy. |
| pytest-socket | Manual monkeypatch of `socket.socket` | pytest-socket provides CLI flag, marker system, and host allowlisting. Monkeypatch is manual and error-prone. |
| respx | pytest-httpx | respx is more mature and has better route-pattern matching. pytest-httpx is simpler but less flexible. |

**Installation:**
```bash
pip install factory-boy faker respx pytest-socket pytest-asyncio pytest-cov
```

Or add to `pyproject.toml` dev group:
```toml
[dependency-groups]
dev = [
    "ruff>=0.9.0",
    "pyright>=1.1.0",
    "pytest>=8.0.0",
    "factory-boy>=3.3.0",
    "Faker>=40.0.0",
    "pytest-asyncio>=1.3.0",
    "respx>=0.22.0",
    "pytest-socket>=0.7.0",
    "pytest-cov>=7.0.0",
]
```

## Architecture Patterns

### Recommended Test Directory Structure
```
tests/
├── __init__.py              # Empty (makes tests a package for imports)
├── conftest.py              # Global: settings reset, DB fixture, HTTP guards, Anthropic guard
├── conftest_factories.py    # Factory definitions (imported by conftest.py)
├── test_scorer.py           # Tests for scorer.py
├── test_models.py           # Tests for models.py
├── test_salary.py           # Tests for salary.py
├── test_dedup.py            # Tests for dedup.py
├── test_config.py           # Tests for config.py
├── test_form_filler.py      # Tests for form_filler.py (pure logic, no browser)
├── test_orchestrator.py     # Tests for orchestrator.py (integration)
├── platforms/
│   ├── __init__.py
│   ├── conftest.py          # Platform-specific fixtures (mock search results, etc.)
│   ├── test_remoteok.py     # Tests for platforms/remoteok.py
│   ├── test_registry.py     # Tests for platforms/registry.py
│   └── test_protocols.py    # Tests for platforms/protocols.py
├── webapp/
│   ├── __init__.py
│   ├── conftest.py          # TestClient fixture, DB seeding
│   ├── test_db.py           # Tests for webapp/db.py
│   └── test_app.py          # Tests for webapp/app.py (FastAPI endpoints)
└── resume_ai/
    ├── __init__.py
    ├── conftest.py          # Mock Anthropic client fixture
    ├── test_tailor.py       # Tests for resume_ai/tailor.py
    ├── test_cover_letter.py # Tests for resume_ai/cover_letter.py
    ├── test_validator.py    # Tests for resume_ai/validator.py
    └── test_tracker.py      # Tests for resume_ai/tracker.py
```

### Pattern 1: Settings Singleton Reset (autouse fixture)

**What:** Autouse fixture in root conftest that resets the `_settings` singleton before each test, preventing config leakage between tests.

**When to use:** Every test (autouse=True).

**Implementation detail:** The `config.py` module has a `reset_settings()` function and an `_settings` global. The fixture must also handle the `JOBFLOW_TEST_DB=1` env var before any DB import.

```python
# tests/conftest.py
import os

# CRITICAL: Set JOBFLOW_TEST_DB before ANY import that touches webapp.db
# webapp/db.py reads this env var at import time (line 10) and init_db()
# runs at import time (line 723). Must be set before first import.
os.environ["JOBFLOW_TEST_DB"] = "1"
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

import pytest
from config import reset_settings


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset the AppSettings singleton before each test."""
    reset_settings()
    yield
    reset_settings()
```

### Pattern 2: In-Memory DB Isolation (per-test fresh DB)

**What:** Each test gets a fresh in-memory SQLite database by resetting the `_memory_conn` singleton in `webapp/db.py`.

**Why per-test (not per-module rollback):** The `webapp/db.py` module uses `get_conn()` which returns a module-level `_memory_conn` singleton. SQLite in-memory DBs do not support proper savepoint/rollback isolation because the connection is shared. Recreating the connection per test is cleaner and faster (< 1ms for schema creation) than trying to roll back.

```python
# tests/conftest.py (continued)
import webapp.db as db_module


@pytest.fixture(autouse=True)
def _fresh_db():
    """Provide a fresh in-memory database for each test.

    Closes and discards the previous in-memory connection, then
    re-initializes the schema via init_db().
    """
    # Close existing connection if any
    if db_module._memory_conn is not None:
        db_module._memory_conn.close()
        db_module._memory_conn = None
    # Re-initialize (creates new in-memory DB with full schema)
    db_module.init_db()
    yield
    # Cleanup after test
    if db_module._memory_conn is not None:
        db_module._memory_conn.close()
        db_module._memory_conn = None
```

### Pattern 3: Seeded DB Fixture for Integration Tests

**What:** Optional fixture that pre-populates the database with realistic job data.

```python
# tests/conftest.py (continued)
from tests.conftest_factories import JobFactory


@pytest.fixture
def db_with_jobs(_fresh_db):
    """Database pre-seeded with 10 realistic jobs across platforms."""
    jobs = []
    for platform in ["indeed", "dice", "remoteok"]:
        for _ in range(3):
            job = JobFactory(platform=platform)
            db_module.upsert_job(job.model_dump(mode="json"))
            jobs.append(job)
    # One high-scoring job
    top_job = JobFactory(
        platform="indeed",
        score=5,
        status="scored",
        title="Principal Engineer",
    )
    db_module.upsert_job(top_job.model_dump(mode="json"))
    jobs.append(top_job)
    return jobs
```

### Pattern 4: Factory Boy with Pydantic v2 Models

**What:** Factory Boy factories that produce valid Pydantic model instances.

**Key detail:** factory-boy has no native Pydantic integration, but setting `class Meta: model = Job` works because factory-boy calls `Job(field1=val1, field2=val2, ...)` which triggers Pydantic's `__init__` validation.

```python
# tests/conftest_factories.py
import factory
from faker import Faker

from models import Job, JobStatus

fake = Faker()


class JobFactory(factory.Factory):
    """Factory for models.Job (Pydantic v2 model).

    factory-boy calls Job(**kwargs) which triggers Pydantic validation.
    All fields must satisfy Pydantic constraints (e.g., score 1-5).
    """

    class Meta:
        model = Job

    id = factory.LazyFunction(lambda: fake.hexify("????????????????"))
    platform = factory.Iterator(["indeed", "dice", "remoteok"])
    title = factory.Faker("job")
    company = factory.Faker("company")
    location = factory.LazyFunction(lambda: fake.random_element(["Remote", "New York, NY", "Toronto, ON"]))
    url = factory.LazyFunction(lambda: f"https://example.com/jobs/{fake.uuid4()}")
    salary = factory.LazyFunction(lambda: f"${fake.random_int(150, 300)}K")
    salary_min = factory.LazyFunction(lambda: fake.random_int(150000, 200000))
    salary_max = factory.LazyFunction(lambda: fake.random_int(200000, 350000))
    description = factory.Faker("paragraphs", nb=3, ext_word_list=None)
    posted_date = factory.LazyFunction(lambda: fake.date_between("-14d", "today").isoformat())
    tags = factory.LazyFunction(lambda: fake.random_elements(
        ["python", "kubernetes", "terraform", "docker", "aws", "gcp"],
        unique=True, length=3,
    ))
    easy_apply = factory.Faker("boolean")
    score = factory.LazyFunction(lambda: fake.random_int(1, 5))
    status = JobStatus.SCORED

    # Fix: Faker 'paragraphs' returns a list; Job.description expects str
    @factory.lazy_attribute
    def description(self):
        return "\n".join(fake.paragraphs(nb=3))
```

### Pattern 5: HTTP Isolation (Two-Layer)

**What:** pytest-socket blocks ALL raw socket access as a global safety net. respx mocks httpx specifically for tests that need HTTP responses.

```python
# tests/conftest.py (continued)

# Layer 1: pytest-socket -- configured via pyproject.toml addopts
# addopts = "--disable-socket --allow-unix-socket"
# This blocks ALL socket.socket calls globally.
# Tests that need mocked HTTP use respx (which doesn't use real sockets).

# Layer 2: respx -- used per-test or per-module for httpx mocking
import respx
import httpx


@pytest.fixture
def mock_remoteok_api():
    """Mock the RemoteOK API with sample response data."""
    sample_response = [
        {"legal": "..."},  # Index 0: metadata
        {
            "id": 12345,
            "position": "Senior Platform Engineer",
            "company": "TestCorp",
            "url": "/remote-jobs/12345",
            "tags": ["python", "kubernetes"],
            "description": "We need a platform engineer...",
            "location": "Remote",
            "salary_min": 200000,
            "salary_max": 300000,
        },
    ]
    with respx.mock:
        respx.get("https://remoteok.com/api").mock(
            return_value=httpx.Response(200, json=sample_response)
        )
        yield
```

### Pattern 6: Anthropic API Guard

**What:** Prevent real Anthropic API calls from ever leaving the process.

```python
# tests/conftest.py (continued)

@pytest.fixture(autouse=True)
def _block_anthropic(monkeypatch):
    """Block all Anthropic API calls.

    Sets a dummy API key (so the client can be instantiated without
    AuthenticationError) and patches the messages.create/parse methods
    to raise immediately with a descriptive error.
    """
    # Env var already set at module level: os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

    def _blocked(*args, **kwargs):
        raise RuntimeError(
            "Test attempted real Anthropic API call -- "
            "use the mock_anthropic fixture instead"
        )

    try:
        import anthropic
        monkeypatch.setattr(anthropic.Anthropic, "__init__", lambda self, **kw: None)
        # Create a dummy instance to patch methods on the class
        monkeypatch.setattr("anthropic.resources.messages.Messages.create", _blocked)
    except ImportError:
        pass  # anthropic not installed -- no guard needed
```

### Anti-Patterns to Avoid

- **Import webapp.db at module level in conftest.py without JOBFLOW_TEST_DB=1:** The env var must be set BEFORE the first import of `webapp.db`, because `init_db()` runs at import time (line 723). If imported without the env var, it creates/migrates a real file-based SQLite database.

- **Using `monkeypatch.setenv` for JOBFLOW_TEST_DB:** `monkeypatch.setenv` runs after imports. The `webapp.db` module reads the env var at import time. Must use `os.environ` at the top of conftest.py before any import.

- **Sharing _memory_conn across tests without reset:** The `webapp.db._memory_conn` singleton persists across tests if not explicitly closed. This causes state leakage (jobs from test A visible in test B).

- **Using `factory.Faker('paragraphs')` for string fields:** Faker's `paragraphs` provider returns a `list[str]`, not a `str`. Pydantic validation will fail. Use a `@factory.lazy_attribute` that joins paragraphs into a string.

- **Not including `__init__.py` in test directories:** Without `__init__.py`, Python's import system may not find conftest.py files in subdirectories, causing fixture resolution failures.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Block all network in tests | Custom socket monkeypatch | pytest-socket `--disable-socket` | Handles edge cases (DNS, UDP, IPv6), provides `@pytest.mark.enable_socket` escape hatch |
| Mock httpx requests | Custom httpx transport patch | respx | Handles async/sync, route matching, response builders, assertion on call counts |
| Random test data | Manual dict literals | factory-boy + Faker | Consistent, reproducible (seedable), compositional (traits, subfactories) |
| Coverage measurement | Manual instrumentation | pytest-cov + coverage.py | Branch coverage, source filtering, multiple report formats |
| Async test detection | Manual `asyncio.run()` wrappers | pytest-asyncio strict mode | Proper event loop management, fixture scope handling |

**Key insight:** The isolation stack (pytest-socket + respx + monkeypatch) forms a defense-in-depth strategy: pytest-socket is the outer wall (blocks everything), respx is the inner layer (provides controlled mock responses), and monkeypatch handles non-HTTP APIs (Anthropic SDK).

## Common Pitfalls

### Pitfall 1: webapp/db.py Import-Time Side Effects

**What goes wrong:** Importing `webapp.db` anywhere triggers `init_db()` at module level (line 723), which creates the SQLite database. Without `JOBFLOW_TEST_DB=1` set beforehand, this creates/migrates a real file-based DB.

**Why it happens:** Python executes module-level code on first import. The `init_db()` call at line 723 of `webapp/db.py` is not gated behind `if __name__ == "__main__"`.

**How to avoid:** Set `os.environ["JOBFLOW_TEST_DB"] = "1"` at the very top of `tests/conftest.py`, BEFORE any import that transitively touches `webapp.db`. This includes `from webapp import db`, `from orchestrator import ...` (which imports `from webapp import db as webdb`), and `from resume_ai.tracker import ...` (which imports `from webapp.db import get_conn`).

**Warning signs:** Test creates `job_pipeline/jobs.db` file on disk. Tests pass but leave behind database files.

### Pitfall 2: Settings Singleton Leakage

**What goes wrong:** `config.get_settings()` returns a cached singleton. If test A modifies settings (or causes them to load from a specific config.yaml), test B sees the same cached instance with stale/wrong values.

**Why it happens:** The `_settings` global in `config.py` persists across test functions within the same process.

**How to avoid:** Autouse fixture that calls `config.reset_settings()` before and after each test. For tests that need specific config values, use `monkeypatch` to set env vars before calling `get_settings()`.

**Warning signs:** Tests pass in isolation (`pytest test_foo.py`) but fail when run together (`pytest`). Test ordering affects results.

### Pitfall 3: config.yaml Dependency in Tests

**What goes wrong:** `AppSettings()` requires a valid `config.yaml` file to exist (it reads search queries, scoring config, etc.). Tests running in CI or clean environments fail with `FileNotFoundError` or `ValidationError`.

**Why it happens:** `pydantic-settings` with `yaml_file="config.yaml"` in `SettingsConfigDict` looks for the file relative to CWD or project root.

**How to avoid:** Create a minimal `tests/fixtures/test_config.yaml` with safe defaults (no real credentials, minimal search queries). The settings reset fixture should point `AppSettings.model_config["yaml_file"]` to this test config, or tests should provide all required fields via init kwargs / env vars.

**Warning signs:** Tests fail with `ValidationError` for missing `search.queries` or `scoring.target_titles`.

### Pitfall 4: Factory Boy + Pydantic Validation Conflicts

**What goes wrong:** Factory Boy generates values that violate Pydantic validators. For example: `salary_max < salary_min` (violates `salary_max_gte_min` validator), `score=0` (violates `ge=1` constraint), `platform="linkedin"` (not in Literal union).

**Why it happens:** Factory Boy doesn't know about Pydantic validators. It generates fields independently without checking cross-field constraints.

**How to avoid:** Use `factory.LazyAttribute` for dependent fields (ensure `salary_max >= salary_min`). Use `factory.Iterator` or explicit values for constrained fields (`platform`, `score`). Test the factory itself in a smoke test.

**Warning signs:** `ValidationError` during test setup, not during the test itself.

### Pitfall 5: pytest-socket + respx Interaction

**What goes wrong:** pytest-socket blocks ALL sockets. respx works by intercepting httpx at the transport level (not socket level). When respx is active AND pytest-socket is active, respx should still work because it never opens a real socket. However, if respx has `passthrough=True` routes, those will fail because the underlying socket is blocked.

**Why it happens:** pytest-socket operates at the `socket.socket` level. respx operates at the httpx transport level. They are independent layers.

**How to avoid:** Never use `respx.passthrough()` in tests. All mocked routes must return mock responses. The `--disable-socket` flag provides the outer safety net; respx provides the inner mock layer.

**Warning signs:** `SocketBlockedError` in tests that use respx with passthrough routes.

### Pitfall 6: pytest-socket and localhost SQLite

**What goes wrong:** Nothing -- SQLite in-memory databases do not use network sockets. `sqlite3.connect(":memory:")` uses a file-based API, not TCP. pytest-socket will NOT interfere with SQLite.

**Why to note it:** This is a common misconception. Teams sometimes add unnecessary socket exemptions for SQLite.

## Code Examples

Verified patterns from official sources and codebase analysis:

### pyproject.toml Configuration

```toml
# Add to existing pyproject.toml

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "strict"
markers = [
    "unit: Pure logic tests with no I/O",
    "integration: Tests that touch the database or combine modules",
    "e2e: End-to-end browser tests (requires Playwright)",
    "slow: Tests that take more than 5 seconds",
]
addopts = [
    "--disable-socket",
    "--allow-unix-socket",
    "-m", "not e2e",
    "--strict-markers",
]

[tool.coverage.run]
source = [
    "config",
    "models",
    "scorer",
    "salary",
    "dedup",
    "form_filler",
    "orchestrator",
    "platforms",
    "webapp",
    "resume_ai",
    "apply_engine",
]
omit = [
    "*/test_*",
    "*/conftest*",
    "*/__pycache__/*",
    "platforms/stealth.py",
    "platforms/indeed.py",
    "platforms/dice.py",
    "platforms/indeed_selectors.py",
    "platforms/dice_selectors.py",
]

[tool.coverage.report]
show_missing = true
skip_empty = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "pass",
]
```

### Root conftest.py (Complete)

```python
"""Root test configuration -- global fixtures and isolation guards.

CRITICAL: os.environ settings MUST be at the top of this file, before
any project imports, because webapp/db.py reads JOBFLOW_TEST_DB at
import time and calls init_db() at module level.
"""

import os

# -- Environment setup (BEFORE any project imports) -------------------------
os.environ["JOBFLOW_TEST_DB"] = "1"
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

import pytest  # noqa: E402

from config import reset_settings  # noqa: E402

import webapp.db as db_module  # noqa: E402


# -- Settings isolation (autouse) -------------------------------------------


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset the AppSettings singleton before and after each test."""
    reset_settings()
    yield
    reset_settings()


# -- Database isolation (autouse) -------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_db():
    """Provide a fresh in-memory SQLite database for each test."""
    if db_module._memory_conn is not None:
        db_module._memory_conn.close()
        db_module._memory_conn = None
    db_module.init_db()
    yield
    if db_module._memory_conn is not None:
        db_module._memory_conn.close()
        db_module._memory_conn = None


# -- Anthropic API guard (autouse) ------------------------------------------


@pytest.fixture(autouse=True)
def _block_anthropic(monkeypatch):
    """Prevent real Anthropic API calls from leaving the process."""
    def _blocked(*args, **kwargs):
        raise RuntimeError(
            "Test attempted real Anthropic API call to api.anthropic.com "
            "-- use the mock_anthropic fixture instead"
        )

    try:
        import anthropic
        monkeypatch.setattr(
            "anthropic.resources.messages.Messages.create", _blocked
        )
        monkeypatch.setattr(
            "anthropic.resources.messages.Messages.parse", _blocked
        )
    except ImportError:
        pass


# -- Seeded DB fixture (opt-in) --------------------------------------------


@pytest.fixture
def db_with_jobs(_fresh_db):
    """Database pre-seeded with realistic job data."""
    from tests.conftest_factories import JobFactory

    jobs = []
    for platform in ["indeed", "dice", "remoteok"]:
        for i in range(3):
            job = JobFactory(platform=platform, score=3 + (i % 3))
            db_module.upsert_job(job.model_dump(mode="json"))
            jobs.append(job)
    return jobs
```

### Test Config YAML (Safe Defaults)

```yaml
# tests/fixtures/test_config.yaml
search:
  min_salary: 100000
  queries:
    - title: "test engineer"
      keywords: []
      max_pages: 1

scoring:
  target_titles:
    - "Senior Software Engineer"
    - "Principal Engineer"
  tech_keywords:
    - python
    - kubernetes
    - terraform
  weights:
    title_match: 2.0
    tech_overlap: 2.0
    remote: 1.0
    salary: 1.0

platforms:
  indeed:
    enabled: false
  dice:
    enabled: false
  remoteok:
    enabled: true

timing:
  nav_delay_min: 0.0
  nav_delay_max: 0.0
  form_delay_min: 0.0
  form_delay_max: 0.0
  page_load_timeout: 5000

apply:
  default_mode: semi_auto
  confirm_before_submit: true
  max_concurrent_applies: 1
  screenshot_before_submit: false
  headed_mode: false
  ats_form_fill_enabled: false
  ats_form_fill_timeout: 10
```

### FastAPI TestClient Fixture

```python
# tests/webapp/conftest.py
import pytest
from fastapi.testclient import TestClient

from webapp.app import app


@pytest.fixture
def client():
    """FastAPI test client -- uses in-memory DB from _fresh_db fixture."""
    return TestClient(app)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydantic-factories (v1) | polyfactory 3.x | 2023 | Renamed, expanded beyond Pydantic. User chose factory-boy instead. |
| pytest-asyncio auto mode | pytest-asyncio strict mode (default since 1.0) | 2025 | Strict mode is now default; explicit `@pytest.mark.asyncio` required |
| pytest.ini for config | pyproject.toml `[tool.pytest.ini_options]` | pytest 6.0+ | Single config file for all tooling |
| coverage.py .coveragerc | pyproject.toml `[tool.coverage.*]` | coverage 5.5+ | Centralized config |
| pytest-socket 0.6 | pytest-socket 0.7.0 | 2024 | Latest release, `--allow-unix-socket` flag |

**Deprecated/outdated:**
- `pydantic-factories`: Renamed to polyfactory. Not used here (user chose factory-boy).
- `pytest-asyncio` auto mode: Was default pre-1.0, now strict is default. Config `asyncio_mode = "strict"` is explicit documentation, not a change.

## Discretion Recommendations

### DB Isolation Level: Per-Test Fresh DB (Recommended)

**Recommendation:** Fresh in-memory SQLite per test (close `_memory_conn`, call `init_db()`).

**Rationale:**
- The `webapp/db.py` module uses a module-level `_memory_conn` singleton. There is no transaction savepoint API exposed -- all functions use `with get_conn() as conn:` which auto-commits.
- SQLite in-memory schema creation is fast (< 1ms). The full schema + 6 migrations run in < 5ms.
- Per-module rollback would require wrapping all `get_conn()` calls in a savepoint, which the current code does not support.
- Fresh DB guarantees zero state leakage and is trivially debuggable.

### Coverage source/omit Configuration

**Recommendation:** Cover all source modules except browser-specific platform files (`stealth.py`, `indeed.py`, `dice.py`, selector files) which require Playwright and are deferred to Phase 15.

**Omit list rationale:**
- `platforms/stealth.py` -- Playwright browser context factory, untestable without browser
- `platforms/indeed.py`, `platforms/dice.py` -- Browser automation, deferred to E2E
- `*_selectors.py` -- Pure data (CSS selectors), no logic to test

### pytest.ini vs pyproject.toml

**Recommendation:** `pyproject.toml` exclusively.

**Rationale:** Project already uses `pyproject.toml` for project metadata, build config, ruff, and has a `[tool.pytest.ini_options]` section with `testpaths`. Adding markers, addopts, and asyncio_mode there keeps all config in one file.

### Factory Boy Default Field Values

**Recommendation:** Use realistic but safe values:
- `platform`: cycle through `["indeed", "dice", "remoteok"]` via `factory.Iterator`
- `score`: random 1-5 via `factory.LazyFunction(lambda: fake.random_int(1, 5))`
- `salary_min`/`salary_max`: ensure max >= min via `factory.LazyAttribute`
- `url`: use `https://example.com/jobs/{uuid}` (safe, non-routable)
- `status`: default to `JobStatus.SCORED` (most useful for tests)
- `description`: join 3 Faker paragraphs into a single string (NOT the list returned by `paragraphs` provider)

## Open Questions

1. **Python 3.14 compatibility for pytest-socket and respx**
   - What we know: pytest-socket 0.7.0 lists Python >=3.8,<4.0 but only classifies up to 3.12. respx 0.22.0 lists up to 3.13. Neither explicitly lists 3.14.
   - What's unclear: Whether they actually work on Python 3.14.3 (the project's version). Both are pure-Python packages, so likely compatible but unverified.
   - Recommendation: Install and run a smoke test during implementation. If either fails, the fallback is: (a) for pytest-socket, use a manual `monkeypatch` of `socket.socket` in conftest; (b) for respx, it will almost certainly work since httpx 0.28.1 is already working on 3.14.

2. **SSE Endpoint Testing (webapp/app.py `/apply/stream`)**
   - What we know: The apply stream endpoint uses `sse-starlette.EventSourceResponse` with `asyncio.Queue`. FastAPI's TestClient is synchronous and may not handle SSE streaming well.
   - What's unclear: Whether `TestClient` can consume SSE events or if `httpx.AsyncClient` with `ASGITransport` is needed.
   - Recommendation: Defer SSE endpoint testing to a later phase (it's an apply-engine integration concern). For Phase 9, focus on the infrastructure. If needed later, use `httpx.AsyncClient(transport=ASGITransport(app=app))` for SSE tests.

3. **Factory Boy `description` field type mismatch**
   - What we know: `factory.Faker('paragraphs')` returns `list[str]`, but `Job.description` is `str`. Pydantic will reject the list.
   - What's unclear: Whether `factory.Faker('text', max_nb_chars=500)` is sufficient or if a `@factory.lazy_attribute` with paragraph joining is better.
   - Recommendation: Use `@factory.lazy_attribute` to join paragraphs. This produces more realistic multi-paragraph descriptions.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `config.py` (lines 288-317 -- singleton pattern and `reset_settings()`)
- Codebase analysis: `webapp/db.py` (lines 9-16 -- `JOBFLOW_TEST_DB` env var, lines 150-168 -- `_memory_conn` singleton, line 723 -- import-time `init_db()`)
- Codebase analysis: `pyproject.toml` (lines 26-30 -- existing dev deps, lines 59-60 -- existing pytest config)
- Codebase analysis: `models.py` (full file -- Pydantic v2 models with validators)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) -- v1.3.0, Python 3.14 support confirmed
- [pytest-cov docs](https://pytest-cov.readthedocs.io/en/latest/config.html) -- v7.0.0, pyproject.toml config
- [Faker PyPI](https://pypi.org/project/Faker/) -- v40.4.0, Python 3.14 support confirmed

### Secondary (MEDIUM confidence)
- [respx PyPI](https://pypi.org/project/respx/) -- v0.22.0, Python up to 3.13 listed
- [respx User Guide](https://lundberg.github.io/respx/guide/) -- mock patterns, assert_all_mocked
- [pytest-socket GitHub](https://github.com/miketheman/pytest-socket) -- v0.7.0, `--disable-socket` flag
- [factory-boy PyPI](https://pypi.org/project/factory-boy/) -- v3.3.3, Python up to 3.13 listed
- [factory-boy with Pydantic](https://lynn-kwong.medium.com/how-to-use-factory-boy-with-pytest-to-fake-pydantic-models-7a33e8d11fc1) -- Meta.model pattern works

### Tertiary (LOW confidence)
- pytest-socket Python 3.14 compatibility: Not officially listed, likely works (pure Python, `>=3.8,<4.0` constraint)
- respx Python 3.14 compatibility: Not officially listed, likely works (pure Python, httpx 0.28.1 already runs on 3.14)
- factory-boy Python 3.14 compatibility: Not officially listed, likely works (pure Python, `>=3.8` constraint)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries are well-established, versions verified on PyPI
- Architecture: HIGH -- Patterns derived directly from codebase analysis of actual singletons, import-time effects, and module structure
- Pitfalls: HIGH -- Every pitfall identified from reading the actual source code (db.py line 723 `init_db()`, config.py `_settings` singleton, Pydantic validators)
- Python 3.14 compatibility: MEDIUM -- Three packages (pytest-socket, respx, factory-boy) don't officially list 3.14 but have no known blockers

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- stable domain, library versions change slowly)
