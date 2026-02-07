# Feature Landscape

**Domain:** Self-hosted single-user job search automation (scraping, scoring, application, tracking)
**Researched:** 2026-02-07
**Overall confidence:** HIGH (based on existing codebase review + competitive landscape survey)

---

## Current State (What Already Exists)

Before mapping features, here is what the codebase already has:

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-platform scraping (Indeed, Dice, RemoteOK) | Built | 3 platforms, 20 search queries |
| Keyword-based scoring (1-5) | Built | Title + tech + location + salary |
| Deduplication | Built | Cross-platform by company::title |
| Web dashboard (list view) | Built | FastAPI + htmx + SQLite |
| Filtering (score, platform, status) | Built | Dashboard filters |
| Job detail page | Built | Description, tags, status, notes |
| Status management | Built | 6 statuses: discovered/scored/approved/applied/rejected/skipped |
| Notes per job | Built | Free-text notes with htmx save |
| Form filler | Built | Heuristic field matching, never auto-submits |
| Easy Apply detection | Built | Indeed + Dice |
| CLI pipeline | Built | --platforms, --headed flags |
| Import from pipeline to dashboard | Built | JSON to SQLite upsert |

**Key gaps visible from competitor analysis:** No scheduled runs, no kanban view, no analytics/funnel, no resume tailoring, no company blacklist/whitelist, no YAML config (hardcoded in Python), no application history timeline, no bulk actions, no search text filtering in dashboard.

---

## Table Stakes

Features users expect from a job search automation tool. Missing any of these makes the tool feel incomplete for its stated purpose ("from discovery to application in one tool").

| # | Feature | Why Expected | Complexity | Dependencies | Currently |
|---|---------|-------------|------------|--------------|-----------|
| T1 | **YAML configuration file** | Every self-hosted tool uses a single config file. Currently profile, queries, and settings are hardcoded in Python classes. A `config.yaml` that owns search queries, candidate profile, platform credentials path, scoring weights, and timing parameters is the entry point for any new user. | Low | None | Hardcoded in config.py + models.py |
| T2 | **Scheduled/recurring runs** | Manual `python orchestrator.py` every time defeats the purpose. Users expect daily automated scraping with new-job detection so they see fresh results without remembering to run the tool. Cron/systemd/launchd integration or built-in scheduler. | Low | None | Manual CLI only |
| T3 | **New job detection (delta awareness)** | Running the pipeline again should surface NEW jobs, not re-show everything. Requires tracking what has been seen before and highlighting what is new since last run. | Medium | T2 (scheduled runs), existing DB | No concept of "seen before" vs "new" |
| T4 | **Dashboard text search** | Filtering by score/platform/status exists, but no way to search by keyword across title, company, or description. Basic expectation for any list of 100+ items. | Low | None | Not implemented |
| T5 | **Richer application status workflow** | 6 statuses exist but miss key stages. Standard: Saved/Wishlist, Applied, Phone Screen, Technical Interview, Final Interview, Offer, Rejected, Withdrawn, Ghosted. Users track where each application stands in the hiring funnel. | Low | None | 6 flat statuses |
| T6 | **Application history/activity log** | When status changes, when notes were added, when job was first discovered, when applied. A timeline per job. Without this, there is no record of what happened when. | Medium | Existing DB schema change | Not implemented |
| T7 | **Company blacklist** | "Never show me jobs from Infosys/Wipro/Cognizant again." Extremely common need. List of companies to permanently exclude from results. | Low | T1 (YAML config) | Not implemented |
| T8 | **Duplicate detection improvement** | Current dedup by `company::title` is naive. Same job posted under slightly different titles or company name variations (e.g., "Google" vs "Google LLC" vs "Alphabet") needs fuzzy matching. | Medium | None | Basic exact-match dedup |
| T9 | **Bulk status actions in dashboard** | Select multiple jobs, mark all as "skipped" or "rejected" at once. Without this, triaging 100 jobs requires 100 individual clicks. | Low | None | Single-job status updates only |
| T10 | **Export/backup** | Export filtered results to CSV/JSON. Single-user tool with SQLite -- if the DB corrupts, everything is lost. Also useful for sharing results or importing elsewhere. | Low | None | Raw JSON files exist but no export from dashboard |
| T11 | **Dashboard stats enhancement** | Current stats show counts by score/status/platform. Missing: jobs added per day/week, response rate, time-in-stage, platform effectiveness. These are basic analytics every tracker shows. | Medium | T6 (activity log for time tracking) | Basic count stats only |
| T12 | **Salary normalization** | Dice formats salary as "USD 224,400.00 - 283,800.00 per year", RemoteOK has int fields, Indeed is inconsistent. Normalize all to comparable USD annual figures for proper filtering and sorting. | Medium | None | Mixed formats, partial normalization |

---

## Differentiators

Features that set this tool apart from competitors and make it portfolio-worthy. Not expected, but demonstrate engineering depth and practical value.

| # | Feature | Value Proposition | Complexity | Dependencies | Portfolio Value |
|---|---------|-------------------|------------|--------------|-----------------|
| D1 | **AI-powered resume tailoring per application** | Generate a tailored resume for each job by analyzing the job description against the candidate profile, adjusting keyword emphasis, reordering skills, and generating a targeted professional summary. This is what AIHawk and commercial tools charge for. Using local LLM (Ollama) or API (OpenAI/Anthropic) to keep it self-hosted. | High | T1 (config for LLM settings), resume template system | Very High -- demonstrates AI/ML chops |
| D2 | **AI cover letter generation** | Generate a targeted cover letter per application using job description + candidate profile + company research. Paired with D1, this creates a complete "tailored application package" per job. | Medium | D1 (same LLM infrastructure) | High |
| D3 | **Kanban board view** | Drag-and-drop visual board with columns for each application stage. This is the primary view in Huntr, Trello-for-jobs, and every serious tracker. Visual pipeline management is immediately impressive in a portfolio demo. | Medium | T5 (richer status workflow) | High -- visually impressive |
| D4 | **Application funnel analytics** | Conversion funnel visualization: Discovered -> Applied -> Phone Screen -> Technical -> Offer. Shows drop-off rates at each stage. Combined with time-in-stage metrics, this gives genuine insight into job search effectiveness. | Medium | T5, T6, T11 | High -- data visualization |
| D5 | **Smart scoring with LLM** | Current scoring is keyword-matching. LLM-based scoring could deeply analyze job description vs. candidate profile for semantic fit -- understanding that "container orchestration" means Kubernetes even if the word is not mentioned. | High | T1 (config for LLM) | High -- AI differentiator |
| D6 | **Notification system** | After scheduled run, notify via email, Slack, or desktop notification about new high-scoring jobs. "You have 3 new score-5 jobs since yesterday." Transforms passive dashboard into active assistant. | Medium | T2 (scheduled runs), T3 (new job detection) | Medium |
| D7 | **Application automation modes** | Three configurable modes: (1) Full-auto with human approval checkpoint, (2) Semi-auto (fill forms, pause before submit), (3) Easy Apply only (safest). Currently mode 2 exists partially. Making this a first-class configurable feature with clear UX is differentiating. | Medium | T1 (config), existing form_filler.py | Medium |
| D8 | **Company research enrichment** | Before applying, auto-fetch company info: Glassdoor rating, employee count, funding stage, tech stack from StackShare/BuiltWith. Show this on the job detail page to help make apply/skip decisions. | High | External API integrations | High -- shows integration skills |
| D9 | **Job description diff/change tracking** | If the same job listing changes its description between scraping runs, highlight what changed. Detects salary updates, requirement changes, and reposted-with-edits. | Medium | T3 (delta awareness) | Medium |
| D10 | **One-click apply from dashboard** | "Apply" button on job detail page that triggers the browser automation apply flow (with human-in-the-loop confirmation). Currently apply only works from CLI Phase 4. Bringing it into the web dashboard makes it a real product. | High | Existing apply infrastructure, WebSocket or polling for status updates | Very High -- end-to-end in one UI |
| D11 | **Scoring explanation** | Show WHY a job scored 4/5: "Title match: Staff Engineer (+2), Tech overlap: kubernetes, terraform, python, langchain, grafana (+2), Remote (+1), Salary $220K-280K meets $200K+ target (+1) = 6 raw -> Score 5." Transparency in scoring builds trust and is portfolio-worthy. | Low | None (scorer already has the data) | Medium |
| D12 | **Multi-resume management** | Dashboard for managing multiple resume versions (ATS, standard, per-company tailored). Track which resume was sent to which company. Currently just file paths in config. | Medium | D1 (resume tailoring) | Medium |

---

## Anti-Features

Features to deliberately NOT build. Common mistakes in this domain that waste effort, create risk, or add complexity without value for a single-user self-hosted tool.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|-------------|-----------|-------------------|
| A1 | **Fully autonomous mass-apply (spray-and-pray)** | ATS systems flag mass-submitted applications. Employers share blacklists across shared ATS platforms. Getting flagged at one company can blacklist you across all companies using the same ATS (Greenhouse, Lever, Workday). The 2025 applicant-to-interview ratio is 3% for mass appliers vs. 14x better for strategic applicants. This destroys the candidate's reputation. | Keep human-in-the-loop as non-negotiable. Modes should be "fill + pause" or "Easy Apply with confirmation", never "fire and forget 500 applications." |
| A2 | **CAPTCHA/Cloudflare bypass or solving** | Arms race that you will lose. CAPTCHA solving services are legally grey. Getting caught means permanent platform bans. Indeed already has aggressive fingerprinting and behavioral analysis. | Detect CAPTCHA, screenshot, notify human. Manual intervention for auth challenges. This is already the correct approach in the codebase. |
| A3 | **Multi-user/team features** | This is a personal tool. Auth, RBAC, multi-tenant data isolation, shared dashboards -- all add massive complexity for zero value. Single-user means no login screen needed. | Keep single-user. No auth on localhost dashboard. If someone wants multi-user, they fork the project. |
| A4 | **LinkedIn integration** | LinkedIn has the most aggressive anti-automation detection in the industry. Account bans are permanent and devastating for professional networking. LinkedIn is too important to risk automating. | Explicitly exclude LinkedIn. Document why. Users who want LinkedIn automation should use dedicated tools like AIHawk at their own risk. |
| A5 | **Chrome extension for job saving** | Building and maintaining a browser extension is a separate product. Cross-browser compatibility, Chrome Web Store publishing, extension manifest updates, content script injection -- all tangential to the core tool. | Keep it server-side. The scraping pipeline + dashboard is the product. Manual URL paste for one-off job additions if needed. |
| A6 | **Mobile app / PWA** | Native mobile or PWA adds build complexity (iOS/Android or service workers, push notifications, offline sync) for minimal gain. Job applications happen at a desk. | Responsive dashboard (already using Tailwind) is sufficient for occasional phone checks. |
| A7 | **AI chatbot / conversational interface** | "Ask your job search assistant" sounds cool but adds LLM latency to every interaction, costs money per query, and is slower than clicking a filter. Chat UI is not the right paradigm for data management. | Use LLM where it adds clear value: resume tailoring, scoring, cover letters. Not as a UI layer. |
| A8 | **Contact/networking CRM** | Huntr has this but it is a separate problem domain. Tracking recruiter conversations, follow-up reminders, LinkedIn connections -- this is CRM software, not job search automation. | Focus on the job listing lifecycle only. Notes field on each job is sufficient for recruiter context. |
| A9 | **Payment/subscription features** | This is an open-source portfolio project. Monetization adds Stripe integration, billing logic, feature gating -- all tangential to the core purpose. | Keep it free and open source. The portfolio value IS that it is free and well-built. |
| A10 | **Real-time collaborative editing** | WebSocket-based real-time updates for multiple users editing the same job. Single user tool -- no collaboration needed. | htmx partial updates on single-user actions are sufficient and already in place. |

---

## Feature Dependencies

```
T1 (YAML Config) ─────────────────────────────────────┐
  |                                                     |
  ├── T7 (Company Blacklist) -- reads from config       |
  |                                                     |
  ├── D1 (Resume Tailoring) -- LLM config               |
  |   └── D2 (Cover Letter) -- same LLM infra           |
  |   └── D12 (Multi-Resume Mgmt) -- resume paths       |
  |                                                     |
  ├── D5 (Smart Scoring) -- LLM config                  |
  |                                                     |
  └── D7 (Apply Modes) -- mode selection in config      |

T2 (Scheduled Runs) ──────────────────────────────────┐
  |                                                     |
  ├── T3 (New Job Detection) -- requires run history    |
  |   └── D9 (Description Diff) -- requires prev state  |
  |                                                     |
  └── D6 (Notifications) -- after scheduled run         |

T5 (Richer Status Workflow) ──────────────────────────┐
  |                                                     |
  ├── D3 (Kanban Board) -- columns = statuses           |
  |                                                     |
  └── T6 (Activity Log) -- status change tracking       |
      |                                                 |
      ├── T11 (Enhanced Stats) -- time-in-stage data    |
      |                                                 |
      └── D4 (Funnel Analytics) -- conversion rates     |

No Dependencies (can be built independently):
  - T4 (Dashboard Text Search)
  - T8 (Fuzzy Dedup)
  - T9 (Bulk Actions)
  - T10 (Export/Backup)
  - T12 (Salary Normalization)
  - D8 (Company Research)
  - D10 (One-Click Apply from Dashboard)
  - D11 (Scoring Explanation)
```

---

## MVP Recommendation (Next Milestone)

The system already works end-to-end: scrape, score, view, apply. The next milestone should focus on making it **usable as a daily driver** and **portfolio-presentable**.

### Priority 1: Daily Driver (must-haves to use this tool every day)

1. **T1 - YAML configuration** -- Unblocks everything. New users cannot use the tool without editing Python source files. Single `config.yaml` replaces hardcoded profile, queries, and settings.
2. **T2 - Scheduled runs** -- Without this, the tool requires manual invocation. Even a simple cron-based approach (run pipeline, import to DB) makes it practical.
3. **T3 - New job detection** -- Without this, scheduled runs are useless because you cannot tell which jobs are new.
4. **T7 - Company blacklist** -- Without this, the same garbage results clog the dashboard run after run.
5. **T4 - Dashboard text search** -- Without this, finding a specific job in 100+ results requires scrolling.
6. **T9 - Bulk actions** -- Without this, triaging results after each run is painfully slow.

### Priority 2: Portfolio-worthy (what makes a recruiter say "impressive")

7. **D11 - Scoring explanation** -- Low effort, high impact. Shows transparency and thoughtfulness.
8. **T5 + D3 - Richer workflow + Kanban board** -- Visually impressive, demonstrates frontend competence.
9. **T6 + T11 - Activity log + Enhanced stats** -- Shows data modeling depth.
10. **D1 - AI resume tailoring** -- The flagship differentiator. Demonstrates AI/ML integration with practical output.

### Defer to Post-MVP

- **D8 (Company Research)** -- High complexity, external API dependencies, unclear value for effort
- **D10 (One-Click Apply from Dashboard)** -- Requires WebSocket/polling architecture, high complexity
- **D2 (Cover Letter Generation)** -- Valuable but depends on D1 being solid first
- **D5 (Smart LLM Scoring)** -- Current keyword scoring works. LLM scoring is expensive and slow for 100+ jobs per run
- **D9 (Description Diff)** -- Nice-to-have, rarely actionable

---

## Competitive Landscape Summary

| Tool | Type | Key Features | What We Can Learn |
|------|------|--------------|-------------------|
| **AIHawk** | OSS, Python+Selenium | YAML config, auto-apply LinkedIn, per-job resume generation, LLM-powered question answering | Config-driven approach, resume generation architecture |
| **JobSync** | OSS, Next.js | Self-hosted, AI resume review, job matching, task logging, analytics dashboard | Dashboard UX patterns, analytics layout |
| **Huntr** | SaaS | Kanban board, Chrome extension, autofill, contact CRM, resume builder | Kanban UX, status workflow design |
| **Loopcv** | SaaS | Auto-apply loops, multi-board config, company exclusion, daily automation | Scheduled loop concept, exclusion lists |
| **Simplify** | SaaS + Extension | Autofill across 100+ ATS platforms, job tracking, one-click apply | ATS-specific form handling patterns |
| **Teal** | SaaS | AI resume tailoring, keyword matching, job tracking, analytics | Resume tailoring UX, keyword analysis display |

**Our positioning:** The only self-hosted tool that combines scraping + scoring + apply automation + dashboard in one Python codebase. AIHawk is the closest competitor but focuses on LinkedIn only and has no web dashboard. JobSync has a dashboard but no scraping or auto-apply. We bridge both sides.

---

## Sources

- [JobSync (GitHub)](https://github.com/Gsync/jobsync) -- self-hosted job tracker, feature reference
- [AIHawk (GitHub)](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) -- auto-apply architecture, YAML config pattern
- [Huntr](https://huntr.co/) -- kanban board UX, autofill features, resume tools
- [Loopcv](https://www.loopcv.pro/) -- auto-apply loop concept, scheduling, exclusion filters
- [The Interview Guys: Auto-Apply Bots](https://blog.theinterviewguys.com/auto-apply-job-bots-might-feel-smart-but-theyre-killing-your-chances/) -- anti-pattern research, ATS detection methods
- [Talroo: Fighting Resume Spam](https://www.talroo.com/blog/fighting-resume-spam-in-2025-how-to-identify-low-intent-applications/) -- employer-side detection patterns
- [AiApply](https://aiapply.co) -- resume tailoring feature patterns
- [Built In Job Tracker](https://builtin.com/articles/built-in-job-tracker-kanban-list) -- kanban workflow stages reference
- [Reztune: AI Resume Tailoring Tools 2026](https://www.reztune.com/blog/best-ai-resume-tailoring-2025/) -- resume tailoring landscape
- [ATS Resume Keywords Guide 2026](https://uppl.ai/ats-resume-keywords/) -- keyword optimization best practices
- [12 Best Job Search Tracker Tools](https://aiapply.co/blog/job-search-tracker) -- tracker feature comparison
