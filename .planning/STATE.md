# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** v1.2 Claude CLI Agent Integration -- Phase 16 (CLI Wrapper Foundation)

## Current Position

Phase: 16 of 19 (CLI Wrapper Foundation)
Plan: 1 of 2 in current phase
Status: Executing
Last activity: 2026-02-11 -- Completed 16-01 (claude_cli package)

Progress: [█░░░░░░░░░] 12% (1/8 plans)

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
Stopped at: Completed 16-01-PLAN.md (claude_cli package). Ready for 16-02 (SDK migration).
Resume file: N/A
