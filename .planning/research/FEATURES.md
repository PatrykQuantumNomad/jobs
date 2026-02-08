# Feature Landscape: Automated Testing & CI

**Domain:** Comprehensive test suite + CI pipeline for a Python/FastAPI/Playwright job search automation app
**Researched:** 2026-02-08
**Overall confidence:** HIGH (pytest/FastAPI/Playwright testing patterns are mature and well-documented)

## Table Stakes

Features every serious test suite must have. Missing = unreliable codebase.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Unit tests for Pydantic models | Data validation is foundational; broken models break everything | Low | `models.py`, `resume_ai/models.py`, `apply_engine/events.py` |
| Unit tests for scoring logic | Scoring is the core value proposition; must be deterministic | Low | `scorer.py` -- test all 4 factors and edge cases |
| Unit tests for salary parsing | Used across all platforms; many edge cases from real data | Low | `salary.py` -- 17+ format variations to cover |
| Unit tests for deduplication | Fuzzy matching has subtle edge cases | Medium | `dedup.py` -- exact + fuzzy passes, alias tracking |
| Integration tests for SQLite DB | DB is the system of record; schema, CRUD, FTS5 must be verified | Medium | `webapp/db.py` -- migrations, upsert, FTS5 search, stats |
| Integration tests for FastAPI endpoints | Web dashboard is the primary user interface | Medium | `webapp/app.py` -- 15+ routes including search, export, import |
| Settings isolation between tests | Singleton state causes test interdependencies | Low | `config.py:reset_settings()` already exists |
| pytest markers (unit/integration/e2e) | Must run fast tests separately from slow ones | Low | pyproject.toml configuration |
| Coverage reporting | Need to know what is tested and what is not | Low | pytest-cov with 70% minimum gate |

## Differentiators

Features that make the test suite robust beyond basic coverage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Mocked RemoteOK API tests | Verify filtering, parsing, error handling without network | Medium | respx mocking of httpx.Client |
| Anti-fabrication validator tests | Ensure LLM guardrails work without calling LLM | Low | `resume_ai/validator.py` -- pure regex, highly testable |
| FTS5 full-text search tests | FTS5 is a critical dashboard feature; edge cases in query syntax | Medium | Test prefix matching, operator handling, empty queries |
| Platform registry validation tests | Decorator-based registration must catch missing protocol methods | Medium | Test both valid and invalid class registration |
| Config YAML loading tests | Settings drive the entire pipeline; invalid config must error clearly | Medium | Test from test YAML fixture, not production config |
| CI pipeline (GitHub Actions) | Automated test runs on push/PR | Medium | Run unit+integration on every push, E2E on schedule/manual |
| Job factory fixture | Clean, readable test data construction | Low | Factory function with sensible defaults |
| Score breakdown tests | Score details are user-facing (displayed in dashboard) | Low | Test `score_job_with_breakdown()` output format |
| Export endpoint tests | CSV/JSON exports must produce correct formats | Low | Verify headers, content types, data accuracy |
| Activity log tests | Activity log tracks user actions; critical for audit trail | Low | Test `log_activity()`, `get_activity_log()` |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Mocked Playwright browser tests | Mock objects will drift from real browser API. Tests pass on mocks but fail on real browsers. High maintenance cost. | Test browser code only in E2E layer with real Playwright. Extract testable logic (parsing, filtering) into unit-testable functions. |
| LLM integration tests | Requires API keys, costs money, non-deterministic output. | Test the Pydantic models, validator, diff generator, and renderer with hardcoded structured output. Mock LLM calls. |
| Screenshot comparison tests | Brittle, platform-dependent, slow. | Test that HTML responses contain expected elements via string/DOM assertions. |
| Load/performance testing | Premature for a single-user local tool. | Monitor response times in manual testing. Add load testing if the app becomes multi-user. |
| Contract testing against live Indeed/Dice | Selectors change frequently. Tests against live sites are inherently flaky. | Track selector changes through manual verification. Document expected selectors in `*_selectors.py` files. |
| Test data seeding from production DB | Leaks personal data into test environments. | Use factory fixtures with synthetic data. |
| Full orchestrator integration test | Orchestrator calls every platform, writes files, prompts user input. Too many side effects. | Test orchestrator phases individually with mocked platforms. |

## Feature Dependencies

```
pytest markers -> conftest.py fixtures -> unit tests
                                      -> integration tests (require DB fixture)
                                      -> e2e tests (require Playwright)

conftest.py fixtures -> job_factory -> used by unit + integration
                     -> test_settings -> used by scorer, config, registry tests
                     -> test_db -> used by db, webapp, import tests

test_db -> test_webapp (TestClient depends on DB being initialized)
test_settings -> test_scorer (scorer reads config for weights)
```

## MVP Recommendation

Prioritize (in build order):

1. **Root conftest.py + test fixtures** -- Foundation everything depends on
2. **Unit tests for models, scorer, salary, dedup** -- Highest value-to-effort ratio
3. **Unit tests for validator** -- Guards LLM output quality
4. **Integration tests for webapp/db.py** -- System of record
5. **Integration tests for webapp/app.py** -- User-facing routes
6. **Integration tests for RemoteOK** -- Only mockable platform
7. **pytest-cov configuration + coverage gate** -- Measure progress
8. **GitHub Actions CI** -- Automate everything

Defer:
- **E2E browser tests**: High setup cost, fragile, not needed until platforms change selectors. Add as a separate phase.
- **pytest-xdist parallelism**: Not needed until suite exceeds 200 tests.
- **Orchestrator integration tests**: Complex mocking for low marginal value.

## Sources

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Best Practices for Organizing Tests](https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/)
- [RESPX User Guide](https://lundberg.github.io/respx/guide/)
- Codebase analysis of all 16+ production modules
