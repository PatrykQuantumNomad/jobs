# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-07)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** Phase 7 complete. Ready for Phase 8 - One-Click Apply.

## Current Position

Phase: 7 of 8 (AI Resume & Cover Letter) -- COMPLETE
Plan: 4 of 4 in current phase
Status: Phase complete
Last activity: 2026-02-07 -- Completed 07-04-PLAN.md (dashboard integration)

Progress: [#######################░░░░░░░] 23/30 (~77%)

## Performance Metrics

**Velocity:**
- Total plans completed: 23
- Average duration: 4.3 min
- Total execution time: 99 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-config-externalization | 3/3 | 16 min | 5.3 min |
| 02-platform-architecture | 2/2 | 9 min | 4.5 min |
| 03-discovery-engine | 3/3 | 15 min | 5.0 min |
| 04-scheduled-automation | 2/2 | 8 min | 4.0 min |
| 05-dashboard-core | 4/4 | 12 min | 3.0 min |
| 06-dashboard-analytics | 2/2 | 8 min | 4.0 min |
| 07-ai-resume-cover-letter | 4/4 | 22 min | 5.5 min |

**Recent Trend:**
- Last 5 plans: 07-01 (4 min), 07-02 (6 min), 07-03 (4 min), 07-04 (8 min)
- Trend: stable

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
- [02-02]: Big-bang migration -- all three adapters migrated together for atomic consistency
- [02-02]: RemoteOK async-to-sync conversion eliminates asyncio from orchestrator entirely
- [02-02]: No --platforms choices constraint -- registry validates at runtime via KeyError
- [03-01]: ScoreBreakdown uses stdlib dataclass (not Pydantic) -- lightweight internal struct
- [03-01]: Added " corporation" to dedup suffix list for Microsoft Corporation variant
- [03-01]: tech_matched keywords included in ScoreBreakdown (Claude's discretion from CONTEXT.md)
- [03-01]: Currency display: USD="$", CAD="C$", EUR="EUR", GBP="GBP" in compact format
- [03-02]: JOBFLOW_TEST_DB=1 env var for in-memory SQLite testing
- [03-02]: Singleton connection for in-memory DBs to share state across get_conn() calls
- [03-02]: ON CONFLICT preserves first_seen_at, updates last_seen_at
- [03-02]: Removed old _deduplicate entirely -- fuzzy_deduplicate is sole dedup path
- [03-02]: backfill_score_breakdowns filters dict keys through Job.model_fields
- [03-03]: parse_json filter returns {} on None/empty/invalid JSON for safe template rendering
- [03-03]: NEW badge in Score column (not separate column) to keep table compact
- [03-03]: No salary placeholder for missing data -- blank cell, not "N/A" or dash
- [03-03]: Tech keywords shown only on detail page, not dashboard cards, to avoid clutter
- [04-01]: getattr(self, '_unattended', False) for backward-compatible unattended checks
- [04-01]: sys.executable resolved to absolute path for venv Python in plist
- [04-01]: launchctl bootstrap/bootout (modern API) instead of deprecated load/unload
- [04-02]: Error tracking via self._run_errors list populated in _login_platform and _search_platform
- [04-02]: try/finally wraps entire pipeline so crashes still produce a run_history entry
- [04-02]: record_run protected by its own try/except to avoid masking pipeline errors
- [05-01]: FTS5 content-sync table with triggers (not standalone) to avoid double-storage
- [05-01]: Activity log uses dedup_key foreign reference (not JOIN-enforced) for simplicity
- [05-01]: Status migration: approved -> saved, skipped -> withdrawn (semantic alignment)
- [05-02]: FTS5 prefix matching: auto-append * to each word when no FTS5 operators detected
- [05-02]: Partial template for table rows enables reuse by search, bulk actions (05-03), and filtering (05-04)
- [05-02]: hx-include captures active filter state so search respects score/platform/status filters
- [05-03]: Log "discovered" activity in upsert_job() for new jobs (not just migration backfill)
- [05-03]: Human-readable status labels via Jinja2 replace/title filters (no server-side mapping dict)
- [05-03]: Activity timeline placed between Notes and Metadata in sidebar
- [05-04]: Annotated[list[str], Form()] for repeated form fields (FastAPI multi-checkbox pattern)
- [05-04]: hx-include merges #bulk-form checkboxes with filter selects outside the form
- [05-04]: Export links use Jinja2 urlencode filter to preserve active filter state in URL params
- [05-04]: bulk_status dropdown in bulk-bar div outside the form, included via hx-include selector
- [06-01]: Inline JSON pattern for chart data (no extra API round-trip on initial load)
- [06-01]: Chart.js CDN loaded synchronously before initialization script
- [06-01]: createOrUpdateChart() helper with Chart.getChart() destroy guard for safe refresh
- [06-01]: Replaced placeholder /stats endpoint with proper /analytics and /api/analytics
- [06-01]: stats_cards.html partial reusable by analytics and future kanban page
- [06-02]: SortableJS 1.15.6 via CDN with forceFallback:true for consistent cross-browser drag behavior
- [06-02]: Optimistic column count updates with DOM rollback on POST failure
- [06-02]: KANBAN_STATUSES excludes discovered and scored (user-managed pipeline only)
- [06-02]: HX-Trigger: statsChanged from POST /jobs/{key}/status triggers stats refresh
- [06-02]: Jinja2 namespace() pattern for cross-loop variable mutation in empty state check
- [07-01]: Field(description=...) on every Pydantic model field for LLM structured output guidance
- [07-01]: WorkExperience.achievements reorder-only constraint documented in Field description
- [07-01]: resume_versions table uses job_dedup_key FK to jobs table for referential integrity
- [07-01]: get_all_versions() LEFT JOINs jobs table to enrich with title/company metadata
- [07-02]: Temperature=0 for resume tailoring (max factual accuracy), 0.3 for cover letter (natural writing)
- [07-02]: Stop-word filtering in entity extraction to prevent false positives from sentence-start capitalization
- [07-02]: Validator works on plain text strings (not Pydantic models) for flexibility across resume and cover letter
- [07-02]: Conservative company detection with stop-word filter to minimize false positives
- [07-02]: Known tech keywords set (~100 terms) for skill extraction covers project domain
- [07-03]: Standalone HTML templates (not extending base.html) since WeasyPrint renders to PDF, not browser
- [07-03]: Lazy Jinja2 Environment initialization via module-level _env pattern for efficiency
- [07-03]: TYPE_CHECKING guard for model imports to avoid circular dependencies
- [07-03]: Calibri with Carlito fallback for ATS compatibility (Carlito is the open-source metric-equivalent)
- [07-03]: Context-mode diff with 3 surrounding lines for focused comparison without noise
- [07-04]: Lazy imports for resume_ai modules to avoid startup failure when AI deps not installed
- [07-04]: AI endpoints registered before catch-all /jobs/{path} GET route (FastAPI path ordering)
- [07-04]: asyncio.to_thread for all LLM calls (non-blocking event loop)
- [07-04]: Post-generation validate_no_fabrication() runs before returning diff view

### Pending Todos

None.

### Blockers/Concerns

- [Research]: ATS form diversity (Greenhouse, Lever, Workday, Ashby) needs phase-level research before Phase 8 planning
- [Research]: Behavioral fingerprinting guardrails need careful implementation in Phase 8 apply engine

## Session Continuity

Last session: 2026-02-07
Stopped at: Phase 7 COMPLETE. All 4 plans executed. Ready for Phase 8 planning.
Resume file: .planning/ROADMAP.md (Phase 8: One-Click Apply)
