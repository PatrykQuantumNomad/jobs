# Architecture

**Analysis Date:** 2026-02-07

## Pattern Overview

**Overall:** Multi-stage job discovery pipeline with human-in-the-loop checkpoints

**Key Characteristics:**
- **Modular platform layer** — Independent, isolated platform implementations (Indeed, Dice, RemoteOK)
- **Five-phase execution** — Setup → Login → Search → Score → Apply (controlled by central orchestrator)
- **Human-in-the-loop design** — Mandatory human approval before application submission, CAPTCHA/verification detection
- **Deduplication engine** — Cross-platform job matching using normalized keys before scoring
- **Async-ready** — RemoteOK uses async/await; browser platforms are synchronous

## Layers

**Browser Automation Layer:**
- Purpose: Orchestrate Playwright stealth sessions for Indeed and Dice
- Location: `platforms/stealth.py`, `platforms/base.py`
- Contains: `get_browser_context()`, persistent context factory, stealth patches, abstract `BasePlatform`
- Depends on: Playwright, playwright-stealth 2.0.1
- Used by: Indeed/Dice platform implementations, orchestrator

**Platform Adapters:**
- Purpose: Platform-specific scraping, search, and apply logic
- Location: `platforms/indeed.py`, `platforms/dice.py`, `platforms/remoteok.py`
- Contains: Login flow, search execution, job extraction, apply form handling
- Depends on: `BasePlatform`, config, models, stealth utilities
- Used by: Orchestrator

**Scoring Engine:**
- Purpose: Rate jobs 1-5 against candidate profile using weighted criteria
- Location: `scorer.py`
- Contains: `JobScorer` class with title, tech, location, and salary scoring
- Depends on: Models, config (candidate profile)
- Used by: Orchestrator phase 3

**Data Models:**
- Purpose: Pydantic v2 schemas for Job, SearchQuery, CandidateProfile
- Location: `models.py`
- Contains: Enums (JobStatus), validators, deduplication logic
- Depends on: Pydantic v2
- Used by: All layers

**Configuration & Secrets:**
- Purpose: Centralized environment loading, platform settings, search queries
- Location: `config.py`
- Contains: Credential loading (from .env), directory paths, timing parameters, search query list
- Depends on: python-dotenv
- Used by: All layers

**Form Filling Heuristics:**
- Purpose: Generic field matching and form population for application forms
- Location: `form_filler.py`
- Contains: Keyword-based field identification, value mapping from candidate profile
- Depends on: Config, models
- Used by: Platform apply methods

**Web Dashboard:**
- Purpose: SQLite-backed job tracker with filtering, sorting, status updates
- Location: `webapp/app.py`, `webapp/db.py`
- Contains: FastAPI routes, Jinja2 templates, SQLite schema
- Depends on: FastAPI, Jinja2, htmx
- Used by: Manual post-pipeline job management

**Orchestrator (Entry Point):**
- Purpose: Coordinate all five phases, manage state, produce output
- Location: `orchestrator.py`
- Contains: `Orchestrator` class with phase methods, deduplication, raw/scored result I/O
- Depends on: All other layers
- Used by: CLI main()

## Data Flow

**Phase 0 - Setup:**

1. Validate Python version (3.11+)
2. Check `.env` exists with required credentials
3. Validate platform-specific secrets (Indeed: session-based, Dice: email+password)
4. Create output directories: `browser_sessions/`, `job_pipeline/`, `debug_screenshots/`, `resumes/`

**Phase 1 - Login:**

1. Get persistent browser context per platform (from `stealth.py`)
2. Indeed: Check for existing session; if missing, open login URL and wait for manual Google OAuth (up to 15s)
3. Dice: Two-step login (email → Continue → password → Sign In)
4. RemoteOK: Skip (no auth required)
5. Close browser on success or failure, cache session for future runs

**Phase 2 - Search:**

1. Load search queries from `Config.DEFAULT_SEARCH_QUERIES` (20 queries)
2. For each query:
   - Build platform-specific search URL with remote filter + recency filter
   - Extract job cards from results using CSS selectors
   - Fetch full job description from detail page
   - Store as `Job` object
3. Save raw results to `job_pipeline/raw_{platform}.json`

**Phase 3 - Score & Deduplicate:**

1. Load all `raw_{platform}.json` files → 600+ raw jobs
2. Deduplicate by normalized key (company + title): ~100 unique jobs
3. For each unique job, run `JobScorer.score_job()`:
   - Title match (0-2 points): exact target titles vs. keywords
   - Tech overlap (0-2 points): count keyword matches in description + tags
   - Location match (0-1 point): remote/Ontario/Canada
   - Salary match (0-1 point): salary >= $200K USD
   - Map 6-point raw score to 1-5 scale
4. Filter to score 3+ only (~20 jobs)
5. Save to `job_pipeline/discovered_jobs.json`
6. Write markdown tracker: `job_pipeline/tracker.md`
7. Generate individual job description files: `job_pipeline/descriptions/{company}_{title}.md`

**Phase 4 - Apply (Human-in-the-Loop):**

1. Display all score 4-5 jobs to human with:
   - Score, company, title, salary, location, platform, URL
   - Prompt for comma-separated indices to apply to
2. For each selected job:
   - If RemoteOK: print external URL (no automation)
   - If Indeed/Dice:
     - Open browser to job detail page
     - Auto-fill application form using `FormFiller`
     - Display form fields to human for review
     - Wait for explicit "submit" confirmation
     - Submit and mark job status as APPLIED
3. Update tracker with new statuses

**State Management:**

- `Orchestrator.discovered_jobs`: In-memory list of scoring jobs (score 3+)
- `Orchestrator._failed_logins`: Track platforms that failed login
- File-based: Raw JSON per-platform, deduplicated JSON, tracker markdown, descriptions
- SQLite (optional): `job_pipeline/jobs.db` for web dashboard persistence

## Key Abstractions

**Platform Interface (`BasePlatform`):**
- Purpose: Enforce contract for all scrapers
- Examples: `IndeedPlatform`, `DicePlatform`, `RemoteOKPlatform`
- Pattern: Abstract methods (login, is_logged_in, search, get_job_details, apply) with shared utilities (human_delay, screenshot, wait_for_human, element_exists)
- Key invariant: All apply methods MUST pause for human confirmation before final submit

**Job Model:**
- Purpose: Unified representation across platforms
- Example fields: id, platform, title, company, url, salary_min/max, description, tags, score, status, applied_date
- Dedup key: Normalized company + title (case-insensitive, stripped of legal suffixes)

**SearchQuery Model:**
- Purpose: Encapsulate search parameters
- Fields: query string, platform, location (auto-set for RemoteOK only), max_pages
- Platform-specific URL building: Each platform's `search()` method translates this into platform-specific URL params

**Stealth Context Factory:**
- Purpose: Abstract Playwright stealth setup
- Returns: (Playwright instance, BrowserContext) tuple
- Anti-detection: System Chrome (not bundled Chromium), disabled automation flag, playwright-stealth hooks
- Persistence: Separate session dirs per platform (`browser_sessions/{platform}/`)

## Entry Points

**CLI (Orchestrator):**
- Location: `orchestrator.py`, `main()` function
- Triggers: `python orchestrator.py [--platforms indeed dice remoteok] [--headed]`
- Responsibilities:
  - Parse command-line arguments (--platforms, --headed)
  - Instantiate `Orchestrator`
  - Call `run()` to execute all five phases
  - Print summary

**Web Dashboard:**
- Location: `webapp/app.py`
- Triggers: `python -m webapp.app` or `uvicorn webapp.app:app`
- Responsibilities:
  - Serve dashboard at http://localhost:8000
  - Load jobs from `job_pipeline/discovered_jobs.json` into SQLite
  - Render filtering/sorting UI with Jinja2 + htmx
  - Allow manual status updates and notes

## Error Handling

**Strategy:** Fail-open with human notification at critical points

**Patterns:**

1. **CAPTCHA/Cloudflare Detection:**
   - Indeed: Detected by checking for "Please solve this challenge" text or Cloudflare timeout
   - Action: Take screenshot, call `wait_for_human()`, pause orchestrator
   - Recovery: Human solves challenge, resumes execution

2. **Login Failure:**
   - Detected: `is_logged_in()` returns False after attempting login
   - Action: Print error message, add platform to `_failed_logins` set
   - Recovery: Skip platform for search phase; orchestrator continues with remaining platforms

3. **Selector Timeout:**
   - When element not found on page (stale selectors)
   - Action: Take screenshot, log error with selector name
   - Recovery: Retry with next job; log to `debug_screenshots/` for manual inspection

4. **Form Filling Failure:**
   - When field not recognized or fill fails
   - Action: Continue to next field (non-blocking)
   - Result: Summary displayed to human before submit

5. **Application Submission Failure:**
   - When form submit times out or server error
   - Action: Print error, mark job status as not applied, continue
   - Recovery: Manual retry available via web dashboard

## Cross-Cutting Concerns

**Logging:** Uses `print()` statements with structured prefixes ("  {platform}: ...", "  {step}: ..."). No file logging configured; console output only.

**Validation:**
- Pydantic v2 field validators (e.g., `salary_max >= salary_min`)
- Platform credential checks before each phase
- Directory existence verification

**Authentication:**
- Indeed: Session-based (Google OAuth), cached in `browser_sessions/indeed/`
- Dice: Email + password, cached in `browser_sessions/dice/`
- RemoteOK: No authentication required

**Rate Limiting:** Randomized delays between page navigations (2-5 seconds) and form interactions (1-2 seconds). Configured in `Config.NAV_DELAY_MIN/MAX`, `Config.FORM_DELAY_MIN/MAX`.

**Stealth:** Applied at context creation via `playwright_stealth.Stealth().apply_stealth_sync(page)`. Hooks all new pages created during session.

---

*Architecture analysis: 2026-02-07*
