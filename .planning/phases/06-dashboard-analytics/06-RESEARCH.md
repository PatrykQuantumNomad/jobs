# Phase 6: Dashboard Analytics - Research

**Researched:** 2026-02-07
**Domain:** Dashboard analytics (charting, kanban drag-and-drop, SQLite analytics queries, htmx real-time updates)
**Confidence:** HIGH

## Summary

Phase 6 adds two major features to the existing FastAPI/htmx/SQLite dashboard: (1) an analytics stats page with charts showing jobs per day/week, response rates, time-in-stage, and platform effectiveness, and (2) a kanban board view with drag-and-drop between status columns. Both features can be implemented by adding two CDN-loaded JavaScript libraries (Chart.js 4.5.1 for charts, SortableJS 1.15.6 for drag-and-drop) to the existing stack, with no build toolchain changes.

The critical architectural insight is that SQLite 3.51.2 (the version on this machine) fully supports window functions (`OVER`, `PARTITION BY`, `LAG`, `LEAD`) -- these were added in SQLite 3.25.0. This means the analytics queries for time-in-stage calculations can use proper window functions rather than expensive correlated subqueries. The `activity_log` table already records `status_change` events with `old_value`, `new_value`, and `created_at` timestamps, providing the raw data for all time-based analytics.

For the kanban board, SortableJS is the established library for drag-and-drop between lists in server-rendered apps. It integrates cleanly with htmx: SortableJS handles the DOM drag interaction, and on the `onEnd` event, an `htmx.ajax()` call sends the status change to the server. The server responds with an `HX-Trigger` header to update the stats panel, keeping charts in sync without a full page refresh.

**Primary recommendation:** Use Chart.js 4.5.1 via CDN for charts, SortableJS 1.15.6 via CDN for kanban drag-and-drop, SQLite window functions for time-in-stage analytics, and htmx `HX-Trigger` response headers to keep stats in sync when jobs move between kanban columns.

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | Web framework, API endpoints | Already in use |
| Jinja2 | 3.1+ | HTML templating | Already in use |
| htmx | 2.0.4 | Frontend interactivity | Already loaded via CDN in base.html |
| SQLite | 3.51.2 | Database (window functions confirmed) | Already in use |
| Tailwind CSS | CDN | Styling | Already loaded via CDN in base.html |

### New CDN Dependencies
| Library | Version | CDN URL | Purpose |
|---------|---------|---------|---------|
| Chart.js | 4.5.1 | `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` | Bar, doughnut, and line charts for analytics dashboard |
| SortableJS | 1.15.6 | `https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js` | Drag-and-drop between kanban columns |

### No Build Toolchain Required
Both libraries work as standalone UMD scripts loaded via `<script>` tag. No npm, no bundler, no transpilation. This matches the existing CDN-only pattern (htmx, Tailwind).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Chart.js | ApexCharts | Larger bundle (~150KB vs ~65KB), more features but overkill for this use case |
| Chart.js | Lightweight-charts (TradingView) | Specialized for financial data, not general purpose |
| SortableJS | Native HTML5 DnD API | No touch support, verbose event handling, no animation, no group support |
| SortableJS | dnd-kit / react-beautiful-dnd | React-specific, not compatible with server-rendered htmx stack |
| SortableJS | Dragula | Abandoned/unmaintained since 2019, SortableJS is actively maintained |

**Installation (add to base.html):**
```html
<!-- Chart.js (only on analytics pages) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<!-- SortableJS (only on kanban page) -->
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
```

**Recommendation:** Load these scripts only on pages that need them using Jinja2 `{% block scripts %}` in base.html, not globally. This avoids loading 65KB of Chart.js on the main job table page.

## Architecture Patterns

### Recommended Project Structure Changes
```
webapp/
├── app.py              # MODIFIED: new /analytics, /kanban, /api/analytics endpoints
├── db.py               # MODIFIED: new analytics query functions
├── templates/
│   ├── base.html       # MODIFIED: add {% block scripts %} for page-specific JS
│   ├── dashboard.html  # UNCHANGED
│   ├── analytics.html  # NEW: stats dashboard with charts
│   ├── kanban.html     # NEW: kanban board view
│   ├── job_detail.html # UNCHANGED
│   ├── run_history.html # UNCHANGED
│   └── partials/
│       ├── job_rows.html    # UNCHANGED
│       ├── stats_cards.html # NEW: htmx-swappable stats summary cards
│       └── kanban_card.html # NEW: individual kanban card partial
└── static/             # EXISTS (currently empty)
```

### Pattern 1: JSON API Endpoint for Chart Data
**What:** A FastAPI endpoint that returns analytics data as JSON, consumed by Chart.js on the client side.
**When to use:** When Chart.js needs structured data to render charts. Charts cannot be server-rendered -- they require client-side JavaScript.
**Why not HTML partials:** Chart.js operates on a `<canvas>` element and needs JSON data objects (labels, datasets). Server-rendered HTML cannot produce charts.
**Example:**
```python
# Source: Chart.js data structure docs + FastAPI JSONResponse
from fastapi.responses import JSONResponse

@app.get("/api/analytics")
async def analytics_api():
    stats = db.get_enhanced_stats()
    return JSONResponse(stats)
```

```javascript
// Client: fetch and render
async function loadCharts() {
    const resp = await fetch('/api/analytics');
    const data = await resp.json();

    new Chart(document.getElementById('jobs-per-day'), {
        type: 'bar',
        data: {
            labels: data.jobs_per_day.map(d => d.date),
            datasets: [{
                label: 'Jobs Discovered',
                data: data.jobs_per_day.map(d => d.count),
                borderWidth: 1
            }]
        },
        options: { scales: { y: { beginAtZero: true } } }
    });
}
```

### Pattern 2: Server-Rendered Analytics Page with Inline JSON
**What:** Render the analytics page server-side with chart data embedded as a JSON `<script>` block, avoiding a separate API call on page load.
**When to use:** For the initial page load of the analytics dashboard.
**Why:** Eliminates a round-trip. The server already has the data; embed it directly.
**Example:**
```html
<!-- analytics.html -->
{% extends "base.html" %}
{% block content %}
<canvas id="jobs-per-day" width="400" height="200"></canvas>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script>
    const analyticsData = {{ analytics_json | safe }};
    // Initialize charts with embedded data
    new Chart(document.getElementById('jobs-per-day'), {
        type: 'bar',
        data: {
            labels: analyticsData.jobs_per_day.map(d => d.date),
            datasets: [{
                label: 'Jobs Discovered',
                data: analyticsData.jobs_per_day.map(d => d.count)
            }]
        }
    });
</script>
{% endblock %}
```

```python
# app.py
@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    stats = db.get_enhanced_stats()
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "stats": stats,
            "analytics_json": json.dumps(stats),
        },
    )
```

### Pattern 3: SortableJS Kanban with htmx.ajax()
**What:** Each kanban column is a SortableJS list. When a card is dragged between columns, the `onEnd` callback fires `htmx.ajax()` to persist the status change.
**When to use:** Kanban board view where jobs are cards in status columns.
**Why htmx.ajax() instead of hx-trigger="end":** The htmx `hx-trigger="end"` pattern works for single-list reordering, but for kanban (dragging between groups), you need to know which column the card landed in. The `onEnd` callback gives you `evt.to.dataset.status` and `evt.item.dataset.key`, which you pass to `htmx.ajax()`.
**Example:**
```html
<!-- kanban.html -->
<div class="flex gap-4 overflow-x-auto">
    {% for status in kanban_statuses %}
    <div class="kanban-column min-w-[280px] flex-shrink-0"
         data-status="{{ status }}">
        <h3 class="font-semibold text-sm text-gray-600 mb-2 uppercase">
            {{ status | replace('_', ' ') }}
            <span class="text-gray-400">({{ columns[status] | length }})</span>
        </h3>
        <div class="kanban-list space-y-2 min-h-[200px] bg-gray-50 rounded-lg p-2"
             data-status="{{ status }}"
             id="col-{{ status }}">
            {% for job in columns[status] %}
            <div class="kanban-card bg-white rounded-lg shadow-sm border p-3 cursor-grab"
                 data-key="{{ job.dedup_key }}"
                 data-status="{{ status }}">
                <div class="font-medium text-sm">{{ job.title }}</div>
                <div class="text-xs text-gray-500">{{ job.company }}</div>
                {% if job.score %}
                <span class="score-{{ job.score }} text-xs">Score: {{ job.score }}</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</div>
```

```javascript
// Initialize SortableJS on each column
document.querySelectorAll('.kanban-list').forEach(list => {
    new Sortable(list, {
        group: 'kanban',
        animation: 150,
        ghostClass: 'opacity-30',
        dragClass: 'shadow-lg',
        onEnd: function(evt) {
            const dedupKey = evt.item.dataset.key;
            const newStatus = evt.to.dataset.status;
            const oldStatus = evt.from.dataset.status;

            if (newStatus === oldStatus) return; // Same column, no change

            // Persist via htmx
            htmx.ajax('POST', `/jobs/${encodeURIComponent(dedupKey)}/status`, {
                values: { status: newStatus },
                target: '#kanban-stats',
                swap: 'innerHTML'
            });
        }
    });
});
```

### Pattern 4: HX-Trigger for Cross-Component Updates
**What:** When a kanban card is moved (status changes), the server responds with an `HX-Trigger` header that causes the stats panel to refresh.
**When to use:** When an action on one component (kanban drag) should update another component (stats cards).
**Example:**
```python
# app.py - status update endpoint enhanced with HX-Trigger
@app.post("/jobs/{dedup_key:path}/status")
async def update_status(dedup_key: str, status: str = Form(...)):
    db.update_job_status(dedup_key, status)
    job = db.get_job(dedup_key)
    label = status.replace("_", " ").title()
    response = HTMLResponse(
        f'<span class="status-badge status-{status}">{label}</span>'
    )
    # Trigger stats refresh on other listening elements
    response.headers["HX-Trigger"] = "statsChanged"
    return response
```

```html
<!-- Stats panel listens for statsChanged event -->
<div id="kanban-stats"
     hx-get="/api/stats-cards"
     hx-trigger="statsChanged from:body"
     hx-swap="innerHTML">
    {% include "partials/stats_cards.html" %}
</div>
```

### Pattern 5: Chart.js Update Without Destroy/Recreate
**What:** When stats change, update existing Chart.js instances by modifying their data and calling `chart.update()` instead of destroying and recreating them.
**When to use:** When the stats panel refreshes after a kanban drag.
**Example:**
```javascript
// Store chart references globally
const charts = {};

function initChart(id, config) {
    if (charts[id]) {
        charts[id].destroy();
    }
    charts[id] = new Chart(document.getElementById(id), config);
    return charts[id];
}

// After htmx swaps new stats, reinitialize charts
document.body.addEventListener('statsChanged', async function() {
    const resp = await fetch('/api/analytics');
    const data = await resp.json();
    // Update existing chart data
    if (charts['platform-chart']) {
        charts['platform-chart'].data.labels = data.by_platform.map(p => p.name);
        charts['platform-chart'].data.datasets[0].data = data.by_platform.map(p => p.count);
        charts['platform-chart'].update('none'); // Skip animation for quick update
    }
});
```

### Anti-Patterns to Avoid
- **Server-rendering charts as HTML:** Chart.js requires a `<canvas>` element and client-side JavaScript. Do not attempt to generate chart markup server-side.
- **Embedding chart data in HTML data attributes:** For more than a few data points, this becomes unwieldy. Use inline JSON `<script>` blocks or fetch from an API endpoint.
- **Using hx-trigger="end" for kanban:** The htmx sortable example is for single-list reordering. For cross-list kanban, use `onEnd` callback with `htmx.ajax()` to know which column the card moved to.
- **Polling for stats updates:** Do not use `hx-trigger="every 30s"` for stats. Stats only change when the user acts (drag a card, import jobs). Use event-driven updates with `HX-Trigger` response headers instead.
- **Destroying and recreating charts on every update:** Chart.js supports in-place data mutation via `chart.data.datasets[0].data = newData; chart.update()`. Destroying and recreating causes flicker.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart rendering | Custom SVG/Canvas drawing | Chart.js 4.5.1 | Handles responsive sizing, tooltips, animations, legend, accessibility, touch |
| Drag-and-drop between lists | Native HTML5 DnD API | SortableJS 1.15.6 | Touch support, animation, group management, accessibility, tested cross-browser |
| Time-in-stage calculation | Python loop over activity_log | SQLite window functions (LAG/LEAD) | Database does the heavy lifting, single query vs. N+1 |
| Jobs per day/week aggregation | Python datetime grouping | SQLite `strftime()` + `GROUP BY` | Aggregate at query level, not application level |
| Date difference calculation | Python timedelta math | SQLite `julianday()` subtraction | Stays in the query, no data transfer overhead |
| Stats refresh after drag | Manual DOM manipulation | htmx `HX-Trigger` + `from:body` listener | Decoupled, declarative, follows htmx patterns |

**Key insight:** The analytics engine belongs in SQLite queries, not in Python application code. SQLite 3.51.2 has all the tools needed: window functions, `julianday()`, `strftime()`, `GROUP BY`. Compute aggregates in SQL and return pre-computed results to the API endpoint.

## Common Pitfalls

### Pitfall 1: Chart.js Canvas Not Found After htmx Swap
**What goes wrong:** Chart.js tries to initialize on a `<canvas>` element that does not yet exist in the DOM because htmx has not finished the swap.
**Why it happens:** If Chart.js initialization code runs before the htmx swap completes, `document.getElementById('myChart')` returns null.
**How to avoid:** Use `htmx.onLoad()` to initialize charts inside swapped content, or initialize charts in a `<script>` block inside the `{% block scripts %}` section that runs after the DOM is ready.
**Warning signs:** `Cannot read properties of null (reading 'getContext')` in console.

### Pitfall 2: Multiple Chart.js Instances on Same Canvas
**What goes wrong:** Navigating to the analytics page, leaving, and returning creates a second Chart.js instance on the same canvas, causing rendering glitches (overlapping tooltips, doubled animations).
**Why it happens:** Chart.js does not automatically clean up when the canvas is removed from the DOM by htmx or navigation.
**How to avoid:** Store chart references in a global `charts` object. Before creating a new chart, check if one already exists and call `charts[id].destroy()` first. Alternatively, use `Chart.getChart(canvasElement)` to check for existing instances.
**Warning signs:** Flickering chart, tooltips showing old data, "Canvas is already in use" warning.

### Pitfall 3: Kanban Card Snaps Back After Drop
**What goes wrong:** User drags a card to a new column, it appears to land, then snaps back to its original column.
**Why it happens:** The `htmx.ajax()` call in `onEnd` fails (network error, validation error), but SortableJS has already moved the DOM element. There is no automatic rollback mechanism.
**How to avoid:** In the `onEnd` callback, show a loading indicator. If the server request fails, manually move the DOM element back to `evt.from` at `evt.oldIndex`. Use a try/catch around the ajax call.
**Warning signs:** Cards appear to move successfully but the database still has the old status.

### Pitfall 4: Time-in-Stage Returns NULL for Jobs Without Activity
**What goes wrong:** Jobs that were imported before the activity_log existed have no `status_change` events, so the time-in-stage query returns NULL or skips them entirely.
**Why it happens:** The activity_log backfill (Phase 5 migration) only inserted `discovered` events, not the initial scoring/status events.
**How to avoid:** Use `COALESCE` in the time-in-stage query to fall back to `jobs.created_at` when no activity_log entry exists. Alternatively, accept that pre-existing jobs will not have time-in-stage data and filter them out with a note.
**Warning signs:** Time-in-stage metrics show 0 jobs or implausibly long durations.

### Pitfall 5: SQLite julianday() With Null Timestamps
**What goes wrong:** `julianday(NULL) - julianday(some_date)` returns NULL, silently excluding rows from AVG/SUM aggregations.
**Why it happens:** Many jobs have NULL values for `applied_date`, `viewed_at`, or activity_log timestamps depending on their status.
**How to avoid:** Always filter with `WHERE column IS NOT NULL` before date arithmetic, or use `COALESCE(column, datetime('now'))` for in-progress calculations. Be explicit about what "time-in-stage" means for jobs still in that stage.
**Warning signs:** Averages seem too low or too high because of missing data points.

### Pitfall 6: Kanban Column Overflow With Many Jobs
**What goes wrong:** The "discovered" or "scored" columns have 50+ jobs, making the kanban board unusable (too many cards to scroll through, poor drag performance).
**Why it happens:** The kanban view is designed for active pipeline management (saved through offer), not for bulk triage of discovered jobs.
**How to avoid:** Only show user-managed statuses on the kanban board (saved, applied, phone_screen, technical, final_interview, offer, rejected, withdrawn, ghosted). Exclude `discovered` and `scored` -- those are managed in the table view. Optionally, limit each column to 20 cards with a "show more" link.
**Warning signs:** Page loads slowly, browser becomes unresponsive during drag, columns are miles long.

### Pitfall 7: Chart.js CDN Script Loaded But Not Available
**What goes wrong:** The `Chart` constructor is called before the CDN script has finished loading, resulting in `Chart is not defined`.
**Why it happens:** When Chart.js is loaded via CDN in a `{% block scripts %}` section, the browser may not have finished downloading it before inline `<script>` code runs.
**How to avoid:** Place the Chart.js initialization script AFTER the CDN `<script>` tag in the same block. CDN scripts are loaded synchronously by default (no `async` or `defer` attribute). Or use `window.addEventListener('load', ...)` for safety.
**Warning signs:** Intermittent `ReferenceError: Chart is not defined` depending on network speed.

## Code Examples

### Enhanced Analytics Query: Jobs Per Day
```sql
-- Source: SQLite strftime() docs + verified on SQLite 3.51.2
-- Jobs discovered per day for the last 30 days
SELECT
    strftime('%Y-%m-%d', created_at) AS date,
    COUNT(*) AS count
FROM jobs
WHERE created_at >= datetime('now', '-30 days')
GROUP BY strftime('%Y-%m-%d', created_at)
ORDER BY date;
```

### Enhanced Analytics Query: Jobs Per Week
```sql
-- Jobs per week (ISO week number)
SELECT
    strftime('%Y-W%W', created_at) AS week,
    COUNT(*) AS count
FROM jobs
WHERE created_at >= datetime('now', '-12 weeks')
GROUP BY strftime('%Y-W%W', created_at)
ORDER BY week;
```

### Enhanced Analytics Query: Platform Effectiveness
```sql
-- Jobs per platform with score distribution
SELECT
    platform,
    COUNT(*) AS total,
    SUM(CASE WHEN score >= 4 THEN 1 ELSE 0 END) AS high_quality,
    ROUND(AVG(score), 1) AS avg_score,
    SUM(CASE WHEN status IN ('applied', 'phone_screen', 'technical',
         'final_interview', 'offer') THEN 1 ELSE 0 END) AS actioned
FROM jobs
GROUP BY platform;
```

### Enhanced Analytics Query: Application Response Rate
```sql
-- Response rate: of jobs applied to, how many progressed beyond 'applied'
SELECT
    COUNT(*) AS total_applied,
    SUM(CASE WHEN status IN ('phone_screen', 'technical',
         'final_interview', 'offer') THEN 1 ELSE 0 END) AS responded,
    ROUND(
        100.0 * SUM(CASE WHEN status IN ('phone_screen', 'technical',
             'final_interview', 'offer') THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS response_rate_pct
FROM jobs
WHERE status NOT IN ('discovered', 'scored', 'saved');
```

### Enhanced Analytics Query: Time-in-Stage Using Window Functions
```sql
-- Source: SQLite window functions docs (supported since 3.25.0, confirmed 3.51.2)
-- Average time spent in each stage before moving to the next
SELECT
    old_value AS stage,
    ROUND(AVG(duration_days), 1) AS avg_days,
    COUNT(*) AS transitions
FROM (
    SELECT
        old_value,
        new_value,
        created_at,
        ROUND(
            julianday(created_at) -
            julianday(LAG(created_at) OVER (
                PARTITION BY dedup_key
                ORDER BY created_at
            )),
            2
        ) AS duration_days
    FROM activity_log
    WHERE event_type = 'status_change'
) sub
WHERE duration_days IS NOT NULL
  AND duration_days > 0
GROUP BY old_value
ORDER BY avg_days DESC;
```

### Enhanced Analytics Query: Status Funnel
```sql
-- Conversion funnel: how many jobs reach each stage
SELECT
    status,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs), 1) AS pct_of_total
FROM jobs
GROUP BY status
ORDER BY CASE status
    WHEN 'discovered' THEN 1
    WHEN 'scored' THEN 2
    WHEN 'saved' THEN 3
    WHEN 'applied' THEN 4
    WHEN 'phone_screen' THEN 5
    WHEN 'technical' THEN 6
    WHEN 'final_interview' THEN 7
    WHEN 'offer' THEN 8
    WHEN 'rejected' THEN 9
    WHEN 'withdrawn' THEN 10
    WHEN 'ghosted' THEN 11
END;
```

### Complete get_enhanced_stats() Function
```python
# Source: combining verified SQL patterns above
def get_enhanced_stats() -> dict:
    """Return analytics data for the dashboard."""
    with get_conn() as conn:
        # Basic stats (existing)
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        # Jobs per day (last 30 days)
        jobs_per_day = [
            {"date": row[0], "count": row[1]}
            for row in conn.execute("""
                SELECT strftime('%Y-%m-%d', created_at) AS date, COUNT(*) AS count
                FROM jobs
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY strftime('%Y-%m-%d', created_at)
                ORDER BY date
            """).fetchall()
        ]

        # Platform effectiveness
        by_platform = [
            {"name": row[0], "total": row[1], "high_quality": row[2],
             "avg_score": row[3], "actioned": row[4]}
            for row in conn.execute("""
                SELECT platform, COUNT(*) AS total,
                       SUM(CASE WHEN score >= 4 THEN 1 ELSE 0 END) AS high_quality,
                       ROUND(AVG(score), 1) AS avg_score,
                       SUM(CASE WHEN status IN ('applied','phone_screen','technical',
                            'final_interview','offer') THEN 1 ELSE 0 END) AS actioned
                FROM jobs GROUP BY platform
            """).fetchall()
        ]

        # Response rate
        resp_row = conn.execute("""
            SELECT COUNT(*) AS total_applied,
                   SUM(CASE WHEN status IN ('phone_screen','technical',
                        'final_interview','offer') THEN 1 ELSE 0 END) AS responded
            FROM jobs
            WHERE status NOT IN ('discovered','scored','saved')
        """).fetchone()
        response_rate = {
            "total_applied": resp_row[0],
            "responded": resp_row[1],
            "rate_pct": round(100.0 * resp_row[1] / resp_row[0], 1)
                        if resp_row[0] > 0 else 0
        }

        # Time-in-stage
        time_in_stage = [
            {"stage": row[0], "avg_days": row[1], "transitions": row[2]}
            for row in conn.execute("""
                SELECT old_value AS stage,
                       ROUND(AVG(duration_days), 1) AS avg_days,
                       COUNT(*) AS transitions
                FROM (
                    SELECT old_value, new_value, created_at,
                           ROUND(julianday(created_at) - julianday(
                               LAG(created_at) OVER (
                                   PARTITION BY dedup_key ORDER BY created_at
                               )
                           ), 2) AS duration_days
                    FROM activity_log
                    WHERE event_type = 'status_change'
                ) sub
                WHERE duration_days IS NOT NULL AND duration_days > 0
                GROUP BY old_value
                ORDER BY avg_days DESC
            """).fetchall()
        ]

        # Status funnel
        status_funnel = [
            {"status": row[0], "count": row[1], "pct": row[2]}
            for row in conn.execute("""
                SELECT status, COUNT(*) AS count,
                       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs), 1)
                FROM jobs GROUP BY status
                ORDER BY CASE status
                    WHEN 'discovered' THEN 1 WHEN 'scored' THEN 2
                    WHEN 'saved' THEN 3 WHEN 'applied' THEN 4
                    WHEN 'phone_screen' THEN 5 WHEN 'technical' THEN 6
                    WHEN 'final_interview' THEN 7 WHEN 'offer' THEN 8
                    WHEN 'rejected' THEN 9 WHEN 'withdrawn' THEN 10
                    WHEN 'ghosted' THEN 11
                END
            """).fetchall()
        ]

    return {
        "total": total,
        "jobs_per_day": jobs_per_day,
        "by_platform": by_platform,
        "response_rate": response_rate,
        "time_in_stage": time_in_stage,
        "status_funnel": status_funnel,
    }
```

### Kanban Board Endpoint
```python
@app.get("/kanban", response_class=HTMLResponse)
async def kanban_view(request: Request):
    # Only show user-managed statuses (not discovered/scored)
    kanban_statuses = [
        "saved", "applied", "phone_screen", "technical",
        "final_interview", "offer", "rejected", "withdrawn", "ghosted"
    ]
    columns = {}
    for status in kanban_statuses:
        columns[status] = db.get_jobs(status=status, sort_by="score", sort_dir="desc")
    stats = db.get_stats()
    return templates.TemplateResponse(
        "kanban.html",
        {
            "request": request,
            "kanban_statuses": kanban_statuses,
            "columns": columns,
            "stats": stats,
            "statuses": STATUSES,
        },
    )
```

### SortableJS Initialization with Error Handling
```javascript
// Source: SortableJS docs + htmx.ajax() API
document.querySelectorAll('.kanban-list').forEach(list => {
    new Sortable(list, {
        group: 'kanban',
        animation: 150,
        ghostClass: 'opacity-30',
        dragClass: 'shadow-lg',
        forceFallback: true,  // Use fallback DnD for consistent behavior
        onEnd: async function(evt) {
            const dedupKey = evt.item.dataset.key;
            const newStatus = evt.to.dataset.status;
            const oldStatus = evt.from.dataset.status;

            if (newStatus === oldStatus) return;

            try {
                // Update column counts in header
                updateColumnCount(oldStatus, -1);
                updateColumnCount(newStatus, 1);

                // Persist to server
                await htmx.ajax('POST',
                    `/jobs/${encodeURIComponent(dedupKey)}/status`,
                    { values: { status: newStatus } }
                );
            } catch (err) {
                // Rollback: move card back to original column
                evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex]);
                updateColumnCount(oldStatus, 1);
                updateColumnCount(newStatus, -1);
                console.error('Status update failed:', err);
            }
        }
    });
});

function updateColumnCount(status, delta) {
    const header = document.querySelector(
        `.kanban-column[data-status="${status}"] .col-count`
    );
    if (header) {
        header.textContent = parseInt(header.textContent) + delta;
    }
}
```

### Chart Initialization with Destroy Guard
```javascript
// Source: Chart.js update docs
const chartInstances = {};

function createOrUpdateChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    // Destroy existing instance to prevent duplicates
    const existing = Chart.getChart(canvas);
    if (existing) {
        existing.destroy();
    }

    const chart = new Chart(canvas, config);
    chartInstances[canvasId] = chart;
    return chart;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLite without window functions | Window functions (LAG, LEAD, OVER) | SQLite 3.25.0 (2018) | Enables time-in-stage in single query |
| Chart.js v2/v3 | Chart.js v4.5.1 | 2023 | Tree-shakeable, ESM support, auto-registration |
| jQuery UI Sortable | SortableJS 1.15.6 | 2020+ | No jQuery dependency, touch support, better API |
| Full-page reload for chart updates | htmx HX-Trigger + event-driven updates | htmx 2.0 | Declarative, no custom event bus needed |
| Custom drag-and-drop with HTML5 DnD API | SortableJS with `group` option | N/A | 90% less code, touch support included |

**Deprecated/outdated:**
- Chart.js v2 CDN URL format (`Chart.min.js`) is different from v4 (`chart.umd.min.js`)
- SortableJS older API used `Sortable.create()` -- current API uses `new Sortable(el, options)`
- htmx 1.x used `hx-trigger="click"` patterns -- htmx 2.0.4 has no breaking changes for patterns used here

## Open Questions

1. **Should the kanban board show all 9 user statuses or a subset?**
   - What we know: The status list has 9 user-facing statuses. Rejected/withdrawn/ghosted are terminal states.
   - What is unclear: Whether having 9 columns is too wide for a single screen (especially on laptops).
   - Recommendation: Show all 9 but use horizontal scrolling. Group terminal statuses (rejected/withdrawn/ghosted) visually with a divider or muted styling. The user can scroll right to see them.

2. **Should charts use polling or only event-driven updates?**
   - What we know: HX-Trigger event-driven updates are cleaner. Polling (`every 30s`) would catch external pipeline runs.
   - What is unclear: Whether the user would run a pipeline while viewing the analytics page.
   - Recommendation: Use event-driven updates for kanban drag actions. Add a manual "Refresh" button on the analytics page. Do not poll -- this is a local tool, not a shared dashboard.

3. **What chart types best represent each metric?**
   - What we know: Chart.js supports bar, line, doughnut, pie, radar, polar area.
   - Recommendation based on data types:
     - Jobs per day/week: **Bar chart** (discrete time periods)
     - Platform effectiveness: **Doughnut chart** (proportional comparison)
     - Status funnel: **Horizontal bar chart** (ordered stages)
     - Response rate: **Single number with progress ring** (could be a small doughnut or just a big number)
     - Time-in-stage: **Horizontal bar chart** (compare durations)

## Sources

### Primary (HIGH confidence)
- [Chart.js 4.5.1 Official Docs](https://www.chartjs.org/docs/latest/) - CDN installation, update pattern, chart types, `chart.update()` API
- [Chart.js Updating Charts](https://www.chartjs.org/docs/latest/developers/updates.html) - Data mutation pattern, `update('none')` for skip animation
- [SortableJS GitHub](https://github.com/SortableJS/Sortable) - `onEnd` callback, `group` option, event properties (`evt.to`, `evt.from`, `evt.item`)
- [htmx Sortable Example](https://htmx.org/examples/sortable/) - Integration pattern for drag-and-drop with htmx triggers
- [htmx HX-Trigger Headers](https://htmx.org/headers/hx-trigger/) - Event-driven cross-component updates, `from:body` modifier
- [htmx Update Other Content](https://htmx.org/examples/update-other-content/) - OOB swap and event-driven patterns
- [SQLite Window Functions](https://sqlite.org/windowfunctions.html) - LAG, LEAD, OVER, PARTITION BY (available since 3.25.0)
- [SQLite Date/Time Functions](https://sqlite.org/lang_datefunc.html) - `julianday()`, `strftime()`, date arithmetic
- Local system verification: SQLite 3.51.2 confirmed (window functions work)
- [jsDelivr Chart.js](https://www.jsdelivr.com/package/npm/chart.js) - CDN URL verified: `chart.js@4.5.1/dist/chart.umd.min.js`
- [jsDelivr SortableJS](https://www.jsdelivr.com/package/npm/sortablejs) - CDN URL verified: `sortablejs@1.15.6/Sortable.min.js`

### Secondary (MEDIUM confidence)
- [MDN Kanban Board with Drag and Drop](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/Kanban_board) - HTML structure patterns for kanban columns
- [htmx nested SortableJS issue #1192](https://github.com/bigskysoftware/htmx/issues/1192) - Cross-list drag with `htmx.ajax()` pattern, `evt.pullMode` for detecting cross-list drags
- [SQLite date difference patterns](https://learnsql.com/cookbook/how-to-calculate-the-difference-between-two-timestamps-in-sqlite/) - `julianday()` subtraction for time intervals

### Tertiary (LOW confidence)
- None. All critical findings verified against official documentation or local system.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Chart.js and SortableJS are well-established, CDN URLs verified on jsDelivr
- Architecture (analytics queries): HIGH - SQLite window functions verified locally (`sqlite3.sqlite_version` = 3.51.2), query patterns tested against official docs
- Architecture (kanban DnD): HIGH - SortableJS `group` option and `onEnd` callback well-documented, htmx.ajax() pattern confirmed in htmx issue #1192
- Architecture (htmx integration): HIGH - HX-Trigger pattern is official htmx docs, `from:body` modifier verified
- Pitfalls: HIGH - Derived from Chart.js update docs (destroy guard), SortableJS event model, and actual codebase analysis (existing activity_log schema)

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (stable libraries, no fast-moving dependencies)
