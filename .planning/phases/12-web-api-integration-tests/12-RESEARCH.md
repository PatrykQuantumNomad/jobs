# Phase 12: Web & API Integration Tests - Research

**Researched:** 2026-02-08
**Domain:** FastAPI endpoint testing with TestClient, RemoteOK API response mocking with respx, platform registry verification
**Confidence:** HIGH

## Summary

This phase tests the web API layer (`webapp/app.py`) and the platform integration layer (`platforms/remoteok.py`, `platforms/registry.py`, `platforms/__init__.py`). The 12 requirements split into two domains: WEB-01 through WEB-08 test FastAPI endpoints via Starlette's `TestClient` (synchronous, no real server needed), and API-01 through API-04 test the RemoteOK response parser and platform registry using `respx` for HTTP mocking.

All infrastructure is already in place from Phase 9. The `tests/webapp/conftest.py` provides a `client` fixture wrapping `TestClient(app)`, and the `tests/platforms/conftest.py` provides a `mock_remoteok_api` fixture using `respx.mock`. The `_fresh_db` autouse fixture from `tests/conftest.py` ensures each test gets a clean in-memory SQLite database, and the `db_with_jobs` fixture seeds 10 realistic jobs across all three platforms. No new libraries or fixtures need to be created.

The web endpoint tests are integration tests because they exercise the full stack: HTTP request -> FastAPI route -> db.py function -> SQLite -> response. They should use `@pytest.mark.integration` at the class level (consistent with Phase 11). The platform tests (API-01 through API-04) are also integration tests because they exercise the full parsing pipeline including config loading and Pydantic model validation. The key challenge is that `RemoteOKPlatform.search()` calls `get_settings()` internally, so tests must ensure `test_config.yaml` is loaded before the platform is instantiated (the existing `_reset_settings` autouse fixture handles clearing, but the test must explicitly call `get_settings("tests/fixtures/test_config.yaml")` to load test config).

**Primary recommendation:** Create two test files: `tests/webapp/test_endpoints.py` for WEB-01 through WEB-08, and `tests/platforms/test_remoteok.py` for API-01 and API-02, plus `tests/platforms/test_registry.py` for API-03 and API-04. Use the existing `client` fixture for all web tests, seed the database with `db_with_jobs` or inline `db_module.upsert_job()` calls, and use `respx.mock` for RemoteOK HTTP mocking. All responses from webapp endpoints are either HTML (htmx partials or full pages), `StreamingResponse` (CSV/JSON exports), or `RedirectResponse` (import). Parse HTML with string assertions, parse CSV with `csv.reader`, and parse JSON with `json.loads`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0.0 | Test framework | Already installed, Phase 9 |
| FastAPI TestClient | (via starlette) | Synchronous HTTP testing | Built into FastAPI, no server needed |
| respx | 0.22.0 | Mock httpx requests | Already installed, Phase 9; purpose-built for httpx |
| factory-boy | >=3.3.0 | Test data factories | Already installed, Phase 9 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| csv (stdlib) | stdlib | Parse CSV export responses | WEB-04: validate CSV structure and field content |
| json (stdlib) | stdlib | Parse JSON export responses | WEB-05: validate JSON structure and field content |
| io.StringIO (stdlib) | stdlib | Read CSV from response text | WEB-04: feed response body into csv.reader |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| String assertions on HTML | BeautifulSoup for parsing | Overkill -- endpoints return simple HTML partials or full pages. String `in` checks and status code assertions are sufficient |
| `respx` for HTTP mocking | `unittest.mock.patch` on `httpx.Client.get` | respx is purpose-built for httpx, already in the project, and the fixture already exists in `tests/platforms/conftest.py` |
| Multiple test files | Single mega-file | Two domains (web + platform) are distinct enough to warrant separation. Keeps files under 300 lines each |

**Installation:** No new packages needed. All test infrastructure from Phase 9 is sufficient.

## Architecture Patterns

### Recommended Test File Structure

```
tests/
├── webapp/
│   ├── __init__.py           # Already exists
│   ├── conftest.py           # Already exists (client fixture)
│   ├── test_db.py            # Already exists (Phase 11)
│   └── test_endpoints.py     # NEW: WEB-01 through WEB-08
├── platforms/
│   ├── __init__.py           # Already exists
│   ├── conftest.py           # Already exists (mock_remoteok_api fixture)
│   ├── test_remoteok.py      # NEW: API-01 and API-02
│   └── test_registry.py      # NEW: API-03 and API-04
```

### Pattern 1: FastAPI TestClient with Seeded DB

**What:** Use the `client` fixture from `tests/webapp/conftest.py` (which wraps `TestClient(app)`) combined with either the `db_with_jobs` fixture for pre-seeded data or inline `db_module.upsert_job()` for specific test scenarios.

**When to use:** All WEB-* tests.

```python
import webapp.db as db_module

@pytest.mark.integration
class TestJobListEndpoint:
    def test_dashboard_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_dashboard_shows_jobs(self, client, db_with_jobs):
        response = client.get("/")
        assert response.status_code == 200
        # db_with_jobs seeds 10 jobs -- verify some appear in HTML
        assert "Principal Engineer" in response.text

    def test_filter_by_score(self, client, db_with_jobs):
        response = client.get("/?score=5")
        assert response.status_code == 200
        # All score-5 jobs should appear; score-3 should not
```

### Pattern 2: Form Submission via TestClient

**What:** FastAPI endpoints that accept `Form()` parameters require `data=` keyword (not `json=`) in TestClient POST requests. The `Content-Type` is automatically set to `application/x-www-form-urlencoded`.

**When to use:** WEB-03 (status update), WEB-06 (bulk status), WEB-07 (notes update).

```python
def test_status_update(self, client):
    db_module.upsert_job(_make_job_dict("Google", "SE"))
    key = _compute_dedup_key("Google", "SE")

    response = client.post(
        f"/jobs/{key}/status",
        data={"status": "applied"},
    )
    assert response.status_code == 200
    # Verify DB was updated
    job = db_module.get_job(key)
    assert job["status"] == "applied"
```

### Pattern 3: Bulk Action with Multi-Value Form Fields

**What:** The bulk status endpoint accepts `job_keys` as a list of form values. TestClient sends this as a list under the `data` key.

**When to use:** WEB-06.

```python
def test_bulk_status_update(self, client):
    for i in range(3):
        db_module.upsert_job(_make_job_dict(f"Co{i}", f"Eng{i}"))
    keys = [_compute_dedup_key(f"Co{i}", f"Eng{i}") for i in range(3)]

    response = client.post(
        "/bulk/status",
        data={
            "job_keys": keys,  # list of values
            "bulk_status": "saved",
        },
    )
    assert response.status_code == 200
    for key in keys:
        assert db_module.get_job(key)["status"] == "saved"
```

### Pattern 4: CSV Export Validation

**What:** Parse the CSV response with `csv.reader` and verify headers and row data match expected job fields.

**When to use:** WEB-04.

```python
import csv
import io

def test_csv_export(self, client, db_with_jobs):
    response = client.get("/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 10  # db_with_jobs seeds 10 jobs
    # Verify expected fields present
    assert "title" in reader.fieldnames
    assert "company" in reader.fieldnames
    assert "score" in reader.fieldnames
```

### Pattern 5: JSON Export Validation

**What:** Parse the JSON export response and verify it matches the expected data schema.

**When to use:** WEB-05.

```python
import json

def test_json_export(self, client, db_with_jobs):
    response = client.get("/export/json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = json.loads(response.text)
    assert isinstance(data, list)
    assert len(data) == 10
    # Verify schema
    for job in data:
        assert "title" in job
        assert "company" in job
        assert "score" in job
        assert "url" in job
```

### Pattern 6: RemoteOK Parsing with respx Mocking

**What:** Use the `mock_remoteok_api` fixture to provide a canned JSON response, then call `RemoteOKPlatform.search()` and verify the parsed `Job` objects have all expected fields.

**When to use:** API-01, API-02.

**Critical detail:** `RemoteOKPlatform.search()` calls `get_settings()` internally for `search.min_salary` and `scoring.tech_keywords`. Tests must load `test_config.yaml` before calling `search()`.

```python
from config import get_settings
from models import SearchQuery
from platforms.remoteok import RemoteOKPlatform

@pytest.mark.integration
class TestRemoteOKParsing:
    def test_parse_valid_response(self, mock_remoteok_api):
        get_settings("tests/fixtures/test_config.yaml")

        platform = RemoteOKPlatform()
        platform.init()

        query = SearchQuery(query="python kubernetes", platform="remoteok")
        jobs = platform.search(query)

        assert len(jobs) >= 1
        job = jobs[0]
        assert job.platform == "remoteok"
        assert job.title == "Senior Platform Engineer"
        assert job.company == "TestCorp"
        assert job.salary_min == 200000
```

### Pattern 7: Platform Registry Discovery

**What:** Import `platforms` (which triggers `_auto_discover()`) and verify the registry contains the expected platforms with correct metadata.

**When to use:** API-03, API-04.

**Critical detail:** `platforms/__init__.py` auto-discovers all platform modules at import time. The Indeed and Dice modules require `playwright` to be installed (they import from `playwright.sync_api`). Since Playwright IS installed in this project, the import succeeds. But the registry test should NOT instantiate browser platforms or call their `init()` method (which needs a real `BrowserContext`). Only test metadata and protocol compliance.

```python
from platforms.registry import get_all_platforms, get_platform, PlatformInfo
from platforms.protocols import APIPlatform, BrowserPlatform

@pytest.mark.integration
class TestPlatformRegistry:
    def test_all_platforms_registered(self):
        platforms = get_all_platforms()
        assert "indeed" in platforms
        assert "dice" in platforms
        assert "remoteok" in platforms

    def test_platform_protocol_compliance(self):
        platforms = get_all_platforms()
        for key, info in platforms.items():
            if info.platform_type == "browser":
                assert isinstance(info.cls(), BrowserPlatform)
            elif info.platform_type == "api":
                assert isinstance(info.cls(), APIPlatform)
```

### Pattern 8: Import Endpoint with Temporary Files

**What:** The `/import` endpoint reads JSON files from `job_pipeline/`. For testing, use `tmp_path` and monkeypatch to redirect the pipeline directory.

**When to use:** WEB-07.

**Critical detail:** The import endpoint uses `Path(__file__).parent.parent / "job_pipeline"` to locate files. For tests, monkeypatch the import function or write temporary JSON files to the expected location. Since tests run with in-memory DB, the import just calls `db.upsert_jobs()` which works with the test DB.

```python
def test_import_endpoint(self, client, tmp_path, monkeypatch):
    # Create a test discovered_jobs.json
    jobs_data = [_make_job_dict("TestCo", "Test Eng")]
    import json
    scored_path = tmp_path / "discovered_jobs.json"
    scored_path.write_text(json.dumps(jobs_data))

    # Monkeypatch the pipeline_dir in the import_jobs function
    import webapp.app as app_module
    monkeypatch.setattr(app_module, "import_jobs", ...)
    # OR: patch Path resolution inside the function
```

### Pattern 9: Search Endpoint (FTS5 through API)

**What:** The `/search` endpoint calls `db.get_jobs(search=...)` which uses FTS5. Test via TestClient to verify the HTTP layer correctly passes query parameters to the database layer.

**When to use:** WEB-08.

```python
def test_search_returns_matching_jobs(self, client):
    db_module.upsert_job(_make_job_dict(
        "Google", "Kubernetes Engineer",
        description="Expert in kubernetes and cloud infrastructure"
    ))
    db_module.upsert_job(_make_job_dict(
        "Microsoft", "Python Developer",
        description="Django web framework specialist"
    ))

    response = client.get("/search?q=kubernetes")
    assert response.status_code == 200
    assert "Kubernetes Engineer" in response.text
    assert "Python Developer" not in response.text
```

### Anti-Patterns to Avoid

- **Testing SSE/streaming endpoints with TestClient:** The apply engine SSE endpoints (`/jobs/{key}/apply/stream`) use `EventSourceResponse` which requires async iteration. `TestClient` does not support SSE streaming well. These endpoints should be excluded from this phase (they involve Playwright browser automation and are E2E territory).

- **Instantiating browser platforms in registry tests:** The Indeed and Dice platform classes need a `BrowserContext` for `init()`. Registry tests should only verify metadata and protocol compliance via `isinstance()`, not call `init()` or `search()`.

- **Importing `platforms` before setting `JOBFLOW_TEST_DB=1`:** The `platforms/__init__.py` imports `platforms.remoteok` which imports `config.py` which may import `webapp.db`. The autouse fixtures in `tests/conftest.py` handle this, but any test file that does `from platforms import ...` at module level must be in a file that is discovered AFTER `conftest.py` runs.

- **Forgetting that POST `/import` returns RedirectResponse (303):** TestClient by default follows redirects. Use `client.post("/import", follow_redirects=False)` to test the redirect status code, or `follow_redirects=True` (default) to test the final page.

- **Using `json=` for form-data endpoints:** FastAPI form parameters use `Content-Type: application/x-www-form-urlencoded`. TestClient requires `data=` (not `json=`) for these endpoints. Using `json=` will result in 422 Unprocessable Entity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request/response testing | Raw socket or requests library | `TestClient(app)` from `fastapi.testclient` | Synchronous, no server, full ASGI stack |
| HTTP mocking for RemoteOK | `unittest.mock.patch` on httpx internals | `respx.mock` context manager | Purpose-built for httpx, clean API, already in project |
| CSV parsing | Manual string splitting | `csv.DictReader(io.StringIO(response.text))` | Handles quoting, escaping, edge cases |
| Job dict construction | 10-field dict literals per test | `_make_job_dict()` helper (same as Phase 11) | DRY, ensures NOT NULL constraints |
| Dedup key computation | Inline normalization | `_compute_dedup_key()` helper (same as Phase 11) | Single source of truth |

**Key insight:** TestClient is synchronous despite FastAPI's async endpoints. The ASGI test transport handles async-to-sync bridging automatically. No need for `pytest-asyncio` or `@pytest.mark.asyncio` on any endpoint test.

## Common Pitfalls

### Pitfall 1: TestClient and RedirectResponse

**What goes wrong:** The `/import` endpoint returns `RedirectResponse(url="/...", status_code=303)`. By default, `TestClient` follows redirects, so the response appears to be a 200 (the dashboard page), not a 303.

**Why it happens:** Starlette TestClient defaults to `follow_redirects=True` in recent versions, though behavior varies by version. In httpx-backed TestClient (FastAPI 0.100+), redirects are followed by default.

**How to avoid:** For import tests, either test the final rendered page (200) and verify imported data appears, or use `client.post("/import", follow_redirects=False)` to check the 303 status code. Both approaches are valid.

**Warning signs:** Assertion `response.status_code == 303` fails because the response is 200 (the followed redirect).

### Pitfall 2: RemoteOK search() Requires Config

**What goes wrong:** `RemoteOKPlatform.search()` calls `get_settings()` which needs a valid config YAML. Without it, the test gets a Pydantic validation error because `search.queries` and `scoring.target_titles` are required fields.

**Why it happens:** The `_reset_settings` autouse fixture clears the settings singleton before each test, but does not load a replacement. The test must explicitly call `get_settings("tests/fixtures/test_config.yaml")`.

**How to avoid:** At the start of any test that uses RemoteOKPlatform, call `get_settings("tests/fixtures/test_config.yaml")`. The `test_config.yaml` has `min_salary: 100000` and tech keywords `["python", "kubernetes", "terraform"]`.

**Warning signs:** `ValidationError` from pydantic-settings when `RemoteOKPlatform.search()` is called.

### Pitfall 3: HTML Responses vs JSON Responses

**What goes wrong:** Most webapp endpoints return `HTMLResponse` (template-rendered HTML). Tests that expect JSON will fail. Only `/export/json` and `/api/analytics` return JSON.

**Why it happens:** The webapp is htmx-based -- it returns HTML partials for htmx swaps and full HTML pages for direct navigation. The export endpoints use `StreamingResponse` which wraps content in a generator.

**How to avoid:** For HTML endpoints, use `response.text` with string `in` assertions. For JSON endpoints, use `response.json()` or `json.loads(response.text)`. For CSV exports, use `csv.DictReader(io.StringIO(response.text))`.

**Warning signs:** `json.JSONDecodeError` when trying to parse an HTML response as JSON.

### Pitfall 4: Bulk Status Form Data Structure

**What goes wrong:** The `bulk_status_update` endpoint expects `job_keys` as a list of form values. Sending a single string or a JSON array does not work -- it must be form-encoded as multiple values with the same key name.

**Why it happens:** FastAPI's `Form()` annotation for `list[str]` expects multiple form fields with the same name (standard HTML form behavior for checkboxes with the same name attribute).

**How to avoid:** In TestClient, pass `data={"job_keys": ["key1", "key2"], "bulk_status": "saved"}`. The TestClient correctly encodes this as `job_keys=key1&job_keys=key2&bulk_status=saved`.

**Warning signs:** `job_keys` is None or empty in the endpoint handler, causing no updates despite sending data.

### Pitfall 5: Platform Registry Auto-Discovery Side Effects

**What goes wrong:** Importing `platforms` triggers `_auto_discover()` which imports all platform modules. This executes `@register_platform` decorators that validate protocol compliance. If a platform module has a bug (missing method), the import itself raises `TypeError`.

**Why it happens:** `_auto_discover()` runs at import time on line 36 of `platforms/__init__.py`. This is by design -- fail-fast validation.

**How to avoid:** Registry tests can simply import `platforms.registry` (which does NOT trigger auto-discovery) or import `platforms` (which does). For API-03, importing `platforms` is the correct approach since it tests discovery. If the import fails, the test failure message will indicate which platform module has a protocol violation.

**Warning signs:** `TypeError: IndeedPlatform is missing required protocol members` on import.

### Pitfall 6: Import Endpoint Pipeline Directory

**What goes wrong:** The `/import` endpoint reads from `Path(__file__).parent.parent / "job_pipeline"` which resolves to the actual project root during tests. If `job_pipeline/` does not exist or is empty, the import returns 0 jobs and redirects.

**Why it happens:** The path is hardcoded relative to `webapp/app.py`. In-memory database tests still look for files on disk.

**How to avoid:** For WEB-07, use `tmp_path` + monkeypatch to create temporary JSON files and redirect the pipeline directory path in the import function. Alternatively, test the import endpoint with the actual (empty) directory and verify it handles the "no files" case gracefully (count=0), plus test with a temporary file written to `job_pipeline/`.

**Warning signs:** Test passes only on machines that happen to have `job_pipeline/discovered_jobs.json` on disk, flaky in CI.

### Pitfall 7: Job Detail Endpoint Path Encoding

**What goes wrong:** The dedup key contains `::` (e.g., `google::staff engineer`). FastAPI's path parameter `{dedup_key:path}` handles this, but some characters in dedup keys might need URL encoding in test URLs.

**Why it happens:** The `:path` converter in FastAPI matches everything after the prefix including slashes. The `::` in dedup keys is fine for path parameters, but the space in the title portion may cause issues.

**How to avoid:** Use the dedup key as-is in `client.get(f"/jobs/{key}")`. TestClient handles URL encoding internally. Verify with a job whose dedup key contains spaces.

**Warning signs:** 404 responses when the dedup key contains spaces or special characters.

## Code Examples

Verified patterns from the actual codebase:

### All Web Endpoints to Test (from webapp/app.py)

```python
# Endpoint inventory for WEB-01 through WEB-08:
#
# GET  /                       -> HTMLResponse (dashboard with filters)     WEB-01
# GET  /search                 -> HTMLResponse (htmx partial: job rows)     WEB-08
# GET  /jobs/{dedup_key:path}  -> HTMLResponse (job detail page)            WEB-02
# POST /jobs/{key}/status      -> HTMLResponse (status badge)               WEB-03
# POST /jobs/{key}/notes       -> HTMLResponse (confirmation text)          WEB-03
# POST /bulk/status            -> HTMLResponse (updated job rows)           WEB-06
# GET  /export/csv             -> StreamingResponse (CSV file download)     WEB-04
# GET  /export/json            -> StreamingResponse (JSON file download)    WEB-05
# POST /import                 -> RedirectResponse (303 to dashboard)       WEB-07
#
# NOT in scope for this phase:
# POST /jobs/{key}/tailor-resume    -> requires LLM (resume_ai)
# POST /jobs/{key}/cover-letter     -> requires LLM (resume_ai)
# POST /jobs/{key}/apply            -> requires Playwright (apply_engine)
# GET  /jobs/{key}/apply/stream     -> SSE (requires async iteration)
# GET  /runs                        -> HTMLResponse (run history page)
# GET  /analytics                   -> HTMLResponse (analytics page)
# GET  /api/analytics               -> JSONResponse (analytics data)
# GET  /kanban                      -> HTMLResponse (kanban board)
```

### CSV Export Field List (from webapp/app.py line 163-174)

```python
# The export_csv endpoint writes these 10 fields in this exact order:
CSV_FIELDS = [
    "title", "company", "location", "salary_display",
    "platform", "status", "score", "url",
    "posted_date", "created_at",
]
```

### JSON Export Field List (from webapp/app.py line 205-218)

```python
# The export_json endpoint exports these 11 fields:
JSON_FIELDS = [
    "title", "company", "location", "salary_display",
    "platform", "status", "score", "url",
    "apply_url", "posted_date", "created_at", "notes",
]
```

### RemoteOK _parse() Method Field Mapping (from platforms/remoteok.py)

```python
# API response field -> Job model field mapping:
# entry["id"]          -> Job.id (str)
# entry["position"]    -> Job.title
# entry["company"]     -> Job.company
# entry["location"]    -> Job.location (defaults to "Remote")
# entry["url"]         -> Job.url (prefixed with https://remoteok.com if relative)
# entry["apply_url"]   -> Job.apply_url
# entry["description"] -> Job.description
# entry["epoch"]       -> Job.posted_date (converted to ISO datetime via UTC)
# entry["tags"]        -> Job.tags
# entry["salary_min"]  -> Job.salary_min (None if 0 or missing)
# entry["salary_max"]  -> Job.salary_max (None if 0 or missing)
#
# Returns None if position, company, or url is empty/missing.
```

### Platform Registry Contents (from codebase analysis)

```python
# After _auto_discover(), the registry contains:
# Key: "indeed"   | name: "Indeed"   | type: "browser" | caps: ["easy_apply"]
# Key: "dice"     | name: "Dice"     | type: "browser" | caps: ["easy_apply"]
# Key: "remoteok" | name: "RemoteOK" | type: "api"     | caps: []
#
# Registry functions:
# get_platform(key)           -> PlatformInfo (raises KeyError if missing)
# get_all_platforms()          -> dict[str, PlatformInfo]
# get_platforms_by_type(type)  -> filtered dict
```

### Requirement-to-Endpoint Mapping

```
WEB-01 (Job list + filters):    GET /            (query params: q, score, platform, status, sort, dir)
WEB-02 (Job detail):            GET /jobs/{key}  (full detail page with description + activity log)
WEB-03 (Status update):         POST /jobs/{key}/status (Form: status)
                                POST /jobs/{key}/notes  (Form: notes)
WEB-04 (CSV export):            GET /export/csv  (same filter params as dashboard)
WEB-05 (JSON export):           GET /export/json (same filter params as dashboard)
WEB-06 (Bulk action):           POST /bulk/status (Form: job_keys[], bulk_status, + filter params)
WEB-07 (Job import):            POST /import     (reads from job_pipeline/ directory)
WEB-08 (Search/FTS5 via API):   GET /search      (htmx partial, same params as dashboard)

API-01 (RemoteOK parsing):      RemoteOKPlatform._parse() and .search() with mocked HTTP
API-02 (RemoteOK errors):       RemoteOKPlatform.search() with error/empty/malformed responses
API-03 (Registry discovery):    platforms._auto_discover() + get_all_platforms()
API-04 (Protocol compliance):   isinstance() checks against BrowserPlatform/APIPlatform protocols
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests.Session for API testing | TestClient from Starlette/FastAPI | FastAPI 0.60+ | No server needed, synchronous, full ASGI stack |
| `unittest.mock.patch` for httpx | `respx` library | respx 0.17+ | Cleaner API, httpx-native, captures request details |
| `isinstance()` for protocol checks | `runtime_checkable` Protocol + `isinstance()` | Python 3.8+ | Verified at import time by registry, testable at runtime |

**Deprecated/outdated:**
- None relevant. FastAPI TestClient API is stable. respx 0.22 API is stable.

## Open Questions

1. **Import Endpoint File I/O Isolation**
   - What we know: `/import` reads from the filesystem (`job_pipeline/` directory). Tests need to either write temporary files to a predictable location or monkeypatch the path.
   - What's unclear: Whether to monkeypatch `Path(__file__).parent.parent` in `import_jobs()` or to create a temporary `job_pipeline/` directory.
   - Recommendation: The simplest approach is to monkeypatch the `pipeline_dir` local variable inside `import_jobs()`. Since `import_jobs` is an `async def`, monkeypatching works on the module-level variable used to construct the path. Alternatively, write the temporary file to the actual `job_pipeline/` location (which exists in the project) and clean up after the test. The monkeypatch approach is cleaner and avoids disk side effects.

2. **SSE Endpoint Testing Scope**
   - What we know: STATE.md flags "SSE endpoint testing: TestClient + EventSourceResponse interaction needs careful design" as a concern.
   - What's unclear: Whether WEB endpoints include the SSE apply stream endpoints.
   - Recommendation: The apply/stream SSE endpoints are NOT in the WEB-01 through WEB-08 requirements. They involve the apply engine which requires Playwright. Exclude them from this phase entirely.

3. **`HX-Trigger` Header on Status Update**
   - What we know: The `POST /jobs/{key}/status` endpoint sets `response.headers["HX-Trigger"] = "statsChanged"` (line 594). This is an htmx-specific header for client-side event triggering.
   - What's unclear: Whether to test the header presence or just the response body.
   - Recommendation: Test both. The header is a functional part of the API that htmx clients depend on. Assert `"HX-Trigger" in response.headers` and `response.headers["HX-Trigger"] == "statsChanged"`.

4. **Dashboard vs Search Endpoint Overlap**
   - What we know: `GET /` returns a full HTML page (dashboard.html), while `GET /search` returns an HTML partial (partials/job_rows.html). Both call `db.get_jobs()` with the same filter parameters.
   - What's unclear: Whether WEB-01 tests the full dashboard or the search partial.
   - Recommendation: WEB-01 tests the full dashboard (`GET /`). WEB-08 tests the search partial (`GET /search`). Both should verify filtering works, but from different endpoints. The dashboard test verifies the full page structure, while the search test verifies the partial returns the correct rows.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `webapp/app.py` (full file -- all 24 endpoints, filter logic, export formats, import logic)
- Codebase analysis: `webapp/db.py` (full file -- all DB functions called by endpoints)
- Codebase analysis: `platforms/remoteok.py` (full file -- search(), _parse(), _matches(), _filter_terms())
- Codebase analysis: `platforms/registry.py` (full file -- register_platform(), get_all_platforms(), _validate_against_protocol())
- Codebase analysis: `platforms/protocols.py` (full file -- BrowserPlatform, APIPlatform protocol definitions)
- Codebase analysis: `platforms/__init__.py` (full file -- _auto_discover() auto-import logic)
- Codebase analysis: `platforms/indeed.py` (full file -- IndeedPlatform with @register_platform decorator)
- Codebase analysis: `platforms/dice.py` (full file -- DicePlatform with @register_platform decorator)
- Codebase analysis: `tests/conftest.py` (full file -- _fresh_db, _reset_settings, db_with_jobs fixtures)
- Codebase analysis: `tests/webapp/conftest.py` (full file -- client fixture)
- Codebase analysis: `tests/platforms/conftest.py` (full file -- mock_remoteok_api fixture)
- Codebase analysis: `tests/webapp/test_db.py` (full file -- Phase 11 patterns for DB integration tests)
- Codebase analysis: `tests/conftest_factories.py` (full file -- JobFactory)
- Codebase analysis: `tests/fixtures/test_config.yaml` (full file -- test configuration)
- Codebase analysis: `pyproject.toml` (full file -- pytest config, markers, coverage settings)
- Package versions verified: FastAPI 0.128.4, Starlette 0.52.1, httpx 0.28.1, respx 0.22.0

### Secondary (MEDIUM confidence)
- FastAPI TestClient documentation (based on Starlette TestClient, backed by httpx)
- respx documentation (0.22.x API for httpx mocking)

### Tertiary (LOW confidence)
- None -- all findings from direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries; all test infrastructure from Phase 9, verified installed versions
- Architecture: HIGH -- Test file structure, patterns, and helpers derived from existing Phase 11 test_db.py and codebase analysis of every endpoint and function under test
- Pitfalls: HIGH -- Every pitfall identified from reading actual source code (form data encoding, redirect following, config loading, path resolution, protocol compliance, registry auto-discovery)

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- stable domain, endpoints and platform code unlikely to change before tests are written)
