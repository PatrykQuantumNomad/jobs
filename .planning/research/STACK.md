# Technology Stack: Testing & CI Additions

**Project:** JobFlow v1.1 -- Automated Test Suite + CI Pipeline
**Researched:** 2026-02-08

## Recommended Stack

### Core Testing Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | >=8.0.0 | Test runner and framework | Already in dev dependencies. Industry standard for Python. Fixture system handles this codebase's singleton patterns cleanly. |
| pytest-cov | >=6.0.0 | Coverage measurement | Integrates with pytest. Generates HTML, XML, and terminal reports. Required for CI coverage gates. |
| pytest-asyncio | >=0.24.0 | Async test support | Required for testing async functions directly (apply engine's `apply()` method). FastAPI TestClient handles async routes without this, but needed for direct async unit testing. |

### HTTP/API Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | >=0.27.0 | HTTP client | Already a project dependency. FastAPI TestClient is backed by httpx. |
| respx | >=0.22.0 | Mock httpx requests | Purpose-built for mocking httpx. RemoteOK uses `httpx.Client`. respx provides pytest fixtures, pattern matching, and call assertions. Preferred over `unittest.mock` for HTTP interactions. |

### Browser Testing (E2E only)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest-playwright | >=0.5.0 | Playwright pytest integration | Official Microsoft plugin. Provides `browser`, `context`, and `page` fixtures with automatic cleanup per test. Already have playwright as a dependency. |

### CI/CD

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| GitHub Actions | N/A | CI pipeline | Repository is on GitHub. Free for public repos. Supports matrix testing for Python versions and OS. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-xdist | >=3.5.0 | Parallel test execution | When test suite exceeds 200 tests and takes >60s. Not needed initially. |
| freezegun | >=1.4.0 | Time/datetime mocking | For testing timestamp-dependent code (activity log `created_at`, `applied_date`). Add when datetime edge cases become important. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP mocking | respx | responses, pytest-httpx | `responses` mocks the `requests` library (we use httpx). `pytest-httpx` works but respx has better pattern matching, built-in call assertions, and wider adoption with httpx. |
| Test runner | pytest | unittest | pytest already in project. Superior fixture system, parametrize decorator, markers, conftest hierarchy. |
| Coverage | pytest-cov | coverage.py directly | pytest-cov wraps coverage.py with pytest integration. Simpler CLI (`pytest --cov`). |
| Browser testing | pytest-playwright | Selenium | Playwright already in project. pytest-playwright is the official Microsoft plugin. Adding Selenium would be redundant. |
| Factory | Simple fixture function | factory-boy, model-bakery | Overkill for ~5 Pydantic models with simple fields. A `_make(**overrides)` function in a fixture suffices. Revisit if object graph complexity grows. |
| Async testing | pytest-asyncio | anyio | pytest-asyncio is simpler. The project only uses asyncio (not trio). |

## Installation

```bash
# Add test dependencies to dev group
uv add --group dev pytest-cov pytest-asyncio respx pytest-playwright

# Playwright browsers (likely already installed from app dependencies)
playwright install chromium
```

### pyproject.toml Changes

```toml
[dependency-groups]
dev = [
    "ruff>=0.9.0",
    "pyright>=1.1.0",
    "pytest>=8.0.0",
    "pytest-cov>=6.0.0",
    "pytest-asyncio>=0.24.0",
    "respx>=0.22.0",
    "pytest-playwright>=0.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Pure logic tests, no I/O (fast)",
    "integration: Tests with DB, HTTP, or config I/O (moderate)",
    "e2e: Browser tests requiring Playwright (slow)",
    "slow: Tests taking >5 seconds",
]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["."]
omit = ["tests/*", ".venv/*", ".planning/*"]

[tool.coverage.report]
show_missing = true
fail_under = 70
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__",
]
```

## Sources

- [pytest documentation](https://docs.pytest.org/en/stable/) -- fixtures, markers, conftest
- [respx on PyPI](https://pypi.org/project/respx/) -- httpx mocking library
- [RESPX User Guide](https://lundberg.github.io/respx/guide/) -- pattern matching, assertions
- [pytest-playwright on PyPI](https://pypi.org/project/pytest-playwright/) -- official Playwright plugin
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) -- TestClient backed by httpx
- [pytest-cov on PyPI](https://pypi.org/project/pytest-cov/) -- coverage integration
