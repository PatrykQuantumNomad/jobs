# Phase 10: Unit Tests - Research

**Researched:** 2026-02-08
**Domain:** Pure logic unit tests for Pydantic models, salary parsing, scoring, deduplication, anti-fabrication validation, and delta detection
**Confidence:** HIGH

## Summary

This phase writes unit tests for all pure logic modules in the codebase. The test infrastructure from Phase 9 is fully operational: pytest configuration, factory-boy fixtures, in-memory DB isolation, network blocking, and Anthropic API guards are all in place and passing (13 smoke tests green). The modules under test are well-structured, pure-logic Python with clean function signatures, making them ideal unit test targets requiring zero I/O mocking.

The eight requirements (UNIT-01 through UNIT-08) map cleanly to six source files: `models.py`, `salary.py`, `scorer.py`, `dedup.py`, `resume_ai/validator.py`, and `webapp/db.py` (for delta detection only). Each module has deterministic inputs and outputs. The scorer requires a `CandidateProfile` and `ScoringWeights` which can be constructed directly without touching config files. The dedup module depends on `rapidfuzz` (already installed). The validator is entirely self-contained with no external dependencies. The delta detection in UNIT-08 requires the DB layer (`remove_stale_jobs`, `first_seen_at`/`last_seen_at` tracking), which touches the database -- but the existing `_fresh_db` autouse fixture provides clean isolation.

**Primary recommendation:** Write one test file per source module (`test_models.py`, `test_salary.py`, `test_scorer.py`, `test_dedup.py`, `test_validator.py`, `test_delta.py`). Use parametrized tests heavily for salary format variations and scoring edge cases. Construct `CandidateProfile` and `ScoringWeights` directly in tests (no `get_settings()` needed). Mark all tests with `@pytest.mark.unit`. UNIT-08 (delta detection) straddles unit/integration -- test the pure logic of `remove_stale_jobs` and timestamp tracking using the in-memory DB fixture.

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
| pytest-cov | 7.0.0 | Coverage reporting | Already configured; run `pytest --cov` to verify coverage |
| rapidfuzz | 3.14+ | Fuzzy matching (production dep) | Already installed; imported by `dedup.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual Job() construction | JobFactory overrides | Factory is better for complex objects; direct `Job()` is fine for targeted validation tests |
| `@pytest.mark.parametrize` | hypothesis property testing | Parametrize is simpler, sufficient for known format variations; hypothesis is overkill for this scope |

**Installation:** No new packages needed. Phase 9 installed everything required.

## Architecture Patterns

### Recommended Test File Structure

```
tests/
├── conftest.py              # Global fixtures (already exists)
├── conftest_factories.py    # JobFactory (already exists)
├── test_smoke.py            # Infrastructure smoke tests (already exists)
├── test_models.py           # NEW: UNIT-01 (Pydantic models)
├── test_salary.py           # NEW: UNIT-02 (salary normalization)
├── test_scorer.py           # NEW: UNIT-03, UNIT-04 (scoring + breakdown)
├── test_dedup.py            # NEW: UNIT-05, UNIT-06 (exact + fuzzy dedup)
├── resume_ai/
│   └── test_validator.py    # NEW: UNIT-07 (anti-fabrication)
└── test_delta.py            # NEW: UNIT-08 (delta detection)
```

### Pattern 1: Direct Pydantic Model Construction for Validation Tests

**What:** Test Pydantic model validation by constructing models directly with valid/invalid data, asserting `ValidationError` for bad inputs.

**When to use:** UNIT-01 -- testing that field validators, type constraints, and cross-field validators work correctly.

**Example:**
```python
import pytest
from pydantic import ValidationError
from models import Job, JobStatus, SearchQuery, CandidateProfile


class TestJob:
    def test_valid_job(self):
        job = Job(platform="indeed", title="Engineer", company="ACME", url="https://example.com")
        assert job.platform == "indeed"

    def test_invalid_platform_rejected(self):
        with pytest.raises(ValidationError):
            Job(platform="linkedin", title="X", company="Y", url="https://x.com")

    def test_salary_max_gte_min(self):
        with pytest.raises(ValidationError, match="salary_max must be >= salary_min"):
            Job(platform="indeed", title="X", company="Y", url="https://x.com",
                salary_min=200000, salary_max=100000)

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            Job(platform="indeed", title="X", company="Y", url="https://x.com", score=0)
        with pytest.raises(ValidationError):
            Job(platform="indeed", title="X", company="Y", url="https://x.com", score=6)
```

### Pattern 2: Parametrized Salary Parsing

**What:** Use `@pytest.mark.parametrize` to test many input formats against expected outputs in a compact table.

**When to use:** UNIT-02 -- salary module has 10+ input formats that need coverage.

**Example:**
```python
import pytest
from salary import parse_salary, parse_salary_ints, NormalizedSalary


@pytest.mark.parametrize("input_text, expected_min, expected_max, expected_currency", [
    ("$150,000 - $200,000", 150000, 200000, "USD"),
    ("$85/hr", 85 * 2080, 85 * 2080, "USD"),
    ("USD 224,400.00 - 283,800.00 per year", 224400, 283800, "USD"),
    ("$175000", 175000, 175000, "USD"),
    ("$150K - $200K", 150000, 200000, "USD"),
    ("150000-180000 CAD", 150000, 180000, "CAD"),
    (None, None, None, "USD"),
    ("", None, None, "USD"),
    ("Competitive", None, None, "USD"),
])
def test_parse_salary(input_text, expected_min, expected_max, expected_currency):
    result = parse_salary(input_text)
    assert result.min_annual == expected_min
    assert result.max_annual == expected_max
    assert result.currency == expected_currency
```

### Pattern 3: Scorer with Explicit Profile (No Settings Singleton)

**What:** Construct `CandidateProfile` and `ScoringWeights` directly, bypassing `get_settings()`. This avoids config file dependencies entirely.

**When to use:** UNIT-03, UNIT-04 -- scorer tests need a controlled, deterministic profile.

**Critical detail:** The `JobScorer.__init__()` calls `get_settings()` if no profile/weights are passed. To keep these pure unit tests, ALWAYS pass both `profile` and `weights` explicitly.

**Example:**
```python
from models import CandidateProfile, Job
from config import ScoringWeights
from scorer import JobScorer


def make_scorer():
    profile = CandidateProfile(
        target_titles=["Senior Software Engineer", "Principal Engineer", "Staff Engineer"],
        tech_keywords=["python", "kubernetes", "terraform", "docker", "aws"],
        desired_salary_usd=200_000,
    )
    weights = ScoringWeights()  # default weights: title=2, tech=2, remote=1, salary=1
    return JobScorer(profile=profile, weights=weights)


def test_perfect_match_scores_5():
    scorer = make_scorer()
    job = Job(
        platform="indeed", title="Principal Engineer", company="ACME",
        url="https://x.com", location="Remote",
        description="python kubernetes terraform docker aws gcp",
        salary_max=250000,
    )
    score = scorer.score_job(job)
    assert score == 5
```

### Pattern 4: Dedup Testing with Controlled Job Lists

**What:** Construct lists of `Job` objects with known company/title values and verify dedup behavior.

**When to use:** UNIT-05, UNIT-06 -- test exact and fuzzy deduplication.

**Example:**
```python
from dedup import fuzzy_deduplicate, _normalize_company
from models import Job


def make_job(company, title, platform="indeed", **kwargs):
    return Job(
        platform=platform, title=title, company=company,
        url=f"https://example.com/{company.lower()}", **kwargs,
    )


class TestExactDedup:
    def test_same_key_deduplicates(self):
        jobs = [
            make_job("Google Inc", "Staff Engineer"),
            make_job("Google Inc", "Staff Engineer"),
        ]
        result = fuzzy_deduplicate(jobs)
        assert len(result) == 1


class TestFuzzyDedup:
    def test_inc_llc_variants_merge(self):
        jobs = [
            make_job("Google Inc.", "Staff Engineer"),
            make_job("Google LLC", "Staff Engineer"),
        ]
        result = fuzzy_deduplicate(jobs)
        assert len(result) == 1
        assert len(result[0].company_aliases) >= 1
```

### Pattern 5: Anti-Fabrication with Known Diff Pairs

**What:** Provide original + tailored text pairs where fabrications are deliberately introduced, verify the validator catches them.

**When to use:** UNIT-07 -- resume anti-fabrication validator.

**Example:**
```python
from resume_ai.validator import validate_no_fabrication


class TestAntiFabrication:
    def test_identical_text_is_valid(self):
        text = "Worked at Google using Python and Kubernetes. Achieved 50% improvement."
        result = validate_no_fabrication(text, text)
        assert result.is_valid

    def test_new_company_detected(self):
        original = "Worked at Google using Python."
        tailored = "Worked at Google and Microsoft using Python."
        result = validate_no_fabrication(original, tailored)
        assert not result.is_valid
        assert "microsoft" in [c.lower() for c in result.new_companies]
```

### Pattern 6: Delta Detection via DB Fixture

**What:** UNIT-08 tests delta detection logic (`remove_stale_jobs`, `first_seen_at`/`last_seen_at`). These touch the DB but are logically testing the delta algorithm, not CRUD operations.

**When to use:** UNIT-08 -- uses `_fresh_db` autouse fixture for isolation.

**Example:**
```python
import webapp.db as db_module
from datetime import datetime


class TestDeltaDetection:
    def test_new_job_gets_first_seen_timestamp(self):
        db_module.upsert_job({
            "id": "j1", "platform": "indeed", "title": "Engineer",
            "company": "ACME", "url": "https://example.com",
        })
        job = db_module.get_job("acme::engineer")
        assert job["first_seen_at"] is not None

    def test_stale_jobs_removed(self):
        # Insert a job with old timestamp
        db_module.upsert_job({...})
        # Run remove_stale_jobs with a newer timestamp
        removed = db_module.remove_stale_jobs(["indeed"], datetime.now().isoformat())
        assert removed == 1
```

### Anti-Patterns to Avoid

- **Calling `get_settings()` in scorer/model tests:** This loads `config.yaml` and creates the settings singleton. Pass `CandidateProfile` and `ScoringWeights` explicitly to `JobScorer`. If you forget and `get_settings()` is called, it will try to load `config.yaml` from CWD -- in tests this may find the project's real config.yaml (not test_config.yaml), causing non-deterministic behavior.

- **Testing dedup_key() only via fuzzy_deduplicate():** Test `Job.dedup_key()` directly to verify the normalization logic (stripping Inc, LLC, etc.) before testing the full dedup pipeline. This makes failures easier to diagnose.

- **Hardcoding salary parse results without checking display format:** The `NormalizedSalary.display` field is user-facing. Test it alongside `min_annual`/`max_annual` to catch formatting regressions.

- **Skipping edge cases for empty/None inputs:** Every public function should be tested with None, empty string, and whitespace-only inputs. `parse_salary(None)`, `parse_salary("")`, `fuzzy_deduplicate([])`, `validate_no_fabrication("", "")`.

- **Marking UNIT-08 delta tests as `@pytest.mark.integration`:** While they touch the DB, the `_fresh_db` fixture is autouse -- these tests run in the same isolation context as all other tests. Mark them `@pytest.mark.unit` for consistency with the phase scope. The distinction is: UNIT tests verify a module's logic; INTEGRATION tests verify cross-module wiring. Delta detection logic is a single module's responsibility.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test job objects | Manual dict-to-Job conversion | `JobFactory(company="X", title="Y")` | Factory handles all required fields, Pydantic validation runs automatically |
| Salary format test matrix | Separate test function per format | `@pytest.mark.parametrize` with tuples | Compact, DRY, easy to extend |
| Scoring profile for tests | Loading from config.yaml | Direct `CandidateProfile(target_titles=[...], tech_keywords=[...])` | Deterministic, no file I/O, no singleton |
| Company name normalization edge cases | Regex testing one-at-a-time | Parametrize `_normalize_company()` directly | Tests the private function that drives both dedup passes |

**Key insight:** Every module under test was designed as a pure function or a class with injectable dependencies. The scorer accepts `profile` and `weights` as constructor args. The salary parser takes a string and returns a dataclass. The dedup takes a list and returns a list. The validator takes two strings and returns a Pydantic model. This design makes unit testing straightforward -- no mocking required.

## Common Pitfalls

### Pitfall 1: Scorer Tests that Depend on Config Singleton

**What goes wrong:** Tests call `JobScorer()` without passing `profile` or `weights`. The constructor calls `get_settings()`, which loads `config.yaml`. If the settings singleton was already initialized (e.g., by a preceding test), the scorer uses stale/wrong profile data. If no config.yaml exists, it crashes.

**Why it happens:** The `JobScorer.__init__` has default args that call `get_settings()` as a fallback.

**How to avoid:** Always pass `profile=CandidateProfile(...)` and `weights=ScoringWeights()` explicitly in unit tests. Create a `make_scorer()` helper that constructs both deterministically.

**Warning signs:** Tests pass in isolation but fail when run with other tests. Different score results depending on test execution order.

### Pitfall 2: Salary Parser K-Notation vs Small Number Ambiguity

**What goes wrong:** The salary parser has a special case: numbers < 1000 without explicit K notation or period markers are treated as K-shorthand (e.g., "150" becomes 150000). Tests that don't account for this heuristic will get unexpected results.

**Why it happens:** The parser is designed for real-world salary strings where "150" almost always means "$150K", not "$150/year". But test inputs may not follow this convention.

**How to avoid:** Test both sides of the < 1000 threshold explicitly. Include test cases like `"150"` (= 150000), `"1500"` (= 1500, NOT 1500000), `"$85/hr"` (= 85 * 2080).

**Warning signs:** Salary test expecting `150` to parse as `150` annual when the parser converts it to `150000`.

### Pitfall 3: Dedup Key Normalization vs Fuzzy Normalization Mismatch

**What goes wrong:** `Job.dedup_key()` (in `models.py`) and `_normalize_company()` (in `dedup.py`) both strip company suffixes but use DIFFERENT lists. `dedup_key()` strips: `" inc."`, `" inc"`, `" llc"`, `" ltd"`, `","`. `_normalize_company()` strips: `" incorporated"`, `" corporation"`, `" company"`, `" corp."`, `" corp"`, `" inc."`, `" inc"`, `" llc"`, `" ltd."`, `" ltd"`, `" co."`. Tests may pass at one level but fail at the other.

**Why it happens:** The two normalization functions were written independently. `dedup_key()` is for exact dedup (Pass 1); `_normalize_company()` is for fuzzy dedup (Pass 2). They intentionally have different scope.

**How to avoid:** Test both functions independently. `dedup_key()` tests go in `test_models.py`; `_normalize_company()` tests go in `test_dedup.py`. Document the difference in test comments.

**Warning signs:** A company like "Google Corp." deduplicates in fuzzy pass but not in exact pass (or vice versa).

### Pitfall 4: Validator Entity Extraction is Heuristic

**What goes wrong:** The `_extract_entities()` function uses regex heuristics for companies (capitalized multi-word sequences), skills (keyword dictionary + CamelCase + ALL_CAPS), and metrics (patterns like `$1.2M`, `50%`, `10x`). Some test inputs may not match the heuristic patterns.

**Why it happens:** Entity extraction without NLP is inherently imprecise. The regex patterns have specific requirements (e.g., company names must be multi-word and capitalized).

**How to avoid:** Test with realistic resume text, not contrived short strings. Use multi-word company names ("Translucent Computing", not just "Google"). Include explicit CamelCase tech terms and ALL_CAPS acronyms in test text.

**Warning signs:** Test expects "google" to be detected as a company name, but the regex requires multi-word capitalized sequences (single word "Google" alone won't match the multi-word pattern, but will match the "at Google" pattern).

### Pitfall 5: Delta Detection Timestamp Precision

**What goes wrong:** `remove_stale_jobs()` compares `last_seen_at` against `run_timestamp` using string comparison. If timestamps are generated in the same second, the comparison may produce unexpected results (equal timestamps are NOT considered stale -- the condition is `last_seen_at < ?`).

**Why it happens:** ISO timestamps compared as strings have second-level granularity. Two jobs inserted within the same second may have identical timestamps.

**How to avoid:** In delta detection tests, use explicitly different timestamps with a clear time gap. Set `last_seen_at` to a past time and `run_timestamp` to a future time, or use `time.sleep(0.01)` between operations.

**Warning signs:** Delta tests pass locally (fast enough to generate different timestamps) but flake in CI (too fast, same timestamp).

## Code Examples

Verified patterns from codebase analysis:

### Module-Under-Test Function Signatures (for test design)

```python
# models.py
class Job(BaseModel):
    def dedup_key(self) -> str: ...

# salary.py
def parse_salary(text: str | None, default_currency: str = "USD") -> NormalizedSalary: ...
def parse_salary_ints(min_val: int | None, max_val: int | None, currency: str = "USD") -> NormalizedSalary: ...

# scorer.py
class JobScorer:
    def __init__(self, profile: CandidateProfile | None = None, weights: ScoringWeights | None = None): ...
    def score_job(self, job: Job) -> int: ...
    def score_job_with_breakdown(self, job: Job) -> tuple[int, ScoreBreakdown]: ...
    def score_batch(self, jobs: list[Job]) -> list[Job]: ...

# dedup.py
def fuzzy_deduplicate(jobs: list[Job]) -> list[Job]: ...
def _normalize_company(name: str) -> str: ...  # private but useful to test directly

# resume_ai/validator.py
def validate_no_fabrication(original_text: str, tailored_text: str) -> ValidationResult: ...
def _extract_entities(text: str) -> dict[str, set[str]]: ...  # private but useful to test directly

# webapp/db.py (delta detection)
def remove_stale_jobs(searched_platforms: list[str], run_timestamp: str) -> int: ...
def upsert_job(job: dict) -> None: ...  # sets first_seen_at, last_seen_at
```

### Scorer Factor Breakdown (for designing test cases)

The scorer computes a weighted raw score and maps it to 1-5:

```python
# Factor ranges:
#   title_pts:  0 (no match), 1 (keyword match), 2 (exact target title match)
#   tech_pts:   0 (<2 keywords), 1 (2-4 keywords), 2 (5+ keywords)
#   remote_pts: 0 (not remote/Ontario), 1 (remote or Ontario)
#   salary_pts: 0 (below $200K), 1 ($200K+ max or min)

# Default weights (ScoringWeights defaults):
#   title_match=2.0, tech_overlap=2.0, remote=1.0, salary=1.0

# Raw score formula:
#   raw = title_pts * (title_match/2) + tech_pts * (tech_overlap/2)
#         + remote_pts * remote + salary_pts * salary

# With defaults: raw = title_pts + tech_pts + remote_pts + salary_pts
# Max raw = 2 + 2 + 1 + 1 = 6

# Mapping:
#   raw >= 5 -> 5
#   raw >= 4 -> 4
#   raw >= 3 -> 3
#   raw >= 2 -> 2
#   else     -> 1
```

### Salary Format Reference (for parametrize matrix)

```python
# From salary.py source code -- all formats it handles:
# 1. Indeed range:      "$150,000 - $200,000"
# 2. Indeed hourly:     "$85/hr" or "$85 an hour"  (x2080)
# 3. Dice verbose:     "USD 224,400.00 - 283,800.00 per year"
# 4. Dice short:       "$175000"
# 5. K notation:       "$150K - $200K"
# 6. CAD suffix:       "150000-180000 CAD"
# 7. Monthly:          "$15,000/month"  (x12)
# 8. Raw ints (API):   parse_salary_ints(200000, 300000)
# 9. RemoteOK quirk:   parse_salary_ints(200000, 0)  -> max=200000
# 10. None/empty:      parse_salary(None) -> NormalizedSalary(min=None, max=None)
# 11. Unparseable:     parse_salary("Competitive") -> NormalizedSalary(min=None)
# 12. GBP:             "GBP 100,000"
# 13. EUR:             "EUR 120,000"
# 14. Small number:    "150" -> treated as 150K = 150000 (heuristic)
```

### dedup_key() Normalization Rules (for test design)

```python
# From models.py Job.dedup_key():
# 1. company.lower().strip()
# 2. Remove: " inc.", " inc", " llc", " ltd", ","
# 3. title.lower().strip()
# 4. Format: "{company}::{title}"
#
# Examples:
#   ("Google Inc.", "Staff Engineer")  -> "google::staff engineer"
#   ("Google, Inc", "Staff Engineer")  -> "google::staff engineer"
#   ("GOOGLE LLC", "staff engineer")   -> "google::staff engineer"
#   ("Google", "Staff Engineer")       -> "google::staff engineer"
```

### Validator Entity Categories (for test design)

```python
# From resume_ai/validator.py _extract_entities():
#
# Companies extracted by:
#   1. Capitalized multi-word sequences: "Translucent Computing" (2+ words starting uppercase)
#   2. Words after "at " or "for " that start uppercase: "at Google"
#   NOTE: Single capitalized words alone (e.g., just "Google" in running text)
#         are NOT extracted by pattern #1, but ARE extracted by pattern #2 if preceded by "at"/"for"
#
# Skills extracted by:
#   1. Known keyword dictionary (_TECH_KEYWORDS): ~170 terms like "python", "kubernetes", "langchain"
#   2. CamelCase terms: "FastAPI", "LangGraph"
#   3. ALL_CAPS terms (2+ chars): "AWS", "GKE", "EKS"
#
# Metrics extracted by:
#   1. Percentages: "50%", "200%"
#   2. Dollar amounts: "$1.2M", "$200,000"
#   3. USD amounts: "USD 224,400.00"
#   4. Multipliers: "10x", "3x"
#   5. Large standalone numbers (3+ digits): "500", "1000"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One test function per input variant | `@pytest.mark.parametrize` tables | pytest 2.0+ (stable) | 10x fewer test functions, same coverage |
| Monkeypatch settings in each test | autouse `_reset_settings` fixture | Phase 9 (this project) | Zero-effort settings isolation |
| Testing via public API only | Testing private helpers directly for complex modules | General best practice | Easier debugging when `_normalize_company()` or `_extract_entities()` breaks |

**Deprecated/outdated:**
- None relevant to this phase. The testing stack is current.

## Open Questions

1. **UNIT-08 Boundary: Pure Unit vs Light Integration**
   - What we know: Delta detection (`remove_stale_jobs`, `first_seen_at`/`last_seen_at`) requires the SQLite DB. The `_fresh_db` autouse fixture provides clean in-memory isolation.
   - What's unclear: Whether UNIT-08 should be marked `@pytest.mark.unit` or `@pytest.mark.integration`. The requirement says "unit tests" but the delta logic inherently touches the DB.
   - Recommendation: Mark as `@pytest.mark.unit`. The DB fixture is autouse -- all tests already run with it. The test verifies delta *logic*, not CRUD operations. Place in `tests/test_delta.py` alongside the other unit test files. Phase 11 (DB integration tests) will cover CRUD operations more thoroughly.

2. **Testing `_normalize_company()` and `_extract_entities()` Directly**
   - What we know: These are private functions (prefixed with `_`). Testing them directly is useful because they contain the core logic that `fuzzy_deduplicate()` and `validate_no_fabrication()` rely on.
   - What's unclear: Whether testing private functions violates project conventions.
   - Recommendation: Test them directly. The alternative -- testing only through the public API -- makes failure diagnosis harder. Use `from dedup import _normalize_company` explicitly. Comment the tests to explain why private function testing is warranted.

3. **Scorer Weight Customization Tests**
   - What we know: `ScoringWeights` allows configurable weights. The scorer uses these weights in the raw score formula.
   - What's unclear: Whether to test with non-default weights.
   - Recommendation: Test with default weights for correctness (UNIT-03/04). Add 1-2 tests with custom weights to verify the weighting formula works (e.g., zero out salary weight and verify salary doesn't affect score).

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `models.py` (full file -- Pydantic models, `dedup_key()`, validators)
- Codebase analysis: `salary.py` (full file -- `parse_salary()`, `parse_salary_ints()`, format handling)
- Codebase analysis: `scorer.py` (full file -- `JobScorer`, `ScoreBreakdown`, factor functions)
- Codebase analysis: `dedup.py` (full file -- `fuzzy_deduplicate()`, `_normalize_company()`, `_fuzzy_merge_group()`)
- Codebase analysis: `resume_ai/validator.py` (full file -- `validate_no_fabrication()`, `_extract_entities()`)
- Codebase analysis: `webapp/db.py` (lines 340-362 -- `remove_stale_jobs()`, lines 214-316 -- `upsert_job()` with `first_seen_at`/`last_seen_at`)
- Codebase analysis: `tests/conftest.py` (full file -- existing fixtures and guards)
- Codebase analysis: `tests/test_smoke.py` (full file -- existing smoke tests)
- Codebase analysis: `pyproject.toml` (full file -- pytest config, markers, coverage config)

### Secondary (MEDIUM confidence)
- Phase 9 research and context documents (established test infrastructure patterns)
- `tests/fixtures/test_config.yaml` (safe defaults for test settings)
- `tests/conftest_factories.py` (JobFactory definition)

### Tertiary (LOW confidence)
- None -- all findings from direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and tested in Phase 9 smoke tests
- Architecture: HIGH -- Test structure follows 1:1 source mapping established in Phase 9; all modules under test are pure functions with clear signatures
- Pitfalls: HIGH -- Every pitfall identified from reading actual source code (scorer constructor fallback, salary K-notation heuristic, dual normalization functions, validator regex patterns, timestamp precision)

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- stable domain, source modules unlikely to change before tests are written)
