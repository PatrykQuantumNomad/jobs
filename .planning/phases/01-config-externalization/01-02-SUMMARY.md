---
phase: 01-config-externalization
plan: 02
subsystem: config
tags: [pydantic-settings, config-migration, scoring-weights, cli-validation]

# Dependency graph
requires:
  - phase: 01-config-externalization (plan 01)
    provides: AppSettings model, get_settings() singleton, ScoringWeights, directory constants, Config shim
provides:
  - orchestrator.py using get_settings() for all configuration
  - scorer.py accepting configurable ScoringWeights via constructor
  - form_filler.py using get_settings() for CandidateProfile
  - --validate CLI flag for dry-run config checking
affects: [01-config-externalization plan 03 (platform migration), 02-protocol-architecture, 04-dashboard-rewrite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Settings injection: pipeline core receives config via get_settings() constructor pattern"
    - "Weighted scoring: ScoringWeights scales raw 0-2 factors with configurable multipliers"
    - "CLI validation: --validate flag for config dry-run without pipeline execution"

key-files:
  created: []
  modified:
    - orchestrator.py
    - scorer.py
    - form_filler.py

key-decisions:
  - "Weighted scoring formula preserves original behavior with default weights (title_match=2.0, tech_overlap=2.0, remote=1.0, salary=1.0)"
  - "Orchestrator loads settings eagerly in __init__ and passes to JobScorer explicitly"
  - "--platforms CLI default changed from hardcoded list to settings.enabled_platforms()"
  - "--validate prints config stats (platforms, queries, titles, keywords) in addition to pass/fail"

patterns-established:
  - "Settings injection: get_settings() called in constructors, config objects passed to collaborators"
  - "CLI validation pattern: try get_settings() catch ValidationError for user-friendly error output"

# Metrics
duration: 5min
completed: 2026-02-07
---

# Phase 1 Plan 2: Pipeline Core Migration Summary

**Migrated orchestrator, scorer, and form_filler from Config class to get_settings() with configurable scoring weights and --validate CLI flag**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-07T16:34:49Z
- **Completed:** 2026-02-07T16:39:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- scorer.py accepts optional ScoringWeights that scale raw scoring factors; default weights reproduce identical scoring to original hardcoded logic
- form_filler.py uses get_settings().build_candidate_profile() instead of Config.CANDIDATE
- orchestrator.py replaced all 15 Config.X references with get_settings() equivalents and directory constants
- New --validate flag checks config.yaml + .env validity and prints config stats without running the pipeline
- --platforms default now uses settings.enabled_platforms() instead of hardcoded ["indeed", "dice", "remoteok"]

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate scorer.py and form_filler.py** - `bd1ec82` (feat)
2. **Task 2: Migrate orchestrator.py and add --validate** - `08720ba` (feat)

## Files Created/Modified
- `scorer.py` - Replaced Config import with get_settings/ScoringWeights; weighted scoring formula
- `form_filler.py` - Replaced Config.CANDIDATE with get_settings().build_candidate_profile()
- `orchestrator.py` - Replaced all Config references with get_settings() and directory constants; added --validate CLI flag

## Decisions Made
- **Weighted scoring formula:** Raw scores (0-2 for title/tech, 0-1 for remote/salary) are multiplied by weight/max_raw_for_factor. With default weights, `title_raw * 2.0/2.0 + tech_raw * 2.0/2.0 + remote_raw * 1.0 + salary_raw * 1.0` = identical to original `title + tech + remote + salary`. This allows users to tune scoring in config.yaml without changing code.
- **Eager settings loading:** Orchestrator calls get_settings() once in __init__ and stores it as self.settings, passing derived objects (profile, weights) to collaborators. This avoids repeated singleton lookups and makes dependencies explicit.
- **--validate exit behavior:** Exits with code 0 on success (printing config stats), code 1 on validation failure (printing each error location and message). Credential warnings are non-fatal since Indeed uses session auth (no credentials needed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing E501 line-too-long in _sanitize**
- **Found during:** Task 2 (orchestrator.py migration)
- **Issue:** `_sanitize()` helper was 103 chars, exceeding 100-char ruff limit (pre-existing from original code)
- **Fix:** Split return into two lines: `safe = ...` then `return safe.strip()...`
- **Files modified:** orchestrator.py
- **Verification:** `ruff check orchestrator.py` passes
- **Committed in:** 08720ba (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial formatting fix. No scope creep.

## Issues Encountered
- Python 3.14 specified in `.python-version` is not installed via pyenv; used project `.venv` (Python 3.14.3) for import verification and `PYENV_VERSION=3.13.1` for ruff linting. No impact on deliverables.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- orchestrator.py, scorer.py, and form_filler.py are fully migrated
- Plan 01-03 (platform module migration) can proceed: platforms/base.py, platforms/stealth.py, platforms/indeed.py, platforms/dice.py, platforms/remoteok.py, and webapp/ still import Config
- After plan 01-03, the Config shim in config.py can be removed entirely

## Self-Check: PASSED

---
*Phase: 01-config-externalization*
*Completed: 2026-02-07*
