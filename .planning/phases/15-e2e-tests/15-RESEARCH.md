# Phase 15: E2E Tests - Research

**Researched:** 2026-02-08
**Domain:** Playwright browser testing for FastAPI + htmx + SQLite dashboard
**Confidence:** HIGH

## Summary

Phase 15 requires writing Playwright-based E2E browser tests that exercise the JobFlow web dashboard end-to-end: loading pages, filtering jobs, changing status, drag-and-drop on the kanban board, and downloading CSV/JSON exports. The existing codebase already has Playwright installed (v1.58.0), pytest markers configured (`@pytest.mark.e2e`), and a CI workflow with a dedicated E2E job. The project uses `pytest-socket` with `--disable-socket` globally, so E2E tests need the `@pytest.mark.enable_socket` marker or `--force-enable-socket` flag.

The core challenge is starting a live FastAPI server for Playwright to navigate against. The standard pattern is a session-scoped pytest fixture that runs uvicorn in a background daemon thread, polls for readiness, yields the base URL, then signals shutdown. The existing in-memory SQLite database (`JOBFLOW_TEST_DB=1`) must be shared between the server thread and the test assertions, which works because `db.py` uses a singleton `_memory_conn` with `check_same_thread=False`.

**Primary recommendation:** Use `pytest-playwright` for fixtures/CLI, run uvicorn in a daemon thread via a session-scoped fixture, use `@pytest.mark.enable_socket` on all E2E tests, and use manual mouse events (not `drag_to()`) for SortableJS kanban drag-and-drop.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-playwright | latest (pip install) | Playwright pytest integration - page/browser/context fixtures | Official Microsoft plugin for Playwright Python |
| playwright | 1.58.0 (already installed) | Browser automation engine | Already in project, used for scraping |
| pytest | 8.0+ (already installed) | Test framework | Already in project |
| uvicorn | 0.34.0+ (already installed) | ASGI server for live testing | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-socket | 0.7.0+ (already installed) | Socket control with `@pytest.mark.enable_socket` | Override global `--disable-socket` for E2E tests |
| factory-boy | 3.3.0+ (already installed) | Test data factories (JobFactory) | Seed database with test data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Threading uvicorn | subprocess uvicorn | subprocess is harder to share in-memory DB with, threading is simpler |
| pytest-playwright | Raw playwright sync API | Lose built-in fixtures, CLI args (--headed, --tracing), page isolation |
| Manual mouse events for D&D | locator.drag_to() | drag_to() fails with SortableJS's forceFallback; manual mouse is reliable |

**Installation:**
```bash
pip install pytest-playwright
# or add to pyproject.toml dev dependencies:
# "pytest-playwright>=0.6.0"
```

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── conftest.py                    # Existing: _fresh_db, _reset_settings, db_with_jobs
├── conftest_factories.py          # Existing: JobFactory
├── e2e/
│   ├── __init__.py
│   ├── conftest.py                # E2E-specific: live_server fixture, e2e_db seeding, browser config
│   ├── test_dashboard.py          # E2E-01, E2E-02: dashboard load + filtering
│   ├── test_status_update.py      # E2E-03: status change via UI + persistence
│   ├── test_kanban.py             # E2E-04: drag-and-drop on kanban board
│   └── test_export.py             # E2E-05: CSV/JSON file downloads
```

### Pattern 1: Live Server Fixture (Session-Scoped)
**What:** Start uvicorn in a daemon thread, wait for readiness, yield base URL
**When to use:** All E2E tests -- they need a real HTTP server to navigate against
**Example:**
```python
# tests/e2e/conftest.py
import threading
import time
import socket
import pytest
from uvicorn import Config, Server

from webapp.app import app

def _port_is_open(host: str, port: int) -> bool:
    """Check if a port is accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex((host, port)) == 0

@pytest.fixture(scope="session")
def live_server():
    """Start uvicorn serving the FastAPI app in a background thread."""
    host, port = "127.0.0.1", 8765  # Use non-standard port to avoid conflicts
    config = Config(app=app, host=host, port=port, log_level="warning")
    server = Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server readiness
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if _port_is_open(host, port):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Live server failed to start within 10 seconds")

    yield f"http://{host}:{port}"

    server.should_exit = True
    thread.join(timeout=5)
```

### Pattern 2: Database Seeding for E2E Tests
**What:** Seed the in-memory database BEFORE the live server starts answering requests
**When to use:** E2E tests that need pre-populated data
**Critical detail:** The `webapp.db` module uses a module-level singleton `_memory_conn` with `check_same_thread=False`, so the test thread and the server thread share the same in-memory SQLite connection. This means `db.upsert_job()` calls from the test thread are immediately visible to the server.
**Example:**
```python
@pytest.fixture
def seeded_db(_fresh_db):
    """Seed the in-memory database with jobs for E2E tests."""
    from tests.conftest_factories import JobFactory
    import webapp.db as db_module

    jobs = []
    for platform in ("indeed", "dice", "remoteok"):
        for score in (3, 4, 5):
            job = JobFactory(
                platform=platform,
                score=score,
                status="scored",  # scored so they show on kanban as "saved" after move
            )
            db_module.upsert_job(job.model_dump(mode="json"))
            jobs.append(job)

    # Add some jobs with specific statuses for kanban testing
    saved_job = JobFactory(platform="indeed", score=4, title="Kanban Test Job")
    db_module.upsert_job(saved_job.model_dump(mode="json"))
    key = f"{saved_job.company.lower().strip()}::{saved_job.title.lower().strip()}"
    # Normalize the key the same way db.py does
    db_module.update_job_status(key, "saved")

    return jobs
```

### Pattern 3: Browser Context Configuration for E2E
**What:** Configure Playwright browser context with accept_downloads and viewport
**When to use:** E2E tests, especially export/download tests
**Example:**
```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "accept_downloads": True,
    }
```

### Pattern 4: Manual Drag-and-Drop for SortableJS
**What:** Use mouse.down/move/up instead of drag_to() for SortableJS columns
**When to use:** E2E-04 kanban drag-and-drop test
**Why:** SortableJS with `forceFallback: true` intercepts pointer events and doesn't respond to native HTML5 drag events that Playwright's `drag_to()` dispatches
**Example:**
```python
async def drag_card_to_column(page, card_locator, target_column_locator):
    """Drag a kanban card to a target column using manual mouse events."""
    source_box = await card_locator.bounding_box()
    target_box = await target_column_locator.bounding_box()

    # Move to center of source card
    await page.mouse.move(
        source_box["x"] + source_box["width"] / 2,
        source_box["y"] + source_box["height"] / 2,
    )
    await page.mouse.down()

    # Move to center of target column (repeat move for SortableJS to register)
    target_x = target_box["x"] + target_box["width"] / 2
    target_y = target_box["y"] + target_box["height"] / 2
    await page.mouse.move(target_x, target_y, steps=10)
    await page.mouse.move(target_x, target_y)  # Second move for SortableJS

    await page.mouse.up()
```

### Pattern 5: Download Testing
**What:** Use `page.expect_download()` context manager to capture file downloads
**When to use:** E2E-05 export CSV/JSON tests
**Example:**
```python
def test_export_csv_download(page, live_server, seeded_db):
    page.goto(f"{live_server}/")

    with page.expect_download() as download_info:
        page.locator("#export-csv-link").click()

    download = download_info.value
    assert "jobs_export_" in download.suggested_filename
    assert download.suggested_filename.endswith(".csv")

    # Read and validate content
    path = download.path()
    content = path.read_text()
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) > 0
```

### Anti-Patterns to Avoid
- **Using TestClient for E2E:** TestClient bypasses the network layer -- it tests routes, not browser interaction. E2E tests must use a real HTTP server with Playwright navigating to it.
- **Using drag_to() for SortableJS:** The kanban board uses `forceFallback: true` which replaces native drag with JavaScript pointer tracking. Playwright's `drag_to()` dispatches native drag events that SortableJS ignores.
- **Sharing database state between session-scoped server and function-scoped tests without coordination:** The in-memory DB is a singleton, so if one test changes data, subsequent tests see those changes. Either reset DB between tests or design tests to be order-independent.
- **Forgetting `@pytest.mark.enable_socket`:** Without it, `pytest-socket` blocks all network calls and E2E tests fail with `SocketBlockedError`.
- **Running E2E tests with the default `pytest` command:** The `addopts` includes `-m "not e2e"` and `--disable-socket`, so E2E tests need explicit invocation: `pytest -m e2e -p no:socket` or `pytest -m e2e --force-enable-socket`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser lifecycle | Manual Playwright sync_api setup/teardown | pytest-playwright fixtures (page, context, browser) | Handles isolation, cleanup, CLI args automatically |
| Waiting for page updates | Manual sleep() calls | Playwright auto-waiting + expect() assertions | Playwright waits for elements, reduces flakiness |
| Server startup/shutdown | Complex process management | uvicorn.Server in daemon thread | Clean, in-process, shares memory with tests |
| Download file handling | Manual temp file management | page.expect_download() + download.path() | Playwright manages temp files, cleanup is automatic |
| Screenshot on failure | Manual try/except screenshot | pytest-playwright --screenshot=only-on-failure | Built-in CLI flag, automatic |

**Key insight:** pytest-playwright eliminates 80% of the browser lifecycle boilerplate. The remaining work is the server fixture and test-specific assertions.

## Common Pitfalls

### Pitfall 1: Socket Blocking Kills E2E Tests
**What goes wrong:** E2E tests fail with `SocketBlockedError` because `pyproject.toml` has `--disable-socket` in addopts
**Why it happens:** The socket blocker applies globally; E2E tests are marked `not e2e` so they normally don't run, but when you run them explicitly the addopts still apply
**How to avoid:** Use `@pytest.mark.enable_socket` on all E2E test classes/functions, OR run with `pytest -m e2e -p no:socket` (disable the socket plugin entirely for E2E runs), OR add `--force-enable-socket` to the CI E2E command
**Warning signs:** `SocketBlockedError: A]test tried to use socket.socket` error message

### Pitfall 2: htmx Partial Swaps Not Awaited
**What goes wrong:** Test asserts on page content before htmx has finished swapping in new content
**Why it happens:** htmx makes async XHR requests; clicking a filter button triggers an htmx request that replaces part of the DOM, but Playwright sees the click as complete immediately
**How to avoid:** After triggering an htmx action, use `page.wait_for_response()` to wait for the XHR, or use `expect(locator).to_have_text()` / `expect(locator).to_contain_text()` which auto-waits, or `page.wait_for_load_state("networkidle")`
**Warning signs:** Flaky tests that pass sometimes and fail at assertion time

### Pitfall 3: SortableJS Drag-and-Drop Requires Manual Mouse Control
**What goes wrong:** `locator.drag_to()` doesn't work -- card doesn't move, status doesn't update
**Why it happens:** Kanban board uses SortableJS with `forceFallback: true`, which intercepts pointer events via JavaScript rather than using native HTML5 drag-and-drop API
**How to avoid:** Use `page.mouse.move()` / `page.mouse.down()` / `page.mouse.up()` sequence with multiple move steps. Pass `steps=10` to `mouse.move()` so SortableJS registers the drag distance
**Warning signs:** Drag operation "completes" but card stays in original column

### Pitfall 4: Database State Leaks Between Tests
**What goes wrong:** Test B fails because Test A left data in the in-memory database
**Why it happens:** The live server fixture is session-scoped but the database fixture is function-scoped. If the server is restarted per-test it's too slow; if the DB isn't reset per-test, state leaks
**How to avoid:** Use the existing `_fresh_db` autouse fixture from `tests/conftest.py` which closes and recreates the in-memory connection before each test. The live server fixture should be session-scoped, and the server will automatically use whatever the current `_memory_conn` is because `get_conn()` returns the singleton
**Warning signs:** Tests pass individually but fail when run together

### Pitfall 5: CDN Resources Not Loading in CI
**What goes wrong:** Tailwind CSS and htmx loaded from CDN (unpkg, cdn.jsdelivr.net) fail to load in CI environments with restricted network or slow connections
**Why it happens:** base.html loads `cdn.tailwindcss.com`, `unpkg.com/htmx.org`, `unpkg.com/htmx-ext-sse`, and kanban.html loads `cdn.jsdelivr.net/npm/sortablejs`
**How to avoid:** These CDN resources are external CSS/JS for styling and interaction. For E2E tests, the functional behavior still works even if Tailwind CSS doesn't load (layout may differ but elements are still present). htmx and SortableJS ARE critical -- they must load for the app to function. CI should allow outbound HTTPS or the test should verify htmx is loaded before proceeding
**Warning signs:** Page loads but no interactive behavior (filters, status updates don't work)

### Pitfall 6: Port Conflicts
**What goes wrong:** Live server fails to start because port is already in use
**Why it happens:** Using port 8000 (same as dev server), or parallel test runs reuse the same port
**How to avoid:** Use a non-standard port like 8765 for E2E tests, or dynamically find a free port using `socket.bind(('', 0))`
**Warning signs:** `OSError: [Errno 48] Address already in use`

## Code Examples

### E2E Test: Dashboard Load and Job Display (E2E-01)
```python
# Source: Verified against webapp/app.py dashboard route and dashboard.html template
import pytest
from playwright.sync_api import expect

@pytest.mark.e2e
@pytest.mark.enable_socket
class TestDashboardE2E:

    def test_dashboard_loads_and_shows_jobs(self, page, live_server, seeded_db):
        """E2E-01: Dashboard loads in browser and displays job list."""
        page.goto(f"{live_server}/")

        # Page title
        expect(page).to_have_title("Dashboard — Job Tracker")

        # Navigation is present
        expect(page.locator("nav")).to_be_visible()
        expect(page.locator("text=Job Tracker")).to_be_visible()

        # Stats bar shows total
        expect(page.locator("text=Total Jobs")).to_be_visible()

        # Job table is present with rows
        rows = page.locator("#job-table-body tr.job-row")
        expect(rows.first).to_be_visible()
        assert rows.count() > 0
```

### E2E Test: Filtering (E2E-02)
```python
    def test_filter_by_platform(self, page, live_server, seeded_db):
        """E2E-02: Filtering by platform returns correct subset."""
        page.goto(f"{live_server}/")

        # Select platform filter
        page.select_option('select[name="platform"]', "dice")
        page.click('button[type="submit"]:has-text("Filter")')

        # Wait for page to reload with filter applied
        page.wait_for_load_state("networkidle")

        # All visible rows should show "dice" platform
        rows = page.locator("#job-table-body tr.job-row")
        for i in range(rows.count()):
            row_text = rows.nth(i).inner_text()
            assert "dice" in row_text.lower()
```

### E2E Test: Status Change Persists (E2E-03)
```python
    def test_status_change_persists(self, page, live_server, seeded_db):
        """E2E-03: Changing status via UI persists after reload."""
        page.goto(f"{live_server}/")

        # Click first job row to go to detail page
        page.locator("#job-table-body tr.job-row").first.click()
        page.wait_for_load_state("networkidle")

        # Change status via the dropdown + submit
        page.select_option('select[name="status"]', "saved")
        page.click('button:has-text("Update")')

        # Wait for htmx response
        page.wait_for_response(lambda r: "/status" in r.url)

        # Verify badge updated
        expect(page.locator("#status-display")).to_contain_text("Saved")

        # Reload and verify persistence
        page.reload()
        page.wait_for_load_state("networkidle")
        expect(page.locator("#status-display")).to_contain_text("Saved")
```

### E2E Test: Download Verification (E2E-05)
```python
import csv
import io
import json

@pytest.mark.e2e
@pytest.mark.enable_socket
class TestExportE2E:

    def test_csv_download(self, page, live_server, seeded_db):
        """E2E-05: Export CSV button triggers valid file download."""
        page.goto(f"{live_server}/")

        with page.expect_download() as download_info:
            page.locator("#export-csv-link").click()

        download = download_info.value
        assert download.suggested_filename.endswith(".csv")

        content = download.path().read_text()
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) > 0
        assert "title" in reader.fieldnames
        assert "company" in reader.fieldnames

    def test_json_download(self, page, live_server, seeded_db):
        """E2E-05: Export JSON button triggers valid file download."""
        page.goto(f"{live_server}/")

        with page.expect_download() as download_info:
            page.locator("#export-json-link").click()

        download = download_info.value
        assert download.suggested_filename.endswith(".json")

        content = download.path().read_text()
        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "title" in data[0]
```

### CI E2E Command (Already Configured)
```bash
# From .github/workflows/ci.yml line 72 -- already in place
uv run pytest -m e2e --tracing=retain-on-failure || true
```

**Critical note:** This CI command may fail because `--disable-socket` from addopts is still active. The command needs either `--force-enable-socket` or `-p no:socket`:
```bash
uv run pytest -m e2e -p no:socket --tracing=retain-on-failure || true
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| subprocess server | Threading server | N/A | Simpler, shares memory, avoids IPC for DB state |
| Manual Playwright setup | pytest-playwright fixtures | Stable since 2023 | Auto page/context isolation, CLI args for debugging |
| Native drag-and-drop API | Manual mouse events for JS libs | Always needed | SortableJS/react-dnd require pointer events, not drag events |
| time.sleep() waits | Playwright auto-waiting + expect() | Playwright 1.20+ | Dramatically reduces flakiness |

**Deprecated/outdated:**
- `page.wait_for_selector()` -- prefer `expect(locator).to_be_visible()` (auto-waiting assertion)
- `page.$(selector)` -- prefer `page.locator(selector)` (lazy evaluation, auto-waiting)
- Synchronous `playwright.sync_api` for new tests -- pytest-playwright handles this automatically

## Open Questions

1. **Sync vs Async Playwright in pytest**
   - What we know: pytest-playwright provides sync fixtures by default (`page` is sync). The dashboard tests don't need async.
   - What's unclear: Whether the live server thread + sync Playwright + async FastAPI causes any issues
   - Recommendation: Use sync Playwright (default pytest-playwright). The server runs in its own thread with its own event loop. No conflict expected.

2. **Database Reset Strategy for Session-Scoped Server**
   - What we know: `_fresh_db` autouse fixture closes and recreates `_memory_conn` before each test. The live server calls `get_conn()` which returns `_memory_conn`. After reset, the server's next request will use the new connection.
   - What's unclear: Whether there's a race condition where the server is mid-request when the test resets the connection
   - Recommendation: Keep the current `_fresh_db` fixture. Since E2E tests drive the browser and wait for responses, there's a natural synchronization point. The test won't reset the DB while the server is responding because the test is waiting for that response. If issues arise, add a small delay or use a lock.

3. **CDN Dependency for htmx/SortableJS**
   - What we know: base.html loads htmx from unpkg.com and kanban.html loads SortableJS from jsdelivr.net
   - What's unclear: Whether CI runners have reliable CDN access
   - Recommendation: CI already allows outbound HTTPS (it installs packages). CDN resources should load fine. If flaky, add a `page.wait_for_function("typeof htmx !== 'undefined'")` guard.

## Sources

### Primary (HIGH confidence)
- Playwright Python official docs: [pytest plugin reference](https://playwright.dev/python/docs/test-runners)
- Playwright Python official docs: [downloads](https://playwright.dev/python/docs/downloads)
- Playwright Python official docs: [input actions](https://playwright.dev/python/docs/input)
- pytest-socket GitHub: [README with enable_socket marker](https://github.com/miketheman/pytest-socket/blob/main/README.md)
- Codebase analysis: `webapp/app.py`, `webapp/db.py`, `webapp/templates/`, `tests/conftest.py`, `pyproject.toml`, `.github/workflows/ci.yml`

### Secondary (MEDIUM confidence)
- [pythontutorials.net: uvicorn threading fixture pattern](https://www.pythontutorials.net/blog/how-to-start-a-uvicorn-fastapi-in-background-when-testing-with-pytest/)
- [Reflect.run: drag-and-drop in Playwright](https://reflect.run/articles/how-to-test-drag-and-drop-interactions-in-playwright/)
- [BrowserStack: Playwright drag and drop guide](https://www.browserstack.com/guide/playwright-drag-and-drop)

### Tertiary (LOW confidence)
- None -- all findings verified against official docs or codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest-playwright is the official plugin, Playwright 1.58.0 is already installed, all dependencies are already in the project
- Architecture: HIGH - Server threading pattern is well-established, database singleton with `check_same_thread=False` is verified in `webapp/db.py`
- Pitfalls: HIGH - Socket blocking verified in `pyproject.toml`, SortableJS `forceFallback` verified in `kanban.html`, CDN dependencies verified in `base.html`
- Drag-and-drop: MEDIUM - Manual mouse approach is widely recommended for SortableJS but exact step count may need tuning

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable domain, Playwright API is mature)
