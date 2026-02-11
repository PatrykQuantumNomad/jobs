# Milestones: JobFlow

## v1.2 Claude CLI Agent Integration (Shipped: 2026-02-11)

**Delivered:** Replaced all Anthropic SDK API calls with Claude CLI subprocess invocations so AI features run on the user's existing subscription with no per-token costs, plus added SSE streaming for resume/cover letter generation and on-demand AI scoring.

**Phases completed:** 16-19 (7 plans total)

**Key accomplishments:**

- Built claude_cli async subprocess wrapper with 7-class exception hierarchy, resilient JSON parser (structured_output + result field fallback), and cold-start retry
- Fully removed Anthropic SDK from runtime -- all AI features now use Claude CLI on user's subscription (no per-token API costs)
- Added on-demand AI scoring with "AI Rescore" button, structured output model (AIScoreResult), and persisted score/reasoning/strengths/gaps display
- SSE streaming for resume tailoring -- 4-stage real-time progress (extracting, generating, validating, rendering) with double-click protection and session cleanup
- SSE streaming for cover letter generation -- 3-stage pipeline with emerald-themed UI and collapsible text preview
- Updated all project documentation to reference Claude CLI instead of Anthropic SDK

**Stats:**

- 28 code files created/modified (+2,486/-362 lines Python + HTML)
- 18,022 total lines of code (16,258 Python + 1,764 HTML)
- 4 phases, 7 plans, 13 tasks
- Tests: 563 -> 581 (18 new integration tests)
- 15 requirements satisfied (15/15)
- 1 day (~5 hours execution, 2026-02-11)

**Git range:** `feat(16-01)` -> `docs(phase-19)`

**What's next:** Enhanced AI features (batch rescore, model selection UI, cost tracking), additional job boards, ATS form fill expansion

---

## v1.1 Test Web App (Shipped: 2026-02-08)

**Delivered:** Comprehensive automated test suite with CI pipeline covering all application layers -- 428 tests (unit, integration, E2E) with 80%+ coverage and GitHub Actions CI.

**Phases completed:** 9-15 (14 plans total)

**Key accomplishments:**

- Built complete test infrastructure with isolation fixtures (settings reset, in-memory DB, network/API blocking) ensuring zero cross-test contamination
- Created 204 unit tests covering all pure logic modules (models, scoring, salary, dedup, anti-fabrication, delta detection) with 92-100% coverage
- Built 68 database integration tests verifying CRUD lifecycle, FTS5 search, activity log, and schema initialization at 91% coverage
- Created 98 web/API integration tests for all FastAPI endpoints, RemoteOK parsing, and platform registry protocol compliance
- Set up GitHub Actions CI pipeline with coverage enforcement (80% threshold), ruff linting, and separate non-blocking E2E job
- Built 11 Playwright E2E tests for dashboard, filtering, kanban drag-and-drop, and CSV/JSON export downloads

**Stats:**

- 141 files created/modified
- 5,639 lines of test code (Python)
- 7 phases, 14 plans
- 428 tests total (417 unit/integration + 11 E2E)
- 45 requirements satisfied (45/45)
- 1 day (2026-02-08)

**Git range:** `docs(09)` -> `code clean up (3741989)`

**What's next:** Next milestone TBD

---

## v1.0 MVP (Shipped: 2026-02-08)

**Delivered:** Complete job search automation platform with discovery, scoring, web dashboard, AI resume tailoring, and one-click apply -- from CLI tool to daily-driver web application in a single day.

**Phases completed:** 1-8 (24 plans total)

**Key accomplishments:**

- Extensible job discovery pipeline across Indeed, Dice, and RemoteOK with pluggable platform architecture using Protocol-based contracts and decorator registry
- Comprehensive web dashboard with FTS5 search, kanban board, Chart.js analytics, bulk actions, and CSV/JSON export
- AI-powered resume and cover letter tailoring via Anthropic structured outputs with anti-fabrication guardrails, PDF rendering, and diff views
- One-click apply automation with real-time SSE progress streaming, 3 apply modes (semi-auto, full-auto, easy-apply-only), and ATS iframe detection for 5 major providers
- Unattended scheduled execution with macOS launchd integration and run history tracking
- Delta-aware job tracking with fuzzy dedup, salary normalization, score breakdowns, and activity logging
- Developer-friendly YAML configuration with pydantic-settings validation and documented config.example.yaml

**Stats:**

- 174 files created/modified
- 8,206 lines of code (6,705 Python + 1,501 HTML)
- 8 phases, 24 plans, ~80 tasks
- 1 day from start to ship (2026-02-07 to 2026-02-08)
- Total execution time: ~126 min across 30 plan executions

**Git range:** `feat(01-01)` -> `docs(08-04)`

**What's next:** Production hardening, additional job boards, enhanced ATS form fill, notification system

---
