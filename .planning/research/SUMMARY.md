# Project Research Summary

**Project:** JobFlow v2 — Claude CLI Subprocess Integration, SSE Streaming for AI Features, On-Demand AI Scoring
**Domain:** CLI subprocess AI integration, SSE-streamed document generation, on-demand AI scoring
**Researched:** 2026-02-11
**Confidence:** HIGH

## Executive Summary

This milestone replaces direct Anthropic SDK calls with Claude CLI subprocess invocations and adds SSE streaming for real-time progress feedback during resume tailoring, cover letter generation, and AI scoring operations. The research confirms this is a zero-new-dependency change: Python 3.14's native asyncio subprocess support handles CLI invocations, the existing sse-starlette infrastructure adapts directly from the apply engine, and Pydantic v2's `model_json_schema()` generates the exact JSON Schema format the CLI requires. The anthropic SDK can be removed from production dependencies entirely.

The recommended approach uses `asyncio.create_subprocess_exec()` for streaming CLI calls (not `asyncio.to_thread(subprocess.run)`) to enable line-by-line NDJSON parsing for SSE progress events. AI scoring is a separate on-demand feature that complements (not replaces) the existing rule-based scorer: heuristic scoring remains instant and free for pipeline bulk processing, while AI scoring provides deep semantic analysis for individual jobs the user is evaluating. The architecture follows the proven apply engine pattern: POST endpoint creates an asyncio.Queue and starts a background task, returns HTML with SSE connection markup, GET endpoint streams from the queue via EventSourceResponse.

Key risks center on subprocess lifecycle management (zombie processes, timeout handling, stderr capture) and the CLI's `--json-schema` regression in v2.1.x where structured output is sometimes embedded in markdown instead of the `structured_output` field. Mitigation includes resilient parsing that handles both formats, timeout/cancellation discipline with proper process cleanup, and SSE disconnection detection to kill orphaned CLI processes when users navigate away. The test mock strategy must migrate from SDK patching to subprocess mocking, requiring an audit of 428+ existing tests.

## Key Findings

### Recommended Stack

The stack changes are minimal—no new dependencies required. Python 3.14's `asyncio.create_subprocess_exec()` handles Claude CLI subprocesses with native streaming via `readline()`. The existing sse-starlette (already at 2.0.0, upgradable to 3.2.0) provides SSE streaming using the exact pattern from the apply engine. Pydantic v2's `model_json_schema()` generates JSON Schemas compatible with the CLI's `--json-schema` flag without transformation. The Claude CLI (verified at v2.1.39) is already installed on the target machine.

**Core technologies:**
- **Claude CLI (`claude -p`)**: LLM inference via subprocess (already installed, v2.1.39) — uses user's Claude subscription, no API key management, provides structured output via `--json-schema` identical to SDK's `messages.parse()`
- **asyncio.create_subprocess_exec**: stdlib async subprocess manager — streams stdout line-by-line for SSE forwarding without blocking the event loop
- **sse-starlette**: already a dependency (v2.0.0+) — EventSourceResponse pattern proven in apply engine, directly reusable
- **Pydantic v2 model_json_schema()**: already a dependency — generates JSON Schema for `--json-schema` flag with zero transformation

**What NOT to add:**
- anthropic SDK can be removed from production (move to dev-only for test mocks during migration)
- No aiofiles, anyio, claude-agent-sdk-python, websockets, celery, or other background task frameworks needed

### Expected Features

The research divides features into three categories based on user expectations for AI-powered document generation and scoring in job search tools.

**Must have (table stakes):**
- Claude CLI subprocess wrapper with timeout, error handling, and CLI availability detection
- Pydantic-to-JSON-Schema bridge for existing TailoredResume/CoverLetter models
- System prompt passthrough via `--system-prompt` flag
- SSE streaming for resume tailoring with real-time progress events
- SSE streaming for cover letter generation with progress visibility
- AI Rescore button on job detail page triggering semantic job-fit analysis
- AI score result display (1-5 scale, reasoning, matched/missing skills)
- AI score persistence to SQLite in separate columns from rule-based score

**Should have (competitive differentiators):**
- Side-by-side score comparison (rule-based vs AI with visual diff)
- Streaming token output during generation (token-by-token text into UI)
- AI score explanation with highlighted job description sections
- Generation cost tracking from CLI JSON response usage metadata
- CLI availability health check in dashboard status indicator

**Defer (v2+):**
- Batch AI rescore ("Score All" with queue and progress)
- Model selection UI (dropdown for sonnet/opus/haiku)
- Real-time token rendering for structured output (partial JSON not renderable)
- Agentic multi-turn CLI calls (single-turn is sufficient for this use case)
- Auto-rescore on import (too expensive, rule-based handles bulk)

### Architecture Approach

The architecture mirrors the existing apply engine SSE pattern: a POST endpoint triggers the operation and returns HTML with `sse-connect` markup, a GET endpoint streams events via EventSourceResponse consuming an asyncio.Queue, and a background task runs the Claude CLI subprocess and pushes progress events to the queue. The CLI wrapper has two modes: streaming (for resume/cover letter with progress) and non-streaming (for AI scoring with structured JSON output).

**Major components:**
1. **resume_ai/claude_cli.py** (NEW) — Core subprocess abstraction with `stream_prompt()` async iterator for SSE and `run_prompt()` for structured output via `--json-schema`
2. **resume_ai/ai_scorer.py** (NEW) — AI job scoring logic using CLI with structured JSON Schema for multi-dimensional fit analysis (title relevance, tech overlap, experience level, culture fit)
3. **resume_ai/tailor.py + cover_letter.py** (MODIFIED) — Add `*_streaming()` async functions alongside existing sync functions (backward compatible for tests)
4. **webapp/app.py** (MODIFIED) — 4 new SSE endpoints (tailor start/stream, cover letter start/stream) + 1 AI rescore endpoint following apply engine pattern
5. **webapp/db.py** (MODIFIED) — Migration v7 adds `ai_score`, `ai_score_breakdown`, `ai_scored_at` columns (AI score separate from rule-based `score`)

**Data flow:** User clicks button → POST creates asyncio.Queue + starts background task → returns HTML with sse-connect → background task spawns `claude -p --output-format stream-json` → reads stdout NDJSON lines → parses `text_delta` events → pushes to queue → GET endpoint yields from queue → htmx swaps progressive HTML updates → final "done" event renders complete result.

**Build order:** (1) claude_cli.py foundation, (2) db.py migration v7, (3) ai_scorer.py, (4) tailor/cover_letter streaming functions, (5) templates/partials, (6) app.py endpoints, (7) job_detail.html SSE wiring, (8) integration testing.

### Critical Pitfalls

The research identified 14 pitfalls across three severity levels. The top five critical issues that require upfront mitigation:

1. **subprocess.run() hangs with CLI** — Using synchronous subprocess.run or wrapping it in asyncio.to_thread blocks the event loop for 5-60+ seconds per call. Zombie processes accumulate if timeouts kill the parent but not Node.js child workers. Prevention: always use `asyncio.create_subprocess_exec()` with PIPE for stdout/stderr, wrap in `asyncio.wait_for(timeout=120)`, kill the process explicitly on timeout/cancellation.

2. **CLI `--json-schema` regression in v2.1.x** — The CLI sometimes returns structured output embedded in markdown within the `result` field instead of the `structured_output` field (known bug #18536). Prevention: build resilient parser handling both formats, pin CLI version in docs, validate against Pydantic models regardless of extraction method.

3. **SSE connection leak on navigation** — When users navigate away during AI scoring, htmx closes the EventSource but the backend continues running the CLI subprocess and accumulating queue events. Prevention: reduce queue polling timeout to 1-2s, check `request.is_disconnected()` frequently, store subprocess handle alongside queue for cancellation, use `sse-close="done"` attribute.

4. **SQLite ALTER TABLE breaks FTS5** — Adding `ai_score` columns with `DEFAULT (datetime('now'))` fails (SQLite doesn't allow expression defaults in ALTER). Adding columns without updating FTS5 triggers leaves the index out of sync. Prevention: use `DEFAULT NULL` for timestamps (populate in code), keep AI score columns OUT of FTS5 initially (add in separate migration v8 if needed with full rebuild).

5. **Error semantics lost crossing process boundary** — The SDK's typed exceptions (AuthenticationError, RateLimitError) collapse into generic subprocess.CalledProcessError. Prevention: build typed error classes (CLITimeoutError, CLIAuthError, CLIRateLimitError) parsed from stderr patterns, create AIProvider abstraction so tests mock at protocol level not implementation level.

## Implications for Roadmap

Based on research, suggested phase structure follows the dependency graph and risk mitigation priorities:

### Phase 1: CLI Wrapper Foundation
**Rationale:** The CLI subprocess wrapper is the foundation for all three features (streaming resume/cover letter, AI scoring). It has the highest risk (subprocess lifecycle management) and must be rock-solid before anything builds on it. Building it first allows unit testing in isolation with known-good inputs before integrating with SSE or existing features.

**Delivers:**
- `resume_ai/claude_cli.py` with `stream_prompt()` and `run_prompt()` functions
- Timeout handling, stderr capture, typed error classes
- CLI availability check with clear error messaging
- Resilient parser for `--json-schema` regression (handles both response formats)

**Addresses:**
- Table stakes: CLI subprocess wrapper, error handling, fallback on CLI unavailability (FEATURES.md)
- Foundation for all SSE streaming and AI scoring features

**Avoids:**
- Pitfall 1 (subprocess hangs) via asyncio.create_subprocess_exec + timeout
- Pitfall 2 (json-schema regression) via dual-format parser
- Pitfall 5 (error semantics) via typed error class reconstruction
- Pitfall 11 (CLI not in PATH) via shutil.which() check

### Phase 2: Database Schema & Test Infrastructure
**Rationale:** The DB migration and test mock updates must happen before implementing features. The schema defines AI score storage (separate from rule-based score), and the test infrastructure prevents accidental real CLI calls. These are orthogonal changes that can be done in parallel after the CLI wrapper exists.

**Delivers:**
- Migration v7: `ai_score`, `ai_score_breakdown`, `ai_scored_at` columns
- `_block_claude_cli` autouse fixture mirroring existing `_block_anthropic`
- `mock_claude_cli` fixture for test control
- Updated `get_jobs()` to support ai_score sorting

**Uses:**
- SQLite ALTER TABLE with DEFAULT NULL (not expression defaults)
- subprocess.run patching in pytest fixtures

**Avoids:**
- Pitfall 4 (ALTER TABLE breaks FTS5) by keeping AI columns out of FTS initially
- Pitfall 7 (score conflict) by storing AI score separately from rule-based score
- Pitfall 8 (test mock strategy) by building CLI-specific fixtures before converting code
- Pitfall 14 (unstructured JSON) by defining clear schema for ai_score_breakdown

### Phase 3: AI Scoring (Non-Streaming)
**Rationale:** AI scoring is the simplest integration—no SSE streaming, no existing code changes. It uses `run_prompt()` with `--json-schema` for structured output, validates the concept end-to-end, and provides immediate user value (see AI score on any job with one click). Success here proves the CLI wrapper works before tackling more complex SSE conversions.

**Delivers:**
- `resume_ai/ai_scorer.py` with multi-dimensional scoring prompt
- POST `/jobs/{key}/ai-rescore` endpoint (no SSE, just spinner)
- `templates/partials/ai_score_result.html` for score display
- Side-by-side score display in job_detail.html

**Implements:**
- AIScoreResult Pydantic model with dimensions: title_relevance, tech_overlap, experience_level, culture_fit, reasoning, matched_skills, missing_skills
- Non-streaming CLI call pattern (10-15s latency, spinner acceptable)

**Avoids:**
- Pitfall 9 (AI scoring too slow) by caching results in DB, only allowing on-demand triggering
- Pitfall 10 (SSE reconnection) not applicable (no SSE in this phase)

### Phase 4: SSE Streaming for Resume Tailoring
**Rationale:** With the CLI wrapper proven and AI scoring working, convert the existing tailor_resume endpoint to SSE streaming. This is the highest-value UX improvement (replaces 10-15s spinner with real-time progress). Uses the apply engine SSE pattern exactly—low risk since the pattern is proven.

**Delivers:**
- `tailor_resume_streaming()` async function in tailor.py (keeps existing sync version)
- POST `/jobs/{key}/tailor-resume/start` + GET `/jobs/{key}/tailor-resume/stream`
- `templates/partials/ai_stream_status.html` for progress rendering
- SSE wiring in job_detail.html AI tools section

**Implements:**
- Queue-based SSE bridging from ARCHITECTURE.md
- Background task with subprocess lifecycle management
- Progress events: "Extracting resume text", "Sending to Claude", "Generating...", "Validating output", "Done"

**Avoids:**
- Pitfall 3 (SSE connection leak) via sse-close, is_disconnected checks, subprocess cleanup in finally block
- Pitfall 6 (POST to SSE conversion) by following apply engine two-step pattern (POST returns sse-connect HTML, GET streams)

### Phase 5: SSE Streaming for Cover Letter Generation
**Rationale:** Near-identical to resume tailoring SSE—same pattern, same template reuse, minimal incremental effort once phase 4 works. Completes the SSE conversion for all AI document generation features.

**Delivers:**
- `generate_cover_letter_streaming()` in cover_letter.py
- POST `/jobs/{key}/cover-letter/start` + GET `/jobs/{key}/cover-letter/stream`
- Reuse `ai_stream_status.html` template from phase 4

**Implements:**
- Same SSE pattern as resume tailoring
- Same progress event structure

**Avoids:**
- Same pitfalls as Phase 4 (already solved)

### Phase Ordering Rationale

- **Foundation first:** CLI wrapper (phase 1) has no dependencies and blocks all other work. Getting subprocess handling right is critical and benefits from isolated development/testing.
- **Infrastructure before features:** DB schema and test mocks (phase 2) enable confident feature implementation without risking data corruption or test pollution.
- **Simple before complex:** AI scoring (phase 3) proves the CLI wrapper end-to-end with the simplest integration surface before tackling SSE streaming complexity.
- **Pattern reuse:** Resume SSE (phase 4) establishes the streaming pattern; cover letter SSE (phase 5) is a trivial clone with different prompts.
- **Avoid rework:** Building in dependency order prevents having to refactor phase N when phase N-1 uncovers architectural issues.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (CLI wrapper):** May need additional research into Claude CLI error output formats if typed error reconstruction proves fragile—currently based on stderr pattern matching which is heuristic.
- **Phase 4/5 (SSE streaming):** If token-by-token streaming is requested (currently deferred), needs research into partial text rendering strategies since JSON Schema output arrives complete, not incrementally parseable.

Phases with standard patterns (skip research-phase):
- **Phase 2 (DB schema):** SQLite ALTER TABLE and pytest fixture patterns are well-documented and proven in codebase.
- **Phase 3 (AI scoring):** Standard FastAPI POST endpoint + Pydantic validation, no novel integration.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Claude CLI verified locally (v2.1.39), asyncio.subprocess is stdlib, sse-starlette already in use. Zero speculation—all tools exist and work. |
| Features | HIGH | Feature breakdown grounded in existing resume_ai/ code and apply engine SSE patterns. Table stakes vs differentiators based on UX expectations from current codebase usage. |
| Architecture | HIGH | Direct codebase analysis of 8 files (app.py, db.py, scorer.py, tailor.py, cover_letter.py, engine.py, conftest.py, job_detail.html). SSE pattern already proven in apply engine. Build order follows dependency graph. |
| Pitfalls | HIGH | All critical pitfalls (1-5) verified against official Python/SQLite/htmx docs AND codebase behavior. Moderate/minor pitfalls (6-14) cross-referenced with GitHub issues and community sources. |

**Overall confidence:** HIGH

### Gaps to Address

While confidence is high overall, three areas need attention during implementation:

- **CLI version pinning:** Research confirmed v2.1.39 works but documented the `--json-schema` regression in v2.1.x. During phase 1, verify which CLI version(s) the resilient parser needs to support and document known-good versions in setup docs.

- **Test mock coverage audit:** The existing test suite has 428+ tests with carefully designed SDK mocks. Phase 2 requires auditing which tests are affected by the CLI migration. Build a script to identify tests that import anthropic or patch Messages to prioritize conversion efforts.

- **FTS5 for AI explanations:** Phase 2 deliberately keeps `ai_score_breakdown` out of FTS5 to avoid complexity. If users want to search AI explanations ("show me jobs where AI said Kubernetes is a gap"), validate whether full-text search on JSON is needed or if the plain text reasoning field is sufficient before designing migration v8.

- **Token-by-token streaming value:** Deferred as an anti-feature because structured output (JSON Schema) arrives complete, not token-by-token. If stakeholders request real-time token streaming anyway, research phase-level progress indicators vs synthetic streaming (emit the JSON fields as they conceptually "complete" even though the model produces them all at once).

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `webapp/app.py`, `webapp/db.py`, `scorer.py`, `resume_ai/tailor.py`, `resume_ai/cover_letter.py`, `apply_engine/engine.py`, `tests/conftest.py`, `tests/resume_ai/conftest.py`, `webapp/templates/job_detail.html`
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) — all CLI flags, output formats, json-schema
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) — programmatic usage, structured output
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) — create_subprocess_exec, cancellation
- [Python subprocess docs](https://docs.python.org/3/library/subprocess.html) — timeout, pipe handling
- [SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html) — DEFAULT constraints
- [SQLite FTS5](https://sqlite.org/fts5.html) — content-sync triggers
- [htmx SSE extension](https://htmx.org/extensions/sse/) — sse-connect, sse-swap, sse-close
- [FastAPI async/concurrency](https://fastapi.tiangolo.com/async/) — to_thread, event loop blocking
- [sse-starlette](https://github.com/sysid/sse-starlette) — EventSourceResponse, disconnect handling
- [Pydantic v2 JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) — model_json_schema(), $refs

### Secondary (MEDIUM confidence)
- [Claude CLI --json-schema bug #18536](https://github.com/anthropics/claude-code/issues/18536) — structured_output regression in v2.1.x (may be fixed in future releases)
- [htmx SSE close discussion #2393](https://github.com/bigskysoftware/htmx/issues/2393) — sse-close behavior clarification
- [htmx SSE DOM removal #2510](https://github.com/bigskysoftware/htmx/issues/2510) — cleanup patterns
- Local verification: Claude CLI 2.1.39 tested with `--output-format json` and `--json-schema` on 2026-02-11

### Tertiary (LOW confidence)
- [AI Hiring with LLMs: Multi-Agent Framework](https://arxiv.org/html/2504.02870v1) — context-aware resume scoring patterns (research paper, not production-tested)

---
*Research completed: 2026-02-11*
*Ready for roadmap: yes*
