# Phase 3: Discovery Engine - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

The scrape-and-score loop produces smarter, more transparent results. Fuzzy company matching catches duplicates the current exact-match misses, score breakdowns explain why each job scored what it did, salary data is comparable across platforms, and repeat runs highlight what is new. No new platforms, no dashboard UI overhaul, no scheduling — this phase improves the data processing pipeline.

</domain>

<decisions>
## Implementation Decisions

### Fuzzy matching rules
- Company-name-only matching (no cross-recruiter description matching)
- Conservative threshold — only merge very close variants like "Google" / "Google LLC". Broader parent-company matches (e.g., "Alphabet") stay separate
- When duplicates merge, keep the most recent posting
- Show merge trail in dashboard: "Also posted as: Google LLC, Alphabet Inc." so the user sees variants were caught

### Score transparency
- Inline breakdown on the job card: "Title +2 | Tech +2 | Remote +1 | Salary 0 = 5"
- Current 5 scoring factors are sufficient: title match, tech overlap, remote, seniority level, salary range — no new factors
- Low-scoring jobs show numbers only — the zeros speak for themselves, no explanatory text

### Claude's Discretion (Score transparency)
- Whether to show matched keywords alongside category scores (e.g., "Tech +2 (Kubernetes, Python)") or just the category total

### Salary normalization
- Display in compact range format: "$150K–$180K USD/yr"
- Show original currency — no conversion between USD/CAD/EUR
- Hourly rates converted to annual (assume 2080 hours/year): "$85/hr" → "$177K/yr"
- Jobs with no salary data: don't show a salary field at all (blank/hidden, not "Not listed")

### Delta detection
- "NEW" badge on job cards for newly discovered jobs
- Badge disappears when the user views (clicks into) the job detail
- No aggregate run summary banner — badges on individual cards are sufficient
- Jobs that disappear from platforms are removed from the dashboard (keep it clean, no stale listings)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-discovery-engine*
*Context gathered: 2026-02-07*
