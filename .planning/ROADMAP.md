# Roadmap: JobFlow

## Overview

JobFlow has a working discovery-to-scoring pipeline with a web dashboard. This roadmap transforms it from a CLI tool requiring manual invocation into a daily-driver automation platform: externalized configuration so anyone can use it, pluggable platform architecture for extensibility, smarter discovery with delta detection and fuzzy dedup, a polished dashboard with search/kanban/analytics, AI-powered resume tailoring per application, and a capstone one-click apply flow triggered from the web UI. Each phase delivers an independently useful capability building on the foundation before it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Config Externalization** - Single YAML config replaces hardcoded Python settings
- [x] **Phase 2: Platform Architecture** - Pluggable platform registry with auto-discovery
- [ ] **Phase 3: Discovery Engine** - Fuzzy dedup, score breakdowns, salary normalization, new job detection
- [ ] **Phase 4: Scheduled Automation** - Unattended pipeline runs via cron/launchd
- [ ] **Phase 5: Dashboard Core** - Search, extended status workflow, bulk actions, export, activity log
- [ ] **Phase 6: Dashboard Analytics** - Stats, metrics, and kanban board view
- [ ] **Phase 7: AI Resume & Cover Letter** - LLM-powered resume tailoring and cover letter generation
- [ ] **Phase 8: One-Click Apply** - Apply modes and dashboard-triggered application submission

## Phase Details

### Phase 1: Config Externalization
**Goal**: User configures their entire profile, search queries, scoring weights, timing, and platform toggles in a single YAML file instead of editing Python source code
**Depends on**: Nothing (first phase)
**Requirements**: CFG-01
**Plans:** 3 plans
**Success Criteria** (what must be TRUE):
  1. User edits a single `config.yaml` file with their name, contact info, skills, search queries, scoring weights, and platform settings -- no Python files touched
  2. Pipeline loads all settings from YAML with pydantic-settings validation and clear error messages for missing or invalid fields
  3. Existing pipeline behavior is unchanged -- same search results, same scoring, same dashboard -- just configured from YAML instead of hardcoded values
  4. A documented `config.example.yaml` exists with every field annotated so a new user can fill it in

Plans:
- [x] 01-01-PLAN.md -- AppSettings model, YAML loader, config files, and dependency setup
- [x] 01-02-PLAN.md -- Pipeline consumer migration (orchestrator, scorer, form_filler) and --validate flag
- [x] 01-03-PLAN.md -- Platform module migration (base, indeed, dice, remoteok)

### Phase 2: Platform Architecture
**Goal**: Adding a new job board requires creating one file that implements a protocol -- no changes to the orchestrator, config, or scoring pipeline
**Depends on**: Phase 1
**Requirements**: PLAT-01
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. Platform implementations use Protocol-based contracts (BrowserPlatform, APIPlatform) instead of BasePlatform ABC inheritance
  2. New platforms are auto-discovered via a registry decorator -- adding a file to `platforms/` is sufficient to register it
  3. Orchestrator iterates over registered platforms from config without any if/elif branching for platform names
  4. Existing Indeed, Dice, and RemoteOK adapters work identically after migration to the new architecture

Plans:
- [x] 02-01-PLAN.md -- Protocol definitions (BrowserPlatform, APIPlatform), registry decorator with fail-fast validation, and BrowserPlatformMixin
- [x] 02-02-PLAN.md -- Big-bang migration: all three adapters to protocols, orchestrator to registry-based iteration, auto-discovery in __init__.py, BasePlatform ABC deleted

### Phase 3: Discovery Engine
**Goal**: The scrape-and-score loop produces smarter, more transparent results -- fuzzy company matching catches duplicates the current exact-match misses, score breakdowns explain why each job scored what it did, salary data is comparable across platforms, and repeat runs highlight what is new
**Depends on**: Phase 1
**Requirements**: DISC-01, DISC-02, DISC-03, CFG-03
**Plans:** 3 plans
**Success Criteria** (what must be TRUE):
  1. After a repeat pipeline run, newly discovered jobs are flagged as "new" in the dashboard while previously seen jobs are not
  2. Jobs from the same company posted under close variant names ("Google" vs "Google LLC") are merged into a single listing, while distant parent companies ("Alphabet") remain separate
  3. Each scored job shows a point-by-point breakdown (e.g., "title +2, tech overlap +2, remote +1, salary 0") visible in the dashboard detail view
  4. Salary figures from all platforms are normalized to annual USD so "$175000", "USD 224,400.00 per year", and "150000-180000 CAD" are directly comparable
  5. Delta detection persists across runs -- the system remembers which jobs it has seen before using the SQLite database

Plans:
- [x] 03-01-PLAN.md -- New processing modules (salary.py, dedup.py), scorer breakdown refactor, model updates
- [ ] 03-02-PLAN.md -- DB schema migration (versioned), orchestrator wiring for salary/dedup/breakdown/delta
- [ ] 03-03-PLAN.md -- Dashboard UI: NEW badges, inline score breakdown, salary display, company aliases

### Phase 4: Scheduled Automation
**Goal**: The pipeline runs automatically on a schedule without manual CLI invocation, producing fresh results daily
**Depends on**: Phase 1, Phase 3
**Requirements**: CFG-02
**Success Criteria** (what must be TRUE):
  1. User configures a schedule in `config.yaml` (e.g., "daily at 8am") and the system generates the appropriate cron/launchd configuration
  2. Scheduled runs execute the full pipeline (search, score, persist to SQLite) without any human interaction required for the discovery phases
  3. Run history is logged so the user can see when the last run happened, how many new jobs were found, and whether any errors occurred
**Plans**: TBD

Plans:
- [ ] 04-01: Scheduler configuration and runner
- [ ] 04-02: Run history and error logging

### Phase 5: Dashboard Core
**Goal**: The web dashboard becomes the primary interface for managing the job search -- users can find specific jobs, track them through an application pipeline, take bulk actions, export data, and see a full activity timeline per job
**Depends on**: Phase 1, Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. User can type a search query and instantly filter the job list by title, company name, or description text
  2. Jobs move through a 9-status workflow (Saved, Applied, Phone Screen, Technical Interview, Final Interview, Offer, Rejected, Withdrawn, Ghosted) with status selectable per job
  3. User can select multiple jobs with checkboxes and update all their statuses in a single action
  4. User can export the current filtered view to CSV or JSON with one click from the dashboard
  5. Each job has an activity log showing a timeline of all events: when it was discovered, every status change, notes added, and application timestamps
**Plans**: TBD

Plans:
- [ ] 05-01: Text search implementation
- [ ] 05-02: Extended status workflow and transitions
- [ ] 05-03: Bulk actions
- [ ] 05-04: Export (CSV/JSON)
- [ ] 05-05: Activity log per job

### Phase 6: Dashboard Analytics
**Goal**: Users can visualize their job search progress with metrics and manage their pipeline through an intuitive kanban board
**Depends on**: Phase 5
**Requirements**: DASH-06, DASH-07
**Success Criteria** (what must be TRUE):
  1. Dashboard shows aggregate stats: jobs discovered per day/week, application response rate, average time-in-stage, and per-platform effectiveness
  2. User can switch to a kanban board view where jobs appear as cards in columns by status, and can drag-and-drop jobs between columns to change status
  3. Stats update in real time as jobs move through the pipeline -- no page refresh needed
**Plans**: TBD

Plans:
- [ ] 06-01: Analytics engine and stats API
- [ ] 06-02: Stats dashboard page
- [ ] 06-03: Kanban board view with drag-and-drop

### Phase 7: AI Resume & Cover Letter
**Goal**: Users generate a tailored resume and cover letter for each application, with AI reordering real experience to match the job description -- never fabricating new claims
**Depends on**: Phase 1
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. User clicks "Tailor Resume" on a job in the dashboard and receives a PDF resume with their real experience reordered and emphasized to match that job's requirements
  2. The tailored resume contains ONLY facts from the user's original profile -- a diff view shows exactly what changed so the user can verify nothing was fabricated
  3. User clicks "Generate Cover Letter" and receives a targeted cover letter referencing the specific company and role
  4. All resume versions (original + tailored variants) are tracked -- user can see which resume was sent to which company
  5. Generated documents are stored in `resumes/tailored/` with clear naming (company + date)
**Plans**: TBD

Plans:
- [ ] 07-01: PDF text extraction and candidate profile loader
- [ ] 07-02: Resume tailoring with anti-fabrication guardrails
- [ ] 07-03: Cover letter generation
- [ ] 07-04: Multi-resume tracking and management
- [ ] 07-05: Dashboard integration (tailor/generate buttons, diff view)

### Phase 8: One-Click Apply
**Goal**: Users can apply to jobs directly from the dashboard with configurable automation levels -- from fully automated (with approval gate) to manual URL opening
**Depends on**: Phase 2, Phase 5, Phase 7
**Requirements**: CFG-04, APPLY-01
**Success Criteria** (what must be TRUE):
  1. User selects an apply mode per job or globally in config: full-auto (fill form + wait for approval + submit), semi-auto (fill form + user reviews + user submits), or Easy Apply only
  2. Clicking "Apply" on a job in the dashboard triggers the browser automation pipeline with real-time status updates visible in the dashboard
  3. The system checks for duplicate applications before submitting (has this job been applied to before?) and warns the user
  4. Apply actions are logged in the job's activity timeline with timestamps, mode used, and outcome (success/failure/skipped)
  5. For external ATS jobs (Greenhouse, Lever), the system opens the apply URL and pre-fills known fields where possible
**Plans**: TBD

Plans:
- [ ] 08-01: Apply mode configuration and resolution
- [ ] 08-02: Apply engine with behavioral guardrails
- [ ] 08-03: Dashboard-to-orchestrator bridge (SSE)
- [ ] 08-04: Pre-apply duplicate detection
- [ ] 08-05: External ATS form filling

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

Note: Phases 3 and 7 only depend on Phase 1 (not on each other or Phase 2), so they could theoretically run in parallel with later phases. However, the linear ordering above is recommended for a solo developer.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Config Externalization | 3/3 | Complete | 2026-02-07 |
| 2. Platform Architecture | 2/2 | Complete | 2026-02-07 |
| 3. Discovery Engine | 1/3 | In progress | - |
| 4. Scheduled Automation | 0/2 | Not started | - |
| 5. Dashboard Core | 0/5 | Not started | - |
| 6. Dashboard Analytics | 0/3 | Not started | - |
| 7. AI Resume & Cover Letter | 0/5 | Not started | - |
| 8. One-Click Apply | 0/5 | Not started | - |
