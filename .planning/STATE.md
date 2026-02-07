# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-07)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** Phase 2 - Platform Architecture

## Current Position

Phase: 2 of 8 (Platform Architecture)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-02-07 -- Completed 02-01-PLAN.md (Protocol definitions, registry, mixin)

Progress: [####░░░░░░░░░░░░░░░░░░░░░░░░░░] 4/30 (~13%)

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 4.8 min
- Total execution time: 19 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-config-externalization | 3/3 | 16 min | 5.3 min |
| 02-platform-architecture | 1/3 | 3 min | 3.0 min |

**Recent Trend:**
- Last 5 plans: 01-01 (6 min), 01-02 (5 min), 01-03 (5 min), 02-01 (3 min)
- Trend: improving

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8-phase structure derived from 19 requirements at comprehensive depth
- [Roadmap]: pydantic-settings with YAML for config (research recommendation)
- [Roadmap]: Protocol-based platform architecture instead of ABC inheritance
- [Roadmap]: anthropic SDK for AI resume/cover letter (not LangChain -- too heavy for single-prompt use)
- [Roadmap]: One-click apply is capstone (Phase 8) -- requires dashboard, AI, and platform architecture ready
- [01-01]: Backward-compatible Config shim added to avoid breaking 6+ existing consumers during migration
- [01-01]: extra="ignore" on AppSettings root to tolerate unrecognized env vars
- [01-01]: Personal profile fields default to empty strings, populated from .env via build_candidate_profile()
- [01-02]: Weighted scoring formula with default weights reproduces original hardcoded scoring exactly
- [01-02]: Orchestrator loads settings eagerly in __init__, passes derived objects to collaborators
- [01-02]: --platforms CLI default changed from hardcoded list to settings.enabled_platforms()
- [01-03]: Use get_settings().timing shortcut (local var) to avoid repeated singleton lookups
- [01-03]: Import DEBUG_SCREENSHOTS_DIR as module constant in base.py (static path, no need for settings call)
- [01-03]: Use scoring.tech_keywords directly for RemoteOK instead of building full CandidateProfile
- [02-01]: BrowserPlatform.init(context) receives BrowserContext; APIPlatform.init() takes no args
- [02-01]: inspect.signature() validates parameter counts (not types) for protocol compliance
- [02-01]: Registry imports protocols lazily inside decorator to avoid circular dependencies

### Pending Todos

None.

### Blockers/Concerns

- [Research]: ATS form diversity (Greenhouse, Lever, Workday, Ashby) needs phase-level research before Phase 8 planning
- [Research]: Behavioral fingerprinting guardrails need careful implementation in Phase 8 apply engine

## Session Continuity

Last session: 2026-02-07
Stopped at: Completed 02-01-PLAN.md (Protocol definitions, registry, mixin)
Resume file: None
