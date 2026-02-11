# Roadmap: JobFlow

## Milestones

- SHIPPED **v1.0 MVP** -- Phases 1-8 (shipped 2026-02-08)
- SHIPPED **v1.1 Test Web App** -- Phases 9-15 (shipped 2026-02-08)
- ACTIVE **v1.2 Claude CLI Agent Integration** -- Phases 16-19

## Phases

<details>
<summary>SHIPPED v1.0 MVP (Phases 1-8) -- SHIPPED 2026-02-08</summary>

- [x] Phase 1: Config Externalization (3/3 plans) -- completed 2026-02-07
- [x] Phase 2: Platform Architecture (2/2 plans) -- completed 2026-02-07
- [x] Phase 3: Discovery Engine (3/3 plans) -- completed 2026-02-07
- [x] Phase 4: Scheduled Automation (2/2 plans) -- completed 2026-02-07
- [x] Phase 5: Dashboard Core (4/4 plans) -- completed 2026-02-07
- [x] Phase 6: Dashboard Analytics (2/2 plans) -- completed 2026-02-07
- [x] Phase 7: AI Resume & Cover Letter (4/4 plans) -- completed 2026-02-07
- [x] Phase 8: One-Click Apply (4/4 plans) -- completed 2026-02-08

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>SHIPPED v1.1 Test Web App (Phases 9-15) -- SHIPPED 2026-02-08</summary>

- [x] Phase 9: Test Infrastructure (2/2 plans) -- completed 2026-02-08
- [x] Phase 10: Unit Tests (3/3 plans) -- completed 2026-02-08
- [x] Phase 11: Database Integration Tests (2/2 plans) -- completed 2026-02-08
- [x] Phase 12: Web & API Integration Tests (3/3 plans) -- completed 2026-02-08
- [x] Phase 13: Config Integration Tests (1/1 plan) -- completed 2026-02-08
- [x] Phase 14: CI Pipeline (1/1 plan) -- completed 2026-02-08
- [x] Phase 15: E2E Tests (2/2 plans) -- completed 2026-02-08

Full details: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

### v1.2 Claude CLI Agent Integration (Active)

**Milestone Goal:** Replace all Anthropic SDK API calls with Claude CLI agent subprocesses so AI features run on the user's Anthropic subscription instead of requiring a separate API key with per-token charges. Add SSE streaming for resume/cover letter generation and on-demand AI scoring.

- [x] **Phase 16: CLI Wrapper Foundation** - Rock-solid subprocess abstraction for invoking Claude CLI with structured output (completed 2026-02-11)
- [x] **Phase 17: AI Scoring** - On-demand semantic job-fit analysis via CLI, stored alongside rule-based scores (completed 2026-02-11)
- [x] **Phase 18: Resume Tailoring via CLI + SSE** - Convert resume generation from SDK to CLI with real-time SSE progress streaming (completed 2026-02-11)
- [ ] **Phase 19: Cover Letter via CLI + SSE & Cleanup** - Convert cover letter generation and finalize SDK removal with documentation

## Phase Details

### Phase 16: CLI Wrapper Foundation
**Goal**: System can invoke Claude CLI as a subprocess with typed structured output, graceful error handling, and no Anthropic SDK runtime dependency
**Depends on**: Nothing (foundation phase)
**Requirements**: CLI-01, CLI-02, CLI-03, CFG-01
**Success Criteria** (what must be TRUE):
  1. Calling the CLI wrapper with a system prompt, user message, and Pydantic model returns a validated instance of that model
  2. When Claude CLI is not installed, times out, returns malformed JSON, or fails auth, the wrapper raises a specific typed error with a descriptive message (not a generic subprocess crash)
  3. The wrapper handles the --json-schema CLI regression (structured_output vs result field) transparently -- caller never sees raw JSON parsing issues
  4. The anthropic SDK package is no longer imported at runtime by any production code path
  5. Tests exist for all error paths (timeout, bad JSON, auth failure, CLI missing) using subprocess mocks
**Plans**: 2 plans

Plans:
- [x] 16-01-PLAN.md -- Build claude_cli/ package (exceptions, parser, client) with comprehensive tests
- [x] 16-02-PLAN.md -- Replace SDK in resume_ai, update webapp call sites, remove SDK dependency, update test infrastructure

### Phase 17: AI Scoring
**Goal**: User can trigger a deep AI-powered job-fit analysis from the dashboard and see semantic score, reasoning, strengths, and gaps alongside the existing rule-based score
**Depends on**: Phase 16 (CLI wrapper)
**Requirements**: SCR-01, SCR-02, SCR-03
**Success Criteria** (what must be TRUE):
  1. Job detail page shows an "AI Rescore" button that triggers semantic analysis using Claude CLI with the full resume and job description
  2. After AI scoring completes, the job detail page displays AI score (1-5), reasoning text, matched strengths, and skill gaps -- separate from the rule-based score
  3. AI score results persist in the database and survive page reloads (ai_score, ai_score_breakdown, ai_scored_at columns)
  4. If the CLI call fails (timeout, auth, unavailable), the user sees a clear error message and the existing rule-based score remains unaffected
**Plans**: 2 plans

Plans:
- [x] 17-01-PLAN.md -- AI scorer module (AIScoreResult model + score_job_ai function), database migration v7, unit tests
- [x] 17-02-PLAN.md -- Dashboard POST endpoint, htmx partial, job detail page UI with button and persisted score display

### Phase 18: Resume Tailoring via CLI + SSE
**Goal**: Resume tailoring runs through Claude CLI instead of the Anthropic SDK and shows real-time SSE progress events during generation
**Depends on**: Phase 16 (CLI wrapper)
**Requirements**: RES-01, RES-02, RES-03, RES-04
**Success Criteria** (what must be TRUE):
  1. Clicking "Tailor Resume" starts a CLI subprocess and streams SSE progress events to the dashboard (extracting, generating, validating, rendering stages visible in real-time)
  2. Anti-fabrication validation still catches any hallucinated skills, companies, or credentials in the CLI-generated output
  3. PDF rendering produces the same quality output as before (WeasyPrint, Calibri/Carlito fonts, ATS-friendly format)
  4. Resume version tracking continues to work -- each tailored resume gets a version number and the user can view/download previous versions
  5. If the user navigates away during generation, the background CLI subprocess is cleaned up (no zombie processes or orphaned SSE connections)
**Plans**: 1 plan

Plans:
- [x] 18-01-PLAN.md -- SSE-backed resume tailoring pipeline (background task, SSE endpoints, htmx template, tests)

### Phase 19: Cover Letter via CLI + SSE & Cleanup
**Goal**: Cover letter generation runs through Claude CLI with SSE streaming, and all documentation reflects the new CLI prerequisite
**Depends on**: Phase 16 (CLI wrapper), Phase 18 (SSE pattern established)
**Requirements**: COV-01, COV-02, COV-03, CFG-02
**Success Criteria** (what must be TRUE):
  1. Clicking "Generate Cover Letter" starts a CLI subprocess and streams SSE progress events to the dashboard (same pattern as resume tailoring)
  2. Cover letter PDF rendering and version tracking work unchanged
  3. CLAUDE.md, setup docs, and any README instructions reference Claude CLI as a prerequisite instead of Anthropic API key
  4. No production code imports or references the anthropic SDK (fully removed from runtime dependencies)
**Plans**: 2 plans

Plans:
- [ ] 19-01-PLAN.md -- SSE cover letter pipeline (background task, SSE endpoints, htmx templates, tests)
- [x] 19-02-PLAN.md -- Documentation update (CLAUDE.md, architecture.md, INTEGRATIONS.md, PROJECT.md) and SDK cleanup verification

## Progress

**Execution Order:**
Phases execute in numeric order: 16 -> 17 -> 18 -> 19
(Note: Phase 17 and 18 both depend only on Phase 16, so they could theoretically run in parallel, but sequential execution avoids conflicts.)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Config Externalization | v1.0 | 3/3 | Complete | 2026-02-07 |
| 2. Platform Architecture | v1.0 | 2/2 | Complete | 2026-02-07 |
| 3. Discovery Engine | v1.0 | 3/3 | Complete | 2026-02-07 |
| 4. Scheduled Automation | v1.0 | 2/2 | Complete | 2026-02-07 |
| 5. Dashboard Core | v1.0 | 4/4 | Complete | 2026-02-07 |
| 6. Dashboard Analytics | v1.0 | 2/2 | Complete | 2026-02-07 |
| 7. AI Resume & Cover Letter | v1.0 | 4/4 | Complete | 2026-02-07 |
| 8. One-Click Apply | v1.0 | 4/4 | Complete | 2026-02-08 |
| 9. Test Infrastructure | v1.1 | 2/2 | Complete | 2026-02-08 |
| 10. Unit Tests | v1.1 | 3/3 | Complete | 2026-02-08 |
| 11. Database Integration Tests | v1.1 | 2/2 | Complete | 2026-02-08 |
| 12. Web & API Integration Tests | v1.1 | 3/3 | Complete | 2026-02-08 |
| 13. Config Integration Tests | v1.1 | 1/1 | Complete | 2026-02-08 |
| 14. CI Pipeline | v1.1 | 1/1 | Complete | 2026-02-08 |
| 15. E2E Tests | v1.1 | 2/2 | Complete | 2026-02-08 |
| 16. CLI Wrapper Foundation | v1.2 | 2/2 | Complete | 2026-02-11 |
| 17. AI Scoring | v1.2 | 2/2 | Complete | 2026-02-11 |
| 18. Resume Tailoring via CLI + SSE | v1.2 | 1/1 | Complete | 2026-02-11 |
| 19. Cover Letter via CLI + SSE & Cleanup | v1.2 | 1/2 | In progress | - |
