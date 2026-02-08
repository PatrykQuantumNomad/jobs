# Phase 13: Config Integration Tests - Research

**Researched:** 2026-02-08
**Domain:** YAML configuration loading, pydantic-settings validation, defaults, and environment variable overrides
**Confidence:** HIGH

## Summary

Phase 13 tests the `config.py` module -- the central `AppSettings` class powered by `pydantic-settings` 2.12.0 that loads operational parameters from `config.yaml` and credentials from `.env`. The test infrastructure from Phase 9 is fully operational with settings isolation (`reset_settings()` autouse fixture), in-memory DB, and network blocking. All 13 smoke tests pass, including two that verify settings singleton cleanup between tests.

The four requirements (CFG-01 through CFG-04) map directly to verified behaviors of the existing `AppSettings` class:

1. **CFG-01 (YAML loads and validates):** `AppSettings` uses a custom `settings_customise_sources` that returns `(init_settings, env_settings, dotenv_settings, YamlConfigSettingsSource)`. The YAML file loads correctly via `get_settings("tests/fixtures/test_config.yaml")` and produces typed, validated settings. Helper methods (`get_search_queries`, `build_candidate_profile`, `validate_platform_credentials`, `enabled_platforms`) are pure logic on the loaded config.

2. **CFG-02 (Validation rejects invalid values):** Pydantic v2 raises `ValidationError` for: missing required fields (`search`, `scoring`), wrong types (string where int expected), out-of-range values (`max_pages=99`, `weekdays=[7]`, `max_concurrent_applies=10`), invalid enum values (`default_mode='yolo'`), and cross-field violations (`salary_max < salary_min` on `Job`, though that is in `models.py`). All produce clear, specific error messages.

3. **CFG-03 (Defaults for optional fields):** When only `search.queries` and `scoring.{target_titles,tech_keywords}` are provided, all optional fields get documented defaults: `search.min_salary=150000`, `platforms.*.enabled=True`, `timing.nav_delay_min=2.0`, `schedule.enabled=False`, `scoring.weights.title_match=2.0`, `apply.default_mode=semi_auto`, etc.

4. **CFG-04 (Env var overrides YAML):** Source priority is `init_kwargs > env_vars > dotenv > yaml`. Top-level fields (e.g., `CANDIDATE_DESIRED_SALARY_USD`, `DICE_EMAIL`) override directly by env var name. Nested sections (e.g., `TIMING`, `PLATFORMS`) can be overridden as JSON env vars but NOT with dot-separated or underscore-delimited field names because `env_nested_delimiter` is `None`. This is a design constraint, not a bug.

**Primary recommendation:** Write a single test file `tests/test_config.py` with four test classes mapping to CFG-01 through CFG-04. Use `tmp_path` for creating test YAML files with specific scenarios. Isolate from the real `.env` by setting `AppSettings.model_config['env_file'] = '/dev/null'` in a fixture. Use `monkeypatch.setenv` for env var override tests. Mark all tests `@pytest.mark.integration`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2+ | Test framework | Already installed, Phase 9 |
| pydantic | 2.12.5 | Validation engine | Already installed, production dep |
| pydantic-settings[yaml] | 2.12.0 | Settings loading from YAML, env, dotenv | Already installed, production dep |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0+ | Write test YAML files programmatically | Already installed (pydantic-settings[yaml] dep); use for creating temp YAML configs in tests |
| pytest-cov | 7.0.0 | Coverage reporting | Already configured; `config.py` is in coverage source list |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tmp_path` + PyYAML for temp configs | Hardcoded YAML strings + `StringIO` | `tmp_path` is cleaner, creates real files, auto-cleanup; pydantic-settings `YamlConfigSettingsSource` expects a file path, not a stream |
| `monkeypatch.setenv` for env overrides | `os.environ` direct manipulation | `monkeypatch` is safer -- auto-reverted after test; `os.environ` requires manual cleanup |

**Installation:** No new packages needed. All dependencies already present.

## Architecture Patterns

### Recommended Test File Structure

```
tests/
├── conftest.py              # Global fixtures (already exists -- settings reset, fresh DB)
├── test_config.py           # NEW: CFG-01 through CFG-04
└── fixtures/
    └── test_config.yaml     # Already exists -- safe defaults for automated tests
```

### Pattern 1: Test Config Isolation Fixture

**What:** A fixture that loads settings from a custom YAML file while isolating from the real `.env` file, then restores original `model_config` values after the test.

**When to use:** Every config test that calls `AppSettings()` or `get_settings()`.

**Example:**
```python
@pytest.fixture
def config_from_yaml(tmp_path):
    """Create AppSettings from a custom YAML, isolated from real .env."""
    import yaml
    from config import AppSettings, reset_settings

    original_yaml = AppSettings.model_config.get("yaml_file")
    original_env = AppSettings.model_config.get("env_file")

    def _load(yaml_data: dict) -> AppSettings:
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(yaml.dump(yaml_data))

        reset_settings()
        AppSettings.model_config["yaml_file"] = str(yaml_path)
        AppSettings.model_config["env_file"] = "/dev/null"
        return AppSettings()

    yield _load

    # Restore original config
    AppSettings.model_config["yaml_file"] = original_yaml
    AppSettings.model_config["env_file"] = original_env
    reset_settings()
```

### Pattern 2: Env Var Override with monkeypatch

**What:** Use `monkeypatch.setenv` to set environment variables that override YAML/default values, verifying pydantic-settings source precedence.

**When to use:** CFG-04 tests.

**Example:**
```python
def test_env_overrides_yaml(config_from_yaml, monkeypatch):
    # Top-level field override
    monkeypatch.setenv("CANDIDATE_DESIRED_SALARY_USD", "300000")

    settings = config_from_yaml(MINIMAL_YAML)
    assert settings.candidate_desired_salary_usd == 300000
```

### Pattern 3: Parametrized Validation Error Tests

**What:** Use `@pytest.mark.parametrize` with invalid YAML data and expected error details.

**When to use:** CFG-02 tests for comprehensive coverage of invalid inputs.

**Example:**
```python
@pytest.mark.parametrize("bad_yaml, expected_loc, expected_type", [
    ({}, ("search",), "missing"),
    ({"search": {"queries": [{"title": "x"}]}, "scoring": {"target_titles": ["x"], "tech_keywords": ["y"]}}, None, None),  # valid baseline
    ({"search": {"min_salary": "not-a-number", "queries": [{"title": "x"}]}, ...}, ("search", "min_salary"), "int_parsing"),
])
def test_validation_rejects_invalid(config_from_yaml, bad_yaml, expected_loc, expected_type):
    ...
```

### Anti-Patterns to Avoid

- **Depending on real `.env` file:** Tests MUST NOT read from the project's `.env` because it contains real credentials and makes tests environment-dependent. Always set `env_file = '/dev/null'`.
- **Forgetting to reset `model_config`:** `AppSettings.model_config` is a class-level dict that persists across tests. If a test modifies `yaml_file` or `env_file` without restoring, subsequent tests may fail unpredictably.
- **Testing `get_settings()` singleton behavior without `reset_settings()`:** The singleton cache means `get_settings()` returns the same object after first call. The autouse `_reset_settings` fixture handles this, but tests must call `reset_settings()` explicitly if they modify `model_config` mid-test.
- **Asserting env var overrides on nested fields with `__` delimiter:** `env_nested_delimiter` is `None` in this project. Env vars like `TIMING__NAV_DELAY_MIN` will NOT work. Nested overrides require JSON env vars for the entire section (e.g., `TIMING='{"nav_delay_min": 99}'`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temp YAML file creation | Manual file I/O with cleanup | `tmp_path` fixture + `yaml.dump()` | Pytest auto-cleanup, no orphaned temp files |
| Env var manipulation | Direct `os.environ` with try/finally | `monkeypatch.setenv` / `monkeypatch.delenv` | Auto-reverted after test, exception-safe |
| Validation error assertion | Catching `Exception` and string matching | `pytest.raises(ValidationError)` + checking `e.errors()` | Type-safe, structured error access |
| Config test isolation | Per-test manual cleanup code | Fixture with yield + teardown | Guarantee cleanup even on test failure |

**Key insight:** The `_reset_settings` autouse fixture from Phase 9 already handles the singleton reset, but `model_config` is a class dict that persists. Tests that modify `model_config['yaml_file']` or `model_config['env_file']` need their own restoration fixture.

## Common Pitfalls

### Pitfall 1: model_config Leakage Between Tests

**What goes wrong:** A test sets `AppSettings.model_config['yaml_file'] = 'custom.yaml'` but crashes before restoring it. The next test loads the wrong YAML file.
**Why it happens:** `model_config` is a class-level `SettingsConfigDict` (dict-like) shared across all instances. The autouse `_reset_settings` only clears the `_settings` singleton, not `model_config`.
**How to avoid:** Use a fixture with `yield` that saves and restores `model_config` values in teardown, regardless of test outcome.
**Warning signs:** Tests pass individually but fail when run together; test order affects results.

### Pitfall 2: Real .env Contamination

**What goes wrong:** Tests load the real `.env` file containing actual credentials (`DICE_PASSWORD`, etc.), causing assertions on default values to fail.
**Why it happens:** `AppSettings` has `env_file=".env"` in its `model_config`. If the real `.env` exists at the project root, `DotEnvSettingsSource` reads it.
**How to avoid:** Set `AppSettings.model_config['env_file'] = '/dev/null'` in the config test fixture.
**Warning signs:** Tests pass in CI (no `.env`) but behave differently locally; credential-dependent assertions have unexpected values.

### Pitfall 3: Env Nested Delimiter is None

**What goes wrong:** Tests set `TIMING__NAV_DELAY_MIN=99` expecting it to override `timing.nav_delay_min`, but the value stays at the YAML/default value.
**Why it happens:** `env_nested_delimiter` is `None` in `AppSettings.model_config`. pydantic-settings only maps env vars to nested fields when a delimiter is configured.
**How to avoid:** For nested section overrides, use JSON env vars: `TIMING='{"nav_delay_min": 99.0, ...}'`. For top-level flat fields, simple env vars work fine.
**Warning signs:** Env override tests pass for `DICE_EMAIL` but fail for `TIMING__NAV_DELAY_MIN`.

### Pitfall 4: YamlConfigSettingsSource Silently Ignores Missing Files

**What goes wrong:** Tests point `yaml_file` at a non-existent path. Instead of a file-not-found error, pydantic-settings silently produces an empty dict, causing `ValidationError` for missing required fields (`search`, `scoring`).
**Why it happens:** `YamlConfigSettingsSource` treats missing YAML files as empty config (returns `{}`), then validation catches the missing required fields.
**How to avoid:** This behavior is actually correct and tested -- assert `ValidationError` with `missing` type for required fields. Don't expect `FileNotFoundError`.
**Warning signs:** N/A -- once understood, this is expected behavior.

### Pitfall 5: Import-Time Side Effects from webapp/db.py

**What goes wrong:** Importing `config` triggers webapp/db.py import chain, which calls `init_db()` and creates a real SQLite database.
**Why it happens:** Python's import system resolves transitive dependencies. `config.py` imports `apply_engine.config`, which may chain further.
**How to avoid:** The root `conftest.py` already sets `JOBFLOW_TEST_DB=1` before any project imports. This is already handled by Phase 9 infrastructure.
**Warning signs:** `job_pipeline/jobs.db` file appears during test runs.

## Code Examples

Verified patterns from live experimentation against the actual codebase:

### Loading Settings from Test YAML

```python
# Verified: get_settings with custom path works
from config import get_settings, reset_settings

reset_settings()
s = get_settings("tests/fixtures/test_config.yaml")
assert s.search.min_salary == 100000
assert s.platforms.indeed.enabled is False
assert s.timing.nav_delay_min == 0.0
```

### Creating Settings from Temporary YAML

```python
# Verified: AppSettings loads from temp YAML with only required fields
import yaml
from config import AppSettings, reset_settings

yaml_data = {
    "search": {"queries": [{"title": "test"}]},
    "scoring": {"target_titles": ["test"], "tech_keywords": ["python"]},
}
yaml_path = tmp_path / "minimal.yaml"
yaml_path.write_text(yaml.dump(yaml_data))

reset_settings()
AppSettings.model_config["yaml_file"] = str(yaml_path)
AppSettings.model_config["env_file"] = "/dev/null"
s = AppSettings()

# Defaults applied for all optional fields
assert s.search.min_salary == 150_000
assert s.platforms.indeed.enabled is True
assert s.timing.nav_delay_min == 2.0
assert s.schedule.enabled is False
assert s.scoring.weights.title_match == 2.0
assert s.apply.default_mode == "semi_auto"
```

### Validation Error Assertions

```python
# Verified: clear ValidationError for invalid types
from pydantic import ValidationError

bad_yaml = {
    "search": {"min_salary": "not-a-number", "queries": [{"title": "test"}]},
    "scoring": {"target_titles": ["test"], "tech_keywords": ["python"]},
}
# ... load via AppSettings ...

with pytest.raises(ValidationError) as exc_info:
    AppSettings()

errors = exc_info.value.errors()
assert any(e["type"] == "int_parsing" and ("search", "min_salary") == tuple(e["loc"]) for e in errors)
```

### Env Var Override (Top-Level Field)

```python
# Verified: env var overrides model default and YAML value
monkeypatch.setenv("CANDIDATE_DESIRED_SALARY_USD", "300000")
# ... load settings ...
assert settings.candidate_desired_salary_usd == 300000
```

### Env Var Override (Nested Section as JSON)

```python
# Verified: JSON env var overrides entire nested section
import json

monkeypatch.setenv("TIMING", json.dumps({
    "nav_delay_min": 99.0,
    "nav_delay_max": 99.0,
    "form_delay_min": 99.0,
    "form_delay_max": 99.0,
    "page_load_timeout": 99000,
}))
# ... load settings ...
assert settings.timing.nav_delay_min == 99.0
```

### Helper Method Tests

```python
# Verified: get_search_queries, enabled_platforms, validate_platform_credentials
s = get_settings("tests/fixtures/test_config.yaml")

queries = s.get_search_queries("indeed")
assert len(queries) == 1
assert queries[0].query == '"test engineer"'
assert queries[0].platform == "indeed"

assert s.enabled_platforms() == ["remoteok"]  # only remoteok enabled in test config

assert s.validate_platform_credentials("indeed") is True  # always true (session auth)
assert s.validate_platform_credentials("remoteok") is True  # public API
```

### Source Priority Verification

```python
# Verified: init kwargs > env vars > yaml > model defaults
# Source priority chain (highest wins):
#   1. Init kwargs
#   2. Environment variables (EnvSettingsSource)
#   3. .env file (DotEnvSettingsSource)
#   4. config.yaml (YamlConfigSettingsSource)
#   5. Model field defaults

# Model default: 200000
settings_default = load_settings(MINIMAL_YAML)
assert settings_default.candidate_desired_salary_usd == 200_000

# Env override: 300000
monkeypatch.setenv("CANDIDATE_DESIRED_SALARY_USD", "300000")
settings_env = load_settings(MINIMAL_YAML)
assert settings_env.candidate_desired_salary_usd == 300_000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pydantic.BaseSettings` (pydantic v1) | `pydantic_settings.BaseSettings` (separate package) | pydantic v2.0 (2023) | Settings moved to separate `pydantic-settings` package |
| `yaml_file` auto-loads | `YamlConfigSettingsSource` must be returned from `settings_customise_sources` | pydantic-settings 2.x | Without explicit source registration, YAML is silently ignored |
| `env_nested_delimiter` common pattern | Still supported but optional | Unchanged | Project chose to leave `None`; nested env overrides require JSON |

**Deprecated/outdated:**
- `pydantic.BaseSettings`: Moved to `pydantic-settings` package in v2. Import from `pydantic_settings` only.
- `validator` decorator: Replaced by `field_validator` in Pydantic v2. Project already uses `field_validator`.

## Verified Behaviors (Experimental Evidence)

All findings below were verified by running actual Python code against the installed packages:

| Behavior | Verified | Method |
|----------|----------|--------|
| `get_settings("tests/fixtures/test_config.yaml")` loads test config | YES | Live execution |
| Empty YAML raises `ValidationError` for `search` and `scoring` | YES | Live execution |
| `min_salary: "not-a-number"` raises `ValidationError` with `int_parsing` | YES | Live execution |
| Minimal YAML (only required fields) gets all defaults | YES | Live execution |
| `CANDIDATE_DESIRED_SALARY_USD` env var overrides model default | YES | Live execution |
| `TIMING` JSON env var overrides YAML section | YES | Live execution |
| `TIMING__NAV_DELAY_MIN` does NOT work (no nested delimiter) | YES | Live execution |
| `env_file='/dev/null'` isolates from real `.env` | YES | Live execution |
| Source priority: init > env > dotenv > yaml > defaults | YES | Live execution |
| Missing YAML file produces `ValidationError` (not `FileNotFoundError`) | YES | Live execution |
| `ScoringWeights(title_match=-1.0)` raises `ValidationError` | YES | Live execution |
| `SearchQueryConfig(title='test', max_pages=99)` raises `ValidationError` | YES | Live execution |
| `ScheduleConfig(weekdays=[7])` raises `ValidationError` | YES | Live execution |
| `ApplyConfig(max_concurrent_applies=10)` raises `ValidationError` | YES | Live execution |
| `ApplyConfig(default_mode='yolo')` raises `ValidationError` | YES | Live execution |
| `ApplyConfig(ats_form_fill_timeout=5)` raises `ValidationError` | YES | Live execution |

## Open Questions

1. **Should we test `env_nested_delimiter` override behavior or just document it?**
   - What we know: `env_nested_delimiter` is `None`. Nested env overrides only work via JSON.
   - What's unclear: Whether this is intentional or an oversight in the config design.
   - Recommendation: Test and document the actual behavior (JSON env vars for nested overrides). Do not change `env_nested_delimiter` -- that's a config design decision outside this test phase.

2. **Should config tests verify `build_candidate_profile()` mapping or defer to unit tests?**
   - What we know: `build_candidate_profile()` maps `.env` fields to a `CandidateProfile`. It's a pure mapping method.
   - What's unclear: Whether this belongs in CFG-01 (config integration) or UNIT-01 (models).
   - Recommendation: Include a basic test in CFG-01 since it exercises the config-to-model integration. Phase 10 unit tests (if they exist for models) can test `CandidateProfile` construction separately.

## Sources

### Primary (HIGH confidence)
- **Live codebase execution** - All code examples and behaviors verified against installed pydantic-settings 2.12.0 and pydantic 2.12.5
- `/Users/patrykattc/work/jobs/config.py` - Full AppSettings implementation with source customization
- `/Users/patrykattc/work/jobs/apply_engine/config.py` - ApplyConfig sub-model with validators
- `/Users/patrykattc/work/jobs/tests/conftest.py` - Existing test infrastructure (settings reset, DB isolation)
- `/Users/patrykattc/work/jobs/tests/fixtures/test_config.yaml` - Existing test YAML config
- `/Users/patrykattc/work/jobs/pyproject.toml` - Pytest configuration, markers, coverage settings

### Secondary (MEDIUM confidence)
- Phase 9 CONTEXT.md and SUMMARY.md - Established patterns for test isolation and config loading

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and verified
- Architecture: HIGH - Patterns verified through live execution against actual AppSettings
- Pitfalls: HIGH - All pitfalls discovered through live experimentation (e.g., env_nested_delimiter, model_config leakage, .env contamination)

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- pydantic-settings 2.12 is mature, config.py unlikely to change)
