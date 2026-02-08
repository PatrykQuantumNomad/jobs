# Testing Patterns

**Analysis Date:** 2026-02-07

## Test Framework

**Runner:**
- pytest (declared in `pyproject.toml` dev dependencies)
- Version: 8.0.0+
- Config: `[tool.pytest.ini_options]` in `pyproject.toml`

**Assertion Library:**
- pytest's built-in assertions (no separate library)

**Run Commands:**
```bash
uv run pytest              # Run all tests
# Note: No tests currently exist in the codebase
```

**Coverage:**
- Not configured (no coverage tool in dependencies)

## Test File Organization

**Location:**
- Test directory configured: `testpaths = ["tests"]` in `pyproject.toml`
- **Current state:** No `tests/` directory exists, no test files found

**Naming:**
- Expected pattern: `test_*.py` or `*_test.py` (pytest default discovery)
- Expected location: `tests/test_orchestrator.py`, `tests/test_scorer.py`, etc.

**Structure:**
- Not applicable (no tests exist)
- Recommended: Mirror source structure in `tests/` directory

## Current Testing Status

**Test Coverage: ZERO**

The codebase has pytest configured but no tests implemented. Key areas that should have tests:

**Critical untested modules:**
- `orchestrator.py` (569 lines) - Main pipeline orchestration
- `scorer.py` (226 lines) - Job scoring logic
- `salary.py` (207 lines) - Salary parsing with complex regex
- `dedup.py` (178 lines) - Fuzzy deduplication algorithm
- `platforms/indeed.py` (367 lines) - Browser automation with anti-detection
- `platforms/dice.py` - Browser automation
- `platforms/remoteok.py` - API integration
- `config.py` (411 lines) - Multi-source settings loading
- `webapp/app.py` (656 lines) - FastAPI endpoints

**Testing approach used instead:**
- Manual end-to-end testing via `uv run jobs-scrape --headed`
- Live browser observation during development
- Debug screenshots saved to `debug_screenshots/` on errors
- Manual verification of scoring output in `job_pipeline/tracker.md`

## Recommended Test Structure

**Unit Tests:**
- `tests/test_salary.py` - Salary parsing edge cases
  - Test K-notation: "150K" → 150000
  - Test hourly conversion: "$85/hr" → 176800
  - Test currency detection: "CAD", "USD", "EUR"
  - Test range parsing: "$150,000 - $200,000"
  - Test RemoteOK integer quirk: `salary_max = 0` handling

- `tests/test_scorer.py` - Scoring logic isolation
  - Test title matching: exact vs keyword
  - Test tech keyword counting: 0, 2, 5+ matches
  - Test location scoring: "remote", "ontario", etc.
  - Test salary overlap: target $200K threshold
  - Test weighted scoring: verify 1-5 mapping

- `tests/test_dedup.py` - Deduplication correctness
  - Test exact key matching
  - Test fuzzy company matching: "Google" vs "Google LLC"
  - Test threshold boundaries: FUZZY_COMPANY_THRESHOLD = 90
  - Test alias tracking
  - Test preference logic: newer posting wins

**Integration Tests:**
- `tests/test_config.py` - Settings loading
  - Test YAML parsing
  - Test .env loading and override precedence
  - Test validation errors
  - Test `build_candidate_profile()` construction

- `tests/test_registry.py` - Platform registration
  - Test decorator validation
  - Test duplicate key detection
  - Test protocol compliance checking
  - Test missing method detection

**Fixtures needed:**
- Sample job data: `@pytest.fixture` returning `Job` instances
- Mock browser context: For testing platform classes without Playwright
- Config file mocks: Temporary `.env` and `config.yaml` for isolated tests
- Database fixture: In-memory SQLite for webapp tests

## Common Patterns

**No existing test patterns to analyze.**

Recommended patterns based on codebase structure:

**Async Testing:**
- Use `pytest-asyncio` for FastAPI endpoint tests
- Mark async tests with `@pytest.mark.asyncio`

**Browser Automation Testing:**
- Mock Playwright `Page` and `BrowserContext` for unit tests
- Use `pytest-playwright` for true browser integration tests
- Fixtures for persistent context cleanup

**Pydantic Model Testing:**
```python
def test_job_model_validation():
    # Valid job
    job = Job(
        platform="indeed",
        title="Senior Engineer",
        company="Google",
        url="https://indeed.com/job/123"
    )
    assert job.platform == "indeed"

    # Validation error
    with pytest.raises(ValidationError):
        Job(platform="invalid", title="", company="", url="")
```

**Settings Testing:**
```python
def test_settings_yaml_loading(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
    search:
      queries: []
      min_salary: 150000
    scoring:
      target_titles: ["Senior Engineer"]
      tech_keywords: ["kubernetes"]
    """)

    settings = get_settings(str(config_file))
    assert settings.search.min_salary == 150000
    reset_settings()  # Clean up singleton
```

## Test Data Management

**Current approach:**
- Real data from platforms used for manual testing
- Raw JSON files in `job_pipeline/` serve as integration test verification
- No fixtures or test data generators

**Recommended approach:**
- Create `tests/fixtures/` directory with sample JSON
- Factory functions for generating test `Job` instances
- Parameterized tests for edge cases

**Example fixture structure:**
```python
# tests/conftest.py
import pytest
from models import Job, JobStatus

@pytest.fixture
def sample_job():
    return Job(
        id="test-123",
        platform="indeed",
        title="Senior Software Engineer",
        company="Acme Corp",
        location="Remote",
        url="https://example.com/job/123",
        salary="$150,000 - $200,000",
        score=4,
        status=JobStatus.SCORED,
    )

@pytest.fixture
def job_batch():
    return [
        Job(platform="indeed", title="Engineer A", company="Co A", url="url1"),
        Job(platform="dice", title="Engineer B", company="Co B", url="url2"),
        Job(platform="remoteok", title="Engineer C", company="Co C", url="url3"),
    ]
```

## Mocking Strategy

**No mocking currently used.**

**Recommended mocking points:**
- Playwright browser operations: Mock `Page.goto()`, `Page.query_selector()`
- HTTP requests: Mock `httpx.AsyncClient` for RemoteOK API tests
- File system: Mock `Path.read_text()`, `Path.write_text()` for config tests
- Environment variables: Mock `os.getenv()` for credential tests

**Example mock pattern:**
```python
from unittest.mock import Mock, patch

def test_indeed_login_success():
    mock_page = Mock()
    mock_page.title.return_value = "Indeed Dashboard"
    mock_page.query_selector.return_value = Mock()  # Logged-in indicator found

    platform = IndeedPlatform()
    platform.page = mock_page

    assert platform.is_logged_in() is True
```

## Testing Tools Available

**Declared in `pyproject.toml`:**
- pytest 8.0.0+
- ruff 0.9.0+ (for linting tests too)

**Missing but recommended:**
- pytest-cov - Code coverage measurement
- pytest-asyncio - Async test support
- pytest-playwright - Browser automation testing
- pytest-mock - Simplified mocking utilities
- testcontainers - For database integration tests

**Add with:**
```bash
uv add --group dev pytest-cov pytest-asyncio pytest-mock
```

## Human-in-the-Loop Testing

**Current approach:**
- `--headed` flag shows browser for visual verification
- `wait_for_human()` prompts pause automation for manual steps
- Screenshots saved to `debug_screenshots/` on errors
- Confirmation prompts before application submission

**Testing challenges:**
- Cannot automate CAPTCHA solving
- Cannot automate Google OAuth flow
- Cannot automate email verification
- Cannot test "submit application" without actually applying

**Recommended test approach:**
- Mock human input prompts in tests
- Use fixture data to bypass browser steps
- Integration tests stop before actual submission
- Document manual test checklist for full end-to-end

## Performance Testing

**No performance tests exist.**

**Recommended areas:**
- Fuzzy deduplication performance on large job batches (1000+ jobs)
- Salary parsing regex performance
- Database query performance in webapp
- Concurrent search across multiple platforms

## Error Scenario Testing

**Current error handling tested manually:**
- CAPTCHA detection (raises RuntimeError with screenshot)
- 404 job pages (detected via page title check)
- Missing selectors (try/except PwTimeout, multiple fallbacks)
- Invalid config (Pydantic ValidationError at startup)

**Recommended error tests:**
- Test CAPTCHA detection logic without triggering real CAPTCHA
- Test 404 handling with mock page titles
- Test selector failures with missing elements
- Test config validation with invalid YAML/env combinations

## CI/CD Integration

**No CI pipeline configured.**

**Recommended CI setup:**
```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest --cov
      - run: uv run ruff check .
```

## Test Isolation

**No tests = no isolation issues yet.**

**Recommended practices:**
- Reset `_settings` singleton after each config test: `reset_settings()`
- Clear `_REGISTRY` after platform registration tests (add `reset_registry()` helper)
- Use `tmp_path` fixture for file operations
- In-memory SQLite (`:memory:`) for database tests

---

*Testing analysis: 2026-02-07*

**Current state:** Zero tests implemented. Framework configured, ready for test development. High-risk areas (salary parsing, deduplication, scoring) should be prioritized for unit test coverage.
