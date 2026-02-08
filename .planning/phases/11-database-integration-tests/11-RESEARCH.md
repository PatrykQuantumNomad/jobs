# Phase 11: Database Integration Tests - Research

**Researched:** 2026-02-08
**Domain:** SQLite integration testing -- CRUD lifecycle, FTS5 search, activity log, bulk operations, schema initialization
**Confidence:** HIGH

## Summary

This phase writes integration tests for the `webapp/db.py` module, covering all database operations against the in-memory SQLite instance established in Phase 9. The module under test is 724 lines containing 18 public functions, a 6-version migration system with FTS5 virtual tables and triggers, and an activity log subsystem. All infrastructure needed for testing is already in place: the `_fresh_db` autouse fixture provides a clean in-memory database per test with full schema + migrations applied, and the `JobFactory` produces valid Pydantic `Job` instances that can be serialized to dicts via `model_dump(mode="json")` for `upsert_job()`.

The five requirements (DB-01 through DB-05) map directly to five testable domains within `webapp/db.py`: (1) CRUD lifecycle across all 11 `JobStatus` states, (2) FTS5 full-text search via `get_jobs(search=...)`, (3) activity log recording via `log_activity()` / `get_activity_log()` / `update_job_status()`, (4) bulk status updates via sequential `update_job_status()` calls (there is no dedicated bulk function in db.py -- the webapp's `bulk_status_update` endpoint loops over individual `update_job_status()` calls), and (5) schema initialization via `init_db()` + `migrate_db()`.

The key insight is that Phase 10's `test_delta.py` already established the pattern for testing `webapp/db.py` -- direct function calls with helper functions for job dict construction and dedup key computation. Phase 11 extends this to comprehensive CRUD and query testing. No new libraries or fixtures are needed; all tests use the existing `_fresh_db` autouse fixture and `JobFactory`.

**Primary recommendation:** Write a single test file `tests/webapp/test_db.py` covering all five requirements. Use `@pytest.mark.integration` at the class level. Reuse the `_make_job_dict()` and `_compute_dedup_key()` helper pattern from `test_delta.py`. Test FTS5 search with realistic multi-word descriptions to exercise the prefix-matching logic in `get_jobs()`. Verify activity log entries are created automatically by `upsert_job()` (on first insert) and `update_job_status()` (on every call). Test schema initialization by verifying table existence via `sqlite_master` queries after `init_db()`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test framework | Already installed, Phase 9 |
| factory-boy | 3.3.3 | Job factories for test data | Already installed, Phase 9 |
| Faker | 40.4.0 | Realistic random data | Already installed, Phase 9 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | Direct DB inspection | Verify schema tables/indexes via `sqlite_master` queries |
| pytest-cov | 7.0.0 | Coverage reporting | Verify webapp/db.py coverage improvement |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct `db_module.upsert_job()` calls | Using `JobFactory` + `model_dump()` for every insert | Factory is overkill when testing specific DB behaviors -- simple dict construction is more readable for integration tests |
| Single test file | Multiple files per requirement | Single file is better here -- all 5 requirements test the same module, share the same helpers, and logically group together |

**Installation:** No new packages needed. All test infrastructure from Phase 9 is sufficient.

## Architecture Patterns

### Recommended Test File Structure

```
tests/
├── webapp/
│   ├── __init__.py           # Already exists
│   ├── conftest.py           # Already exists (TestClient fixture)
│   └── test_db.py            # NEW: DB-01 through DB-05
```

### Pattern 1: Job Dict Helper (Reuse from test_delta.py)

**What:** A `_make_job_dict()` helper that builds minimal valid job dicts for `upsert_job()`. The exact same pattern used in `test_delta.py`.

**When to use:** Every test that inserts jobs. Avoids repeating 8+ required fields.

```python
def _make_job_dict(
    company: str,
    title: str,
    platform: str = "indeed",
    **kwargs,
) -> dict:
    """Build a minimal job dict suitable for upsert_job()."""
    defaults = {
        "id": f"{company.lower().replace(' ', '-')}-{title.lower().replace(' ', '-')}",
        "platform": platform,
        "title": title,
        "company": company,
        "url": f"https://example.com/{company.lower().replace(' ', '-')}",
        "location": "Remote",
        "description": f"{title} role at {company}",
        "status": "discovered",
    }
    defaults.update(kwargs)
    return defaults
```

### Pattern 2: Dedup Key Computation Helper

**What:** Replicate the dedup_key logic from `upsert_job()` to compute expected keys for assertions.

```python
def _compute_dedup_key(company: str, title: str) -> str:
    """Replicate the dedup_key logic from webapp/db.py upsert_job."""
    c = (
        company.lower().strip()
        .replace(" inc.", "").replace(" inc", "")
        .replace(" llc", "").replace(" ltd", "")
        .replace(",", "")
    )
    t = title.lower().strip()
    return f"{c}::{t}"
```

### Pattern 3: Status Lifecycle Parametrization

**What:** Test that a job can transition through all 11 `JobStatus` states using parametrized test.

**When to use:** DB-01 -- verifying that `update_job_status()` persists each status value.

```python
@pytest.mark.parametrize("status", [
    "discovered", "scored", "saved", "applied",
    "phone_screen", "technical", "final_interview",
    "offer", "rejected", "withdrawn", "ghosted",
], ids=lambda s: s)
def test_status_transition(self, status):
    db_module.upsert_job(_make_job_dict("ACME", "Engineer"))
    key = _compute_dedup_key("ACME", "Engineer")
    db_module.update_job_status(key, status)
    job = db_module.get_job(key)
    assert job["status"] == status
```

### Pattern 4: FTS5 Search Testing

**What:** Insert jobs with known text content, then search using `get_jobs(search=...)` and verify the correct jobs are returned.

**When to use:** DB-02 -- testing FTS5 full-text search behavior.

**Critical detail:** The `get_jobs()` function adds prefix matching (`word*`) for non-operator queries. This means searching "kube" will match "kubernetes". Special FTS5 operators (`"`, `*`, `AND`, `OR`, `NOT`) are passed through without prefix-wrapping.

```python
def test_fts_partial_match(self):
    db_module.upsert_job(_make_job_dict("Google", "Staff Engineer",
        description="Expert in kubernetes and terraform"))
    db_module.upsert_job(_make_job_dict("Microsoft", "PM",
        description="Product management role"))
    results = db_module.get_jobs(search="kube")
    assert len(results) == 1
    assert results[0]["company"] == "Google"
```

### Pattern 5: Activity Log Verification

**What:** Perform status changes and verify that `get_activity_log()` returns the expected event entries with correct old/new values.

**When to use:** DB-03 -- verifying automatic activity log creation.

```python
def test_status_change_logged(self):
    db_module.upsert_job(_make_job_dict("ACME", "Engineer"))
    key = _compute_dedup_key("ACME", "Engineer")
    db_module.update_job_status(key, "applied")
    log = db_module.get_activity_log(key)
    status_changes = [e for e in log if e["event_type"] == "status_change"]
    assert len(status_changes) == 1
    assert status_changes[0]["old_value"] == "discovered"
    assert status_changes[0]["new_value"] == "applied"
```

### Pattern 6: Schema Verification via sqlite_master

**What:** After `init_db()`, query `sqlite_master` to verify all expected tables, indexes, and triggers exist.

**When to use:** DB-05 -- verifying database initialization creates the full schema.

```python
def test_all_tables_created(self):
    conn = db_module.get_conn()
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "jobs" in tables
    assert "activity_log" in tables
    assert "run_history" in tables
    assert "resume_versions" in tables
    assert "jobs_fts" in tables
```

### Anti-Patterns to Avoid

- **Testing `upsert_job()` with dicts missing required fields:** The SQL INSERT has NOT NULL constraints on `id`, `platform`, `title`, `company`, `url`. Omitting any of these will cause `sqlite3.IntegrityError`, not a Pydantic error (db.py takes raw dicts, not models). Always use `_make_job_dict()` to ensure all required fields are present.

- **Relying on insertion order for FTS5 results:** FTS5 results are not ordered by insertion time by default. `get_jobs()` orders by the `sort_by` parameter (default `score DESC`). Always set scores on test jobs or specify `sort_by` explicitly to get deterministic ordering.

- **Testing FTS5 with single-character queries:** SQLite FTS5 has a minimum token length. Single-character prefix queries like `search="k"` may not work reliably. Use at least 3-character search terms.

- **Forgetting that `upsert_job()` auto-creates a "discovered" activity log entry on NEW inserts:** The first call to `upsert_job()` logs a "discovered" event. Tests checking activity log entries must account for this baseline event.

- **Assuming `update_job_status("applied")` only updates status:** When status is "applied", the function also sets `applied_date` to the current timestamp. Tests for the "applied" status should verify both fields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job dict construction | Manual dict with 8+ fields per test | `_make_job_dict()` helper | DRY, readable, ensures all NOT NULL fields present |
| Dedup key computation | Copying the normalization logic inline | `_compute_dedup_key()` helper | Single source of truth for expected keys |
| Schema existence checks | Manual SQL per table | Loop over expected table names with `sqlite_master` query | Extensible, catches missing tables in one test |
| Test data with realistic descriptions | Short "test" strings | Faker or multi-sentence descriptions | FTS5 behaves differently with real tokenizable text vs single words |

**Key insight:** The `webapp/db.py` module takes raw dicts (not Pydantic models) for all write operations. This means tests can construct simple dicts without going through `JobFactory` and `model_dump()`. The `_make_job_dict()` helper is sufficient and more readable than factory-generated data for targeted integration tests. Use `JobFactory` only when you need a batch of realistic jobs (e.g., `db_with_jobs` fixture).

## Common Pitfalls

### Pitfall 1: FTS5 Trigger Sync on Upsert vs Insert

**What goes wrong:** FTS5 is synced via triggers on INSERT, DELETE, and UPDATE. The `upsert_job()` function uses `INSERT ... ON CONFLICT DO UPDATE`, which fires the INSERT trigger on first insert but the UPDATE trigger on subsequent upserts. If FTS triggers are misconfigured, re-upserted jobs may have stale or duplicate FTS entries.

**Why it happens:** `INSERT ... ON CONFLICT DO UPDATE` in SQLite fires the INSERT trigger for new rows and the UPDATE trigger for conflict resolution (when the ON CONFLICT clause activates). The FTS5 UPDATE trigger in `webapp/db.py` correctly handles this: it deletes the old FTS entry and inserts the new one.

**How to avoid:** Test FTS5 search both after initial insert and after re-upsert with changed description. Verify that the search finds the updated text, not the old text.

**Warning signs:** FTS5 search returns duplicate results or stale text after re-upserting a job with a different description.

### Pitfall 2: Activity Log "discovered" Event on Upsert

**What goes wrong:** `upsert_job()` checks `is_new = get_job(dedup_key) is None` before inserting, then logs a "discovered" event only if the job was new. Tests that re-upsert the same job should NOT see a second "discovered" event. But tests that assert activity log length must account for the first "discovered" event.

**Why it happens:** The `is_new` check on line 243 runs before the INSERT/UPDATE. For new jobs, `get_job()` returns None, so `is_new = True`. For re-upserts, the job already exists, so `is_new = False`.

**How to avoid:** In tests that verify `update_job_status()` activity logging, always account for the initial "discovered" event from `upsert_job()`. The total activity log for a job that was inserted and then had its status changed once will have 2 entries: "discovered" + "status_change".

**Warning signs:** Tests expecting exactly 1 activity log entry fail because there are 2 (discovered + the tested event).

### Pitfall 3: FTS5 Special Characters Causing SQL Errors

**What goes wrong:** FTS5 `MATCH` queries with special characters can cause SQLite `OperationalError`. Characters like `*`, `"`, and `:` have special meaning in FTS5 query syntax. Unbalanced quotes, lone `*`, or `:` can crash the query.

**Why it happens:** The `get_jobs()` function does minimal sanitization: it adds prefix `*` to each word when no FTS5 operators are detected. But if the user's search term contains characters like unbalanced `"` or standalone `:`, the resulting FTS5 query may be malformed.

**How to avoid:** Test with various special character inputs: single `"`, `*`, `:`, `(`, `)`, `+`, `-`, `@`, `#`, `$`. Verify that either the search returns results gracefully or the error is handled (currently `get_jobs()` does NOT catch `OperationalError` from FTS5 -- this is a potential bug to document).

**Warning signs:** `sqlite3.OperationalError: fts5: syntax error near` on searches with special characters.

### Pitfall 4: get_jobs() Sort Order with NULL Scores

**What goes wrong:** `get_jobs(sort_by="score", sort_dir="desc")` uses `NULLS LAST`. Jobs with `score=None` appear last, regardless of sort direction. Tests that insert jobs without scores and then check ordering must account for this.

**Why it happens:** The SQL query on line 447 explicitly includes `NULLS LAST` in the ORDER BY clause.

**How to avoid:** Either assign scores to all test jobs, or explicitly test the NULL-last behavior as its own test case.

**Warning signs:** Tests checking result ordering fail because unscored jobs unexpectedly appear at the end.

### Pitfall 5: Bulk Status Update Is Not Atomic

**What goes wrong:** The webapp's bulk_status_update endpoint (and db.py) loops through `update_job_status()` for each job individually. If one call fails midway, earlier jobs have already been updated. Tests must verify that each call succeeds independently, not assume transactional atomicity.

**Why it happens:** `update_job_status()` is called in a loop (line 128-129 of `webapp/app.py`). There is no wrapping transaction across the batch.

**How to avoid:** Test bulk updates by calling `update_job_status()` in a loop (mimicking the webapp behavior), then verify each job's status individually. Do NOT test via the webapp endpoint in this phase -- that belongs to Phase 12 (WEB-06).

**Warning signs:** Tests assuming bulk atomicity fail when one job key is invalid (the valid jobs get updated but the invalid one raises or is skipped).

### Pitfall 6: Migration Idempotency

**What goes wrong:** Running `migrate_db()` twice should be safe (idempotent). The migration code catches `"duplicate column name"` and `"already exists"` errors. But if a migration SQL statement fails with a different error message, it will raise.

**Why it happens:** Lines 186-189 of `webapp/db.py` catch `sqlite3.OperationalError` and skip only if the message contains specific substrings. Novel errors pass through.

**How to avoid:** Test that `init_db()` can be called twice without error. Also test that calling `migrate_db()` on an already-migrated database produces no changes.

**Warning signs:** `sqlite3.OperationalError` on second `init_db()` call.

## Code Examples

Verified patterns from the actual codebase:

### All Public Functions in webapp/db.py (Complete API Surface)

```python
# Connection & Schema
def get_conn() -> sqlite3.Connection: ...
def migrate_db(conn: sqlite3.Connection) -> None: ...
def init_db() -> None: ...

# Write Operations
def upsert_job(job: dict) -> None: ...          # Insert or update, logs "discovered" for new
def upsert_jobs(jobs: list[dict]) -> int: ...    # Bulk upsert, returns count
def update_job_status(dedup_key: str, status: str) -> None: ...   # Logs "status_change"
def update_job_notes(dedup_key: str, notes: str) -> None: ...     # Logs "note_added"
def mark_viewed(dedup_key: str) -> None: ...     # Sets viewed_at if null

# Read Operations
def get_job(dedup_key: str) -> dict | None: ...
def get_jobs(search, score_min, platform, status, sort_by, sort_dir) -> list[dict]: ...
def get_stats() -> dict: ...
def get_enhanced_stats() -> dict: ...

# Activity Log
def log_activity(dedup_key, event_type, old_value, new_value, detail) -> None: ...
def get_activity_log(dedup_key: str) -> list[dict]: ...

# Delta Tracking
def remove_stale_jobs(searched_platforms, run_timestamp) -> int: ...
def mark_viewed(dedup_key: str) -> None: ...
def backfill_score_breakdowns(scorer_fn) -> int: ...

# Run History
def record_run(...) -> None: ...
def get_run_history(limit: int = 50) -> list[dict]: ...
```

### DB-01: CRUD Lifecycle State Transitions

```python
# All 11 JobStatus values that a job can have:
ALL_STATUSES = [
    "discovered", "scored", "saved", "applied",
    "phone_screen", "technical", "final_interview",
    "offer", "rejected", "withdrawn", "ghosted",
]

# A full lifecycle test:
# 1. upsert_job() -> status="discovered" (default)
# 2. update_job_status() -> iterate through each status
# 3. get_job() -> verify status persisted
# 4. get_jobs(status="applied") -> verify filter works
# 5. delete: not a first-class operation -- remove_stale_jobs() or direct SQL
```

### DB-02: FTS5 Search Query Behavior

```python
# From get_jobs() in webapp/db.py (lines 418-426):
# If search has no FTS5 operators, each word gets a "*" suffix for prefix matching:
#   "kubernetes" -> "kubernetes*"
#   "senior python" -> "senior* python*"
#
# FTS5 operators are detected by checking for: '"', '*', 'AND', 'OR', 'NOT'
# If operators present, the search term is passed through unmodified.
#
# FTS5 columns indexed: title, company, description
# Content table: jobs (content='jobs', content_rowid=rowid)
# Sync: via triggers on INSERT, DELETE, UPDATE
```

### DB-03: Activity Log Auto-Creation Points

```python
# Events automatically logged by db.py functions:
# 1. upsert_job() on NEW job   -> event_type="discovered", new_value=platform
# 2. update_job_status()        -> event_type="status_change", old_value=old_status, new_value=new_status
# 3. update_job_notes()         -> event_type="note_added", detail=notes_text
#
# Manual logging (from webapp/app.py, not db.py):
# 4. job_detail() view          -> event_type="viewed"         (called via db.log_activity)
# 5. tailor_resume_endpoint()   -> event_type="resume_tailored" (called via db.log_activity)
# 6. cover_letter_endpoint()    -> event_type="cover_letter_generated" (called via db.log_activity)
```

### DB-05: Schema Tables, Indexes, and Triggers

```python
# Expected tables after init_db() + migrate_db() to version 6:
EXPECTED_TABLES = {
    "jobs",             # Main job table (CREATE TABLE in SCHEMA)
    "activity_log",     # Status/event tracking (migration v4)
    "run_history",      # Pipeline run history (migration v3)
    "resume_versions",  # Resume/cover letter tracking (migration v6)
    "jobs_fts",         # FTS5 virtual table (migration v4)
}

# Expected indexes:
EXPECTED_INDEXES = {
    "idx_activity_dedup",     # ON activity_log(dedup_key)
    "idx_activity_created",   # ON activity_log(created_at)
    "idx_resume_versions_job", # ON resume_versions(job_dedup_key)
}

# Expected triggers:
EXPECTED_TRIGGERS = {
    "jobs_fts_ai",   # AFTER INSERT ON jobs -> sync FTS
    "jobs_fts_ad",   # AFTER DELETE ON jobs -> sync FTS
    "jobs_fts_au",   # AFTER UPDATE ON jobs -> sync FTS
}

# Schema version:
# PRAGMA user_version should be 6 after full migration
```

### Requirement-to-Function Mapping

```
DB-01 (CRUD):     upsert_job, get_job, update_job_status, update_job_notes,
                  get_jobs (filter by status), mark_viewed, remove_stale_jobs
DB-02 (FTS5):     get_jobs(search=...), upsert_job (triggers FTS sync)
DB-03 (Activity): log_activity, get_activity_log, update_job_status (auto-logs),
                  upsert_job (auto-logs "discovered"), update_job_notes (auto-logs)
DB-04 (Bulk):     update_job_status in a loop (no dedicated bulk fn in db.py)
DB-05 (Schema):   init_db, migrate_db, SCHEMA, MIGRATIONS dict
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| File-based SQLite for tests | In-memory SQLite with per-test reset | Phase 9 (this project) | Zero disk I/O, < 5ms per test setup |
| Testing DB via ORM | Direct function calls on db module | This project (no ORM) | Simpler, matches actual code paths |
| FTS5 not tested | FTS5 with trigger-based sync, prefix matching | This project | Must test FTS sync after INSERT/UPDATE/DELETE |

**Deprecated/outdated:**
- None relevant to this phase. SQLite FTS5 API is stable since SQLite 3.9.0 (2015).

## Open Questions

1. **FTS5 Special Character Handling: Bug or Feature?**
   - What we know: `get_jobs()` does NOT catch `sqlite3.OperationalError` from malformed FTS5 queries. Searching for unbalanced `"` or lone `:` will crash.
   - What's unclear: Whether to test this as "expected behavior" (the caller should sanitize) or as a bug to file.
   - Recommendation: Test with special characters. If the function raises `OperationalError`, document it in the test as a known limitation (not a blocker for Phase 11). The fix (wrapping FTS5 MATCH in try/except) can be a quick task.

2. **Delete Operation: No First-Class API**
   - What we know: `webapp/db.py` has no `delete_job(dedup_key)` function. The only delete path is `remove_stale_jobs()` which deletes by platform + timestamp comparison. Direct SQL DELETE is possible but not exposed.
   - What's unclear: Whether DB-01 "delete" requirement means testing `remove_stale_jobs()` or if a `delete_job()` function needs to be created.
   - Recommendation: Test "delete" via `remove_stale_jobs()` -- this is the only delete mechanism in the codebase. Phase 10's `test_delta.py` already covers this function. For DB-01, verify the CRUD lifecycle ends with `remove_stale_jobs()` deleting the job and the job being retrievable as `None` afterward.

3. **backfill_score_breakdowns() Testing**
   - What we know: This function takes a `scorer_fn` callable and re-scores jobs that have `score IS NOT NULL AND score_breakdown IS NULL`. It is part of the DB API surface.
   - What's unclear: Whether it falls under DB-01 scope or should be deferred.
   - Recommendation: Include a basic test for it in the CRUD section. Create a mock `scorer_fn` that returns `(5, {"title": 2})`. Insert a job with `score=3, score_breakdown=None`, call `backfill_score_breakdowns()`, verify the score and breakdown are updated.

4. **get_stats() and get_enhanced_stats() Testing Scope**
   - What we know: These are read-only aggregation queries. `get_stats()` returns totals by score/status/platform. `get_enhanced_stats()` returns analytics data with window functions.
   - What's unclear: Whether these belong in DB-01 (CRUD) or are out of scope for Phase 11.
   - Recommendation: Include basic tests for both. Insert known jobs, verify aggregation counts are correct. The enhanced stats tests can verify the structure of the returned dict without testing every SQL edge case.

5. **run_history and resume_versions Testing**
   - What we know: `record_run()` and `get_run_history()` manage pipeline run history. `resume_versions` table is populated by `resume_ai/tracker.py`, not by `webapp/db.py` directly.
   - What's unclear: Whether to test these under DB-01 or defer to later phases.
   - Recommendation: Test `record_run()` and `get_run_history()` as part of DB-01. They are simple CRUD. The `resume_versions` table is only verified to exist (DB-05); its population is tested in resume_ai integration tests.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `webapp/db.py` (full file -- all 18 public functions, schema, migrations v1-v6, FTS5 setup, activity log, triggers)
- Codebase analysis: `tests/conftest.py` (full file -- `_fresh_db` autouse fixture, `db_with_jobs` seeded fixture)
- Codebase analysis: `tests/test_delta.py` (full file -- established pattern for testing webapp/db.py functions)
- Codebase analysis: `tests/conftest_factories.py` (full file -- JobFactory definition)
- Codebase analysis: `models.py` (full file -- JobStatus enum with all 11 states)
- Codebase analysis: `webapp/app.py` (lines 113-142 -- bulk_status_update endpoint showing the loop pattern)
- Phase 9 research and verification (test infrastructure confirmed working)
- Phase 10 research and summaries (established test patterns for this codebase)

### Secondary (MEDIUM confidence)
- SQLite FTS5 documentation (https://sqlite.org/fts5.html) -- FTS5 query syntax, prefix matching, content sync
- SQLite documentation on `INSERT ... ON CONFLICT` trigger behavior

### Tertiary (LOW confidence)
- None -- all findings from direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new libraries needed; all test infrastructure from Phase 9
- Architecture: HIGH -- Test file structure, helpers, and patterns directly derived from existing test_delta.py and codebase analysis
- Pitfalls: HIGH -- Every pitfall identified from reading the actual db.py source code (FTS5 triggers, activity log auto-creation, upsert ON CONFLICT behavior, NULL score sorting, migration idempotency)

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- stable domain, webapp/db.py unlikely to change before tests are written)
