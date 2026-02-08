# Codebase Concerns

**Analysis Date:** 2026-02-07

## Tech Debt

**Indeed selector brittleness:**
- Issue: DOM selectors are isolated in `platforms/indeed_selectors.py` but change frequently. ~50% of job cards return bogus `data-jk` values causing 404s. Multiple fallback description selectors required.
- Files: `platforms/indeed.py`, `platforms/indeed_selectors.py`
- Impact: Search yields drop when Indeed changes DOM structure. Failed detail fetches waste time and produce incomplete job data.
- Fix approach: Implement selector versioning with automatic fallback chains. Add monitoring to detect when primary selectors fail rate exceeds threshold (>30%).

**Dice selector migration lag:**
- Issue: Platform migrated from legacy `dhi-search-card` and `[data-cy=...]` selectors to React `data-testid` attributes. Current code works but no validation layer.
- Files: `platforms/dice.py`, `platforms/dice_selectors.py`
- Impact: Next Dice redesign will break extraction silently. No test coverage for selector resilience.
- Fix approach: Add integration tests that verify selector existence on live pages. Implement selector health checks in orchestrator pre-flight.

**Silent error swallowing:**
- Issue: 106 try/except blocks across 14 files, many with bare `except Exception: pass` or `except: continue` that suppress errors without logging.
- Files: `form_filler.py` (lines 134, 190), `apply_engine/engine.py` (lines 129, 149, 213, 304, 354, 461, 468, 503), `platforms/indeed.py` (line 243), `platforms/stealth.py` (lines 67, 71), `platforms/mixins.py` (line 103)
- Impact: Failures in form filling, browser context cleanup, and element detection go unreported. Debugging requires adding print statements manually.
- Fix approach: Replace bare except with specific exception types. Log all caught exceptions at DEBUG level minimum. Add structured logging with context (platform, job_id).

**Mixed logging strategy:**
- Issue: Codebase uses both `print()` statements (125+ occurrences) and Python logging (only in `apply_engine/engine.py`). No centralized log configuration.
- Files: All platform modules, `orchestrator.py`, `scorer.py`, `form_filler.py`
- Impact: No log levels, no file output, no timestamps on most messages. Scheduled runs produce unstructured stdout only.
- Fix approach: Migrate all print() to logging. Add config for log levels (DEBUG for dev, INFO for prod). Write logs to `job_pipeline/runs/{timestamp}.log`.

**Credential exposure risk:**
- Issue: `.env` file exists in repo root with real credentials. `.env.example` template exists but no validation that `.env` is gitignored.
- Files: `.env` (contains `DICE_PASSWORD`), `config.py`
- Impact: Accidental `git add .env` would commit credentials to public repo. No runtime check that credentials aren't hardcoded.
- Fix approach: Add pre-commit hook to reject commits containing `.env`. Add startup validation that credentials come from environment only, not hardcoded strings.

## Known Bugs

**Indeed sponsored card false positives:**
- Symptoms: Sponsored cards with fake job IDs (`fedcba9876543210` pattern) pass through extraction, produce 404 on detail fetch
- Files: `platforms/indeed.py` (line 234 `_is_sponsored()`, line 287)
- Trigger: Any Indeed search returns mix of organic + sponsored cards
- Workaround: 404 detection in `get_job_details()` (line 151) skips these jobs but wastes a page navigation per fake ID
- Fix approach: Improve sponsored detection heuristic. Check for `data-jk` format patterns (real IDs are 16-char hex, fake are sequential). Add URL validation before navigation.

**RemoteOK salary filtering inconsistency:**
- Symptoms: Some jobs have `salary_min > 0` but `salary_max = 0`, causing filter logic to fail
- Files: `platforms/remoteok.py` (line 71)
- Trigger: RemoteOK API returns partial salary data for certain posts
- Workaround: Current code uses `salary_max or None` but filter only checks `salary_max` (line 71)
- Fix approach: Use `max(salary_min, salary_max)` for threshold check. Add validation that at least one salary field is nonzero before filtering.

**Dashboard in-memory DB mode breaks resume tracking:**
- Symptoms: When `JOBFLOW_TEST_DB=1` is set, resume versions table exists but isn't persisted between requests
- Files: `webapp/db.py` (lines 12-17, 133-146)
- Trigger: Running tests with in-memory DB, then querying resume versions
- Workaround: Singleton `_memory_conn` shares state within process but loses data on restart
- Fix approach: Use separate test fixtures with proper teardown. Don't rely on env var for DB mode selection.

## Security Considerations

**Browser session persistence:**
- Risk: Persistent browser contexts in `browser_sessions/` store cookies, localStorage, and credentials indefinitely
- Files: `platforms/stealth.py` (line 31), `platforms/indeed.py`, `platforms/dice.py`
- Current mitigation: Directory is gitignored. Sessions are not encrypted at rest.
- Recommendations: Add session encryption using keyring or encrypted volumes. Implement session expiration (30-day TTL). Clear sessions after N failed logins.

**Resume file path injection:**
- Risk: `resume_path` parameter in apply flow comes from database query, could be manipulated if DB is compromised
- Files: `apply_engine/engine.py` (line 485 `_get_resume_path()`), `form_filler.py` (line 84)
- Current mitigation: Paths are validated with `Path.exists()` before use
- Recommendations: Whitelist allowed resume directories (`resumes/`, `resumes/tailored/`). Reject absolute paths outside project root. Add path traversal checks.

**ATS iframe form fill blind trust:**
- Risk: `form_filler.py` detects ATS iframes but doesn't validate origins before filling forms
- Files: `form_filler.py` (lines 140-165 `_detect_ats_iframe()`)
- Current mitigation: Keyword matching on known ATS domains (greenhouse.io, lever.co, ashbyhq.com)
- Recommendations: Whitelist exact domains with TLS certificate validation. Reject iframes from unexpected origins. Add user confirmation before filling external forms.

**Screenshot path injection:**
- Risk: Screenshot filenames use unsanitized job IDs and platform names
- Files: `platforms/mixins.py` (line 68), `apply_engine/engine.py` (line 449)
- Current mitigation: `datetime.now().strftime()` adds timestamp suffix
- Recommendations: Sanitize `platform_name` and `job.id` with regex `[^a-zA-Z0-9_-]`. Limit filename length to 255 chars.

## Performance Bottlenecks

**Synchronous job detail fetching:**
- Problem: Each job detail page is fetched sequentially with 2-5s delay between requests
- Files: `platforms/indeed.py` (line 139 `get_job_details()`), `orchestrator.py`
- Cause: Playwright Page is not thread-safe, delays are anti-bot mitigation
- Improvement path: Use multiple browser contexts in parallel (one per platform). Fetch details for 5 jobs concurrently per context with shared rate limiter.

**SQLite write lock contention:**
- Problem: Dashboard and orchestrator both write to `job_pipeline/jobs.db`, causing BUSY errors under concurrent access
- Files: `webapp/db.py` (line 164 `PRAGMA busy_timeout = 5000`)
- Cause: WAL mode helps but long-running transactions (apply flows) block reads
- Improvement path: Increase busy timeout to 30s for apply flows. Use separate read-only connections for dashboard queries. Consider PostgreSQL for production.

**Full-page screenshots on every failure:**
- Problem: `screenshot(full_page=True)` on large job description pages takes 3-5s, blocks apply flow
- Files: `platforms/mixins.py` (line 71), `apply_engine/engine.py` (line 451)
- Cause: Full-page rendering for 10+ page descriptions
- Improvement path: Use viewport screenshots only unless explicitly requested. Compress PNGs with pngquant. Implement async screenshot queue.

**FTS5 rebuild on schema migration:**
- Problem: `INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')` scans entire jobs table on every migration run
- Files: `webapp/db.py` (line 109)
- Cause: Migration 4 rebuilds FTS index, runs even when already migrated (idempotency check missing)
- Improvement path: Add migration tracking table to skip already-applied migrations. Use incremental FTS updates via triggers only.

## Fragile Areas

**Playwright stealth configuration:**
- Files: `platforms/stealth.py` (lines 42-57)
- Why fragile: Relies on `playwright-stealth` 2.0.1 API (`apply_stealth_sync`) which changed between v1 and v2. Google OAuth detection bypasses stealth on Indeed.
- Safe modification: Always test against live Indeed first. Use `channel="chrome"` (system Chrome) not bundled Chromium. Verify OAuth still works after stealth changes.
- Test coverage: No automated tests for stealth effectiveness. Manual verification required.

**Indeed login flow:**
- Files: `platforms/indeed.py` (lines 54-93)
- Why fragile: Human-in-the-loop manual Google OAuth. Session expiry detection via DOM selector `logged_in_indicator` which changes.
- Safe modification: Test session expiry by deleting `browser_sessions/indeed/`. Add timeout to input prompt (currently blocks forever). Screenshot before raising login failure.
- Test coverage: No test for session restoration. Scheduled mode `_unattended` flag blocks on expired session (intentional, but undocumented).

**Job deduplication key generation:**
- Files: `dedup.py` (lines 20-40), `apply_engine/dedup.py` (line 23)
- Why fragile: `dedup_key` is lowercase normalized `title||company`. Typos in company name create duplicate entries. No edit distance matching.
- Safe modification: Always regenerate keys when changing normalization. Migrate existing keys in database with UPDATE statement.
- Test coverage: Unit tests exist for `make_dedup_key()` but not for fuzzy matching edge cases.

**Database migration version tracking:**
- Files: `webapp/db.py` (lines 178-198 `migrate_db()`)
- Why fragile: `PRAGMA user_version` is the only migration state. Rolling back requires manual SQL. `duplicate column name` errors are silently ignored (line 190).
- Safe modification: Never decrement `SCHEMA_VERSION`. Add forward-only migrations. Test migrations on copy of production DB first.
- Test coverage: No automated migration tests. Manual verification required.

## Scaling Limits

**Single-threaded orchestrator:**
- Current capacity: 3 platforms × 10 queries × 5 pages = ~150 jobs/run, takes 30-45 minutes
- Limit: One platform at a time, sequential page navigation
- Scaling path: Spawn platform workers in parallel threads. Share deduplication cache. Aggregate results at end. Limit: Playwright contexts are CPU-bound (4-6 contexts max on 8-core machine).

**SQLite jobs table:**
- Current capacity: ~10K jobs tested, performs well
- Limit: FTS5 index size grows linearly with description text. ~100K jobs = 500MB+ database, query latency increases.
- Scaling path: Archive old jobs (applied, rejected, withdrawn) to separate table. Implement periodic vacuum. Migrate to PostgreSQL at 50K+ active jobs.

**Resume tailoring storage:**
- Current capacity: Tailored resumes stored as PDFs in `resumes/tailored/{company}_{timestamp}.pdf`
- Limit: Filesystem inode limits (~100K files on ext4). No cleanup of old versions.
- Scaling path: Store resume content in DB (BLOB or compressed TEXT). Keep only latest 3 versions per job. Implement LRU cleanup.

## Dependencies at Risk

**playwright-stealth 2.0.1:**
- Risk: Not actively maintained (last update 2024-09). API changed drastically between v1 and v2.
- Impact: Future Playwright upgrades may break stealth compatibility. Google/Cloudflare detection bypass could stop working.
- Migration plan: Fork playwright-stealth and maintain internally. Evaluate alternatives (undetected-playwright, pyppeteer-stealth). Consider moving to residential proxies + real Chrome profiles.

**httpx for RemoteOK:**
- Risk: None (stable library)
- Impact: None
- Migration plan: N/A

**Pydantic v2:**
- Risk: None (stable library, but project uses v2 features like `model_dump(mode="json")`)
- Impact: Downgrading to Pydantic v1 would break serialization code
- Migration plan: Pin `pydantic>=2.0` in requirements. Avoid v3 beta until stable release.

## Missing Critical Features

**Apply flow validation:**
- Problem: No confirmation that application was actually submitted. `platform.apply()` returns boolean but doesn't verify server response.
- Blocks: Accurate application tracking. User may think job was submitted but form failed silently.
- Priority: High — implement post-submit verification (check for "Application submitted" text, confirmation page URL pattern).

**Selector health monitoring:**
- Problem: No automated detection when platform selectors break. Failures only discovered when running pipeline manually.
- Blocks: Proactive maintenance. Scheduled runs fail silently until human notices.
- Priority: Medium — implement daily selector health check that visits platform homepage and verifies key elements exist.

**Resume version diff tracking:**
- Problem: `resume_versions` table stores paths but no diff of what changed between versions
- Blocks: Understanding why a resume was tailored differently. Audit trail for changes.
- Priority: Low — add `changes_summary` TEXT column with bullet points of modifications.

## Test Coverage Gaps

**Platform login flows:**
- What's not tested: Indeed Google OAuth, Dice two-step login, session restoration
- Files: `platforms/indeed.py` (lines 54-93), `platforms/dice.py` (lines 50-92)
- Risk: Login changes break pipeline, only discovered on next run
- Priority: High — add integration tests with test accounts. Mock Google OAuth for Indeed.

**Form filling heuristics:**
- What's not tested: Field matching logic in `form_filler.py` against real ATS pages (Greenhouse, Lever, Ashby)
- Files: `form_filler.py` (lines 89-118)
- Risk: Keyword changes in ATS forms cause fields to be skipped
- Priority: Medium — capture sample ATS page HTML, test field matching offline.

**Database migration rollback:**
- What's not tested: Rolling back from schema v6 to v5, handling corrupted PRAGMA user_version
- Files: `webapp/db.py` (lines 178-198)
- Risk: Botched migration leaves database in inconsistent state
- Priority: Medium — add migration test suite with before/after snapshots. Test on copies of production DB.

**Error handling in apply engine:**
- What's not tested: Threading edge cases (confirmation timeout, cancel during apply, concurrent applies)
- Files: `apply_engine/engine.py` (lines 52-105, 510-545)
- Risk: Race conditions in event queue, semaphore deadlock, orphaned browser contexts
- Priority: High — add concurrency tests with pytest-asyncio. Simulate timeout scenarios.

---

*Concerns audit: 2026-02-07*
