# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** v1.2 Claude CLI Agent Integration -- Phase 19 (Cover Letter via CLI + SSE & Cleanup)

## Current Position

Phase: 19 of 19 (Cover Letter via CLI + SSE & Cleanup)
Plan: 2 of 2 in current phase (COMPLETE)
Status: Phase 19 Complete -- v1.2 Milestone Complete
Last activity: 2026-02-11 -- Completed 19-01 (SSE Cover Letter Pipeline)

Progress: [██████████] 100% (8/8 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 24 (+ 6 docs/verification)
- Average duration: 4.2 min per plan
- Total execution time: ~126 min

**Velocity (v1.1):**
- Total plans completed: 14
- Total tests written: 428
- Timeline: 1 day (2026-02-08)

**Velocity (v1.2):**

| Plan | Duration | Tasks | Files | Tests |
|------|----------|-------|-------|-------|
| 16-01 | 8 min | 2 | 9 | 31 |
| 16-02 | 5 min | 2 | 9 | 563 (full suite) |
| 17-01 | 5 min | 2 | 6 | 569 (full suite) |
| 17-02 | 3 min | 2 | 3 | 569 (full suite) |
| 18-01 | 5 min | 2 | 4 | 575 (full suite) |
| 19-01 | 4 min | 2 | 5 | 581 (full suite) |
| 19-02 | 3 min | 1 | 4 | 575 (full suite) |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (17 entries across v1.0 + v1.1 + v1.2).

Recent decisions affecting current work:
- v1.2: Replace Anthropic SDK with Claude CLI subprocess for AI features (runs on subscription, no API key needed)
- v1.2: Use asyncio.create_subprocess_exec for CLI calls (not subprocess.run in to_thread) -- enables streaming
- v1.2: AI scores stored as new columns on jobs table (not separate table)
- v1.2: SSE streaming for resume/cover letter follows apply_engine pattern (Queue + background task + EventSourceResponse)
- v1.2: Resilient JSON parser needed for CLI --json-schema regression (handle both structured_output and result fields)
- 16-01: PEP 695 type parameters required by ruff UP047 on Python 3.14 target
- 16-01: Separate except clauses needed to avoid ruff auto-fix breaking tuple-style multi-exception catches
- 16-02: Wrap CLIError in RuntimeError at resume_ai boundary for webapp backward compatibility
- 16-02: Use CLI model alias "sonnet" instead of full model ID (CLI resolves aliases)
- 16-02: Controller pattern for mock_claude_cli fixture (set_response/set_error methods)
- 17-01: Single-module ai_scorer.py at project root (not a package) -- feature is small enough
- 17-01: mock_claude_cli fixture moved to root conftest for cross-module test availability
- 17-01: Schema version test assertions use SCHEMA_VERSION constant instead of hardcoded integers
- 17-02: Amber-600 button color for AI Analysis to differentiate from other sidebar buttons
- 17-02: Inline persisted score in job_detail.html (no include partial) to avoid extra request on page load
- 18-01: Pre-render resume_diff.html in background task and embed in done event HTML
- 18-01: Patch source modules (resume_ai.*) in tests since _run_resume_tailor uses lazy imports
- 19-01: 3-stage cover letter pipeline (no validation stage unlike 4-stage resume tailor)
- 19-01: Emerald-500 spinner and collapsible text preview in done event
- 19-02: Historical/contextual SDK references in PROJECT.md preserved (requirements/decisions describe transition, not current state)
- 19-02: config.yaml "anthropic" tech keyword preserved (legitimate technology name for job matching)

### Pending Todos

None.

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Fix technical debt: remove Config shim, dead static mount, update arch docs | 2026-02-08 | 9f7f3de | [001-fix-technical-debt](./quick/001-fix-technical-debt/) |
| 002 | Fix CI: increase test coverage from 62.61% to 80%+ (115 new tests) | 2026-02-08 | bf35a16 | [002-fix-ci-increase-test-coverage-from-62-61](./quick/002-fix-ci-increase-test-coverage-from-62-61/) |
| 003 | Fix kanban drag-and-drop destroying board (htmx.ajax swap bug) | 2026-02-08 | 31dc69b | [003-fix-kanban-drag-and-drop-status-switchin](./quick/003-fix-kanban-drag-and-drop-status-switchin/) |

## Session Continuity

Last session: 2026-02-11
Stopped at: Completed 19-01-PLAN.md (SSE Cover Letter Pipeline). Phase 19 complete. v1.2 milestone complete (8/8 plans).
Resume file: N/A
