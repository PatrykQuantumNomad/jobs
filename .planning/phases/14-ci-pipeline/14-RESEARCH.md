# Phase 14: CI Pipeline - Research

**Researched:** 2026-02-08
**Domain:** GitHub Actions CI/CD for Python project with pytest, coverage enforcement, ruff linting, and Playwright E2E
**Confidence:** HIGH

## Summary

Phase 14 adds a GitHub Actions CI pipeline to a Python 3.14 project managed by `uv` with 417 existing tests (unit + integration) that complete in ~1.5 seconds at 63% coverage. The project uses `ruff` for linting (currently passing clean), `pytest-cov` for coverage, and `pytest-asyncio` for async tests. E2E tests (Phase 15, not yet implemented) will use Playwright and must run as a separate, non-blocking CI job.

The standard approach is a single workflow file (`.github/workflows/ci.yml`) with two jobs: (1) a required `test-and-lint` job that runs pytest with coverage enforcement and ruff check, and (2) an optional `e2e` job that installs Playwright browsers and runs `pytest -m e2e`. The `astral-sh/setup-uv@v7` action handles uv installation, Python resolution from `.python-version`, and dependency caching natively. System dependencies for WeasyPrint (Pango, HarfBuzz) must be installed via `apt` before `uv sync`.

**Primary recommendation:** Use `astral-sh/setup-uv@v7` with `enable-cache: true` as the foundation. Skip `actions/setup-python` entirely -- `setup-uv` reads `.python-version` (which already pins `3.14`) and manages Python installation via `uv python install`. Add `fail_under = 80` to `[tool.coverage.report]` in `pyproject.toml`. Use `astral-sh/ruff-action@v3` for linting (separate step, reads `pyproject.toml` config). Make the E2E job `continue-on-error: true` so it does not block PR merges.

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `astral-sh/setup-uv` | v7 | Install uv, manage Python, cache deps | Official Astral action; built-in caching, reads `.python-version` and `uv.lock` |
| `actions/checkout` | v6 | Clone repository | Official GitHub action |
| `astral-sh/ruff-action` | v3 | Run ruff linting | Official Astral action; zero-config, reads `pyproject.toml` |
| `actions/upload-artifact` | v5 | Upload coverage/trace artifacts | Official GitHub action for CI artifacts |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `actions/cache` | v5 | Manual cache control | Only if `setup-uv` built-in caching proves insufficient (unlikely) |
| `actions/setup-python` | v6 | Install Python independently | NOT needed -- `setup-uv` handles Python via `.python-version` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `astral-sh/setup-uv` | `actions/setup-python` + manual pip/uv install | Requires separate caching setup, more YAML boilerplate, no lockfile-aware caching |
| `astral-sh/ruff-action` | `uv run ruff check .` step | Works fine but ruff-action provides `--output-format=github` annotations for free |
| `continue-on-error: true` on E2E job | Separate workflow with `workflow_dispatch` trigger | Separate workflow is harder to discover and won't show status on PRs |

## Architecture Patterns

### Recommended Workflow Structure

```
.github/
└── workflows/
    └── ci.yml           # Single workflow, two jobs
```

### Pattern 1: Single Workflow, Two Jobs

**What:** One `ci.yml` with a required `test-lint` job and an optional `e2e` job.
**When to use:** Always -- keeps CI configuration in one place.
**Why:** The test suite (417 tests, 1.5s) is fast enough for a single job. Splitting unit vs integration into separate jobs adds complexity with no speed benefit.

```yaml
# Source: astral-sh/setup-uv official docs + Playwright Python CI docs
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install system dependencies
        run: sudo apt-get update && sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

      - name: Install Python and project dependencies
        run: uv sync --locked --dev

      - name: Lint with ruff
        uses: astral-sh/ruff-action@v3

      - name: Run tests with coverage
        run: uv run pytest --cov --cov-report=term-missing --cov-report=xml

      - name: Upload coverage artifact
        uses: actions/upload-artifact@v5
        if: always()
        with:
          name: coverage-report
          path: coverage.xml

  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    continue-on-error: true
    needs: test-lint
    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install system dependencies
        run: sudo apt-get update && sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

      - name: Install Python and project dependencies
        run: uv sync --locked --dev

      - name: Install Playwright browsers
        run: uv run playwright install --with-deps chromium

      - name: Run E2E tests
        run: uv run pytest -m e2e --tracing=retain-on-failure

      - name: Upload traces
        uses: actions/upload-artifact@v5
        if: always()
        with:
          name: playwright-traces
          path: test-results/
```

### Pattern 2: Coverage Enforcement via pyproject.toml

**What:** Set `fail_under` in `[tool.coverage.report]` rather than as a CLI flag.
**When to use:** Always -- keeps the threshold in version control, not duplicated in CI YAML and local dev commands.

```toml
# In pyproject.toml
[tool.coverage.report]
fail_under = 80
```

Then `uv run pytest --cov` will exit non-zero if coverage drops below 80%. No `--cov-fail-under` flag needed in CI.

### Pattern 3: uv sync --locked for Reproducibility

**What:** Use `--locked` flag to fail CI if `uv.lock` is out of date.
**When to use:** Always in CI -- catches developers who modify `pyproject.toml` without running `uv lock`.

### Anti-Patterns to Avoid

- **Caching Playwright browsers:** Playwright's official docs explicitly recommend against this. "The amount of time it takes to restore the cache is comparable to the time it takes to download the binaries." Use `playwright install --with-deps` every time.
- **Splitting unit and integration into separate jobs:** With 1.5s total runtime, parallelizing adds overhead (job setup, dependency install) that dwarfs any time saved.
- **Using `actions/setup-python` alongside `setup-uv`:** Redundant. `setup-uv` reads `.python-version` and installs Python via `uv python install`. Adding `setup-python` creates version conflicts.
- **Hardcoding coverage threshold in CI YAML:** Use `[tool.coverage.report] fail_under` in `pyproject.toml` so local and CI enforcement are identical.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python + uv installation | Manual `curl` + `pip install uv` | `astral-sh/setup-uv@v7` | Handles caching, version pinning, `.python-version` reading |
| Ruff installation + invocation | `pip install ruff && ruff check .` | `astral-sh/ruff-action@v3` | Zero-config, GitHub annotations, version management |
| Dependency caching | `actions/cache` with manual key computation | `setup-uv` `enable-cache: true` | Built-in, uses `uv.lock` hash automatically |
| Coverage threshold enforcement | Custom script parsing coverage output | `[tool.coverage.report] fail_under = 80` | Native pytest-cov feature, works locally and in CI |

**Key insight:** The `astral-sh/setup-uv@v7` action eliminates most caching complexity. Its built-in cache uses `uv.lock` hash as cache key, prunes automatically, and handles Python version resolution. Manual `actions/cache` is only needed for Playwright browsers (which should NOT be cached per official recommendation).

## Common Pitfalls

### Pitfall 1: Missing System Dependencies for WeasyPrint

**What goes wrong:** `uv sync` succeeds but `import weasyprint` fails at test time with `OSError: cannot load library 'libpango-1.0-0'`.
**Why it happens:** WeasyPrint depends on Pango, HarfBuzz, and related C libraries that are not installed on `ubuntu-latest` by default.
**How to avoid:** Add `apt-get install` step BEFORE `uv sync`: `sudo apt-get update && sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`
**Warning signs:** Tests pass locally (macOS has these via Homebrew) but fail in CI.

### Pitfall 2: Python 3.14 Not Available Without Correct Configuration

**What goes wrong:** `setup-uv` or `setup-python` cannot find Python 3.14.
**Why it happens:** Python 3.14.3 was added to GitHub Actions runners on 2026-02-04. The `.python-version` file contains `3.14`. `setup-uv` reads this and uses `uv python install` which downloads from python-build-standalone.
**How to avoid:** Use `astral-sh/setup-uv@v7` which handles Python installation via `uv python install`. If using `actions/setup-python@v6` instead, Python 3.14 is available as of 2026-02-04 without `allow-prereleases`.
**Warning signs:** CI fails with "Python 3.14 not found" -- update action versions.

### Pitfall 3: uv.lock Out of Date

**What goes wrong:** `uv sync --locked` fails because `uv.lock` doesn't match `pyproject.toml`.
**Why it happens:** Developer modified `pyproject.toml` but forgot to run `uv lock`.
**How to avoid:** The `--locked` flag in CI catches this immediately. Developers should run `uv lock` locally after dependency changes.
**Warning signs:** CI fails on the "Install dependencies" step with a lockfile mismatch error.

### Pitfall 4: Coverage Threshold Blocks CI Due to Uncovered New Code

**What goes wrong:** Developer adds new module without tests, CI fails on coverage threshold.
**Why it happens:** `fail_under = 80` is checked against total coverage across all configured sources.
**How to avoid:** This is actually DESIRED behavior -- it forces test coverage for new code. Current coverage is 63%, so the threshold of 80% means tests must be added for uncovered modules before enabling the threshold. Consider starting at a lower threshold or ramping up.
**Warning signs:** Coverage is currently 63%. Setting `fail_under = 80` immediately would fail CI. Options: (a) start at 60% and ramp up, (b) wait for more test phases to complete, (c) accept 80% as a goal that may initially fail.

### Pitfall 5: E2E Job Blocks PR Merges

**What goes wrong:** PR cannot be merged because E2E tests (which may be flaky or not yet implemented) fail.
**Why it happens:** The E2E job is configured as a required check in branch protection rules.
**How to avoid:** Use `continue-on-error: true` on the E2E job. Do NOT add it to branch protection required checks. Only `test-lint` should be required.
**Warning signs:** PR shows yellow (pending) or red (failed) for E2E but green for test-lint. Verify branch protection settings.

### Pitfall 6: conftest.py Import-Time Side Effects in CI

**What goes wrong:** Tests fail with database errors or missing environment variables.
**Why it happens:** `tests/conftest.py` sets `JOBFLOW_TEST_DB=1` and `ANTHROPIC_API_KEY=test-key-not-real` before importing project modules. If pytest collects tests before conftest runs (shouldn't happen, but CI environments can be surprising), imports fail.
**How to avoid:** The existing conftest.py handles this correctly. No CI-specific changes needed. Just verify tests pass in CI the same as locally.
**Warning signs:** `ModuleNotFoundError` or `AuthenticationError` in CI but not locally.

## Code Examples

### Example 1: Complete ci.yml Workflow

```yaml
# Source: astral-sh/setup-uv docs, Playwright Python CI docs, pytest-cov docs
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install system dependencies (WeasyPrint)
        run: |
          sudo apt-get update
          sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

      - name: Install Python and project dependencies
        run: uv sync --locked --dev

      - name: Lint
        uses: astral-sh/ruff-action@v3

      - name: Test with coverage
        run: uv run pytest --cov --cov-report=term-missing --cov-report=xml

      - name: Upload coverage
        uses: actions/upload-artifact@v5
        if: always()
        with:
          name: coverage-report
          path: coverage.xml
          retention-days: 14

  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    continue-on-error: true
    needs: test-lint

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install system dependencies (WeasyPrint)
        run: |
          sudo apt-get update
          sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0

      - name: Install Python and project dependencies
        run: uv sync --locked --dev

      - name: Install Playwright browsers
        run: uv run playwright install --with-deps chromium

      - name: Run E2E tests
        run: uv run pytest -m e2e --tracing=retain-on-failure

      - name: Upload Playwright traces
        uses: actions/upload-artifact@v5
        if: always()
        with:
          name: playwright-traces
          path: test-results/
          retention-days: 7
```

### Example 2: pyproject.toml Coverage Threshold Addition

```toml
# Add to existing [tool.coverage.report] section
[tool.coverage.report]
show_missing = true
skip_empty = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "pass",
]
```

### Example 3: Concurrency Control

```yaml
# Cancel in-progress CI runs when a new push arrives on the same branch
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This prevents resource waste when developers push multiple commits in quick succession.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install` + `actions/cache` for venv | `astral-sh/setup-uv@v7` with built-in caching | 2025-2026 | Eliminates ~15 lines of cache YAML, handles lockfile hashing |
| `actions/setup-python` for Python install | `setup-uv` reads `.python-version` and uses `uv python install` | 2025+ | One action handles both uv and Python, no version conflicts |
| `pip install ruff && ruff check .` | `astral-sh/ruff-action@v3` | 2024+ | Zero-config, GitHub PR annotations |
| `actions/checkout@v4` | `actions/checkout@v6` | 2026 | Improved performance, node20 runtime |
| Cache Playwright browsers with `actions/cache` | Don't cache -- `playwright install --with-deps` | Playwright docs (current) | Cache restore time equals download time; system deps can't be cached |
| `allow-prereleases: true` for Python 3.14 | Python 3.14 GA builds available on runners | 2026-02-04 | `setup-python@v6` supports 3.14 without prereleases flag |

**Deprecated/outdated:**
- `actions/checkout@v3`, `actions/checkout@v4`: Older node runtimes, use `v6`
- `actions/setup-python` for uv projects: Redundant when `setup-uv` manages Python
- `actions/cache` for uv dependencies: Replaced by `setup-uv` built-in caching
- `allow-prereleases: true` for Python 3.14: No longer needed as of Feb 2026

## Open Questions

1. **Coverage threshold: 80% vs current 63%**
   - What we know: Current total coverage is 63%. The requirement says 80%.
   - What's unclear: Whether all preceding test phases (10-13) will be complete and raise coverage above 80% before Phase 14 executes.
   - Recommendation: Set `fail_under = 80` in `pyproject.toml` as specified. If coverage is below 80% when CI goes live, the pipeline will correctly fail, signaling that more tests are needed. This is the intended behavior. Alternatively, the planner could make this a two-step process: (a) create the workflow with the threshold, (b) verify coverage meets the threshold and adjust if needed.

2. **E2E tests don't exist yet (Phase 15)**
   - What we know: No tests are marked `@pytest.mark.e2e`. The E2E job will collect zero tests and pass vacuously.
   - What's unclear: Whether a vacuous pass is acceptable or if the E2E job should be skipped entirely until Phase 15.
   - Recommendation: Include the E2E job in the workflow now. `pytest -m e2e` with no matching tests exits with code 5 (no tests collected), which pytest reports as a failure. Add `--no-header -rN` flags or handle the exit code. Simplest: add `|| true` after the pytest command in the E2E step, or use `continue-on-error: true` (already planned). When Phase 15 adds E2E tests, the job will start running them automatically.

3. **Branch protection rules**
   - What we know: CI-01 requires tests run on push to main and on PR. CI-05 requires E2E not blocking.
   - What's unclear: Whether branch protection rules should be configured as part of this phase.
   - Recommendation: Branch protection configuration is a GitHub settings change, not a code change. Document in the plan that `test-lint` should be added as a required check and `e2e` should NOT be. Actual configuration is a manual step.

4. **WeasyPrint system dependencies on `ubuntu-latest`**
   - What we know: WeasyPrint needs `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0`. These are not pre-installed on `ubuntu-latest`.
   - What's unclear: Whether the exact package names are correct for the current `ubuntu-latest` (Noble 24.04).
   - Recommendation: Add the `apt-get install` step and test. If package names changed, the CI will fail with a clear error indicating which package is missing. HIGH confidence these names are correct based on WeasyPrint's own CI configuration.

## Sources

### Primary (HIGH confidence)
- [astral-sh/setup-uv README](https://github.com/astral-sh/setup-uv) - Caching, Python version management, all inputs
- [Using uv in GitHub Actions (Astral docs)](https://docs.astral.sh/uv/guides/integration/github/) - Official workflow examples, `uv sync --locked`
- [astral-sh/ruff-action](https://github.com/astral-sh/ruff-action) - v3, inputs, YAML examples
- [Playwright Python CI docs](https://playwright.dev/python/docs/ci) - GitHub Actions workflow, browser installation, anti-caching recommendation
- [coverage.py config reference](https://coverage.readthedocs.io/en/latest/config.html) - `fail_under` in `[tool.coverage.report]`
- [pytest-cov config docs](https://pytest-cov.readthedocs.io/en/latest/config.html) - `--cov-fail-under`, report formats

### Secondary (MEDIUM confidence)
- [actions/python-versions releases](https://github.com/actions/python-versions/releases) - Python 3.14.3 available for Linux 22.04/24.04 as of 2026-02-04
- [actions/checkout releases](https://github.com/actions/checkout/releases) - v6 is current
- [WeasyPrint First Steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) - System dependency list for Ubuntu
- [actions/setup-python@v5 README](https://github.com/actions/setup-python/tree/v5) - Python 3.14 support, `allow-prereleases` flag

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools verified via official documentation and READMEs
- Architecture: HIGH - Workflow structure follows official examples from Astral and Playwright
- Pitfalls: HIGH - WeasyPrint deps, Python 3.14, and Playwright caching verified against official docs
- Coverage threshold: MEDIUM - 80% target is specified in requirements, but current 63% means it may fail initially

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- GitHub Actions ecosystem moves slowly)
