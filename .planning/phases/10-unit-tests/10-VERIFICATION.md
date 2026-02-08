---
phase: 10-unit-tests
verified: 2026-02-08T16:25:30Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 10: Unit Tests Verification Report

**Phase Goal:** All pure logic modules (models, scoring, salary, dedup, anti-fabrication, delta detection) have passing tests that verify correctness without any I/O

**Verified:** 2026-02-08T16:25:30Z

**Status:** passed

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Invalid Pydantic model inputs (wrong types, missing fields, bad enums) are rejected with clear validation errors | ✓ VERIFIED | 54 tests in test_models.py covering all validation rules: platform literals, required fields (title/company/url), score bounds (1-5), salary cross-field validator (max >= min), JobStatus enum (11 values) — all pass |
| 2 | Salary normalization converts all supported formats (hourly, monthly, yearly, USD, CAD, ranges, bare numbers) to comparable annual USD values | ✓ VERIFIED | 31 tests in test_salary.py covering 14 documented formats (Indeed range, hourly, Dice verbose, K-notation, CAD suffix, monthly, GBP/EUR, None/empty/unparseable), sub-1000 K-heuristic, RemoteOK quirks (max=0), display format, raw preservation — all pass with 100% coverage |
| 3 | Job scoring produces deterministic 1-5 scores for known inputs and the breakdown explains each point awarded or withheld | ✓ VERIFIED | 52 tests in test_scorer.py covering all 4 factors independently (title 0-2, tech 0-2, location 0-1, salary 0-1), boundary mapping (raw 0→score 1, raw 2→2, raw 3→3, raw 4→4, raw 6→5), batch operations, and ScoreBreakdown display formats — all pass with 92% scorer.py coverage |
| 4 | Deduplication detects same job across platforms when company names differ by case, suffix (Inc/LLC), or spacing | ✓ VERIFIED | 33 tests in test_dedup.py covering _normalize_company (15 suffix variants: Inc/LLC/Ltd/Corp/Corporation/Incorporated/Company/Co.), exact Pass 1 (identical dedup_key), fuzzy Pass 2 (LLC vs Inc, Corp variants, Co variants), cross-platform merging, alias recording, sorted aliases — all pass with 96% dedup.py coverage |
| 5 | Delta detection correctly distinguishes new jobs from previously-seen jobs based on normalized identifiers | ✓ VERIFIED | 11 tests in test_delta.py covering timestamp assignment (first_seen_at, last_seen_at), timestamp preservation on re-upsert, stale removal (searched platforms only, fresh preserved, empty platforms no-op, multi-platform, mixed), full delta cycle — all pass using explicit timestamps to avoid flakiness |
| 6 | Anti-fabrication validator detects new companies, skills, and metrics added by LLM that were not in the original | ✓ VERIFIED | 23 tests in test_validator.py covering _extract_entities (multi-word companies, at/for patterns, known tech keywords, CamelCase, ALL_CAPS acronyms, percentages, dollar amounts, multipliers, large numbers) and validate_no_fabrication (new companies/skills/metrics detection, warnings, identical/reordered text handling) — all pass with 98% validator.py coverage |
| 7 | All tests marked with @pytest.mark.unit and run without config files, network access, or external services | ✓ VERIFIED | All 204 tests run with `-m unit` filter. Smoke tests verify test isolation: settings not loaded (ANTHROPIC_API_KEY="fake-test-key"), network blocked (pytest-socket), in-memory DB (_fresh_db fixture) — 13/13 smoke tests pass |
| 8 | Custom ScoringWeights change the final score (e.g., zeroing salary weight removes salary influence) | ✓ VERIFIED | Tests in TestCustomWeights verify factor isolation: zero salary weight prevents salary from contributing, doubled title weight increases title influence — both tests pass |
| 9 | score_batch() scores all jobs in-place, sets status to SCORED, and sorts descending | ✓ VERIFIED | Tests in TestScoreBatch verify batch operations: all jobs get scores, status set to JobStatus.SCORED, result list sorted highest-to-lowest — all 3 tests pass |
| 10 | Tags contribute to tech scoring via search text concatenation | ✓ VERIFIED | test_tags_contribute in TestTechScoring verifies tags=["python", "kubernetes", "terraform", "docker", "aws"] with empty description scores 2 tech points — test passes confirming tags are included in keyword matching |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_models.py` | UNIT-01: Pydantic model validation tests for Job, SearchQuery, CandidateProfile, JobStatus | ✓ VERIFIED | 54 tests, 100% models.py coverage (69 statements), contains TestJob, TestJobStatus, TestDedupKey, TestSearchQuery, TestCandidateProfile |
| `tests/test_salary.py` | UNIT-02: Salary normalization tests for parse_salary, parse_salary_ints, NormalizedSalary | ✓ VERIFIED | 31 tests, 100% salary.py coverage (72 statements), contains TestParseSalary (14 formats), TestParseSalarySmallNumbers (sub-1000 heuristic), TestParseSalaryInts (RemoteOK quirks), TestSalaryDisplay, TestSalaryRawPreserved |
| `tests/test_scorer.py` | UNIT-03 and UNIT-04: Job scoring correctness and score breakdown tests | ✓ VERIFIED | 52 tests, 92% scorer.py coverage (95 statements, 8 lines uncovered in score_batch_with_breakdown), contains TestTitleScoring, TestTechScoring, TestLocationScoring, TestSalaryScoring, TestOverallScoring, TestScoreBatch, TestCustomWeights, TestScoreBreakdown |
| `tests/test_dedup.py` | UNIT-05 and UNIT-06: Exact and fuzzy deduplication tests | ✓ VERIFIED | 33 tests, 96% dedup.py coverage (80 statements, 3 lines uncovered in edge case logic), contains TestNormalizeCompany (15 parametrized cases), TestExactDedup (10 tests), TestFuzzyDedup (8 tests) |
| `tests/resume_ai/test_validator.py` | UNIT-07: Anti-fabrication validation tests | ✓ VERIFIED | 23 tests, 98% validator.py coverage (64 statements, 1 line uncovered), contains TestExtractEntities (12 tests), TestAntiFabrication (9 tests), TestValidationResult (2 tests) |
| `tests/test_delta.py` | UNIT-08: Delta detection tests | ✓ VERIFIED | 11 tests using _fresh_db in-memory fixture for isolation, contains TestNewJobTimestamps (4 tests), TestRemoveStaleJobs (6 tests), TestDeltaDetectionFlow (1 full cycle test) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| tests/test_models.py | models.py | Direct import of Job, SearchQuery, CandidateProfile, JobStatus | ✓ WIRED | Import found: `from models import CandidateProfile, Job, JobStatus, SearchQuery` — all classes constructed and validated in tests |
| tests/test_salary.py | salary.py | Direct import of parse_salary, parse_salary_ints, NormalizedSalary | ✓ WIRED | Import found: `from salary import NormalizedSalary, parse_salary, parse_salary_ints` — all functions called with 14+ parametrized inputs |
| tests/test_scorer.py | scorer.py | Direct import of JobScorer, ScoreBreakdown | ✓ WIRED | Import found: `from scorer import JobScorer, ScoreBreakdown` — JobScorer constructed with explicit profile/weights (no get_settings()), score_job_with_breakdown called, ScoreBreakdown.display_inline/to_dict tested |
| tests/test_scorer.py | models.py | Direct construction of CandidateProfile and Job | ✓ WIRED | Import found: `from models import CandidateProfile, Job, JobStatus` — _make_scorer helper builds CandidateProfile, _make_job helper builds Job instances |
| tests/test_scorer.py | config.py | Direct construction of ScoringWeights | ✓ WIRED | Import found: `from config import ScoringWeights` — custom weights tested (zero salary, double title) |
| tests/test_dedup.py | dedup.py | Import of fuzzy_deduplicate, _normalize_company | ✓ WIRED | Import found: `from dedup import _normalize_company, fuzzy_deduplicate` — both functions tested with 15+ parametrized company names |
| tests/resume_ai/test_validator.py | resume_ai/validator.py | Import of validate_no_fabrication, _extract_entities | ✓ WIRED | Import found: `from resume_ai.validator import ValidationResult, _extract_entities, validate_no_fabrication` — both functions tested with realistic resume text |
| tests/test_delta.py | webapp/db.py | Import of upsert_job, remove_stale_jobs, get_job | ✓ WIRED | Import found: `import webapp.db as db_module` — all three functions called with explicit timestamps via _set_last_seen helper |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| UNIT-01 | Pydantic model validation tests | ✓ SATISFIED | 54 tests in test_models.py covering all model validation rules |
| UNIT-02 | Salary normalization tests | ✓ SATISFIED | 31 tests in test_salary.py covering all 14 documented formats |
| UNIT-03 | Job scoring correctness tests | ✓ SATISFIED | 40+ tests in test_scorer.py covering all 4 factors and boundary mapping |
| UNIT-04 | Score breakdown tests | ✓ SATISFIED | Tests in TestScoreBreakdown covering display_inline, display_with_keywords, to_dict, tuple return |
| UNIT-05 | Exact deduplication tests | ✓ SATISFIED | Tests in TestExactDedup covering identical dedup_key, winner selection, alias recording |
| UNIT-06 | Fuzzy deduplication tests | ✓ SATISFIED | Tests in TestFuzzyDedup covering LLC/Inc/Corp variants, cross-platform merging, sorted aliases |
| UNIT-07 | Anti-fabrication validation tests | ✓ SATISFIED | 23 tests in test_validator.py covering entity extraction and fabrication detection |
| UNIT-08 | Delta detection tests | ✓ SATISFIED | 11 tests in test_delta.py covering timestamp assignment, stale removal, full cycle |

### Anti-Patterns Found

No anti-patterns detected. Scanned all 6 test files for:
- TODO/FIXME/XXX/HACK/PLACEHOLDER comments: None found
- Empty implementations (return None/{}): None found (helpers return valid test data)
- Console.log only implementations: N/A (Python tests use assertions)
- Stub tests: All tests have meaningful assertions and verify behavior

### Test Execution Results

```
$ uv run pytest tests/test_models.py tests/test_salary.py tests/test_scorer.py tests/test_dedup.py tests/resume_ai/test_validator.py tests/test_delta.py -v -m unit

204 tests collected
204 tests passed in 0.67s

Breakdown:
- test_models.py: 54 tests
- test_salary.py: 31 tests
- test_scorer.py: 52 tests
- test_dedup.py: 33 tests
- test_validator.py: 23 tests
- test_delta.py: 11 tests
```

**Coverage:**
- models.py: 100% (69/69 statements)
- salary.py: 100% (72/72 statements)
- scorer.py: 92% (87/95 statements, 8 lines in score_batch_with_breakdown unused)
- dedup.py: 96% (77/80 statements, 3 lines in edge case logic)
- resume_ai/validator.py: 98% (63/64 statements, 1 line in display logic)

**Regression Check:**
All smoke tests pass (13/13) confirming no regressions:
- Factory smoke tests: 3/3 pass
- Settings isolation: 2/2 pass
- Database isolation: 3/3 pass
- Anthropic guard: 1/1 pass
- Network blocked: 1/1 pass
- Environment: 2/2 pass

### Commit Verification

All 6 commits from the 3 plan summaries exist in git history:

| Commit | Task | Type |
|--------|------|------|
| 8ba903c | Task 1: Create tests/test_models.py | test |
| 7b58a8f | Task 2: Create tests/test_salary.py | test |
| 17acdfd | Task 1: Create tests/test_scorer.py | test |
| 8d14296 | Task 1: Create tests/test_dedup.py | test |
| c48e521 | Task 2: Create tests/resume_ai/test_validator.py | test |
| e6fc73b | Task 3: Create tests/test_delta.py | test |

### Success Criteria Verification

All success criteria from ROADMAP.md are satisfied:

1. ✓ **Invalid Pydantic model inputs rejected with clear validation errors**
   - test_invalid_platform_rejected, test_missing_required_fields, test_score_lower_bound, test_score_upper_bound, test_salary_max_lt_min_rejected all pass with ValidationError
   
2. ✓ **Salary normalization converts all supported formats to comparable annual USD values**
   - 14 format parametrize table covers: Indeed range, hourly ($85/hr, $85 an hour), Dice verbose (USD X.XX per year), K-notation ($150K-$200K), CAD suffix, monthly, GBP/EUR, None/empty/unparseable
   - parse_salary_ints handles RemoteOK quirk (max=0 treated as None)
   - NormalizedSalary.display produces compact format: $150K-$200K USD/yr, C$150K-C$180K CAD/yr
   
3. ✓ **Job scoring produces deterministic 1-5 scores for known inputs and the breakdown explains each point awarded or withheld**
   - test_perfect_match_scores_5: title="Principal Engineer", 5+ tech keywords, location="Remote", salary_max=250000 → score=5
   - test_minimal_match_scores_1: title="Intern", no tech, no remote, no salary → score=1
   - Boundary tests at raw scores 2, 3, 4 all map correctly
   - ScoreBreakdown.display_inline produces: "Title +2 | Tech +1 | Remote +1 | Salary +0 = 4"
   
4. ✓ **Deduplication detects same job across platforms when company names differ by case, suffix (Inc/LLC), or spacing**
   - test_dedup_key_normalization parametrize table: "Google Inc.", "GOOGLE LLC", "Google Ltd" all → "google::staff engineer"
   - test_llc_vs_inc_merges, test_corp_variants_merge, test_co_variant_merges all pass
   - test_cross_platform_dedup: indeed + dice jobs with same company+title → 1 result
   
5. ✓ **Delta detection correctly distinguishes new jobs from previously-seen jobs based on normalized identifiers**
   - test_new_job_gets_first_seen_at, test_new_job_gets_last_seen_at: timestamps assigned on insert
   - test_first_seen_preserved_on_update: re-upsert keeps original first_seen_at
   - test_last_seen_updated_on_re_upsert: re-upsert updates last_seen_at
   - test_stale_job_removed: job with old last_seen_at removed when platform searched
   - test_unsearched_platform_preserved: dice job kept when only indeed searched
   - test_full_delta_cycle: realistic 2-run simulation with 3 jobs (2 remain, 1 removed)

---

_Verified: 2026-02-08T16:25:30Z_
_Verifier: Claude (gsd-verifier)_
