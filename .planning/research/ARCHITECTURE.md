# Architecture Patterns

**Domain:** Claude CLI subprocess integration, SSE streaming for AI document generation, on-demand AI scoring
**Researched:** 2026-02-11
**Confidence:** HIGH (based on codebase analysis, Claude Code CLI docs, existing SSE patterns in apply_engine)

## Recommended Architecture

### System Overview: Before and After

**Current flow (resume tailoring):**
```
User clicks "Tailor Resume"
  -> htmx POST /jobs/{key}/tailor-resume
  -> asyncio.to_thread(tailor_resume)    # blocks for 10-15s
  -> anthropic.Anthropic().messages.parse()
  -> returns complete HTML partial (resume_diff.html)
  -> htmx swaps into #resume-ai-result
```
Problem: No progress feedback. User sees a spinner for 10-15 seconds with no indication of what is happening. The Anthropic SDK call is blocking and all-or-nothing.

**New flow (with Claude CLI + SSE):**
```
User clicks "Tailor Resume"
  -> htmx POST /jobs/{key}/tailor-resume
  -> creates asyncio.Queue, starts background task
  -> returns SSE connection HTML (like apply engine pattern)
  -> htmx sse-connect to /jobs/{key}/tailor-resume/stream

Background task:
  -> asyncio.create_subprocess_exec("claude", "-p", ..., "--output-format", "stream-json")
  -> reads stdout line by line (NDJSON)
  -> parses stream events, extracts text deltas
  -> pushes rendered HTML fragments to asyncio.Queue

SSE endpoint:
  -> reads from Queue
  -> yields events to EventSourceResponse
  -> htmx swaps progressive updates into DOM
  -> on "done" event: renders final diff + download link
```

### Component Map

```
                       EXISTING                           NEW
                    +-------------------+
                    |   job_detail.html  |  (MODIFIED: SSE wiring for resume/cover letter)
                    +--------+----------+
                             |
                    htmx POST + SSE
                             |
                    +--------v----------+
                    |   webapp/app.py   |  (MODIFIED: 3 new SSE endpoints, 1 AI score endpoint)
                    +--------+----------+
                             |
         +-------------------+-------------------+
         |                   |                   |
+--------v------+   +--------v------+   +--------v------+
| resume_ai/    |   | resume_ai/    |   | resume_ai/    |
| tailor.py     |   | cover_letter  |   | ai_scorer.py  |  <-- NEW FILE
| (MODIFIED)    |   | .py (MODIFIED)|   |               |
+--------+------+   +--------+------+   +--------+------+
         |                   |                   |
         +-------------------+-------------------+
                             |
                    +--------v----------+
                    | resume_ai/        |
                    | claude_cli.py     |  <-- NEW FILE (core abstraction)
                    +--------+----------+
                             |
              asyncio.create_subprocess_exec
                             |
                    +--------v----------+
                    | claude -p         |
                    | --output-format   |
                    | stream-json       |
                    +-------------------+
```

### Component Boundaries

| Component | Responsibility | Status | Communicates With |
|-----------|---------------|--------|-------------------|
| `resume_ai/claude_cli.py` | Subprocess lifecycle, NDJSON parsing, streaming text extraction | **NEW** | `tailor.py`, `cover_letter.py`, `ai_scorer.py` |
| `resume_ai/ai_scorer.py` | AI-powered job scoring via Claude CLI with structured JSON output | **NEW** | `claude_cli.py`, `webapp/app.py`, `webapp/db.py` |
| `resume_ai/tailor.py` | Resume tailoring prompt construction, result parsing | **MODIFIED** | `claude_cli.py` (replaces `anthropic` SDK) |
| `resume_ai/cover_letter.py` | Cover letter prompt construction, result parsing | **MODIFIED** | `claude_cli.py` (replaces `anthropic` SDK) |
| `webapp/app.py` | SSE endpoints for resume/cover letter streaming, AI rescore endpoint | **MODIFIED** | `tailor.py`, `cover_letter.py`, `ai_scorer.py`, `db.py` |
| `webapp/db.py` | Schema migration v7 (ai_score columns) | **MODIFIED** | `ai_scorer.py` reads/writes via existing functions |
| `webapp/templates/job_detail.html` | SSE wiring for AI tools section | **MODIFIED** | `app.py` SSE endpoints |
| `webapp/templates/partials/ai_stream_status.html` | Progressive SSE event rendering | **NEW** | `app.py` SSE endpoints |
| `webapp/templates/partials/ai_score_result.html` | AI score display partial | **NEW** | `app.py` AI rescore endpoint |

### Data Flow: Claude CLI Streaming

```
claude_cli.py                    webapp/app.py                    Browser
============                    =============                    =======

create_subprocess_exec()
  |
  | stdout (NDJSON lines)
  |
  v
parse each line as JSON -------> push to asyncio.Queue ---------> SSE EventSourceResponse
  |                                                                  |
  | filter for:                                                      | htmx sse-swap
  |   stream_event +                                                 |
  |   content_block_delta +                                          v
  |   text_delta                                              Progressive HTML updates:
  |                                                           "Analyzing job description..."
  | accumulate full text                                      "Reordering skills..."
  |                                                           "Generating summary..."
  v                                                                  |
process.wait()                                                       |
  |                                                                  |
  v                                                                  v
return complete text -----> parse structured output ---------> Final result partial:
                            (JSON from --json-schema          diff view + download link
                             or text post-processing)         OR score display
```

## New Components: Detailed Design

### 1. `resume_ai/claude_cli.py` -- Core Abstraction

This is the central new component. It wraps the Claude CLI subprocess and provides two modes of operation.

**Mode A: Streaming text (for resume/cover letter with progress)**
```python
# resume_ai/claude_cli.py
import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default model for CLI calls
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


@dataclass
class StreamChunk:
    """A chunk of text from the Claude CLI stream."""
    text: str
    is_final: bool = False


@dataclass
class CliResult:
    """Complete result from a Claude CLI call."""
    text: str
    session_id: str | None = None
    usage: dict | None = None


async def stream_prompt(
    prompt: str,
    *,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> AsyncIterator[StreamChunk]:
    """Stream Claude CLI output as text chunks.

    Uses --output-format stream-json with --verbose and
    --include-partial-messages to get token-by-token NDJSON.
    Yields StreamChunk objects with extracted text deltas.
    """
    cmd = [
        "claude", "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--model", model,
        "--max-turns", "1",
    ]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Send prompt via stdin
    assert process.stdin is not None
    process.stdin.write(prompt.encode("utf-8"))
    await process.stdin.drain()
    process.stdin.close()

    # Read NDJSON lines from stdout
    assert process.stdout is not None
    accumulated_text = ""

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        try:
            event = json.loads(line.decode("utf-8").strip())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Extract text deltas from stream events
        if (
            event.get("type") == "stream_event"
            and event.get("event", {}).get("delta", {}).get("type") == "text_delta"
        ):
            text = event["event"]["delta"]["text"]
            accumulated_text += text
            yield StreamChunk(text=text)

    # Wait for process to complete
    await process.wait()

    if process.returncode != 0:
        stderr = await process.stderr.read() if process.stderr else b""
        logger.error("Claude CLI exited with code %d: %s", process.returncode, stderr.decode())

    # Yield final chunk with accumulated text
    yield StreamChunk(text=accumulated_text, is_final=True)


async def run_prompt(
    prompt: str,
    *,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    json_schema: str | None = None,
) -> CliResult:
    """Run Claude CLI and return complete result (non-streaming).

    Used for structured output (AI scoring) where streaming is not needed.
    Uses --output-format json for structured response.
    """
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", model,
        "--max-turns", "1",
    ]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if json_schema:
        cmd.extend(["--json-schema", json_schema])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input=prompt.encode("utf-8"))

    if process.returncode != 0:
        raise RuntimeError(
            f"Claude CLI exited with code {process.returncode}: {stderr.decode()}"
        )

    result = json.loads(stdout.decode("utf-8"))
    return CliResult(
        text=result.get("result", ""),
        session_id=result.get("session_id"),
        usage=result.get("usage"),
    )
```

**Key design decisions:**
- Uses `asyncio.create_subprocess_exec` (not `subprocess.Popen`) because the caller is the async FastAPI event loop
- Sends prompt via stdin (not CLI arg) to handle long prompts safely -- CLI args have OS-level length limits
- Parses NDJSON line-by-line for streaming, filters for `text_delta` events specifically
- `stream_prompt()` is an async iterator -- natural fit for asyncio.Queue bridging
- `run_prompt()` is a simple async function for non-streaming structured output (AI scoring)
- No `asyncio.to_thread` needed because `create_subprocess_exec` is already non-blocking

### 2. `resume_ai/ai_scorer.py` -- AI-Powered Scoring

```python
# resume_ai/ai_scorer.py
import json

from resume_ai.claude_cli import run_prompt

AI_SCORER_SYSTEM_PROMPT = """\
You are a job match scoring assistant. Given a candidate resume and a job \
description, score the match on a scale of 1-5 with a detailed breakdown.

Score criteria:
- 5: Exceptional match -- candidate exceeds requirements
- 4: Strong match -- candidate meets most requirements
- 3: Moderate match -- candidate meets some requirements
- 2: Weak match -- minimal overlap
- 1: Poor match -- misaligned

Provide scores for each dimension: title_relevance, tech_overlap, \
experience_level, culture_fit, and overall."""

AI_SCORE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "overall_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "title_relevance": {"type": "integer", "minimum": 1, "maximum": 5},
        "tech_overlap": {"type": "integer", "minimum": 1, "maximum": 5},
        "experience_level": {"type": "integer", "minimum": 1, "maximum": 5},
        "culture_fit": {"type": "integer", "minimum": 1, "maximum": 5},
        "reasoning": {"type": "string"},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_score", "title_relevance", "tech_overlap",
        "experience_level", "culture_fit", "reasoning",
    ],
})


async def ai_score_job(
    resume_text: str,
    job_title: str,
    job_description: str,
    company_name: str,
) -> dict:
    """Score a job match using Claude AI.

    Returns a dict with overall_score (1-5), dimension scores,
    reasoning, matched_skills, and missing_skills.
    """
    prompt = (
        f"## Candidate Resume\n\n{resume_text}\n\n"
        f"## Job: {job_title} at {company_name}\n\n{job_description}"
    )

    result = await run_prompt(
        prompt,
        system_prompt=AI_SCORER_SYSTEM_PROMPT,
        json_schema=AI_SCORE_SCHEMA,
    )

    # Parse structured output from CLI JSON response
    return json.loads(result.text) if result.text.startswith("{") else {"overall_score": 0}
```

**Key design decisions:**
- Uses `--json-schema` flag for structured output -- the CLI enforces the schema
- Does NOT need streaming because scoring is a fast single-turn call
- Returns a dict matching the schema, ready for SQLite JSON storage
- Async by nature (no `to_thread` wrapper needed)

### 3. Modifications to `resume_ai/tailor.py`

The tailor module gets a new async streaming function alongside the existing sync function (keep backward compatibility for tests/CLI usage).

```python
# Added to resume_ai/tailor.py

async def tailor_resume_streaming(
    resume_text: str,
    job_description: str,
    job_title: str,
    company_name: str,
    model: str = DEFAULT_MODEL,
) -> AsyncIterator[StreamChunk]:
    """Stream resume tailoring via Claude CLI.

    Yields text chunks as they arrive. The final chunk (is_final=True)
    contains the complete accumulated text for post-processing.
    """
    from resume_ai.claude_cli import stream_prompt

    user_message = (
        f"## Original Resume\n\n{resume_text}\n\n"
        f"## Target Job Description\n\n{job_description}\n\n"
        f"## Target Role\n\n"
        f"- **Job Title:** {job_title}\n"
        f"- **Company:** {company_name}\n"
    )

    async for chunk in stream_prompt(
        user_message,
        system_prompt=SYSTEM_PROMPT,
        model=model,
    ):
        yield chunk
```

**The existing `tailor_resume()` sync function is preserved** for backward compatibility and testing. The new streaming variant is used exclusively by the SSE endpoints.

Same pattern applies to `resume_ai/cover_letter.py`.

### 4. SSE Endpoints in `webapp/app.py`

Follow the exact pattern from the apply engine. Three new endpoints per AI tool: trigger (POST), stream (GET SSE), and the existing sync endpoint is kept as fallback.

```python
# New pattern in webapp/app.py (sketch -- not complete implementation)

# ---- Resume tailoring with SSE ----

_ai_sessions: dict[str, asyncio.Queue] = {}

@app.post("/jobs/{dedup_key:path}/tailor-resume/start", response_class=HTMLResponse)
async def tailor_resume_start(request: Request, dedup_key: str):
    """Start streaming resume tailoring, return SSE connection HTML."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    queue = asyncio.Queue()
    _ai_sessions[f"tailor:{dedup_key}"] = queue

    # Start background task
    asyncio.create_task(_run_tailor_stream(job, dedup_key, queue))

    encoded_key = urllib.parse.quote(dedup_key, safe="")
    return HTMLResponse(
        f'<div hx-ext="sse"'
        f' sse-connect="/jobs/{encoded_key}/tailor-resume/stream"'
        f' sse-swap="progress"'
        f' sse-close="done">'
        f'  <div id="ai-stream-status">'
        f'    <p class="text-sm text-gray-500">Starting resume tailoring...</p>'
        f'  </div>'
        f'</div>'
    )

@app.get("/jobs/{dedup_key:path}/tailor-resume/stream")
async def tailor_resume_stream(request: Request, dedup_key: str):
    """SSE endpoint streaming resume tailoring progress."""
    from sse_starlette import EventSourceResponse

    queue = _ai_sessions.get(f"tailor:{dedup_key}")
    if queue is None:
        return HTMLResponse("No active session", status_code=404)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    event_type = event.get("type", "progress")
                    html = templates.get_template(
                        "partials/ai_stream_status.html"
                    ).render(event=event, dedup_key=dedup_key)
                    yield {"event": event_type, "data": html}
                    if event_type == "done":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
```

### 5. Database Schema Migration (v7)

```python
# Added to webapp/db.py MIGRATIONS dict

7: [
    "ALTER TABLE jobs ADD COLUMN ai_score INTEGER",
    "ALTER TABLE jobs ADD COLUMN ai_score_breakdown TEXT",
    "ALTER TABLE jobs ADD COLUMN ai_scored_at TEXT",
],
```

Three new columns on the `jobs` table:
- `ai_score` (INTEGER): The AI-generated overall score (1-5), separate from the existing heuristic `score`
- `ai_score_breakdown` (TEXT): JSON blob with dimension scores, reasoning, matched/missing skills
- `ai_scored_at` (TEXT): ISO timestamp of when AI scoring was performed

**The existing `score` column is untouched.** AI score is a separate dimension -- the heuristic score runs during pipeline scraping (fast, free), while AI score is on-demand from the dashboard (slower, costs API credits).

## Patterns to Follow

### Pattern 1: Queue-Based SSE Bridging (Reuse from apply_engine)

**What:** Use `asyncio.Queue` to bridge background async tasks to SSE `EventSourceResponse` generators.

**Why:** This exact pattern already works in `apply_engine/engine.py` (lines 82-84, 112-122). The apply engine uses `_make_emitter()` with `loop.call_soon_threadsafe()` to bridge sync threads to async queues. For Claude CLI, the subprocess is already async, so the simpler direct `queue.put()` pattern works.

**Example:**
```python
async def _run_tailor_stream(job: dict, dedup_key: str, queue: asyncio.Queue):
    """Background task: stream resume tailoring and push events to queue."""
    try:
        # Emit progress events as chunks arrive
        await queue.put({"type": "progress", "message": "Extracting resume text..."})

        resume_text = await asyncio.to_thread(extract_resume_text, resume_path)
        await queue.put({"type": "progress", "message": "Sending to Claude..."})

        accumulated = ""
        async for chunk in tailor_resume_streaming(...):
            if not chunk.is_final:
                accumulated += chunk.text
                # Emit every ~200 chars to avoid flooding
                if len(accumulated) % 200 < len(chunk.text):
                    await queue.put({
                        "type": "progress",
                        "message": f"Generating... ({len(accumulated)} chars)",
                    })
            else:
                # Final chunk -- do post-processing
                await queue.put({"type": "progress", "message": "Validating output..."})
                # ... validation, PDF generation, etc.
                await queue.put({
                    "type": "done",
                    "message": "Resume tailored successfully",
                    "html": rendered_result_html,
                })
    except Exception as exc:
        await queue.put({"type": "error", "message": str(exc)})
        await queue.put({"type": "done", "message": "Tailoring failed"})
    finally:
        _ai_sessions.pop(f"tailor:{dedup_key}", None)
```

### Pattern 2: Async Subprocess for Claude CLI (Not asyncio.to_thread)

**What:** Use `asyncio.create_subprocess_exec()` directly instead of wrapping `subprocess.run()` in `asyncio.to_thread()`.

**Why:** The Claude CLI streams output over time (10-30 seconds for resume tailoring). `asyncio.to_thread(subprocess.run)` would block the thread until the process completes, preventing incremental streaming. `create_subprocess_exec` with `readline()` gives line-by-line access to NDJSON output without blocking the event loop.

**Critical distinction from apply_engine:** The apply engine uses `asyncio.to_thread()` because Playwright is synchronous and cannot be made async. The Claude CLI subprocess IS naturally async via `asyncio.subprocess`. Do not wrap it in `to_thread`.

### Pattern 3: Prompt via stdin, Not CLI Argument

**What:** Send the prompt to the Claude CLI via stdin (`process.stdin.write()`) rather than as a CLI argument.

**Why:** Resume text + job descriptions can easily exceed 100KB. OS-level argument length limits (`ARG_MAX`) are typically 256KB on macOS but as low as 128KB on some Linux systems. Stdin has no practical limit.

**How:**
```python
process = await asyncio.create_subprocess_exec(
    "claude", "-p", "--output-format", "stream-json", ...,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
process.stdin.write(prompt.encode("utf-8"))
await process.stdin.drain()
process.stdin.close()
```

### Pattern 4: Separate Heuristic and AI Scores

**What:** Keep the existing `score` column for the fast heuristic scorer. Add `ai_score` as a separate column.

**Why:** The heuristic scorer runs during pipeline scraping (milliseconds per job, free). AI scoring is on-demand (10+ seconds per job, costs API credits). They serve different purposes:
- Heuristic score: batch triage during scraping (all jobs get one automatically)
- AI score: deep analysis when a user is evaluating a specific job

The dashboard can display both: "Score: 4 | AI: 5" with the AI score breakdown on hover/expand.

### Pattern 5: Structured Output via --json-schema (AI Scorer)

**What:** Use the Claude CLI's `--json-schema` flag for AI scoring instead of parsing free-form text.

**Why:** The CLI enforces the JSON schema at the model level (equivalent to `messages.parse()` with `output_format`). This guarantees the response matches the expected structure without brittle regex parsing. The structured output appears in the `structured_output` field of the JSON response.

```bash
claude -p --output-format json \
  --json-schema '{"type":"object","properties":{"overall_score":{"type":"integer"}},...}'
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using subprocess.Popen in Sync Context

**What:** Wrapping `subprocess.Popen()` or `subprocess.run()` in `asyncio.to_thread()` for the Claude CLI.

**Why bad:** Loses streaming capability. The thread blocks until the process completes. No incremental progress events can be emitted. The user stares at a spinner for 15+ seconds with no feedback -- exactly the problem we are solving.

**Instead:** Use `asyncio.create_subprocess_exec()` with `stdout=PIPE`, read lines with `readline()` in an async loop.

### Anti-Pattern 2: Single Endpoint for Both Trigger and Stream

**What:** Having one POST endpoint that both starts the generation and returns the SSE stream.

**Why bad:** htmx's SSE extension (`hx-ext="sse"`) requires a GET endpoint for `sse-connect`. The trigger must be a POST (to initiate the action), and the stream must be a separate GET (for the SSE connection). The apply engine already demonstrates this two-endpoint pattern correctly.

**Instead:** POST `/jobs/{key}/tailor-resume/start` returns HTML with `sse-connect` pointing to GET `/jobs/{key}/tailor-resume/stream`.

### Anti-Pattern 3: Replacing the Anthropic SDK Entirely

**What:** Removing `anthropic` from requirements and making the Claude CLI the only way to call the model.

**Why bad:** The existing sync `tailor_resume()` and `generate_cover_letter()` functions work and are used by tests. The CLI approach adds subprocess overhead and requires the `claude` binary to be installed. Keeping both paths provides fallback and testability.

**Instead:** Add new `*_streaming()` async functions that use `claude_cli.py`. Keep existing sync functions that use the `anthropic` SDK. The SSE endpoints call the streaming variants; the original POST endpoints keep using the sync path (via `asyncio.to_thread`).

### Anti-Pattern 4: Parsing Full Resume from Streaming Text

**What:** Trying to parse the Claude CLI's streaming text output into `TailoredResume` or `CoverLetter` Pydantic models mid-stream.

**Why bad:** Streaming produces partial text. You cannot parse a half-complete JSON object into a Pydantic model. The stream is for progress feedback, not for structured parsing.

**Instead:** Use streaming ONLY for progress events ("Generating... 500 chars"). When the stream completes, use the accumulated full text (or a separate `--output-format json` call) to produce the structured Pydantic model for diff/PDF generation.

### Anti-Pattern 5: Global Mutable State for Session Management

**What:** Using a module-level `_ai_sessions: dict` without cleanup, allowing leaked sessions to accumulate.

**Why bad:** If the user navigates away or the SSE connection drops, orphaned queues persist in memory. Over time, this leaks memory.

**Instead:** Always clean up sessions in `finally` blocks (like `apply_engine/engine.py` lines 98-100). Add a timeout to the queue consumer. Consider a TTL-based cleanup sweep on a periodic task.

## Integration Points: Existing vs New Code

### Files Modified

| File | What Changes | Why |
|------|-------------|-----|
| `resume_ai/tailor.py` | Add `tailor_resume_streaming()` async function | New streaming path alongside existing sync |
| `resume_ai/cover_letter.py` | Add `generate_cover_letter_streaming()` async function | Same pattern as tailor |
| `webapp/app.py` | 4 new endpoints: tailor start/stream, cover letter start/stream, AI rescore | SSE streaming + scoring |
| `webapp/db.py` | Migration v7 (3 new columns), `update_ai_score()` helper, bump `SCHEMA_VERSION` to 7 | AI score storage |
| `webapp/templates/job_detail.html` | SSE wiring in AI Resume Tools section, AI score display | Frontend integration |
| `config.py` | Optional: `claude_cli_model` setting in YAML | Model selection |

### Files Created

| File | Purpose | Depends On |
|------|---------|-----------|
| `resume_ai/claude_cli.py` | Claude CLI subprocess wrapper (streaming + non-streaming) | `asyncio`, `json` (stdlib only) |
| `resume_ai/ai_scorer.py` | AI scoring logic, prompt construction, result parsing | `claude_cli.py` |
| `webapp/templates/partials/ai_stream_status.html` | SSE event rendering template for AI streaming | Follows `apply_status.html` pattern |
| `webapp/templates/partials/ai_score_result.html` | AI score display with breakdown | Standard htmx partial |

### Dependencies Between New Components

```
claude_cli.py (foundation -- no internal dependencies)
    |
    +---> tailor.py (adds streaming function, imports stream_prompt)
    |
    +---> cover_letter.py (adds streaming function, imports stream_prompt)
    |
    +---> ai_scorer.py (imports run_prompt for structured output)
              |
              v
         webapp/db.py (migration v7 -- ai_score columns)
              |
              v
         webapp/app.py (new endpoints import tailor, cover_letter, ai_scorer)
              |
              v
         job_detail.html + partials (SSE wiring, score display)
```

## Build Order

The dependency graph dictates this build order:

```
Step 1: resume_ai/claude_cli.py
    |   Core abstraction. No dependencies on existing code.
    |   Test: can stream "hello world" prompt, can run with json-schema.
    v
Step 2: webapp/db.py migration v7
    |   Add ai_score, ai_score_breakdown, ai_scored_at columns.
    |   Bump SCHEMA_VERSION to 7. Add update_ai_score() helper.
    |   Test: migration runs cleanly on existing DB.
    v
Step 3: resume_ai/ai_scorer.py
    |   Depends on: claude_cli.py (step 1), db.py (step 2 for schema).
    |   Test: mock subprocess, verify prompt construction + parsing.
    v
Step 4: resume_ai/tailor.py + cover_letter.py modifications
    |   Add *_streaming() async functions.
    |   Keep existing sync functions untouched.
    |   Depends on: claude_cli.py (step 1).
    v
Step 5: webapp/templates/partials/ (new templates)
    |   ai_stream_status.html following apply_status.html pattern.
    |   ai_score_result.html for score display.
    |   No backend dependency -- pure HTML/Jinja2.
    v
Step 6: webapp/app.py SSE endpoints + AI rescore endpoint
    |   Depends on: steps 3, 4, 5.
    |   New endpoints: tailor start/stream, cover letter start/stream, AI rescore.
    v
Step 7: webapp/templates/job_detail.html modifications
    |   Wire SSE for AI tools section.
    |   Add AI score display.
    |   Depends on: step 6 (endpoints must exist).
    v
Step 8: Integration testing
        End-to-end: click tailor -> see streaming progress -> get result.
```

**Rationale:** Each step builds on the previous with no forward dependencies. Steps 2-4 can potentially be parallelized since they only share claude_cli.py as a dependency, but the sequential order is safer for a single developer workflow.

## Scalability Considerations

| Concern | At 1 user (current) | At 5 concurrent streams | At 10+ concurrent |
|---------|---------------------|------------------------|-------------------|
| Subprocess count | 1 Claude CLI process | 5 concurrent processes | Add semaphore (limit 3) |
| Memory (queues) | Negligible | ~50KB per queue | TTL cleanup, max queue size |
| Claude API rate limits | No concern | Check Anthropic limits | Queue/serialize requests |
| SSE connections | 1 | 5 open connections | EventSourceResponse handles fine |
| SQLite writes | No contention | WAL handles writes | WAL + busy_timeout already set |

For single-user self-hosted use, none of these are real concerns. The semaphore pattern from `apply_engine/engine.py` (line 42: `asyncio.Semaphore(1)`) can be reused if subprocess concurrency becomes an issue.

## Sources

- [Claude Code Headless Mode / Programmatic Usage](https://code.claude.com/docs/en/headless) -- CLI flags, stream-json format, --json-schema
- [Python asyncio Subprocess Documentation](https://docs.python.org/3/library/asyncio-subprocess.html) -- create_subprocess_exec, PIPE, readline
- [sse-starlette GitHub](https://github.com/sysid/sse-starlette) -- EventSourceResponse, async generator pattern
- [Claude Code streaming output issue #733](https://github.com/anthropics/claude-code/issues/733) -- stream-json NDJSON format details
- Codebase analysis: `apply_engine/engine.py` (Queue + SSE pattern), `webapp/app.py` (existing SSE endpoints), `resume_ai/tailor.py` (current Anthropic SDK usage)
