---
phase: 16-cli-wrapper-foundation
plan: 01
subsystem: ai
tags: [claude-cli, subprocess, pydantic, async, structured-output, json-schema]

# Dependency graph
requires: []
provides:
  - "claude_cli package: async subprocess wrapper for Claude CLI with typed Pydantic output"
  - "CLIError exception hierarchy (7 classes) for all CLI error paths"
  - "Resilient JSON parser handling structured_output and result field regression"
  - "Cold-start retry logic for first-invocation failures"
  - "Auth error detection from stderr and response envelope"
affects: [17-resume-cli-migration, 18-cover-letter-cli-migration, 19-ai-scoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 695 type parameters on generic functions (def func[T: BaseModel])"
    - "asyncio.create_subprocess_exec with PIPE for CLI invocation"
    - "Pydantic model_json_schema() for CLI --json-schema flag"
    - "Separate except clauses to avoid ruff UP rule interference"

key-files:
  created:
    - claude_cli/__init__.py
    - claude_cli/client.py
    - claude_cli/exceptions.py
    - claude_cli/parser.py
    - tests/claude_cli/__init__.py
    - tests/claude_cli/conftest.py
    - tests/claude_cli/test_exceptions.py
    - tests/claude_cli/test_parser.py
    - tests/claude_cli/test_client.py
  modified: []

key-decisions:
  - "Used PEP 695 type parameters (def func[T: BaseModel]) instead of TypeVar per ruff UP047 rule"
  - "Separate except clauses instead of tuple-style to avoid ruff auto-fix breaking multi-exception catches"
  - "Internal _ExecutionResult class encapsulates subprocess output parsing and auth detection"

patterns-established:
  - "claude_cli.run() as single async entry point for all AI features"
  - "Mock subprocess fixture pattern: patch asyncio.create_subprocess_exec + shutil.which"
  - "sample_envelope() helper for building test CLI response envelopes"

# Metrics
duration: 8min
completed: 2026-02-11
---

# Phase 16 Plan 01: claude_cli Package Summary

**Async subprocess wrapper for Claude CLI with 7-class exception hierarchy, resilient JSON parser (structured_output + result fallback), cold-start retry, and 31 tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-11T15:42:14Z
- **Completed:** 2026-02-11T15:50:24Z
- **Tasks:** 2
- **Files created:** 9

## Accomplishments
- Built complete claude_cli package with async subprocess wrapper, resilient parser, and typed exceptions
- Resilient parser handles both structured_output (normal) and result field JSON/markdown (regression per GitHub #18536)
- Cold-start retry (1 automatic retry) for first-invocation failures (GitHub #23265)
- Auth error detection from stderr keywords and response envelope is_error field
- 31 tests covering all error paths with mocked subprocess (no real CLI calls)
- Full existing test suite (563 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create claude_cli package with exceptions, parser, and client** - `1b528ed` (feat)
2. **Task 2: Comprehensive tests for parser, exceptions, and client** - `424a842` (test)

## Files Created
- `claude_cli/__init__.py` - Public API exports: run() and all 7 exception classes
- `claude_cli/exceptions.py` - CLIError hierarchy: NotFound, Timeout, Auth, Process, Malformed, Response
- `claude_cli/parser.py` - Resilient JSON parser: structured_output -> result JSON -> result markdown -> error
- `claude_cli/client.py` - Async subprocess wrapper with timeout, auth detection, cold-start retry
- `tests/claude_cli/__init__.py` - Test package marker
- `tests/claude_cli/conftest.py` - SampleModel, sample_envelope(), mock_subprocess fixture
- `tests/claude_cli/test_exceptions.py` - 8 tests for exception construction and inheritance
- `tests/claude_cli/test_parser.py` - 12 tests for all parser resolution paths
- `tests/claude_cli/test_client.py` - 11 tests for subprocess invocation, errors, retry

## Decisions Made
- Used PEP 695 type parameters (`def func[T: BaseModel]`) instead of `TypeVar` -- required by ruff UP047 rule on Python 3.14
- Used separate `except` clauses instead of tuple-style `except (A, B):` -- ruff's auto-fix destructively converts tuple syntax to Python 2 comma syntax
- Created internal `_ExecutionResult` class to encapsulate subprocess output and separate parsing/auth-detection from the retry loop

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PEP 695 type parameters required by linter**
- **Found during:** Task 1
- **Issue:** Ruff UP047 rule requires PEP 695 type parameter syntax on Python 3.14 target; `TypeVar("T", bound=BaseModel)` was flagged
- **Fix:** Changed `T = TypeVar("T", bound=BaseModel)` + `def func(model: type[T])` to `def func[T: BaseModel](model: type[T])`
- **Files modified:** claude_cli/parser.py, claude_cli/client.py
- **Verification:** `uv run ruff check claude_cli/` passes
- **Committed in:** 1b528ed (Task 1 commit)

**2. [Rule 3 - Blocking] Ruff auto-fix breaks tuple-style except clauses**
- **Found during:** Task 1
- **Issue:** Ruff format + check --fix converts `except (json.JSONDecodeError, ValidationError):` to broken Python 2 syntax `except json.JSONDecodeError, ValidationError:`
- **Fix:** Split into separate `except` clauses: `except json.JSONDecodeError: pass` / `except ValidationError: pass`
- **Files modified:** claude_cli/parser.py, claude_cli/client.py
- **Verification:** `uv run ruff check claude_cli/` and `uv run python -c "from claude_cli import run"` both pass
- **Committed in:** 1b528ed (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking -- linter compatibility)
**Impact on plan:** Both fixes were required for linter compliance. No scope change. Functionality identical to plan specification.

## Issues Encountered
None beyond the linter compatibility deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- claude_cli package ready for use by Phase 17 (resume tailoring migration) and Phase 18 (cover letter migration)
- All downstream phases can import `from claude_cli import run` and call it with their Pydantic models
- Mock fixtures in tests/claude_cli/conftest.py provide reusable patterns for downstream test suites
- Plan 16-02 can proceed to wire this package into existing resume_ai and webapp code

## Self-Check: PASSED

- All 9 files exist on disk
- Both task commits verified (1b528ed, 424a842)
- 31 tests pass, 563 full suite tests pass

---
*Phase: 16-cli-wrapper-foundation*
*Completed: 2026-02-11*
