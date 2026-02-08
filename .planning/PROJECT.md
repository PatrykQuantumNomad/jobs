# JobFlow -- Personal Job Search Automation

## What This Is

A self-hosted, single-user job search automation platform with comprehensive test coverage. Clone the repo, drop in your resume and a YAML config file, and the system scrapes job boards (Indeed, Dice, RemoteOK), scores matches against your profile, manages listings through a web dashboard with analytics and kanban views, generates AI-tailored resumes and cover letters, and automates applications with configurable control levels -- from one-click auto-apply to careful manual review. Runs daily via launchd scheduler with real-time SSE progress streaming to the dashboard. Backed by 428 automated tests and CI pipeline.

## Core Value

**From discovery to application in one tool.** The system must reliably find relevant jobs, present them clearly, and make applying as frictionless as the user wants -- whether that's one-click auto-apply or careful manual review.

## Requirements

### Validated

- ✓ Multi-platform scraping (Indeed, Dice, RemoteOK) -- existing + v1.0
- ✓ Stealth browser automation with anti-detection (Playwright + playwright-stealth) -- existing
- ✓ Session persistence per platform (browser_sessions/) -- existing
- ✓ Human-in-the-loop CAPTCHA/verification handling -- existing
- ✓ Job scoring engine (1-5 scale against candidate profile) -- existing + v1.0
- ✓ Cross-platform deduplication by normalized company+title -- existing + v1.0 (fuzzy)
- ✓ CLI orchestrator with 5-phase pipeline (setup -> login -> search -> score -> apply) -- existing
- ✓ Web dashboard with SQLite persistence, filtering, status updates -- existing + v1.0
- ✓ Form filling heuristics for application fields -- existing + v1.0 (ATS iframe)
- ✓ Configurable search queries and platform selection -- existing + v1.0 (YAML)
- ✓ Debug screenshot capture on selector failure -- existing
- ✓ CFG-01: Single YAML config for all settings -- v1.0
- ✓ CFG-02: Scheduled pipeline runs via launchd -- v1.0
- ✓ CFG-03: Salary normalization to comparable USD annual -- v1.0
- ✓ CFG-04: Apply mode selection (full-auto, semi-auto, easy-apply-only) -- v1.0
- ✓ DISC-01: Delta detection for new jobs -- v1.0
- ✓ DISC-02: Fuzzy company deduplication -- v1.0
- ✓ DISC-03: Score breakdown with point-by-point explanation -- v1.0
- ✓ DASH-01: FTS5 text search -- v1.0
- ✓ DASH-02: 9-status workflow (Saved through Ghosted) -- v1.0
- ✓ DASH-03: Bulk status actions -- v1.0
- ✓ DASH-04: CSV/JSON export -- v1.0
- ✓ DASH-05: Activity log per job -- v1.0
- ✓ DASH-06: Analytics with Chart.js -- v1.0
- ✓ DASH-07: Kanban board with SortableJS drag-and-drop -- v1.0
- ✓ AI-01: AI-tailored resume per job -- v1.0
- ✓ AI-02: AI-generated cover letter -- v1.0
- ✓ AI-03: Multi-resume version tracking -- v1.0
- ✓ APPLY-01: One-click apply from dashboard with SSE streaming -- v1.0
- ✓ PLAT-01: Pluggable platform architecture -- v1.0
- ✓ 428 automated tests (unit, integration, E2E) with 80%+ coverage -- v1.1
- ✓ GitHub Actions CI pipeline with coverage enforcement and linting -- v1.1
- ✓ Test isolation infrastructure (settings reset, in-memory DB, network/API blocking) -- v1.1
- ✓ Playwright E2E tests for dashboard, kanban, and export flows -- v1.1

### Active

(None -- planning next milestone)

### Out of Scope

- Multi-user / multi-tenant support -- single-user tool, configured per clone
- Mobile app / PWA -- web dashboard is sufficient, job apps happen at a desk
- LinkedIn integration -- aggressive anti-automation, permanent account ban risk
- CAPTCHA/Cloudflare bypass -- arms race, legally grey, detect-and-notify is correct
- Chrome extension -- separate product, tangential to core
- AI chatbot interface -- LLM latency per interaction, slower than clicking filters
- Contact/networking CRM -- separate problem domain, notes field is sufficient
- Payment/subscription features -- open-source portfolio project, no monetization
- Fully autonomous mass-apply -- ATS blacklisting risk, destroys candidate reputation
- Offline mode -- real-time scraping is core value

## Context

**v1.0 shipped:** 2026-02-08. 8 phases, 24 plans, ~80 tasks. 6,705 Python + 1,501 HTML LOC. Full pipeline from YAML config through discovery, scoring, dashboard management, AI resume tailoring, to one-click apply with real-time SSE streaming.

**v1.1 shipped:** 2026-02-08. 7 phases, 14 plans, 45 requirements. 5,639 lines of test code. 428 tests (417 unit/integration + 11 E2E). GitHub Actions CI with 80%+ coverage enforcement. Found and fixed 4 production bugs during test development.

**Tech stack:** Python 3.14, Playwright + playwright-stealth, FastAPI + Jinja2 + htmx, SQLite (FTS5), pydantic-settings + YAML, Anthropic SDK (Claude), WeasyPrint, sse-starlette, Chart.js, SortableJS, pytest + factory-boy + respx + pytest-playwright

**Known technical debt:**
- CDN-loaded JS libraries (htmx, Chart.js, SortableJS) rather than bundled
- Lazy imports could be replaced with proper dependency injection
- ATS form fill covers 5 providers (Greenhouse, Lever, Ashby, BambooHR, Workday) but needs broader coverage
- 4 analytics routes lack integration tests
- SSE endpoint testing not implemented (TestClient + EventSourceResponse interaction)
- scorer.py score_batch_with_breakdown uncovered (8 lines)

## Constraints

- **Tech stack**: Python 3.14, Playwright, FastAPI -- established and working, no reason to change
- **Single user**: All design decisions assume one user per installation. No auth layer needed.
- **Anti-detection**: Must maintain stealth browser approach. System Chrome, no automation flags.
- **Human-in-the-loop**: Application submission always requires human approval (even in "auto" mode, there's an approve step)
- **Credentials**: Always from .env, never committed. Platform credentials stay separate from user profile config.
- **Test coverage**: Maintain 80%+ coverage. All new features must include tests.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| pydantic-settings with YAML config | Clean, validated, type-safe configuration | ✓ Good |
| Protocol-based platform architecture | More Pythonic than ABC, easier to test and extend | ✓ Good |
| Three apply modes (auto/semi/manual) | Different comfort levels for different job types | ✓ Good |
| Anthropic SDK for AI (not LangChain) | Lightweight, single-prompt use doesn't need framework overhead | ✓ Good |
| asyncio.to_thread for Playwright bridge | Correct pattern for sync-in-async without blocking event loop | ✓ Good |
| FTS5 content-sync tables | Search without double-storage of job data | ✓ Good |
| WeasyPrint for PDF rendering | Jinja2 HTML templates, Calibri/Carlito font fallback for ATS | ✓ Good |
| SSE via sse-starlette + htmx-ext-sse | Real-time dashboard updates without WebSocket complexity | ✓ Good |
| Temperature=0 for resume, 0.3 for cover letter | Max accuracy for factual resume, natural voice for letters | ✓ Good |
| Lazy imports throughout | Prevents circular deps and startup failures when optional deps missing | ✓ Good -- but tech debt |
| Strict asyncio mode for tests | Force explicit @pytest.mark.asyncio, prevent accidental sync/async mixing | ✓ Good |
| JOBFLOW_TEST_DB=1 for in-memory SQLite | Clean separation: env var before import prevents production DB touch | ✓ Good |
| Factory-boy with Meta.model=Job | Automatic Pydantic validation on every factory-created instance | ✓ Good |
| No Playwright mocking for scraper tests | Anti-pattern; extract pure parsing functions instead for testability | ✓ Good |
| Coverage threshold in pyproject.toml | Single source of truth, not CLI flags that can diverge | ✓ Good |
| E2E tests CI-optional (continue-on-error) | Playwright browser tests are flaky by nature, shouldn't block PRs | ✓ Good |

---
*Last updated: 2026-02-08 after v1.1 milestone complete*
