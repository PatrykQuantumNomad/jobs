---
phase: 19-cover-letter-via-cli-sse-cleanup
plan: 01
subsystem: webapp
tags: [sse, cover-letter, streaming, htmx]
dependency_graph:
  requires: [16-02, 18-01]
  provides: [sse-cover-letter-pipeline]
  affects: [webapp/app.py, job_detail.html]
tech_stack:
  added: []
  patterns: [sse-background-task, asyncio-queue, session-dedup]
key_files:
  created:
    - webapp/templates/partials/cover_letter_status.html
    - webapp/templates/partials/cover_letter_result.html
    - tests/webapp/test_cover_letter_sse.py
  modified:
    - webapp/app.py
    - webapp/templates/job_detail.html
key_decisions:
  - "3-stage pipeline (extracting/generating/rendering) vs 4-stage resume tailor (no validation stage for cover letters)"
  - "Emerald-500 spinner color to match emerald-600 button branding"
  - "Collapsible text preview in done event via format_cover_letter_as_text"
metrics:
  duration: 4 min
  completed: 2026-02-11
---

# Phase 19 Plan 01: SSE Cover Letter Pipeline Summary

SSE-backed cover letter generation with 3-stage progress streaming (extracting, generating, rendering) and emerald-themed UI, replicating Phase 18 resume tailoring pattern.

## What Was Done

### Task 1: SSE cover letter pipeline and endpoints (3ad0d84)

Replaced the synchronous cover letter endpoint with an SSE-backed streaming pipeline following the exact pattern established in Phase 18 for resume tailoring.

**webapp/app.py changes:**
- Added `_cover_sessions` and `_cover_tasks` module-level dicts for session tracking
- Created `_run_cover_letter()` background task with 3 stages: extract resume text, generate cover letter via Claude CLI, render PDF via WeasyPrint (in asyncio.to_thread)
- Replaced blocking `cover_letter_endpoint` with SSE trigger that returns `sse-connect` HTML immediately
- Added `cover_letter_stream` SSE endpoint with session cleanup on disconnect and 15s ping keepalive
- Double-click protection via `_cover_sessions` dedup check returns amber "already in progress" message
- Final result HTML includes download link and collapsible cover letter text preview

**Template changes:**
- Created `cover_letter_status.html` partial with emerald-500 spinner for progress, red alert for errors, raw HTML passthrough for done
- Created `cover_letter_result.html` partial with success banner, download button, and collapsible text preview via `<details>`
- Updated `job_detail.html`: Cover Letter button now uses `hx-disabled-elt="this"` instead of `hx-indicator="#resume-spinner"`, added disabled styling classes
- Removed `#resume-spinner` div entirely -- both AI tool buttons now use SSE for progress

### Task 2: Integration tests (00781cb)

Created 6 integration tests in `tests/webapp/test_cover_letter_sse.py`:
1. `test_cover_letter_returns_sse_connect_html` -- POST returns SSE-connect div
2. `test_cover_letter_404_for_missing_job` -- 404 for nonexistent job
3. `test_cover_letter_already_in_progress` -- Double-click protection
4. `test_stream_404_for_no_session` -- Stream 404 without active session
5. `test_background_task_emits_stage_events` -- 3 progress + done events
6. `test_background_task_emits_error_on_failure` -- Error propagation

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- `uv run ruff check .` -- zero lint errors
- `uv run ruff format --check .` -- 88 files formatted
- `uv run pytest tests/ -x` -- 581 passed (575 original + 6 new), zero regressions
- `_cover_sessions` appears in 5 locations in webapp/app.py
- SSE stream endpoint registered at line 545, catch-all GET at line 811 (correct order)
- `resume-spinner` returns zero matches in .py and .html files

## Self-Check: PASSED

All 5 created/modified files verified on disk. Both commit hashes (3ad0d84, 00781cb) found in git log.
