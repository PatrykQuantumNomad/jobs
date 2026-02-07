# Technology Stack

**Analysis Date:** 2026-02-07

## Languages

**Primary:**
- Python 3.11+ - All core application code, including browser automation, API clients, and web server

**Secondary:**
- Jinja2 - Web dashboard templating (HTML)
- JavaScript/htmx - Frontend interactions in web dashboard (minimal, htmx-driven)

## Runtime

**Environment:**
- Python 3.11 (or later)
- Chromium via Playwright (headless or headed)

**Package Manager:**
- pip/uv - `pyproject.toml` based dependency management
- Lockfile: Present via `pyproject.toml` with `[dependency-groups]` for dev deps

## Frameworks

**Core:**
- Playwright 1.58.0+ - Browser automation (Indeed, Dice), persistent contexts
- playwright-stealth 2.0.1+ - Anti-detection layer (applies Stealth patches to pages, hooks browser context)
- httpx 0.27.0+ - Async HTTP client for RemoteOK API
- pydantic 2.0.0+ - Data validation and serialization (Job, SearchQuery, CandidateProfile models)
- FastAPI 0.115.0+ - Web server for job tracker dashboard
- Jinja2 3.1.0+ - Template rendering for dashboard

**Testing:**
- pytest 8.0.0+ - Unit testing framework
- ruff 0.9.0+ - Linting and import sorting

**Build/Dev:**
- hatchling - Python package building (specified in `[build-system]`)
- uvicorn 0.34.0+ - ASGI server for FastAPI (via `webapp.app:main`)

## Key Dependencies

**Critical:**
- Playwright 1.58.0+ - Core browser automation infrastructure; removes `--enable-automation` flag and uses `channel="chrome"` to avoid detection
- playwright-stealth 2.0.1+ - Applies stealth patches via `Stealth().apply_stealth_sync(page)` API; essential for circumventing Cloudflare and fingerprinting
- httpx 0.27.0+ - Async HTTP client for RemoteOK API queries; supports `httpx.AsyncClient` with async/await
- pydantic 2.0.0+ - Type-safe models; uses `field_validator`, `model_dump(mode="json")` for serialization

**Infrastructure:**
- python-dotenv 1.0.0+ - Environment variable loading from `.env` file at application startup
- python-jobspy 1.1.0+ - Optional supplementary job discovery (listed but not actively integrated in current code)
- FastAPI 0.115.0+ - REST API + Jinja2 template rendering for dashboard
- uvicorn 0.34.0+ - ASGI application server (used in `webapp.app:main`)
- python-multipart 0.0.18+ - Form data parsing for FastAPI endpoints

## Configuration

**Environment:**
- `.env` file (gitignored) - Contains `INDEED_EMAIL`, `INDEED_PASSWORD`, `DICE_EMAIL`, `DICE_PASSWORD`
- Template: `.env.example` provided with placeholder credentials
- Loaded at startup via `from dotenv import load_dotenv` in `config.py`

**Build:**
- `pyproject.toml` - Project metadata, dependency declarations, build backend config
  - `[tool.ruff]` section: Python 3.11 target, 100-char line length, rules E, F, I, UP, B, SIM
  - `[tool.pytest.ini_options]` section: Tests located in `tests/` directory
  - Entry points: `jobs-scrape` → `orchestrator:main`, `jobs-web` → `webapp.app:main`

## Platform Requirements

**Development:**
- Python 3.11+ installed
- Chrome/Chromium available locally (Playwright uses `channel="chrome"` for system browser)
- Virtual environment with dependencies from `pyproject.toml`
- Credentials in `.env`: `INDEED_EMAIL`, `DICE_EMAIL`, `DICE_PASSWORD` (Indeed uses Google OAuth, no password needed)

**Production:**
- Python 3.11+ runtime
- System Chrome installed (Playwright anti-detection requires system browser, not Playwright's bundled Chromium)
- Persistent directories: `browser_sessions/`, `job_pipeline/`, `debug_screenshots/`, `resumes/`
- `.env` with credentials at application root
- Network access to: `indeed.com`, `dice.com`, `remoteok.com` APIs

## Database

**SQLite:**
- Location: `job_pipeline/jobs.db`
- Manager: Direct `sqlite3` module (not an ORM)
- Used by: Web dashboard (`webapp/db.py`)
- Schema created on first import via `SCHEMA` in `webapp/db.py`
- Fields: jobs table with id, platform, title, company, location, url, salary*, apply_url, description, posted_date, tags, easy_apply, score, status, applied_date, notes, created_at, updated_at, dedup_key

---

*Stack analysis: 2026-02-07*
