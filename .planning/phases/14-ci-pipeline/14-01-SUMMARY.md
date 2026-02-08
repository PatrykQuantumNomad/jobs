---
phase: 14-ci-pipeline
plan: 01
subsystem: infra
tags: [github-actions, ci, coverage, ruff, playwright, uv]

# Dependency graph
requires:
  - phase: 09-test-infrastructure
    provides: pytest config, markers, coverage settings
  - phase: 10-unit-tests
    provides: unit test suite for CI to run
  - phase: 11-database-integration-tests
    provides: integration test suite for CI to run
  - phase: 12-web-api-integration-tests
    provides: API/web test suite for CI to run
  - phase: 13-config-integration-tests
    provides: config test suite for CI to run
provides:
  - GitHub Actions CI workflow with test-lint and e2e jobs
  - Coverage threshold enforcement (fail_under = 80)
  - Automated ruff linting on every push/PR
  - Concurrency control for CI runs
affects: [15-e2e-tests]

# Tech tracking
tech-stack:
  added: [github-actions, astral-sh/setup-uv@v7, astral-sh/ruff-action@v3, actions/upload-artifact@v5]
  patterns: [uv-based CI without setup-python, coverage threshold in pyproject.toml not CLI]

key-files:
  created: [.github/workflows/ci.yml]
  modified: [pyproject.toml]

key-decisions:
  - "Coverage threshold in pyproject.toml (fail_under=80), not as CLI flag -- single source of truth for local and CI"
  - "setup-uv@v7 handles Python installation from .python-version -- no setup-python needed"
  - "Playwright browsers NOT cached per official recommendation (restore time equals download time)"
  - "E2E job uses continue-on-error: true and || true for exit code 5 (no tests collected)"

patterns-established:
  - "CI config: coverage/lint thresholds in pyproject.toml, workflow just runs tools"
  - "E2E separation: non-blocking job that depends on test-lint passing first"

# Metrics
duration: 2min
completed: 2026-02-08
---

# Phase 14 Plan 01: CI Pipeline Summary

**GitHub Actions CI with test-lint job (pytest + coverage + ruff) and optional non-blocking E2E job (Playwright), using astral-sh/setup-uv@v7 for Python/dependency management and fail_under=80 coverage threshold**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-08T20:17:07Z
- **Completed:** 2026-02-08T20:19:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Coverage threshold (fail_under = 80) added to pyproject.toml -- single source of truth for local and CI enforcement
- GitHub Actions workflow with two jobs: required test-lint and optional e2e
- Concurrency group cancels in-progress runs when new commits push to same ref
- All five CI requirements (CI-01 through CI-05) satisfied in one workflow file

## Task Commits

Each task was committed atomically:

1. **Task 1: Add coverage threshold to pyproject.toml** - `f378441` (chore)
2. **Task 2: Create GitHub Actions CI workflow** - `6e6cc16` (feat)

## Files Created/Modified
- `.github/workflows/ci.yml` - GitHub Actions CI workflow with test-lint and e2e jobs
- `pyproject.toml` - Added fail_under = 80 to [tool.coverage.report]

## Decisions Made
- Coverage threshold in pyproject.toml (fail_under=80), not as CLI flag -- avoids duplication between local and CI
- astral-sh/setup-uv@v7 handles Python installation via .python-version -- no actions/setup-python needed
- Playwright browsers NOT cached per official Playwright recommendation (restore time equals download time)
- E2E job uses continue-on-error: true plus || true to handle exit code 5 when no e2e tests exist yet
- WeasyPrint system dependencies (libpango, libpangoft2, libharfbuzz-subset) installed via apt-get in both jobs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. The CI workflow triggers automatically on push/PR to main.

## Next Phase Readiness
- CI pipeline is ready -- pushing to main or opening a PR will trigger test-lint and e2e jobs
- Phase 15 (E2E Tests) will add actual Playwright tests that the e2e job will discover via `-m e2e`
- Current coverage is ~63% which will cause CI to fail on the coverage gate until more tests bring it to 80% -- this is intentional and signals test gaps
- The `|| true` in the e2e pytest command handles the current state where no e2e tests exist (exit code 5)

---
*Phase: 14-ci-pipeline*
*Completed: 2026-02-08*
