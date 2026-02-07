# External Integrations

**Analysis Date:** 2026-02-07

## APIs & External Services

**Indeed.com:**
- Search API + Easy Apply integration
  - SDK/Client: Playwright browser automation (stealth)
  - Auth: Google OAuth (session-based via `secure.indeed.com/auth`)
  - Env vars: `INDEED_EMAIL` (no password — OAuth login)
  - Anti-bot: HIGH (Cloudflare Turnstile, fingerprinting)
  - Entry point: `platforms/indeed.py` → `IndeedPlatform` class
  - Human-in-loop: Required for CAPTCHA, Cloudflare challenge, email verification

**Dice.com:**
- Job search + Easy Apply integration
  - SDK/Client: Playwright browser automation
  - Auth: Email + password login (two-step: email → "Continue" → password → "Sign In")
  - Env vars: `DICE_EMAIL`, `DICE_PASSWORD`
  - Anti-bot: LOW (standard delays sufficient, no CAPTCHA reported)
  - Entry point: `platforms/dice.py` → `DicePlatform` class
  - Human-in-loop: Required for unusual challenges or selector failures

**RemoteOK.com:**
- Pure HTTP API for job listings
  - SDK/Client: `httpx.AsyncClient` (async HTTP)
  - Auth: None required
  - Endpoint: `GET https://remoteok.com/api`
  - Response format: JSON array; index 0 is metadata, real jobs from index 1+
  - Entry point: `platforms/remoteok.py` → `RemoteOKPlatform` class
  - Data delay: 24 hours behind real-time

## Data Storage

**Databases:**
- SQLite at `job_pipeline/jobs.db`
  - Connection: Direct `sqlite3.connect()` in `webapp/db.py`
  - Client: Native Python `sqlite3` module (no ORM)
  - Schema: Single `jobs` table with job metadata, scoring, and status fields
  - Initialized on first app startup

**File Storage:**
- Local filesystem only:
  - `job_pipeline/` - Pipeline output (raw JSON, scored JSON, descriptions)
  - `job_pipeline/descriptions/` - Individual job descriptions as markdown files
  - `browser_sessions/{platform}/` - Persistent Playwright browser contexts (chromium user data dirs)
  - `debug_screenshots/` - Screenshots on selector failures or errors
  - `resumes/` - Resume PDFs (ATS-optimized and standard versions)

**Caching:**
- Browser session persistence: Playwright `launch_persistent_context()` caches cookies/session per platform in `browser_sessions/{platform}/`
- No external cache service (Redis, Memcached, etc.)

## Authentication & Identity

**Auth Providers:**
- **Indeed:** Google OAuth (via `secure.indeed.com/auth`) — session-based, cached in persistent browser context
- **Dice:** Native email/password login (two-step form)
- **RemoteOK:** No authentication required

**Implementation:**
- Credentials stored in `.env` (gitignored)
- Loaded at startup by `config.py` via `python-dotenv`
- Indeed: Uses browser session persistence; Google auth is browser-based, requires manual login on first run
- Dice: Direct credential passing in login form

## Monitoring & Observability

**Error Tracking:**
- Custom screenshot-based debugging: `screenshot()` method saves full-page PNG to `debug_screenshots/` on selector failures
- No remote error tracking service (Sentry, DataDog, etc.)

**Logs:**
- Console output only (print statements in orchestrator, platform modules)
- No structured logging framework
- Errors surface via orchestrator exception handling and error messages
- Human-in-loop checkpoints prompt for manual action on failures

## CI/CD & Deployment

**Hosting:**
- Local (development only currently)
- Python application runs locally; not containerized

**CI Pipeline:**
- None configured
- No GitHub Actions, GitLab CI, or other automation

## Environment Configuration

**Required env vars:**
- `INDEED_EMAIL` - Gmail address for Indeed Google OAuth (no password needed)
- `DICE_EMAIL` - Dice account email
- `DICE_PASSWORD` - Dice account password

**Optional vars:**
- None (all other config is in `config.py`)

**Secrets location:**
- `.env` file at project root (template: `.env.example`)
- Never committed to git (in `.gitignore`)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- RemoteOK: `apply_url` field in API response redirects to company's external ATS (Lever, Greenhouse, Ashby, etc.)
- No outbound webhooks initiated by this application

## External Dependencies for Core Functionality

**Playwright Stealth:**
- `playwright-stealth` 2.0.1+ patches Playwright pages to remove automation detection
- Applies patches via `Stealth().apply_stealth_sync(page)` to all pages in persistent context
- Essential for avoiding anti-bot measures on Indeed (Cloudflare) and Dice

**Browser Channel:**
- Uses `channel="chrome"` to launch system Chrome instead of Playwright's bundled Chromium
- Reason: Google blocks OAuth (Indeed login) in automation-detected browsers; system Chrome bypasses this

**User Agent & Fingerprinting:**
- Custom user agent: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...`
- Locale: `en-US`, Timezone: `America/Toronto`
- Stealth patches hide `--enable-automation` flag and `AutomationControlled` features

## Rate Limiting & Delays

**Indeed/Dice (Browser):**
- Navigation delay: 2–5 seconds (randomized)
- Form interaction delay: 1–2 seconds (randomized)
- Page load timeout: 30 seconds
- Purpose: Avoid triggering anti-bot rate limits

**RemoteOK (API):**
- User-Agent header: `JobSearchBot/1.0 (pgolabek@gmail.com)`
- No explicit rate limit observed; 95 jobs returned per API call
- Timeout: 30 seconds per request

## Resume Integration

**Resume Files:**
- `resumes/Patryk_Golabek_Resume_ATS.pdf` - Default, ATS-optimized resume
- `resumes/Patryk_Golabek_Resume.pdf` - Standard resume
- `resumes/tailored/` - Per-company tailored versions (not auto-generated)
- Upload via: Form filler `fill_form()` method detects file input and calls `set_input_files()`

---

*Integration audit: 2026-02-07*
