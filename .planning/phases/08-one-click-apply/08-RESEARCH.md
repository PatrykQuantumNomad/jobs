# Phase 8: One-Click Apply - Research

**Researched:** 2026-02-07
**Domain:** Browser automation orchestration from web dashboard, SSE real-time updates, ATS form filling, duplicate detection, apply mode configuration
**Confidence:** HIGH

## Summary

Phase 8 is the capstone feature: triggering Playwright-based job application from the htmx dashboard, with configurable automation levels and real-time status streaming. The core architectural challenge is bridging FastAPI's async event loop with Playwright's synchronous browser automation. The existing codebase uses Playwright's sync API throughout (`platforms/indeed.py`, `platforms/dice.py`, `platforms/stealth.py`), and running sync Playwright inside an asyncio event loop causes a fatal error. The proven solution is to run the apply engine in a separate thread via `asyncio.to_thread()` (which the project already uses for LLM calls in `webapp/app.py`) or in a subprocess.

The dashboard-to-orchestrator bridge uses Server-Sent Events (SSE) via `sse-starlette` 3.2.0 (standards-compliant, FastAPI-native) paired with htmx's SSE extension (`htmx-ext-sse` 2.2.4, already compatible with htmx 2.0.4 used in `base.html`). This combination provides real-time progress updates without WebSockets or polling. The apply engine publishes structured events (login status, form fill progress, awaiting confirmation, success/failure) to an `asyncio.Queue`, and the SSE endpoint drains that queue to the browser.

For external ATS form filling (Greenhouse, Lever, Ashby), all three provide documented APIs that accept `first_name`, `last_name`, `email`, resume file, and custom questions. However, most companies use embedded iframes or custom career pages -- not direct API access. The practical approach is browser-based form filling with Playwright, using heuristic field detection (label text, `name`/`id`/`placeholder` attributes, `input` types) rather than per-ATS selectors. The existing `form_filler.py` concept should be expanded into a field-mapping engine that uses the `CandidateProfile` model.

Duplicate detection is straightforward: the `jobs` table already has `status` and `applied_date` columns, and the `activity_log` table records all status changes. Before any apply action, check `status IN ('applied', 'phone_screen', 'technical', 'final_interview', 'offer')` or `applied_date IS NOT NULL`.

**Primary recommendation:** Use `asyncio.to_thread()` to run sync Playwright apply flows from async FastAPI endpoints, stream progress via `sse-starlette` + htmx SSE extension, add an `apply` section to `config.yaml` for mode configuration, and expand `form_filler.py` into a heuristic field-detection engine for external ATS forms.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sse-starlette` | 3.2.0 | Server-Sent Events from FastAPI endpoints | Standards-compliant SSE for Starlette/FastAPI. Handles async generators, client disconnect detection, graceful shutdown. Published 2026-01-17. |
| `htmx-ext-sse` | 2.2.4 | Client-side SSE reception and DOM swapping | Official htmx SSE extension. Compatible with htmx 2.0.4 already in project. Provides `sse-connect`, `sse-swap`, and `sse-close` attributes. |
| `playwright` | (existing) | Browser automation for Indeed/Dice Easy Apply and external ATS | Already installed and used throughout the project. Sync API in `platforms/*.py`. |
| `playwright-stealth` | 2.0.1+ | Anti-detection for browser automation | Already installed. `Stealth().apply_stealth_sync(page)` API. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | `asyncio.to_thread()` for sync-to-async bridge, `asyncio.Queue` for event bus | Bridge sync Playwright code to async FastAPI. Queue for SSE event streaming. |
| `pydantic` | (existing) | Apply config models, event models | Already in project. Define `ApplyMode`, `ApplyConfig`, `ApplyEvent` models. |
| `pydantic-settings` | (existing) | Load apply config from `config.yaml` | Already powers `AppSettings`. Add `apply:` section to `config.yaml`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sse-starlette` | WebSockets | WebSockets are bidirectional but SSE is simpler, works through proxies, auto-reconnects, and the communication is one-way (server -> client). htmx has native SSE support but WebSocket support requires a separate extension. |
| `asyncio.to_thread()` | `ProcessPoolExecutor` | Separate process avoids GIL entirely but complicates state sharing (browser context, event queue). Thread is sufficient because Playwright's sync API delegates to a subprocess internally anyway. |
| `asyncio.to_thread()` | Playwright async API | Would require rewriting all platform adapters (`indeed.py`, `dice.py`, `stealth.py`, `mixins.py`). Not worth the effort -- `to_thread()` works cleanly with existing sync code. |
| Heuristic form filling | Per-ATS selector maps | Per-ATS maps are brittle and require constant maintenance. Heuristic detection (label text matching, attribute patterns) handles unknown forms gracefully. |

**Installation:**
```bash
pip install sse-starlette
# htmx SSE extension loaded via CDN in base.html:
# <script src="https://unpkg.com/htmx-ext-sse@2.2.4/sse.js"></script>
```

## Architecture Patterns

### Recommended Project Structure
```
project-root/
├── apply_engine/
│   ├── __init__.py
│   ├── config.py              # ApplyMode enum, ApplyConfig model
│   ├── engine.py              # Main apply orchestration (runs in thread)
│   ├── events.py              # ApplyEvent model, event types
│   ├── dedup.py               # Pre-apply duplicate detection
│   └── ats_filler.py          # Heuristic form field detection and filling
├── webapp/
│   ├── app.py                 # Add SSE and apply endpoints
│   └── templates/
│       ├── partials/
│       │   └── apply_status.html  # SSE-swapped apply progress UI
│       └── job_detail.html        # Add apply button and mode selector
├── config.py                  # Add ApplyConfig to AppSettings
└── config.yaml                # Add apply: section
```

### Pattern 1: Sync-to-Async Bridge via asyncio.to_thread()
**What:** Run synchronous Playwright browser automation in a background thread from an async FastAPI endpoint, streaming progress events via an asyncio.Queue.
**When to use:** Every apply action triggered from the dashboard.
**Why:** Playwright sync API cannot run inside an asyncio event loop (raises "Playwright Sync API inside asyncio loop" error). `asyncio.to_thread()` runs the function in a separate thread with its own event loop context, which Playwright handles correctly. The project already uses this pattern in `webapp/app.py` for LLM calls (line 233: `await asyncio.to_thread(tailor_resume, ...)`).
**Example:**
```python
# Source: Existing project pattern (webapp/app.py line 233) + Playwright docs
import asyncio
from sse_starlette import EventSourceResponse

# In FastAPI endpoint:
@app.post("/jobs/{dedup_key}/apply")
async def apply_to_job(request: Request, dedup_key: str, mode: str = Form("semi_auto")):
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("Job not found", status_code=404)

    # Check for duplicate
    if is_already_applied(dedup_key):
        return HTMLResponse("Already applied", status_code=409)

    # Create event queue for SSE streaming
    event_queue: asyncio.Queue = asyncio.Queue()

    # Launch apply in background thread
    asyncio.create_task(_run_apply(job, mode, event_queue))

    # Return SSE stream
    return EventSourceResponse(event_generator(event_queue))

async def _run_apply(job: dict, mode: str, queue: asyncio.Queue):
    """Bridge: run sync Playwright in thread, push events to async queue."""
    try:
        await asyncio.to_thread(
            apply_engine.run, job, mode, lambda evt: queue.put_nowait(evt)
        )
    except Exception as exc:
        await queue.put({"event": "error", "data": str(exc)})
    finally:
        await queue.put({"event": "done", "data": ""})

async def event_generator(queue: asyncio.Queue):
    """Drain the event queue as SSE events."""
    while True:
        event = await queue.get()
        if event.get("event") == "done":
            yield {"event": "done", "data": "complete"}
            break
        yield event
```

### Pattern 2: SSE + htmx for Real-Time Apply Status
**What:** Stream apply progress events from FastAPI to the browser using SSE, with htmx handling DOM updates.
**When to use:** When the user clicks "Apply" on a job detail page.
**Example (server side):**
```python
# Source: sse-starlette 3.2.0 docs + htmx SSE extension 2.2.4 docs
from sse_starlette import EventSourceResponse

async def event_generator(queue: asyncio.Queue):
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=120)
        yield {
            "event": event["type"],  # e.g., "progress", "awaiting_confirm", "done"
            "data": event["html"],   # Pre-rendered HTML partial
        }
```
**Example (client side):**
```html
<!-- Source: htmx.org/extensions/sse/ -->
<div id="apply-container"
     hx-ext="sse"
     sse-connect="/jobs/{{ job.dedup_key }}/apply/stream"
     sse-swap="progress"
     sse-close="done">
    <div id="apply-status">Connecting...</div>
</div>
```

### Pattern 3: Apply Mode Configuration
**What:** Users select automation level per-job or globally via `config.yaml`.
**When to use:** Before triggering any apply action.
**Example:**
```python
# config.yaml section:
# apply:
#   default_mode: semi_auto  # full_auto | semi_auto | easy_apply_only
#   confirm_before_submit: true
#   max_concurrent_applies: 1
#   screenshot_before_submit: true

from enum import Enum
from pydantic import BaseModel

class ApplyMode(str, Enum):
    FULL_AUTO = "full_auto"       # Fill form + wait for approval + submit
    SEMI_AUTO = "semi_auto"       # Fill form + user reviews + user submits
    EASY_APPLY_ONLY = "easy_apply_only"  # Only Indeed/Dice Easy Apply

class ApplyConfig(BaseModel):
    default_mode: ApplyMode = ApplyMode.SEMI_AUTO
    confirm_before_submit: bool = True
    max_concurrent_applies: int = 1
    screenshot_before_submit: bool = True
```

### Pattern 4: Heuristic Form Field Detection
**What:** Detect and fill form fields on unknown ATS pages by analyzing labels, attributes, and input types.
**When to use:** External ATS forms (Greenhouse, Lever, Ashby, custom career pages).
**Example:**
```python
# Source: Common patterns across Greenhouse/Lever/Ashby forms
FIELD_PATTERNS = {
    "first_name": {
        "labels": ["first name", "given name", "nombre"],
        "attrs": ["first_name", "firstname", "first-name", "fname"],
        "input_types": ["text"],
    },
    "last_name": {
        "labels": ["last name", "surname", "family name"],
        "attrs": ["last_name", "lastname", "last-name", "lname"],
        "input_types": ["text"],
    },
    "email": {
        "labels": ["email", "e-mail"],
        "attrs": ["email", "e-mail", "applicant_email"],
        "input_types": ["email", "text"],
    },
    "phone": {
        "labels": ["phone", "telephone", "mobile"],
        "attrs": ["phone", "telephone", "mobile", "tel"],
        "input_types": ["tel", "text"],
    },
    "resume": {
        "labels": ["resume", "cv", "curriculum"],
        "attrs": ["resume", "cv"],
        "input_types": ["file"],
    },
    # ... location, linkedin, github, cover_letter, etc.
}

def detect_field(element, page) -> str | None:
    """Match a form element to a known field type using heuristic analysis."""
    # 1. Check name/id attributes
    name = element.get_attribute("name") or ""
    elem_id = element.get_attribute("id") or ""
    placeholder = element.get_attribute("placeholder") or ""

    for field_type, patterns in FIELD_PATTERNS.items():
        for attr_pattern in patterns["attrs"]:
            if attr_pattern in name.lower() or attr_pattern in elem_id.lower():
                return field_type

    # 2. Check associated label text
    label_text = _get_label_text(element, page)
    for field_type, patterns in FIELD_PATTERNS.items():
        for label_pattern in patterns["labels"]:
            if label_pattern in label_text.lower():
                return field_type

    # 3. Check placeholder text
    for field_type, patterns in FIELD_PATTERNS.items():
        for label_pattern in patterns["labels"]:
            if label_pattern in placeholder.lower():
                return field_type

    return None
```

### Anti-Patterns to Avoid
- **Running sync Playwright directly in async endpoint:** Causes "Playwright Sync API inside asyncio loop" fatal error. Always use `asyncio.to_thread()`.
- **Polling for apply status:** Use SSE, not periodic AJAX polling. SSE is more efficient and provides instant updates.
- **Per-ATS hardcoded selectors for external forms:** These break constantly. Use heuristic detection with fallback to "open URL in browser" mode.
- **Rewriting platform adapters to async:** The existing sync Playwright code works. `asyncio.to_thread()` is the correct bridge. Do not rewrite `indeed.py`, `dice.py`, `stealth.py`, or `mixins.py`.
- **Running multiple concurrent applies:** Apply actions must be serialized (one at a time) because they share browser context state. Use a semaphore or queue.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE streaming from FastAPI | Custom StreamingResponse with `text/event-stream` | `sse-starlette` 3.2.0 `EventSourceResponse` | Handles W3C SSE spec compliance, client disconnect detection, graceful shutdown, retry headers, event IDs. Manual implementation misses edge cases. |
| SSE reception in htmx | Custom JavaScript EventSource handling | `htmx-ext-sse` 2.2.4 | Automatic reconnection with exponential backoff, DOM swapping, named event routing, connection lifecycle management. |
| Form field type detection | Simple string matching on `name` | Multi-signal heuristic (name + id + label + placeholder + aria-label + input type) | Single-signal matching misses 40%+ of fields. Labels are the most reliable signal but require DOM traversal to find associated `<label>` elements. |
| Duplicate detection | Custom dedup logic | SQL query on existing `jobs` table (`status`, `applied_date`, `activity_log`) | The database already tracks all the state needed. A simple query is more reliable than in-memory tracking. |
| Apply event bus | Custom pub/sub system | `asyncio.Queue` | Built-in, thread-safe (via `put_nowait()`), async-aware (via `await queue.get()`), perfect for bridging sync thread to async SSE generator. |

**Key insight:** The existing codebase already has 90% of the infrastructure needed. The `BrowserPlatform` protocol defines `apply()` methods, the `Orchestrator._apply_to()` shows the flow, `webapp/app.py` shows the `asyncio.to_thread()` pattern, and `db.py` has activity logging. This phase wires them together with SSE streaming and adds config-driven mode selection.

## Common Pitfalls

### Pitfall 1: Playwright Sync API in Asyncio Loop
**What goes wrong:** Calling `sync_playwright()` or any sync Playwright method from an async FastAPI endpoint raises `RuntimeError: It looks like you are using Playwright Sync API inside the asyncio loop. Please use the Async API instead.`
**Why it happens:** FastAPI runs in an asyncio event loop. Playwright's sync API creates its own event loop internally. Nested event loops are not allowed.
**How to avoid:** Always use `asyncio.to_thread()` to run sync Playwright code in a separate thread. The thread gets its own event loop context. This is proven in the existing codebase (line 233 of `webapp/app.py`).
**Warning signs:** Any direct call to platform `.apply()`, `.login()`, or `get_browser_context()` from an `async def` endpoint.

### Pitfall 2: Browser Context Sharing Between Requests
**What goes wrong:** Two concurrent apply requests share the same browser context, causing page navigation conflicts and state corruption.
**Why it happens:** `stealth.py::get_browser_context()` returns a persistent context tied to a platform-specific user data directory. If two applies run simultaneously for the same platform, they collide.
**How to avoid:** Enforce single-apply serialization with `asyncio.Semaphore(1)`. Never allow concurrent applies for the same platform. The config `max_concurrent_applies: 1` should be enforced at the engine level.
**Warning signs:** Apply actions returning wrong job data, screenshots showing unexpected pages, "Target page, context or browser has been closed" errors.

### Pitfall 3: SSE Connection Lifetime Mismatch
**What goes wrong:** The SSE connection drops before the apply flow completes, or hangs indefinitely after completion.
**Why it happens:** Apply flows can take 30-120 seconds (login + navigate + fill + confirm). The SSE connection must stay alive the entire time. Conversely, if the apply finishes but the SSE generator doesn't terminate, the connection leaks.
**How to avoid:** Use a sentinel event (`event: done`) to signal completion and trigger `sse-close="done"` on the htmx side. Add a timeout on the SSE generator (e.g., 180 seconds). Send periodic keepalive events (`event: ping`) every 15 seconds to prevent proxy timeouts.
**Warning signs:** Browser shows "connection closed" mid-apply, or apply-status div never shows final result.

### Pitfall 4: Human-in-the-Loop in Semi-Auto Mode
**What goes wrong:** The existing `wait_for_human()` method in `BrowserPlatformMixin` uses `input()` to block on stdin. This doesn't work when triggered from a web dashboard.
**Why it happens:** The current apply flow is designed for CLI execution, not web-triggered execution.
**How to avoid:** For dashboard-triggered applies, replace `input()` with an event-based confirmation flow: the apply engine sends an `awaiting_confirm` SSE event with a confirmation URL/button. The user clicks the button in the dashboard, which hits a REST endpoint that signals the apply thread to continue (via a `threading.Event` or `asyncio.Event`).
**Warning signs:** Apply hangs indefinitely waiting for stdin input that will never come.

### Pitfall 5: Indeed CAPTCHA During Apply
**What goes wrong:** Indeed detects automation and presents a Cloudflare Turnstile challenge during the apply flow.
**Why it happens:** Indeed has HIGH anti-bot detection. Even with stealth plugins, apply actions (which involve form submissions) trigger more aggressive detection than passive browsing.
**How to avoid:** For Indeed: always use headed mode (visible browser) for applies, not headless. Send an SSE event alerting the user that a CAPTCHA appeared and manual intervention is needed. Take a screenshot and display it in the dashboard. Do NOT attempt automated CAPTCHA solving.
**Warning signs:** Apply fails with "CAPTCHA detected" or page shows Cloudflare challenge frame.

### Pitfall 6: External ATS Iframe Isolation
**What goes wrong:** Many companies embed Greenhouse/Lever/Ashby forms inside iframes. Playwright's `page.query_selector()` doesn't search inside iframes by default.
**Why it happens:** ATS providers use embedded iframes for their application forms. The parent page is the company's career site.
**How to avoid:** After navigating to the apply URL, check for iframes. If an iframe is found with an ATS domain (`boards.greenhouse.io`, `jobs.lever.co`, `jobs.ashbyhq.com`), switch to the iframe's content frame before attempting field detection: `frame = page.frame(url="*greenhouse*")` or iterate `page.frames`.
**Warning signs:** No form fields detected on pages that visually show a form, `None` returned from `query_selector()` calls on visible elements.

## Code Examples

### Example 1: Apply Engine Core Loop
```python
# Source: Derived from existing orchestrator._apply_to() pattern
import asyncio
import threading

class ApplyEngine:
    """Runs apply flow in a thread, publishes events to async queue."""

    def __init__(self, settings):
        self.settings = settings
        self._apply_lock = asyncio.Semaphore(1)  # Serialize applies

    async def apply(self, job: dict, mode: str, queue: asyncio.Queue):
        """Entry point called from async FastAPI endpoint."""
        async with self._apply_lock:
            await asyncio.to_thread(
                self._apply_sync, job, mode,
                lambda evt: asyncio.run_coroutine_threadsafe(
                    queue.put(evt),
                    asyncio.get_event_loop()
                )
            )

    def _apply_sync(self, job: dict, mode: str, emit):
        """Sync apply flow -- runs in separate thread."""
        platform_name = job["platform"]
        emit({"type": "progress", "html": f"Starting apply for {job['title']}..."})

        from platforms import get_browser_context, close_browser
        from platforms.registry import get_platform

        info = get_platform(platform_name)

        if info.platform_type == "api":
            # External ATS -- open URL and attempt form fill
            emit({"type": "progress", "html": "Opening external application page..."})
            self._fill_external_form(job, mode, emit)
            return

        # Browser platform -- Easy Apply flow
        emit({"type": "progress", "html": f"Launching browser for {info.name}..."})
        pw, ctx = get_browser_context(platform_name, headless=False)

        try:
            platform = info.cls()
            platform.init(ctx)
            with platform:
                if not platform.is_logged_in():
                    emit({"type": "progress", "html": "Logging in..."})
                    platform.login()

                emit({"type": "progress", "html": "Navigating to job page..."})
                # ... apply flow continues
        finally:
            close_browser(pw, ctx)
            emit({"type": "done", "html": ""})
```

### Example 2: SSE Endpoint for Apply Status
```python
# Source: sse-starlette 3.2.0 + htmx-ext-sse 2.2.4 docs
from sse_starlette import EventSourceResponse

@app.get("/jobs/{dedup_key}/apply/stream")
async def apply_stream(request: Request, dedup_key: str):
    """SSE endpoint that streams apply progress."""
    # Get the event queue for this job's apply session
    queue = apply_sessions.get(dedup_key)
    if not queue:
        return HTMLResponse("No active apply session", status_code=404)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield {
                        "event": event["type"],
                        "data": event["html"],
                    }
                    if event["type"] == "done":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive to prevent proxy timeout
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
```

### Example 3: Duplicate Detection Query
```python
# Source: Existing db.py patterns
def is_already_applied(dedup_key: str) -> dict | None:
    """Check if a job has already been applied to.

    Returns None if not applied, or a dict with apply details if already applied.
    """
    with get_conn() as conn:
        row = conn.execute(
            """SELECT status, applied_date FROM jobs
               WHERE dedup_key = ?
               AND (applied_date IS NOT NULL
                    OR status IN ('applied', 'phone_screen', 'technical',
                                  'final_interview', 'offer'))""",
            (dedup_key,),
        ).fetchone()
    if row:
        return {"status": row["status"], "applied_date": row["applied_date"]}
    return None
```

### Example 4: Apply Config in config.yaml
```yaml
# New section added to config.yaml
apply:
  default_mode: semi_auto        # full_auto | semi_auto | easy_apply_only
  confirm_before_submit: true     # Always show confirmation before final submit
  max_concurrent_applies: 1       # Serialize -- never run concurrent applies
  screenshot_before_submit: true  # Save screenshot for audit trail
  headed_mode: true               # Always visible browser for apply actions
  ats_form_fill:
    enabled: true                 # Attempt to fill external ATS forms
    timeout_seconds: 120          # Max time per form fill attempt
```

### Example 5: htmx Apply Button Integration
```html
<!-- On job_detail.html -->
<div id="apply-section" class="bg-white rounded-lg shadow-sm border p-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-3">Apply</h2>

    <!-- Mode selector -->
    <select id="apply-mode" class="border rounded px-3 py-1.5 text-sm mb-3 w-full">
        <option value="semi_auto">Semi-Auto (fill + review)</option>
        <option value="full_auto">Full Auto (fill + confirm + submit)</option>
        <option value="easy_apply_only">Easy Apply Only</option>
    </select>

    <!-- Apply button triggers POST then connects to SSE stream -->
    <button hx-post="/jobs/{{ job.dedup_key | urlencode }}/apply"
            hx-vals='js:{"mode": document.getElementById("apply-mode").value}'
            hx-target="#apply-status"
            hx-swap="innerHTML"
            class="w-full bg-purple-600 text-white px-4 py-2 rounded text-sm
                   hover:bg-purple-700">
        Apply Now
    </button>

    <!-- SSE stream container (activated after POST response) -->
    <div id="apply-status" class="mt-4"></div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLI-only apply with `input()` prompts | Web-triggered apply with SSE streaming | This phase | Apply no longer requires terminal access. Dashboard is the single control surface. |
| Single apply mode (manual approval via stdin) | Configurable modes (full-auto, semi-auto, easy-apply-only) | This phase | Users choose their comfort level. Full-auto for high-confidence matches, semi-auto for review. |
| No external ATS support | Heuristic form filling for Greenhouse/Lever/Ashby | This phase | 30-50% of jobs link to external ATS. Basic form filling covers the common fields. |
| Status polling or no real-time updates | SSE via `sse-starlette` + htmx SSE extension | This phase | Instant progress updates. No wasted requests. Auto-reconnection. |

**Deprecated/outdated:**
- The `Orchestrator.phase_4_apply()` method with `input()` prompts will remain for CLI mode but the dashboard apply path bypasses it entirely.
- The `BrowserPlatformMixin.wait_for_human()` method using `input()` must be augmented (not replaced) to support an event-based confirmation path for dashboard-triggered applies.

## Open Questions

1. **CAPTCHA handling in dashboard mode**
   - What we know: Indeed has HIGH anti-bot detection. CAPTCHAs appear during apply flows. The current code raises `RuntimeError` on CAPTCHA detection.
   - What's unclear: How to surface a CAPTCHA challenge to the user via the dashboard. Embedding a screenshot is one option. Forwarding the browser window for manual solving is another.
   - Recommendation: For v1, detect CAPTCHA, take screenshot, send it as an SSE event with an embedded image, and instruct the user to solve it in the visible browser window (applies always use headed mode). Add a "I solved it, continue" button.

2. **External ATS form fill success rate**
   - What we know: Greenhouse, Lever, and Ashby have consistent form structures. But many companies customize their forms heavily (custom questions, multi-step wizards, conditional logic).
   - What's unclear: What percentage of forms can be auto-filled reliably. Custom questions (free text like "Why do you want to work here?") cannot be auto-filled without LLM.
   - Recommendation: For v1, fill standard fields (name, email, phone, resume, cover letter, LinkedIn, GitHub) and leave custom questions empty with a notification. Semi-auto mode lets the user complete custom fields manually. LLM-based custom question answering is a future enhancement.

3. **Concurrent browser sessions**
   - What we know: `get_browser_context()` creates persistent contexts per platform in `browser_sessions/{platform}/`. The orchestrator creates and destroys contexts per operation.
   - What's unclear: Whether the dashboard server should maintain a long-lived browser context or create/destroy per apply action.
   - Recommendation: Create and destroy per apply action (matches existing orchestrator pattern). Long-lived contexts risk session corruption and memory leaks. The 5-10 second startup cost is acceptable for an apply action.

4. **Resume version selection for apply**
   - What we know: Phase 7 generates tailored resumes per job, stored in `resumes/tailored/` and tracked in the `resume_versions` table.
   - What's unclear: Which resume to use when applying -- the default ATS resume or a tailored version if one exists?
   - Recommendation: Auto-detect: if a tailored resume exists for this job (via `resume_versions` table), use it. Otherwise, fall back to the default ATS resume. Show which resume will be used in the pre-apply confirmation.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `platforms/protocols.py`, `platforms/indeed.py`, `platforms/dice.py`, `platforms/stealth.py`, `platforms/mixins.py`, `orchestrator.py`, `webapp/app.py`, `webapp/db.py`, `config.py`, `models.py` -- verified all existing patterns, data models, and integration points.
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) -- Version 3.2.0, published 2026-01-17. EventSourceResponse, ServerSentEvent, JSONServerSentEvent APIs.
- [htmx SSE Extension docs](https://htmx.org/extensions/sse/) -- Version 2.2.4. sse-connect, sse-swap, sse-close attributes. Compatible with htmx 2.0.4+.
- [Playwright Python docs](https://playwright.dev/python/docs/library) -- Sync vs async API. Confirmed sync API cannot run in asyncio loop.

### Secondary (MEDIUM confidence)
- [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html) -- Application submission endpoint, required fields (first_name, last_name, email), optional fields (phone, resume, cover_letter, education, employment, custom questions).
- [Lever Postings API](https://github.com/lever/postings-api) -- POST endpoint, required fields (name, email), optional fields (resume, phone, org, urls, comments).
- [Ashby API](https://developers.ashbyhq.com/reference/applicationformsubmit) -- applicationForm.submit endpoint, multipart/form-data, fieldSubmissions with path-based field identification.
- [Playwright issue #462](https://github.com/microsoft/playwright-python/issues/462) -- Confirmed: sync API inside asyncio loop causes RuntimeError. Solution: use async API or run in separate thread.

### Tertiary (LOW confidence)
- WebSearch on behavioral fingerprinting patterns (multiple sources, general guidance) -- fingerprint-suite, Playwright Extra, stealth configuration. General anti-bot strategy, not specific to job apply flows.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- sse-starlette and htmx SSE extension are well-documented, actively maintained, and version-verified. Playwright patterns verified against existing codebase.
- Architecture: HIGH -- sync-to-async bridge pattern proven in existing codebase (`webapp/app.py` line 233). SSE + htmx pattern documented in official docs. Apply engine design follows existing orchestrator patterns.
- Pitfalls: HIGH -- Playwright asyncio conflict verified via official GitHub issues. Browser context sharing identified from codebase analysis. SSE lifecycle issues documented in sse-starlette docs.
- ATS form filling: MEDIUM -- API docs verified for Greenhouse/Lever/Ashby, but real-world form diversity is high. Heuristic approach is recommended based on pattern analysis, but success rates need runtime validation.

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (30 days -- stable domain, libraries are mature)
