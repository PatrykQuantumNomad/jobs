---
phase: 002-fix-ci-coverage
plan: 01
subsystem: testing
tags: [pytest, pytest-cov, coverage, unit-tests, integration-tests, mock-anthropic]

# Dependency graph
requires:
  - phase: v1.1
    provides: "Full codebase with resume_ai, apply_engine, webapp modules"
provides:
  - "115 new tests covering resume_ai (96%), apply_engine (events/dedup/engine helpers), webapp untested routes"
  - "80.01% total coverage (up from 62.61%), CI fail_under=80 now passes"
  - "Protocol and mixin tests for platforms module"
affects: [CI pipeline, any future code changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "mock_anthropic fixture for Anthropic API testing"
    - "Mock Jinja2 DictLoader + WeasyPrint for renderer tests"
    - "threading.Event-based dashboard confirmation testing"
    - "_TestPlatform concrete class for mixin testing"

key-files:
  created:
    - tests/resume_ai/test_models.py
    - tests/resume_ai/test_tailor.py
    - tests/resume_ai/test_cover_letter.py
    - tests/resume_ai/test_diff.py
    - tests/resume_ai/test_extractor.py
    - tests/resume_ai/test_renderer.py
    - tests/resume_ai/test_tracker.py
    - tests/apply_engine/__init__.py
    - tests/apply_engine/test_events.py
    - tests/apply_engine/test_dedup.py
    - tests/apply_engine/test_engine.py
    - tests/platforms/test_protocols.py
    - tests/platforms/test_mixins.py
  modified:
    - tests/webapp/test_endpoints.py

key-decisions:
  - "Mock WeasyPrint HTML class and Jinja2 DictLoader instead of real template rendering for renderer tests"
  - "Test get_versions_for_job ordering as set membership rather than strict ordering (SQLite second-level timestamp precision)"
  - "Cover platforms/mixins.py to 100% via mock page + input patching to reach 80% threshold"

patterns-established:
  - "apply_engine tests use mock settings to avoid real config loading and Playwright imports"
  - "Protocol compliance tested via isinstance checks on mock conforming/non-conforming classes"

# Metrics
duration: 8min
completed: 2026-02-08
---

# Quick Task 002: Fix CI -- Increase Test Coverage from 62.61% to 80%+

**115 new tests across resume_ai, apply_engine, platforms, and webapp bringing coverage from 62.61% to 80.01% -- CI fail_under=80 now passes**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-08T22:54:26Z
- **Completed:** 2026-02-08T23:03:20Z
- **Tasks:** 3
- **Files created:** 13
- **Files modified:** 1

## Accomplishments

- resume_ai/ coverage: 0% (except validator) to 96% across all 7 submodules
- apply_engine/ coverage: ~2% to 100% for events, dedup, and engine sync helpers (30% overall due to untestable browser code)
- webapp/app.py: 10 new test classes covering kanban, analytics, run history, stats cards, apply endpoints, resume versions
- platforms/mixins.py: 27% to 100% via mock page and input patching
- Total: 532 tests pass (up from 417 existing), 80.01% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tests for resume_ai/ module** - `867510c` (test)
2. **Task 2: Add tests for apply_engine/ and untested webapp routes** - `0e39039` (test)
3. **Task 3: Verify full test suite with >= 80% coverage** - `bf35a16` (test)

## Files Created/Modified

- `tests/resume_ai/test_models.py` - SkillSection, WorkExperience, TailoredResume, CoverLetter Pydantic model tests
- `tests/resume_ai/test_tailor.py` - tailor_resume API mocking, error handling, format_resume_as_text
- `tests/resume_ai/test_cover_letter.py` - generate_cover_letter API mocking, format_cover_letter_as_text
- `tests/resume_ai/test_diff.py` - HTML diff table generation and CSS wrapping
- `tests/resume_ai/test_extractor.py` - PDF text extraction with monkeypatched pymupdf4llm
- `tests/resume_ai/test_renderer.py` - PDF rendering with mocked Jinja2 DictLoader + WeasyPrint
- `tests/resume_ai/test_tracker.py` - Resume version CRUD against in-memory SQLite
- `tests/apply_engine/__init__.py` - Package init
- `tests/apply_engine/test_events.py` - ApplyEventType enum, ApplyEvent model, factory functions
- `tests/apply_engine/test_dedup.py` - is_already_applied for all status permutations
- `tests/apply_engine/test_engine.py` - ApplyEngine confirm/cancel/queue/emit/resume-path helpers
- `tests/platforms/test_protocols.py` - BrowserPlatform/APIPlatform runtime isinstance checks
- `tests/platforms/test_mixins.py` - BrowserPlatformMixin utilities with mock page
- `tests/webapp/test_endpoints.py` - Added 11 new test classes for untested routes

## Decisions Made

- Mocked WeasyPrint and Jinja2 via DictLoader rather than requiring real templates in CI -- keeps tests fast and isolated
- Used set membership assertion for `get_versions_for_job` ordering since SQLite `created_at` has second-level precision (both inserts in same second)
- Targeted platforms/mixins.py (100%) and platforms/protocols.py (isinstance checks) to reach the 80% threshold rather than attempting to test heavy browser automation code

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_tracker ordering assertion**
- **Found during:** Task 1 (resume_ai tests)
- **Issue:** `test_returns_versions_for_job` asserted strict ordering but SQLite `created_at` has second-level precision -- both inserts within same second have identical timestamps
- **Fix:** Changed assertion from strict `versions[0]["file_path"]` check to set membership `{v["file_path"] for v in versions}`
- **Files modified:** tests/resume_ai/test_tracker.py
- **Verification:** Test passes consistently
- **Committed in:** 867510c (Task 1 commit)

**2. [Rule 3 - Blocking] Added protocol and mixin tests to reach 80% threshold**
- **Found during:** Task 3 (coverage verification)
- **Issue:** Coverage was 78% after Tasks 1-2, short of the 80% threshold. Plan anticipated this and suggested targeting protocols.py and mixins.py
- **Fix:** Added test_protocols.py (6 tests), test_mixins.py (13 tests), and one webapp test for _parse_score exception branch
- **Files modified:** tests/platforms/test_protocols.py, tests/platforms/test_mixins.py, tests/webapp/test_endpoints.py
- **Verification:** Coverage reached 80.01%
- **Committed in:** bf35a16 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in test, 1 blocking coverage gap)
**Impact on plan:** Both expected -- plan explicitly anticipated the coverage gap in Task 3. No scope creep.

## Issues Encountered

None -- all tests passed on first run (except the expected ordering fix in tracker tests).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CI coverage threshold of 80% is now met
- All 532 tests pass with zero failures
- No regressions in existing 417 tests
- Coverage report shows remaining gaps are in browser automation code (apply_engine/engine.py _apply_browser/_fill_external_form) which requires real Playwright -- appropriate for E2E tests only

## Self-Check: PASSED

- All 15 files verified present on disk
- All 3 task commits verified in git log (867510c, 0e39039, bf35a16)

---
*Quick Task: 002-fix-ci-coverage*
*Completed: 2026-02-08*
