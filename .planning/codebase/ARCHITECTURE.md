# Architecture

**Analysis Date:** 2026-02-07

## Pattern Overview

**Overall:** Pluggable adapter pipeline with event-driven orchestration

**Key Characteristics:**
- Five-phase orchestrated pipeline (setup → login → search → score → apply)
- Protocol-based platform adapters registered via decorator at import time
- Dual-track execution: synchronous Playwright automation with async web dashboard
- Event-driven apply engine bridging sync thread to async SSE streams
- LLM-powered resume tailoring integrated into web UI

## Layers

**Orchestration Layer:**
- Purpose: Coordinates end-to-end pipeline execution across platforms
- Location: `orchestrator.py`
- Contains: Phase sequencing, platform dispatch, result aggregation, human-in-the-loop prompts
- Depends on: platforms registry, scorer, config, webapp.db
- Used by: CLI entry point (`main()`), scheduler

**Platform Adapter Layer:**
- Purpose: Abstracts job board specifics behind uniform Protocol interfaces
- Location: `platforms/`
- Contains: BrowserPlatform and APIPlatform implementations (Indeed, Dice, RemoteOK)
- Depends on: models (Job, SearchQuery), config (credentials, timing)
- Used by: orchestrator (via registry lookup)

**Scoring Layer:**
- Purpose: Rates jobs 1-5 against candidate profile with explainable breakdowns
- Location: `scorer.py`
- Contains: Multi-factor scoring (title, tech, remote, salary) with configurable weights
- Depends on: models (Job, CandidateProfile), config (ScoringWeights)
- Used by: orchestrator phase 3, webapp.db (backfill operation)

**Web Dashboard Layer:**
- Purpose: Provides human-facing UI for job tracking and apply automation
- Location: `webapp/app.py`, `webapp/db.py`
- Contains: FastAPI routes, htmx partials, SQLite persistence, SSE endpoints
- Depends on: apply_engine, resume_ai, models
- Used by: Human operator via browser

**Apply Engine Layer:**
- Purpose: Orchestrates multi-step apply flows with real-time progress streaming
- Location: `apply_engine/engine.py`
- Contains: Background thread executor, SSE event emission, human-confirmation gates
- Depends on: platforms registry, form_filler, dedup logic
- Used by: webapp (POST /jobs/{key}/apply endpoints)

**Resume AI Layer:**
- Purpose: LLM-powered resume tailoring and cover letter generation
- Location: `resume_ai/`
- Contains: Anthropic structured outputs, PDF rendering, anti-fabrication validation
- Depends on: anthropic SDK, pypdf, reportlab
- Used by: webapp (POST /jobs/{key}/tailor-resume)

**Configuration Layer:**
- Purpose: Loads operational params (YAML) and secrets (.env) with validation
- Location: `config.py`
- Contains: Pydantic settings models, platform credential validation, directory constants
- Depends on: pydantic-settings, models
- Used by: All layers (orchestrator, platforms, scorer, webapp)

**Data Models Layer:**
- Purpose: Domain models with validation and serialization
- Location: `models.py`
- Contains: Job, SearchQuery, CandidateProfile, JobStatus enum
- Depends on: Pydantic v2
- Used by: All layers

## Data Flow

**Discovery Flow (CLI):**

1. User runs `python orchestrator.py --platforms indeed remoteok`
2. Orchestrator.phase_0_setup validates credentials, creates directories
3. Orchestrator.phase_1_login: registry.get_platform("indeed") → IndeedPlatform instance → login() → session cached in `browser_sessions/indeed/`
4. Orchestrator.phase_2_search: platform.search(query) → list[Job] → saved to `job_pipeline/raw_indeed.json`
5. Orchestrator.phase_3_score: dedup.fuzzy_deduplicate(all_jobs) → scorer.score_batch_with_breakdown() → webapp.db.upsert_job() → `job_pipeline/discovered_jobs.json` + `jobs.db`
6. Orchestrator.phase_4_apply: filter score >= 4 → human approval prompt → platform.apply(job, resume_path)

**Dashboard Flow (Web):**

1. User visits `http://127.0.0.1:8000`
2. GET / → webapp.db.get_jobs() → SELECT from SQLite → Jinja2 template → HTML + htmx
3. User clicks "Apply" → POST /jobs/{key}/apply → ApplyEngine.apply() starts background thread
4. Background thread: Playwright opens browser → fills form → emits ApplyEvent("FORM_FILLED") → queue.put()
5. SSE stream: GET /jobs/{key}/apply/stream → event_generator yields HTML partials → htmx swaps into DOM
6. User clicks "Confirm" → POST /jobs/{key}/apply/confirm → threading.Event.set() → background thread resumes → submit button clicked

**Resume Tailoring Flow:**

1. User clicks "Tailor Resume" on job detail page
2. POST /jobs/{key}/tailor-resume → resume_ai.extractor.extract_resume_text(pdf_path)
3. LLM call: tailor_resume(resume_text, job_description) → TailoredResume (Pydantic model from Anthropic structured outputs)
4. resume_ai.diff.generate_resume_diff_html() → unified diff with HTML formatting
5. resume_ai.renderer.render_resume_pdf() → reportlab generates PDF → `resumes/tailored/{company}_{date}.pdf`
6. resume_ai.tracker.save_resume_version() → INSERT into resume_versions table
7. Partial response: `partials/resume_diff.html` → htmx swaps into #resume-output

**State Management:**
- Pipeline state: Transient in Orchestrator instance (discovered_jobs list)
- Job persistence: SQLite (`job_pipeline/jobs.db`) + JSON snapshots
- Browser sessions: Playwright persistent contexts in `browser_sessions/{platform}/`
- Apply sessions: In-memory dict `ApplyEngine._sessions` keyed by dedup_key
- Configuration: Lazy singleton `get_settings()` caches AppSettings instance

## Key Abstractions

**Platform Protocol:**
- Purpose: Contract for pluggable job board adapters
- Examples: `platforms/protocols.py` (BrowserPlatform, APIPlatform)
- Pattern: runtime_checkable Protocol with init/login/search/get_job_details/apply methods

**Registry Decorator:**
- Purpose: Auto-discovery and fail-fast validation of platform implementations
- Examples: `@register_platform("indeed", platform_type="browser", capabilities=["easy_apply"])`
- Pattern: Decorator validates class against Protocol at import time, stores in `_REGISTRY` dict

**Job Model:**
- Purpose: Normalized job listing across platforms
- Examples: `models.py` Job (id, platform, title, company, salary_min/max, score, status)
- Pattern: Pydantic v2 BaseModel with field validators and custom serialization

**ScoreBreakdown:**
- Purpose: Explainable scoring with per-factor attribution
- Examples: `scorer.py` ScoreBreakdown dataclass (title_points, tech_points, tech_matched list)
- Pattern: Dataclass with to_dict() for SQLite JSON storage, display methods for UI

**ApplyEvent:**
- Purpose: Typed progress events for SSE streaming
- Examples: `apply_engine/events.py` ApplyEvent (type: ApplyEventType enum, message, metadata)
- Pattern: Pydantic model serialized to dict for SSE data field

## Entry Points

**CLI Pipeline:**
- Location: `orchestrator.py` main()
- Triggers: `python orchestrator.py [--platforms X Y] [--headed] [--scheduled]`
- Responsibilities: Argparse setup, Orchestrator instantiation, run() invocation

**Web Dashboard:**
- Location: `webapp/app.py` main()
- Triggers: `python -m webapp.app` or `uvicorn webapp.app:app`
- Responsibilities: FastAPI app startup, route registration, template loading

**Scheduler (Cron):**
- Location: `scheduler.py` main()
- Triggers: `python scheduler.py` (runs as daemon)
- Responsibilities: APScheduler setup, daily job at config.schedule.hour:minute

**Platform Auto-Discovery:**
- Location: `platforms/__init__.py` _auto_discover()
- Triggers: Import of platforms module
- Responsibilities: pkgutil.iter_modules → importlib.import_module → @register_platform executes

## Error Handling

**Strategy:** Fail-fast for configuration errors, graceful degradation for runtime errors

**Patterns:**
- Config validation: Pydantic ValidationError at settings load → sys.exit(1)
- Platform login failure: Add to `_failed_logins` set → skip platform for run → log to `_run_errors`
- Search query error: Catch exception per query → continue to next query → append to `_run_errors`
- Apply flow error: Emit ApplyEvent(type=ERROR) → display in UI → do not mark as applied
- Resume tailoring error: Catch exception → return HTML error partial → do not save version
- Screenshot on failure: Save to `debug_screenshots/{platform}_{timestamp}.png` for post-mortem

## Cross-Cutting Concerns

**Logging:** Python logging module (logger = logging.getLogger(__name__)), console output via print() for user-facing messages

**Validation:** Pydantic v2 field validators (e.g., salary_max >= salary_min), @field_validator decorators, Protocol validation at registration time

**Authentication:** Platform-specific (Indeed: Google OAuth session cache, Dice: email+password form, RemoteOK: public API no auth)

---

*Architecture analysis: 2026-02-07*
