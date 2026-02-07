# Codebase Concerns

**Analysis Date:** 2026-02-07

## Tech Debt

**DOM Selector Fragility (High Impact):**
- Issue: Indeed and Dice selectors are hardcoded strings that break frequently as platforms redesign their UIs. Current selectors marked "verified 2026-02-06" but have historical pattern of 2-4 week lifespan before breakage.
- Files: `platforms/indeed_selectors.py`, `platforms/dice_selectors.py`, `platforms/indeed.py`, `platforms/dice.py`
- Impact: Search phase fails silently (0 jobs extracted), apply flow clicks wrong elements, description parsing skipped. Human discovers only after running full pipeline.
- Fix approach:
  - Implement automated selector validation (check selectors exist on page before using)
  - Add fallback selector chains (primary, secondary, tertiary)
  - Implement visual regression testing with headless screenshots
  - Create observer pattern to detect DOM changes and alert when selectors fail

**Salary Parsing Edge Cases (Medium Impact):**
- Issue: Multiple salary parsing implementations with inconsistent logic. `_parse_salary()` in `platforms/indeed.py` handles hourly/monthly conversion differently than `platforms/dice.py` version. Salary text formats vary widely (USD vs $, commas vs dots in thousands separators, single values vs ranges).
- Files: `platforms/indeed.py` (lines 308-338), `platforms/dice.py` (lines 272-293), `scorer.py` (line 96)
- Impact: Salary scores calculated incorrectly (jobs above $200K may be marked as below threshold). Score 4-5 jobs lost in filtering.
- Fix approach:
  - Consolidate salary parsing to single module `salary_parser.py` with comprehensive test cases
  - Add validation that salary_max >= salary_min (partially exists in `models.py` but not in parsing)
  - Handle edge cases: no salary, only minimum, only maximum, hourly rates, international formats

**Insufficient Error Recovery in Browser Automation (Medium Impact):**
- Issue: When browser automation fails (timeout, stale element, selector mismatch), orchestrator logs error and skips platform. No retry logic, no incremental state saving. If Indeed search times out on page 5 of 10, all 5 pages are lost.
- Files: `orchestrator.py` (lines 124-150), `platforms/indeed.py` (lines 73-109), `platforms/dice.py` (lines 78-106)
- Impact: Large result set lost (potentially 50+ jobs per failed search). Manual re-run required.
- Fix approach:
  - Save intermediate results after each page/query (write to raw_{platform}_{query}.json)
  - Implement exponential backoff retry on timeout (3 retries, 5/15/30 second delays)
  - Add circuit breaker to skip platform after 3 consecutive failures

**Inconsistent Job ID Generation (Low Impact):**
- Issue: Indeed uses `data-jk`, Dice uses `data-job-guid`, RemoteOK uses `id`. Job.id field defaults to empty string. ~20% of extracted jobs have empty ID, making tracking/replay difficult.
- Files: `models.py` (line 24, default ""), `platforms/indeed.py` (line 290), `platforms/dice.py` (no ID set), `platforms/remoteok.py` (line 110)
- Impact: Hard to identify duplicate jobs across reruns, ID-based lookups fail, tracking database can't match reruns to originals.
- Fix approach:
  - Make ID generation consistent: Job(id=platform+dedup_key) when platform-specific ID unavailable
  - Add unique constraint in webapp/db.py on (platform, dedup_key) pair instead of relying on ID

**Resource Cleanup on Exception (Low Impact):**
- Issue: Browser contexts and HTTP clients may not close if exception occurs mid-pipeline. `stealth.py` close_browser() catches exceptions silently. RemoteOK async context manager in `remoteok.py` close() may be skipped if orchestrator crashes before awaiting.
- Files: `platforms/stealth.py` (lines 62-71), `orchestrator.py` (lines 82-101, 149), `platforms/remoteok.py` (line 70)
- Impact: Orphaned browser processes consume memory/ports. Async client left open (socket leak).
- Fix approach:
  - Use context managers (with statement) for all browser/client lifecycles
  - Add finally blocks or async context manager protocol to remoteok.py
  - Add atexit handler to clean up browser_sessions on unexpected exit

---

## Known Bugs

**Indeed 404 Detection Incomplete (Medium Severity):**
- Symptoms: ~50% of Indeed job cards have bogus tracking IDs (`fedcba9876543210` pattern). Clicking these produces 404 pages. Current code detects by page title "Not Found | Indeed" but misses some variations.
- Files: `platforms/indeed.py` (lines 122-126)
- Trigger: Run full Indeed search, observe final job_pipeline/raw_indeed.json includes 0-description jobs from 404 pages
- Workaround: Filter raw JSON manually post-pipeline, remove jobs with description length < 50 chars
- Fix: Tighten 404 detection: check for 404 in URL, check if description section element is empty, validate job_id format before visiting

**Dice "Easy Apply" Detection Unreliable (Low Severity):**
- Symptoms: Some Easy Apply jobs missing from filtered results. Text "Easy Apply" appears in card inner text, but nearby elements changed position.
- Files: `platforms/dice.py` (line 210, `has_easy = "Easy Apply" in card_text`)
- Trigger: Run Dice search, compare Easy Apply toggle count in UI vs extracted easy_apply=True count in raw_dice.json
- Workaround: None — jobs without easy_apply flag still apply-able, just not filtered by dashboard
- Fix: Verify selector `[data-testid='easy-apply-badge']` or similar exists; extract programmatically instead of text search

**Form Filler Field Matching False Positives (Low Severity):**
- Symptoms: Textareas labeled "Job description" get filled with candidate's desired salary. Generic keywords like "location" match location fields AND location filters in search forms.
- Files: `form_filler.py` (lines 109-138)
- Trigger: Custom application forms with unusual label text (e.g., "Where will you be working?" matches "location")
- Workaround: Skip form filling, fill manually for edge cases
- Fix: Add context-aware matching (e.g., if form action contains "apply" or `/application`, match fields; if form action is search, skip)

---

## Security Considerations

**Credentials in Memory (Medium Risk):**
- Risk: Config.DICE_EMAIL and Config.DICE_PASSWORD loaded at module import time and held in memory for entire pipeline. If process dumps or debugger attaches, credentials visible in .env memory region.
- Files: `config.py` (lines 29-32), `platforms/dice.py` (lines 48, 57)
- Current mitigation: .env is gitignored, credentials never logged, platform raises RuntimeError if missing
- Recommendations:
  - Load credentials lazily (only at login time) and clear from memory after successful auth
  - Implement credential caching in browser context (don't store in Python memory)
  - Add warning in README against running pipeline in containers/shared environments

**Unvalidated Form Filling (Low Risk):**
- Risk: `form_filler.py` fills any field matching keywords without validating field type, size, or format constraints. Could cause validation errors on submit (e.g., phone field expects 10 digits, script fills "416-708-9839").
- Files: `form_filler.py` (lines 52-105)
- Current mitigation: Human-in-the-loop always confirms before final submit
- Recommendations:
  - Add form validation: parse field constraints (pattern, maxlength, required), pre-validate values
  - Log filled values before human confirmation step

**Screenshot Storage Path Traversal Prevention (Low Risk):**
- Risk: `orchestrator.py` _sanitize() function truncates filenames but doesn't prevent directory traversal. Edge case: company name "../../etc" could escape debug_screenshots/
- Files: `orchestrator.py` (lines 385-387, sanitize function), `platforms/base.py` (line 68, screenshot method)
- Current mitigation: sanitize function removes most special chars
- Recommendations:
  - Use UUID or counter for screenshot names instead of sanitized user input
  - Validate sanitized paths with `Path.resolve().is_relative_to(DEBUG_SCREENSHOTS_DIR)`

---

## Performance Bottlenecks

**Sequential Page Navigation in Search (High Impact on Runtime):**
- Problem: Indeed and Dice searches load pages sequentially (for loop over max_pages), waiting for page load and selector visibility before proceeding. With 5-page searches × 10 queries × 2 platforms = 100 pages at 2-5s delay = 200-500s per run.
- Files: `platforms/indeed.py` (lines 79-106), `platforms/dice.py` (lines 83-103)
- Cause: Browser automation requires serial navigation; can't parallelize due to shared page object
- Improvement path:
  - Batch queries: run Indeed and Dice searches in parallel threads (orchestrator.py already does this for RemoteOK)
  - Pre-fetch next page while processing current page (load page 2 while extracting page 1)
  - Reduce page load timeout from 30s to 15s with fallback

**RemoteOK Single API Call (Low Impact on Runtime):**
- Problem: RemoteOK searches return ~95 jobs max, regardless of query. Current code re-fetches API for each of 10 search queries, wasting bandwidth.
- Files: `platforms/remoteok.py` (line 33, single API call per query loop iteration)
- Cause: API schema doesn't support filters; all jobs returned every time
- Improvement path:
  - Cache API response (expires after 1 hour) to avoid re-fetching
  - Run single API call outside query loop, filter results by all queries
  - Add ETag/If-Modified-Since to avoid re-parsing unchanged response

**Score Calculation Walks Full Text (Low Impact):**
- Problem: `scorer.py` _tech_score() concatenates full description + tags (~5KB average) per job, searches for 34 keywords (in/substring operations, O(n*m)). With 500+ jobs, this is slow.
- Files: `scorer.py` (lines 74-82)
- Cause: Full-text search instead of indexed/normalized keywords
- Improvement path:
  - Index job description at parse time: split into tokens, lowercase, deduplicate
  - Pre-compile keyword regex pattern
  - Use set intersection instead of substring search

---

## Fragile Areas

**Indeed Sponsored Card Detection (Fragile):**
- Files: `platforms/indeed.py` (lines 202-213)
- Why fragile: Sponsored label detection uses "sponsored" string search in card.inner_text(). Indeed sometimes uses "Ad", "Promoted", or no visible label. If Indeed removes label entirely, sponsored cards pollute results.
- Safe modification:
  - Check sponsor attribute: some DOM elements may have `[data-sponsored]` or similar
  - Validate job_id format before visiting (real IDs are hex-like, fake IDs follow patterns)
  - Cross-reference with company reputation (sponsored posts often from unknown companies)
- Test coverage: No unit tests for sponsored detection, only discovered by observation during manual runs

**Selector Waterfalls in Job Details (Fragile):**
- Files: `platforms/indeed.py` (lines 128-143 — four fallback selectors for description)
- Why fragile: Multiple selector fallbacks indicate author knew Indeed changes selectors. If all four fail, no description is extracted and job scores lower. Hard to debug which selector worked vs failed.
- Safe modification:
  - Log which selector matched for each job (e.g., "job X: matched selector 2")
  - Alert if description empty (screenshot + human review)
- Test coverage: No test for selector fallback logic; would break silently if all fail

**Form Filling Keyword Matching (Fragile):**
- Files: `form_filler.py` (lines 18-40, _FIELD_KEYWORDS dict)
- Why fragile: Substring matching with generic keywords. Form with label "What is your current location?" matches "location" → fills with "Springwater, ON, Canada" even if it's a search filter.
- Safe modification:
  - Add form context checks (form action, button labels)
  - Maintain blocklist of common false-positive labels (e.g., "Location filter", "Job location preferences")
  - Use fuzzy matching (difflib) instead of substring to catch variations
- Test coverage: No test cases for form filling edge cases

**Browser Session Persistence Assumption (Fragile):**
- Files: `platforms/stealth.py` (line 31 — assumes browser_sessions/ directory persists), `orchestrator.py` (line 87 — creates persistent context)
- Why fragile: Indeed session cached in browser_sessions/indeed/ expires after ~7 days. Script assumes session always valid. If expired, login step silently returns False (line 40-42 in indeed.py) and search is skipped without error.
- Safe modification:
  - Check session validity before search (load Indeed home page, verify logged_in indicator present)
  - If session expired, prompt human to re-login (don't skip silently)
  - Document session expiration in README
- Test coverage: No test for expired session handling

---

## Scaling Limits

**SQLite Database Scaling (Medium Concern):**
- Current capacity: ~10K jobs (tested with RemoteOK + Indeed + Dice over 2 weeks)
- Limit: SQLite WAL (write-ahead logging) works to ~100K jobs before lock contention. Dashboard query times >5s with >50K jobs.
- Scaling path:
  - Migrate to PostgreSQL if job history grows beyond 6 months
  - Add indexes on (platform, created_at, status) for common queries
  - Implement job archival (move jobs older than 90 days to archive table)

**Browser Session Directory Bloat (Low Concern):**
- Current capacity: Each platform session (indeed/, dice/, remoteok/) ~50-200MB after 2 weeks of runs
- Limit: browser_sessions/ exceeds 1GB after 6 weeks, slow to copy/backup
- Scaling path:
  - Add cleanup script to remove browser_sessions older than 30 days
  - Document in README: `rm -rf browser_sessions/*/` to reset sessions
  - Consider ephemeral sessions (don't persist) for non-auth platforms

**API Rate Limiting (Low Concern for Current Setup):**
- RemoteOK: No documented rate limit, returns same ~95 jobs per request
- Indeed: High anti-bot (uses stealth), likely rate-limited by IP/session after 100+ queries
- Dice: Low anti-bot, likely rate-limited after 1000+ requests
- Current capacity: ~30 search queries per run (10 queries × 3 platforms) is safe
- Scaling path: If expanding to 100+ queries, implement request queuing, per-platform rate limit tracking

---

## Dependencies at Risk

**playwright-stealth Version Lock (Medium Risk):**
- Risk: Project pins playwright-stealth==2.0.1 (per CLAUDE.md). API changed from v1 (stealth_sync) to v2 (Stealth().apply_stealth_sync). If stealth 2.1+ changes API again, automation breaks. Upstream development stalled (last release 2024-06).
- Impact: Can't upgrade Playwright without stealth breaking
- Migration plan:
  - Monitor playwright-stealth releases; prepare conditional code for v3 API
  - Document stealth API in code (why v2.0.1 required, what changed from v1)
  - Consider custom stealth implementation if upstream abandons library

**Pydantic v2 Field Validator Edge Case (Low Risk):**
- Risk: `models.py` salary_max validator (lines 49-55) accesses info.data.get("salary_min") which may not exist if salary_max is validated first. Validator ordering not guaranteed in Pydantic v2.
- Impact: ValidationError if salary_max passed without salary_min, catching this in production
- Migration plan:
  - Add explicit check: `if "salary_min" not in info.data: return v`
  - Add unit test: `Job(salary_max=200000)` should not raise

**httpx Async Client Timeout Configuration (Low Risk):**
- Risk: `platforms/remoteok.py` (line 25) sets global timeout=30.0s. If API slow, entire pipeline stalls. If timeout too low, transient network issues cause retry loop.
- Impact: RemoteOK search fails silently (returns empty list, line 38)
- Mitigation in place: Try/except on HTTP errors
- Recommendation: Make timeout configurable (Config.REMOTEOK_TIMEOUT), add per-request timeout override

---

## Missing Critical Features

**No Job Deduplication Across Reruns (Medium Concern):**
- Problem: Running pipeline twice discovers same jobs. discovered_jobs.json contains duplicates from run 1 and run 2. webapp/db.py upsert keeps both via dedup_key collision, but JSON file grows unbounded.
- Blocks: Can't track application history (did I already apply to this job? when?)
- Fix: Implement job history dedup:
  - Before scoring, check if job exists in job_pipeline/jobs.db
  - Merge with existing record (keep highest score, newest description)
  - Mark as re-discovered vs new

**No Partial Progress Save (Medium Concern):**
- Problem: If pipeline crashes during Phase 2 (search), all extracted jobs lost. No recovery point.
- Blocks: Can't resume interrupted searches
- Fix: Save raw results incrementally per-platform per-query, not all at end

**No Competitor Job Filtering (Low Concern):**
- Problem: Script applies to jobs posted by recruiters/job boards, not direct employers. No blacklist for recruiting agencies.
- Blocks: Wasted applications on indirect hiring channels
- Fix: Add company_type field (direct, recruiter, board) and filter in Phase 3

**No Resume Tailoring Automation (Low Concern):**
- Problem: CLAUDE.md documents resume tailoring approach but no automation implemented. Form_filler.py generic but doesn't extract job keywords to customize resume.
- Blocks: Can't auto-tailor resumes per job in apply phase
- Fix: Implement resume_tailor.py that parses job description, extracts keywords, regenerates resume PDF with keyword emphasis

---

## Test Coverage Gaps

**No Unit Tests for Salary Parsing (High Priority):**
- What's not tested: _parse_salary() functions in indeed.py and dice.py
- Files: `platforms/indeed.py` (lines 308-338), `platforms/dice.py` (lines 272-293)
- Risk: Edge cases silently fail (hourly to annual conversion, missing commas, K notation)
- Add tests for:
  - "$150K - $200K" → (150000, 200000)
  - "$150,000 - $200,000" → (150000, 200000)
  - "$75/hour" → (156000, 156000) [40 hrs/wk × 52 wk]
  - "USD 224,400.00 - 283,800.00 per year" → (224400, 283800)
  - null/empty → (None, None)

**No Integration Tests for Scoring (Medium Priority):**
- What's not tested: Full scoring pipeline with real jobs
- Files: `scorer.py` (entire module)
- Risk: Scoring rubric changes without validation
- Add tests for:
  - Job with "Principal Engineer" title scores 2+ on title
  - Job with 5+ tech keywords scores 2 on tech
  - Remote location scores 1, Springwater ON scores 1, SF scores 0
  - Salary $225K scores 1, $150K scores 0

**No E2E Tests for Deduplication (Medium Priority):**
- What's not tested: Cross-platform dedup logic
- Files: `orchestrator.py` (lines 206-221)
- Risk: Duplicates slip through (dedup_key matching is fragile with company name normalization)
- Add test: Two jobs with same title, company "Acme Inc" vs "ACME, Inc." → deduplicated to 1

**No Selector Validation Tests (High Priority):**
- What's not tested: Whether selectors exist on live pages
- Files: `platforms/indeed_selectors.py`, `platforms/dice_selectors.py`
- Risk: Selectors fail silently, discovered during full run (50+ minute wait)
- Add: Headless browser test that loads Indeed home, Dice search page, validates each selector exists (or fails fast with clear error)

**No Form Filling Edge Cases (Medium Priority):**
- What's not tested: FormFiller behavior with ambiguous labels
- Files: `form_filler.py`
- Risk: Form fields filled incorrectly on custom ATS
- Add test: Form with fields like "Preferred location" (should not match location), "Current role" (should match current_title)

---

*Concerns audit: 2026-02-07*
