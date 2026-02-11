# Domain Pitfalls: Claude CLI Subprocess, SSE Streaming, and AI Scoring Integration

**Domain:** Adding Claude CLI subprocess integration, SSE streaming for AI features, and on-demand AI scoring to an existing FastAPI + htmx + SQLite job search automation app
**Researched:** 2026-02-11
**Confidence:** HIGH (grounded in direct codebase analysis of `webapp/app.py`, `scorer.py`, `webapp/db.py`, `resume_ai/tailor.py`, `apply_engine/engine.py`, and verified against official documentation for Claude CLI, htmx SSE extension, FastAPI, and SQLite)

---

## Critical Pitfalls

Mistakes that cause hangs, data corruption, broken UI, or require rewrites.

---

### Pitfall 1: `subprocess.run()` with Claude CLI Hangs Indefinitely, Blocking FastAPI's Event Loop

**What goes wrong:** The Claude CLI (`claude -p "..." --output-format json`) is invoked via `subprocess.run()` from an async FastAPI endpoint. The CLI call takes 5-60+ seconds depending on prompt complexity. If called directly inside an `async def` endpoint, it blocks the entire event loop -- no other requests are served. If wrapped in `asyncio.to_thread()`, the thread still blocks until the CLI returns. If the CLI hangs (network issue, Anthropic API outage, rate limit), the thread never returns, the timeout is never triggered, and the request hangs until the client disconnects.

The existing codebase already uses `asyncio.to_thread()` for LLM calls in `tailor_resume_endpoint` (line 278 of `webapp/app.py`) and `cover_letter_endpoint` (line 367). Replacing the SDK calls with CLI subprocess calls inherits the same pattern -- but subprocess.run has additional failure modes that the SDK doesn't: the CLI process can become a zombie, stderr can fill the pipe buffer causing a deadlock, or the CLI can prompt for input (e.g., permission dialogs) and block forever.

**Why it happens:** `subprocess.run(capture_output=True)` internally calls `Popen.communicate()`, which handles stdout/stderr reading safely. But `subprocess.run(timeout=60)` only kills the process after the timeout -- it does NOT prevent the 4KB pipe buffer deadlock if you're manually managing pipes. Also, the Claude CLI is a Node.js process that spawns child processes; `process.kill()` sends SIGTERM to the parent, but the Node.js child workers may continue running.

**Consequences:**
- FastAPI becomes unresponsive to all requests while a CLI call hangs
- Zombie Node.js processes accumulate if timeouts kill the parent but not children
- If stderr is not captured, error messages from the CLI are lost, making debugging impossible
- Memory leak from accumulated subprocess handles that were never waited on

**Prevention:**
1. Always use `subprocess.run()` with BOTH `capture_output=True` and `timeout=N`:
   ```python
   result = subprocess.run(
       ["claude", "-p", prompt, "--output-format", "json"],
       capture_output=True,
       text=True,
       timeout=120,
   )
   ```
   `capture_output=True` is safe because it uses `communicate()` internally, avoiding the pipe buffer deadlock.

2. Wrap the `subprocess.run` call in `asyncio.to_thread()` just as the current SDK calls are wrapped:
   ```python
   result = await asyncio.to_thread(_run_claude_cli, prompt, json_schema)
   ```

3. Handle `subprocess.TimeoutExpired` explicitly and kill the process tree, not just the parent:
   ```python
   try:
       result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
   except subprocess.TimeoutExpired as exc:
       # subprocess.run already kills the process on timeout, but children may survive
       logger.error("Claude CLI timed out after 120s: %s", exc.stderr)
       raise RuntimeError("AI scoring timed out -- the Claude CLI did not respond") from exc
   ```

4. Never use `subprocess.Popen` with manual pipe management for the CLI -- always use `subprocess.run` with `capture_output=True` which handles pipe reading correctly.

5. For the alternative async approach, use `asyncio.create_subprocess_exec`:
   ```python
   proc = await asyncio.create_subprocess_exec(
       "claude", "-p", prompt, "--output-format", "json",
       stdout=asyncio.subprocess.PIPE,
       stderr=asyncio.subprocess.PIPE,
   )
   try:
       stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
   except asyncio.TimeoutError:
       proc.kill()
       await proc.wait()
       raise
   ```
   This is fully async and does not block any event loop thread.

**Detection (warning signs):**
- Dashboard becomes unresponsive during AI scoring operations
- `ps aux | grep claude` shows orphaned Node.js processes
- Memory usage grows over time with many CLI invocations
- Error messages like "AI scoring failed" with no details (stderr was lost)

**Phase:** First phase -- the subprocess wrapper must be rock-solid before any feature uses it.

**Confidence:** HIGH -- verified against Python 3.14 subprocess documentation, FastAPI async/await documentation, and the existing `asyncio.to_thread` pattern in `webapp/app.py`.

**Sources:**
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
- [Python asyncio subprocess documentation](https://docs.python.org/3/library/asyncio-subprocess.html)
- [FastAPI concurrency and async/await](https://fastapi.tiangolo.com/async/)

---

### Pitfall 2: Claude CLI `--json-schema` Regression -- `structured_output` Field Missing in v2.1.x

**What goes wrong:** You pass a Pydantic v2 model's JSON schema to `claude -p --output-format json --json-schema '...'` expecting the response to have a `structured_output` field containing parsed JSON matching your schema. Instead, the CLI returns the schema-conforming JSON embedded as a markdown code block inside the `result` text field. This is a **known regression** introduced between Claude CLI v2.0.76 and v2.1.1 (GitHub issue #18536).

The existing codebase uses Pydantic v2 models extensively (`TailoredResume`, `CoverLetter`, `ScoreBreakdown`). Generating the JSON schema from these models with `TailoredResume.model_json_schema()` produces a schema with `$defs` and `$ref` for nested types (`SkillSection`, `WorkExperience`). The CLI's `--json-schema` flag was designed to handle standard JSON Schema, but the `$ref`/`$defs` structure from Pydantic's nested models may not be fully supported or may trigger the regression.

**Why it happens:** The Claude CLI underwent a major version bump (2.0.x to 2.1.x) that changed how structured outputs are processed. The `--json-schema` feature was implemented in v2.0.45 and worked correctly through v2.0.76, but the internal response handling changed in v2.1.1, causing the structured output to be rendered as text rather than parsed as JSON.

**Consequences:**
- Parsing the CLI response with `json.loads(result["structured_output"])` fails with `KeyError`
- Falling back to `result["result"]` gives you a string containing markdown, not JSON
- The JSON embedded in the markdown may not conform to your schema (type mismatches, missing fields)
- Pydantic validation on the extracted JSON fails intermittently
- Tests pass with one CLI version but break with another

**Prevention:**
1. Pin the Claude CLI version in your project and CI. Document which version is known-working. Test with that specific version before deploying.

2. Build a resilient response parser that handles BOTH the correct format and the regression format:
   ```python
   def parse_cli_response(raw_json: dict) -> dict:
       # Correct format (v2.0.x)
       if "structured_output" in raw_json and raw_json["structured_output"] is not None:
           return raw_json["structured_output"]
       # Regression format (v2.1.x) -- extract JSON from markdown in result
       result_text = raw_json.get("result", "")
       json_match = re.search(r"```json\s*\n(.*?)\n```", result_text, re.DOTALL)
       if json_match:
           return json.loads(json_match.group(1))
       # Last resort -- try parsing the result directly
       return json.loads(result_text)
   ```

3. Always validate the parsed output against the Pydantic model, regardless of how it was extracted:
   ```python
   parsed = parse_cli_response(raw)
   score_result = AIScoreResult.model_validate(parsed)
   ```

4. For the Pydantic `$ref`/`$defs` issue: generate a **flattened** JSON schema instead of the default nested one. Pydantic v2 supports `model_json_schema(mode="serialization")` and custom schema generation:
   ```python
   schema = AIScoreResult.model_json_schema()
   # Inline $defs to remove $ref (some tools don't handle $ref well)
   import jsonschema
   resolved = jsonschema.RefResolver.from_schema(schema)
   ```
   Or simpler: keep the AI scoring output model flat (no nested Pydantic models in the schema passed to CLI).

5. Consider a dual-path approach: try `--json-schema` first, fall back to prompt-based JSON extraction with validation if structured output fails.

**Detection (warning signs):**
- `KeyError: 'structured_output'` in production logs
- AI scoring returns `None` or empty results intermittently
- CLI version upgrade breaks all AI features simultaneously
- Different behavior between local development and CI (different CLI versions)

**Phase:** First phase -- build the CLI wrapper with regression handling before implementing any feature on top of it.

**Confidence:** MEDIUM -- the regression is documented in [GitHub issue #18536](https://github.com/anthropics/claude-code/issues/18536) but may be fixed in a future release. The `$ref`/`$defs` concern is based on Pydantic v2 documentation and general JSON Schema tooling experience.

**Sources:**
- [Claude CLI --json-schema bug (GitHub #18536)](https://github.com/anthropics/claude-code/issues/18536)
- [Claude Code headless mode documentation](https://code.claude.com/docs/en/headless)
- [Pydantic v2 JSON Schema documentation](https://docs.pydantic.dev/latest/concepts/json_schema/)

---

### Pitfall 3: SSE Connection Leak When User Navigates Away During AI Scoring

**What goes wrong:** A new AI scoring endpoint uses SSE to stream progress events (like the existing apply engine does). The user clicks "AI Score" on a job, the frontend opens an SSE connection via htmx's `sse-connect`, and the backend starts a Claude CLI subprocess. The user navigates to a different page (clicks "Dashboard", "Kanban", etc.) while the AI scoring is in progress. The htmx SSE extension closes the EventSource on the client side (because the DOM element is removed), but the backend doesn't know the client disconnected -- the CLI subprocess continues running, the asyncio.Queue continues accumulating events, and the `event_generator()` coroutine continues looping.

The existing apply engine has this exact pattern (lines 530-561 of `webapp/app.py`): it checks `request.is_disconnected()` in the event generator, but this check only runs when the generator yields. If the generator is blocked on `asyncio.wait_for(queue.get(), timeout=15)`, it won't check disconnection for up to 15 seconds. During those 15 seconds, the CLI subprocess is still running and burning tokens.

**Why it happens:** SSE is unidirectional -- the client can close the connection, but the server only discovers this when it tries to write to the connection. The `request.is_disconnected()` check is cooperative: it only works when the coroutine yields control. The Claude CLI subprocess runs independently of the SSE connection and has no way to know the client left.

**Consequences:**
- Wasted Claude API tokens on scoring jobs the user doesn't care about
- Accumulated `asyncio.Queue` objects consuming memory (never garbage collected because the generator still holds a reference)
- Orphaned CLI subprocesses consuming system resources
- If many users (even a single user rapidly navigating) trigger multiple scorings and navigate away, the server accumulates zombie coroutines and subprocesses

**Prevention:**
1. Use htmx's `sse-close` attribute to gracefully close the connection when a specific event is received:
   ```html
   <div hx-ext="sse"
        sse-connect="/jobs/{key}/ai-score/stream"
        sse-swap="progress"
        sse-close="done">
   ```

2. Reduce the queue polling timeout to 1-2 seconds so disconnection is detected faster:
   ```python
   async def event_generator():
       try:
           while True:
               if await request.is_disconnected():
                   _cancel_cli_process(dedup_key)
                   break
               try:
                   event = await asyncio.wait_for(queue.get(), timeout=2)
                   yield {"event": event_type, "data": html}
                   if event_type == "done":
                       break
               except TimeoutError:
                   yield {"event": "ping", "data": ""}
       except asyncio.CancelledError:
           _cancel_cli_process(dedup_key)
   ```

3. Store the subprocess `Popen` handle alongside the queue in the session dict, so it can be killed on disconnect:
   ```python
   _sessions[dedup_key] = {"queue": queue, "process": proc}
   ```

4. Add a background cleanup task that periodically checks for stale sessions (no events emitted for 5+ minutes) and kills their subprocesses.

5. On the htmx side, listen for `htmx:sseClose` to trigger cleanup:
   ```html
   <div hx-ext="sse"
        sse-connect="..."
        hx-on:htmx:sseClose="htmx.ajax('POST', '/jobs/{key}/ai-score/cancel')">
   ```

**Detection (warning signs):**
- Server memory grows over time during development sessions
- `ps aux | grep claude` shows many CLI processes after navigating around the dashboard
- SSE connections in browser DevTools Network tab show "pending" connections that never close
- Server logs show "ping" events being sent to connections where no client is listening

**Phase:** Must be addressed when designing the SSE streaming architecture for AI scoring, before implementation.

**Confidence:** HIGH -- verified by reading the existing apply engine SSE implementation in `webapp/app.py` (lines 530-561), the htmx SSE extension documentation, and `sse-starlette` disconnect handling.

**Sources:**
- [htmx SSE extension documentation](https://htmx.org/extensions/sse/)
- [htmx SSE close connection discussion (#2393)](https://github.com/bigskysoftware/htmx/issues/2393)
- [sse-starlette documentation](https://github.com/sysid/sse-starlette)
- [FastAPI disconnect detection (#9398)](https://github.com/fastapi/fastapi/discussions/9398)

---

### Pitfall 4: SQLite ALTER TABLE ADD COLUMN for AI Scoring Breaks FTS5 Triggers

**What goes wrong:** Adding new columns to the `jobs` table (e.g., `ai_score INTEGER`, `ai_score_explanation TEXT`, `ai_scored_at TEXT`) via `ALTER TABLE jobs ADD COLUMN` works for the `jobs` table itself but silently invalidates the FTS5 content sync triggers. The current FTS5 setup (migration version 4, lines 83-124 of `webapp/db.py`) uses content-sync triggers that reference specific columns: `title`, `company`, `description`. The FTS5 virtual table was created with `content='jobs', content_rowid=rowid`. When you add new columns to `jobs`, the FTS5 table's rowid-based content mapping still works, but if you want the new columns to be FTS-searchable (e.g., searching AI score explanations), you need to:
1. Drop and recreate the FTS5 virtual table with the new columns
2. Drop and recreate all three triggers (AFTER INSERT, AFTER DELETE, AFTER UPDATE)
3. Rebuild the FTS index

Doing step 1 without step 3 means existing data is not indexed in the new FTS table. Doing steps 1-2 without step 3 means the triggers only capture NEW data. The current migration system handles this with `INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')`, but a migration that adds the new columns must be carefully ordered.

**Why it happens:** SQLite's FTS5 content-sync mechanism maintains a mapping between the `jobs` table and the FTS index via triggers. Adding columns to `jobs` does not automatically add them to FTS5. The FTS5 virtual table schema is fixed at creation time.

Additionally, SQLite's `ALTER TABLE ADD COLUMN` has limitations: the new column CANNOT have a DEFAULT value that is an expression (like `CURRENT_TIMESTAMP` or `(datetime('now'))`). It CAN have a literal DEFAULT (`DEFAULT 0`, `DEFAULT ''`, `DEFAULT NULL`). The current `ai_scored_at` column should use `DEFAULT NULL`, not `DEFAULT (datetime('now'))`.

**Consequences:**
- `ALTER TABLE jobs ADD COLUMN ai_scored_at TEXT DEFAULT (datetime('now'))` fails with a SQLite error
- FTS search returns results that don't include AI score explanations even after adding the column to FTS
- Existing jobs have no FTS entries for the new columns even after adding triggers
- If migration version 7 adds columns but version 8 adds FTS, a crash between versions 7 and 8 leaves an inconsistent state

**Prevention:**
1. Keep new AI scoring columns OUT of FTS5. The `ai_score_explanation` is long-form text that benefits from FTS, but add it as a separate migration step with explicit FTS rebuild:
   ```python
   MIGRATIONS[7] = [
       "ALTER TABLE jobs ADD COLUMN ai_score INTEGER",
       "ALTER TABLE jobs ADD COLUMN ai_score_explanation TEXT",
       "ALTER TABLE jobs ADD COLUMN ai_scored_at TEXT",  # No DEFAULT expression!
   ]
   ```

2. If AI score explanations should be FTS-searchable, add a SEPARATE migration version that modifies FTS5:
   ```python
   MIGRATIONS[8] = [
       "DROP TRIGGER IF EXISTS jobs_fts_ai",
       "DROP TRIGGER IF EXISTS jobs_fts_ad",
       "DROP TRIGGER IF EXISTS jobs_fts_au",
       "DROP TABLE IF EXISTS jobs_fts",
       """CREATE VIRTUAL TABLE jobs_fts USING fts5(
           title, company, description, ai_score_explanation,
           content='jobs', content_rowid=rowid
       )""",
       # Recreate all three triggers with the new column list
       # ...
       "INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')",
   ]
   ```

3. Use `DEFAULT NULL` or no DEFAULT for new timestamp columns. Populate `ai_scored_at` in application code when the AI scoring actually runs:
   ```python
   conn.execute(
       "UPDATE jobs SET ai_score = ?, ai_score_explanation = ?, ai_scored_at = ? WHERE dedup_key = ?",
       (score, explanation, datetime.now().isoformat(), dedup_key),
   )
   ```

4. Test the migration chain in unit tests: apply migrations 1 through N on a fresh database and verify the schema matches expectations. The existing test suite should already test this (see previous pitfalls document).

**Detection (warning signs):**
- `sqlite3.OperationalError: cannot use a non-deterministic function in CHECK or DEFAULT`
- FTS search for AI explanation text returns zero results
- Migration works on fresh database but fails on existing database (column already exists from manual testing)
- `get_jobs(search="machine learning")` doesn't find jobs whose AI explanation mentions machine learning

**Phase:** Database schema changes should be done FIRST in the milestone, before any AI scoring logic. The migration must be in place before the scoring endpoint writes to the new columns.

**Confidence:** HIGH -- verified against SQLite ALTER TABLE documentation, the existing migration chain in `webapp/db.py` (lines 53-145), and the FTS5 extension documentation.

**Sources:**
- [SQLite ALTER TABLE documentation](https://www.sqlite.org/lang_altertable.html)
- [SQLite FTS5 Extension documentation](https://sqlite.org/fts5.html)
- [SQLite FTS5 trigger corruption forum post](https://sqlite.org/forum/info/da59bf102d7a7951740bd01c4942b1119512a86bfa1b11d4f762056c8eb7fc4e)

---

### Pitfall 5: Converting Pydantic SDK `messages.parse()` to CLI `--json-schema` Changes Error Semantics

**What goes wrong:** The current resume tailoring code (`resume_ai/tailor.py`) uses `client.messages.parse(output_format=TailoredResume)` which returns a typed Pydantic object directly -- the SDK handles JSON parsing and Pydantic validation internally. Errors are typed: `anthropic.AuthenticationError`, `anthropic.APIError`, and the `parsed_output is None` case.

When switching to the CLI, ALL errors become `subprocess.CalledProcessError` (non-zero exit code), `subprocess.TimeoutExpired`, or "the JSON in stdout doesn't match the schema." The rich error taxonomy collapses into generic subprocess errors. The existing error handling in `tailor_resume` (lines 86-123) catches `AuthenticationError` and `APIError` separately to provide useful error messages -- these specific error types disappear when using the CLI.

Furthermore, the CLI's error output goes to stderr as human-readable text, not structured JSON. Parsing stderr to extract the error type is fragile and version-dependent.

**Why it happens:** The Anthropic Python SDK provides typed exceptions because it controls the HTTP interaction. The CLI is a separate process that communicates via stdout/stderr text. The process boundary erases type information.

**Consequences:**
- Error messages in the dashboard become generic ("AI scoring failed") instead of specific ("API key invalid", "Rate limited, retry in 30s", "Model refused to generate output")
- The distinction between retryable errors (rate limit, timeout) and permanent errors (bad API key, invalid schema) is lost
- The existing test mocks that patch `anthropic.Anthropic` and raise typed exceptions no longer apply -- all test mocks must be rewritten to mock `subprocess.run` instead
- The 428+ existing tests that mock the Anthropic SDK become dead code

**Prevention:**
1. Build a CLI wrapper that reconstitutes typed errors from the subprocess output:
   ```python
   class CLIError(RuntimeError):
       """Base error for CLI subprocess failures."""
       pass

   class CLITimeoutError(CLIError):
       """CLI process exceeded timeout."""
       pass

   class CLIAuthError(CLIError):
       """API key missing or invalid."""
       pass

   class CLIRateLimitError(CLIError):
       """Rate limited, should retry after delay."""
       retry_after: float = 60.0

   def run_claude_cli(prompt: str, json_schema: dict | None = None, timeout: int = 120) -> dict:
       try:
           result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
       except subprocess.TimeoutExpired as exc:
           raise CLITimeoutError(f"CLI timed out after {timeout}s") from exc

       if result.returncode != 0:
           stderr = result.stderr.lower()
           if "authentication" in stderr or "api key" in stderr:
               raise CLIAuthError("Invalid or missing API key")
           if "rate limit" in stderr:
               raise CLIRateLimitError("Rate limited")
           raise CLIError(f"CLI failed (exit {result.returncode}): {result.stderr[:500]}")

       return json.loads(result.stdout)
   ```

2. Create an abstraction layer that both the SDK path and the CLI path can implement:
   ```python
   class AIProvider(Protocol):
       def score_job(self, job_description: str, resume_text: str) -> AIScoreResult: ...
       def tailor_resume(self, ...) -> TailoredResume: ...
   ```
   This allows the test suite to mock at the provider level regardless of whether the implementation uses SDK or CLI.

3. Update the test mock strategy: instead of patching `anthropic.Anthropic`, patch the `run_claude_cli` wrapper function. This is a ONE-TIME migration for all 428+ tests.

4. Keep the existing SDK-based code as a fallback. The CLI wrapper can try CLI first and fall back to SDK if `claude` is not in PATH.

**Detection (warning signs):**
- Error messages in the dashboard become "subprocess.CalledProcessError" -- meaningless to the user
- Tests that mock `anthropic.Anthropic` pass but the real CLI code path is never tested
- Rate limit errors cause immediate failure instead of retry
- Auth errors are not detected until after a long timeout

**Phase:** Design the abstraction layer BEFORE converting any existing SDK calls to CLI calls. The wrapper is the foundation for everything else.

**Confidence:** HIGH -- verified by reading the existing error handling in `resume_ai/tailor.py` (lines 86-123), the test mocks in `tests/resume_ai/conftest.py`, and the global API blocker in `tests/conftest.py` (lines 84-105).

---

## Moderate Pitfalls

Mistakes that cause degraded UX, test failures, or integration issues.

---

### Pitfall 6: Existing htmx POST Endpoints Cannot Be Trivially Converted to SSE

**What goes wrong:** The current "Tailor Resume" and "Generate Cover Letter" buttons use standard htmx POST with `hx-indicator` for loading state (lines 141-158 of `job_detail.html`). Someone decides to convert these to SSE for real-time progress. The conversion requires changing BOTH the backend (return `EventSourceResponse` instead of `HTMLResponse`) and the frontend (change from `hx-post` with `hx-target` to `hx-ext="sse"` with `sse-connect` and `sse-swap`). But the SSE extension requires a GET endpoint for the connection, not POST. The button click needs to trigger a POST that starts the operation AND returns HTML that establishes the SSE connection -- a two-step flow.

The existing apply engine already solved this pattern (lines 478-527 of `webapp/app.py`): the POST endpoint starts the background task and returns HTML containing the SSE connection markup. But this pattern is easy to get wrong:

- The POST returns HTML with `sse-connect="/jobs/{key}/ai-score/stream"` -- but the key must be URL-encoded
- The SSE GET endpoint must find the queue that was created by the POST handler
- If the user clicks the button twice, two POST requests create two queues, and the SSE endpoint connects to the wrong one
- htmx's SSE extension reconnects automatically on failure -- if the scoring finishes and the endpoint returns 404 (session cleaned up), htmx keeps trying to reconnect with exponential backoff

**Why it happens:** SSE is inherently a long-lived GET connection, but triggering an operation is inherently POST. The mismatch requires the two-step pattern (POST to start, GET to stream). htmx handles this with the `sse-connect` attribute in returned HTML, but the coordination between POST handler and GET handler is manual and error-prone.

**Consequences:**
- Double-click on "AI Score" button creates duplicate scoring operations, wasting tokens
- SSE reconnection after scoring completes causes 404 errors in browser console
- URL encoding issues in `sse-connect` path cause connection failures for job keys with special characters
- The `hx-indicator` spinner doesn't show during the SSE connection phase (it only works with standard htmx requests, not SSE)

**Prevention:**
1. Follow the exact same pattern as the existing apply engine (lines 478-527 of `webapp/app.py`). It is battle-tested.

2. Disable the button after first click to prevent double-submission:
   ```html
   <button hx-post="/jobs/{{ key }}/ai-score"
           hx-target="#ai-score-result"
           hx-swap="innerHTML"
           hx-disabled-elt="this">
       AI Score
   </button>
   ```

3. Use `sse-close="done"` on the SSE container to prevent reconnection after completion:
   ```html
   <div hx-ext="sse"
        sse-connect="/jobs/{key}/ai-score/stream"
        sse-swap="progress"
        sse-close="done">
   ```

4. URL-encode the dedup_key in the SSE connection URL just as the apply engine does (line 517):
   ```python
   encoded_key = urllib.parse.quote(dedup_key, safe="")
   ```

5. Show a custom loading indicator in the initial POST response HTML (not via `hx-indicator`) since SSE doesn't trigger htmx indicators.

**Detection (warning signs):**
- Browser console shows repeated 404 errors on `/ai-score/stream` after scoring completes
- Multiple concurrent Claude CLI processes for the same job
- Loading spinner never appears or never disappears
- SSE connection fails with special characters in company names (e.g., `AT&T::senior engineer`)

**Phase:** UI/endpoint design phase. Establish the pattern before implementing individual SSE features.

**Confidence:** HIGH -- verified by reading the existing apply engine implementation and the htmx SSE extension documentation.

**Sources:**
- [htmx SSE extension](https://htmx.org/extensions/sse/)
- [htmx sseClose event behavior](https://github.com/bigskysoftware/htmx/issues/2393)

---

### Pitfall 7: AI Score and Rule-Based Score Conflict in UI and Sorting

**What goes wrong:** The existing `jobs` table has a `score INTEGER` column (1-5) populated by the rule-based `JobScorer`. The new AI scoring produces a different score (potentially different scale, different criteria). If both scores are stored and the dashboard sorts by "score," which score is used? If the AI score overwrites the rule-based score, the user loses the deterministic, explainable scoring. If they're stored separately (`score` and `ai_score`), every query that currently references `score` (including FTS ranking, Kanban ordering, CSV export, analytics) must be updated to handle both.

The existing scorer returns `ScoreBreakdown` with `total`, `title_points`, `tech_points`, `remote_points`, `salary_points`. The AI score would have a completely different breakdown (semantic relevance, skill match quality, culture fit, etc.). Displaying both side-by-side is useful, but the UI currently shows a single score badge in the dashboard table, kanban cards, and job detail page.

**Why it happens:** The original system was designed around a single scoring dimension. Adding a second scoring dimension is a cross-cutting concern that touches the database schema, query layer, API responses, and every template that displays a score.

**Consequences:**
- Sorting jobs by "score" becomes ambiguous
- Analytics dashboards show combined statistics that mix rule-based and AI scores
- Users don't know which score to trust for making decisions
- Filters like "show me score 4+ jobs" apply to only one score type

**Prevention:**
1. Store AI score in a SEPARATE column (`ai_score INTEGER`) and never overwrite the rule-based `score`:
   ```sql
   ALTER TABLE jobs ADD COLUMN ai_score INTEGER;
   ALTER TABLE jobs ADD COLUMN ai_score_explanation TEXT;
   ALTER TABLE jobs ADD COLUMN ai_scored_at TEXT;
   ```

2. Add a `composite_score` or `effective_score` computed property that combines both scores. Use this for sorting:
   ```python
   # In the query layer
   effective_score = "COALESCE(ai_score, score, 0)"
   ```

3. In the UI, display both scores clearly labeled:
   ```html
   <span class="score-rule" title="Rule-based score">{{ job.score }}</span>
   {% if job.ai_score %}
   <span class="score-ai" title="AI score">{{ job.ai_score }}</span>
   {% endif %}
   ```

4. Keep the rule-based scorer as the primary score for ALL existing features. AI scoring is additive -- it provides a second opinion, not a replacement.

5. Add a sort option "AI Score" alongside the existing "Score" sort. Don't change the default.

6. Add `ai_score` to the `allowed_sorts` set in `get_jobs()` (line 442 of `webapp/app.py`).

**Detection (warning signs):**
- User confusion about which score number means what
- Kanban cards showing one score but sorted by another
- CSV export missing AI scores
- Analytics page showing inflated "average score" because it mixes both scoring systems

**Phase:** Schema design phase. The column naming and relationship between scores must be decided before any implementation.

**Confidence:** HIGH -- verified by tracing all score references in the codebase: `scorer.py`, `webapp/db.py` (queries), `webapp/app.py` (sorting, filtering), `job_detail.html`, `kanban_card.html`, `dashboard.html`, `analytics.html`.

---

### Pitfall 8: Test Mock Strategy Must Change From SDK Patching to CLI Patching

**What goes wrong:** The existing test infrastructure has a carefully designed mock strategy:
- `tests/conftest.py` has an autouse `_block_anthropic` fixture that patches `Messages.create` and `Messages.parse` (lines 84-105)
- `tests/resume_ai/conftest.py` has a `mock_anthropic` fixture that provides a controllable mock client (lines 8-36)
- Individual tests like `test_tailor.py` use `mock_anthropic.messages.parse.return_value` to control responses

When the implementation switches from `anthropic.Anthropic().messages.parse()` to `subprocess.run(["claude", "-p", ...])`, ALL of these mocks become inert. The autouse `_block_anthropic` fixture still patches the SDK, but the code no longer uses the SDK -- it shells out to the CLI. The mock_anthropic fixture still works but tests that use it aren't testing the real code path. Worse: if someone forgets to mock `subprocess.run`, tests will actually invoke the Claude CLI, which costs money and requires the CLI to be installed.

**Why it happens:** The mock strategy was correctly designed for the SDK-based architecture. Switching to CLI-based architecture requires a corresponding mock strategy migration. If the implementation changes without updating the test mocks, you get false confidence: tests pass but don't test the actual code.

**Consequences:**
- Tests pass but the mocked code path (SDK) is never exercised in production (CLI)
- Tests that forget to mock `subprocess.run` execute real CLI commands (cost, flakiness, CI failure)
- The 428+ existing tests need audit to determine which are affected
- New AI scoring tests are written without guidance on how to mock the CLI wrapper

**Prevention:**
1. Create a new autouse fixture that blocks real CLI invocations, mirroring the existing `_block_anthropic`:
   ```python
   @pytest.fixture(autouse=True)
   def _block_claude_cli(monkeypatch):
       """Prevent accidental real Claude CLI calls during tests."""
       original_run = subprocess.run

       def guarded_run(cmd, *args, **kwargs):
           if isinstance(cmd, (list, tuple)) and len(cmd) > 0 and "claude" in str(cmd[0]):
               raise RuntimeError(
                   "Test attempted real Claude CLI call -- use mock_claude_cli fixture"
               )
           return original_run(cmd, *args, **kwargs)

       monkeypatch.setattr(subprocess, "run", guarded_run)
   ```

2. Create a `mock_claude_cli` fixture that returns controlled responses:
   ```python
   @pytest.fixture
   def mock_claude_cli(monkeypatch):
       responses = {}
       def fake_run(cmd, *args, **kwargs):
           # Return a CompletedProcess with configurable stdout
           return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(responses.get("default", {})))
       monkeypatch.setattr(subprocess, "run", fake_run)
       return responses
   ```

3. Keep the existing `_block_anthropic` fixture active -- the SDK-based resume tailoring may still exist as a fallback or separate code path.

4. If building an `AIProvider` abstraction (see Pitfall 5), mock at THAT level instead of mocking subprocess. This makes tests independent of whether the provider uses SDK or CLI.

5. Audit all test files in `tests/resume_ai/` and `tests/apply_engine/` to identify which tests use the Anthropic mock and need to be updated.

**Detection (warning signs):**
- Tests pass but coverage report shows the CLI wrapper code has 0% coverage
- CI pipeline starts billing Anthropic API credits
- `claude: command not found` errors in CI test output
- New tests copy the old mock pattern and test dead code paths

**Phase:** Test infrastructure update -- should happen IMMEDIATELY after building the CLI wrapper, before implementing any features.

**Confidence:** HIGH -- verified by reading the existing test infrastructure: `tests/conftest.py` (lines 84-105), `tests/resume_ai/conftest.py` (lines 8-36), `tests/resume_ai/test_tailor.py`.

---

### Pitfall 9: AI Scoring Every Job On-Demand Is Too Slow and Too Expensive

**What goes wrong:** A user loads the dashboard and sees 500 jobs. They want AI scores for "the good ones." The naive implementation adds an "AI Score" button to each job card, or a "Score All" bulk action. Each AI scoring call takes 5-15 seconds via the CLI and costs ~$0.01-0.05 per job (depending on description length). Scoring all 500 jobs takes 42-125 minutes and costs $5-25. Even scoring the 50 "score 4+" jobs takes 4-12 minutes.

The existing rule-based scorer processes all jobs in `score_batch()` in milliseconds because it's pure string matching. Users expect similar speed from "AI Score" and are frustrated when the button spins for 10 seconds with no feedback.

**Why it happens:** LLM scoring is fundamentally slower and more expensive than rule-based scoring. The CLI adds per-invocation overhead (process spawn, Node.js startup, API round-trip). There's no caching -- scoring the same job twice costs the same amount.

**Consequences:**
- Users avoid AI scoring because it's too slow
- Bulk scoring operations time out or exhaust the API budget
- If scoring is triggered on page load (e.g., "auto-score unscored jobs"), the dashboard becomes unusable
- No way to prioritize which jobs to score first

**Prevention:**
1. AI scoring must be explicitly triggered per-job, never automatic or bulk. The UI should make the cost visible:
   ```html
   <button>AI Score (~10s, ~$0.02)</button>
   ```

2. Cache AI scores in the database. Once a job is AI-scored, never re-score it unless the user explicitly asks. Add `ai_scored_at` timestamp to skip already-scored jobs.

3. Use SSE streaming to show progress ("Analyzing job description...", "Comparing to profile...", "Generating explanation...") so the user sees activity during the 5-15 second wait.

4. For bulk operations, implement a queue: "Score next 10 unscored jobs" with progress bar. Process one at a time with a cancel button.

5. Consider a "pre-score" that uses the rule-based scorer as a filter: only offer AI scoring for jobs that scored 3+ on the rule-based scorer. This reduces the target set from 500 to ~50.

6. If using SSE for progress, emit intermediate results so the user can see the score as soon as it's computed, even before the full explanation is ready.

**Detection (warning signs):**
- Users click "AI Score" and immediately navigate away (they gave up waiting)
- Anthropic API bills spike unexpectedly
- Dashboard performance degrades when many jobs are AI-scored simultaneously
- The "Score All" button was added but nobody uses it

**Phase:** UX design phase. The interaction pattern (single-job scoring with SSE progress) should be designed before implementation.

**Confidence:** HIGH -- based on known LLM latency characteristics and the existing codebase's scoring patterns in `scorer.py`.

---

### Pitfall 10: htmx SSE Extension Reconnection Creates Duplicate Scoring Requests

**What goes wrong:** The htmx SSE extension has built-in automatic reconnection with exponential backoff. If the SSE connection drops (network blip, server restart, proxy timeout), htmx automatically reconnects to the `sse-connect` URL. If the SSE endpoint is `/jobs/{key}/ai-score/stream` and the scoring already completed (session cleaned up), the reconnection returns a 404 or an empty stream. htmx interprets the failed connection as a transient error and retries with backoff.

Worse: if the scoring backend is stateless about "has this job been scored," the reconnection might trigger a NEW scoring operation -- spending another $0.02 and 10 seconds on a job that was already scored.

The existing apply engine has partial protection against this: `is_already_applied()` checks the database (lines 493-501 of `webapp/app.py`). But if the AI scoring endpoint doesn't have an equivalent check, reconnection creates duplicate work.

**Why it happens:** SSE reconnection is a browser/htmx feature designed for long-lived event streams (stock tickers, chat). It assumes the stream is meant to be persistent. For one-shot operations like "score this job," reconnection is undesirable behavior.

**Consequences:**
- Duplicate AI scoring charges
- Inconsistent state if the second scoring produces a different result than the first
- Browser console filled with reconnection errors
- User sees stale progress messages from a previous scoring attempt

**Prevention:**
1. Always use `sse-close="done"` to close the EventSource when the operation completes. This prevents reconnection for completed operations.

2. Add an idempotency check in the SSE endpoint:
   ```python
   @app.get("/jobs/{key}/ai-score/stream")
   async def ai_score_stream(key: str):
       queue = _sessions.get(key)
       if queue is None:
           # No active session -- scoring already completed or never started
           return HTMLResponse("<p>Scoring complete or not started.</p>", status_code=404)
   ```

3. In the POST endpoint that triggers scoring, check if the job already has an AI score:
   ```python
   job = db.get_job(dedup_key)
   if job.get("ai_score") is not None:
       return HTMLResponse("Already scored: " + str(job["ai_score"]))
   ```

4. Add `hx-on:htmx:sseError` handler to the SSE container that stops reconnection attempts:
   ```html
   <div hx-ext="sse"
        sse-connect="..."
        sse-close="done"
        hx-on:htmx:sseError="this.removeAttribute('sse-connect')">
   ```

**Detection (warning signs):**
- Anthropic API logs show duplicate requests for the same job within seconds
- Browser DevTools shows repeated SSE connection attempts to the same URL
- `ai_scored_at` timestamps show multiple entries for the same job
- Server logs show "no active session" 404s after successful scoring

**Phase:** SSE endpoint implementation phase. Idempotency must be built in from the start.

**Confidence:** HIGH -- verified against htmx SSE extension reconnection behavior documented at [htmx.org/extensions/sse](https://htmx.org/extensions/sse/).

---

## Minor Pitfalls

Mistakes that cause annoyance, confusion, or minor issues.

---

### Pitfall 11: Claude CLI Not Installed or Not in PATH in CI

**What goes wrong:** The CI environment (GitHub Actions, etc.) doesn't have the Claude CLI installed. Tests that mock `subprocess.run` pass, but integration tests or the actual deployment fail with `FileNotFoundError: [Errno 2] No such file or directory: 'claude'`.

**Prevention:**
1. Add a startup check in the CLI wrapper:
   ```python
   import shutil
   if shutil.which("claude") is None:
       raise RuntimeError("Claude CLI not found in PATH. Install with: npm install -g @anthropic-ai/claude-code")
   ```
2. Make the CLI path configurable via settings:
   ```yaml
   ai:
     cli_path: "claude"  # or "/usr/local/bin/claude"
   ```
3. In CI, skip AI scoring tests if the CLI is not installed, using a pytest marker.

**Phase:** CLI wrapper implementation.

**Confidence:** HIGH -- standard subprocess PATH resolution behavior.

---

### Pitfall 12: JSON Schema Passed Via Command Line Exceeds Shell Argument Limits

**What goes wrong:** Pydantic v2's `model_json_schema()` for a model with nested types (`TailoredResume` with `SkillSection`, `WorkExperience`, etc.) produces a schema that is 2-5KB of JSON. Passing this as a command-line argument to `--json-schema '{...}'` approaches the shell argument length limit (typically 128KB-2MB on modern systems, but some shells/platforms have lower limits). More practically, the schema contains characters that need shell escaping (quotes, braces, backslashes), making the command fragile.

**Prevention:**
1. Write the JSON schema to a temporary file and pass the file path:
   ```python
   import tempfile
   with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
       json.dump(schema, f)
       schema_path = f.name
   cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", schema_path]
   ```
   NOTE: Check if `--json-schema` accepts a file path or only inline JSON. If only inline, use `subprocess.run` with the JSON as a string argument (not shell-interpreted).

2. Use `subprocess.run` with a LIST argument (never `shell=True`) to avoid shell escaping issues:
   ```python
   subprocess.run(["claude", "-p", prompt, "--json-schema", json.dumps(schema)], ...)
   ```

3. Keep AI scoring output models flat (no nested Pydantic models) to minimize schema size.

**Phase:** CLI wrapper implementation.

**Confidence:** MEDIUM -- shell argument limits are rarely hit in practice but JSON escaping issues are common.

---

### Pitfall 13: `asyncio.to_thread` and `asyncio.create_subprocess_exec` Have Different Cancellation Semantics

**What goes wrong:** Code that uses `await asyncio.to_thread(subprocess.run, cmd, ...)` cannot be cancelled from the async side. When `asyncio.to_thread` is cancelled, the background thread continues running `subprocess.run` to completion. The subprocess is NOT killed. In contrast, `asyncio.create_subprocess_exec` supports proper cancellation: when the coroutine is cancelled, you can handle `CancelledError` and kill the process.

**Prevention:**
1. If cancellation is important (user clicks "Cancel" on AI scoring), use `asyncio.create_subprocess_exec`:
   ```python
   proc = await asyncio.create_subprocess_exec("claude", "-p", prompt, ...)
   try:
       stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
   except (asyncio.CancelledError, asyncio.TimeoutError):
       proc.kill()
       await proc.wait()
       raise
   ```

2. If using `asyncio.to_thread`, the subprocess handle must be accessible so external code can kill it:
   ```python
   _active_processes = {}

   def _run_cli_sync(dedup_key, cmd):
       proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
       _active_processes[dedup_key] = proc
       try:
           stdout, stderr = proc.communicate(timeout=120)
       finally:
           _active_processes.pop(dedup_key, None)
       return stdout, stderr

   def cancel_scoring(dedup_key):
       proc = _active_processes.get(dedup_key)
       if proc:
           proc.terminate()
   ```

**Phase:** Applies when implementing the cancel functionality for AI scoring.

**Confidence:** HIGH -- verified against Python asyncio documentation for `to_thread` and `create_subprocess_exec`.

---

### Pitfall 14: Existing `score_breakdown` Column Is JSON Text, Not a Foreign Key

**What goes wrong:** The existing `score_breakdown TEXT` column (migration version 2) stores a JSON-serialized `ScoreBreakdown.to_dict()`. Someone adds `ai_score_explanation TEXT` for the AI scoring explanation. Now there are two unstructured JSON text columns. Querying "show me all jobs where the AI explanation mentions Kubernetes" requires `LIKE '%Kubernetes%'` on the text column -- no FTS, no indexing.

**Prevention:**
1. Store AI score explanations as structured JSON with a consistent schema:
   ```python
   ai_explanation = json.dumps({
       "overall": "Strong match for the role based on...",
       "strengths": ["10 years Kubernetes experience", "Platform engineering background"],
       "concerns": ["No mention of Java which is listed as required"],
       "confidence": 0.85,
   })
   ```

2. If full-text search on AI explanations is needed, add the column to the FTS5 virtual table (see Pitfall 4).

3. Consider storing the AI explanation as plain text (not JSON) if the primary use case is human reading, not programmatic querying.

**Phase:** Schema design phase.

**Confidence:** MEDIUM -- depends on actual use case for AI explanations.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| CLI wrapper implementation | subprocess.run hangs indefinitely | Always use `capture_output=True` + `timeout=N`, wrap in `asyncio.to_thread` or use `create_subprocess_exec` |
| CLI wrapper implementation | `--json-schema` regression in CLI v2.1.x | Build resilient parser handling both `structured_output` and markdown-in-`result` formats |
| CLI wrapper implementation | Error semantics lost crossing process boundary | Build typed error classes parsed from stderr content |
| CLI wrapper implementation | Claude CLI not in PATH | Startup check with `shutil.which()`, configurable CLI path |
| Database schema migration | `ALTER TABLE ADD COLUMN` with expression DEFAULT fails | Use `DEFAULT NULL` for timestamps, set in application code |
| Database schema migration | FTS5 triggers not updated for new columns | Separate migration version for FTS changes with full rebuild |
| Database schema migration | Two scoring systems conflict in UI/queries | Separate columns (`score` vs `ai_score`), add `effective_score` |
| SSE streaming endpoints | Connection leak on navigation away | `sse-close="done"`, frequent `is_disconnected()` checks, subprocess cleanup |
| SSE streaming endpoints | htmx reconnection triggers duplicate work | `sse-close="done"`, idempotency check in endpoint, disable button after click |
| SSE streaming endpoints | Converting POST to SSE requires two-step pattern | Follow existing apply engine pattern exactly |
| Test infrastructure update | Existing SDK mocks don't cover CLI code path | Add `_block_claude_cli` autouse fixture, create `mock_claude_cli` fixture |
| Test infrastructure update | 428+ tests need audit for mock updates | Build `AIProvider` protocol, mock at abstraction level |
| AI scoring UX | Per-job scoring is slow and expensive | Cache results, SSE progress feedback, pre-filter with rule-based scorer |

---

## Sources

### Verified (HIGH confidence)
- Direct codebase analysis of `webapp/app.py`, `webapp/db.py`, `scorer.py`, `resume_ai/tailor.py`, `apply_engine/engine.py`, `tests/conftest.py`, `tests/resume_ai/conftest.py`
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) -- pipe deadlock, timeout behavior
- [Python asyncio subprocess documentation](https://docs.python.org/3/library/asyncio-subprocess.html) -- cancellation semantics
- [SQLite ALTER TABLE documentation](https://www.sqlite.org/lang_altertable.html) -- DEFAULT expression limitations
- [SQLite FTS5 Extension documentation](https://sqlite.org/fts5.html) -- content-sync triggers, rebuild command
- [htmx SSE extension documentation](https://htmx.org/extensions/sse/) -- sse-close, reconnection, cleanup
- [Claude Code headless mode documentation](https://code.claude.com/docs/en/headless) -- CLI flags, output formats
- [FastAPI concurrency documentation](https://fastapi.tiangolo.com/async/) -- async/await, blocking calls

### Cross-referenced (MEDIUM confidence)
- [Claude CLI --json-schema bug (GitHub #18536)](https://github.com/anthropics/claude-code/issues/18536) -- structured_output regression in v2.1.x
- [Claude CLI --json-schema feature (GitHub #9058)](https://github.com/anthropics/claude-code/issues/9058) -- original implementation details
- [htmx SSE close connection (#2393)](https://github.com/bigskysoftware/htmx/issues/2393) -- sse-close attribute behavior
- [htmx SSE DOM removal (#2510)](https://github.com/bigskysoftware/htmx/issues/2510) -- cleanup when elements removed
- [sse-starlette disconnect handling](https://github.com/sysid/sse-starlette) -- request.is_disconnected patterns
- [Pydantic v2 JSON Schema documentation](https://docs.pydantic.dev/latest/concepts/json_schema/) -- $ref/$defs behavior
- [Python subprocess deadlock discussion](https://discuss.python.org/t/details-of-process-wait-deadlock/69481) -- pipe buffer deadlock
- [Kill subprocess and children on timeout](https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/) -- process tree termination
