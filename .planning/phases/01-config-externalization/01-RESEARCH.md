# Phase 1: Config Externalization - Research

**Researched:** 2026-02-07
**Domain:** pydantic-settings with YAML configuration, Python settings management
**Confidence:** HIGH

## Summary

This phase replaces the hardcoded `Config` class and `CandidateProfile` defaults with a `config.yaml` file loaded via `pydantic-settings` with `YamlConfigSettingsSource`. The codebase has 7 files importing `Config` with ~40 attribute references spanning credentials, timing, directories, search queries, candidate profile, and salary filters. The migration is straightforward because pydantic-settings v2.12.0 has native YAML support via `pip install pydantic-settings[yaml]`, and the existing codebase already uses Pydantic v2 models throughout.

The key architectural decision is splitting settings into two models: an `AppSettings(BaseSettings)` that loads non-sensitive config from `config.yaml` via `YamlConfigSettingsSource`, and credential fields that continue loading from `.env` via the built-in `DotEnvSettingsSource`. Personal profile info (name, email, phone) also lives in `.env` per user decision. The `settings_customise_sources` classmethod controls priority order.

**Primary recommendation:** Use `pydantic-settings[yaml]` v2.12.0 with a single `AppSettings(BaseSettings)` class that combines `YamlConfigSettingsSource` for config.yaml and `DotEnvSettingsSource` for .env credentials/personal data. Nested sub-models (`SearchConfig`, `ScoringConfig`, `PlatformConfig`, `TimingConfig`) map to YAML sections. Pydantic v2 naturally reports all validation errors at once in a single `ValidationError`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single `config.yaml` file at project root (next to `orchestrator.py`)
- Organized by domain: `search:`, `scoring:`, `platforms:`, `schedule:` (not by pipeline phase)
- No overrides mechanism -- one file, edit it directly
- No config splitting -- everything non-sensitive in one YAML
- Credentials stay in `.env` (gitignored) -- `DICE_EMAIL`, `DICE_PASSWORD`, `INDEED_EMAIL`
- Personal profile info (name, email, phone, location, GitHub, etc.) also moves to `.env` -- keeps `config.yaml` free of personal data
- `config.yaml` is committable to git -- safe to share as a template
- `config.example.yaml` provided alongside with placeholder values
- Strict validation -- every field must be present, error on missing
- All validation errors reported at once (not fail-on-first) with specific field-level messages
- `--validate` flag on orchestrator for dry-run config check without running the pipeline
- `config.example.yaml` is heavily commented -- inline YAML comments explain every field and valid values
- Structured queries with explicit fields (title, keywords, location) -- not plain strings
- Each query can optionally specify `platforms: [indeed, dice]` to limit which platforms run it; defaults to all enabled platforms if omitted
- Scoring weights are configurable in YAML (title_match, tech_overlap, remote, etc.)
- All scored jobs are saved regardless of score -- no minimum threshold in config

### Claude's Discretion
- Whether `.env` vars are referenced explicitly in config.yaml (e.g., `${DICE_PASSWORD}`) or handled implicitly by code
- Exact pydantic-settings model structure and field naming
- How structured queries are assembled into platform-specific search URLs
- Validation error formatting details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic-settings | 2.12.0 | Settings management with multi-source loading | Official Pydantic companion for settings; has native YAML, .env, and env var sources |
| pydantic | 2.x (existing) | Data validation and model definitions | Already in use throughout the codebase |
| PyYAML | (via pydantic-settings[yaml]) | YAML parsing | Installed automatically as dependency of the yaml extra |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | (existing) | .env file loading | Already used; pydantic-settings also has built-in dotenv support via DotEnvSettingsSource |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-settings[yaml] | pydantic-settings-yaml (third-party) | Third-party wrapper; unnecessary since native yaml support exists in pydantic-settings 2.x |
| pydantic-settings[yaml] | Manual PyYAML + BaseModel | Loses source priority, env override, dotenv integration; reinventing the wheel |
| pydantic-settings[yaml] | yaml-settings-pydantic | Third-party; less maintained; native support is better |

**Installation:**
```bash
pip install "pydantic-settings[yaml]"
```

This installs `pydantic-settings` 2.12.0 and `PyYAML` as a dependency. The existing `python-dotenv` and `pydantic` packages are already installed.

## Architecture Patterns

### Recommended Settings Model Structure

```python
# config.py (new version)
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


# Sub-models use BaseModel (not BaseSettings) -- they are sections of the YAML
class SearchQueryConfig(BaseModel):
    """A single structured search query."""
    title: str                                    # e.g., "Senior Software Engineer"
    keywords: list[str] = []                      # e.g., ["Kubernetes", "remote"]
    location: str = ""                            # e.g., "Remote"
    platforms: list[str] = []                      # empty = all enabled platforms
    max_pages: int = Field(default=5, ge=1, le=10)

class SearchConfig(BaseModel):
    """search: section of config.yaml."""
    queries: list[SearchQueryConfig]
    min_salary: int = 150_000

class ScoringWeights(BaseModel):
    """scoring.weights: section -- user-tunable scoring factors."""
    title_match: float = Field(default=2.0, ge=0)
    tech_overlap: float = Field(default=2.0, ge=0)
    remote: float = Field(default=1.0, ge=0)
    salary: float = Field(default=1.0, ge=0)

class ScoringConfig(BaseModel):
    """scoring: section of config.yaml."""
    target_titles: list[str]
    tech_keywords: list[str]
    weights: ScoringWeights = ScoringWeights()

class PlatformToggle(BaseModel):
    """Per-platform settings."""
    enabled: bool = True

class PlatformsConfig(BaseModel):
    """platforms: section of config.yaml."""
    indeed: PlatformToggle = PlatformToggle()
    dice: PlatformToggle = PlatformToggle()
    remoteok: PlatformToggle = PlatformToggle()

class TimingConfig(BaseModel):
    """timing: section of config.yaml."""
    nav_delay_min: float = 2.0
    nav_delay_max: float = 5.0
    form_delay_min: float = 1.0
    form_delay_max: float = 2.0
    page_load_timeout: int = 30_000

class ScheduleConfig(BaseModel):
    """schedule: section of config.yaml (placeholder for Phase 4)."""
    pass  # Fields added in Phase 4


# Root settings model -- combines YAML + .env
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",  # Catch typos in config.yaml
    )

    # From config.yaml (nested sections)
    search: SearchConfig
    scoring: ScoringConfig
    platforms: PlatformsConfig = PlatformsConfig()
    timing: TimingConfig = TimingConfig()
    schedule: ScheduleConfig = ScheduleConfig()

    # From .env (flat, env var names)
    indeed_email: str | None = None
    dice_email: str | None = None
    dice_password: str | None = None

    # Personal profile from .env
    candidate_first_name: str = ""
    candidate_last_name: str = ""
    candidate_email: str = ""
    candidate_phone: str = ""
    candidate_location: str = ""
    candidate_github: str = ""
    candidate_github_personal: str = ""
    candidate_website: str = ""
    candidate_youtube: str = ""
    candidate_years_experience: str = ""
    candidate_current_title: str = ""
    candidate_current_company: str = ""
    candidate_work_authorization: str = ""
    candidate_willing_to_relocate: str = ""
    candidate_desired_salary: str = ""
    candidate_desired_salary_usd: int = 200_000
    candidate_start_date: str = ""
    candidate_education: str = ""
    candidate_resume_path: str = "resumes/Patryk_Golabek_Resume.pdf"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,          # Highest: constructor args (for testing)
            env_settings,           # Environment variables override everything
            dotenv_settings,        # .env file
            YamlConfigSettingsSource(settings_cls),  # config.yaml
        )
```

### Key Design Decisions

**1. Sub-models are `BaseModel`, not `BaseSettings`**
Only the root `AppSettings` inherits from `BaseSettings`. Nested section models (`SearchConfig`, `ScoringConfig`, etc.) inherit from `BaseModel`. This is the correct pydantic-settings pattern -- `BaseSettings` provides source loading, sub-models are just structure.

**2. Source Priority Order: env > .env > yaml**
Environment variables override .env, which overrides config.yaml. This matters for CI/CD or deployment overrides but keeps the common case simple (just edit config.yaml). `init_settings` is highest for testability.

**3. Credentials handled implicitly by code, not explicitly in YAML**
Recommendation for Claude's discretion area: Do NOT reference env vars in config.yaml (no `${DICE_PASSWORD}` syntax). Instead, pydantic-settings automatically maps env vars to flat fields on `AppSettings`. This is cleaner -- config.yaml contains only non-sensitive domain config, and .env contains all credentials/personal data. The code handles the boundary.

**4. CandidateProfile becomes a computed property**
The existing `CandidateProfile` model in `models.py` stays as-is for downstream compatibility (`scorer.py`, `form_filler.py` use it). `AppSettings` gets a method that constructs a `CandidateProfile` from its `.env`-sourced fields plus `scoring.target_titles` and `scoring.tech_keywords` from YAML. This avoids breaking any code that takes a `CandidateProfile`.

**5. Structured search queries assembled into SearchQuery for platforms**
`SearchQueryConfig` (from YAML) is a user-facing config object. A method on `AppSettings` converts these into the existing `SearchQuery` model for each platform, applying the `platforms` filter and constructing the query string from `title` + `keywords`.

### Anti-Patterns to Avoid
- **Global singleton at import time:** The current `Config` class loads at import time (`Config.ensure_directories()` at module level). The new `AppSettings` should be instantiated explicitly and passed as a dependency, not created at import time. This enables testing and the `--validate` flag.
- **Mixing BaseSettings with BaseModel for sub-sections:** Do not make `SearchConfig(BaseSettings)` -- only the root model should inherit `BaseSettings`.
- **Removing CandidateProfile from models.py:** Keep it as a domain model. Have `AppSettings` construct one from its fields. The scorer and form_filler already accept `CandidateProfile` as a parameter.

### Recommended Migration Pattern

The current codebase uses `Config.ATTRIBUTE` as a class-level access pattern in 7 files. The migration should:

1. Create `AppSettings` in `config.py`, replacing the `Config` class
2. Provide a module-level `get_settings()` function that lazily instantiates and caches `AppSettings` (singleton pattern with explicit initialization)
3. Update each consumer file to call `get_settings()` or accept settings as a parameter
4. Keep backward compatibility by mapping old attribute paths to new ones during migration

```python
# Lazy singleton pattern
_settings: AppSettings | None = None

def get_settings(config_path: str = "config.yaml") -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings(_yaml_file=config_path)
    return _settings

def reset_settings() -> None:
    """For testing -- clear cached settings."""
    global _settings
    _settings = None
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing + validation | Custom yaml.safe_load + manual validation | pydantic-settings YamlConfigSettingsSource | Handles nested models, type coercion, error messages automatically |
| .env loading | Custom os.getenv + dotenv | pydantic-settings DotEnvSettingsSource | Already integrated with the settings model, auto-maps env var names |
| Multi-source priority | Custom merge logic | settings_customise_sources tuple ordering | Source priority is a single tuple return -- first = highest priority |
| Validation error aggregation | Try/except per field | Pydantic v2 ValidationError | Pydantic v2 automatically collects ALL field errors into one ValidationError with per-field detail |
| Config file discovery | Custom path resolution | SettingsConfigDict yaml_file | Handles relative paths from CWD |

**Key insight:** pydantic-settings handles the entire config loading pipeline (YAML parsing, .env loading, env var override, type validation, error collection) with ~20 lines of model definition. Custom solutions would need hundreds of lines and miss edge cases.

## Common Pitfalls

### Pitfall 1: Sub-models inheriting BaseSettings
**What goes wrong:** Defining nested config sections as `BaseSettings` subclasses causes them to independently load from environment variables with unpredictable field name collisions.
**Why it happens:** Intuition says "settings model = BaseSettings" but only the root needs source loading.
**How to avoid:** All nested section models inherit from `BaseModel`. Only `AppSettings` inherits `BaseSettings`.
**Warning signs:** Nested fields mysteriously getting values from unrelated env vars.

### Pitfall 2: Import-time initialization
**What goes wrong:** Creating `AppSettings()` at module level (like current `Config.ensure_directories()`) means config.yaml must exist before any import, breaking tests and the `--validate` flag.
**Why it happens:** Current code pattern uses class-level attributes.
**How to avoid:** Use lazy initialization via `get_settings()` function. Never instantiate at import time.
**Warning signs:** `FileNotFoundError` on import, inability to test with different configs.

### Pitfall 3: Forgetting to register YamlConfigSettingsSource
**What goes wrong:** Setting `yaml_file="config.yaml"` in `SettingsConfigDict` but not overriding `settings_customise_sources` means YAML is never actually loaded. The model silently falls back to env/dotenv/defaults only.
**Why it happens:** The `yaml_file` config key does NOT auto-register the YAML source. You MUST explicitly add `YamlConfigSettingsSource(settings_cls)` in `settings_customise_sources`.
**How to avoid:** Always override `settings_customise_sources` and include `YamlConfigSettingsSource(settings_cls)` in the returned tuple.
**Warning signs:** All YAML values ignored, only defaults used.

### Pitfall 4: Breaking existing SearchQuery model
**What goes wrong:** Changing the `SearchQuery` model in `models.py` to match the new config format breaks platform modules that construct URLs from it.
**Why it happens:** Conflating config-layer models with domain-layer models.
**How to avoid:** Keep `SearchQuery` in `models.py` as the domain model. Add `SearchQueryConfig` as the config-layer model. Provide a conversion method.
**Warning signs:** Platform search methods receiving unexpected field types.

### Pitfall 5: extra="forbid" catching env vars
**What goes wrong:** Setting `extra="forbid"` on `AppSettings` causes it to reject any env vars or .env fields not explicitly defined as fields on the model.
**Why it happens:** `extra="forbid"` applies to ALL sources, not just YAML.
**How to avoid:** Either define all expected env vars as fields on `AppSettings`, or use `extra="ignore"` and validate the YAML structure separately. Alternatively, use `extra="forbid"` only on the nested `BaseModel` sub-models while keeping `extra="ignore"` on the root `BaseSettings`.
**Warning signs:** `ValidationError` mentioning env vars you didn't expect.

### Pitfall 6: Validation errors not user-friendly
**What goes wrong:** Pydantic v2's `ValidationError` produces developer-friendly but not user-friendly error messages (references internal field paths like `scoring.weights.title_match`).
**Why it happens:** Default Pydantic error formatting is optimized for developers.
**How to avoid:** Catch `ValidationError` in the CLI entry point and format errors with clear messages like `"scoring.weights.title_match: must be >= 0, got -5"`. Pydantic's `e.errors()` returns a list of dicts with `loc`, `msg`, and `type` fields.
**Warning signs:** Users seeing raw Pydantic tracebacks.

## Code Examples

### Loading Settings from YAML + .env

```python
# Source: pydantic-settings official docs + verified pattern
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # YAML sections
    search: SearchConfig
    scoring: ScoringConfig

    # .env credentials
    dice_email: str | None = None
    dice_password: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )

# Instantiation -- validates immediately, raises ValidationError with ALL errors
settings = AppSettings()
```

### Formatting Validation Errors for Users

```python
# Source: Pydantic v2 error handling docs
from pydantic import ValidationError

def load_and_validate(config_path: str = "config.yaml") -> AppSettings:
    try:
        return AppSettings()
    except ValidationError as e:
        print("Configuration errors found:\n")
        for error in e.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            msg = error["msg"]
            print(f"  {loc}: {msg}")
        raise SystemExit(1)
```

### --validate Flag Integration

```python
# In orchestrator.py CLI
parser.add_argument(
    "--validate",
    action="store_true",
    help="Validate config.yaml and .env without running the pipeline",
)

if args.validate:
    try:
        settings = AppSettings()
        print("Config validation passed.")
        # Also check .env completeness
        warnings = []
        if settings.platforms.indeed.enabled and not settings.indeed_email:
            warnings.append("Indeed enabled but INDEED_EMAIL not set in .env")
        if settings.platforms.dice.enabled and not (settings.dice_email and settings.dice_password):
            warnings.append("Dice enabled but DICE_EMAIL/DICE_PASSWORD not set in .env")
        for w in warnings:
            print(f"  WARNING: {w}")
        sys.exit(0)
    except ValidationError as e:
        # format errors
        sys.exit(1)
```

### Constructing CandidateProfile from Settings

```python
# AppSettings method
def build_candidate_profile(self) -> CandidateProfile:
    """Construct a CandidateProfile from .env personal data + YAML scoring config."""
    return CandidateProfile(
        first_name=self.candidate_first_name,
        last_name=self.candidate_last_name,
        email=self.candidate_email,
        phone=self.candidate_phone,
        location=self.candidate_location,
        github=self.candidate_github,
        github_personal=self.candidate_github_personal,
        website=self.candidate_website,
        youtube=self.candidate_youtube,
        years_experience=self.candidate_years_experience,
        current_title=self.candidate_current_title,
        current_company=self.candidate_current_company,
        work_authorization=self.candidate_work_authorization,
        willing_to_relocate=self.candidate_willing_to_relocate,
        desired_salary=self.candidate_desired_salary,
        desired_salary_usd=self.candidate_desired_salary_usd,
        start_date=self.candidate_start_date,
        education=self.candidate_education,
        resume_path=self.candidate_resume_path,
        target_titles=self.scoring.target_titles,
        tech_keywords=self.scoring.tech_keywords,
    )
```

### Converting Config Queries to Domain SearchQuery

```python
def get_search_queries(self, platform: str) -> list[SearchQuery]:
    """Convert structured config queries into platform SearchQuery objects."""
    queries = []
    for qcfg in self.search.queries:
        # Skip if query specifies platforms and this one isn't included
        if qcfg.platforms and platform not in qcfg.platforms:
            continue
        # Build query string from title + keywords
        parts = [f'"{qcfg.title}"'] if qcfg.title else []
        parts.extend(qcfg.keywords)
        query_str = " ".join(parts)
        queries.append(SearchQuery(
            query=query_str,
            platform=platform,
            location=qcfg.location or "",
            max_pages=qcfg.max_pages,
        ))
    return queries
```

### Example config.yaml Structure

```yaml
# ── Search Configuration ──────────────────────────────────────────
search:
  # Minimum annual salary (USD) to include in results.
  # Jobs below this threshold are filtered out. Set to 0 to disable.
  min_salary: 150000

  # Structured search queries. Each query runs on all enabled platforms
  # unless 'platforms' is specified to restrict it.
  queries:
    - title: "Senior Software Engineer"
      keywords: ["Kubernetes", "remote"]
      location: "Remote"
      max_pages: 5

    - title: "Staff Engineer"
      keywords: ["platform engineering"]
      platforms: ["indeed", "dice"]  # Skip RemoteOK for this query

    - title: "Principal Engineer"
      keywords: ["Kubernetes", "cloud infrastructure"]

# ── Scoring Configuration ─────────────────────────────────────────
scoring:
  # Titles that earn maximum title_match score (case-insensitive)
  target_titles:
    - "Senior Software Engineer"
    - "Principal Engineer"
    - "Staff Engineer"
    - "Platform Engineering Lead"
    - "DevOps Lead"
    - "Engineering Manager"

  # Keywords to match in job descriptions/tags (case-insensitive)
  tech_keywords:
    - kubernetes
    - python
    - terraform
    - langchain
    # ... etc

  # Scoring weights -- adjust to tune what matters most to you.
  # Higher weight = more influence on final 1-5 score.
  weights:
    title_match: 2.0    # 0-2 raw points for title match
    tech_overlap: 2.0   # 0-2 raw points for tech keyword overlap
    remote: 1.0         # 0-1 for remote/acceptable location
    salary: 1.0         # 0-1 for salary meeting target

# ── Platform Configuration ────────────────────────────────────────
platforms:
  indeed:
    enabled: true
  dice:
    enabled: true
  remoteok:
    enabled: true

# ── Timing (anti-detection delays) ────────────────────────────────
timing:
  nav_delay_min: 2.0      # Min seconds between page navigations
  nav_delay_max: 5.0      # Max seconds between page navigations
  form_delay_min: 1.0     # Min seconds between form interactions
  form_delay_max: 2.0     # Max seconds between form interactions
  page_load_timeout: 30000 # Milliseconds for Playwright page loads

# ── Schedule (Phase 4 placeholder) ────────────────────────────────
schedule: {}
```

## Config Migration Surface Area

Every `Config.ATTRIBUTE` reference in the codebase that must be migrated:

| Current Access | File(s) | New Access Path | Source |
|----------------|---------|-----------------|--------|
| `Config.PROJECT_ROOT` | orchestrator.py | Computed from `__file__` (no config needed) | Code |
| `Config.BROWSER_SESSIONS_DIR` | platforms/stealth.py | Computed path (not user-configurable) | Code |
| `Config.DEBUG_SCREENSHOTS_DIR` | platforms/base.py | Computed path | Code |
| `Config.JOB_PIPELINE_DIR` | orchestrator.py | Computed path | Code |
| `Config.JOB_DESCRIPTIONS_DIR` | orchestrator.py | Computed path | Code |
| `Config.RESUMES_DIR` | (unused directly) | -- | -- |
| `Config.RESUMES_TAILORED_DIR` | (unused directly) | -- | -- |
| `Config.INDEED_EMAIL` | platforms/indeed.py | `settings.indeed_email` | .env |
| `Config.DICE_EMAIL` | platforms/dice.py | `settings.dice_email` | .env |
| `Config.DICE_PASSWORD` | platforms/dice.py | `settings.dice_password` | .env |
| `Config.RESUME_ATS_PATH` | orchestrator.py | `settings.candidate_resume_path` (computed Path) | .env |
| `Config.NAV_DELAY_MIN/MAX` | platforms/base.py | `settings.timing.nav_delay_min/max` | YAML |
| `Config.FORM_DELAY_MIN/MAX` | platforms/base.py | `settings.timing.form_delay_min/max` | YAML |
| `Config.PAGE_LOAD_TIMEOUT` | indeed.py, dice.py | `settings.timing.page_load_timeout` | YAML |
| `Config.MIN_SALARY` | indeed.py, remoteok.py | `settings.search.min_salary` | YAML |
| `Config.DEFAULT_SEARCH_QUERIES` | config.py | `settings.search.queries` (structured) | YAML |
| `Config.CANDIDATE` | scorer.py, form_filler.py, remoteok.py | `settings.build_candidate_profile()` | .env + YAML |
| `Config.validate_platform_credentials()` | orchestrator.py, dice.py | Method on AppSettings | .env + YAML |
| `Config.ensure_directories()` | orchestrator.py, config.py | Standalone function (not config) | Code |
| `Config.get_search_queries()` | orchestrator.py | `settings.get_search_queries(platform)` | YAML |

### Files Requiring Changes (7 total)

1. **config.py** -- Complete rewrite: replace `Config` class with `AppSettings(BaseSettings)` + sub-models + `get_settings()`
2. **models.py** -- Remove hardcoded defaults from `CandidateProfile` (make all fields required or accept via constructor); keep the model itself
3. **orchestrator.py** -- Replace all `Config.X` with `get_settings().X`; add `--validate` flag
4. **scorer.py** -- Accept `AppSettings` or `CandidateProfile` in constructor instead of importing `Config`
5. **form_filler.py** -- Accept `CandidateProfile` parameter instead of importing `Config`
6. **platforms/base.py** -- Accept timing settings via constructor or `get_settings()`
7. **platforms/indeed.py** -- Replace `Config.PAGE_LOAD_TIMEOUT`, `Config.MIN_SALARY`
8. **platforms/dice.py** -- Replace `Config.DICE_EMAIL`, `Config.DICE_PASSWORD`, `Config.PAGE_LOAD_TIMEOUT`
9. **platforms/remoteok.py** -- Replace `Config.MIN_SALARY`, `Config.CANDIDATE`

### New Files

1. **config.yaml** -- Actual user config with Patryk's values (gitignored or committed per decision)
2. **config.example.yaml** -- Heavily commented template with placeholder values

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydantic-settings 1.x (separate package) | pydantic-settings 2.x (redesigned for Pydantic v2) | 2023 | New `SettingsConfigDict`, `settings_customise_sources` API |
| Custom YAML loader + BaseModel | YamlConfigSettingsSource (native) | pydantic-settings 2.x | No need for third-party yaml-settings packages |
| `BaseSettings` for all models | `BaseSettings` only for root, `BaseModel` for nested | pydantic-settings 2.x best practice | Prevents env var collision on nested models |

**Deprecated/outdated:**
- `pydantic-settings-yaml` (third-party): Unnecessary since pydantic-settings 2.x has native YAML support via `[yaml]` extra
- `yaml-settings-pydantic`: Same -- native support supersedes it
- `pydantic.BaseSettings` (v1 location): Moved to `pydantic_settings.BaseSettings` in v2

## Open Questions

1. **CandidateProfile field requirements**
   - What we know: Current `CandidateProfile` has all defaults hardcoded. Moving personal data to `.env` means these defaults become empty strings.
   - What's unclear: Should `CandidateProfile` fields be Optional (allow empty) or required (fail validation if .env is incomplete)?
   - Recommendation: Make them Optional with empty string defaults. The `--validate` flag can warn about missing fields without hard-failing.

2. **Directory paths in config**
   - What we know: `PROJECT_ROOT`, `JOB_PIPELINE_DIR`, etc. are currently class attributes on `Config`. They're not really "configuration" -- they're computed paths.
   - What's unclear: Should these be in config.yaml or remain as computed values?
   - Recommendation: Keep directory paths as computed values in code (not in YAML). They're infrastructure, not user configuration. A standalone `ensure_directories()` function replaces the class method.

3. **How platforms receive settings**
   - What we know: Platform classes currently import `Config` directly. The new pattern needs them to receive `AppSettings` or relevant subsets.
   - What's unclear: Constructor injection vs. module-level `get_settings()` call?
   - Recommendation: Pass relevant config subset to platform constructors (e.g., `BasePlatform.__init__(self, context, timing: TimingConfig)`). This is more testable than global access.

## Sources

### Primary (HIGH confidence)
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- v2.12.0 (Nov 2025), yaml extra, Python >=3.10
- [pydantic-settings official docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) -- YamlConfigSettingsSource, settings_customise_sources
- [pydantic-settings API reference](https://docs.pydantic.dev/latest/api/pydantic_settings/) -- YamlConfigSettingsSource(settings_cls, yaml_file, yaml_file_encoding)
- [pydantic-settings GitHub issue #366](https://github.com/pydantic/pydantic-settings/issues/366) -- Working YAML example with settings_customise_sources

### Secondary (MEDIUM confidence)
- [Keeping Configurations Sane with Pydantic Settings](https://ai.ragv.in/posts/sane-configs-with-pydantic-settings/) -- Nested model patterns, source priority examples
- [How to Load Configuration in Pydantic](https://medium.com/@wihlarkop/how-to-load-configuration-in-pydantic-3693d0ee81a3) -- Combined env + YAML patterns

### Tertiary (LOW confidence)
- None -- all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pydantic-settings 2.12.0 with yaml extra is verified on PyPI, API documented
- Architecture: HIGH -- patterns verified against official docs and working examples
- Pitfalls: HIGH -- based on official docs (must register YamlConfigSettingsSource) and codebase analysis (import-time init)
- Migration surface: HIGH -- exhaustive grep of all Config.* references in codebase

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (stable library, unlikely to change significantly)
