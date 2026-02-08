# Technology Stack

**Analysis Date:** 2026-02-07

## Languages

**Primary:**
- Python 3.11+ - All application code (orchestrator, platforms, webapp, resume AI)

**Secondary:**
- None - Pure Python project

## Runtime

**Environment:**
- Python 3.11 or higher (required)

**Package Manager:**
- uv / pip
- Lockfile: None (dependencies specified in `pyproject.toml`)
- Virtual environment: `.venv/` (gitignored)

## Frameworks

**Core:**
- FastAPI 0.115.0+ - Web dashboard backend (`webapp/app.py`)
- Playwright 1.58.0+ - Browser automation (Indeed, Dice)
- Pydantic 2.x - Data validation and settings management

**Testing:**
- pytest 8.0.0+ - Test framework (dev dependency)

**Build/Dev:**
- Hatchling - Build backend (`pyproject.toml`)
- Ruff 0.9.0+ - Linter and formatter (dev dependency)

## Key Dependencies

**Critical:**
- `playwright-stealth>=2.0.1` - Anti-detection for browser automation (`platforms/stealth.py`)
- `httpx>=0.27.0` - Async HTTP client for RemoteOK API (`platforms/remoteok.py`)
- `anthropic>=0.79.0` - Claude API for resume tailoring (`resume_ai/tailor.py`)
- `pydantic>=2.0.0,<3.0.0` - Data models and validation (`models.py`, `config.py`)
- `pydantic-settings[yaml]>=2.12.0` - Multi-source config (YAML + .env)

**Infrastructure:**
- `python-dotenv>=1.0.0` - Environment variable loading from `.env`
- `python-jobspy>=1.1.0` - Supplementary job discovery (optional)
- `jinja2>=3.1.0` - Template engine for web dashboard
- `uvicorn>=0.34.0` - ASGI server for FastAPI
- `python-multipart>=0.0.18` - Form data parsing (file uploads)
- `rapidfuzz>=3.14` - Fuzzy string matching for deduplication
- `pymupdf4llm>=0.2.9` - PDF text extraction (resume parsing)
- `weasyprint>=68.0` - HTML to PDF conversion (resume rendering)
- `sse-starlette` - Server-sent events for apply engine (runtime import)

## Configuration

**Environment:**
- Configuration loaded via `config.py` using pydantic-settings
- Operational settings: `config.yaml` (search queries, scoring weights, platform toggles)
- Credentials/personal data: `.env` (Indeed email, Dice email/password, candidate profile)
- Settings singleton: `get_settings()` from `config.py`

**Build:**
- `pyproject.toml` - PEP 621 project metadata, dependencies, tool configuration
- `tool.ruff` - Linter config (target Python 3.11, line length 100)
- `tool.pytest.ini_options` - Test configuration (testpaths: `tests/`)

## Platform Requirements

**Development:**
- Python 3.11+
- Chromium browser installed via `playwright install chromium`
- System Chrome browser (for stealth mode via `channel="chrome"`)

**Production:**
- Same as development (designed for local execution, not deployment)
- Persistent browser sessions stored in `browser_sessions/` (gitignored)
- SQLite database at `job_pipeline/jobs.db` (created automatically)

---

*Stack analysis: 2026-02-07*
