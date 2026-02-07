---
phase: 01-config-externalization
plan: 03
subsystem: platforms
tags: [config-migration, get_settings, platforms, timing, credentials]

# Dependency graph
requires:
  - 01-01 (AppSettings foundation, get_settings() singleton, Config shim)
provides:
  - All platform modules consuming get_settings() directly
  - Zero Config class references in platforms/
affects:
  - 01-02 (parallel consumer migration -- scorer, orchestrator, form_filler)
  - Future phases can safely remove the Config shim once 01-02 also completes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "get_settings().timing for delay/timeout values in platform modules"
    - "get_settings().search.min_salary for salary filtering"
    - "get_settings().scoring.tech_keywords for RemoteOK tag matching"
    - "get_settings().validate_platform_credentials() for credential checks"

# File tracking
key-files:
  created: []
  modified:
    - platforms/base.py
    - platforms/indeed.py
    - platforms/dice.py
    - platforms/remoteok.py

# Decisions
decisions:
  - id: "03-01"
    description: "Use get_settings().timing shortcut (local var) to avoid repeated singleton lookups in hot paths"
    rationale: "Cleaner code, single call per method instead of repeated get_settings() chains"
  - id: "03-02"
    description: "Import DEBUG_SCREENSHOTS_DIR as module constant in base.py rather than calling get_settings()"
    rationale: "Directory path is static and already exported as module constant from config.py"
  - id: "03-03"
    description: "Use get_settings().scoring.tech_keywords instead of build_candidate_profile().tech_keywords for RemoteOK"
    rationale: "Avoids constructing full CandidateProfile just to access tech keywords that live in scoring config"

# Metrics
metrics:
  duration: "5 min"
  completed: "2026-02-07"
---

# Phase 01 Plan 03: Platform Module Migration Summary

**Migrated all four platform modules (base.py, indeed.py, dice.py, remoteok.py) from legacy Config class to get_settings() -- timing delays, page timeouts, credentials, and salary filters now read from config.yaml/.env via AppSettings.**

## What Changed

### platforms/base.py
- Replaced `from config import Config` with `from config import DEBUG_SCREENSHOTS_DIR, get_settings`
- `human_delay()`: timing delays read from `get_settings().timing` instead of `Config.NAV_DELAY_MIN/MAX` and `Config.FORM_DELAY_MIN/MAX`
- `screenshot()`: uses imported `DEBUG_SCREENSHOTS_DIR` constant instead of `Config.DEBUG_SCREENSHOTS_DIR`

### platforms/indeed.py
- Replaced `from config import Config` with `from config import get_settings`
- `login()`: page_load_timeout read from `settings.timing.page_load_timeout` (3 occurrences, stored as local var)
- `search()`: page_load_timeout via settings
- `get_job_details()`: page_load_timeout via settings
- `apply()`: page_load_timeout via settings
- `_build_search_url()`: min_salary read from `get_settings().search.min_salary`

### platforms/dice.py
- Replaced `from config import Config` with `from config import get_settings`
- `login()`: credentials via `settings.dice_email` and `settings.dice_password`, credential validation via `settings.validate_platform_credentials("dice")`, page_load_timeout via settings
- `search()`: page_load_timeout via settings
- `get_job_details()`: page_load_timeout via settings
- `apply()`: page_load_timeout via settings

### platforms/remoteok.py
- Replaced `from config import Config` with `from config import get_settings`
- `search()`: min_salary read from `get_settings().search.min_salary`
- `_filter_terms()`: tech_keywords read from `get_settings().scoring.tech_keywords`
- Fixed pre-existing `timezone.utc` -> `UTC` alias (UP017 lint)

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Migrate base.py and remoteok.py | `c3632ac` | platforms/base.py, platforms/remoteok.py |
| 2 | Migrate indeed.py and dice.py | `6a9e793` | platforms/indeed.py, platforms/dice.py |

## Verification Results

- `ruff check` passes on all four platform files
- All four modules import successfully (no runtime errors)
- `grep -rn "from config import Config" platforms/*.py` returns nothing
- `grep -rn "Config\." platforms/*.py` returns nothing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing ruff lint errors in platform files**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** Pre-existing lint violations (UP017 timezone.utc alias in remoteok.py, E741 ambiguous variable name in dice.py, SIM108 ternary suggestions in dice.py and indeed.py) caused ruff to fail
- **Fix:** Applied all lint fixes alongside the Config migration
- **Files modified:** platforms/remoteok.py, platforms/dice.py, platforms/indeed.py
- **Commits:** c3632ac, 6a9e793

## Decisions Made

1. **Use `timing` local variable shortcut** -- Instead of `get_settings().timing.page_load_timeout` on every call, methods store `timing = get_settings().timing` or `timeout = settings.timing.page_load_timeout` as a local var.

2. **Import DEBUG_SCREENSHOTS_DIR directly** -- `base.py` imports the module constant from config.py rather than accessing via `get_settings()`, since it's a static path.

3. **Use scoring.tech_keywords for RemoteOK** -- Instead of `build_candidate_profile().tech_keywords`, use `get_settings().scoring.tech_keywords` directly to avoid constructing the full CandidateProfile.

## Next Phase Readiness

Platform modules are fully migrated. Once 01-02 completes (orchestrator, scorer, form_filler), the Config shim in config.py can be safely removed. No blockers identified.

## Self-Check: PASSED
