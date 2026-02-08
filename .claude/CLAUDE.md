# JobFlow — Personal Job Search Automation

Self-hosted pipeline that scrapes job boards (Indeed, Dice, RemoteOK), scores matches against a candidate profile, manages listings through a web dashboard, generates AI-tailored resumes, and automates applications with configurable control levels. Single-user, local-only.

**Stack:** Python 3.14, Playwright + playwright-stealth, FastAPI + Jinja2 + htmx, SQLite (FTS5), Pydantic v2 + pydantic-settings (YAML), Anthropic SDK, WeasyPrint, SSE via sse-starlette.

## Commands

```bash
# Dev
uv run ruff format .                                     # format (line length 100)
uv run ruff check --fix .                                # lint + auto-fix
uv run pytest                                            # unit + integration tests
uv run pytest -m e2e                                     # E2E browser tests (separate)

# Run
python orchestrator.py                                   # full pipeline (all platforms)
python orchestrator.py --platforms indeed remoteok        # select platforms
python orchestrator.py --platforms indeed --headed        # visible browser for debugging
python -m webapp.app                                     # dashboard at localhost:8000

# Setup
pip install -r requirements.txt && playwright install chromium
```

## Architecture

Five-phase pipeline (setup → login → search → score → apply) with pluggable platform adapters registered via `@register_platform` decorator. Dual-track: synchronous Playwright automation for scraping, async FastAPI dashboard for UI.

**Key layers:**
- `orchestrator.py` — Pipeline coordination, phase sequencing, human-in-the-loop prompts
- `platforms/` — Pluggable adapters behind Protocol interfaces (`protocols.py`). Each platform has a module + `*_selectors.py` for DOM selectors
- `scorer.py` — Job scoring (1–5) with explainable breakdowns against candidate profile
- `webapp/` — FastAPI dashboard with SQLite, htmx partials, SSE streaming for apply progress
- `apply_engine/` — Background thread apply orchestration with SSE events and confirmation gates
- `resume_ai/` — Anthropic structured outputs for resume tailoring, anti-fabrication validation
- `config.py` — Pydantic settings loading from `config.yaml` (operational) + `.env` (secrets)
- `models.py` — Pydantic v2 domain models (Job, SearchQuery, CandidateProfile)

**Config split:** Operational settings (queries, weights, timing) in `config.yaml`. Credentials and personal data in `.env` (never committed). Singleton via `get_settings()`.

## Conventions

- **Formatting:** Ruff, line length 100, rules `["E", "F", "I", "UP", "B", "SIM"]`
- **Types:** Use `str | None` not `Optional[str]`, `list[Job]` not `List[Job]`. No `from __future__ import annotations` needed (Python 3.14 has native deferred evaluation)
- **Imports:** Absolute only, never relative. Order: future → stdlib → third-party → local. Use `if TYPE_CHECKING:` for type-only imports
- **Naming:** snake_case functions/vars, PascalCase classes, UPPER_CASE constants. Private with underscore prefix. Platform classes: `{Name}Platform`
- **Pydantic:** `BaseModel` for domain objects, `BaseSettings` for config. `model_dump(mode="json")` for serialization. `@field_validator` with `@classmethod`
- **Error handling:** Catch-and-log for per-query/per-job failures (pipeline continues). Raise for config/setup errors (fail fast). Screenshot to `debug_screenshots/` on unexpected page state
- **Selectors:** Always isolated in `*_selectors.py` — never inline selectors in platform logic. Verify elements exist before interaction
- **Tests:** `@pytest.mark.unit` or `@pytest.mark.integration` on test classes. E2E tests marked `@pytest.mark.e2e` (excluded from default run)

## Where to Add New Code

- **New platform:** `platforms/{name}.py` + `platforms/{name}_selectors.py`. Add `@register_platform` decorator. Protocol validated at import time.
- **New dashboard route:** `webapp/app.py` (route) + `webapp/templates/partials/` (htmx partial) + `webapp/db.py` (query if needed)
- **New scoring factor:** `scorer.py` (method + update ScoreBreakdown) + `config.yaml` (weight)
- **New resume AI feature:** `resume_ai/{feature}.py` + `resume_ai/models.py` (Pydantic model for structured output)

## Human-in-the-Loop Checkpoints

IMPORTANT: Non-negotiable. The agent MUST stop and wait for human input:

1. CAPTCHA / Cloudflare challenge → screenshot, report, wait
2. Email or SMS verification → report, wait for human
3. Before submitting ANY application → display job title, company, salary, match score — wait for explicit "yes"
4. Selector failures → screenshot to `debug_screenshots/`, report before retrying
5. Missing credentials → report and skip that platform entirely
6. Before uploading resume → confirm which resume version

## Browser Automation Safety

- Always use `launch_persistent_context()` with per-platform user data dir in `browser_sessions/`
- Never attempt CAPTCHA bypass — stop and ask human
- Rate limiting: 2–5s randomized delay between navigations, 1–2s between form actions
- Stealth: `channel="chrome"` (system Chrome), `playwright-stealth` 2.0.1 API: `Stealth().apply_stealth_sync(page)`
- Credentials from `.env` via python-dotenv — if missing, skip platform
- NEVER fabricate experience or qualifications in any form fill
- NEVER commit `.env` files or credentials

## Planning & State (GSD)

This project uses the GSD plugin. Planning artifacts live in `.planning/` and are generated/maintained by GSD commands. When `.planning/` exists, read the relevant doc for deeper context:

- `.planning/STATE.md` — Where we left off, session continuity, accumulated decisions
- `.planning/ROADMAP.md` — Current milestone, phase status, plan details
- `.planning/PROJECT.md` — Scope, constraints, key decisions, shipped vs in-progress
- `.planning/REQUIREMENTS.md` — Requirement IDs and traceability
- `.planning/codebase/*.md` — Deep architecture, conventions, concerns, integrations analysis

## Agent Teams

Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json` env. Describe team structure in your prompt — each teammate loads this CLAUDE.md automatically.
