---
phase: 16-cli-wrapper-foundation
verified: 2026-02-11T16:05:09Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 16: CLI Wrapper Foundation Verification Report

**Phase Goal:** System can invoke Claude CLI as a subprocess with typed structured output, graceful error handling, and no Anthropic SDK runtime dependency

**Verified:** 2026-02-11T16:05:09Z
**Status:** PASSED
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Calling the CLI wrapper with a system prompt, user message, and Pydantic model returns a validated instance of that model | ✓ VERIFIED | `claude_cli.run()` in `claude_cli/client.py` accepts these parameters and returns typed model. Test `test_run_success` validates this. |
| 2 | When Claude CLI is not installed, times out, returns malformed JSON, or fails auth, the wrapper raises a specific typed error with a descriptive message (not a generic subprocess crash) | ✓ VERIFIED | Exception hierarchy in `claude_cli/exceptions.py` covers all error cases: `CLINotFoundError`, `CLITimeoutError`, `CLIMalformedOutputError`, `CLIAuthError`, `CLIProcessError`. Tests verify each path. |
| 3 | The wrapper handles the --json-schema CLI regression (structured_output vs result field) transparently -- caller never sees raw JSON parsing issues | ✓ VERIFIED | `claude_cli/parser.py` implements 6-path resolution: structured_output, result JSON, result markdown, is_error, max retries, empty. Tests cover all paths including regression fallbacks. |
| 4 | The anthropic SDK package is no longer imported at runtime by any production code path | ✓ VERIFIED | `grep -r "import anthropic" resume_ai/ webapp/ orchestrator.py scorer.py config.py models.py` returns zero results. SDK removed from `pyproject.toml` dependencies line 19. |
| 5 | Tests exist for all error paths (timeout, bad JSON, auth failure, CLI missing) using subprocess mocks | ✓ VERIFIED | `tests/claude_cli/test_client.py` has 11 tests covering all error paths. `tests/resume_ai/conftest.py` provides `mock_claude_cli` fixture. Global `_block_cli` fixture prevents accidental real subprocess calls. |
| 6 | resume_ai/tailor.py calls claude_cli.run() instead of anthropic.Anthropic().messages.parse() | ✓ VERIFIED | Line 8: `from claude_cli import run as cli_run`, line 95: `await cli_run(...)`. Function is async. No anthropic imports. |
| 7 | resume_ai/cover_letter.py calls claude_cli.run() instead of anthropic.Anthropic().messages.parse() | ✓ VERIFIED | Line 8: `from claude_cli import run as cli_run`, line 94: `await cli_run(...)`. Function is async. No anthropic imports. |

**Score:** 7/7 truths verified (100%)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `claude_cli/__init__.py` | Public API exports | ✓ VERIFIED | Exports `run()` and all exception classes. 45 lines, substantive. |
| `claude_cli/exceptions.py` | Typed exception hierarchy | ✓ VERIFIED | 6 exception classes with context attributes. 75 lines, substantive. |
| `claude_cli/parser.py` | Resilient JSON parser | ✓ VERIFIED | 6-path resolution algorithm for CLI regression handling. 104 lines, substantive. |
| `claude_cli/client.py` | Async subprocess wrapper | ✓ VERIFIED | `run()` function with timeout, auth detection, cold-start retry. 213 lines, substantive. |
| `resume_ai/tailor.py` | Async resume tailoring via claude_cli.run() | ✓ VERIFIED | Line 95: `await cli_run(...)`. Wraps CLIError in RuntimeError. 148 lines, substantive. |
| `resume_ai/cover_letter.py` | Async cover letter generation via claude_cli.run() | ✓ VERIFIED | Line 94: `await cli_run(...)`. Wraps CLIError in RuntimeError. 130 lines, substantive. |
| `webapp/app.py` | Direct await of async AI functions | ✓ VERIFIED | Line 278: `await tailor_resume(...)`, line 367: `await generate_cover_letter(...)`. No `asyncio.to_thread` wrapper. |
| `pyproject.toml` | Dependencies without anthropic SDK | ✓ VERIFIED | Lines 6-22: dependencies list, anthropic removed. Line 47: claude_cli in packages. Line 94: claude_cli in coverage. |
| `tests/conftest.py` | _block_cli fixture | ✓ VERIFIED | Lines 81-95: `_block_cli` autouse fixture patches `asyncio.create_subprocess_exec`. |
| `tests/resume_ai/conftest.py` | mock_claude_cli fixture | ✓ VERIFIED | Lines 10-86: controller fixture with `set_response()` and `set_error()` methods. |
| `tests/claude_cli/test_client.py` | Comprehensive client tests | ✓ VERIFIED | 11 tests covering success, errors, timeout, auth detection, cold-start retry. |
| `tests/claude_cli/test_parser.py` | Parser regression tests | ✓ VERIFIED | 12 tests covering all 6 resolution paths including CLI regression fallbacks. |
| `tests/resume_ai/test_tailor.py` | Async tests with CLI mocks | ✓ VERIFIED | All tests use `@pytest.mark.asyncio` and `mock_claude_cli` fixture. |
| `tests/resume_ai/test_cover_letter.py` | Async tests with CLI mocks | ✓ VERIFIED | All tests use `@pytest.mark.asyncio` and `mock_claude_cli` fixture. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `resume_ai/tailor.py` | `claude_cli/client.py` | `import and call claude_cli.run()` | ✓ WIRED | Line 8: import, line 95: `await cli_run(...)` with full parameters. |
| `resume_ai/cover_letter.py` | `claude_cli/client.py` | `import and call claude_cli.run()` | ✓ WIRED | Line 8: import, line 94: `await cli_run(...)` with full parameters. |
| `webapp/app.py` | `resume_ai/tailor.py` | `await tailor_resume()` directly (no to_thread) | ✓ WIRED | Line 278: `tailored = await tailor_resume(resume_text=..., job_description=..., job_title=..., company_name=...)` |
| `webapp/app.py` | `resume_ai/cover_letter.py` | `await generate_cover_letter()` directly (no to_thread) | ✓ WIRED | Line 367: `letter = await generate_cover_letter(resume_text=..., job_description=..., job_title=..., company_name=...)` |
| `tests/conftest.py` | `claude_cli` | `_block_cli fixture patches asyncio.create_subprocess_exec` | ✓ WIRED | Line 95: `monkeypatch.setattr("asyncio.create_subprocess_exec", _blocked)` |
| `tests/resume_ai/conftest.py` | `claude_cli.client` | Patches create_subprocess_exec and shutil.which | ✓ WIRED | Lines 79-84: patches both subprocess exec and which for CLI mock control. |

### Requirements Coverage

Based on `.planning/REQUIREMENTS.md` v1.2 requirements:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CLI-01 (invoke CLI with typed output) | ✓ SATISFIED | `claude_cli.run()` implemented and tested. All truths 1, 6, 7 verified. |
| CLI-02 (graceful error handling) | ✓ SATISFIED | Exception hierarchy complete. All error paths tested. Truth 2 verified. |
| CLI-03 (--json-schema regression handling) | ✓ SATISFIED | 6-path parser with fallbacks. Truth 3 verified. |
| CFG-01 (SDK removed from runtime) | ✓ SATISFIED | Zero anthropic imports in production. Removed from dependencies. Truth 4 verified. |

**Coverage:** 4/4 Phase 16 requirements satisfied (100%)

### Anti-Patterns Found

**None detected.** Scanned all modified files for:
- TODO/FIXME/XXX/HACK/PLACEHOLDER comments: None found
- Empty implementations (return null, return {}, return []): None found
- Console.log-only implementations: Not applicable (Python)
- Unwired artifacts: All artifacts imported and used
- Stub patterns: All functions have substantive implementations

### Test Suite Status

```
================ 563 passed, 12 deselected, 5 warnings in 3.76s ================
```

**Test breakdown:**
- Total tests: 563 passed
- claude_cli package tests: 26 tests (test_client: 11, test_parser: 12, test_exceptions: 3)
- resume_ai tests: Updated to async with subprocess mocks
- Smoke tests: CLI guard verified, no-SDK-import verified
- Zero regressions from SDK migration

### Commits Verified

| Task | Commit | Message | Verified |
|------|--------|---------|----------|
| 16-01 (claude_cli package) | 1b528ed | feat(16-01): create claude_cli package with exceptions, parser, and client | ✓ |
| 16-01 (tests) | 424a842 | test(16-01): comprehensive tests for claude_cli package | ✓ |
| 16-02 (SDK migration) | 39de611 | feat(16-02): replace Anthropic SDK with claude_cli in production code | ✓ |
| 16-02 (test migration) | 412e239 | test(16-02): update test infrastructure for Claude CLI subprocess mocks | ✓ |

All 4 commits exist and match summary claims.

### Human Verification Required

None. All success criteria are programmatically verifiable and have been verified.

## Summary

Phase 16 goal **ACHIEVED**. The system can invoke Claude CLI as a subprocess with typed structured output, graceful error handling, and no Anthropic SDK runtime dependency.

**What was built (Plan 16-01):**
- `claude_cli/` package with exceptions, parser, and client modules
- Typed exception hierarchy for all error cases (CLINotFoundError, CLITimeoutError, CLIAuthError, CLIProcessError, CLIMalformedOutputError, CLIResponseError)
- Resilient JSON parser handling --json-schema regression (structured_output vs result field)
- Async subprocess wrapper with timeout, auth detection, and cold-start retry
- Comprehensive test suite with 26 tests covering all success and error paths

**What was wired (Plan 16-02):**
- resume_ai/tailor.py and resume_ai/cover_letter.py converted from synchronous Anthropic SDK to async claude_cli.run()
- webapp/app.py updated to await AI functions directly (no asyncio.to_thread wrapper)
- anthropic SDK removed from pyproject.toml runtime dependencies entirely
- Test infrastructure migrated: _block_cli replaces _block_anthropic, mock_claude_cli replaces mock_anthropic
- All 563 tests pass with zero regressions

**Success criteria verified:**
1. ✓ CLI wrapper returns typed Pydantic models from structured output
2. ✓ All error paths (timeout, bad JSON, auth, CLI missing) raise specific typed errors
3. ✓ --json-schema regression handled transparently via 6-path parser
4. ✓ Zero production files import anthropic SDK
5. ✓ All error paths tested with subprocess mocks

**Ready for:** Phase 17 (AI Scoring), Phase 18 (Resume Tailoring SSE), Phase 19 (Cover Letter SSE)

---

_Verified: 2026-02-11T16:05:09Z_  
_Verifier: Claude (gsd-verifier)_
