# Phase 5: Dashboard Core - Research

**Researched:** 2026-02-07
**Domain:** FastAPI + htmx web dashboard, SQLite FTS5, activity logging
**Confidence:** HIGH

## Summary

Phase 5 adds five features to the existing FastAPI/htmx/SQLite dashboard: text search, extended status workflow (9 statuses), bulk status actions, CSV/JSON export, and per-job activity logs. The existing codebase already has a working dashboard with a job table, status badges, score/platform/status filters, and htmx-powered status updates. All five features can be implemented using the existing stack (FastAPI + Jinja2 + htmx + raw SQLite) without adding any new dependencies.

The most significant technical decision is using SQLite FTS5 for text search rather than LIKE queries. FTS5 is available on the target system (SQLite 3.51.2), runs ~3x faster even on small datasets, and scales gracefully to thousands of job descriptions. The external content table pattern keeps the FTS index synchronized with the main `jobs` table via triggers, avoiding data duplication. For the activity log, a simple append-only `activity_log` table captures all events (status changes, notes, discovery) with application-level inserts rather than database triggers, giving full control over event types and metadata.

**Primary recommendation:** Use FTS5 external content tables for search, a simple `activity_log` table for event tracking, htmx bulk update pattern with form-wrapped checkboxes, and Python `csv`/`json` standard library modules for export. No new pip dependencies needed.

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | Web framework, API endpoints | Already in use, async-ready |
| Jinja2 | 3.1+ | HTML templating | Already in use for dashboard |
| htmx | 2.0.4 | Frontend interactivity without JS | Already loaded via CDN in base.html |
| SQLite | 3.51.2 | Database with FTS5 support | Already in use, FTS5 confirmed available |
| Tailwind CSS | CDN | Styling | Already loaded via CDN in base.html |

### Supporting (Python standard library only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `csv` | stdlib | CSV export generation | Export endpoint, DictWriter for headers |
| `json` | stdlib | JSON export generation | Export endpoint, json.dumps with indent |
| `io.StringIO` | stdlib | In-memory CSV buffer | StreamingResponse for CSV download |
| `urllib.parse` | stdlib | URL encoding for search params | Preserving filters in export URLs |

### No New Dependencies Needed
| Problem | Existing Solution | Why No Addition |
|---------|-------------------|-----------------|
| Full-text search | SQLite FTS5 (built-in) | Already compiled into system SQLite |
| CSV export | Python csv module | Standard library, no pandas needed |
| JSON export | Python json module | Standard library, already in use |
| Frontend interactivity | htmx 2.0.4 | Already loaded, covers all patterns needed |
| Select-all checkbox | 6 lines of vanilla JS | Not worth adding Alpine.js/Hyperscript for one feature |

## Architecture Patterns

### Recommended Project Structure Changes
```
webapp/
├── app.py              # MODIFIED: new endpoints (search, bulk, export, activity)
├── db.py               # MODIFIED: FTS5 setup, activity_log table, new queries
├── templates/
│   ├── base.html       # MODIFIED: new status CSS colors
│   ├── dashboard.html  # MODIFIED: search input, checkboxes, bulk action bar, export buttons
│   ├── job_detail.html # MODIFIED: activity timeline section, 9-status dropdown
│   ├── run_history.html # UNCHANGED
│   └── partials/       # NEW: htmx partial templates
│       └── job_rows.html   # NEW: just the <tbody> content for search results
├── static/             # EXISTS (currently empty)
└── __init__.py
```

### Pattern 1: FTS5 External Content Table
**What:** An FTS5 virtual table that indexes the `jobs` table content but does not store a copy of it. Synchronized via SQLite triggers.
**When to use:** When you need full-text search on an existing table without duplicating data.
**Example:**
```sql
-- Source: https://www.sqlite.org/fts5.html (External Content Tables section)

-- Create FTS5 index on existing jobs table
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, company, description,
    content='jobs',
    content_rowid=rowid
);

-- Trigger: keep FTS index updated on INSERT
CREATE TRIGGER IF NOT EXISTS jobs_fts_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, company, description)
    VALUES (new.rowid, new.title, new.company, new.description);
END;

-- Trigger: keep FTS index updated on DELETE
CREATE TRIGGER IF NOT EXISTS jobs_fts_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company, description)
    VALUES ('delete', old.rowid, old.title, old.company, old.description);
END;

-- Trigger: keep FTS index updated on UPDATE
CREATE TRIGGER IF NOT EXISTS jobs_fts_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company, description)
    VALUES ('delete', old.rowid, old.title, old.company, old.description);
    INSERT INTO jobs_fts(rowid, title, company, description)
    VALUES (new.rowid, new.title, new.company, new.description);
END;

-- Rebuild index for existing data
INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild');
```

**Querying:**
```sql
-- Basic search with ranking
SELECT j.* FROM jobs j
JOIN jobs_fts ON jobs_fts.rowid = j.rowid
WHERE jobs_fts MATCH ?
ORDER BY jobs_fts.rank;

-- Boolean operators work: 'kubernetes AND remote'
-- Prefix matching works: 'kube*'
-- Phrase matching works: '"platform engineer"'
```

**Critical detail:** The `jobs` table currently uses `dedup_key TEXT` as PRIMARY KEY, which means SQLite assigns implicit integer rowids. The FTS5 `content_rowid` must reference the integer rowid, not the text primary key. Using `content_rowid=rowid` (the implicit one) works correctly.

### Pattern 2: htmx Active Search (Debounced)
**What:** A search input that filters results server-side with a 500ms debounce, replacing the table body via htmx.
**When to use:** Instant filter-as-you-type UI without JavaScript.
**Example:**
```html
<!-- Source: https://htmx.org/examples/active-search/ -->
<input type="search" name="q" placeholder="Search jobs..."
       hx-get="/search"
       hx-trigger="input changed delay:500ms, keyup[key=='Enter']"
       hx-target="#job-table-body"
       hx-swap="innerHTML"
       hx-indicator="#search-spinner"
       hx-include="[name='score'],[name='platform'],[name='status'],[name='sort'],[name='dir']"
       class="border rounded px-3 py-1.5 text-sm w-full md:w-80">
<span id="search-spinner" class="htmx-indicator text-sm text-gray-400">Searching...</span>
```
**Key:** `hx-include` pulls in the existing filter values so search respects active filters.

### Pattern 3: htmx Bulk Update with Checkboxes
**What:** A form wrapping the job table with checkboxes per row and a bulk action bar.
**When to use:** Select multiple rows and apply an action (status change) to all at once.
**Example:**
```html
<!-- Source: https://htmx.org/examples/bulk-update/ -->
<form id="bulk-form">
    <div id="bulk-bar" class="hidden bg-indigo-50 border border-indigo-200 rounded p-3 mb-4 flex items-center gap-4">
        <span id="selected-count">0 selected</span>
        <select name="bulk_status">
            <option value="">Change status to...</option>
            <!-- status options -->
        </select>
        <button type="button"
                hx-post="/bulk/status"
                hx-include="#bulk-form"
                hx-target="#job-table-body"
                hx-swap="innerHTML"
                class="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm">
            Apply
        </button>
    </div>
    <table>
        <tbody id="job-table-body">
            <tr>
                <td><input type="checkbox" name="job_keys" value="company::title"></td>
                <!-- ... row data ... -->
            </tr>
        </tbody>
    </table>
</form>
```
**Select-all checkbox:** Requires a small inline `<script>` (6 lines) since htmx does not handle checkbox toggling. This is the one place vanilla JS is needed.

### Pattern 4: Activity Log Table
**What:** An append-only table that records all events for a job.
**When to use:** Timeline of discovery, status changes, notes, and applications.
**Example:**
```sql
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_key TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- 'discovered', 'status_change', 'note_added', 'applied', 'scored', 'viewed'
    old_value TEXT,             -- previous status (for status_change)
    new_value TEXT,             -- new status (for status_change)
    detail TEXT,                -- additional context (note text, score, etc.)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dedup_key) REFERENCES jobs(dedup_key)
);

CREATE INDEX IF NOT EXISTS idx_activity_log_dedup_key ON activity_log(dedup_key);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
```
**Why application-level, not triggers:** Triggers cannot capture event metadata (who changed it, which endpoint, note content). Application-level inserts in `db.update_job_status()` and `db.update_job_notes()` give full control.

### Pattern 5: CSV/JSON Export via StreamingResponse
**What:** Endpoints that return the current filtered job list as a downloadable CSV or JSON file.
**When to use:** Export buttons on the dashboard.
**Example:**
```python
# Source: FastAPI official docs + standard library
import csv
import io
import json
from fastapi.responses import StreamingResponse, JSONResponse

@app.get("/export/csv")
async def export_csv(score: int | None = None, platform: str | None = None,
                     status: str | None = None, q: str | None = None):
    jobs = db.get_jobs(score_min=score, platform=platform, status=status, search=q)
    output = io.StringIO()
    fields = ["title", "company", "location", "salary_display", "platform",
              "status", "score", "url", "posted_date", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        writer.writerow(job)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs_export.csv"},
    )
```

### Anti-Patterns to Avoid
- **Client-side search with JavaScript:** The data lives in SQLite. Shipping all jobs to the browser for filtering defeats server-side rendering. Use FTS5 server-side.
- **Storing activity in the jobs table:** Adding columns like `status_history TEXT` as JSON in the jobs table creates parsing overhead and limits querying. Use a separate table.
- **Using pandas for CSV export:** The project has no pandas dependency. The stdlib `csv` module handles this in 10 lines. Do not add a heavy dependency for a simple task.
- **Alpine.js/Hyperscript for checkbox logic:** Adding a JS micro-framework for one "select all" checkbox is over-engineering. Six lines of vanilla JS suffice.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search | Custom tokenizer, LIKE with wildcards | SQLite FTS5 with `MATCH` | FTS5 handles tokenization, stemming, ranking, boolean operators |
| Search debouncing | JavaScript debounce library | htmx `delay:500ms` trigger modifier | Built into htmx, zero JS |
| CSV generation | String concatenation | `csv.DictWriter` | Handles quoting, escaping, headers automatically |
| Status workflow validation | Custom state machine class | Simple list constant + validation | Only 9 statuses, no complex transitions to enforce |

**Key insight:** This phase is enhancement of an existing, working dashboard. The technology decisions are already made (FastAPI, htmx, SQLite, Jinja2). The research is about which patterns within that stack to use, not which stack to choose.

## Common Pitfalls

### Pitfall 1: FTS5 rowid vs. dedup_key Mismatch
**What goes wrong:** The `jobs` table uses `dedup_key TEXT` as PRIMARY KEY. Developers might try `content_rowid='dedup_key'`, but FTS5 requires an INTEGER rowid.
**Why it happens:** SQLite assigns an implicit integer `rowid` even to tables with text primary keys, but it is not obvious.
**How to avoid:** Use `content_rowid=rowid` (the implicit one). When querying, JOIN `jobs_fts.rowid = jobs.rowid`. Verify with: `SELECT rowid, dedup_key FROM jobs LIMIT 5`.
**Warning signs:** "datatype mismatch" errors when inserting into FTS5 table.

### Pitfall 2: FTS5 Index Not Rebuilt After Migration
**What goes wrong:** Existing jobs in the database are not searchable after adding FTS5.
**Why it happens:** The triggers only capture future INSERT/UPDATE/DELETE. The migration must explicitly rebuild the index for existing data.
**How to avoid:** Include `INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')` as the last step in the migration that creates the FTS5 table and triggers.
**Warning signs:** Search returns 0 results when jobs are clearly present.

### Pitfall 3: Status Enum Mismatch Between models.py and db.py
**What goes wrong:** The `JobStatus` enum in `models.py` has 6 values (discovered, scored, approved, applied, rejected, skipped) but the dashboard needs 9 statuses. Updating one but not the other causes serialization errors.
**Why it happens:** Status values are stored as plain strings in SQLite but validated through the Pydantic enum in the pipeline.
**How to avoid:** Update `JobStatus` enum in `models.py`, the `STATUSES` list in `app.py`, and the CSS classes in `base.html` all in the same plan. Add a migration to convert old status values to the new vocabulary.
**Warning signs:** "value is not a valid enumeration member" Pydantic errors during import.

### Pitfall 4: Checkbox Values Lost on htmx Swap
**What goes wrong:** User checks boxes, searches/filters, and the table body is replaced by htmx -- all checkbox state is lost.
**Why it happens:** htmx innerHTML swap replaces the entire `<tbody>`, including checked inputs.
**How to avoid:** Accept this as expected behavior (new results = new selection). Alternatively, process selections before allowing a new search. The bulk action bar should be designed so users: filter first, then select and act.
**Warning signs:** Users check 10 boxes, type a search term, and their selection disappears.

### Pitfall 5: Export Not Respecting Active Filters
**What goes wrong:** User filters to Score 5 + Remote, clicks Export, and gets all 500 jobs.
**Why it happens:** The export button links to `/export/csv` without passing the current filter parameters.
**How to avoid:** Export buttons must include query parameters matching the current filters. Use JavaScript or htmx `hx-include` to pass the current filter form values to the export URL.
**Warning signs:** Exported file has more rows than displayed on dashboard.

### Pitfall 6: Activity Log for Existing Jobs
**What goes wrong:** Jobs that were discovered before the activity log feature have no timeline entries.
**Why it happens:** The activity_log table starts empty and only captures future events.
**How to avoid:** During migration, backfill a `discovered` event for every existing job using their `created_at` timestamp.
**Warning signs:** Old jobs show "No activity" while new jobs have full timelines.

## Code Examples

### Search Endpoint (FastAPI + FTS5)
```python
# Source: verified against SQLite 3.51.2 FTS5 on target system

@app.get("/search", response_class=HTMLResponse)
async def search_jobs(
    request: Request,
    q: str = Query(""),
    score: int | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    # Return just the table body rows for htmx swap
    return templates.TemplateResponse(
        "partials/job_rows.html",
        {"request": request, "jobs": jobs, "statuses": STATUSES},
    )
```

### FTS5-Enabled get_jobs Query
```python
def get_jobs(
    search: str | None = None,
    score_min: int | None = None,
    platform: str | None = None,
    status: str | None = None,
    sort_by: str = "score",
    sort_dir: str = "desc",
) -> list[dict]:
    where_clauses = []
    params: list = []
    join = ""

    if search and search.strip():
        # Use FTS5 for text search
        join = "JOIN jobs_fts ON jobs_fts.rowid = jobs.rowid"
        where_clauses.append("jobs_fts MATCH ?")
        # Add wildcards for prefix matching: "kube" -> "kube*"
        term = search.strip()
        if not any(c in term for c in ('"', '*', 'AND', 'OR', 'NOT')):
            # Simple search: add prefix matching
            words = term.split()
            term = " ".join(f"{w}*" for w in words if w)
        params.append(term)

    if score_min is not None:
        where_clauses.append("jobs.score >= ?")
        params.append(score_min)
    # ... other filters ...

    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"SELECT jobs.* FROM jobs {join} {where} ORDER BY ..."

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
```

### Bulk Status Update Endpoint
```python
@app.post("/bulk/status", response_class=HTMLResponse)
async def bulk_status_update(
    request: Request,
    job_keys: list[str] = Form(default=[]),
    bulk_status: str = Form(...),
):
    if bulk_status and job_keys:
        for key in job_keys:
            old_status = db.get_job(key).get("status") if db.get_job(key) else None
            db.update_job_status(key, bulk_status)
            db.log_activity(key, "status_change", old_value=old_status, new_value=bulk_status)
    # Re-fetch and return updated table body
    jobs = db.get_jobs()
    return templates.TemplateResponse(
        "partials/job_rows.html",
        {"request": request, "jobs": jobs, "statuses": STATUSES},
    )
```

### Activity Log Query
```python
def get_activity_log(dedup_key: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM activity_log
               WHERE dedup_key = ?
               ORDER BY created_at DESC""",
            (dedup_key,),
        ).fetchall()
    return [dict(row) for row in rows]

def log_activity(
    dedup_key: str,
    event_type: str,
    old_value: str | None = None,
    new_value: str | None = None,
    detail: str | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO activity_log (dedup_key, event_type, old_value, new_value, detail)
               VALUES (?, ?, ?, ?, ?)""",
            (dedup_key, event_type, old_value, new_value, detail),
        )
```

### Select-All Checkbox (Minimal Vanilla JS)
```html
<script>
document.getElementById('select-all').addEventListener('change', function() {
    document.querySelectorAll('input[name="job_keys"]').forEach(cb => {
        cb.checked = this.checked;
    });
    updateBulkBar();
});

function updateBulkBar() {
    const count = document.querySelectorAll('input[name="job_keys"]:checked').length;
    document.getElementById('selected-count').textContent = count + ' selected';
    document.getElementById('bulk-bar').classList.toggle('hidden', count === 0);
}
// Attach to each checkbox
document.addEventListener('change', function(e) {
    if (e.target.name === 'job_keys') updateBulkBar();
});
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `stealth_sync(page)` | `Stealth().apply_stealth_sync(page)` | playwright-stealth 2.0.1 | Not relevant to Phase 5, but documented in memory |
| `LIKE '%term%'` for search | FTS5 `MATCH` with ranking | SQLite 3.9.0+ (2015) | 3x faster even at small scale, proper tokenization |
| htmx 1.x | htmx 2.0.4 | 2024 | Minor attribute changes, already on 2.0.4 |
| Manual status strings | Pydantic enum `JobStatus` | Phase A | Must be updated for 9-status workflow |

**Deprecated/outdated:**
- None specific to this phase. The existing stack is current.

## Status Workflow Design

### Current Status Values (6)
```python
# models.py
class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    SCORED = "scored"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    SKIPPED = "skipped"
```

### Required Status Values (9 from DASH-02)
```
Saved, Applied, Phone Screen, Technical Interview,
Final Interview, Offer, Rejected, Withdrawn, Ghosted
```

### Reconciliation Strategy
The requirement specifies 9 user-facing statuses. The existing pipeline uses `discovered` and `scored` internally (set by the pipeline, not the user). These should remain as internal pipeline statuses, with the 9 user-facing statuses added for the application tracking workflow.

**Recommended combined enum (11 total):**
```python
class JobStatus(str, Enum):
    # Pipeline-managed (set by orchestrator)
    DISCOVERED = "discovered"
    SCORED = "scored"
    # User-managed (set from dashboard)
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"
```

**Migration path:** Existing `approved` -> `saved`, existing `skipped` -> `withdrawn`. Data migration query needed.

## Schema Migration Plan

This phase requires schema version 4 -> 5 (two migrations):

**Version 4: FTS5 + Activity Log**
```sql
-- FTS5 virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, company, description,
    content='jobs',
    content_rowid=rowid
);

-- Synchronization triggers
CREATE TRIGGER IF NOT EXISTS jobs_fts_ai AFTER INSERT ON jobs BEGIN ... END;
CREATE TRIGGER IF NOT EXISTS jobs_fts_ad AFTER DELETE ON jobs BEGIN ... END;
CREATE TRIGGER IF NOT EXISTS jobs_fts_au AFTER UPDATE ON jobs BEGIN ... END;

-- Rebuild index for existing data
INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild');

-- Activity log table
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_activity_dedup ON activity_log(dedup_key);

-- Backfill discovery events for existing jobs
INSERT INTO activity_log (dedup_key, event_type, new_value, created_at)
SELECT dedup_key, 'discovered', platform, COALESCE(first_seen_at, created_at)
FROM jobs;
```

**Version 5: Status vocabulary migration**
```sql
UPDATE jobs SET status = 'saved' WHERE status = 'approved';
UPDATE jobs SET status = 'withdrawn' WHERE status = 'skipped';
```

## Open Questions

1. **Should search include tags?**
   - What we know: FTS5 can index additional columns. Tags are stored as JSON arrays in the `tags` column.
   - What is unclear: Whether users would expect tag search from the search box, or if tags are too generic to be useful.
   - Recommendation: Include tags in FTS5 index. Low cost, potential benefit. Parse JSON array to space-separated string during index rebuild.

2. **Should status transitions be enforced?**
   - What we know: The requirement says 9 statuses but does not specify allowed transitions (e.g., can you go from "Ghosted" back to "Phone Screen"?).
   - What is unclear: Whether free-form status selection is intended or if a state machine is needed.
   - Recommendation: Allow free-form status changes. A state machine adds complexity with no stated requirement. Any status can transition to any other status.

3. **Export filename conventions**
   - What we know: Users need CSV and JSON export.
   - What is unclear: Whether the filename should include the date, filter description, or be generic.
   - Recommendation: Include date: `jobs_export_2026-02-07.csv`. Keep it simple.

## Sources

### Primary (HIGH confidence)
- [SQLite FTS5 Official Documentation](https://www.sqlite.org/fts5.html) - External content tables, triggers, MATCH syntax, bm25 ranking
- [htmx Active Search Example](https://htmx.org/examples/active-search/) - Input trigger pattern, debounce, target swap
- [htmx Bulk Update Example](https://htmx.org/examples/bulk-update/) - Form wrapping, checkbox pattern, bulk action
- [FastAPI Custom Responses](https://fastapi.tiangolo.com/advanced/custom-response/) - StreamingResponse for file downloads
- Local system verification: SQLite 3.51.2 with FTS5 confirmed working (external content tables, triggers, bm25, highlight)

### Secondary (MEDIUM confidence)
- [Simon Willison - JSON audit log in SQLite](https://til.simonwillison.net/sqlite/json-audit-log) - Audit trail design patterns
- [Sling Academy - CSV in FastAPI](https://www.slingacademy.com/article/how-to-return-a-csv-file-in-fastapi/) - StreamingResponse with csv module
- [htmx Documentation](https://htmx.org/docs/) - hx-include, hx-trigger modifiers

### Tertiary (LOW confidence)
- None. All findings verified against official docs or local system.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; existing stack verified in codebase
- Architecture (FTS5): HIGH - Verified FTS5 works on target SQLite 3.51.2 with external content tables, triggers, bm25 ranking
- Architecture (htmx patterns): HIGH - Official htmx examples match exactly what is needed
- Architecture (Activity log): HIGH - Standard append-only table pattern, well-understood
- Pitfalls: HIGH - Derived from actual codebase analysis (rowid vs dedup_key, enum mismatch, migration rebuild)

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (stable stack, no fast-moving dependencies)
