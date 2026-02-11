# Feature Landscape: Claude CLI Agent Integration

**Domain:** CLI subprocess AI integration, SSE-streamed document generation, on-demand AI scoring
**Researched:** 2026-02-11
**Overall confidence:** MEDIUM (Claude CLI `--json-schema` is well-documented; SSE streaming patterns are mature; subprocess-to-SSE bridging is novel integration work)

## Table Stakes

Features users expect when AI document generation and scoring are present. Missing = experience feels broken or incomplete.

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| Claude CLI subprocess wrapper | Core building block -- replaces `anthropic.Anthropic()` calls with `claude -p --output-format json --json-schema <schema>` | Medium | Claude CLI installed, PATH accessible |
| Pydantic-to-JSON-Schema bridge | Existing `TailoredResume` and `CoverLetter` Pydantic models must feed `--json-schema` flag directly via `model_json_schema()` | Low | Existing `resume_ai/models.py` |
| System prompt passthrough | Anti-fabrication system prompts in `tailor.py` and `cover_letter.py` must pass to CLI via `--system-prompt` or `--system-prompt-file` | Low | Existing system prompts |
| Error handling for CLI failures | Process exit codes, stderr capture, timeout handling, missing CLI binary detection | Medium | Subprocess wrapper |
| Fallback on CLI unavailability | If `claude` binary not found or crashes, surface clear error to user (not a stack trace) | Low | Subprocess wrapper |
| SSE streaming for resume tailoring | Replace the htmx spinner with real-time progress events during generation (connecting, generating, validating, rendering PDF, done) | Medium | Subprocess wrapper, existing SSE infrastructure from apply engine |
| SSE streaming for cover letter generation | Same SSE pattern as resume tailoring -- progress events visible in job detail sidebar | Medium | Same as above |
| AI Rescore button on job detail page | "AI Rescore" button next to existing score display that calls Claude CLI to analyze job fit semantically | Medium | Subprocess wrapper, new Pydantic model for AI score output |
| AI score result display | Show AI score (1-5), reasoning, matched skills, gaps -- replaces or supplements rule-based score | Low | AI Rescore endpoint, htmx partial |
| AI score persistence to SQLite | Store AI score, reasoning, and metadata in DB alongside rule-based score | Low | `webapp/db.py` schema extension |

## Differentiators

Features that elevate beyond basic "call AI and display result." Not expected, but significantly improve the experience.

| Feature | Value Proposition | Complexity | Depends On |
|---------|-------------------|------------|------------|
| Streaming token output during generation | Show Claude's actual text output streaming token-by-token into the UI via `--output-format stream-json`, not just phase markers | High | `asyncio.create_subprocess_exec`, stream-json parsing, SSE forwarding |
| Side-by-side score comparison | Show rule-based score AND AI score together with a visual diff of what each found | Low | AI Rescore + existing `ScoreBreakdown` |
| Batch AI rescore | "Rescore All" button to AI-rescore multiple jobs (queued, one at a time) with progress | Medium | AI Rescore endpoint, queue, SSE progress |
| AI score explanation with job description highlights | AI score response highlights which parts of the job description matched or missed | Medium | Richer Pydantic output model, template rendering |
| Generation cost tracking | Track and display token usage / cost per generation (Claude CLI JSON output includes usage metadata) | Low | Parse `usage` field from CLI JSON response |
| Model selection in UI | Dropdown to pick model (sonnet vs opus vs haiku) before generating resume/cover letter/rescore | Low | Pass `--model` flag to CLI subprocess |
| Retry with different prompt | If generation fails validation, offer "Retry" button that re-runs with the same inputs | Low | SSE error state with retry action |
| CLI availability health check | Dashboard status indicator showing whether `claude` CLI is available and authenticated | Low | `claude --version` subprocess check |

## Anti-Features

Features to explicitly NOT build. Avoiding these keeps scope manageable and architecture clean.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Claude Agent SDK Python package integration | Adds a heavy dependency (`claude-agent-sdk`) when the CLI subprocess approach is simpler, lighter, and more debuggable. The SDK is still pre-1.0 with breaking changes. | Use `claude -p --output-format json --json-schema` via subprocess. Same structured output, no dependency. |
| WebSocket for streaming | Overkill for single-user app. SSE already works for apply engine, adding WebSocket introduces new infrastructure. | Use SSE via sse-starlette (already a dependency). htmx SSE extension already in use. |
| Real-time token-by-token rendering for resume | Resume is structured output (JSON schema enforced) -- tokens arrive as partial JSON that cannot be rendered until complete. Partial rendering would show garbage. | Stream phase-level progress events (connecting, generating, validating, rendering). Show final result when complete. |
| Agentic multi-turn CLI calls | Claude CLI with `--max-turns` enables multi-turn agentic workflows where the model uses tools. For document generation and scoring, single-turn is sufficient. Multi-turn adds unpredictable latency and cost. | Use `--max-turns 1` (or omit) and `--tools ""` to disable tool use. Keep calls deterministic and fast. |
| Parallel CLI subprocess calls | Running multiple `claude` processes simultaneously risks API rate limits, unclear cost control, and race conditions on output. | Serialize AI operations. One at a time. Apply engine already uses `asyncio.Semaphore(1)` for this pattern. |
| Auto-rescore on import | Automatically AI-rescoring all newly imported jobs would be expensive (API costs) and slow. The rule-based scorer handles bulk well. | AI Rescore is on-demand, user-triggered. Rule-based score remains the default for bulk pipeline. |
| Replace rule-based scoring entirely | Rule-based scoring is instant, free, and deterministic. Replacing it with AI scoring makes the pipeline slow and expensive. | Keep both. Rule-based for pipeline/bulk. AI for on-demand deep analysis of individual jobs. |
| Store full Claude CLI response in DB | Raw JSON responses are large and mostly metadata. Storing them wastes DB space. | Extract and store only: AI score, reasoning, matched_skills, gaps, model_used, tokens_used. |

## Feature Dependencies

```
claude_cli_wrapper (new module)
  -> resume tailoring SSE endpoint (replaces spinner)
  -> cover letter SSE endpoint (replaces spinner)
  -> AI rescore endpoint (new feature)

SSE infrastructure (adapt from apply engine)
  -> resume tailoring SSE
  -> cover letter SSE
  -> AI rescore SSE (optional -- rescore may be fast enough for spinner)

Pydantic models
  -> TailoredResume.model_json_schema() -> --json-schema for resume CLI call
  -> CoverLetter.model_json_schema() -> --json-schema for cover letter CLI call
  -> AIScoreResult (new model) -> --json-schema for rescore CLI call

DB schema extension
  -> ai_score column on jobs table (nullable int, 1-5)
  -> ai_score_reasoning column (nullable text)
  -> ai_score_metadata column (nullable JSON: model, tokens, timestamp)

htmx templates
  -> partials/resume_stream.html (SSE progress during generation)
  -> partials/cover_letter_stream.html (SSE progress during generation)
  -> partials/ai_score_result.html (AI score display)
  -> job_detail.html updates (AI Rescore button, SSE containers)
```

## MVP Recommendation

Prioritize (in build order):

1. **Claude CLI subprocess wrapper** -- Foundation for all three features. Handles `asyncio.create_subprocess_exec`, JSON parsing, error handling, timeout, schema injection. Single module, tested independently.

2. **AI Rescore button + endpoint** -- Smallest integration surface. New Pydantic model (`AIScoreResult`), new endpoint, new htmx partial. Does not change existing code paths. Good validation that the CLI wrapper works.

3. **SSE streaming for resume tailoring** -- Replace spinner with real-time progress. Adapts existing SSE patterns from apply engine. Changes the existing `/jobs/{key}/tailor-resume` endpoint from synchronous POST to SSE-streaming flow.

4. **SSE streaming for cover letter generation** -- Same pattern as resume tailoring. Minimal incremental effort once the first SSE document endpoint works.

5. **DB schema for AI scores** -- Add columns, migration, display in templates. Low risk, low effort, but depends on AI Rescore being functional.

Defer:
- **Token-by-token streaming**: High complexity, low value for structured output (partial JSON is not renderable). Phase-level progress is sufficient.
- **Batch AI rescore**: Nice-to-have but not needed for initial release. Individual rescore proves the value first.
- **Model selection UI**: Default to sonnet. Add dropdown later if users want to choose.
- **Cost tracking**: Parse and log it, but don't build a UI for it in MVP.

## Key Technical Decisions

### CLI Invocation Pattern
```python
# Use asyncio.create_subprocess_exec (not subprocess.run) because:
# 1. FastAPI is async -- blocking subprocess.run freezes the event loop
# 2. Streaming stdout line-by-line feeds SSE events
# 3. Timeout handling via asyncio.wait_for

proc = await asyncio.create_subprocess_exec(
    "claude", "-p",
    "--output-format", "json",
    "--json-schema", schema_json,
    "--system-prompt-file", prompt_file,
    "--model", model,
    "--max-turns", "1",
    "--tools", "",                          # disable tool use
    "--no-session-persistence",             # don't save session
    "--dangerously-skip-permissions",       # no permission prompts in -p mode
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, stderr = await asyncio.wait_for(
    proc.communicate(input=prompt_bytes),
    timeout=120,
)
```

### SSE Streaming Architecture
```
Browser                FastAPI                  Claude CLI
  |                      |                         |
  |-- POST /tailor ----->|                         |
  |<-- HTML (sse-connect)|                         |
  |                      |                         |
  |-- GET /tailor/stream>|                         |
  |                      |-- subprocess_exec ----->|
  |<-- SSE: "starting"   |                         |
  |                      |<-- stdout (json) -------|
  |<-- SSE: "validating" |                         |
  |<-- SSE: "rendering"  |                         |
  |<-- SSE: "done" + HTML|                         |
  |                      |                         |
```

### AI Score Output Model
```python
class AIScoreResult(BaseModel):
    """Structured output for AI-powered job scoring."""
    score: int = Field(ge=1, le=5, description="Overall fit score 1-5")
    reasoning: str = Field(description="2-3 sentence explanation of the score")
    matched_skills: list[str] = Field(description="Skills from resume that match the job")
    missing_skills: list[str] = Field(description="Skills the job wants that are not in resume")
    culture_fit_notes: str = Field(description="Notes on company/role culture alignment")
```

## Sources

- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- Authoritative docs for `-p`, `--output-format json`, `--json-schema`, `--system-prompt` flags (HIGH confidence)
- [Claude Code Headless/Programmatic Usage](https://code.claude.com/docs/en/headless) -- Subprocess patterns, structured output examples (HIGH confidence)
- [Agent SDK Structured Outputs](https://platform.claude.com/docs/en/agent-sdk/structured-outputs) -- `structured_output` field in JSON response, Pydantic integration, error handling subtypes (HIGH confidence)
- [sse-starlette GitHub](https://github.com/sysid/sse-starlette) -- EventSourceResponse API, ping, send_timeout, async generator pattern (HIGH confidence)
- [htmx SSE Extension](https://htmx.org/extensions/sse/) -- `sse-connect`, `sse-swap`, `sse-close`, lifecycle events (HIGH confidence)
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) -- `create_subprocess_exec`, PIPE, readline patterns (HIGH confidence)
- [AI Hiring with LLMs: Multi-Agent Framework](https://arxiv.org/html/2504.02870v1) -- Context-aware resume scoring patterns (MEDIUM confidence)
- Codebase analysis: `resume_ai/tailor.py`, `resume_ai/cover_letter.py`, `scorer.py`, `webapp/app.py`, `apply_engine/engine.py`, `apply_engine/events.py`
