---
phase: 01-config-externalization
plan: 01
subsystem: config
tags: [pydantic-settings, yaml, config, validation, singleton]

# Dependency graph
requires: []
provides:
  - AppSettings model with nested sub-models for all config sections
  - Lazy singleton get_settings() / reset_settings()
  - config.yaml with all current operational values
  - config.example.yaml with comprehensive comments
  - CandidateProfile without hardcoded personal data
  - Backward-compatible Config shim for existing consumers
affects:
  - 01-config-externalization (plans 02, 03 -- consumer migration)
  - All phases using config.py

# Tech tracking
tech-stack:
  added: [pydantic-settings 2.12.0, pyyaml]
  patterns:
    - "Multi-source settings: YAML for ops config, .env for secrets/personal data"
    - "Lazy singleton via get_settings() -- no import-time side effects"
    - "Backward compat shim: Config class delegates to AppSettings"

key-files:
  created:
    - config.yaml
    - config.example.yaml
  modified:
    - config.py
    - models.py
    - pyproject.toml

key-decisions:
  - "Added backward-compatible Config shim to avoid breaking existing consumers"
  - "Used extra='ignore' on AppSettings root to avoid rejecting unrecognized env vars"
  - "Personal profile fields default to empty strings, populated from .env via build_candidate_profile()"

patterns-established:
  - "Config singleton: get_settings() for cached instance, reset_settings() for testing"
  - "YAML sections map 1:1 to nested BaseModel sub-models"
  - "SearchQueryConfig.platforms list for per-query platform filtering"

# Metrics
duration: 6min
completed: 2026-02-07
---

# Phase 1 Plan 1: AppSettings Foundation Summary

**pydantic-settings AppSettings model with YAML config source, lazy singleton, and backward-compatible Config shim**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-07T16:25:01Z
- **Completed:** 2026-02-07T16:31:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Replaced monolithic Config class with validated AppSettings(BaseSettings) using pydantic-settings
- Created config.yaml with all 22 search queries, 6 target titles, 34 tech keywords, platform toggles, and timing
- Created config.example.yaml with inline comments on every field for new-user onboarding
- Removed all hardcoded personal data from CandidateProfile (now populated from .env)
- Preserved backward compatibility via Config shim -- existing consumers (scorer, orchestrator, platforms) continue working

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AppSettings model and sub-models in config.py** - `6ba6aa8` (feat)
2. **Task 2: Create config.yaml, config.example.yaml, and update models.py** - `7f5891c` (feat)

## Files Created/Modified
- `config.py` - Complete rewrite: AppSettings with nested sub-models, get_settings(), ensure_directories(), Config shim
- `models.py` - CandidateProfile: removed hardcoded defaults, all personal fields now empty string
- `pyproject.toml` - Added pydantic-settings[yaml]>=2.12.0 dependency
- `config.yaml` - Operational config: 22 queries, scoring weights, platform toggles, timing
- `config.example.yaml` - Heavily commented template with placeholder values for new users

## Decisions Made
- **Backward-compatible Config shim:** Added a Config class that delegates to AppSettings via get_settings(). This prevents breaking the 6+ existing consumers (orchestrator.py, scorer.py, form_filler.py, platforms/base.py, platforms/indeed.py, platforms/dice.py, platforms/remoteok.py) that import `from config import Config`. Plans 01-02 and 01-03 will migrate them and remove the shim.
- **extra="ignore" on root:** AppSettings uses `extra="ignore"` to avoid rejecting unexpected environment variables from .env (like DICE_PASSWORD which isn't a model field name pattern but is a valid credential).
- **Empty string defaults for personal fields:** CandidateProfile fields default to "" rather than None, keeping the str type consistent. Actual values come from .env via build_candidate_profile().

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added backward-compatible Config shim**
- **Found during:** Task 1 (config.py rewrite)
- **Issue:** Plan did not mention backward compatibility, but 6+ existing modules import `from config import Config`. Removing Config would break scorer.py, orchestrator.py, form_filler.py, and all platform modules.
- **Fix:** Added a Config class that delegates static attributes and classmethods to the new AppSettings singleton via get_settings(). This ensures existing code continues to work while Plans 01-02 and 01-03 migrate consumers.
- **Files modified:** config.py
- **Verification:** `from config import Config; Config.get_search_queries('indeed')` returns 22 queries
- **Committed in:** 6ba6aa8 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for maintaining working codebase. Without the shim, all existing modules would fail to import. No scope creep -- the shim is temporary and will be removed in Plan 02-03.

## Issues Encountered
- Python 3.14 specified in .python-version but not installed via pyenv. Resolved by using existing .venv which already had Python 3.14.3 installed.
- pip was not present in the venv. Resolved with `python -m ensurepip` before installing dependencies.
- Pre-existing ruff lint warnings in models.py (UP042 on JobStatus, SIM102 on salary_max_gte_min) -- these are in unchanged code and will be addressed in a separate cleanup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- AppSettings foundation is ready for consumer migration in Plans 01-02 and 01-03
- Config shim ensures zero breakage during incremental migration
- config.yaml and config.example.yaml are committed and ready

## Self-Check: PASSED

---
*Phase: 01-config-externalization*
*Completed: 2026-02-07*
