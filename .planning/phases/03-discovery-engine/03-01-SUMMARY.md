---
phase: 03-discovery-engine
plan: 01
subsystem: data-processing
tags: [rapidfuzz, salary-parsing, deduplication, scoring, pydantic]

# Dependency graph
requires:
  - phase: 01-config-externalization
    provides: AppSettings, ScoringWeights, CandidateProfile, get_settings()
provides:
  - "salary.py: unified salary parser (parse_salary, parse_salary_ints, NormalizedSalary)"
  - "dedup.py: two-pass fuzzy deduplication with merge trail (fuzzy_deduplicate)"
  - "scorer.py: ScoreBreakdown dataclass with display_inline/display_with_keywords/to_dict"
  - "models.py: Job.company_aliases, Job.salary_display, Job.salary_currency fields"
affects: [03-02-PLAN (orchestrator wiring), 03-03-PLAN (dashboard UI), webapp/db.py (schema migration)]

# Tech tracking
tech-stack:
  added: [rapidfuzz 3.14.3]
  patterns: [unified-parser-module, two-pass-dedup, breakdown-alongside-score]

key-files:
  created: [salary.py, dedup.py]
  modified: [scorer.py, models.py, pyproject.toml]

key-decisions:
  - "Added ' corporation' to dedup suffix list (not in research examples but needed for Microsoft Corporation -> Microsoft)"
  - "ScoreBreakdown uses stdlib dataclass (not Pydantic) per research recommendation -- lightweight internal struct"
  - "display_inline format: 'Title +N | Tech +N | Remote +N | Salary +N = N' (matches CONTEXT.md spec)"
  - "tech_matched keywords included in breakdown (Claude's discretion from CONTEXT.md)"

patterns-established:
  - "Unified parser pattern: single module replacing scattered platform-specific parsers"
  - "Breakdown-alongside-score: _compute() returns tuple, public methods extract what they need"
  - "Two-pass dedup: exact key (fast) then fuzzy within same-title groups (bounded N)"

# Metrics
duration: 6min
completed: 2026-02-07
---

# Phase 3 Plan 1: Processing Modules Summary

**Unified salary parser handling 8+ formats, two-pass fuzzy dedup with rapidfuzz (threshold 90), and ScoreBreakdown with per-factor points and matched keywords**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-07T18:35:22Z
- **Completed:** 2026-02-07T18:41:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- salary.py parses all known platform formats ($150K, $85/hr, USD verbose, CAD suffix, RemoteOK ints, monthly, None)
- dedup.py merges "Google"/"Google LLC" and "Microsoft"/"Microsoft Corporation" while keeping "Google"/"Alphabet" and "Meta"/"Meta Platforms" separate
- ScoreBreakdown captures title, tech, remote, salary points with display_inline() matching the "Title +2 | Tech +2 | Remote +1 | Salary 0 = 5" format
- NormalizedSalary fields map cleanly to Job.salary_min/salary_max/salary_display/salary_currency

## Task Commits

Each task was committed atomically:

1. **Task 1: Create salary.py, dedup.py, update models and dependencies** - `cbc6f52` (feat)
2. **Task 2: Refactor scorer.py to return ScoreBreakdown alongside int score** - `0f272a7` (feat)

## Files Created/Modified
- `salary.py` - Unified salary parser with NormalizedSalary dataclass, parse_salary(), parse_salary_ints()
- `dedup.py` - Two-pass fuzzy deduplication engine with rapidfuzz company name matching
- `scorer.py` - Added ScoreBreakdown dataclass, score_job_with_breakdown(), score_batch_with_breakdown()
- `models.py` - Added company_aliases, salary_display, salary_currency fields to Job model
- `pyproject.toml` - Added rapidfuzz>=3.14 dependency and build includes for new modules

## Decisions Made
- Added " corporation" to dedup suffix normalization list -- research examples omitted it but "Microsoft Corporation" is a common variant
- Used stdlib `dataclasses` for ScoreBreakdown per research recommendation (internal struct, not serialized via Pydantic)
- Included tech_matched keywords in breakdown (Claude's discretion per CONTEXT.md)
- Currency symbols: USD="$", CAD="C$", EUR="EUR", GBP="GBP" for compact display format

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added " corporation" to company suffix normalization**
- **Found during:** Task 1 (dedup.py verification)
- **Issue:** "Microsoft Corporation" was not merging with "Microsoft" because " corporation" was missing from the suffix list (only " corp.", " corp", " incorporated" were present)
- **Fix:** Added " corporation" to `_COMPANY_SUFFIXES` tuple in dedup.py
- **Files modified:** dedup.py
- **Verification:** "Microsoft" vs "Microsoft Corporation" now correctly merges to 1 result
- **Committed in:** cbc6f52 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- salary.py, dedup.py, and scorer.py ScoreBreakdown are ready for wiring into orchestrator (plan 03-02)
- models.py Job fields ready for schema migration in webapp/db.py (plan 03-02)
- display_inline() and display_with_keywords() formats ready for dashboard templates (plan 03-03)
- rapidfuzz installed and working in the project venv

---
*Phase: 03-discovery-engine*
*Completed: 2026-02-07*
