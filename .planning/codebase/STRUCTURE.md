# Codebase Structure

**Analysis Date:** 2026-02-07

## Directory Layout

```
/Users/patrykattc/work/jobs/
├── orchestrator.py           # Entry point — coordinates all five phases
├── scorer.py                 # Job scoring engine (1-5 rating)
├── models.py                 # Pydantic v2 data models (Job, SearchQuery, CandidateProfile)
├── config.py                 # Environment loading, platform config, search queries
├── form_filler.py            # Generic form-filling heuristics
│
├── platforms/                # Platform-specific implementations
│   ├── __init__.py
│   ├── base.py               # Abstract BasePlatform class (login, search, apply interface)
│   ├── stealth.py            # Playwright stealth config and context factory
│   │
│   ├── indeed.py             # Indeed.com automation (Playwright + stealth)
│   ├── indeed_selectors.py   # Indeed CSS selectors and URL templates
│   │
│   ├── dice.py               # Dice.com automation (Playwright)
│   ├── dice_selectors.py     # Dice CSS selectors and URL templates
│   │
│   └── remoteok.py           # RemoteOK API client (async HTTP, no browser)
│
├── webapp/                   # Web dashboard for job tracking
│   ├── __init__.py
│   ├── app.py                # FastAPI app with routes
│   ├── db.py                 # SQLite layer (schema, queries)
│   ├── templates/            # Jinja2 HTML templates
│   │   └── dashboard.html    # Main job tracker UI
│   └── static/               # CSS, JS assets
│
├── job_pipeline/             # Pipeline output directory (created at runtime)
│   ├── raw_indeed.json       # Raw jobs from Indeed (600+ jobs)
│   ├── raw_dice.json         # Raw jobs from Dice
│   ├── raw_remoteok.json     # Raw jobs from RemoteOK
│   ├── discovered_jobs.json  # Deduplicated and scored (score 3+)
│   ├── tracker.md            # Markdown summary table
│   ├── jobs.db               # SQLite database (web dashboard)
│   └── descriptions/         # Individual job markdown files
│       └── {company}_{title}.md
│
├── browser_sessions/         # Persistent Playwright contexts (gitignored)
│   ├── indeed/               # Indeed session directory
│   │   └── Default/          # Playwright profile with cached cookies/auth
│   └── dice/                 # Dice session directory
│       └── Default/
│
├── debug_screenshots/        # Error/debug screenshots (created on failure)
│   └── {platform}_{context}_{timestamp}.png
│
├── resumes/                  # Resume files
│   ├── Patryk_Golabek_Resume_ATS.pdf       # ATS-optimized (default)
│   ├── Patryk_Golabek_Resume.pdf           # Standard version
│   └── tailored/             # Company-specific tailored versions
│       └── Patryk_Golabek_Resume_{CompanyName}.pdf
│
├── .env                      # Credentials (gitignored, never committed)
├── requirements.txt          # Python dependencies
└── README.md                 # Usage instructions
```

## Directory Purposes

**platforms/:**
- Purpose: Platform-specific automation modules
- Contains: Scrapers for Indeed, Dice, RemoteOK; stealth utilities; selector definitions
- Key files: `base.py` (interface), `stealth.py` (context factory), `{platform}.py` (implementation), `{platform}_selectors.py` (CSS selectors)

**webapp/:**
- Purpose: FastAPI web dashboard for post-pipeline job management
- Contains: Server routes, database layer, Jinja2 templates, static assets
- Key files: `app.py` (routes), `db.py` (SQLite schema/queries), `templates/dashboard.html` (UI)

**job_pipeline/:**
- Purpose: Pipeline execution outputs (auto-created)
- Contains: Raw JSON per-platform, deduplicated/scored JSON, tracker markdown, individual job descriptions, SQLite database
- Key files: `raw_{platform}.json` (input for phase 3), `discovered_jobs.json` (output for phase 4), `tracker.md` (human-readable summary)

**browser_sessions/:**
- Purpose: Persistent Playwright browser profiles (gitignored)
- Contains: Cached cookies, local storage, IndexedDB (authentication)
- Key files: `{platform}/Default/` (Chromium user data directory)

**debug_screenshots/:**
- Purpose: Screenshots for error debugging
- Contains: PNG images captured on selector timeouts, login failures, unexpected page states
- Naming: `{platform}_{context}_{YYYYMMDD_HHMMSS}.png`

**resumes/:**
- Purpose: Resume files for application uploads
- Contains: ATS-optimized version (default), standard version, per-company tailored PDFs
- Key files: `*_Resume_ATS.pdf` (default for all applications), `tailored/` (customized per company)

## Key File Locations

**Entry Points:**
- `orchestrator.py`: Main pipeline execution (`python orchestrator.py`)
- `webapp/app.py`: Web dashboard (`python -m webapp.app`)

**Configuration:**
- `config.py`: Environment variables, directory paths, timing, search queries
- `.env`: Credentials (INDEED_EMAIL, DICE_EMAIL, DICE_PASSWORD) — never read directly

**Core Logic:**
- `models.py`: Pydantic schemas for Job, SearchQuery, CandidateProfile
- `scorer.py`: `JobScorer` class for 1-5 rating
- `form_filler.py`: Generic form filling with keyword-based field identification
- `platforms/base.py`: Abstract `BasePlatform` interface

**Platform-Specific:**
- `platforms/indeed.py`: Indeed search, login, detail fetching, apply
- `platforms/indeed_selectors.py`: CSS selectors, URL templates for Indeed
- `platforms/dice.py`: Dice search, login, detail fetching, apply
- `platforms/dice_selectors.py`: CSS selectors, URL templates for Dice
- `platforms/remoteok.py`: RemoteOK API client (async HTTP)

**Browser Automation:**
- `platforms/stealth.py`: `get_browser_context()` factory, stealth patches, context cleanup

**Web Dashboard:**
- `webapp/app.py`: FastAPI routes, query string filters, status updates
- `webapp/db.py`: SQLite schema, insert/update/query methods

**Pipeline Outputs:**
- `job_pipeline/raw_{indeed,dice,remoteok}.json`: Raw results before scoring
- `job_pipeline/discovered_jobs.json`: Final scored results (score 3+)
- `job_pipeline/tracker.md`: Markdown summary table for human review
- `job_pipeline/descriptions/{company}_{title}.md`: Individual job markdown files

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `form_filler.py`, `indeed_selectors.py`)
- Selectors: `{platform}_selectors.py` (e.g., `indeed_selectors.py`, `dice_selectors.py`)
- Platform implementations: `{platform}.py` (e.g., `indeed.py`, `dice.py`, `remoteok.py`)
- Pipeline outputs: `{type}_{platform}.json` (e.g., `raw_indeed.json`, `raw_dice.json`)
- Job descriptions: `{company}_{title}.md` (sanitized, max 60 chars)
- Screenshots: `{platform}_{context}_{timestamp}.png` (e.g., `indeed_login_failed_20260207_143022.png`)

**Directories:**
- Platform-specific: `platforms/{platform}/` (not used currently; platform modules are flat)
- Outputs: `{output_type}_{platform}/` or `{output_type}/` (e.g., `job_pipeline/descriptions/`)
- Sessions: `browser_sessions/{platform}/` (e.g., `browser_sessions/indeed/`)
- Tailored content: `{type}/tailored/` (e.g., `resumes/tailored/`)

**Classes:**
- Platforms: `{PlatformName}Platform` (e.g., `IndeedPlatform`, `DicePlatform`, `RemoteOKPlatform`)
- Services: `{Service}` (e.g., `JobScorer`, `FormFiller`)
- Models: `{Entity}` (e.g., `Job`, `SearchQuery`, `CandidateProfile`)
- Enums: `{Entity}Status` (e.g., `JobStatus`)

**Functions:**
- Phase methods: `phase_{N}_{description}()` (e.g., `phase_0_setup()`, `phase_3_score()`)
- Private/internal: `_description()` (leading underscore)
- Utility: Concise, descriptive (e.g., `get_browser_context()`, `close_browser()`, `element_exists()`)

## Where to Add New Code

**New Platform (e.g., LinkedIn, GitHub Jobs):**
- Create: `platforms/{platform}.py` (inherit from `BasePlatform`)
- Create: `platforms/{platform}_selectors.py` (selectors and URL templates)
- Implement: `login()`, `search()`, `get_job_details()`, `apply()` methods
- Register in: `orchestrator.py` phase methods (phase_1_login, phase_2_search, phase_4_apply)
- Update: `config.py` to add platform credentials validation

**New Scoring Factor:**
- Edit: `scorer.py` `JobScorer` class
- Add: New `_factor_score()` method returning 0-2 points
- Update: `score_job()` raw points calculation
- Adjust: Mapping from 6-point scale to 1-5 scale if needed

**New Form Field:**
- Edit: `form_filler.py` `_FIELD_KEYWORDS` dictionary
- Add: New field key → keyword list entry
- Update: `_value_for()` method to include mapping from `CandidateProfile`

**New Dashboard Feature:**
- Routes: Add `@app.get()` or `@app.post()` in `webapp/app.py`
- Database: Add query method to `webapp/db.py`
- Template: Create/edit template in `webapp/templates/`

**New Search Query:**
- Edit: `config.py` `Config.DEFAULT_SEARCH_QUERIES` list
- Format: Quoted string (e.g., `"Principal Engineer" Kubernetes remote`)
- Scope: Each platform processes independently; remote filtering is handled by platform-specific URL params

**Utilities/Helpers:**
- General utilities: `platforms/base.py` (shared across platforms)
- Form logic: `form_filler.py` (application form filling)
- Scoring: `scorer.py` (job matching and rating)
- Shared models: `models.py` (Pydantic schemas)

## Special Directories

**browser_sessions/:**
- Purpose: Persistent browser state for session caching
- Generated: Yes (auto-created by `get_browser_context()`)
- Committed: No (gitignored — contains authentication data)
- Lifetime: Persists across multiple orchestrator runs until manually deleted
- When to delete: If login state is corrupted; orchestrator will re-authenticate on next run

**debug_screenshots/:**
- Purpose: Error screenshots for troubleshooting
- Generated: Yes (on selector failures, login issues, unexpected page states)
- Committed: No (gitignored — can be large)
- Naming: Includes platform, context, and timestamp for tracking

**job_pipeline/:**
- Purpose: Execution outputs and intermediate files
- Generated: Yes (phases 2-3 create JSON files; phase 4 creates descriptions)
- Committed: No for JSON files (gitignored), but `tracker.md` can be committed for history
- Cleanup: Safe to delete; orchestrator recreates on next run

**job_pipeline/descriptions/:**
- Purpose: Individual markdown files per scored job
- Generated: Yes (one per score 3+ job in phase 3)
- Committed: No (gitignored)
- Naming: `{company}_{title}.md` (sanitized for filesystem)

**resumes/tailored/:**
- Purpose: Company-specific tailored resume versions
- Generated: Manual (not auto-generated by pipeline)
- Committed: No (gitignored — many variants)
- Format: PDF (same as main resumes)

---

*Structure analysis: 2026-02-07*
