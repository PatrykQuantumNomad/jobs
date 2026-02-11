# Phase 18: Resume Tailoring via CLI + SSE - Research

**Researched:** 2026-02-11
**Domain:** SSE streaming, asyncio subprocess orchestration, htmx real-time UI
**Confidence:** HIGH

## Summary

Phase 18 converts the existing resume tailoring endpoint from a synchronous request-response pattern (POST returns HTML partial after 10-15s) to a streaming SSE pattern that shows real-time progress through four stages: extracting, generating, validating, rendering. The codebase already has a complete working SSE pattern in the apply_engine (Queue + background task + EventSourceResponse) and a complete working CLI integration in resume_ai/tailor.py (claude_cli.run()). This phase combines both patterns.

The core technical challenge is straightforward: the current `tailor_resume_endpoint` in `webapp/app.py` (line 248) does all work inline and returns a single HTML partial. The new version must (1) return an SSE-connect HTML snippet immediately (like the apply trigger endpoint does at line 550), (2) run the multi-stage pipeline in a background asyncio.Task emitting progress events to a Queue, and (3) stream those events via an EventSourceResponse endpoint. Process cleanup on client disconnect is handled by checking `request.is_disconnected()` in the SSE generator -- the same pattern already working in `apply_stream`.

**Primary recommendation:** Follow the apply_engine SSE pattern exactly (Queue + background Task + EventSourceResponse), but run stages as async steps rather than in a thread (since claude_cli.run() is already async). Emit stage-specific events (extracting, generating, validating, rendering, done/error) using a new ResumeEvent model parallel to ApplyEvent.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sse-starlette | 3.2.0 | Server-Sent Events for FastAPI | Already in use for apply_stream endpoint |
| htmx-ext-sse | 2.2.4 | Client-side SSE connection via htmx | Already loaded in base.html (line 9) |
| asyncio (stdlib) | Python 3.14 | Subprocess exec, Queue, Task | Already used by claude_cli.client |
| FastAPI | 0.115.0+ | Web framework, endpoints, templates | Already the app framework |
| WeasyPrint | 68.0+ | PDF rendering | Already used in resume_ai/renderer.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pymupdf4llm | 0.2.9+ | PDF text extraction | Already used in resume_ai/extractor.py |
| pydantic | 2.0+ | Event models, structured output | Already the data layer |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.Queue for event buffering | asyncio.Event per stage | Queue is more flexible (multiple events per stage), matches apply_engine pattern |
| Background asyncio.Task | Background thread (asyncio.to_thread) | Task is simpler since all steps are already async (no sync Playwright here) |

**Installation:** No new dependencies needed. All libraries already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
webapp/app.py              # New SSE endpoint + modified trigger endpoint
resume_ai/tailor.py        # Unchanged (already async via claude_cli.run())
resume_ai/validator.py     # Unchanged (pure sync function)
resume_ai/renderer.py      # Unchanged (sync PDF rendering)
resume_ai/tracker.py       # Unchanged (sync DB operations)
resume_ai/extractor.py     # Unchanged (sync PDF extraction)
resume_ai/models.py        # Unchanged
webapp/templates/partials/  # New SSE status partial for resume progress
webapp/templates/job_detail.html  # Modified "Tailor Resume" button
```

### Pattern 1: SSE-Backed Background Pipeline (from apply_engine)
**What:** POST endpoint creates a Queue, starts a background Task, returns HTML that connects to an SSE endpoint. The SSE endpoint reads from the Queue and yields events until "done".
**When to use:** Any operation that takes >3s and has identifiable stages the user should see.
**Existing implementation in codebase:**

```python
# webapp/app.py line 550-599 (trigger_apply)
@app.post("/jobs/{dedup_key:path}/apply")
async def trigger_apply(request: Request, dedup_key: str, mode: str = Form("")):
    queue = asyncio.Queue()
    engine._sessions[dedup_key] = queue
    asyncio.create_task(_run_apply(job, mode, queue))
    # Return HTML with sse-connect pointing to stream endpoint
    return HTMLResponse(
        f'<div hx-ext="sse" sse-connect="/jobs/{encoded_key}/apply/stream" ...>'
    )

# webapp/app.py line 602-633 (apply_stream)
@app.get("/jobs/{dedup_key:path}/apply/stream")
async def apply_stream(request: Request, dedup_key: str):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            event = await asyncio.wait_for(queue.get(), timeout=15)
            html = templates.get_template("partials/apply_status.html").render(...)
            yield {"event": event_type, "data": html}
            if event_type == "done":
                break
    return EventSourceResponse(event_generator())
```

### Pattern 2: Stage-Based Progress Emission
**What:** Define discrete stages (extracting, generating, validating, rendering) and emit a progress event at each stage boundary. The final event is either "done" (with result HTML) or "error".
**When to use:** Multi-step pipelines where each step is meaningful to the user.
**Example for resume tailoring:**

```python
# Stages for resume tailoring SSE events
STAGES = ["extracting", "generating", "validating", "rendering"]

async def _run_resume_tailor(dedup_key: str, job: dict, queue: asyncio.Queue):
    try:
        # Stage 1: Extract
        _emit(queue, "progress", "Extracting resume text...")
        resume_text = extract_resume_text(resume_path)

        # Stage 2: Generate (this is the slow CLI call)
        _emit(queue, "progress", "Generating tailored resume via AI...")
        tailored = await tailor_resume(resume_text=..., ...)

        # Stage 3: Validate
        _emit(queue, "progress", "Running anti-fabrication validation...")
        validation = validate_no_fabrication(resume_text, tailored_text)

        # Stage 4: Render
        _emit(queue, "progress", "Rendering PDF...")
        render_resume_pdf(tailored, ...)
        save_resume_version(...)

        # Done: emit final result with download link
        _emit(queue, "done", result_html)
    except Exception as exc:
        _emit(queue, "error", str(exc))
    finally:
        _emit(queue, "done", "")  # Ensure SSE closes
```

### Pattern 3: Process Cleanup on Disconnect
**What:** When the user navigates away, the SSE connection closes. The event generator detects `request.is_disconnected()` and breaks. For the CLI subprocess, since `claude_cli.run()` uses `asyncio.create_subprocess_exec`, cancelling the Task (which happens when the generator stops) will propagate cancellation to the `await proc.communicate()` call, which will leave the subprocess orphaned unless explicitly killed.
**When to use:** Always for long-running SSE pipelines.
**Implementation approach:**

```python
async def _run_resume_tailor(dedup_key: str, job: dict, queue: asyncio.Queue):
    try:
        # ... pipeline stages ...
    except asyncio.CancelledError:
        # Task was cancelled (SSE disconnect) -- cleanup
        _emit(queue, "done", "Generation cancelled")
        raise  # Re-raise to fully cancel
    except Exception as exc:
        _emit(queue, "error", str(exc))
```

The key insight: `asyncio.create_task()` returns a Task. When the SSE generator exits (client disconnects), the Queue stops being consumed, but the background Task continues. We need a mechanism to cancel the Task. The apply_engine handles this via explicit session tracking (`_sessions` dict). The same pattern works here: store the Task in a dict, cancel it when SSE disconnects.

### Anti-Patterns to Avoid
- **Blocking the event loop during PDF rendering:** `render_resume_pdf()` uses WeasyPrint which is CPU-bound and blocking. Wrap in `asyncio.to_thread()` to avoid blocking SSE ping events.
- **Forgetting the final "done" event:** If the background task crashes without emitting "done", the SSE connection hangs forever. Always use try/finally to emit "done".
- **Using subprocess.run instead of asyncio.create_subprocess_exec:** Already addressed -- claude_cli.run() is async. But `extract_resume_text()` (pymupdf4llm) and `render_resume_pdf()` (WeasyPrint) are sync and should be wrapped in `asyncio.to_thread()` if they take significant time.
- **Emitting queue events after the queue is no longer consumed:** Use `queue.put_nowait()` wrapped in a try/except to silently discard events if the queue is full or closed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE transport | Custom chunked HTTP responses | sse-starlette EventSourceResponse | Handles keep-alive, reconnection, content-type headers |
| Client SSE handling | Custom JavaScript EventSource | htmx-ext-sse (already loaded) | Declarative sse-connect/sse-swap attributes, auto-reconnect |
| Event queue | Custom threading.Queue bridge | asyncio.Queue | Background task and SSE generator are both async -- no thread bridge needed |
| Subprocess management | Raw subprocess.Popen | claude_cli.run() via asyncio.create_subprocess_exec | Timeout, error typing, JSON parsing already handled |
| PDF rendering | HTML-to-PDF with raw wkhtmltopdf | WeasyPrint via resume_ai/renderer.py | Already built, ATS-friendly templates, Calibri/Carlito fonts |

**Key insight:** Every component needed for this phase already exists in the codebase. The phase is about wiring them together with SSE streaming, not building new capabilities.

## Common Pitfalls

### Pitfall 1: WeasyPrint Blocking the Event Loop
**What goes wrong:** WeasyPrint PDF rendering is CPU-intensive and synchronous. If called directly in the async background task, it blocks the event loop, causing SSE ping events to be delayed and the client to think the connection dropped.
**Why it happens:** WeasyPrint does font loading, CSS computation, and PDF generation synchronously.
**How to avoid:** Wrap `render_resume_pdf()` in `asyncio.to_thread()`:
```python
await asyncio.to_thread(render_resume_pdf, tailored, name, contact, output_path)
```
**Warning signs:** SSE connection drops during "Rendering PDF..." stage; client shows "reconnecting".

### Pitfall 2: Zombie Background Tasks on Navigation
**What goes wrong:** User clicks "Tailor Resume", sees SSE progress, then navigates away. The background asyncio.Task keeps running, the CLI subprocess keeps running, but nobody is consuming the Queue.
**Why it happens:** `asyncio.create_task()` fires-and-forget -- the task continues even if the SSE generator exits.
**How to avoid:** Track active tasks in a module-level dict. When SSE generator exits (disconnect detected), cancel the task. Also set a reasonable timeout on the CLI call (already 120s default in claude_cli.run()).
```python
_resume_tasks: dict[str, asyncio.Task] = {}

# In trigger endpoint:
task = asyncio.create_task(_run_resume_tailor(...))
_resume_tasks[dedup_key] = task

# In SSE generator cleanup:
task = _resume_tasks.pop(dedup_key, None)
if task and not task.done():
    task.cancel()
```
**Warning signs:** Growing memory usage, multiple CLI processes running for same job.

### Pitfall 3: Race Condition Between POST and SSE Connect
**What goes wrong:** The POST trigger endpoint creates the Queue and starts the background task. It returns HTML with `sse-connect` pointing to the stream endpoint. But if the background task emits events before the SSE connection is established, those events are lost (nobody consuming the Queue yet).
**Why it happens:** There is a time gap between POST response and the browser establishing the SSE connection.
**How to avoid:** This is the same race condition the apply_engine already has. The solution is to not emit the first event immediately -- start the task but have it emit after a brief `await asyncio.sleep(0)` or use a sentinel event. In practice, the extraction step takes >100ms, so the SSE connection is established before the first event. The apply_engine works fine without special handling.
**Warning signs:** First "Extracting..." event sometimes missing.

### Pitfall 4: Double "done" Events
**What goes wrong:** The background task emits "done" on success AND the finally block also emits "done" for safety. This causes the SSE generator to yield two "done" events.
**Why it happens:** Defensive programming (always emit done) conflicts with normal flow.
**How to avoid:** Use a flag variable or only emit "done" in the finally block:
```python
async def _run_resume_tailor(...):
    result_html = ""
    try:
        # ... stages ...
        result_html = render_success_partial(...)
    except Exception as exc:
        result_html = render_error_html(str(exc))
    finally:
        _emit(queue, "done", result_html)
```
**Warning signs:** SSE client receives two "done" events, second one may cause UI glitch.

### Pitfall 5: Stale Session State
**What goes wrong:** User clicks "Tailor Resume" twice quickly. Two background tasks run for the same dedup_key, both writing to different queues. The SSE endpoint connects to whichever queue was stored last.
**Why it happens:** No semaphore or session dedup check.
**How to avoid:** Check for existing session before starting. If a session exists, return an error or cancel the old one:
```python
if dedup_key in _resume_sessions:
    return HTMLResponse("Resume generation already in progress...")
```
**Warning signs:** Duplicate PDF files, confused SSE events.

## Code Examples

### Example 1: Resume Tailoring Background Task

```python
# Source: Derived from existing apply_engine pattern + resume_ai/tailor.py
async def _run_resume_tailor(
    dedup_key: str,
    job: dict,
    resume_path: str,
    queue: asyncio.Queue,
) -> None:
    """Background task: run resume tailoring pipeline with SSE progress events."""
    from resume_ai.diff import generate_resume_diff_html, wrap_diff_html
    from resume_ai.extractor import extract_resume_text
    from resume_ai.renderer import render_resume_pdf
    from resume_ai.tailor import format_resume_as_text, tailor_resume
    from resume_ai.tracker import save_resume_version
    from resume_ai.validator import validate_no_fabrication

    def _emit(event_type: str, message: str, html: str = ""):
        queue.put_nowait({"type": event_type, "message": message, "html": html})

    try:
        # Stage 1: Extract
        _emit("progress", "Extracting resume text from PDF...")
        resume_text = await asyncio.to_thread(extract_resume_text, resume_path)

        # Stage 2: Generate (slow -- CLI subprocess, 10-60s)
        _emit("progress", "Generating tailored resume via AI... this may take a minute")
        tailored = await tailor_resume(
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Stage 3: Validate
        _emit("progress", "Running anti-fabrication validation...")
        tailored_text = format_resume_as_text(tailored)
        validation = validate_no_fabrication(resume_text, tailored_text)

        # Stage 4: Render PDF
        _emit("progress", "Rendering PDF...")
        # ... (build output_path, render, save version, log activity)
        await asyncio.to_thread(render_resume_pdf, tailored, name, contact, output_path)
        save_resume_version(...)

        # Build result HTML (the same resume_diff partial)
        diff_html = generate_resume_diff_html(resume_text, tailored_text)
        result_html = templates.get_template("partials/resume_diff.html").render(...)
        _emit("done", "Resume tailored successfully", html=result_html)

    except asyncio.CancelledError:
        _emit("done", "Generation cancelled")
        raise
    except Exception as exc:
        _emit("error", f"Resume tailoring failed: {exc}")
        _emit("done", "")
```

### Example 2: SSE Trigger Endpoint (POST)

```python
# Source: Parallel to existing trigger_apply pattern (webapp/app.py line 550)
_resume_sessions: dict[str, asyncio.Queue] = {}
_resume_tasks: dict[str, asyncio.Task] = {}

@app.post("/jobs/{dedup_key:path}/tailor-resume", response_class=HTMLResponse)
async def tailor_resume_endpoint(request: Request, dedup_key: str):
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    if dedup_key in _resume_sessions:
        return HTMLResponse("Resume generation already in progress...")

    queue = asyncio.Queue()
    _resume_sessions[dedup_key] = queue
    task = asyncio.create_task(_run_resume_tailor(dedup_key, job, resume_path, queue))
    _resume_tasks[dedup_key] = task

    encoded_key = urllib.parse.quote(dedup_key, safe="")
    return HTMLResponse(
        f'<div hx-ext="sse"'
        f' sse-connect="/jobs/{encoded_key}/tailor-resume/stream"'
        f' sse-swap="progress"'
        f' sse-close="done">'
        f'  <div class="flex items-center gap-2 py-2">'
        f'    <div class="animate-spin h-4 w-4 border-2 border-indigo-500 ...'
        f'    </div>'
        f'    <span class="text-sm text-gray-500">Starting resume tailoring...</span>'
        f'  </div>'
        f'</div>'
    )
```

### Example 3: SSE Stream Endpoint (GET)

```python
# Source: Parallel to existing apply_stream pattern (webapp/app.py line 602)
@app.get("/jobs/{dedup_key:path}/tailor-resume/stream")
async def resume_tailor_stream(request: Request, dedup_key: str):
    from sse_starlette import EventSourceResponse

    queue = _resume_sessions.get(dedup_key)
    if queue is None:
        return HTMLResponse("No active session", status_code=404)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    event_type = event.get("type", "progress")
                    html = templates.get_template(
                        "partials/resume_tailor_status.html"
                    ).render(event=event, dedup_key=dedup_key)
                    yield {"event": event_type, "data": html}
                    if event_type == "done":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            # Cleanup session
            _resume_sessions.pop(dedup_key, None)
            task = _resume_tasks.pop(dedup_key, None)
            if task and not task.done():
                task.cancel()

    return EventSourceResponse(event_generator())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| POST waits 10-15s, returns full HTML | POST returns SSE connector, events stream in real-time | This phase | User sees progress instead of frozen spinner |
| Anthropic SDK (sync, wrapped in to_thread) | claude_cli.run() (native async subprocess) | Phase 16 (completed) | No thread bridge needed for CLI call |
| No process cleanup on disconnect | Task cancellation + session cleanup | This phase | No zombie CLI processes |

**Current state of resume tailoring (what exists):**
- `resume_ai/tailor.py`: `tailor_resume()` is already async, calls `claude_cli.run()`, returns `TailoredResume`
- `resume_ai/validator.py`: `validate_no_fabrication()` is sync, pure Python, fast
- `resume_ai/renderer.py`: `render_resume_pdf()` is sync, WeasyPrint, CPU-bound
- `resume_ai/tracker.py`: `save_resume_version()` is sync, SQLite insert
- `resume_ai/extractor.py`: `extract_resume_text()` is sync, pymupdf4llm
- `webapp/app.py`: `tailor_resume_endpoint()` at line 248 does everything inline

## Open Questions

1. **htmx sse-swap with multiple event types**
   - What we know: The apply_engine uses `sse-swap="progress"` and `sse-close="done"`. The "done" event carries the final HTML. For resume tailoring, the "done" event should carry the full resume_diff partial (download link, validation status, diff view).
   - What's unclear: Whether `sse-swap="progress"` with `sse-close="done"` correctly handles the case where the "done" event's HTML should replace the entire SSE container (not just append). The apply_engine emits a "done" event that shows a completion message, but the SSE div then closes (removed from DOM?).
   - Recommendation: Test with the existing apply pattern. The "done" event yields data via `sse-swap`, then `sse-close="done"` tells htmx to close the connection. The last swapped HTML stays in the DOM. This should work for showing the resume_diff partial as the final result. If not, use a separate `hx-swap-oob` target.

2. **Cancellation propagation to CLI subprocess**
   - What we know: `asyncio.Task.cancel()` raises `CancelledError` in the task. If the task is awaiting `claude_cli.run()` which awaits `proc.communicate()`, the `CancelledError` will interrupt the await. But `proc.communicate()` might not kill the subprocess.
   - What's unclear: Whether cancelling the asyncio Task also terminates the child process, or if the child process becomes orphaned.
   - Recommendation: In the `_run_resume_tailor` task, catch `CancelledError`, and in the handler, attempt to kill any running subprocess. Since `claude_cli.run()` manages the subprocess internally, we may need to add a cancellation mechanism to `claude_cli.client` or accept that the subprocess self-terminates after its own timeout (120s default). For v1, accept that the subprocess runs to completion on its own timeout -- it's a single user tool and the 120s timeout is adequate protection.

3. **Resume generation already in progress**
   - What we know: Need to prevent double-submission. The apply_engine checks for existing sessions.
   - What's unclear: Best UX -- should the button be disabled while generation is in progress? Should we show the existing stream?
   - Recommendation: Disable the button via htmx attributes (`hx-disabled-elt`) during the SSE connection. If a session already exists, return an informational message instead of starting a new one.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis:** `webapp/app.py` -- existing apply_stream SSE pattern (lines 550-633)
- **Codebase analysis:** `apply_engine/engine.py` -- Queue + background task pattern
- **Codebase analysis:** `apply_engine/events.py` -- ApplyEvent model for SSE events
- **Codebase analysis:** `resume_ai/tailor.py` -- current async tailor_resume() implementation
- **Codebase analysis:** `resume_ai/validator.py` -- anti-fabrication validation
- **Codebase analysis:** `resume_ai/renderer.py` -- WeasyPrint PDF rendering
- **Codebase analysis:** `resume_ai/tracker.py` -- resume version tracking
- **Codebase analysis:** `claude_cli/client.py` -- async subprocess wrapper
- **Codebase analysis:** `webapp/templates/job_detail.html` -- current "Tailor Resume" button
- **Codebase analysis:** `webapp/templates/base.html` -- htmx-ext-sse 2.2.4 loaded
- **Codebase analysis:** `pyproject.toml` -- sse-starlette>=2.0.0 (installed 3.2.0)

### Secondary (MEDIUM confidence)
- **sse-starlette 3.2.0** -- EventSourceResponse async generator pattern verified via working code in apply_stream
- **htmx-ext-sse 2.2.4** -- sse-connect/sse-swap/sse-close attributes verified via working code in trigger_apply

### Tertiary (LOW confidence)
- **asyncio.Task cancellation propagation to subprocess** -- Needs validation on whether cancelling a Task that awaits `proc.communicate()` actually kills the child process. Current assumption: it does not, and this is acceptable for v1 given the 120s CLI timeout.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already in use in the codebase, no new dependencies
- Architecture: HIGH -- Direct replication of the apply_engine SSE pattern, which is proven to work
- Pitfalls: HIGH -- WeasyPrint blocking and zombie processes are well-understood; apply_engine already solves most of these
- Process cleanup: MEDIUM -- asyncio.Task cancellation to subprocess propagation needs validation

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable patterns, no library changes expected)
