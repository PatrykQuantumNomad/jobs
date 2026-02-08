# Coding Conventions

**Analysis Date:** 2026-02-07

## Naming Patterns

**Files:**
- Snake_case for Python modules: `orchestrator.py`, `form_filler.py`, `dedup.py`
- Platform-specific suffix for selectors: `indeed_selectors.py`, `dice_selectors.py`
- Test files: Not currently present (no tests found in codebase)

**Functions:**
- Snake_case for all functions: `get_settings()`, `fuzzy_deduplicate()`, `parse_salary()`
- Private functions prefixed with underscore: `_sanitize()`, `_prefer()`, `_normalize_company()`
- Private methods prefixed with underscore: `_extract_card()`, `_compute()`, `_title_score()`

**Variables:**
- Snake_case for local variables: `job_id`, `salary_text`, `min_val`
- UPPER_CASE for module-level constants: `HOURLY_MULTIPLIER`, `FUZZY_COMPANY_THRESHOLD`, `_REGISTRY`
- Descriptive names preferred over abbreviations: `dedup_key` over `dk`, `platform_name` over `pname`

**Classes:**
- PascalCase for all classes: `JobScorer`, `Orchestrator`, `BrowserPlatformMixin`
- Dataclasses for data containers: `ScoreBreakdown`, `NormalizedSalary`, `PlatformInfo`
- Pydantic models for validated data: `Job`, `SearchQuery`, `CandidateProfile`, `AppSettings`
- Protocol suffix for protocol definitions: `BrowserPlatform`, `APIPlatform`

**Types:**
- Use `type[ClassName]` for class references (modern Python 3.11+ syntax)
- Prefer `str | None` over `Optional[str]` (PEP 604 union syntax)
- `list[Job]` over `List[Job]` (built-in generics, no typing import needed)

## Code Style

**Formatting:**
- Tool: Ruff (configured in `pyproject.toml`)
- Line length: 100 characters (see `[tool.ruff] line_length = 100`)
- Commands:
  - `uv run ruff format .` - Auto-format all files
  - `uv run ruff check .` - Lint without fixing
  - `uv run ruff check --fix .` - Lint and auto-fix

**Linting:**
- Tool: Ruff
- Rules enabled: `["E", "F", "I", "UP", "B", "SIM"]`
  - E: pycodestyle errors
  - F: pyflakes
  - I: isort (import sorting)
  - UP: pyupgrade (modern Python syntax)
  - B: flake8-bugbear
  - SIM: flake8-simplify
- Target: Python 3.11+

**Docstrings:**
- Module docstrings: Required at top of every file, triple-quoted, describes purpose
- Class docstrings: Brief description of responsibility
- Function docstrings: For public functions, RST-style with parameter descriptions
- Private functions: May omit docstring if self-explanatory

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations`
2. Standard library: `import json`, `import sys`, `from pathlib import Path`
3. Third-party: `from playwright.sync_api import BrowserContext`, `from pydantic import BaseModel`
4. Local application: `from config import get_settings`, `from models import Job`

**Patterns:**
- Always use absolute imports, never relative: `from models import Job` not `from .models import Job`
- Group imports by category with blank lines between groups
- Use `if TYPE_CHECKING:` for type-only imports to avoid circular dependencies

**Example from `platforms/indeed.py`:**
```python
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import BrowserContext
from playwright.sync_api import TimeoutError as PwTimeout

from config import PROJECT_ROOT, get_settings
from models import Job, SearchQuery
from platforms.mixins import BrowserPlatformMixin
from platforms.registry import register_platform
```

**Circular Dependency Resolution:**
- Use Protocol classes for interfaces: `platforms/protocols.py` defines contracts
- `TYPE_CHECKING` guards for type hints: See `platforms/mixins.py` lines 31-32
- Import chain ordering enforced: models → protocols → registry → platform implementations

## Error Handling

**Patterns:**
- Catch-and-log for non-critical platform errors (per-query failures should not stop pipeline)
- Raise for critical setup failures (missing credentials, invalid config)
- Use domain-specific exceptions when helpful: `RuntimeError` for auth failures, `KeyError` for registry misses

**Examples from `orchestrator.py`:**
```python
# Non-critical: log and continue
try:
    found = platform.search(q)
except Exception as exc:
    print(f"  {info.name}: error on '{q.query}' -- {exc}")
    self._run_errors.append(f"{info.name}: error on '{q.query}' -- {exc}")
    continue

# Critical: fail fast
if not (PROJECT_ROOT / ".env").exists():
    print("  ERROR: .env not found -- copy .env.example and fill in credentials")
    sys.exit(1)
```

**Browser automation:**
- Screenshot on unexpected page state: `self.screenshot(f"captcha_{context}")`
- Detect challenges and raise with clear instructions
- Use `try/except PwTimeout` for optional elements: See `platforms/indeed.py` lines 163-171

**Registry validation:**
- Fail at import time, not runtime: `@register_platform` decorator validates Protocol compliance
- Missing methods cause `TypeError` immediately when module loads
- Clear error messages listing missing members: See `platforms/registry.py` lines 104-108

## Logging

**Framework:** Print statements (no structured logging framework)

**Patterns:**
- Phase headers with horizontal rules: `print("=" * 60)`
- Indented output for nested operations: `print(f"  {message}")`
- Status indicators: `print(f"  Indeed: {len(jobs)} unique jobs for '{query.query}'")`
- Error prefix: `print(f"  ERROR: {message}")`
- Warning prefix: `print(f"  WARNING: {message}")`

**Examples:**
```python
print("\n[Phase 2] Job Search")
print("-" * 60)
print(f"  Indeed: searching '{query.query}' ...")
print(f"    page {page_idx + 1}: {len(cards)} cards, {new_on_page} new")
```

## Comments

**When to Comment:**
- Complex business logic: Scoring thresholds, deduplication algorithms
- Anti-pattern workarounds: See `platforms/indeed.py` line 286 "Skip sponsored/promoted cards"
- API quirks: See `salary.py` line 173 "RemoteOK quirk: salary_max = 0 when salary_min > 0"
- Selector stability notes: DOM structure assumptions that may break

**Style:**
- Inline comments at end of line for brief explanations
- Block comments above code for multi-line explanations
- Section separators with 70-character dashed lines:
  ```python
  # ---------------------------------------------------------------------------
  # Public API
  # ---------------------------------------------------------------------------
  ```

**What NOT to comment:**
- Self-documenting code: Don't comment `i += 1  # increment i`
- Obvious operations: Method names should describe intent

## Function Design

**Size:**
- Public functions: 10-50 lines typical
- Private helpers: Under 30 lines preferred
- Orchestrator phases: 20-80 lines (phase methods encapsulate workflow)

**Parameters:**
- Use keyword-only args for config: `def __init__(self, *, headless: bool = True)`
- Type hints required for all parameters and return values
- Optional parameters use `| None = None` pattern, not `Optional[T]`
- Path parameters: Use `pathlib.Path`, not strings

**Return Values:**
- Explicit return types in all function signatures
- Use tuple unpacking for multi-value returns: `score, breakdown = self._compute(job)`
- Return `None` for side-effect functions: `def ensure_directories() -> None:`
- Boolean for success/failure: `def login(self) -> bool:`

**Example patterns:**
```python
# Good: clear signature, typed, keyword-only for config
def parse_salary(
    text: str | None,
    default_currency: str = "USD",
) -> NormalizedSalary:
    ...

# Good: multi-value return with destructuring
def _tech_score_with_keywords(self, job: Job) -> tuple[int, list[str]]:
    ...

# Good: side-effect function returns None
def ensure_directories() -> None:
    ...
```

## Module Design

**Exports:**
- No `__all__` declarations (implicit public API via naming)
- Public API: Functions/classes without leading underscore
- Private helpers: Leading underscore indicates internal use

**Module-level state:**
- Lazy singletons pattern: `_settings: AppSettings | None = None` in `config.py`
- Global registries: `_REGISTRY: dict[str, PlatformInfo] = {}` in `platforms/registry.py`
- Reset functions for testing: `reset_settings()` in `config.py`

**Barrel Files:**
- `platforms/__init__.py` exports: `get_all_platforms()`, `get_browser_context()`, `close_browser()`
- Simplifies imports for consumers: `from platforms import get_platform`
- No re-exports of internal implementation details

## Type Annotations

**Coverage:**
- All function signatures include parameter and return types
- Class attributes typed: `platform_name: str`, `page: Page`
- Use `from __future__ import annotations` at top of every file (enables forward references)

**Modern syntax (Python 3.11+):**
- Union types: `str | None` not `Optional[str]`
- Built-in generics: `list[Job]` not `List[Job]`
- Type aliases: `type[ClassName]` for class references

**Pydantic validators:**
- Use `@field_validator` decorator (Pydantic v2 syntax)
- Access sibling fields via `info.data.get()` pattern
- Return validated value from validator, raise `ValueError` on failure

## Pydantic Conventions

**Model definition:**
- Use `BaseModel` for domain objects: `Job`, `SearchQuery`, `CandidateProfile`
- Use `BaseSettings` for configuration: `AppSettings` loads from YAML + .env
- Enums for status fields: `class JobStatus(str, Enum):`

**Serialization:**
- Use `model_dump(mode="json")` for JSON output (handles dates, enums)
- Use `Field(default_factory=list)` for mutable defaults, never `[]`
- Use enum members in code: `JobStatus.SCORED` not string `"scored"`

**Validation:**
- Field validators use `@field_validator` decorator with `@classmethod`
- Custom settings sources: Override `settings_customise_sources` for YAML loading
- See `config.py` lines 192-213 for settings source customization

## Browser Automation

**Stealth configuration:**
- Always use system Chrome: `channel="chrome"` in launch args
- Disable automation flags: `--disable-blink-features=AutomationControlled`
- Apply playwright-stealth via new API: `Stealth().apply_stealth_sync(page)`

**Delays:**
- Navigation: 2-5 seconds randomized via `self.human_delay("nav")`
- Form interaction: 1-2 seconds via `self.human_delay("form")`
- Read from config: `get_settings().timing.nav_delay_min`

**Element detection:**
- Non-throwing check: `self.element_exists(selector, timeout=5000)`
- Explicit waits: `self.page.wait_for_selector(selector, timeout=10_000)`
- Multiple selector fallback: Try list of selectors in order (See `platforms/indeed.py` lines 157-171)

## Configuration

**YAML + .env split:**
- Operational config in `config.yaml`: search queries, scoring weights, timing
- Secrets in `.env`: credentials, personal profile data
- Never commit `.env`, always provide `.env.example`

**Loading pattern:**
- Singleton via `get_settings()`: Lazy load, cache instance
- Reset for testing: `reset_settings()` clears singleton
- Validation on load: Pydantic validates all fields at instantiation

---

*Convention analysis: 2026-02-07*
