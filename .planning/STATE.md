# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** v1.2 Claude CLI Agent Integration

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v1.2
Last activity: 2026-02-11 — Milestone v1.2 started

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

- v1.2: Replace Anthropic SDK with Claude CLI subprocess for AI features (runs on subscription, no API key needed)
- v1.2: CLI wrapper at top-level claude_cli.py (cross-cutting, not resume-specific)
- v1.2: Sync subprocess.run wrapped in asyncio.to_thread (matches existing pattern)
- v1.2: AI scores stored as new columns on jobs table (not separate table)
- v1.2: SSE streaming for resume/cover letter (upgrade from htmx spinner)

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
Stopped at: Milestone v1.2 initialization — requirements and roadmap being defined.
Resume file: N/A
