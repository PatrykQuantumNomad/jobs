# Requirements: JobFlow

**Defined:** 2026-02-11
**Core Value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.

## v1.2 Requirements

Requirements for Claude CLI Agent Integration milestone. Each maps to roadmap phases.

### CLI Integration

- [ ] **CLI-01**: User can invoke Claude CLI as subprocess with system prompt, user message, and JSON schema for structured output
- [ ] **CLI-02**: CLI wrapper handles errors gracefully (timeout, non-zero exit, malformed JSON, auth failure, CLI not installed) with descriptive messages
- [ ] **CLI-03**: CLI wrapper returns typed Pydantic models from structured_output with resilient fallback parser for CLI regression

### Resume Tailoring

- [ ] **RES-01**: Resume tailoring uses Claude CLI subprocess instead of Anthropic SDK API
- [ ] **RES-02**: Resume tailoring shows SSE progress events during generation (extracting, generating, validating, rendering)
- [ ] **RES-03**: Anti-fabrication validation still runs on CLI-generated output
- [ ] **RES-04**: PDF rendering and version tracking continue to work unchanged

### Cover Letter

- [ ] **COV-01**: Cover letter generation uses Claude CLI subprocess instead of Anthropic SDK API
- [ ] **COV-02**: Cover letter generation shows SSE progress events during generation
- [ ] **COV-03**: PDF rendering and version tracking continue to work unchanged

### AI Scoring

- [ ] **SCR-01**: User can trigger AI rescore from the job detail page via "AI Rescore" button
- [ ] **SCR-02**: AI scoring uses Claude CLI with full resume and job description context for semantic analysis
- [ ] **SCR-03**: AI score (1-5), reasoning, strengths, and gaps are stored in database and displayed alongside keyword score

### Configuration & Cleanup

- [ ] **CFG-01**: Anthropic SDK no longer required for runtime AI features
- [ ] **CFG-02**: Setup documentation and CLAUDE.md updated for Claude CLI prerequisite

## Future Requirements

Deferred to v2+. Tracked but not in current roadmap.

### Enhanced AI Features

- **EHAI-01**: Batch AI rescore ("Score All" with queue and progress bar)
- **EHAI-02**: Model selection UI (dropdown for sonnet/opus/haiku per operation)
- **EHAI-03**: Token-by-token streaming during structured output generation
- **EHAI-04**: AI score explanation with highlighted job description sections
- **EHAI-05**: Generation cost tracking from CLI JSON response usage metadata
- **EHAI-06**: CLI availability health check indicator in dashboard header

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Agentic multi-turn CLI calls | Single-turn prompts are sufficient for resume/cover letter/scoring |
| Auto-rescore on import | Too expensive for bulk pipeline; rule-based handles volume |
| Real-time token rendering for structured output | JSON Schema output arrives complete, partial JSON not renderable |
| Side-by-side rule vs AI score comparison | Nice-to-have but not essential for v1.2; can add in quick task |
| FTS5 search on AI score explanations | Adds FTS rebuild complexity; defer until user need confirmed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 16 | Pending |
| CLI-02 | Phase 16 | Pending |
| CLI-03 | Phase 16 | Pending |
| RES-01 | Phase 18 | Pending |
| RES-02 | Phase 18 | Pending |
| RES-03 | Phase 18 | Pending |
| RES-04 | Phase 18 | Pending |
| COV-01 | Phase 19 | Pending |
| COV-02 | Phase 19 | Pending |
| COV-03 | Phase 19 | Pending |
| SCR-01 | Phase 17 | Pending |
| SCR-02 | Phase 17 | Pending |
| SCR-03 | Phase 17 | Pending |
| CFG-01 | Phase 16 | Pending |
| CFG-02 | Phase 19 | Pending |

**Coverage:**
- v1.2 requirements: 15 total
- Mapped to phases: 15/15
- Unmapped: 0

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after roadmap creation*
