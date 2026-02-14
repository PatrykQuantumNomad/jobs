# JobFlow -- Personal Job Search Automation

## What This Is

A self-hosted, single-user job search automation platform with comprehensive test coverage, AI features powered by Claude CLI, and a professional showcase site. Clone the repo, install Claude CLI, drop in your resume and a YAML config file, and the system scrapes job boards (Indeed, Dice, RemoteOK), scores matches against your profile (rule-based + on-demand AI semantic analysis), manages listings through a web dashboard with analytics and kanban views, generates AI-tailored resumes and cover letters with real-time SSE progress streaming, and automates applications with configurable control levels -- from one-click auto-apply to careful manual review. Runs daily via launchd scheduler. Backed by 581 automated tests and CI pipeline. Includes a deployed GitHub Pages showcase site at patrykquantumnomad.github.io/jobs/.

## Core Value

**From discovery to application in one tool.** The system must reliably find relevant jobs, present them clearly, and make applying as frictionless as the user wants -- whether that's one-click auto-apply or careful manual review.

## Requirements

### Validated

- ✓ Multi-platform scraping (Indeed, Dice, RemoteOK) -- v1.0
- ✓ Stealth browser automation with anti-detection (Playwright + playwright-stealth) -- v1.0
- ✓ Session persistence per platform (browser_sessions/) -- v1.0
- ✓ Human-in-the-loop CAPTCHA/verification handling -- v1.0
- ✓ Job scoring engine (1-5 scale against candidate profile) -- v1.0
- ✓ Cross-platform deduplication by normalized company+title -- v1.0
- ✓ CLI orchestrator with 5-phase pipeline (setup -> login -> search -> score -> apply) -- v1.0
- ✓ Web dashboard with SQLite persistence, filtering, status updates -- v1.0
- ✓ Form filling heuristics for application fields -- v1.0
- ✓ Configurable search queries and platform selection -- v1.0
- ✓ Debug screenshot capture on selector failure -- v1.0
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
- ✓ CLI-01: Claude CLI subprocess with structured output -- v1.2
- ✓ CLI-02: CLI error handling (timeout, exit code, JSON, auth, not installed) -- v1.2
- ✓ CLI-03: Typed Pydantic models from structured_output with resilient parser -- v1.2
- ✓ RES-01: Resume tailoring via Claude CLI (not Anthropic SDK) -- v1.2
- ✓ RES-02: Resume tailoring SSE progress events -- v1.2
- ✓ RES-03: Anti-fabrication validation on CLI output -- v1.2
- ✓ RES-04: PDF rendering and version tracking unchanged -- v1.2
- ✓ COV-01: Cover letter via Claude CLI (not Anthropic SDK) -- v1.2
- ✓ COV-02: Cover letter SSE progress events -- v1.2
- ✓ COV-03: Cover letter PDF rendering and version tracking unchanged -- v1.2
- ✓ SCR-01: On-demand AI rescore from job detail page -- v1.2
- ✓ SCR-02: AI scoring with full resume + job description context -- v1.2
- ✓ SCR-03: AI score, reasoning, strengths, gaps stored and displayed -- v1.2
- ✓ CFG-01: Anthropic SDK removed from runtime dependencies -- v1.2
- ✓ CFG-02: Documentation updated for Claude CLI prerequisite -- v1.2
- ✓ SETUP-01..05: Astro v5 project with Tailwind v4, design tokens, BaseLayout, SEO meta -- v1.3
- ✓ CONT-01..09: 9 content sections (Hero, Stats, Features, TechStack, Architecture, Code, Timeline, QuickStart, Footer) -- v1.3
- ✓ DSGN-01..04: Professional palette, responsive design, dark mode, ScreenshotFrame -- v1.3
- ✓ DPLY-01..04: GitHub Actions deploy, path isolation, CI separation, production deployment -- v1.3
- ✓ SEO-01..04: OpenGraph, Twitter Card, JSON-LD, sitemap -- v1.3
- ✓ PLSH-01..03: Terminal animation, scroll fade-ins, smooth scroll NavBar -- v1.3

### Active

(None -- define in next milestone via `/gsd:new-milestone`)

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

**v1.2 shipped:** 2026-02-11. 4 phases, 7 plans, 15 requirements. Replaced Anthropic SDK with Claude CLI subprocess for all AI features. Added on-demand AI scoring, SSE streaming for resume/cover letter. 18 new tests (563 -> 581). Zero production files import anthropic SDK.

**v1.3 shipped:** 2026-02-13. 5 phases, 10 plans, 21 tasks. GitHub Pages showcase site built with Astro v5 + Tailwind v4 in `/site`. 9 responsive content sections, animated terminal demo, dark mode, scroll animations, path-isolated CI/CD. Deployed at patrykquantumnomad.github.io/jobs/.

**Tech stack:** Python 3.14, Playwright + playwright-stealth, FastAPI + Jinja2 + htmx, SQLite (FTS5), pydantic-settings + YAML, Claude CLI (subprocess with structured output), WeasyPrint, sse-starlette, Chart.js, SortableJS, pytest + factory-boy + respx + pytest-playwright | Site: Astro v5, Tailwind v4, @fontsource, @astrojs/sitemap, Shiki

**Codebase:** ~19,100 LOC (16,258 Python + 1,764 HTML + 1,113 Astro/CSS/SVG). 581 automated tests. Site: 41 files, 1,113 LOC.

**Known technical debt:**
- CDN-loaded JS libraries (htmx, Chart.js, SortableJS) rather than bundled
- Lazy imports could be replaced with proper dependency injection
- ATS form fill covers 5 providers (Greenhouse, Lever, Ashby, BambooHR, Workday) but needs broader coverage
- 4 analytics routes lack integration tests
- SSE endpoint testing relies on background task testing pattern (direct Queue testing), not actual SSE stream parsing
- scorer.py score_batch_with_breakdown uncovered (8 lines)
- ScreenshotFrame.astro unused in production (replaced by TerminalDemo, kept for future screenshots)
- Site uses placeholder gradient in ScreenshotFrame instead of real dashboard screenshots

## Constraints

- **Tech stack**: Python 3.14, Playwright, FastAPI -- established and working, no reason to change
- **Single user**: All design decisions assume one user per installation. No auth layer needed.
- **Anti-detection**: Must maintain stealth browser approach. System Chrome, no automation flags.
- **Human-in-the-loop**: Application submission always requires human approval (even in "auto" mode, there's an approve step)
- **Credentials**: Always from .env, never committed. Platform credentials stay separate from user profile config.
- **Test coverage**: Maintain 80%+ coverage. All new features must include tests.
- **AI runtime**: Claude CLI must be installed. AI features use subprocess invocation, not SDK API calls.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| pydantic-settings with YAML config | Clean, validated, type-safe configuration | ✓ Good |
| Protocol-based platform architecture | More Pythonic than ABC, easier to test and extend | ✓ Good |
| Three apply modes (auto/semi/manual) | Different comfort levels for different job types | ✓ Good |
| Claude CLI for AI (not Anthropic SDK) | Runs on user's subscription, no per-token API costs, structured output via --json-schema | ✓ Good |
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
| asyncio.create_subprocess_exec for CLI | Enables streaming, cleaner than to_thread(subprocess.run) | ✓ Good |
| Resilient JSON parser for CLI output | Handles structured_output and result field regression transparently | ✓ Good |
| AI scores as columns on jobs table | Simpler than separate table, score is 1:1 with job | ✓ Good |
| Queue + background task for SSE | Established pattern from apply_engine, consistent across all SSE features | ✓ Good |
| CLIError -> RuntimeError at boundary | Backward compatibility with webapp's generic exception handler | ✓ Good |
| Single-module ai_scorer.py | Feature is small enough, parallels existing scorer.py | ✓ Good |

| Astro for site (not Starlight) | Marketing-forward, not docs-heavy; custom components over framework constraints | ✓ Good |
| Same-repo /site folder | One repo, GitHub Pages from subfolder, simpler maintenance | ✓ Good |
| Blues/grays professional palette | Unique identity distinct from personal site (orange) and networking-tools (dark orange) | ✓ Good |
| Tailwind v4 CSS-first @theme tokens | No tailwind.config.js needed, OKLCH for perceptual uniformity | ✓ Good |
| data-theme attribute for dark mode | Tailwind v4 @custom-variant requires CSS selector, data attributes more semantic | ✓ Good |
| Path-based CI workflow isolation | site/** triggers deploy, Python CI ignores site/** -- no unnecessary builds | ✓ Good |
| IntersectionObserver for animations | Zero-dependency, fire-once, prefers-reduced-motion support built-in | ✓ Good |
| .js-enabled CSS gate | Progressive enhancement: content visible without JS, animations are additive | ✓ Good |

---
*Last updated: 2026-02-13 after v1.3 milestone*
