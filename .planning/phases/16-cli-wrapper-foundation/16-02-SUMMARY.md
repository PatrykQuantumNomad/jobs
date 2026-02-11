---
phase: 16-cli-wrapper-foundation
plan: 02
subsystem: ai
tags: [claude-cli, subprocess, async, sdk-migration, resume-ai, cover-letter]

# Dependency graph
requires:
  - phase: 16-01
    provides: "claude_cli package with async subprocess wrapper and typed Pydantic output"
provides:
  - "resume_ai/tailor.py using claude_cli.run() instead of anthropic SDK"
  - "resume_ai/cover_letter.py using claude_cli.run() instead of anthropic SDK"
  - "webapp/app.py awaiting async functions directly (no asyncio.to_thread)"
  - "anthropic SDK fully removed from runtime dependencies"
  - "Test infrastructure using subprocess mocks instead of SDK mocks"
affects: [17-resume-streaming, 18-cover-letter-streaming, 19-ai-scoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "async def for AI functions using claude_cli.run() with CLIError -> RuntimeError wrapping"
    - "mock_claude_cli controller fixture with set_response()/set_error() methods"
    - "_block_cli autouse fixture patches asyncio.create_subprocess_exec globally"

key-files:
  created: []
  modified:
    - resume_ai/tailor.py
    - resume_ai/cover_letter.py
    - webapp/app.py
    - pyproject.toml
    - tests/conftest.py
    - tests/resume_ai/conftest.py
    - tests/resume_ai/test_tailor.py
    - tests/resume_ai/test_cover_letter.py
    - tests/test_smoke.py

key-decisions:
  - "Wrap CLIError in RuntimeError for backward compatibility with webapp error handling"
  - "Use model alias 'sonnet' instead of full model ID for CLI (CLI resolves aliases)"
  - "Controller pattern for mock_claude_cli fixture (set_response/set_error methods)"

patterns-established:
  - "AI function signature: async def func(...) -> PydanticModel with CLIError -> RuntimeError"
  - "mock_claude_cli fixture: controller with set_response(model_instance) and set_error(rc, stderr)"
  - "Production code never imports anthropic -- all AI via claude_cli.run()"

# Metrics
duration: 5min
completed: 2026-02-11
---

# Phase 16 Plan 02: SDK Migration Summary

**Replaced Anthropic SDK with claude_cli.run() in tailor/cover-letter code, made both async, removed SDK from dependencies, updated all tests to subprocess mocks**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-11T15:54:46Z
- **Completed:** 2026-02-11T16:00:22Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Converted tailor_resume() and generate_cover_letter() from synchronous Anthropic SDK to async claude_cli.run()
- Removed anthropic SDK from pyproject.toml runtime dependencies entirely
- Updated webapp/app.py to await AI functions directly (no asyncio.to_thread wrapper needed)
- Replaced _block_anthropic and mock_anthropic test fixtures with _block_cli and mock_claude_cli
- All 563 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert resume_ai to use claude_cli and update webapp call sites** - `39de611` (feat)
2. **Task 2: Update test infrastructure and resume_ai tests for subprocess mocks** - `412e239` (test)

## Files Modified
- `resume_ai/tailor.py` - Async resume tailoring via claude_cli.run() with CLIError wrapping
- `resume_ai/cover_letter.py` - Async cover letter generation via claude_cli.run() with CLIError wrapping
- `webapp/app.py` - Direct await of tailor_resume() and generate_cover_letter() (no to_thread)
- `pyproject.toml` - Removed anthropic dependency, added claude_cli to wheel packages and coverage
- `tests/conftest.py` - Replaced _block_anthropic with _block_cli (patches create_subprocess_exec)
- `tests/resume_ai/conftest.py` - Replaced mock_anthropic with mock_claude_cli controller fixture
- `tests/resume_ai/test_tailor.py` - Async tests with CLI subprocess mocks
- `tests/resume_ai/test_cover_letter.py` - Async tests with CLI subprocess mocks
- `tests/test_smoke.py` - TestCLIGuard, TestNoAnthropicSDKInProduction, removed SDK-specific tests

## Decisions Made
- Wrapped CLIError in RuntimeError at the resume_ai boundary to maintain backward compatibility with webapp's generic exception handler
- Used CLI model alias "sonnet" instead of full model ID "claude-sonnet-4-5-20250929" -- the CLI resolves aliases internally
- Created a controller pattern for mock_claude_cli fixture with set_response() and set_error() methods for cleaner test setup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Claude CLI must already be installed (established in Phase 16-01).

## Next Phase Readiness
- Phase 16 is now complete: claude_cli package built (16-01) and wired into all production code (16-02)
- Zero production files import anthropic -- SDK fully removed from runtime
- All AI features route through claude_cli.run() which is natively async
- Ready for Phase 17 (SSE streaming for resume tailoring) and Phase 18 (SSE streaming for cover letters)
- mock_claude_cli fixture pattern available for all downstream test suites

## Self-Check: PASSED

- All 9 modified files exist on disk
- Task 1 commit verified (39de611)
- Task 2 commit verified (412e239)
- 563 tests pass, zero regressions
- Zero production files import anthropic
- anthropic not in pyproject.toml dependencies

---
*Phase: 16-cli-wrapper-foundation*
*Completed: 2026-02-11*
