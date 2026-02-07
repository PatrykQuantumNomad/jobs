# Project Research Summary

**Project:** Job Search Automation (Milestone 2)
**Domain:** Self-hosted job search automation with AI-powered resume tailoring
**Researched:** 2026-02-07
**Confidence:** HIGH

## Executive Summary

This project is a working job search automation tool that scrapes Indeed, Dice, and RemoteOK, scores jobs against a candidate profile, and provides semi-automated application submission. The codebase already has a complete discovery-to-application pipeline with a web dashboard. Milestone 2 focuses on making it a daily driver tool and portfolio-worthy through externalized configuration, AI-powered resume tailoring, and enhanced dashboard capabilities.

The research reveals a well-structured monolithic architecture ready for selective evolution. The critical path is: externalize configuration (YAML replaces hardcoded Python), build platform registry for extensibility, add AI resume tailoring with strict anti-hallucination guardrails, and connect the dashboard to the orchestrator via server-sent events. The top pitfall is account bans from behavioral fingerprinting - technical anti-detection exists but behavioral modeling (rate limiting, randomized timing, session variation) is critical before any automated submissions.

Key recommendation: build foundation components first (platform registry, YAML config), then add daily-driver features (scheduled runs, new job detection, dashboard search), then AI capabilities. Avoid over-engineering the plugin system - three platforms do not justify elaborate infrastructure. Avoid fully autonomous mass-apply - human-in-the-loop is non-negotiable for reputation protection.

## Key Findings

### Recommended Stack

The existing stack (Playwright, FastAPI, Pydantic v2, htmx, SQLite) is solid. New dependencies focus on AI integration and configuration management rather than replacing working components.

**Core additions:**
- **anthropic (>=0.78.0)**: Resume tailoring, intelligent scoring, cover letter generation - user already has Claude Code access, no need for OpenAI abstraction
- **PyMuPDF (>=1.26.7)**: Extract text from PDF resumes for AI processing - fastest Python PDF extractor with good structure preservation
- **weasyprint (>=68.1)**: Generate tailored PDFs from HTML templates - integrates with existing Jinja2 skills, produces ATS-parseable output
- **pydantic-settings[yaml] (>=2.12.0)**: Type-safe YAML config with env override - extends existing Pydantic usage, replaces hardcoded Config class
- **Alpine.js (3.15 CDN)**: Client-side interactivity (dropdowns, modals) - complements existing htmx without build step

**Explicitly NOT recommended:**
- LangChain/LangGraph: massive dependency tree for single-prompt resume tailoring use case
- OpenAI SDK: adding second LLM provider doubles config surface with no benefit
- SQLAlchemy: 5 queries in SQLite does not justify ORM overhead
- React/Vue/Svelte: htmx + Alpine achieves same result without build tooling

### Expected Features

The system already works end-to-end. Next milestone makes it usable daily and portfolio-impressive.

**Must have (table stakes):**
- YAML configuration file - every self-hosted tool has this, currently hardcoded in Python
- Scheduled/recurring runs - manual CLI defeats automation purpose
- New job detection (delta awareness) - scheduled runs useless without knowing what is new
- Dashboard text search - basic expectation for 100+ item lists
- Company blacklist - extremely common need ("never show Infosys again")
- Bulk status actions - triaging 100 jobs with 100 clicks is painful

**Should have (competitive differentiators):**
- AI resume tailoring per application - flagship feature, demonstrates AI/ML integration
- Kanban board view - visually impressive, primary view in competitors like Huntr
- Scoring explanation - transparency ("why 4/5: title match +2, tech overlap +2...")
- Application funnel analytics - conversion visualization, time-in-stage metrics
- One-click apply from dashboard - brings automation into web UI

**Defer (v2+):**
- Company research enrichment (Glassdoor ratings, funding) - high complexity, unclear ROI
- Smart LLM scoring - current keyword scoring works, LLM is expensive/slow for 100+ jobs
- AI chatbot/conversational interface - chat UI wrong paradigm for data management
- Contact/networking CRM - separate problem domain from job search automation

**Anti-features (never build):**
- Fully autonomous mass-apply - ATS blacklists shared across platforms, destroys reputation
- CAPTCHA/Cloudflare bypass - arms race that cannot be won, results in bans
- LinkedIn integration - most aggressive anti-automation detection, too important to risk
- Multi-user features - single-user tool, no auth/RBAC overhead needed

### Architecture Approach

Current architecture is a clean monolith with BasePlatform ABC, isolated selectors, and phase-based pipeline. Evolution path: selective refactoring for extensibility, not rewriting working code.

**Major components:**

1. **AppSettings (pydantic-settings)** - Load config from TOML + .env + env vars with type validation, replaces hardcoded Config class
2. **Platform Registry** - Auto-discover platform adapters via decorator + pkgutil, eliminates if/elif branching in orchestrator
3. **Dual Platform Protocols** - Separate BrowserPlatform (Playwright) from APIPlatform (httpx) protocols, both feed same pipeline
4. **Apply Engine with Mode Awareness** - Three modes: auto (fill+submit), semi-auto (fill+confirm), manual (open URL only)
5. **AI Resume Tailorer** - LLM-based tailoring with strict anti-fabrication guardrails: diff output vs input, structured JSON response, human review checkpoint
6. **Dashboard with SSE** - FastAPI SSE events for real-time pipeline updates, htmx frontend receives status, triggers actions

**Key architectural decisions:**
- SQLite becomes single source of truth (no dual JSON + DB storage)
- Make RemoteOK synchronous (httpx supports sync) - entire pipeline synchronous simplifies debugging
- Separate SearchPlatform from ApplyHandler - job discovered on RemoteOK applies via Greenhouse/Lever
- Use Protocols not abstract base classes - implementations match interface without inheritance
- Platform registry via decorator + pkgutil - simpler than entry_points for single-repo project

### Critical Pitfalls

Top 5 mistakes that cause rewrites, bans, or render tool useless:

1. **Account ban from behavioral fingerprinting** - Indeed uses anomaly detection on behavioral patterns (uniform timing, identical mouse paths, no scroll variation), not just technical detection. Current human_delay() insufficient. Prevention: rate-limit to 5-10 applications/day, randomize session duration, vary mouse paths with Bezier curves, never apply to 2+ jobs in one browser session. Daily budget with hard enforcement is prerequisite for apply phase.

2. **ATS form diversity overwhelms generic filler** - RemoteOK redirects land on Greenhouse, Lever, Workday, Ashby, custom pages. Each has different DOM, validation, multi-step flows. Current keyword-matching FormFiller handles maybe 30%. Prevention: build explicit handlers for top 5 ATS platforms, use Greenhouse/Lever APIs (documented, stable) where possible, detect ATS from URL patterns, abort if fewer than 3 standard fields identified.

3. **AI resume tailoring fabricates experience** - LLM fills gaps with plausible fabrications ("increased deployment frequency by 340%", "extensive Terraform CDK experience"). Even one hallucinated skill is unacceptable. Prevention: LLM never generates new facts, provide structured source-of-truth CandidateProfile, constrained prompt ("reorder REAL experience, do NOT add"), post-generation diff verification, human review checkpoint showing diff.

4. **Duplicate applications destroy credibility** - Current dedup (company::title) only operates within single run, does not persist. Re-running pipeline re-discovers same jobs. Prevention: query jobs.db for status='applied' before ANY submission, record attempts immediately (not just successes), fuzzy company name normalization (strip "Inc", "LLC"), cross-platform dedup check.

5. **Session expiry mid-application causes phantom submissions** - Session cookies expire server-side during long pipeline runs. Tool clicks submit but form fails silently. Database records "applied" but application never went through. Prevention: check is_logged_in() before each application (not just pipeline start), verify confirmation page loaded after submit, check email for confirmation within 5 minutes.

**Phase-specific warnings:**
- Phase 1 (Apply infrastructure): daily budget and behavioral guardrails are prerequisites before any automated submissions
- Phase 2 (AI tailoring): verification step (diff output vs source) must be built simultaneously with generation, not retrofitted
- Ongoing: selector health checks (verify expected elements exist on known pages) and monitoring (track match rates over time)

## Implications for Roadmap

Based on dependency analysis and pitfall mitigation strategies, suggested phase structure:

### Phase 1: Foundation - Config Externalization + Platform Registry
**Rationale:** Everything depends on these. Configuration currently hardcoded makes tool unusable by new users (must edit Python source). Platform registry eliminates if/elif branching, enables adding platforms/ATS handlers without touching orchestrator.

**Delivers:**
- YAML config file (config.toml) for candidate profile, search queries, platform settings, timing parameters
- pydantic-settings-based AppSettings loading TOML + .env + env vars
- Platform registry with decorator auto-discovery (platforms/__init__.py)
- Dual protocols for BrowserPlatform vs APIPlatform
- Single source of truth: SQLite (orchestrator writes directly to DB, JSON becomes optional export)

**Addresses:** T1 (YAML config) from features research - blocks T7 (company blacklist), D1 (resume tailoring), D7 (apply modes)

**Avoids:** Pitfall 11 (config drift) - single source of truth for candidate data

**Research flag:** Standard pattern (pydantic-settings documented, registry pattern well-known) - no additional research needed

---

### Phase 2: Daily Driver - Scheduled Runs + Delta Detection + Dashboard Polish
**Rationale:** Makes tool practical for daily use. Without scheduled runs and new job detection, manual CLI defeats automation purpose. Without dashboard search/bulk actions, triaging 100+ jobs is painful.

**Delivers:**
- Scheduled pipeline runs (cron/systemd/launchd integration or built-in scheduler)
- New job detection (track seen jobs, highlight delta since last run in dashboard)
- Dashboard text search across title/company/description
- Bulk status actions (select multiple jobs, mark all as skipped/rejected)
- Company blacklist (config.yaml list, filter during search phase)
- Richer application status workflow (9 statuses: saved, applied, phone screen, technical, final, offer, rejected, withdrawn, ghosted)
- Activity log per job (status changes, notes added, discovery/apply timestamps)

**Addresses:** T2 (scheduled runs), T3 (new job detection), T4 (text search), T7 (blacklist), T9 (bulk actions), T5 (richer workflow), T6 (activity log)

**Dependencies:** Phase 1 (needs config system, DB as single source of truth)

**Avoids:** Pitfall 4 (duplicate applications) - delta detection prevents re-applying to same jobs

**Research flag:** Standard patterns (cron integration, SQLite delta queries) - no additional research needed

---

### Phase 3: Apply Engine + Behavioral Guardrails
**Rationale:** Makes application submission production-ready with anti-ban protections. Must be built before any automated submissions to avoid account bans.

**Delivers:**
- ApplyEngine with mode awareness (auto/semi-auto/manual)
- Mode resolution (external ATS always manual, non-Easy Apply degrades to semi-auto)
- Daily application budget enforcement (5-10/day hard limit in orchestrator)
- Behavioral variation (randomize session duration, mouse path Bezier curves, idle periods)
- Session health checks (is_logged_in before each apply, verify confirmation page after submit)
- Duplicate detection (pre-apply DB check, fuzzy company normalization, cross-platform dedup)
- Apply status tracking (applying -> applied/apply_failed, immediate recording)

**Addresses:** D7 (apply modes) from features research

**Dependencies:** Phase 1 (needs platform registry, config for mode selection), Phase 2 (needs activity log for status tracking)

**Avoids:** Pitfall 1 (behavioral fingerprinting ban), Pitfall 4 (duplicates), Pitfall 5 (session expiry)

**Research flag:** HIGH PRIORITY - ATS-specific handlers (Greenhouse API, Lever API documented; Workday/Ashby need DOM analysis). Likely needs /gsd:research-phase for each major ATS platform.

---

### Phase 4: AI Resume Tailoring
**Rationale:** Flagship differentiator, demonstrates AI/ML integration. Built last because it is additive (does not block other features) and optional (ai.enabled = false by default).

**Delivers:**
- anthropic SDK integration for resume tailoring
- PyMuPDF text extraction from base resume PDF
- Resume tailoring prompt with anti-fabrication constraints (reorder REAL experience, no new facts)
- Structured JSON response (summary, skills_to_highlight, experience_order)
- Post-generation verification (diff output vs CandidateProfile, flag new skills/metrics)
- Human review checkpoint (show diff before any submission)
- weasyprint PDF generation from Jinja2 template + tailored content
- ATS-safe PDF validation (single-column, standard fonts, no tables, contact in body)
- Dashboard trigger button ("Tailor Resume" per job, async action)

**Addresses:** D1 (AI resume tailoring) - flagship feature

**Dependencies:** Phase 1 (needs config for LLM provider/model), standalone otherwise

**Avoids:** Pitfall 3 (fabricated experience - strict verification), Pitfall 8 (PDF fails ATS parsing - validation), Pitfall 9 (LLM cost explosion - caching, tiered models)

**Research flag:** MEDIUM - weasyprint + Jinja2 pattern documented; prompt engineering for quality tailoring needs iteration and testing

---

### Phase 5: Dashboard SSE + Pipeline Trigger + Kanban Board
**Rationale:** Connects dashboard to orchestrator, makes it command center not just viewer. Kanban board is visually impressive for portfolio presentation.

**Delivers:**
- FastAPI SSE endpoint (/events) with pipeline event bus
- htmx SSE integration on frontend (real-time status updates)
- Dashboard API to trigger pipeline (POST /api/pipeline/run starts orchestrator in background)
- Kanban board view with drag-and-drop status changes (columns = application stages)
- One-click apply from dashboard (triggers ApplyEngine for single job)
- Config editor UI (view/edit config.toml from dashboard)
- Enhanced stats (jobs per day/week, response rate, time-in-stage, platform effectiveness)
- Application funnel analytics (discovered -> applied -> phone -> offer conversion visualization)

**Addresses:** D3 (kanban board), D10 (one-click apply from dashboard), T11 (enhanced stats), D4 (funnel analytics)

**Dependencies:** Phase 2 (needs activity log for time-in-stage), Phase 3 (needs ApplyEngine for dashboard-triggered apply)

**Avoids:** None directly - this is polish/UX enhancement

**Research flag:** LOW - sse-starlette + htmx SSE pattern documented; kanban drag-drop with htmx is well-known pattern

---

### Phase Ordering Rationale

- **Phase 1 first** because config externalization and platform registry are foundational - every other component needs them
- **Phase 2 before Phase 3** because scheduled runs + delta detection provide the job stream for apply engine; also avoids building apply automation when discovery is still manual CLI
- **Phase 3 before Phase 4** because apply engine with guardrails must be production-ready before adding AI complexity; also AI-tailored resumes need apply infrastructure to be useful
- **Phase 4 standalone** because AI is optional additive feature - does not block anything, can be built in parallel with Phase 5
- **Phase 5 last** because it is polish/UX enhancement requiring mature pipeline (dashboard triggering orchestrator only makes sense when orchestrator is robust)

**Dependency critical path:** Phase 1 (config + registry) -> Phase 2 (scheduled discovery) -> Phase 3 (apply engine) -> Phase 5 (dashboard integration). Phase 4 (AI) branches off Phase 1 and can be built anytime after.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (Apply Engine):** Each major ATS platform (Greenhouse, Lever, Workday, Ashby) needs DOM analysis or API documentation review. Likely trigger /gsd:research-phase per ATS to identify selectors, multi-step flows, validation patterns.
- **Phase 4 (AI Resume Tailoring):** Prompt engineering for quality tailoring needs iteration. May trigger targeted research on ATS parsing validation techniques and anti-hallucination prompt patterns.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** pydantic-settings, platform registry via decorator pattern - both well-documented
- **Phase 2 (Daily Driver):** cron integration, SQLite delta queries, dashboard CRUD - standard web app patterns
- **Phase 5 (Dashboard SSE):** sse-starlette + htmx SSE documented; kanban drag-drop with htmx is established pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended packages verified on PyPI with recent versions (anthropic 0.78.0 Feb 5, weasyprint 68.1 Feb 6). pydantic-settings YAML support confirmed in official docs. Alpine.js 3.15 stable. |
| Features | HIGH | Based on existing codebase review (working end-to-end pipeline) + competitive landscape survey (Huntr, AIHawk, JobSync). Feature priorities grounded in table-stakes expectations vs differentiators. |
| Architecture | HIGH | Grounded in direct analysis of existing codebase (base.py, orchestrator.py, models.py). Patterns (platform registry, pydantic-settings, SSE) are well-documented with verified examples. |
| Pitfalls | HIGH | Top pitfalls verified against Indeed DSA report (behavioral detection), Greenhouse/Lever API docs (ATS diversity), published hallucination research (LLM fabrication), and direct codebase analysis (dedup logic, session handling). |

**Overall confidence:** HIGH

### Gaps to Address

**Minor gaps that need attention during implementation:**

- **ATS selector maintenance:** Indeed/Dice selectors already documented as requiring frequent updates (MEMORY.md shows multiple selector changes). Phase 3 needs selector health checks and monitoring. Not a research gap - an operational reality.

- **Behavioral fingerprinting specifics:** Indeed's anomaly detection methods are proprietary (not public). Prevention strategies (rate limiting, randomized timing, session variation) are based on industry best practices and competitor analysis (Wonsulting shutdown data), not direct verification of Indeed's exact algorithm. Implement conservatively and monitor for ban signals.

- **LLM prompt quality:** Resume tailoring prompt engineering needs iteration and testing with real job descriptions. Initial prompt constraints (no new facts, structured output, source-of-truth) are sound, but quality/tone may need refinement. Plan for prompt iteration in Phase 4.

- **Workday DOM structure:** Workday uses Web Components (Shadow DOM) which are harder to scrape than standard DOM. Phase 3 ATS research may find Workday requires different Playwright approaches (execute_script to access shadowRoot). Flag for deeper investigation during Phase 3 planning.

- **PDF ATS parsing validation:** Recommendations (single-column, standard fonts, no tables) are based on ATS best practices from multiple sources, but actual ATS parsing behavior varies by vendor and version. Build validation step (extract text with PyPDF2, verify content order) but expect edge cases.

## Sources

### Primary (HIGH confidence)
- **Existing codebase:** Direct analysis of base.py, orchestrator.py, models.py, db.py, form_filler.py, stealth.py, indeed_selectors.py, dice_selectors.py - confirms current architecture, gaps, and extension points
- [anthropic on PyPI](https://pypi.org/project/anthropic/) - v0.78.0 (Feb 5, 2026)
- [PyMuPDF on PyPI](https://pypi.org/project/PyMuPDF/) - v1.26.7
- [WeasyPrint on PyPI](https://pypi.org/project/weasyprint/) - v68.1 (Feb 6, 2026)
- [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/) - v2.12.0
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - YamlConfigSettingsSource confirmed
- [Alpine.js](https://alpinejs.dev/) - v3.15.x
- [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html) - application submission endpoints
- [Lever Postings API](https://github.com/lever/postings-api) - public application API
- [Python Packaging Guide: Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) - registry pattern
- [fastapi-sse-htmx Example](https://github.com/vlcinsky/fastapi-sse-htmx) - SSE + htmx integration
- [Playwright persistent context issues](https://github.com/microsoft/playwright/issues/36139) - session cookie bugs

### Secondary (MEDIUM confidence)
- [JobSync GitHub](https://github.com/Gsync/jobsync) - self-hosted job tracker feature reference
- [AIHawk GitHub](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) - auto-apply architecture, YAML config patterns
- [Huntr](https://huntr.co/) - kanban board UX, autofill features
- [Loopcv](https://www.loopcv.pro/) - auto-apply loop concept, scheduling
- [GrackerAI: AI Job Automation 2025](https://gracker.ai/blog/ai-job-apply-bots-2025) - Wonsulting shutdown, application rate data
- [Resumly: ATS PDF Formatting](https://www.resumly.ai/blog/formatting-resume-pdfs-best-practices-to-avoid-ats-errors) - PDF pitfalls
- [ScrapeOps: Make Playwright Undetectable](https://scrapeops.io/playwright-web-scraping-playbook/nodejs-playwright-make-playwright-undetectable/) - behavioral fingerprinting
- [Vectara hallucination study](https://medium.com/@markus_brinsa/hallucination-rates-in-2025-accuracy-refusal-and-liability-aa0032019ca1) - LLM hallucination rates

### Tertiary (LOW confidence - needs validation)
- Indeed DSA transparency report claim about "anomaly detection and machine learning" for bot detection - report exists but specific methods not public
- Workday "loses more than half of content" during PDF parsing - single source (Resumly), may be version/config dependent

---

*Research completed: 2026-02-07*
*Ready for roadmap: yes*
