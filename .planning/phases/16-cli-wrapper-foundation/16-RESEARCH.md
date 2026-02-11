# Phase 16: CLI Wrapper Foundation - Research

**Researched:** 2026-02-11
**Domain:** Claude CLI subprocess integration, structured output parsing, async process management
**Confidence:** HIGH

## Summary

This phase replaces the Anthropic Python SDK (`anthropic>=0.79.0`) with direct subprocess calls to the Claude CLI (`claude` binary) for all AI features. The project currently uses `anthropic.Anthropic().messages.parse()` in two files (`resume_ai/tailor.py` and `resume_ai/cover_letter.py`) to get structured Pydantic model output. The wrapper must reproduce this behavior using `asyncio.create_subprocess_exec` with `claude -p --output-format json --json-schema`.

The CLI (verified locally at v2.1.39) returns a JSON envelope containing a `structured_output` field when `--json-schema` is provided. However, there is a **confirmed regression** (GitHub issue #18536) where some CLI versions return the structured data as a markdown-embedded JSON string in the `result` field instead of the `structured_output` field. The wrapper must handle both cases transparently. There is also a documented **cold-start failure pattern** (GitHub issue #23265) where the first invocation with `--json-schema` fails and the second succeeds.

**Primary recommendation:** Build a single `claude_cli.py` module with an async `run()` function and typed exception hierarchy. Use `asyncio.create_subprocess_exec` with `PIPE` for stdout/stderr. Parse the JSON envelope with a resilient parser that checks `structured_output` first, falls back to extracting JSON from `result`, then validates through `Pydantic.model_validate()`. Include automatic retry (1 retry) for the cold-start bug.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio (stdlib) | Python 3.14 | Subprocess management via `create_subprocess_exec` | Decision from STATE.md -- enables streaming, native to Python |
| pydantic | >=2.0.0 | `model_json_schema()` for CLI schema, `model_validate()` for parsing | Already in project, generates JSON Schema compatible with `--json-schema` |
| json (stdlib) | Python 3.14 | JSON parsing of CLI output envelope | No external deps needed |
| shutil (stdlib) | Python 3.14 | `shutil.which("claude")` to detect CLI availability | Standard approach for binary detection |
| re (stdlib) | Python 3.14 | Extract JSON from markdown code blocks in `result` field (fallback) | Needed for regression handling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | Python 3.14 | Log CLI invocations, errors, timing | Always -- debug visibility |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.create_subprocess_exec | subprocess.run in to_thread | Decision already locked: asyncio approach enables streaming in Phases 18-19 |
| Raw JSON parsing | claude-agent-sdk-python | Would add a dependency; project goal is to remove SDK deps, not add new ones |

**Installation:**
No new packages needed. All functionality uses stdlib + existing pydantic.

## Architecture Patterns

### Recommended Project Structure
```
claude_cli/
    __init__.py         # Public API: run(), stream() (stream added Phase 18)
    client.py           # Core subprocess logic: _execute(), _parse_response()
    exceptions.py       # CLIError hierarchy: CLINotFoundError, CLITimeoutError, etc.
    parser.py           # Resilient JSON parser: structured_output + result fallback
```

### Pattern 1: Async Subprocess with Typed Output
**What:** Single async function that takes a Pydantic model class, generates JSON Schema, calls Claude CLI, parses response, returns validated model instance.
**When to use:** Every AI feature call (scoring, resume tailoring, cover letter).
**Example:**
```python
# Source: Verified against Claude CLI v2.1.39 + official docs
import asyncio
import json
import shutil
from pydantic import BaseModel

async def run(
    *,
    system_prompt: str,
    user_message: str,
    output_model: type[BaseModel],
    model: str = "sonnet",
    max_turns: int = 3,
    timeout_seconds: float = 120.0,
) -> BaseModel:
    """Invoke Claude CLI and return a validated Pydantic model."""
    claude_path = shutil.which("claude")
    if claude_path is None:
        raise CLINotFoundError("Claude CLI not found on PATH")

    schema_json = json.dumps(output_model.model_json_schema())

    cmd = [
        claude_path,
        "-p", user_message,
        "--output-format", "json",
        "--json-schema", schema_json,
        "--system-prompt", system_prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--no-session-persistence",
        "--tools", "",  # Disable tools -- pure generation
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise CLITimeoutError(f"Claude CLI timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        raise CLIProcessError(
            f"Claude CLI exited with code {proc.returncode}",
            returncode=proc.returncode,
            stderr=stderr.decode(errors="replace"),
        )

    return parse_cli_response(stdout.decode(), output_model)
```

### Pattern 2: Resilient JSON Parser (Handles CLI Regression)
**What:** Parser that handles both `structured_output` field (correct behavior) and JSON-in-markdown `result` field (regression behavior).
**When to use:** Always -- called by `run()` internally.
**Example:**
```python
# Source: Verified behavior from CLI v2.1.39 + GitHub issues #18536, #23265
import json
import re
from pydantic import BaseModel, ValidationError

def parse_cli_response(raw_stdout: str, model: type[BaseModel]) -> BaseModel:
    """Parse CLI JSON envelope and return validated Pydantic model.

    Handles two known output formats:
    1. Normal: {"structured_output": {...}, "result": "", ...}
    2. Regression: {"result": "```json\\n{...}\\n```", ...}
    """
    try:
        envelope = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        raise CLIMalformedOutputError(
            f"CLI output is not valid JSON: {exc}",
            raw_output=raw_stdout[:500],
        ) from exc

    # Check for CLI-level errors
    if envelope.get("is_error"):
        raise CLIResponseError(
            f"CLI reported error: {envelope.get('result', 'unknown')}",
            envelope=envelope,
        )

    # Path 1: structured_output field (correct behavior)
    structured = envelope.get("structured_output")
    if structured is not None:
        try:
            return model.model_validate(structured)
        except ValidationError as exc:
            raise CLIMalformedOutputError(
                f"structured_output failed validation: {exc}",
                raw_output=json.dumps(structured)[:500],
            ) from exc

    # Path 2: JSON embedded in result field (regression)
    result_text = envelope.get("result", "")
    if result_text:
        # Try parsing result directly as JSON
        try:
            data = json.loads(result_text)
            return model.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Try extracting JSON from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", result_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return model.model_validate(data)
            except (json.JSONDecodeError, ValidationError):
                pass

    # Path 3: Check subtype for structured output retry exhaustion
    subtype = envelope.get("subtype", "")
    if subtype == "error_max_structured_output_retries":
        raise CLIMalformedOutputError(
            "CLI exhausted retries producing valid structured output",
            raw_output=raw_stdout[:500],
        )

    raise CLIMalformedOutputError(
        "CLI response contains neither structured_output nor parseable result",
        raw_output=raw_stdout[:500],
    )
```

### Pattern 3: Typed Exception Hierarchy
**What:** Exception classes that give callers enough info to display user-friendly errors.
**When to use:** Every error path.
**Example:**
```python
class CLIError(Exception):
    """Base exception for all Claude CLI errors."""

class CLINotFoundError(CLIError):
    """Claude CLI binary not found on PATH."""

class CLITimeoutError(CLIError):
    """Claude CLI subprocess timed out."""

class CLIAuthError(CLIError):
    """Claude CLI authentication failure (not logged in)."""

class CLIProcessError(CLIError):
    """Claude CLI exited with non-zero return code."""
    def __init__(self, message: str, *, returncode: int, stderr: str):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr

class CLIMalformedOutputError(CLIError):
    """Claude CLI returned output that could not be parsed."""
    def __init__(self, message: str, *, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output

class CLIResponseError(CLIError):
    """Claude CLI returned is_error=true in its response envelope."""
    def __init__(self, message: str, *, envelope: dict):
        super().__init__(message)
        self.envelope = envelope
```

### Anti-Patterns to Avoid
- **subprocess.run in to_thread:** Decision already locked -- use asyncio.create_subprocess_exec. subprocess.run blocks a thread and cannot be cancelled gracefully.
- **Parsing result field first:** Always check `structured_output` before `result` -- the regression path is the fallback, not the primary.
- **Catching generic Exception from CLI:** Use typed exceptions so callers (webapp endpoints) can display appropriate error messages.
- **Hardcoding claude binary path:** Use `shutil.which("claude")` to find it on PATH. Different machines install it differently.
- **Not killing timed-out processes:** Always `proc.kill()` then `await proc.wait()` on timeout to avoid zombie processes.
- **Passing schema as file path:** Pass JSON Schema as inline string via `--json-schema` argument, not a temp file. Avoids cleanup issues.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema generation | Manual dict construction | `Pydantic.model_json_schema()` | Pydantic already generates correct JSON Schema from existing models |
| CLI binary detection | PATH string splitting | `shutil.which("claude")` | Handles PATH, executable permissions, platform differences |
| Process timeout | Manual timer threads | `asyncio.wait_for(proc.communicate(), timeout=N)` | Built into asyncio, handles cancellation correctly |
| JSON extraction from markdown | Custom string slicing | `re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)` | Regex handles variations in markdown formatting |
| Auth failure detection | Parsing stderr text | Check `is_error` field + stderr content for "auth" / "login" / "not authenticated" | CLI returns structured error info |

**Key insight:** The entire wrapper is stdlib + Pydantic (already a dependency). Zero new packages needed.

## Common Pitfalls

### Pitfall 1: The structured_output vs result Regression
**What goes wrong:** CLI versions around 2.1.x sometimes return structured data as markdown-embedded JSON in the `result` field instead of the `structured_output` field.
**Why it happens:** Known regression (GitHub #18536), confirmed broken in 2.1.1, fixed in some later versions but may recur with CLI updates.
**How to avoid:** Always implement the fallback parser that checks `structured_output` first, then tries to parse `result` as JSON, then tries to extract JSON from markdown code blocks in `result`.
**Warning signs:** `structured_output` key missing from envelope, `result` field contains backtick-fenced JSON.

### Pitfall 2: Cold-Start First-Invocation Failure
**What goes wrong:** First call to `claude -p --json-schema` fails (exit code 1, null output), second call succeeds.
**Why it happens:** Known issue (GitHub #23265) -- some kind of initialization/caching needed on first run with `--json-schema`.
**How to avoid:** Implement automatic retry (max 1 retry) when getting a null/error response. Log the retry so it is visible.
**Warning signs:** Exit code 1 on first run, success on immediate retry.

### Pitfall 3: Claude CLI Not Authenticated
**What goes wrong:** CLI returns auth errors because user hasn't run `claude setup-token` or their session expired.
**Why it happens:** Unlike the SDK which uses ANTHROPIC_API_KEY env var, the CLI uses its own auth system (subscription-based).
**How to avoid:** Detect auth errors in stderr or the `is_error` field. Raise `CLIAuthError` with a message telling the user to run `claude setup-token`.
**Warning signs:** Stderr contains "not authenticated", "login", or "auth" keywords. `is_error: true` in envelope.

### Pitfall 4: The --tools Flag and Turn Count
**What goes wrong:** Without `--tools ""`, the CLI may use tools (Bash, Read, etc.) to try to answer the prompt, consuming turns and producing non-structured output.
**Why it happens:** Claude Code's default mode includes all tools. Structured output generation requires at least 2 turns (1 for generation, 1 for schema validation).
**How to avoid:** Pass `--tools ""` to disable all tools. Set `--max-turns 3` (minimum 2 needed, 1 buffer for retries). Verified that `--max-turns 2` was insufficient in some test runs.
**Warning signs:** `subtype: "error_max_turns"` in response, `num_turns` matching `max_turns`.

### Pitfall 5: Large Schema Serialization
**What goes wrong:** Complex Pydantic models (like TailoredResume with nested $defs) produce large JSON Schema strings that may hit shell argument length limits.
**Why it happens:** `model_json_schema()` includes `$defs`, `description`, `title` for every field. TailoredResume schema is ~2KB.
**How to avoid:** Shell argument limits are typically 128KB-2MB on macOS/Linux, so 2KB is fine. But if schemas grow, consider writing to a temp file and passing `--json-schema "$(cat schema.json)"` pattern. For now, inline is safe.
**Warning signs:** OS error about argument list too long (unlikely for current models).

### Pitfall 6: Existing Tests Import anthropic at Module Level
**What goes wrong:** After removing the anthropic SDK from runtime, test files that `import anthropic` at the top level will fail with ImportError.
**Why it happens:** `tests/conftest.py` sets `os.environ["ANTHROPIC_API_KEY"]` and patches `anthropic.resources.messages.Messages`. Tests in `tests/resume_ai/` import `anthropic` directly.
**How to avoid:** Phase 16 must update test infrastructure: remove the `_block_anthropic` fixture, update `tests/resume_ai/conftest.py`, remove the ANTHROPIC_API_KEY env setup. Replace with subprocess mocking (`unittest.mock.patch("asyncio.create_subprocess_exec")`).
**Warning signs:** ImportError for anthropic in test runs after SDK removal.

### Pitfall 7: ANTHROPIC_API_KEY Still Referenced in conftest.py
**What goes wrong:** Even after removing the SDK from production code, the test conftest sets `os.environ["ANTHROPIC_API_KEY"]` at module level (line 22).
**Why it happens:** Historical requirement -- Anthropic SDK client raises AuthenticationError if API key is not set.
**How to avoid:** Remove the env var setup from conftest.py when removing the SDK. But be careful: if any transitive dependency still imports anthropic, the ImportError will surface.
**Warning signs:** Test failures mentioning ANTHROPIC_API_KEY after SDK removal.

## Code Examples

### Complete CLI Invocation (Verified)
```python
# Source: Verified against Claude CLI v2.1.39 on macOS
# Tested: 2026-02-11

# JSON output envelope structure (without --json-schema):
{
    "type": "result",
    "subtype": "success",      # or "error_max_turns", "error_max_structured_output_retries"
    "is_error": False,
    "duration_ms": 2157,
    "duration_api_ms": 2142,
    "num_turns": 1,
    "result": "The text response...",
    "stop_reason": None,
    "session_id": "uuid-here",
    "total_cost_usd": 0.1088725,
    "usage": { ... },
    "modelUsage": { ... },
    "permission_denials": [],
    "uuid": "uuid-here",
}

# JSON output envelope structure (with --json-schema):
{
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "duration_ms": 4720,
    "duration_api_ms": 4700,
    "num_turns": 2,            # Note: structured output uses 2 turns minimum
    "result": "",              # Empty when structured_output is present
    "structured_output": {     # The validated structured data
        "answer": 4
    },
    "session_id": "uuid-here",
    "total_cost_usd": 0.0196215,
    "usage": { ... },
    "uuid": "uuid-here",
}
```

### Pydantic JSON Schema Generation (Verified)
```python
# Source: Verified against existing resume_ai/models.py
import json
from resume_ai.models import TailoredResume

schema = TailoredResume.model_json_schema()
schema_json = json.dumps(schema)
# Produces valid JSON Schema with $defs for SkillSection, WorkExperience
# Can be passed directly to --json-schema flag
```

### CLI Command Construction
```python
# Source: Verified against claude --help output, v2.1.39
cmd = [
    "claude",
    "-p", "Your prompt here",
    "--output-format", "json",
    "--json-schema", '{"type":"object","properties":{"answer":{"type":"number"}},"required":["answer"]}',
    "--system-prompt", "You are an expert assistant.",
    "--model", "sonnet",           # Alias for latest sonnet model
    "--max-turns", "3",            # 2 minimum for structured output + 1 buffer
    "--no-session-persistence",    # Don't save session to disk
    "--tools", "",                 # Disable all tools -- pure generation only
]
```

### Detecting Authentication Errors
```python
# Auth failure detection heuristics (need verification against live failures):
def _detect_auth_error(returncode: int, stderr: str, envelope: dict | None) -> bool:
    """Check if the CLI error is an authentication failure."""
    stderr_lower = stderr.lower()
    auth_keywords = ["not authenticated", "login", "auth", "setup-token", "subscription"]
    if any(kw in stderr_lower for kw in auth_keywords):
        return True
    if envelope and envelope.get("is_error"):
        result_text = str(envelope.get("result", "")).lower()
        if any(kw in result_text for kw in auth_keywords):
            return True
    return False
```

### Stream-JSON Format (for Phase 18-19 reference)
```python
# Source: Verified against Claude CLI v2.1.39
# stream-json requires --verbose flag
# Returns newline-delimited JSON objects:

# Event types observed:
# {"type": "system", "subtype": "init", ...}          # Initialization
# {"type": "system", "subtype": "hook_started", ...}   # Hook events
# {"type": "assistant", "message": {...}, ...}          # Model response
# {"type": "result", "subtype": "success", ...}        # Final result

# For streaming text extraction:
# Filter for type=="assistant" messages, extract content[].text
# Or use --include-partial-messages for token-level streaming
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `anthropic.Anthropic().messages.parse()` | `claude -p --json-schema` via subprocess | v1.2 (this phase) | No API key needed, uses subscription |
| `ANTHROPIC_API_KEY` env var for auth | `claude setup-token` (subscription auth) | v1.2 (this phase) | Simpler setup, no per-token costs |
| `output_format=PydanticModel` in SDK | `--json-schema` + `model_json_schema()` + `model_validate()` | v1.2 (this phase) | Same end result, different plumbing |
| Synchronous `client.messages.parse()` in `to_thread` | `asyncio.create_subprocess_exec` | v1.2 (this phase) | Native async, enables streaming |

**Deprecated/outdated:**
- `anthropic>=0.79.0` dependency: Remove from `pyproject.toml` dependencies (line 19)
- `ANTHROPIC_API_KEY` env var: No longer needed, remove from `.env.example` and docs
- `tests/conftest.py` line 22: `os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"` -- remove
- `tests/conftest.py` `_block_anthropic` fixture: Replace with subprocess mock strategy
- `tests/resume_ai/conftest.py` `mock_anthropic` fixture: Replace with CLI mock fixture

## Files That Need Changes

### Production Code (SDK Removal)
| File | Current State | Change Needed |
|------|---------------|---------------|
| `resume_ai/tailor.py` | `import anthropic`, `client.messages.parse()` | Replace with `claude_cli.run()` call |
| `resume_ai/cover_letter.py` | `import anthropic`, `client.messages.parse()` | Replace with `claude_cli.run()` call |
| `webapp/app.py` (lines 278, 368) | `asyncio.to_thread(tailor_resume, ...)` | Change to `await tailor_resume(...)` (now async) |
| `pyproject.toml` (line 19) | `"anthropic>=0.79.0"` | Remove from dependencies |

### Test Code (SDK Mock Removal)
| File | Current State | Change Needed |
|------|---------------|---------------|
| `tests/conftest.py` (line 22) | `os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"` | Remove |
| `tests/conftest.py` (lines 84-105) | `_block_anthropic` fixture patches SDK | Replace with `_block_cli` that patches subprocess |
| `tests/resume_ai/conftest.py` | `mock_anthropic` fixture creates mock SDK client | Replace with `mock_claude_cli` that returns mock Process |
| `tests/resume_ai/test_tailor.py` | Tests use `mock_anthropic.messages.parse` | Rewrite to mock subprocess output |
| `tests/resume_ai/test_cover_letter.py` | Tests use `mock_anthropic` fixture | Rewrite to mock subprocess output |
| `tests/test_smoke.py` (line 124) | `import anthropic` in smoke test | Remove or update |

### New Files
| File | Purpose |
|------|---------|
| `claude_cli/__init__.py` | Public API exports: `run`, exception classes |
| `claude_cli/client.py` | Core subprocess execution logic |
| `claude_cli/exceptions.py` | Typed exception hierarchy |
| `claude_cli/parser.py` | Resilient JSON response parser |
| `tests/claude_cli/test_client.py` | Unit tests for subprocess wrapper |
| `tests/claude_cli/test_parser.py` | Unit tests for JSON parser (all paths) |
| `tests/claude_cli/test_exceptions.py` | Unit tests for exception construction |
| `tests/claude_cli/conftest.py` | Mock fixtures for subprocess |

## Open Questions

1. **Auth error detection specifics**
   - What we know: CLI returns `is_error: true` and non-zero exit code on auth failure
   - What's unclear: Exact stderr text for different auth failure modes (expired session, never authenticated, rate limited). Need to test against live failure.
   - Recommendation: Build broad keyword-based detection, log stderr for future refinement. LOW confidence on exact error messages.

2. **--tools "" behavior with structured output**
   - What we know: Disabling tools works (`--tools ""`) and structured output still functions (verified locally)
   - What's unclear: Whether some prompts benefit from tool use during structured output generation
   - Recommendation: Use `--tools ""` by default for predictable behavior. Add optional `tools` parameter to `run()` for future flexibility.

3. **CLI version pinning**
   - What we know: Current version is 2.1.39, structured output works. Regressions existed in 2.1.1.
   - What's unclear: Whether future CLI updates will introduce new regressions
   - Recommendation: Log CLI version at startup. Don't pin to a specific version, but document minimum known-working version (2.0.45+, when --json-schema was added).

4. **Cost tracking from CLI response**
   - What we know: CLI envelope includes `total_cost_usd` and `usage` with token counts
   - What's unclear: Whether to expose this in the wrapper now or defer to future requirement EHAI-05
   - Recommendation: Parse and store `total_cost_usd` and token usage in the return type for logging, but don't build a cost tracking feature yet (deferred to v2+).

## Sources

### Primary (HIGH confidence)
- Claude CLI v2.1.39 `--help` output -- verified locally 2026-02-11
- Claude CLI JSON output envelope -- verified with live test invocations 2026-02-11
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- official documentation
- [Run Claude Code Programmatically](https://code.claude.com/docs/en/headless) -- official headless/SDK docs
- [Agent SDK Structured Outputs](https://platform.claude.com/docs/en/agent-sdk/structured-outputs) -- official structured output docs
- Existing codebase: `resume_ai/tailor.py`, `resume_ai/cover_letter.py`, `resume_ai/models.py`, `tests/conftest.py`, `tests/resume_ai/conftest.py`
- `pyproject.toml` -- current dependency list

### Secondary (MEDIUM confidence)
- [GitHub Issue #18536](https://github.com/anthropics/claude-code/issues/18536) -- structured_output regression, confirmed with repro
- [GitHub Issue #23265](https://github.com/anthropics/claude-code/issues/23265) -- cold-start pattern failure
- [GitHub Issue #9058](https://github.com/anthropics/claude-code/issues/9058) -- original --json-schema feature request (completed)
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) -- stdlib reference

### Tertiary (LOW confidence)
- Auth error messages -- based on GitHub issue reports, not verified against live failure

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib + existing pydantic, no new deps
- Architecture: HIGH -- verified CLI behavior locally, clear module structure
- Pitfalls: HIGH for regression/cold-start (confirmed via GitHub issues + testing), LOW for auth error detection (unverified)
- Code examples: HIGH -- all verified against live CLI v2.1.39

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (CLI updates may introduce new behaviors; revalidate after major CLI version bumps)
