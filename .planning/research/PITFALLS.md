# Domain Pitfalls: Adding a Test Suite to JobFlow

**Domain:** Automated test suite + CI pipeline for a Python/FastAPI/Playwright job search automation app
**Researched:** 2026-02-08
**Confidence:** HIGH (grounded in direct codebase analysis of all 20+ modules, verified against pytest/FastAPI documentation)

---

## Critical Pitfalls

Mistakes that cause test suites to be unreliable, misleading, or abandoned entirely.

---

### Pitfall 1: The `webapp.db` Module Runs `init_db()` at Import Time

**What goes wrong:** Line 723 of `webapp/db.py` calls `init_db()` as a module-level side effect. This means _any_ import of `webapp.db` (or anything that transitively imports it) immediately creates a SQLite database, runs the full migration chain (6 versions, including FTS5 virtual tables and triggers), and sets `PRAGMA user_version`. In tests, this fires before any fixture has a chance to set up a test database. The production `jobs.db` file gets touched by test collection. If the file doesn't exist (CI environment), it gets created in the wrong location.

**Why it happens:** The module was designed for a single-process dashboard app where eager initialization is convenient. The `JOBFLOW_TEST_DB=1` environment variable support exists but must be set _before_ the module is first imported, which pytest doesn't guarantee unless carefully managed.

**Consequences:**
- Tests corrupt the production database if run from the project root
- In CI, `init_db()` creates `job_pipeline/jobs.db` in the checkout directory, which may be read-only
- FTS5 virtual tables fail silently if the SQLite build doesn't include FTS5 (some CI images have minimal SQLite)
- The `_memory_conn` singleton persists across tests if not explicitly reset, leaking state between test functions

**Prevention:**
1. Set `JOBFLOW_TEST_DB=1` in `conftest.py` at the very top, before any application imports. Use `os.environ["JOBFLOW_TEST_DB"] = "1"` as the first line.
2. Add a session-scoped fixture that resets `webapp.db._memory_conn = None` and calls `webapp.db.init_db()` to guarantee a clean schema, then a function-scoped fixture that resets `_memory_conn` between tests for isolation.
3. Never import `webapp.db` at the top of test files -- always import inside test functions or via fixtures that run after environment setup.
4. In CI, verify the SQLite version supports FTS5: `sqlite3.connect(":memory:").execute("pragma compile_options").fetchall()` and check for `ENABLE_FTS5`.

**Detection (warning signs):**
- Tests pass locally but fail in CI with "no such table: jobs_fts"
- A `jobs.db` file appears in `job_pipeline/` after running tests
- Tests that modify job data see stale data from previous tests

**Phase:** Must be the FIRST thing addressed. The `conftest.py` environment setup is a prerequisite for every other test.

**Confidence:** HIGH -- verified by direct reading of `webapp/db.py` lines 10-16, 152-168, and 723.

---

### Pitfall 2: The `config.py` Singleton Poisons Cross-Test State

**What goes wrong:** `config.py` uses a module-level `_settings: AppSettings | None = None` singleton cached by `get_settings()`. Once any test calls `get_settings()`, ALL subsequent tests in the same process get the same `AppSettings` instance -- including its credential fields, search queries, scoring weights, and platform toggles. Tests that need different configurations (e.g., testing with Dice disabled, or testing with different scoring weights) silently use the first test's configuration.

**Why it happens:** The singleton pattern is efficient for production but toxic for test isolation. The `reset_settings()` function exists (line 315) but only clears the cache -- it doesn't prevent the next `get_settings()` from reading the real `config.yaml` and `.env` files, which may not exist in CI.

**Consequences:**
- Tests depend on the order they run (first test sets the singleton)
- Tests fail in CI because `config.yaml` doesn't exist, causing `ValidationError` on required fields (`search.queries`, `scoring.target_titles`)
- Credential fields (`dice_password`, etc.) leak into test output/logs
- Changing scoring weights in one test affects scoring tests that run later

**Prevention:**
1. Create a `tests/fixtures/config.yaml` with minimal valid configuration (a few search queries, a few tech keywords, all platforms disabled). This is the "test config" that every test uses.
2. Build a `conftest.py` fixture that calls `reset_settings()` in teardown AND patches the YAML file path to point at the test config:
   ```python
   @pytest.fixture(autouse=True)
   def clean_settings(tmp_path):
       from config import reset_settings
       reset_settings()
       yield
       reset_settings()
   ```
3. For tests that need custom settings, use `AppSettings` constructor directly with explicit kwargs instead of `get_settings()` -- this bypasses the singleton entirely.
4. Never rely on `.env` existing in tests. Set `env_file = None` or use `model_config` overrides in test fixtures.

**Detection (warning signs):**
- Tests pass when run individually but fail when run together
- `pytest --randomly-seed=X` produces different pass/fail results
- Tests fail in CI with "field required" errors on settings fields

**Phase:** Must be addressed in the same initial `conftest.py` setup as Pitfall 1. Settings and database isolation are co-dependent.

**Confidence:** HIGH -- verified by direct reading of `config.py` lines 288-317 and the `AppSettings` class.

---

### Pitfall 3: Platform Auto-Discovery Imports Playwright at Collection Time

**What goes wrong:** `platforms/__init__.py` calls `_auto_discover()` at import time (line 36), which uses `pkgutil.iter_modules` to import every platform module. This imports `platforms/indeed.py`, `platforms/dice.py`, and `platforms/stealth.py`, all of which have top-level `from playwright.sync_api import ...` imports. If Playwright is not installed (lightweight CI) or browsers aren't available, test collection crashes with `ImportError` before a single test runs.

Even if Playwright is installed, importing `stealth.py` instantiates `_stealth = Stealth()` at module level (line 9), which may have side effects depending on the playwright-stealth version.

**Why it happens:** The decorator-based platform registry (`@register_platform`) requires modules to be imported for registration to occur. This is a classic tradeoff between convenient auto-discovery and testability.

**Consequences:**
- Cannot run ANY tests in a CI environment that doesn't have Playwright + Chromium installed
- Tests for pure-logic modules (scorer, dedup, salary, models) fail at collection because they transitively import platform code
- The 400MB Playwright browser download becomes a CI requirement even for unit tests

**Prevention:**
1. Structure tests in layers that control imports:
   - `tests/unit/` -- NEVER imports `platforms`, `orchestrator`, or `webapp.app`. Tests `scorer.py`, `dedup.py`, `salary.py`, `models.py` in isolation.
   - `tests/integration/` -- Imports webapp/db but mocks Playwright. Tests FastAPI endpoints via `TestClient`.
   - `tests/e2e/` -- Requires Playwright. Tests platform modules (skipped in CI without browsers).
2. For unit tests, avoid importing anything from `platforms` or `orchestrator` at the top of test files. If a unit under test imports from `platforms`, mock the import:
   ```python
   import sys
   sys.modules["platforms"] = MagicMock()
   ```
3. In CI, use conditional test markers:
   ```python
   # conftest.py
   import pytest
   try:
       import playwright
       HAS_PLAYWRIGHT = True
   except ImportError:
       HAS_PLAYWRIGHT = False

   playwright_required = pytest.mark.skipif(
       not HAS_PLAYWRIGHT, reason="Playwright not installed"
   )
   ```
4. Mark all tests that need a browser with `@pytest.mark.playwright` and exclude them in fast CI runs: `pytest -m "not playwright"`.

**Detection (warning signs):**
- `pytest --collect-only` crashes with `ModuleNotFoundError: playwright`
- CI pipeline installs Playwright + Chromium for a "unit test" job that never opens a browser
- Test suite takes 3+ minutes just to install dependencies

**Phase:** Must be addressed in test directory structure design (Phase 1). Getting import boundaries wrong early means restructuring every test file later.

**Confidence:** HIGH -- verified by reading `platforms/__init__.py` lines 24-36 and `platforms/stealth.py` lines 6-9.

---

### Pitfall 4: Testing `asyncio.to_thread` Code Without Understanding the Event Loop

**What goes wrong:** The webapp uses `asyncio.to_thread()` in multiple endpoints (`tailor_resume_endpoint`, `cover_letter_endpoint`) to run synchronous LLM calls off the event loop. The `ApplyEngine` uses `asyncio.to_thread(self._apply_sync, ...)` for browser automation. When testing these endpoints with FastAPI's `TestClient`, the test hangs or raises `RuntimeError: no running event loop` because `TestClient` manages its own event loop and `to_thread` interacts poorly with it.

Additionally, `ApplyEngine._make_emitter()` captures `asyncio.get_running_loop()` and uses `loop.call_soon_threadsafe()` to bridge sync-to-async. In tests, the captured loop may not be the same loop the test is running on, causing events to be silently dropped.

**Why it happens:** FastAPI's `TestClient` (via Starlette) creates a new event loop internally. `asyncio.to_thread` needs a running loop. The combination works in production (uvicorn provides the loop) but in tests, the loop lifecycle is different. The `ApplyEngine` further complicates this by mixing `asyncio.Queue`, `threading.Event`, and `asyncio.Semaphore` across async and sync contexts.

**Consequences:**
- Tests hang indefinitely waiting for thread results
- Events emitted via `call_soon_threadsafe` disappear in test context
- Flaky test failures that depend on thread scheduling
- SSE streaming tests are impossible to write deterministically without careful queue management

**Prevention:**
1. For endpoint tests that call `asyncio.to_thread`, mock the synchronous function directly. Do NOT let the actual thread spawn in unit tests:
   ```python
   @patch("webapp.app.tailor_resume", return_value=mock_tailored_resume)
   async def test_tailor_endpoint(mock_tailor, client):
       ...
   ```
2. For `ApplyEngine` tests, test `_apply_sync` directly as a synchronous function (it's the actual logic). Test the async wrapper (`apply`) separately with a controlled event loop using `pytest-asyncio`.
3. For SSE streaming endpoints, use `httpx.AsyncClient` with `pytest-asyncio` instead of `TestClient`, and pre-populate the event queue in the fixture:
   ```python
   @pytest.mark.asyncio
   async def test_apply_stream():
       queue = asyncio.Queue()
       await queue.put({"type": "progress", "message": "test"})
       await queue.put({"type": "done", "message": "done"})
       # Then consume the SSE endpoint
   ```
4. Never test thread-to-event-loop bridging in unit tests. Accept that `_make_emitter` and `call_soon_threadsafe` need an integration test with a real event loop, and mark it accordingly.

**Detection (warning signs):**
- Tests hang with no output (deadlocked on thread/queue)
- `RuntimeError: This event loop is already running` in test output
- SSE tests randomly pass/fail depending on thread scheduling
- Tests that pass locally but timeout in CI (different CPU timing)

**Phase:** Phase 2 (integration tests). Unit tests should mock away the threading entirely.

**Confidence:** HIGH -- verified by reading `webapp/app.py` lines 264, 354, `apply_engine/engine.py` lines 82-86, 112-122.

---

### Pitfall 5: FTS5 Virtual Tables Break In-Memory Database Isolation

**What goes wrong:** The `JOBFLOW_TEST_DB=1` flag switches to an in-memory SQLite database, which is good for isolation. But the FTS5 triggers (migration version 4) create AFTER INSERT/UPDATE/DELETE triggers on the `jobs` table that sync data to the `jobs_fts` virtual table. If a test inserts data, the FTS triggers fire. If the test then calls `get_jobs(search="kubernetes")`, the FTS query runs against the virtual table. This works -- until you need to test FTS-specific behavior like prefix matching, boolean operators, or the rebuild command.

The real problem: if you reset the database between tests by simply deleting all rows (`DELETE FROM jobs`), the FTS triggers fire and try to update `jobs_fts`. If the FTS index is corrupted (which can happen from interrupted tests), subsequent FTS queries fail with `fts5: database disk image is malformed`. The in-memory database is gone, but the corruption happened during the test run.

**Why it happens:** FTS5 virtual tables maintain their own internal B-tree data structure. The `DELETE FROM jobs` cascades to the FTS triggers, but if the test process is interrupted (e.g., `KeyboardInterrupt`, test timeout, fixture teardown error), the FTS index can be left in an inconsistent state. In-memory databases don't have WAL journaling to recover from this.

**Consequences:**
- FTS5 corruption causes ALL subsequent tests in the session to fail with cryptic SQLite errors
- Tests that pass individually fail when run as a suite (FTS state leaks)
- Cannot reliably test the full-text search functionality

**Prevention:**
1. For each test function, create a fresh in-memory database connection rather than sharing one across the test session:
   ```python
   @pytest.fixture
   def test_db():
       import webapp.db as db
       db._memory_conn = None  # Force new connection
       db._USE_MEMORY = True
       db.init_db()
       yield db
       db._memory_conn.close()
       db._memory_conn = None
   ```
2. Never use `DELETE FROM jobs` for cleanup. Instead, drop the entire in-memory connection and reinitialize. This is faster and guarantees a clean FTS state.
3. For tests that specifically test FTS search behavior, use a dedicated fixture that inserts known data and verifies FTS queries against it. Do not mix FTS tests with other database tests.
4. Add a safety check in `conftest.py` teardown that verifies `jobs_fts` integrity:
   ```python
   conn.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('integrity-check')")
   ```

**Detection (warning signs):**
- `sqlite3.DatabaseError: database disk image is malformed` in test output
- FTS search tests return 0 results despite data being present in `jobs` table
- Tests that use `db.get_jobs(search=...)` fail intermittently

**Phase:** Phase 1 (database fixture design). FTS5 handling must be correct from the start.

**Confidence:** HIGH -- FTS5 corruption behavior verified via SQLite documentation. Trigger cascade verified by reading `webapp/db.py` lines 83-124.

---

## Moderate Pitfalls

Mistakes that cause flaky tests, slow CI, or testing gaps.

---

### Pitfall 6: Lazy Imports in Endpoint Handlers Evade Mock Patches

**What goes wrong:** Multiple FastAPI endpoints use lazy imports inside the function body. For example, `tailor_resume_endpoint` imports `resume_ai.tailor`, `resume_ai.diff`, `resume_ai.extractor`, etc. inside the `try` block (lines 242-247 of `webapp/app.py`). The `trigger_apply` endpoint imports `apply_engine.dedup` inside the function (line 476). When you write a test that patches `resume_ai.tailor.tailor_resume`, the patch doesn't take effect because the endpoint imports from the module path at call time, not at module load time.

The standard `@patch("webapp.app.tailor_resume")` pattern fails because `tailor_resume` is NOT a module-level attribute of `webapp.app` -- it's imported locally inside the endpoint function.

**Why it happens:** The lazy imports were deliberately chosen to avoid import errors when optional dependencies (Anthropic SDK, Playwright) aren't installed. This is good production practice but makes standard mock.patch patterns fail.

**Consequences:**
- Tests that patch LLM calls still make real API calls (costs money, requires API keys in CI)
- Tests that patch `is_already_applied` don't prevent the real DB check
- Patches applied at the wrong module path silently do nothing -- tests appear to pass but aren't actually testing the mock

**Prevention:**
1. Patch at the SOURCE module, not at the import site. For lazy imports inside functions, you must patch the module that the function imports from:
   ```python
   # WRONG -- webapp.app.tailor_resume doesn't exist at module level
   @patch("webapp.app.tailor_resume")

   # RIGHT -- patch where the function actually imports from
   @patch("resume_ai.tailor.tailor_resume")
   ```
2. For the Anthropic SDK calls, mock at the `anthropic.Anthropic` class level to prevent any real API calls:
   ```python
   @patch("anthropic.Anthropic")
   def test_tailor(mock_anthropic):
       mock_client = mock_anthropic.return_value
       mock_client.messages.parse.return_value = ...
   ```
3. Create reusable fixtures for common mock targets:
   ```python
   @pytest.fixture
   def mock_anthropic(monkeypatch):
       mock = MagicMock()
       monkeypatch.setattr("anthropic.Anthropic", lambda: mock)
       return mock
   ```
4. Verify mocks are actually being called with `mock.assert_called_once()`. Silent mock failures are the most dangerous test bug.

**Detection (warning signs):**
- Tests make real HTTP requests to Anthropic API (visible in network logs)
- Tests fail with `ANTHROPIC_API_KEY not set` -- the mock didn't intercept the call
- `mock.call_count == 0` despite the test supposedly exercising the mocked code path

**Phase:** Phase 2 (integration tests). Must understand this pattern before writing any endpoint tests.

**Confidence:** HIGH -- verified by reading all lazy import sites in `webapp/app.py` (lines 242-247, 334-337, 425, 445-446, 457, 469, 476, 518).

---

### Pitfall 7: Scoring and Dedup Tests Depend on Config State

**What goes wrong:** `JobScorer.__init__()` calls `get_settings()` to get the candidate profile and scoring weights (line 95-97 of `scorer.py`). `RemoteOKPlatform.search()` calls `get_settings()` for tech keywords (line 49). `FormFiller.__init__()` calls `get_settings()` for the candidate profile (line 50 of `form_filler.py`). Every pure-logic module that seems like it should be independently testable actually reaches back to the global settings singleton.

**Why it happens:** Dependency injection was partially implemented -- `JobScorer` accepts optional `profile` and `weights` parameters. But the fallback to `get_settings()` means tests that forget to pass explicit values silently use the global config, which may be the real `config.yaml` or a corrupted singleton from a previous test.

**Consequences:**
- Scorer tests produce different results depending on which `config.yaml` is loaded
- Tests pass locally (where `config.yaml` has 30 tech keywords) but fail in CI (where the test config has 5)
- Dedup tests are affected by scoring weights (scorer is called during orchestrator dedup phase)

**Prevention:**
1. Always pass explicit dependencies in tests. Never rely on `get_settings()` defaults:
   ```python
   def test_scorer():
       profile = CandidateProfile(
           target_titles=["Senior Engineer"],
           tech_keywords=["python", "kubernetes"],
           desired_salary_usd=200_000,
       )
       weights = ScoringWeights()
       scorer = JobScorer(profile=profile, weights=weights)
       # Now test scoring with known, deterministic config
   ```
2. For integration tests that must use `get_settings()`, the autouse fixture from Pitfall 2 ensures a clean test config is loaded.
3. Create factory fixtures for common test objects:
   ```python
   @pytest.fixture
   def make_job():
       def _make(title="Engineer", company="Acme", **kwargs):
           return Job(platform="indeed", title=title, company=company,
                      url="https://example.com", **kwargs)
       return _make
   ```
4. The `dedup.py` module is clean -- it takes `list[Job]` and returns `list[Job]` with no config dependency. Keep it that way. It's the ideal model for testable design.

**Detection (warning signs):**
- Scorer tests hardcode expected score values that don't match the scoring formula
- Tests pass only when run from the project root (where `config.yaml` lives)
- Adding a new tech keyword to `config.yaml` breaks scorer tests

**Phase:** Phase 1 (unit tests). Scorer and dedup are the easiest modules to test first, but only if config isolation is handled.

**Confidence:** HIGH -- verified by reading `scorer.py` lines 91-97, `form_filler.py` line 50, `platforms/remoteok.py` line 49.

---

### Pitfall 8: TestClient and SSE `EventSourceResponse` Incompatibility

**What goes wrong:** The `/jobs/{key}/apply/stream` endpoint returns an `EventSourceResponse` from `sse-starlette`. FastAPI's `TestClient` (backed by Starlette's `TestClient` which wraps `httpx`) can make the request, but reading the SSE stream is awkward: the response is a streaming response that requires iterating over chunks. The standard `response.json()` or `response.text` approach reads the entire response, blocking until the stream completes or times out.

The stream's completion depends on a `done` event being emitted by the background apply task, which is spawned via `asyncio.create_task()` in `trigger_apply`. In tests, the background task never runs because `TestClient` manages its own event loop synchronously.

**Why it happens:** SSE is inherently asynchronous and long-lived. TestClient is synchronous. The two models clash fundamentally. The `sse-starlette` library works correctly in production with uvicorn's async loop but in tests, the async task that feeds events into the queue never gets scheduled.

**Consequences:**
- SSE tests hang waiting for events that never come
- Tests succeed vacuously (request returns 200 but stream is empty)
- Background tasks spawned by `asyncio.create_task` in endpoints silently fail in test context

**Prevention:**
1. Do NOT test the full SSE flow in unit tests. Instead, test the components separately:
   - Test event generation (`ApplyEvent` models, `_emit_sync`)
   - Test queue consumption logic in isolation
   - Test the endpoint returns the correct content type and connects to SSE
2. For integration testing of the SSE stream, use `httpx.AsyncClient` with `pytest-asyncio` and ASGI transport:
   ```python
   @pytest.mark.asyncio
   async def test_sse_stream():
       async with httpx.AsyncClient(
           transport=httpx.ASGITransport(app=app), base_url="http://test"
       ) as client:
           # Pre-populate queue, then request stream
           ...
   ```
3. Test the `apply_stream` generator function directly by providing a pre-filled `asyncio.Queue` and a mock request with `is_disconnected()` returning `True` after N events.
4. Use `sse-starlette`'s built-in test helpers if available (check library docs).

**Detection (warning signs):**
- SSE test takes exactly the timeout duration to complete (it's waiting, not testing)
- `response.status_code == 200` but `response.text == ""`
- Test passes but the code path was never actually exercised

**Phase:** Phase 2 (integration tests) or Phase 3 (E2E). SSE testing is inherently complex.

**Confidence:** HIGH -- verified by reading `webapp/app.py` lines 515-546 and understanding TestClient/EventSourceResponse interaction model.

---

### Pitfall 9: Mocking Playwright for Platform Tests is Harder Than It Looks

**What goes wrong:** Someone writes tests for `IndeedPlatform.search()` by mocking `BrowserContext`, `Page`, `Locator`, `ElementHandle`, etc. The mock chain becomes 5+ levels deep: `mock_context.pages.__getitem__.return_value.query_selector_all.return_value.__getitem__.return_value.get_attribute.return_value = "data-jk-value"`. Each test is 50+ lines of mock setup for 5 lines of assertion. When the implementation changes (e.g., switches from `query_selector_all` to `locator().all()`), every test breaks even though the behavior is identical.

**Why it happens:** Playwright's API is deeply nested and imperative. Browser automation code is inherently coupled to the page interaction sequence. Mocking at the Playwright API level tests the mock, not the code.

**Consequences:**
- Platform test maintenance cost exceeds the value of the tests
- Tests pass with mocks but the real platform interactions fail (false confidence)
- Developers avoid changing platform code because it breaks too many tests

**Prevention:**
1. Do NOT mock Playwright objects. Instead, separate testable logic from browser interaction:
   - Extract data parsing into pure functions: `parse_job_card(html: str) -> Job`
   - Extract URL building into pure functions: `build_search_url(query, page) -> str`
   - Extract salary parsing (already done: `salary.py`) and dedup (already done: `dedup.py`)
   - Test these pure functions with simple inputs/outputs
2. For the actual browser interaction code, use Playwright's own test infrastructure with real (local) HTML fixtures:
   ```python
   # Serve a static HTML file that mimics Indeed's structure
   @pytest.fixture
   def mock_indeed_page(page):
       page.set_content(INDEED_RESULTS_HTML)
       return page
   ```
3. Use recorded HTTP responses (via `page.route()`) instead of mocking DOM queries:
   ```python
   await page.route("**/indeed.com/jobs*", lambda route: route.fulfill(
       body=Path("tests/fixtures/indeed_results.html").read_text(),
       content_type="text/html",
   ))
   ```
4. Accept that platform modules are "adapters" in the hexagonal architecture sense. Test the ports (pure logic), not the adapters (browser interaction). The adapters get tested by E2E tests, not unit tests.

**Detection (warning signs):**
- Test file is longer than the module it tests (mock setup > test logic)
- Changing a `query_selector` call to a `locator` call breaks 20 tests
- Every test starts with 30+ lines of mock configuration

**Phase:** Phase 1 (architecture decision). Decide the testing boundary before writing any platform tests.

**Confidence:** HIGH -- well-established testing pattern for adapter/port architecture. Verified against the platform code structure.

---

### Pitfall 10: Missing Test Config Files Cause Silent Failures

**What goes wrong:** `AppSettings` has `model_config = SettingsConfigDict(yaml_file="config.yaml", env_file=".env")`. In CI, neither file exists. `pydantic-settings` will look for `config.yaml` in the current working directory. If not found, the YAML source returns empty, and required fields (`search.queries`, `scoring.target_titles`) fail validation with a `ValidationError`. But this error only occurs when `get_settings()` is first called -- if no test calls it (e.g., all unit tests mock their dependencies), the tests pass. Then someone adds one integration test that triggers the settings load, and the entire CI pipeline breaks.

**Why it happens:** The `settings_customise_sources` override on `AppSettings` makes YAML loading explicit. If the YAML file is missing, pydantic-settings raises at construction time, not at field access time.

**Consequences:**
- CI pipeline works for months, then breaks when the first integration test is added
- The error message (`validation error for AppSettings: search -> queries: field required`) doesn't mention the missing YAML file
- Developers copy `config.yaml` into CI as a workaround, accidentally including production search queries

**Prevention:**
1. Create `tests/fixtures/test_config.yaml` with minimal valid data:
   ```yaml
   search:
     min_salary: 100000
     queries:
       - title: "test engineer"
         keywords: []
   scoring:
     target_titles: ["Test Engineer"]
     tech_keywords: ["python", "testing"]
   platforms:
     indeed: { enabled: false }
     dice: { enabled: false }
     remoteok: { enabled: false }
   ```
2. Create `tests/fixtures/test.env` with empty/dummy credentials:
   ```env
   INDEED_EMAIL=test@example.com
   DICE_EMAIL=test@example.com
   DICE_PASSWORD=test
   CANDIDATE_FIRST_NAME=Test
   CANDIDATE_LAST_NAME=User
   ```
3. In `conftest.py`, set the config path before any import of config:
   ```python
   os.environ["JOBFLOW_TEST_DB"] = "1"
   # Then in fixture:
   AppSettings.model_config["yaml_file"] = "tests/fixtures/test_config.yaml"
   ```
4. Add a CI smoke test that ONLY tests `get_settings()` initialization -- this catches config issues immediately rather than buried in unrelated test failures.

**Detection (warning signs):**
- `ValidationError` in CI that doesn't occur locally
- Tests pass when run from project root but fail from a different directory
- `.env` credentials appear in CI logs

**Phase:** Phase 1 (test infrastructure). This is part of the `conftest.py` foundation.

**Confidence:** HIGH -- verified by reading `config.py` lines 135-213 and the `settings_customise_sources` override.

---

## Minor Pitfalls

Mistakes that cause annoyance, slow tests, or minor gaps in coverage.

---

### Pitfall 11: Anthropic SDK Calls in Tests Cost Real Money

**What goes wrong:** A test for `tailor_resume` or `generate_cover_letter` runs without mocking the Anthropic client. The test makes a real API call to Claude, which costs ~$0.03-0.10 per call. At 50 test runs/day during development, this adds up. Worse, the API call takes 3-10 seconds, making the test suite slow. Even worse, if `ANTHROPIC_API_KEY` is in `.env` locally but not in CI, the test passes locally and fails in CI.

**Prevention:**
1. Always mock `anthropic.Anthropic` in tests. Create a fixture that provides a pre-built `TailoredResume` or `CoverLetter` response.
2. Add a `conftest.py` safety net that patches `anthropic.Anthropic.__init__` to raise if called without explicit opt-in:
   ```python
   @pytest.fixture(autouse=True)
   def block_real_api_calls(monkeypatch):
       def blocked(*args, **kwargs):
           raise RuntimeError("Real API call blocked in tests. Use mock_anthropic fixture.")
       monkeypatch.setattr("anthropic.Anthropic.__init__", blocked)
   ```
3. For the few integration tests that need real API calls, use a marker: `@pytest.mark.api` and skip in CI: `pytest -m "not api"`.

**Phase:** Phase 1 (conftest safety net). The API blocker should be autouse.

---

### Pitfall 12: `time.sleep()` in Mixin Methods Slows Tests

**What goes wrong:** `BrowserPlatformMixin.human_delay()` calls `time.sleep(random.uniform(2.0, 5.0))`. If platform tests exercise any code path that includes delays, each test takes 2-5 seconds just waiting. With 50 platform-related tests, the suite takes 4+ minutes on sleep alone.

**Prevention:**
1. Mock `time.sleep` in all platform tests:
   ```python
   @pytest.fixture(autouse=True)
   def no_sleep(monkeypatch):
       monkeypatch.setattr("time.sleep", lambda _: None)
   ```
2. Better: since platform tests shouldn't exercise browser code anyway (Pitfall 9), this is only relevant for integration tests that test the mixin methods directly.

**Phase:** Phase 1 (conftest fixture). Trivial to add, big impact on test speed.

---

### Pitfall 13: `datetime.now()` Makes Test Assertions Fragile

**What goes wrong:** Multiple modules use `datetime.now().isoformat()` for timestamps (`webapp/db.py` line 242, `orchestrator.py` line 56, etc.). Tests that assert on these values are inherently flaky because the timestamp changes between the action and the assertion. A test like `assert job["created_at"] == "2026-02-08T10:30:00"` will fail one second later.

**Prevention:**
1. Use `freezegun` or `time-machine` to freeze time in tests that need deterministic timestamps:
   ```python
   from freezegun import freeze_time

   @freeze_time("2026-02-08T10:00:00")
   def test_upsert_sets_timestamp():
       db.upsert_job({"title": "Test", ...})
       job = db.get_job("acme::test")
       assert job["created_at"].startswith("2026-02-08")
   ```
2. Alternatively, assert on timestamp format or ordering rather than exact values:
   ```python
   assert job["created_at"] is not None
   assert job["updated_at"] >= job["created_at"]
   ```
3. Add `freezegun` or `time-machine` to dev dependencies.

**Phase:** Phase 1 (dev dependencies). Add the library early.

---

### Pitfall 14: httpx Client in RemoteOK Tests Makes Real HTTP Calls

**What goes wrong:** `RemoteOKPlatform.search()` uses `self.client.get(self.API_URL)` where `self.client` is an `httpx.Client`. If tests instantiate `RemoteOKPlatform` and call `.init()` + `.search()` without mocking, they hit the real RemoteOK API. This makes tests slow (network latency), flaky (API may be down), and non-deterministic (API returns different jobs each time).

**Prevention:**
1. Use `respx` (the httpx equivalent of `responses`) to mock HTTP calls:
   ```python
   import respx

   @respx.mock
   def test_remoteok_search():
       respx.get("https://remoteok.com/api").respond(
           json=[{}, {"position": "Engineer", "company": "Test", ...}]
       )
       platform = RemoteOKPlatform()
       platform.init()
       jobs = platform.search(SearchQuery(query="python", platform="remoteok"))
       assert len(jobs) == 1
   ```
2. Store a sample API response in `tests/fixtures/remoteok_api_response.json` for consistent test data.
3. Add `respx` to dev dependencies.

**Phase:** Phase 1 (dev dependencies and fixtures).

---

### Pitfall 15: No Test for the Database Migration Chain

**What goes wrong:** The database has 6 migration versions with ALTER TABLE, CREATE TABLE, CREATE VIRTUAL TABLE, CREATE TRIGGER, and data backfill statements. Nobody tests that applying migrations 1-through-6 on an empty database produces the same schema as applying the full `SCHEMA` SQL. A migration bug (e.g., wrong column type, missing INDEX) goes undetected until it hits production data.

**Prevention:**
1. Write a migration test that:
   - Creates a fresh in-memory database
   - Applies ONLY the `SCHEMA` SQL (no migrations)
   - Creates another fresh in-memory database
   - Applies `SCHEMA` then runs `migrate_db()` from version 0 to 6
   - Compares the schemas (table definitions, indexes, triggers)
2. Write a test for each migration version that starts with version N-1 schema and applies version N migration.
3. Test idempotency: running `migrate_db()` twice should not raise errors (the existing code has `IF NOT EXISTS` and ignores "duplicate column" errors, but verify).

**Phase:** Phase 2 (integration tests). After basic database fixtures are working.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Test infrastructure (Phase 1) | `webapp.db` import-time `init_db()` | Set `JOBFLOW_TEST_DB=1` before any imports in conftest |
| Test infrastructure (Phase 1) | Config singleton poisons test state | `reset_settings()` autouse fixture + test config YAML |
| Test infrastructure (Phase 1) | Platform imports require Playwright | Layer tests: unit/integration/e2e with import guards |
| Test infrastructure (Phase 1) | Missing config files in CI | Ship `tests/fixtures/test_config.yaml` and `test.env` |
| Unit tests (Phase 1-2) | Scorer/dedup depend on global config | Always pass explicit dependencies, never rely on `get_settings()` |
| Unit tests (Phase 1-2) | Lazy imports defeat mock.patch | Patch at source module, not import site |
| Integration tests (Phase 2) | asyncio.to_thread hangs in tests | Mock the sync function, don't let real threads spawn |
| Integration tests (Phase 2) | SSE stream tests hang or timeout | Test components separately, use httpx.AsyncClient for SSE |
| Integration tests (Phase 2) | FTS5 corruption across tests | Fresh in-memory DB per test, never `DELETE FROM jobs` |
| Integration tests (Phase 2) | Real API calls cost money/fail in CI | Autouse fixture blocks `anthropic.Anthropic` and httpx |
| Platform tests (Phase 3) | Deep Playwright mock chains | Don't mock Playwright. Extract pure functions, test those |
| CI pipeline (Phase 3) | Playwright browser download slows CI | Skip browser tests in fast CI; separate E2E job with caching |
| All phases | `datetime.now()` makes assertions fragile | Use freezegun/time-machine or assert on format/ordering |

---

## Sources

### Verified (HIGH confidence)
- Direct codebase analysis of all 20+ Python modules in the JobFlow project
- [FastAPI Testing documentation](https://fastapi.tiangolo.com/tutorial/testing/) -- TestClient behavior
- [pytest fixtures documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html) -- fixture scoping and teardown
- [SQLite FTS5 Extension documentation](https://www.sqlite.org/fts5.html) -- integrity-check command, content sync triggers
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) -- test helpers and reset fixtures

### Cross-referenced (MEDIUM confidence)
- [Be careful of Import-time Side Effects in pytest](https://atsss.medium.com/be-careful-to-import-time-side-effects-in-pytest-7d9c074b0a6f) -- import-time side effects in test collection
- [Patching pydantic settings in pytest](https://rednafi.com/python/patch-pydantic-settings-in-pytest/) -- pydantic-settings singleton testing patterns
- [async test patterns for Pytest](https://tonybaloney.github.io/posts/async-test-patterns-for-pytest-and-unittest.html) -- asyncio.to_thread testing strategies
- [9 Playwright Best Practices and Pitfalls to Avoid](https://betterstack.com/community/guides/testing/playwright-best-practices/) -- test isolation in browser automation
- [Python 3.13 SQLite ResourceWarning](https://alexwlchan.net/til/2025/python3-13-sqlite-warnings/) -- unclosed connection warnings in tests
