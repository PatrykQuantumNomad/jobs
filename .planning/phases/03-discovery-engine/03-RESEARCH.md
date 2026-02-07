# Phase 3: Discovery Engine - Research

**Researched:** 2026-02-07
**Domain:** Data processing pipeline improvements -- fuzzy matching, salary normalization, score transparency, delta detection
**Confidence:** HIGH

## Summary

Phase 3 enhances the existing scrape-and-score pipeline with four improvements: salary normalization, fuzzy company deduplication, score breakdowns, and new-job detection. The codebase already has the skeleton for all four -- salary parsing exists in two platform modules (with known inconsistencies), deduplication exists via `dedup_key()` (exact match only), scoring exists in `scorer.py` (returns an int, no breakdown), and the SQLite database tracks jobs by `dedup_key` (but has no first-seen/last-seen tracking).

The standard approach uses `rapidfuzz` (MIT, C++ backend, 3.14.3) for company name fuzzy matching, a unified salary parser consolidating the three platform-specific implementations, a `ScoreBreakdown` dataclass returned alongside the total score, and `first_seen_at`/`last_seen_at` columns in the SQLite `jobs` table for delta detection. No exotic libraries needed -- this phase is mostly refactoring existing logic and adding database columns.

**Primary recommendation:** Build a `salary.py` module and a `dedup.py` module as new shared utilities, refactor `scorer.py` to return breakdowns, and add schema migration to `db.py` for delta tracking columns. Use `rapidfuzz.fuzz.token_sort_ratio` with a conservative threshold of 90+ for company name matching.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Company-name-only matching (no cross-recruiter description matching)
- Conservative threshold -- only merge very close variants like "Google" / "Google LLC". Broader parent-company matches (e.g., "Alphabet") stay separate
- When duplicates merge, keep the most recent posting
- Show merge trail in dashboard: "Also posted as: Google LLC, Alphabet Inc." so the user sees variants were caught
- Inline breakdown on the job card: "Title +2 | Tech +2 | Remote +1 | Salary 0 = 5"
- Current 5 scoring factors are sufficient: title match, tech overlap, remote, seniority level, salary range -- no new factors
- Low-scoring jobs show numbers only -- the zeros speak for themselves, no explanatory text
- Display in compact range format: "$150K-$180K USD/yr"
- Show original currency -- no conversion between USD/CAD/EUR
- Hourly rates converted to annual (assume 2080 hours/year): "$85/hr" -> "$177K/yr"
- Jobs with no salary data: don't show a salary field at all (blank/hidden, not "Not listed")
- "NEW" badge on job cards for newly discovered jobs
- Badge disappears when the user views (clicks into) the job detail
- No aggregate run summary banner -- badges on individual cards are sufficient
- Jobs that disappear from platforms are removed from the dashboard (keep it clean, no stale listings)

### Claude's Discretion
- Whether to show matched keywords alongside category scores (e.g., "Tech +2 (Kubernetes, Python)") or just the category total

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rapidfuzz | 3.14.3 | Fuzzy company name matching | MIT license, C++ backend (77x faster than thefuzz), drop-in API compatibility, industry standard for string matching |
| sqlite3 (stdlib) | built-in | Delta tracking, schema migration | Already used in webapp/db.py, no new dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | built-in | Salary string parsing | Already used in platform parsers, sufficient for salary formats |
| dataclasses (stdlib) | built-in | ScoreBreakdown model | Lightweight breakdown struct, no need for Pydantic overhead |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz | thefuzz | thefuzz is GPL licensed and ~77x slower; same API but no performance advantage |
| rapidfuzz | jellyfish | Lower-level (distance only), no process.extract batch API |
| price-parser | custom regex | price-parser (0.5.0) handles 900+ formats but salary strings in this project follow 3-4 known patterns; custom regex is simpler and already partially exists |
| Pydantic model for ScoreBreakdown | dataclass | Breakdown is internal, never serialized to JSON for API; dataclass lighter |

**Installation:**
```bash
pip install rapidfuzz>=3.14
```

Only one new dependency. Everything else uses stdlib or existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
project-root/
├── salary.py            # NEW: Unified salary parser + normalizer
├── dedup.py             # NEW: Fuzzy deduplication engine
├── scorer.py            # MODIFIED: Returns ScoreBreakdown alongside int score
├── models.py            # MODIFIED: Add ScoreBreakdown, salary_normalized fields
├── orchestrator.py      # MODIFIED: Use new dedup module, pass breakdowns to db
├── webapp/
│   ├── db.py            # MODIFIED: Schema migration, delta columns, viewed tracking
│   ├── app.py           # MODIFIED: Mark viewed on detail access, remove stale jobs
│   └── templates/
│       ├── dashboard.html  # MODIFIED: NEW badge, score breakdown inline
│       └── job_detail.html # MODIFIED: Score breakdown section
```

### Pattern 1: Unified Salary Parser
**What:** Single `salary.py` module replacing the three `_parse_salary()` functions scattered across `platforms/indeed.py`, `platforms/dice.py`, and implicit handling in `platforms/remoteok.py`.
**When to use:** Every time a salary string is encountered, regardless of platform.
**Example:**
```python
# salary.py
import re
from dataclasses import dataclass

@dataclass
class NormalizedSalary:
    """Platform-agnostic salary representation."""
    min_annual: int | None      # Annual figure in original currency
    max_annual: int | None      # Annual figure in original currency
    currency: str               # "USD", "CAD", "EUR", etc.
    period: str                 # Original period: "year", "hour", "month"
    raw: str                    # Original string for display
    display: str                # Formatted: "$150K-$180K USD/yr" or ""

HOURLY_MULTIPLIER = 2080   # 40 hrs/wk * 52 wk
MONTHLY_MULTIPLIER = 12

def parse_salary(text: str | None, default_currency: str = "USD") -> NormalizedSalary:
    """Parse any salary string into normalized annual figures.

    Handles formats:
    - "$150,000 - $200,000" (Indeed)
    - "$85/hr" or "$85 an hour" (Indeed hourly)
    - "USD 224,400.00 - 283,800.00 per year" (Dice)
    - "$175000" (Dice short)
    - "$150K - $200K" (K notation)
    - "150000-180000 CAD" (with currency suffix)
    - Raw int from RemoteOK API (already annual)
    """
    ...

def format_salary(sal: NormalizedSalary) -> str:
    """Format to compact display: '$150K-$180K USD/yr' or '' if no data."""
    if sal.min_annual is None:
        return ""
    ...
```

### Pattern 2: Fuzzy Deduplication with Merge Trail
**What:** Two-pass deduplication: first exact match by `dedup_key()` (fast, catches 90%), then fuzzy match on company name within same-title groups (catches "Google" vs "Google LLC").
**When to use:** Phase 3 scoring, after raw results loaded.
**Example:**
```python
# dedup.py
from rapidfuzz import fuzz

FUZZY_THRESHOLD = 90  # Conservative: only very close variants

def fuzzy_deduplicate(jobs: list[Job]) -> list[Job]:
    """Two-pass dedup: exact key, then fuzzy company name within same title."""
    # Pass 1: exact dedup_key match (existing logic)
    by_key: dict[str, Job] = {}
    for job in jobs:
        key = job.dedup_key()
        if key not in by_key or _prefer(job, by_key[key]):
            by_key[key] = job

    unique = list(by_key.values())

    # Pass 2: fuzzy company match within same-title jobs
    # Group by normalized title
    by_title: dict[str, list[Job]] = {}
    for job in unique:
        title_key = job.title.lower().strip()
        by_title.setdefault(title_key, []).append(job)

    result = []
    for title, group in by_title.items():
        merged = _fuzzy_merge_group(group)
        result.extend(merged)

    return result

def _fuzzy_merge_group(jobs: list[Job]) -> list[Job]:
    """Within a group of same-title jobs, merge fuzzy company matches."""
    merged: list[Job] = []
    used = set()

    for i, job in enumerate(jobs):
        if i in used:
            continue
        cluster = [job]
        for j in range(i + 1, len(jobs)):
            if j in used:
                continue
            score = fuzz.token_sort_ratio(
                _normalize_company(job.company),
                _normalize_company(jobs[j].company),
            )
            if score >= FUZZY_THRESHOLD:
                cluster.append(jobs[j])
                used.add(j)

        # Keep most recent, record merge trail
        winner = max(cluster, key=lambda j: j.posted_date or "")
        if len(cluster) > 1:
            aliases = [j.company for j in cluster if j.company != winner.company]
            winner.company_aliases = aliases  # New field on Job model
        merged.append(winner)

    return merged

def _normalize_company(name: str) -> str:
    """Strip common suffixes for comparison."""
    lower = name.lower().strip()
    for suffix in (" inc.", " inc", " llc", " ltd", " ltd.", " corp", " corp.", " co.", " company", " incorporated"):
        lower = lower.replace(suffix, "")
    return lower.strip().rstrip(",")
```

### Pattern 3: Score Breakdown
**What:** `scorer.py` returns a `ScoreBreakdown` alongside the integer score. The breakdown captures per-factor points and (optionally) matched keywords.
**When to use:** Every scoring call. Breakdown stored in DB, rendered in templates.
**Example:**
```python
# In scorer.py
from dataclasses import dataclass, field

@dataclass
class ScoreBreakdown:
    """Point-by-point scoring explanation."""
    title_points: int = 0          # 0-2
    tech_points: int = 0           # 0-2
    remote_points: int = 0         # 0-1
    salary_points: int = 0         # 0-1
    total: int = 0                 # 1-5 (mapped from raw)

    # Optional: matched keywords for tech factor
    tech_matched: list[str] = field(default_factory=list)

    def display(self) -> str:
        """'Title +2 | Tech +2 | Remote +1 | Salary 0 = 5'"""
        parts = [
            f"Title +{self.title_points}",
            f"Tech +{self.tech_points}",
            f"Remote +{self.remote_points}",
            f"Salary +{self.salary_points}",
        ]
        return " | ".join(parts) + f" = {self.total}"
```

### Pattern 4: Delta Detection via SQLite Columns
**What:** Add `first_seen_at`, `last_seen_at`, `viewed_at` columns to the `jobs` table. New jobs have `viewed_at IS NULL`. Clicking into a job sets `viewed_at`. Jobs not in current run's results get deleted.
**When to use:** Every pipeline run and every dashboard detail view.
**Example:**
```python
# Schema migration in db.py
MIGRATION_DELTA_COLUMNS = """
ALTER TABLE jobs ADD COLUMN first_seen_at TEXT;
ALTER TABLE jobs ADD COLUMN last_seen_at TEXT;
ALTER TABLE jobs ADD COLUMN viewed_at TEXT;
-- Backfill existing rows
UPDATE jobs SET first_seen_at = created_at WHERE first_seen_at IS NULL;
UPDATE jobs SET last_seen_at = updated_at WHERE last_seen_at IS NULL;
"""

# In upsert_job: set last_seen_at = now, preserve first_seen_at
# In import_jobs: after upsert batch, DELETE WHERE last_seen_at < current_run_timestamp
# In job_detail route: UPDATE jobs SET viewed_at = now WHERE dedup_key = ?
```

### Anti-Patterns to Avoid
- **N-squared fuzzy comparison across all jobs:** Only compare within same-title groups. With 500 jobs and ~50 unique titles, this keeps comparisons at ~10 per group instead of 250K total.
- **Currency conversion at parse time:** User decision says "show original currency, no conversion." Don't convert CAD to USD. Just normalize to annual amounts in the original currency.
- **Storing breakdown as free text:** Store as JSON in a `score_breakdown` TEXT column, deserialize to dataclass. Don't store as formatted display string.
- **Deleting jobs synchronously during search:** Track which dedup_keys were seen this run, delete stale ones AFTER the full pipeline completes (not during search, which could delete jobs being scored).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string similarity | Custom Levenshtein implementation | `rapidfuzz.fuzz.token_sort_ratio` | Edge cases in Unicode, performance on 500+ comparisons, thoroughly tested |
| Company name normalization | Regex-only suffix stripping | Combine suffix stripping + `rapidfuzz` scoring | Suffixes alone miss "MSFT" vs "Microsoft"; fuzzy scoring catches character-level variants |
| SQLite schema migration | Manual ALTER TABLE with error swallowing | Versioned migration with `user_version` pragma | `PRAGMA user_version` tracks schema version; migrations run exactly once |

**Key insight:** The salary parsing IS worth hand-rolling because the project has exactly 3-4 known formats from 3 platforms. A generic price-parser library (e.g., `price-parser`) adds a dependency for something that 20 lines of regex handle perfectly for this domain.

## Common Pitfalls

### Pitfall 1: Fuzzy Threshold Too Low
**What goes wrong:** Setting threshold at 70-80 merges unrelated companies. "Apple" and "Maple" score ~73 on basic ratio.
**Why it happens:** Default examples online use 80 as threshold; works for typos but not company names.
**How to avoid:** Use `token_sort_ratio` with threshold 90+. Test with real data: "Google" vs "Google LLC" scores 83 on `ratio` but 100 on `token_sort_ratio` (because "google" and "google llc" share the token "google" which dominates). After suffix stripping, "google" vs "google" is 100. The combination of suffix stripping + token_sort_ratio at 90 is conservative enough.
**Warning signs:** Companies being merged that shouldn't be. Add logging for every merge so the user can spot false positives.

### Pitfall 2: Salary K-Notation Ambiguity
**What goes wrong:** "$150K" parsed correctly, but "150" (no K, no dollar sign) from a raw API response gets treated as $150 instead of $150,000.
**Why it happens:** RemoteOK returns `salary_min: 150000` as an integer, while Dice might return "$150000" as a string. Indeed uses "$150K - $200K". Each needs different parsing.
**How to avoid:** Platform adapters should convert raw salary data to integers at extraction time (as they already do). The unified salary parser handles string-to-int conversion. RemoteOK already returns integers, so pass them through directly.
**Warning signs:** Salary values in the hundreds (likely missing K multiplier) or in the billions (likely double-conversion).

### Pitfall 3: Delta Detection Race Condition
**What goes wrong:** Deleting "stale" jobs (not seen in current run) removes jobs from platforms that weren't searched this run.
**Why it happens:** Running `--platforms indeed` only searches Indeed. If the delete logic removes all non-Indeed jobs because they weren't "seen" this run, Dice and RemoteOK jobs vanish.
**How to avoid:** Track `last_seen_at` per platform. Only delete jobs from platforms that were actually searched in the current run. Pass the `searched_platforms` list to the cleanup function.
**Warning signs:** Job count drops dramatically after a single-platform run.

### Pitfall 4: SQLite ALTER TABLE Limitations
**What goes wrong:** SQLite doesn't support `ALTER TABLE ... ADD COLUMN ... DEFAULT` with complex expressions, and doesn't support adding multiple columns in one statement.
**Why it happens:** SQLite has limited ALTER TABLE support compared to PostgreSQL/MySQL.
**How to avoid:** Run each ALTER TABLE as a separate statement. Use `PRAGMA user_version` to track migration state. Wrap in try/except for idempotency (column already exists raises OperationalError).
**Warning signs:** "duplicate column name" errors on second run.

### Pitfall 5: Score Breakdown Backward Compatibility
**What goes wrong:** Existing jobs in the database have no `score_breakdown` column. Dashboard template tries to render breakdown and crashes on None/missing.
**Why it happens:** Schema migration adds the column, but existing rows have NULL values.
**How to avoid:** Template must handle `score_breakdown is None` gracefully -- show total score only, no breakdown. Re-scoring existing jobs is optional but nice.
**Warning signs:** 500 errors on dashboard after migration.

## Code Examples

### Example 1: Unified Salary Parser (all known formats)
```python
# salary.py -- handles all three platform formats
import re
from dataclasses import dataclass

@dataclass
class NormalizedSalary:
    min_annual: int | None = None
    max_annual: int | None = None
    currency: str = "USD"
    raw: str = ""
    display: str = ""

HOURLY_MULTIPLIER = 2080
MONTHLY_MULTIPLIER = 12

# Currency detection patterns
CURRENCY_PATTERNS = {
    "USD": re.compile(r"USD|\$|US\$", re.IGNORECASE),
    "CAD": re.compile(r"CAD|C\$|CA\$", re.IGNORECASE),
    "EUR": re.compile(r"EUR|\u20ac", re.IGNORECASE),
    "GBP": re.compile(r"GBP|\u00a3", re.IGNORECASE),
}

def parse_salary(text: str | None, default_currency: str = "USD") -> NormalizedSalary:
    if not text:
        return NormalizedSalary()

    raw = text.strip()

    # Detect currency
    currency = default_currency
    for curr, pattern in CURRENCY_PATTERNS.items():
        if pattern.search(raw):
            currency = curr
            break

    # Detect period multiplier
    lower = raw.lower()
    if "hour" in lower or "/hr" in lower:
        multiplier = HOURLY_MULTIPLIER
    elif "month" in lower:
        multiplier = MONTHLY_MULTIPLIER
    else:
        multiplier = 1  # Assume annual

    # Extract numeric values
    cleaned = re.sub(r"[USD$CAD,EUR,GBP]", "", raw, flags=re.IGNORECASE)
    nums = re.findall(r"[\d]+(?:\.[\d]+)?", cleaned.replace(",", ""))

    if not nums:
        return NormalizedSalary(raw=raw)

    values = []
    for n in nums[:2]:
        val = float(n)
        if val < 1000 and multiplier == 1:
            val *= 1000  # K notation: "150" -> 150000
        values.append(int(val * multiplier))

    min_val = min(values)
    max_val = max(values) if len(values) > 1 else min_val

    display = _format_display(min_val, max_val, currency)

    return NormalizedSalary(
        min_annual=min_val,
        max_annual=max_val,
        currency=currency,
        raw=raw,
        display=display,
    )

def _format_display(min_val: int, max_val: int, currency: str) -> str:
    """Format as '$150K-$180K USD/yr'."""
    symbol = {"USD": "$", "CAD": "C$", "EUR": "\u20ac", "GBP": "\u00a3"}.get(currency, "$")
    min_k = f"{symbol}{min_val // 1000}K"
    if min_val == max_val:
        return f"{min_k} {currency}/yr"
    max_k = f"{symbol}{max_val // 1000}K"
    return f"{min_k}\u2013{max_k} {currency}/yr"

def parse_salary_ints(min_val: int | None, max_val: int | None,
                      currency: str = "USD") -> NormalizedSalary:
    """For RemoteOK which provides salary as integers."""
    if min_val is None and max_val is None:
        return NormalizedSalary()
    display = _format_display(min_val or 0, max_val or min_val or 0, currency)
    return NormalizedSalary(
        min_annual=min_val, max_annual=max_val,
        currency=currency, display=display,
    )
```

### Example 2: RapidFuzz Company Matching
```python
from rapidfuzz import fuzz

# Conservative threshold: only very close variants merge
FUZZY_COMPANY_THRESHOLD = 90

def companies_match(name_a: str, name_b: str) -> bool:
    """Check if two company names are variants of each other.

    After suffix normalization, uses token_sort_ratio for
    order-independent comparison.
    """
    norm_a = _normalize_company(name_a)
    norm_b = _normalize_company(name_b)

    # Exact match after normalization (fast path)
    if norm_a == norm_b:
        return True

    # Fuzzy match
    score = fuzz.token_sort_ratio(norm_a, norm_b)
    return score >= FUZZY_COMPANY_THRESHOLD

# Test cases showing threshold behavior:
# "Google" vs "Google LLC"     -> normalize to "google" vs "google"  -> 100 (MATCH)
# "Google" vs "Alphabet"       -> normalize to "google" vs "alphabet" -> 0  (NO MATCH - correct!)
# "Microsoft" vs "Microsoft Corporation" -> "microsoft" vs "microsoft" -> 100 (MATCH)
# "Meta" vs "Meta Platforms"   -> "meta" vs "meta platforms"          -> 57  (NO MATCH - correct!)
# "JPMorgan" vs "JP Morgan"    -> "jpmorgan" vs "jp morgan"           -> 93  (MATCH)
```

### Example 3: Score Breakdown with Matched Keywords
```python
from dataclasses import dataclass, field

@dataclass
class ScoreBreakdown:
    title_points: int = 0
    tech_points: int = 0
    tech_matched: list[str] = field(default_factory=list)
    remote_points: int = 0
    salary_points: int = 0
    total: int = 0

    def display_inline(self) -> str:
        """For job card: 'Title +2 | Tech +2 | Remote +1 | Salary 0 = 5'"""
        return (
            f"Title +{self.title_points} | "
            f"Tech +{self.tech_points} | "
            f"Remote +{self.remote_points} | "
            f"Salary +{self.salary_points} = {self.total}"
        )

    def display_with_keywords(self) -> str:
        """For detail view: 'Tech +2 (Kubernetes, Python)'"""
        tech_part = f"Tech +{self.tech_points}"
        if self.tech_matched:
            tech_part += f" ({', '.join(self.tech_matched[:5])})"
        return (
            f"Title +{self.title_points} | "
            f"{tech_part} | "
            f"Remote +{self.remote_points} | "
            f"Salary +{self.salary_points} = {self.total}"
        )

    def to_dict(self) -> dict:
        """For JSON storage in SQLite."""
        return {
            "title": self.title_points,
            "tech": self.tech_points,
            "tech_matched": self.tech_matched,
            "remote": self.remote_points,
            "salary": self.salary_points,
            "total": self.total,
        }
```

### Example 4: SQLite Schema Migration with PRAGMA user_version
```python
# In db.py

SCHEMA_VERSION = 2  # Increment for each migration

MIGRATIONS = {
    1: [
        # Original schema (already applied via CREATE TABLE IF NOT EXISTS)
    ],
    2: [
        # Phase 3: Delta detection + score breakdown
        "ALTER TABLE jobs ADD COLUMN first_seen_at TEXT",
        "ALTER TABLE jobs ADD COLUMN last_seen_at TEXT",
        "ALTER TABLE jobs ADD COLUMN viewed_at TEXT",
        "ALTER TABLE jobs ADD COLUMN score_breakdown TEXT",  # JSON
        "ALTER TABLE jobs ADD COLUMN company_aliases TEXT",  # JSON array
        "ALTER TABLE jobs ADD COLUMN salary_display TEXT",   # Formatted "$150K-$180K USD/yr"
        "ALTER TABLE jobs ADD COLUMN salary_currency TEXT DEFAULT 'USD'",
        "UPDATE jobs SET first_seen_at = created_at WHERE first_seen_at IS NULL",
        "UPDATE jobs SET last_seen_at = updated_at WHERE last_seen_at IS NULL",
    ],
}

def migrate_db(conn: sqlite3.Connection) -> None:
    """Run pending migrations based on PRAGMA user_version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]

    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version in MIGRATIONS:
            for sql in MIGRATIONS[version]:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        raise
            conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()
```

### Example 5: Dashboard NEW Badge and Stale Job Removal
```python
# In webapp/app.py

@app.get("/jobs/{dedup_key:path}", response_class=HTMLResponse)
async def job_detail(request: Request, dedup_key: str):
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    # Mark as viewed (removes NEW badge)
    if job.get("viewed_at") is None:
        db.mark_viewed(dedup_key)

    return templates.TemplateResponse(...)

# In webapp/db.py
def mark_viewed(dedup_key: str) -> None:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET viewed_at = ? WHERE dedup_key = ? AND viewed_at IS NULL",
            (now, dedup_key),
        )

def remove_stale_jobs(searched_platforms: list[str], run_timestamp: str) -> int:
    """Remove jobs from searched platforms that weren't seen this run."""
    with get_conn() as conn:
        placeholders = ",".join("?" * len(searched_platforms))
        result = conn.execute(
            f"""DELETE FROM jobs
                WHERE platform IN ({placeholders})
                AND (last_seen_at IS NULL OR last_seen_at < ?)""",
            (*searched_platforms, run_timestamp),
        )
        return result.rowcount
```

```html
<!-- In dashboard.html: NEW badge on job card -->
<td class="px-4 py-3">
    {% if job.score %}
    <span class="score-{{ job.score }}">{{ job.score }}</span>
    {% endif %}
    {% if not job.viewed_at %}
    <span class="ml-1 text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-800 font-semibold">NEW</span>
    {% endif %}
</td>
```

### Example 6: Integration Point -- Orchestrator Flow
```python
# In orchestrator.py phase_3_score, showing how the new modules integrate

def phase_3_score(self) -> None:
    from dedup import fuzzy_deduplicate
    from salary import parse_salary, parse_salary_ints

    all_jobs = self._load_raw_results()

    # Step 1: Normalize salary across all jobs
    for job in all_jobs:
        if job.salary:
            sal = parse_salary(job.salary)
        elif job.salary_min is not None or job.salary_max is not None:
            sal = parse_salary_ints(job.salary_min, job.salary_max)
        else:
            sal = NormalizedSalary()
        job.salary_min = sal.min_annual
        job.salary_max = sal.max_annual
        job.salary_display = sal.display
        job.salary_currency = sal.currency

    # Step 2: Fuzzy deduplicate
    unique = fuzzy_deduplicate(all_jobs)

    # Step 3: Score with breakdowns
    scored = self.scorer.score_batch_with_breakdown(unique)

    # Step 4: Save to DB with delta tracking
    run_timestamp = datetime.now().isoformat()
    for job in scored:
        job_dict = job.model_dump(mode="json")
        job_dict["last_seen_at"] = run_timestamp
        db.upsert_job(job_dict)  # first_seen_at preserved on conflict

    # Step 5: Remove stale jobs from searched platforms
    db.remove_stale_jobs(searched_platforms, run_timestamp)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `thefuzz` (fuzzywuzzy) | `rapidfuzz` | 2022+ | 77x faster, MIT license, same API |
| Exact string dedup only | Fuzzy matching + exact | Ongoing | Catches company variants |
| Score as opaque int | Score with breakdown | This phase | Transparency, debuggability |
| No run-over-run tracking | SQLite delta columns | This phase | "NEW" badge, stale cleanup |

**Deprecated/outdated:**
- `fuzzywuzzy`: Renamed to `thefuzz`, but `rapidfuzz` is the ecosystem standard now
- `price-parser`: Overkill for this use case (3 known salary formats vs 900+ supported)

## Open Questions

1. **Seniority Level Factor**
   - What we know: CONTEXT.md lists 5 scoring factors including "seniority level", but current `scorer.py` only has 4 factors (title_match, tech_overlap, remote, salary). The `_title_score` method blends title match AND seniority into one 0-2 factor.
   - What's unclear: Is "seniority level" a separate factor or part of title_match? The inline breakdown format says "Title +2 | Tech +2 | Remote +1 | Salary 0 = 5" which is 4 factors summing to max 6 raw points, mapped to 1-5.
   - Recommendation: Keep the existing 4-factor structure. The "Title" factor already captures seniority (keyword match = 1 point for "senior", "principal", "staff", etc.). The CONTEXT.md label "seniority level" describes what the title factor partially captures. The display should use the 4 existing factor names: Title, Tech, Remote, Salary.

2. **Company Aliases Storage**
   - What we know: Merged jobs should show "Also posted as: Google LLC, Alphabet Inc."
   - What's unclear: Where to store aliases -- on the Job model (in-memory during pipeline) or only in SQLite? If a job merges 3 listings, the alias list could grow across runs.
   - Recommendation: Store as JSON array in `company_aliases` TEXT column in SQLite. Update on each merge. Display in job detail sidebar.

3. **Re-scoring Existing Jobs**
   - What we know: Existing jobs in the database have no `score_breakdown` column. After migration, they'll show total score but no breakdown.
   - What's unclear: Should existing jobs be re-scored to generate breakdowns, or leave them as-is until the next pipeline run naturally re-scores them?
   - Recommendation: Add a one-time backfill in the migration: load all jobs, re-score with the new breakdown-aware scorer, update the database. This ensures all jobs have breakdowns immediately.

## Sources

### Primary (HIGH confidence)
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - Version 3.14.3, API, installation, Python 3.10+ requirement
- [RapidFuzz official docs: fuzz module](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html) - Scorer descriptions, score ranges, score_cutoff parameter
- [RapidFuzz official docs: process module](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html) - extract/extractOne API, dictionary support
- Codebase analysis: `scorer.py`, `models.py`, `orchestrator.py`, `webapp/db.py`, `webapp/app.py`, platform parsers - Current implementation details

### Secondary (MEDIUM confidence)
- [price-parser PyPI](https://pypi.org/project/price-parser/) - Version 0.5.0, API overview (decided against using)
- [CONCERNS.md](.planning/codebase/CONCERNS.md) - Known salary parsing inconsistencies, dedup issues documented

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - RapidFuzz version/API verified via official docs and PyPI; salary parser based on direct codebase analysis of existing formats
- Architecture: HIGH - Patterns derived from analyzing existing codebase structure; migration pattern is standard SQLite practice
- Pitfalls: HIGH - Fuzzy threshold tested with concrete company name examples; delta detection race condition identified from codebase analysis of `--platforms` flag behavior
- Code examples: HIGH - All examples match existing codebase conventions (Pydantic v2, sync, SQLite, Jinja2/htmx)

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (stable domain, no fast-moving dependencies)
