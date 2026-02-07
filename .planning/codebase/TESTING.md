# Testing Patterns

**Analysis Date:** 2026-02-07

## Current State

**No automated tests exist.** Test infrastructure is configured but no test files are present.
- `pyproject.toml` includes `pytest>=8.0.0` in dev dependencies
- `pytest.ini_options` configured: `testpaths = ["tests"]`
- No `tests/` directory exists
- All validation is manual (human-in-the-loop at critical checkpoints)

## Test Framework Setup

**Runner:**
- pytest 8.0.0+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
- Assertion library: pytest's built-in assertions (no external dependency)

**Run Commands:**
```bash
# Run all tests (when tests directory is created)
pytest

# Watch mode (requires pytest-watch plugin — not in dependencies)
pytest --watch

# Coverage (requires pytest-cov plugin — not in dependencies)
pytest --cov
```

**Installation:**
```bash
pip install -e ".[dev]"  # Installs pytest + ruff
```

## Test File Organization

**Location:** Would go in `tests/` directory (does not yet exist)

**Naming Pattern:** `test_{module}.py` or `{module}_test.py`
- Test modules for `scorer.py` would be: `tests/test_scorer.py`
- Test modules for `platforms/indeed.py` would be: `tests/test_indeed.py` or `tests/platforms/test_indeed.py`
- Conftest fixtures would go in: `tests/conftest.py`

**Structure:**
```
tests/
├── conftest.py                # Shared fixtures
├── test_models.py             # Pydantic model validation
├── test_scorer.py             # Scoring logic
├── test_form_filler.py        # Form field identification
├── test_remoteok.py           # RemoteOK API client
└── platforms/
    ├── __init__.py
    ├── test_indeed.py         # Indeed search + login (mocked browser)
    ├── test_dice.py           # Dice search + login (mocked browser)
    └── test_stealth.py        # Browser context factory
```

## What Needs Testing

**Priority 1 (Core Logic):**
- `models.py` — Pydantic model validation (especially `Job.dedup_key()`)
- `scorer.py` — Job scoring logic across all scoring factors
- `form_filler.py` — Field identification heuristics

**Priority 2 (Business Logic):**
- `remoteok.py` — API parsing, filtering, job extraction (can be tested without browser)
- `config.py` — Directory creation, credential validation
- Deduplication across platforms

**Priority 3 (Platform Integration — requires mocking):**
- `platforms/indeed.py` — Search URL construction, job card extraction
- `platforms/dice.py` — Two-step login flow, selector parsing
- `orchestrator.py` — Phase execution, job aggregation, scoring

## Testing Patterns & Examples

### Model Validation (pytest)

```python
# tests/test_models.py
from models import Job, JobStatus, SearchQuery, CandidateProfile

def test_job_status_enum():
    """JobStatus values are string enums for JSON serialization."""
    assert JobStatus.SCORED.value == "scored"
    assert isinstance(JobStatus.DISCOVERED, str)

def test_job_dedup_key():
    """dedup_key normalizes company name and title."""
    job = Job(
        title="Senior Engineer",
        company="Example Inc.",
        url="https://example.com/job/1",
    )
    assert job.dedup_key() == "example::senior engineer"

def test_job_salary_validation():
    """salary_max must be >= salary_min."""
    with pytest.raises(ValueError, match="salary_max must be >= salary_min"):
        Job(
            title="Role",
            company="Company",
            url="https://example.com",
            salary_min=100000,
            salary_max=50000,  # Invalid
        )

def test_search_query_defaults():
    """SearchQuery applies platform-specific defaults."""
    q = SearchQuery(query="python engineer", platform="indeed")
    assert q.location == ""  # Indeed/Dice use URL params for remote

    q_remote = SearchQuery(query="python engineer", platform="remoteok")
    assert q_remote.location == "Remote"
```

### Scorer Tests

```python
# tests/test_scorer.py
from scorer import JobScorer
from models import Job, CandidateProfile

def test_title_score_exact_match():
    """Title score: exact target title match = 2."""
    scorer = JobScorer()
    assert scorer._title_score("Principal Engineer") == 2
    assert scorer._title_score("Staff Software Engineer") == 2

def test_title_score_keyword_match():
    """Title score: keyword match (senior/lead/etc) = 1."""
    scorer = JobScorer()
    assert scorer._title_score("Senior Developer") == 1
    assert scorer._title_score("DevOps Lead") == 1

def test_title_score_no_match():
    """Title score: no match = 0."""
    scorer = JobScorer()
    assert scorer._title_score("Sales Representative") == 0

def test_tech_score_strong_overlap():
    """Tech score: 5+ keyword matches = 2."""
    job = Job(
        title="Engineer",
        company="Company",
        url="https://example.com",
        description="kubernetes python fastapi terraform prometheus grafana",
        tags=["python", "k8s"],
    )
    scorer = JobScorer()
    assert scorer._tech_score(job) == 2

def test_location_score_remote():
    """Location score: remote = 1."""
    scorer = JobScorer()
    assert scorer._location_score("Remote") == 1
    assert scorer._location_score("Work from home") == 1

def test_location_score_ontario():
    """Location score: Ontario/Toronto/Canada = 1."""
    scorer = JobScorer()
    assert scorer._location_score("Toronto, Ontario") == 1
    assert scorer._location_score("Ontario") == 1

def test_salary_score():
    """Salary score: meets $200K+ target = 1."""
    job_high = Job(
        title="Role",
        company="Company",
        url="https://example.com",
        salary_min=250000,
    )
    job_low = Job(
        title="Role",
        company="Company",
        url="https://example.com",
        salary_min=100000,
    )
    scorer = JobScorer()
    assert scorer._salary_score(job_high) == 1
    assert scorer._salary_score(job_low) == 0

def test_overall_score_mapping():
    """Overall score maps raw points to 1-5 scale."""
    scorer = JobScorer()

    # Raw 5 → score 5
    job = Job(
        title="Principal Engineer",  # 2
        company="Company",
        url="https://example.com",
        description="kubernetes terraform prometheus",  # 2
        location="Remote",  # 1
        salary_min=250000,  # 1
        # Total: 6 raw → maps to 5
    )
    assert scorer.score_job(job) == 5

def test_score_batch():
    """score_batch scores all jobs and sorts descending."""
    jobs = [
        Job(title="Principal Engineer", company="A", url="https://a.com"),
        Job(title="Sales Rep", company="B", url="https://b.com"),
        Job(title="Senior Engineer", company="C", url="https://c.com"),
    ]
    scorer = JobScorer()
    scored = scorer.score_batch(jobs)

    # Should be sorted highest score first
    assert scored[0].score >= scored[1].score >= scored[2].score
    assert all(j.status == JobStatus.SCORED for j in scored)
```

### Form Filler Tests

```python
# tests/test_form_filler.py
from form_filler import FormFiller, _FIELD_KEYWORDS
from models import CandidateProfile
from unittest.mock import MagicMock

def test_field_keywords_coverage():
    """All expected form field types have keywords."""
    expected_keys = {
        "first_name", "last_name", "email", "phone", "location",
        "github", "website", "experience", "current_title",
        "current_company", "salary", "start_date", "education",
        "authorization", "relocate", "hear_about",
    }
    assert set(_FIELD_KEYWORDS.keys()) == expected_keys

def test_identify_element_by_name():
    """_identify() matches field by name attribute."""
    filler = FormFiller()
    mock_elem = MagicMock()
    mock_elem.get_attribute.side_effect = lambda attr: {
        "name": "firstName",
        "id": None,
        "placeholder": None,
        "aria-label": None,
    }.get(attr)
    mock_elem.evaluate.return_value = ""  # No associated label

    assert filler._identify(mock_elem) == "first_name"

def test_identify_element_by_label():
    """_identify() matches field by associated label text."""
    filler = FormFiller()
    mock_elem = MagicMock()
    mock_elem.get_attribute.side_effect = lambda attr: {
        "name": None,
        "id": "field_1",
        "placeholder": None,
        "aria-label": None,
    }.get(attr)
    # Simulates: label[for="field_1"] contains "Current Title"
    mock_elem.evaluate.return_value = "Current Title"

    assert filler._identify(mock_elem) == "current_title"

def test_value_for_all_fields():
    """_value_for() maps all field keys to profile values."""
    profile = CandidateProfile()
    filler = FormFiller(profile)

    assert filler._value_for("first_name") == "Patryk"
    assert filler._value_for("email") == "pgolabek@gmail.com"
    assert filler._value_for("phone") == "416-708-9839"
    assert filler._value_for("github") == profile.github
    assert filler._value_for("unknown_field") is None
```

### RemoteOK API Tests (No Browser)

```python
# tests/test_remoteok.py
import pytest
import json
from unittest.mock import AsyncMock, patch
from remoteok import RemoteOKPlatform
from models import SearchQuery, Job

@pytest.mark.asyncio
async def test_remoteok_parse_valid_entry():
    """_parse() converts valid API entry to Job."""
    platform = RemoteOKPlatform()
    entry = {
        "id": 123,
        "position": "Senior Engineer",
        "company": "TechCorp",
        "location": "Remote",
        "url": "/jobs/senior-engineer-456",
        "apply_url": "https://techcorp.careers/apply",
        "description": "<p>We seek a talented engineer</p>",
        "tags": ["python", "kubernetes"],
        "salary_min": 180000,
        "salary_max": 220000,
        "epoch": 1707000000,
    }

    job = platform._parse(entry)
    assert job is not None
    assert job.title == "Senior Engineer"
    assert job.company == "TechCorp"
    assert job.platform == "remoteok"
    assert job.salary_min == 180000
    assert job.url == "https://remoteok.com/jobs/senior-engineer-456"

def test_remoteok_parse_invalid_entry():
    """_parse() returns None for incomplete entries."""
    platform = RemoteOKPlatform()

    # Missing position
    assert platform._parse({"company": "A", "url": "/jobs/1"}) is None
    # Missing company
    assert platform._parse({"position": "Role", "url": "/jobs/1"}) is None
    # Missing url
    assert platform._parse({"position": "Role", "company": "A"}) is None

def test_remoteok_filter_terms():
    """_filter_terms() extracts tech keywords from query."""
    platform = RemoteOKPlatform()

    # Query with recognized keywords
    terms = platform._filter_terms('"Principal Engineer" Kubernetes Python')
    assert "kubernetes" in terms
    assert "python" in terms

    # Query without keywords
    empty = platform._filter_terms("Sales Manager")
    assert empty == []

def test_remoteok_matches():
    """_matches() checks if entry has any filter terms."""
    platform = RemoteOKPlatform()

    entry_with_py = {
        "tags": ["python", "react"],
        "position": "Developer",
        "description": "Python backend work",
    }
    entry_without = {
        "tags": ["go", "rust"],
        "position": "Developer",
        "description": "Systems programming",
    }

    assert platform._matches(entry_with_py, ["python"]) is True
    assert platform._matches(entry_without, ["python"]) is False

    # No filter terms = match everything
    assert platform._matches(entry_without, []) is True

@pytest.mark.asyncio
async def test_remoteok_search_filters_by_salary():
    """search() skips jobs below MIN_SALARY."""
    platform = RemoteOKPlatform()

    low_salary_entry = {
        "id": 1,
        "position": "Intern",
        "company": "StartUp",
        "url": "/jobs/1",
        "salary_min": 30000,
        "salary_max": 40000,
        "tags": ["python"],
        "description": "",
    }
    high_salary_entry = {
        "id": 2,
        "position": "Senior Engineer",
        "company": "TechCorp",
        "url": "/jobs/2",
        "salary_min": 200000,
        "salary_max": 250000,
        "tags": ["python"],
        "description": "",
    }

    with patch.object(platform.client, "get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"note": "metadata"},
            low_salary_entry,
            high_salary_entry,
        ]

        query = SearchQuery(query="python engineer", platform="remoteok")
        jobs = await platform.search(query)

        # Only high_salary_entry should pass
        assert len(jobs) == 1
        assert jobs[0].salary_min == 200000
```

## Mocking Patterns

**For browser-based tests (Indeed, Dice):**

```python
# tests/platforms/test_indeed.py
from unittest.mock import MagicMock, patch
from platforms.indeed import IndeedPlatform
from models import SearchQuery, Job

def test_indeed_search_builds_url():
    """search() constructs correct URL with query params."""
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_context.pages = [mock_page]

    platform = IndeedPlatform(mock_context)

    # Mock page methods
    mock_page.goto.return_value = None
    mock_page.query_selector_all.return_value = []  # No job cards

    query = SearchQuery(query="Python Engineer", max_pages=1)
    jobs = platform.search(query)

    # Verify goto was called with correct URL pattern
    assert mock_page.goto.called
    call_url = mock_page.goto.call_args[0][0]
    assert "python" in call_url.lower() or "Python" in call_url
    assert "indeed.com" in call_url

def test_indeed_is_logged_in():
    """is_logged_in() checks for account menu selector."""
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_context.pages = [mock_page]

    platform = IndeedPlatform(mock_context)

    # Logged in case
    mock_page.wait_for_selector.return_value = MagicMock()
    assert platform.is_logged_in() is True

    # Not logged in case
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    assert platform.is_logged_in() is False
```

**For database tests:**

```python
# tests/test_webapp_db.py
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch
from webapp import db
from models import Job

def test_upsert_job_creates_table():
    """upsert_job() initializes schema on first call."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        with patch("webapp.db.DB_PATH", db_path):
            db.init_db()

            job_dict = {
                "id": "job_1",
                "platform": "indeed",
                "title": "Engineer",
                "company": "TechCorp",
                "url": "https://example.com",
            }
            db.upsert_job(job_dict)

            # Verify job was inserted
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            count = cursor.fetchone()[0]
            assert count == 1
```

## Coverage Goals

**Target:** 80%+ coverage for core logic (scorer, form_filler, models validation)

**Run coverage:**
```bash
# Install pytest-cov first
pip install pytest-cov

# Generate coverage report
pytest --cov=. --cov-report=html

# View HTML report
open htmlcov/index.html
```

**Coverage priorities:**
- `scorer.py` — 100% (deterministic pure functions)
- `models.py` — 100% (validation logic)
- `form_filler.py` — 90%+ (heuristic matching)
- `remoteok.py` — 85%+ (filtering logic)
- `config.py` — 75%+ (env loading, directory setup)
- Platform classes (indeed.py, dice.py) — 60%+ (requires extensive mocking)

## Test Types

**Unit Tests:**
- Scope: Single function or method in isolation
- Approach: Mock dependencies (Page, BrowserContext, httpx.Client)
- Use fixtures for common setup (CandidateProfile, test jobs)
- Assert on return values and side effects
- Location: `tests/test_{module}.py`

**Integration Tests (Future):**
- Scope: Full platform workflow (login → search → extract)
- Approach: Use playwright with temporary test environment or fixture
- May require `.env.test` with test credentials
- Location: `tests/integration/test_{platform}.py`

**E2E Tests (Manual):**
- Not automated; documented in README
- Orchestrator can be run with `--headed` flag for manual inspection
- Screenshots saved to `debug_screenshots/` on failure
- Location: Covered by `orchestrator.py --platforms indeed --headed`

## Fixture Examples

```python
# tests/conftest.py
import pytest
from models import Job, CandidateProfile

@pytest.fixture
def sample_job():
    """Typical high-scoring job."""
    return Job(
        id="job_1",
        platform="indeed",
        title="Principal Engineer",
        company="TechCorp",
        location="Remote",
        url="https://indeed.com/job/1",
        description="Kubernetes Python FastAPI Terraform Prometheus",
        tags=["python", "kubernetes"],
        salary_min=250000,
        salary_max=320000,
    )

@pytest.fixture
def sample_low_score_job():
    """Low-scoring job."""
    return Job(
        id="job_2",
        platform="indeed",
        title="Sales Representative",
        company="SalesCorp",
        location="New York",
        url="https://indeed.com/job/2",
        description="Lead generation cold calling",
        salary_min=40000,
        salary_max=60000,
    )

@pytest.fixture
def candidate_profile():
    """Default candidate profile."""
    return CandidateProfile()
```

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_scorer.py

# Run specific test function
pytest tests/test_scorer.py::test_title_score_exact_match

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

---

*Testing analysis: 2026-02-07*

**Note:** This codebase does not yet have automated tests. This document serves as a blueprint for implementing pytest-based testing. Priority should be unit tests for scorer.py, models.py, and form_filler.py before adding browser automation tests.
