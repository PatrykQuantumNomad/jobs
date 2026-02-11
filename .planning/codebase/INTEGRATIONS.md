# External Integrations

**Analysis Date:** 2026-02-07

## APIs & External Services

**Job Platforms:**
- Indeed - Browser automation via Playwright (session-based Google OAuth)
  - SDK/Client: playwright (sync API)
  - Auth: INDEED_EMAIL (env var) - cached session in `browser_sessions/indeed/`
  - Anti-bot: HIGH - Cloudflare Turnstile, fingerprinting, behavioral analysis
  - Stealth: `playwright-stealth` 2.0.1 with system Chrome

- Dice - Browser automation via Playwright (email/password)
  - SDK/Client: playwright (sync API)
  - Auth: DICE_EMAIL, DICE_PASSWORD (env vars)
  - Anti-bot: LOW - standard delays sufficient

- RemoteOK - Public HTTP API (no auth)
  - SDK/Client: httpx (async client)
  - Auth: None (User-Agent header for politeness)
  - Endpoint: `https://remoteok.com/api`

**AI/ML:**
- Anthropic Claude - Resume tailoring and cover letter generation via CLI subprocess
  - Client: `claude_cli/` package (asyncio.create_subprocess_exec)
  - Auth: Claude CLI authenticated via user's Anthropic subscription (no API key needed)
  - Model: `sonnet` (CLI alias, resolves to latest Claude Sonnet)
  - Usage: `resume_ai/tailor.py`, `resume_ai/cover_letter.py`, `ai_scorer.py`
  - API: `claude_cli.run()` with `--json-schema` for structured output

## Data Storage

**Databases:**
- SQLite (local)
  - Connection: `job_pipeline/jobs.db` (auto-created)
  - Client: sqlite3 (stdlib)
  - Schema: `webapp/db.py` - jobs, run_history, activity_log, resume_versions, jobs_fts (FTS5)
  - Migrations: Version-based via `PRAGMA user_version` (6 schema versions)

**File Storage:**
- Local filesystem only
  - Job descriptions: `job_pipeline/descriptions/` (markdown)
  - Resumes: `resumes/` (PDF)
  - Tailored resumes: `resumes/tailored/` (PDF)
  - Screenshots: `debug_screenshots/` (PNG)
  - Browser sessions: `browser_sessions/{platform}/` (Playwright persistent contexts)
  - Pipeline output: `job_pipeline/*.json` (raw and scored jobs)

**Caching:**
- Browser session persistence via Playwright `launch_persistent_context()`
  - Indeed: `browser_sessions/indeed/`
  - Dice: `browser_sessions/dice/`

## Authentication & Identity

**Auth Provider:**
- Custom per-platform
  - Indeed: Google OAuth (manual first-time login, session cached)
  - Dice: Form-based email/password (two-step: email → Continue → password → Sign In)
  - RemoteOK: None (public API)

**Implementation:**
- Session management: Playwright persistent contexts with stealth patches (`platforms/stealth.py`)
- Credential storage: `.env` file (never committed)
- Validation: `config.py::AppSettings.validate_platform_credentials(platform: str)`

## Monitoring & Observability

**Error Tracking:**
- None (local execution only)

**Logs:**
- Stdout/stderr only
- Activity log: SQLite `activity_log` table (job-level events: discovered, viewed, status_change, note_added, resume_tailored)
- Run history: SQLite `run_history` table (pipeline execution metadata)

## CI/CD & Deployment

**Hosting:**
- Local execution only (not deployed)

**CI Pipeline:**
- None

**Automation:**
- Scheduled runs via macOS launchd (`scheduler.py` generates `.plist` files)
- Manual execution via `python orchestrator.py` or `jobs-scrape` script

## Environment Configuration

**Required env vars:**
- `INDEED_EMAIL` - Indeed account email (session-based Google auth)
- `DICE_EMAIL` - Dice account email
- `DICE_PASSWORD` - Dice account password
- Candidate profile fields: `CANDIDATE_FIRST_NAME`, `CANDIDATE_LAST_NAME`, `CANDIDATE_EMAIL`, etc. (20+ fields in `config.py`)

**Secrets location:**
- `.env` file in project root (gitignored)
- Example: `.env.example` (committed, no real credentials)

**Optional env vars:**
- `JOBFLOW_TEST_DB=1` - Use in-memory SQLite for testing (`webapp/db.py`)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (all integrations are pull-based)

## Browser Automation Details

**Stealth Configuration:**
- System: `platforms/stealth.py::get_browser_context()`
- Browser: System Chrome via `channel="chrome"` (NOT Playwright's bundled Chromium)
- Anti-detection:
  - `--disable-blink-features=AutomationControlled`
  - `ignore_default_args=["--enable-automation"]`
  - `playwright-stealth` 2.0.1 API: `Stealth().apply_stealth_sync(page)`
- User-Agent: Mozilla/5.0 Macintosh Chrome/120.0.0.0
- Locale: en-US
- Timezone: America/Toronto

**Session Persistence:**
- Persistent contexts: `launch_persistent_context(user_data_dir)`
- Indeed: `browser_sessions/indeed/`
- Dice: `browser_sessions/dice/`
- Benefits: Cached cookies, local storage, login sessions

## Human-in-the-Loop Checkpoints

**Interactive Flows:**
- CAPTCHA detection → screenshot + raise RuntimeError (`platforms/indeed.py`)
- Email verification → screenshot + raise RuntimeError
- Application confirmation → `wait_for_human()` prompt before submit
- Resume upload confirmation → `wait_for_human()` prompt

**Non-interactive Mode:**
- Scheduled runs (`_unattended=True`) skip interactive prompts, raise errors instead

---

*Integration audit: 2026-02-07*
