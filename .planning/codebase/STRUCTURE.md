# Codebase Structure

**Analysis Date:** 2026-02-07

## Directory Layout

```
/Users/patrykattc/work/jobs/
├── .claude/                        # GSD framework + project instructions
│   ├── agents/                     # Agent definitions (gsd-*, job-scorer, etc.)
│   ├── commands/gsd/               # GSD command implementations
│   ├── get-shit-done/              # GSD framework core
│   ├── hooks/                      # Git hooks
│   └── CLAUDE.md                   # Project-specific instructions
├── .planning/                      # GSD planning artifacts
│   ├── codebase/                   # Codebase documentation (ARCHITECTURE.md, etc.)
│   ├── milestones/                 # Milestone tracking
│   ├── phases/                     # Phase-by-phase implementation plans
│   └── research/                   # Research notes
├── platforms/                      # Job board platform adapters
│   ├── __init__.py                 # Auto-discovery + registry exports
│   ├── protocols.py                # BrowserPlatform/APIPlatform Protocol definitions
│   ├── registry.py                 # @register_platform decorator + validation
│   ├── mixins.py                   # BrowserPlatformMixin (shared helpers)
│   ├── stealth.py                  # Playwright stealth configuration
│   ├── indeed.py                   # Indeed adapter (366 lines)
│   ├── indeed_selectors.py         # Indeed DOM selectors
│   ├── dice.py                     # Dice adapter
│   ├── dice_selectors.py           # Dice DOM selectors
│   └── remoteok.py                 # RemoteOK API adapter
├── webapp/                         # FastAPI web dashboard
│   ├── app.py                      # Routes + endpoints (655 lines)
│   ├── db.py                       # SQLite database layer
│   ├── static/                     # CSS, JS, images
│   └── templates/                  # Jinja2 templates + htmx partials
├── apply_engine/                   # One-click apply orchestration
│   ├── engine.py                   # Background thread + SSE event emission (549 lines)
│   ├── events.py                   # ApplyEvent Pydantic models
│   ├── config.py                   # ApplyMode enum + ApplyConfig
│   └── dedup.py                    # Already-applied deduplication
├── resume_ai/                      # LLM-powered resume tailoring
│   ├── tailor.py                   # Resume tailoring via Anthropic structured outputs
│   ├── cover_letter.py             # Cover letter generation
│   ├── extractor.py                # PDF → text extraction
│   ├── diff.py                     # Unified diff HTML generation
│   ├── renderer.py                 # PDF rendering (reportlab)
│   ├── validator.py                # Anti-fabrication validation
│   ├── tracker.py                  # Resume version tracking (SQLite)
│   └── models.py                   # TailoredResume, CoverLetter Pydantic models
├── browser_sessions/               # Playwright persistent contexts (gitignored)
├── debug_screenshots/              # Error screenshots (gitignored)
├── job_pipeline/                   # Pipeline output (gitignored)
│   ├── jobs.db                     # SQLite database
│   ├── raw_{platform}.json         # Raw search results per platform
│   ├── discovered_jobs.json        # Scored + deduplicated jobs (score >= 3)
│   ├── tracker.md                  # Markdown summary table
│   └── descriptions/               # Full job descriptions as markdown
├── resumes/                        # Resume PDFs
│   ├── Patryk_Golabek_Resume_ATS.pdf
│   ├── Patryk_Golabek_Resume.pdf
│   └── tailored/                   # LLM-generated tailored resumes
├── orchestrator.py                 # Main pipeline orchestrator (568 lines)
├── scorer.py                       # Job scoring engine (225 lines)
├── config.py                       # Settings (YAML + .env) (411 lines)
├── models.py                       # Pydantic domain models (124 lines)
├── dedup.py                        # Fuzzy deduplication logic
├── salary.py                       # Salary normalization
├── form_filler.py                  # Generic form-filling logic
├── scheduler.py                    # APScheduler daemon
├── config.yaml                     # Operational configuration (search queries, scoring weights)
├── .env                            # Credentials + personal profile (gitignored)
├── requirements.txt                # Python dependencies
└── README.md                       # Usage documentation
```

## Directory Purposes

**platforms/**
- Purpose: Pluggable adapters for job boards (Indeed, Dice, RemoteOK)
- Contains: Protocol definitions, registry, platform implementations, DOM selectors
- Key files: `protocols.py` (contracts), `registry.py` (decorator), `indeed.py` (366 lines)

**webapp/**
- Purpose: Web dashboard for job tracking, apply automation, resume tailoring
- Contains: FastAPI routes, SQLite database layer, Jinja2 templates, htmx partials
- Key files: `app.py` (655 lines, all routes), `db.py` (SQLite CRUD)

**apply_engine/**
- Purpose: Background apply orchestration with SSE progress streaming
- Contains: Thread-based executor, event emission, confirmation gates
- Key files: `engine.py` (549 lines, core orchestration)

**resume_ai/**
- Purpose: LLM-powered resume/cover letter generation with anti-fabrication
- Contains: Anthropic API calls, PDF rendering, diff generation, version tracking
- Key files: `tailor.py` (LLM prompt), `renderer.py` (reportlab)

**.planning/**
- Purpose: GSD framework planning artifacts (not runtime code)
- Contains: Milestones, phases, research notes, codebase documentation
- Key files: `MILESTONES.md`, `ROADMAP.md`, `STATE.md`, `codebase/*.md`

**browser_sessions/**
- Purpose: Persistent Playwright contexts for session caching
- Contains: Chromium user data directories (per platform)
- Generated: Yes (by Playwright)
- Committed: No (gitignored)

**job_pipeline/**
- Purpose: Pipeline output (JSON, SQLite, markdown)
- Contains: Raw results, scored jobs, SQLite database, descriptions
- Generated: Yes (by orchestrator)
- Committed: No (gitignored)

**resumes/**
- Purpose: Resume PDFs (original + LLM-generated tailored versions)
- Contains: ATS resume, standard resume, tailored/ subdirectory
- Generated: tailored/ only (by resume_ai)
- Committed: Original resumes yes, tailored/ no (gitignored)

## Key File Locations

**Entry Points:**
- `orchestrator.py`: CLI pipeline (`python orchestrator.py`)
- `webapp/app.py`: Web dashboard (`python -m webapp.app`)
- `scheduler.py`: Cron daemon (`python scheduler.py`)

**Configuration:**
- `config.yaml`: Operational params (search queries, scoring weights, platform toggles, timing)
- `.env`: Credentials (INDEED_EMAIL, DICE_EMAIL, DICE_PASSWORD) + personal profile fields
- `config.py`: Settings loader (Pydantic settings with YAML + .env sources)

**Core Logic:**
- `orchestrator.py`: Five-phase pipeline coordination (setup → login → search → score → apply)
- `scorer.py`: Job scoring (1-5) with explainable breakdowns
- `platforms/registry.py`: Platform registration + Protocol validation
- `apply_engine/engine.py`: Background apply orchestration + SSE streaming
- `resume_ai/tailor.py`: LLM resume tailoring

**Testing:**
- Not detected (no test files found)

## Naming Conventions

**Files:**
- Snake_case for Python modules: `orchestrator.py`, `form_filler.py`
- Platform selectors: `{platform}_selectors.py` (e.g., `indeed_selectors.py`)
- Uppercase for documentation: `ARCHITECTURE.md`, `CONVENTIONS.md`

**Directories:**
- Lowercase with underscores: `apply_engine/`, `resume_ai/`, `job_pipeline/`
- Hidden directories with dot prefix: `.claude/`, `.planning/`

**Classes:**
- PascalCase: `Orchestrator`, `JobScorer`, `IndeedPlatform`, `ApplyEngine`
- Platform classes: `{Platform}Platform` (e.g., `IndeedPlatform`)
- Protocol suffix: `BrowserPlatform`, `APIPlatform`

**Functions:**
- Snake_case: `get_settings()`, `ensure_directories()`, `tailor_resume()`
- Private helpers with underscore prefix: `_validate_against_protocol()`, `_apply_sync()`

**Variables:**
- Snake_case: `discovered_jobs`, `dedup_key`, `resume_text`
- Constants: UPPERCASE_WITH_UNDERSCORES in module scope (e.g., `PROJECT_ROOT`, `DEFAULT_MODEL`)

## Where to Add New Code

**New Platform Adapter:**
- Implementation: `platforms/{platform}.py`
- Selectors (if browser): `platforms/{platform}_selectors.py`
- Tests: Not yet established (create `tests/platforms/test_{platform}.py`)
- Registration: Add `@register_platform("{platform}", ...)` decorator to class

**New Scoring Factor:**
- Primary code: `scorer.py` (add method to JobScorer, update ScoreBreakdown dataclass)
- Configuration: `config.yaml` (add weight to `scoring.weights` section)
- Tests: Not yet established

**New Dashboard Route:**
- Implementation: `webapp/app.py` (add FastAPI route function)
- Template: `webapp/templates/{name}.html` or `webapp/templates/partials/{name}.html`
- Database: `webapp/db.py` (add query function if new data access needed)

**New Resume AI Feature:**
- Primary code: `resume_ai/{feature}.py`
- Models: `resume_ai/models.py` (add Pydantic model for structured LLM output)
- Integration: `webapp/app.py` (add POST endpoint), `webapp/templates/partials/` (add htmx partial)

**New Apply Engine Mode:**
- Configuration: `apply_engine/config.py` (add ApplyMode enum member)
- Implementation: `apply_engine/engine.py` (add conditional logic in `_apply_sync()`)
- UI: `webapp/templates/job_detail.html` (add mode selection dropdown)

**Utilities:**
- Shared helpers: Add to appropriate module (`config.py`, `models.py`) or create new module in root
- Platform-specific helpers: `platforms/mixins.py` (BrowserPlatformMixin)

## Special Directories

**.claude/**
- Purpose: GSD framework + project instructions
- Generated: No (checked into git)
- Committed: Yes

**.planning/**
- Purpose: GSD planning artifacts (milestones, phases, research)
- Generated: Yes (by GSD commands)
- Committed: Yes

**browser_sessions/**
- Purpose: Playwright persistent contexts (session caching)
- Generated: Yes (by Playwright launch_persistent_context)
- Committed: No (gitignored)

**debug_screenshots/**
- Purpose: Error screenshots for debugging failed selectors
- Generated: Yes (by platform adapters on error)
- Committed: No (gitignored)

**job_pipeline/**
- Purpose: Pipeline output (JSON, SQLite, markdown)
- Generated: Yes (by orchestrator phases)
- Committed: No (gitignored)

**resumes/tailored/**
- Purpose: LLM-generated tailored resumes per job
- Generated: Yes (by resume_ai endpoints)
- Committed: No (gitignored)

**.venv/**
- Purpose: Python virtual environment
- Generated: Yes (by venv/virtualenv)
- Committed: No (gitignored)

**.ruff_cache/**
- Purpose: Ruff linter cache
- Generated: Yes (by ruff)
- Committed: No (gitignored)

---

*Structure analysis: 2026-02-07*
