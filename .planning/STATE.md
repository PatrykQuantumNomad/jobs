# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** v1.2 Claude CLI Agent Integration -- Phase 16 (CLI Wrapper Foundation)

## Current Position

Phase: 16 of 19 (CLI Wrapper Foundation)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-02-11 -- Roadmap created for v1.2 milestone (4 phases, 8 plans, 15 requirements)

Progress: [░░░░░░░░░░] 0% (0/8 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 24 (+ 6 docs/verification)
- Average duration: 4.2 min per plan
- Total execution time: ~126 min

**Velocity (v1.1):**
- Total plans completed: 14
- Total tests written: 428
- Timeline: 1 day (2026-02-08)

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (17 entries across v1.0 + v1.1 + v1.2).

Recent decisions affecting current work:
- v1.2: Replace Anthropic SDK with Claude CLI subprocess for AI features (runs on subscription, no API key needed)
- v1.2: Use asyncio.create_subprocess_exec for CLI calls (not subprocess.run in to_thread) -- enables streaming
- v1.2: AI scores stored as new columns on jobs table (not separate table)
- v1.2: SSE streaming for resume/cover letter follows apply_engine pattern (Queue + background task + EventSourceResponse)
- v1.2: Resilient JSON parser needed for CLI --json-schema regression (handle both structured_output and result fields)

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
Stopped at: Roadmap created for v1.2 milestone. Ready to plan Phase 16.
Resume file: N/A
