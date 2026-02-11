# Technology Stack: Claude CLI Agent Integration

**Project:** JobFlow v2 -- Claude CLI Subprocess Integration, SSE Streaming for AI Features, On-Demand AI Scoring
**Researched:** 2026-02-11

## Executive Summary

This milestone replaces the `anthropic.Anthropic().messages.parse()` SDK calls with `claude -p` subprocess invocations and adds SSE streaming to resume/cover letter generation endpoints. The stack changes are minimal -- zero new dependencies. Python 3.14's `asyncio.create_subprocess_exec` handles Claude CLI subprocesses, the existing `sse-starlette>=2.0.0` handles SSE streaming (identical pattern to apply engine), and Pydantic v2's `model_json_schema()` generates the `--json-schema` payloads. The `anthropic` SDK dependency can be removed from production requirements.

## Recommended Stack

### Claude CLI Integration (NEW)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Claude CLI (`claude`) | >=2.1.39 | LLM inference via subprocess | Already installed on the target machine (verified: v2.1.39). The `-p --output-format json --json-schema` flags provide structured output identical to `messages.parse()` but without API key management, SDK version coupling, or per-token billing through the SDK. Uses the user's existing Claude subscription. |
| `asyncio.create_subprocess_exec` | stdlib | Async subprocess management | Python 3.14 stdlib. Streams stdout line-by-line via `process.stdout.readline()` for SSE forwarding. No external dependency needed. |
| `json` | stdlib | Parse CLI response / generate schema | Stdlib. Parses the JSON response envelope (`structured_output` field) and serializes Pydantic JSON schemas for `--json-schema`. |

### SSE Streaming (EXISTING -- reuse pattern)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sse-starlette | >=2.0.0 (have), latest 3.2.0 | Server-Sent Events | Already a dependency. The apply engine SSE pattern (`EventSourceResponse` + `asyncio.Queue` + async generator) is directly reusable for resume/cover letter streaming. No version bump required -- 2.0.0 works fine, but 3.2.0 is available if upgrading. |
| htmx SSE extension | already in use | Client-side SSE consumption | Already in the dashboard. `hx-ext="sse"`, `sse-connect`, `sse-swap` attributes. Same pattern as apply engine streaming. |

### Structured Output (EXISTING -- leverage Pydantic)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pydantic v2 | >=2.0.0 (have) | JSON Schema generation + response validation | `TailoredResume.model_json_schema()` produces the exact JSON Schema that `claude -p --json-schema` requires. After CLI returns, `TailoredResume.model_validate(data["structured_output"])` reconstructs the typed model. Zero new code for schema generation. |

### On-Demand Scoring (EXISTING -- no new deps)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Existing `scorer.py` | N/A | Job scoring engine | Already implements `JobScorer.score_job_with_breakdown()`. The new endpoint just wraps this in an async FastAPI route with `asyncio.to_thread()` for the computation. |
| SQLite | existing | Score persistence | `db.py` already has `upsert_jobs()` which handles score updates. |

## What NOT to Add

| Library | Why Not |
|---------|---------|
| `anthropic` SDK (REMOVE from production) | The whole point of this milestone is replacing SDK calls with CLI subprocess calls. Move `anthropic>=0.79.0` from `dependencies` to `dev` group (still needed for tests that mock the old interface during migration). |
| `aiofiles` | Not needed. `asyncio.create_subprocess_exec` handles async I/O natively. |
| `anyio` | Not needed. Pure asyncio is sufficient -- no trio support required. |
| `claude-agent-sdk-python` | Overkill. The CLI `-p` flag provides everything needed. The Python SDK adds complexity, a new dependency, and no additional value for this use case (simple prompt-in, structured-JSON-out). |
| `websockets` | SSE is unidirectional (server-to-client), which is exactly what we need. WebSockets add bidirectional complexity for zero benefit here. |
| `celery` / `dramatiq` | Background task queues are unnecessary. `asyncio.create_subprocess_exec` + `asyncio.Queue` provides the same async subprocess + event streaming without infrastructure overhead. Single-user app. |

## Claude CLI Response Format (Verified)

### Standard JSON (`--output-format json`)

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "duration_ms": 19342,
  "duration_api_ms": 19329,
  "num_turns": 1,
  "result": "...(text response)...",
  "stop_reason": null,
  "session_id": "a7285b81-...",
  "total_cost_usd": 0.017168,
  "usage": { "input_tokens": 2, "output_tokens": 339, ... },
  "modelUsage": { ... },
  "permission_denials": [],
  "uuid": "eb4ddc52-..."
}
```

### With `--json-schema` (adds `structured_output` field)

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "result": "",
  "structured_output": { ... validated JSON matching schema ... },
  "session_id": "...",
  "total_cost_usd": 0.017168,
  "usage": { ... },
  ...
}
```

Key details (verified locally with Claude CLI 2.1.39):
- `result` is empty string when `--json-schema` is used (all output goes to `structured_output`)
- `structured_output` contains the validated JSON object matching the provided schema
- `is_error` is `false` on success, `true` on failure
- `total_cost_usd` tracks spend per call (useful for budget tracking)

### Stream JSON (`--output-format stream-json`)

NDJSON (newline-delimited JSON). Each line is an event object:

```json
{"type":"system","subtype":"init","session_id":"...","model":"claude-sonnet-4-5-20250929",...}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"Hi"}},...}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"! I'm ready"}},...}
{"type":"result","subtype":"success","result":"...","structured_output":{...},...}
```

Key event types for streaming:
- `type: "system", subtype: "init"` -- session initialization (skip)
- `type: "stream_event"` with `event.delta.type == "text_delta"` -- text tokens
- `type: "result"` -- final result with `structured_output` (terminal event)

## CLI Flags Reference

| Flag | Purpose | Value |
|------|---------|-------|
| `-p` / `--print` | Non-interactive mode (required) | N/A |
| `--output-format json` | JSON response envelope | For non-streaming calls |
| `--output-format stream-json` | NDJSON streaming | For SSE-streamed calls |
| `--json-schema '<schema>'` | Structured output validation | Pydantic's `model_json_schema()` output |
| `--model sonnet` | Model selection | Use alias `sonnet` for latest Sonnet |
| `--system-prompt '<prompt>'` | Replace default system prompt | Resume/cover letter system prompts |
| `--tools ""` | Disable all tools | Prevent Claude from using Bash/Edit/etc -- pure LLM inference only |
| `--no-session-persistence` | Don't save session to disk | Prevent session file accumulation from automated calls |
| `--max-budget-usd <amount>` | Spend cap per call | Safety limit (e.g., 0.50 for resume, 0.25 for cover letter) |
| `--verbose` | Include partial messages | Required with `--include-partial-messages` for streaming |
| `--include-partial-messages` | Stream token-by-token | Required for SSE text streaming |

## Integration Architecture

### Subprocess Wrapper (`claude_cli.py`)

```python
import asyncio
import json
from pydantic import BaseModel

async def call_claude(
    prompt: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    model: str = "sonnet",
    max_budget_usd: float = 0.50,
) -> dict:
    """Call Claude CLI with structured output, return parsed response."""
    schema_json = json.dumps(output_schema.model_json_schema())

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p",
        "--output-format", "json",
        "--json-schema", schema_json,
        "--system-prompt", system_prompt,
        "--model", model,
        "--tools", "",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate(prompt.encode())
    response = json.loads(stdout)

    if response.get("is_error"):
        raise RuntimeError(f"Claude CLI error: {response.get('result', stderr.decode())}")

    return response
```

### Streaming Wrapper (for SSE)

```python
async def stream_claude(
    prompt: str,
    system_prompt: str,
    model: str = "sonnet",
) -> AsyncGenerator[str, None]:
    """Stream text deltas from Claude CLI as they arrive."""
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p",
        "--output-format", "stream-json",
        "--system-prompt", system_prompt,
        "--model", model,
        "--tools", "",
        "--no-session-persistence",
        "--verbose",
        "--include-partial-messages",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    proc.stdin.write(prompt.encode())
    proc.stdin.close()

    async for line in proc.stdout:
        event = json.loads(line)
        if (event.get("type") == "stream_event"
            and event.get("event", {}).get("delta", {}).get("type") == "text_delta"):
            yield event["event"]["delta"]["text"]
```

### SSE Endpoint Pattern (mirroring apply engine)

```python
from sse_starlette import EventSourceResponse

@app.post("/jobs/{dedup_key:path}/tailor-resume-stream")
async def tailor_resume_stream(request: Request, dedup_key: str):
    # ... validation, resume extraction ...

    async def event_generator():
        async for text_chunk in stream_claude(prompt, SYSTEM_PROMPT):
            html = f'<span>{text_chunk}</span>'
            yield {"event": "progress", "data": html}
        # Final result with structured output
        result = await call_claude(prompt, SYSTEM_PROMPT, TailoredResume)
        tailored = TailoredResume.model_validate(result["structured_output"])
        # ... render PDF, validate, etc ...
        yield {"event": "done", "data": final_html}

    return EventSourceResponse(event_generator())
```

## Pydantic JSON Schema Compatibility

Verified: `TailoredResume.model_json_schema()` produces valid JSON Schema that `claude -p --json-schema` accepts. The schema includes `$defs` for nested models (`SkillSection`, `WorkExperience`), `description` fields from Pydantic `Field(description=...)`, and proper `type` annotations. No transformation needed.

The `CoverLetter.model_json_schema()` similarly works out of the box.

## Config Changes

### config.yaml additions

```yaml
claude_cli:
  model: "sonnet"                    # Model alias (sonnet = latest Claude Sonnet)
  max_budget_resume: 0.50            # USD spend cap for resume tailoring
  max_budget_cover_letter: 0.25      # USD spend cap for cover letter generation
  max_budget_scoring: 0.10           # USD spend cap for AI-enhanced scoring (if added)
  timeout: 120                       # Seconds before killing subprocess
```

### pyproject.toml changes

```toml
# REMOVE from dependencies:
#   "anthropic>=0.79.0",

# ADD to dev dependencies (for test mocking during migration):
#   "anthropic>=0.79.0",
```

## Installation

```bash
# No new pip packages needed!

# Verify Claude CLI is available
claude --version  # Should be >=2.1.39

# Optional: upgrade sse-starlette (not required)
uv add "sse-starlette>=3.2.0"
```

## Sources

- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- all CLI flags, `--output-format`, `--json-schema` (HIGH confidence, official docs)
- [Run Claude Code Programmatically](https://code.claude.com/docs/en/headless) -- `-p` mode, structured output, streaming (HIGH confidence, official docs)
- [sse-starlette on PyPI](https://pypi.org/project/sse-starlette/) -- version 3.2.0, Jan 2026 (HIGH confidence)
- [Python 3.14 asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) -- `create_subprocess_exec`, `readline()` streaming (HIGH confidence)
- Local verification: Claude CLI 2.1.39 response format tested with `--output-format json` and `--json-schema` (HIGH confidence, verified 2026-02-11)
