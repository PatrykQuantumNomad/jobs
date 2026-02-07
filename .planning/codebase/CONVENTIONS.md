# Coding Conventions

**Analysis Date:** 2026-02-07

## Naming Patterns

**Files:**
- Module names: snake_case (e.g., `form_filler.py`, `orchestrator.py`)
- Selector files: `{platform}_selectors.py` (e.g., `indeed_selectors.py`, `dice_selectors.py`)
- Class/factory functions in dedicated files: `{name}.py` contains one primary class or utilities
- Web files: `app.py` for FastAPI application, `db.py` for database layer

**Functions:**
- Private/internal methods: `_name()` with single leading underscore (e.g., `_identify()`, `_title_score()`)
- Public methods: no underscore prefix (e.g., `login()`, `search()`, `score_job()`)
- Utility helper methods: prefixed with `_` to indicate internal use
- Handler methods follow pattern: `{action}_{object}` (e.g., `screenshot()`, `element_exists()`, `wait_for_human()`)

**Variables:**
- Local variables: snake_case (e.g., `seen_ids`, `base_url`, `posted_date`)
- Constants: UPPER_CASE (e.g., `NAV_DELAY_MIN`, `RESUME_ATS_PATH`)
- Instance variables: snake_case without leading underscore (e.g., `self.platform_name`, `self.page`, `self.context`)
- Temporary loop variables: single letter or descriptive (e.g., `for page_idx in range(...)`, `for card in cards`, `for job in jobs`)

**Types:**
- Type hints required: use PEP 484 syntax with `from __future__ import annotations` at top of file
- Union types: `str | None` (Python 3.10+ style), not `Optional[str]`
- Collection types: `list[str]`, `dict[str, str]`, `set[str]` (not `List[str]`, `Dict[str, str]`)
- Literal types: `Literal["indeed", "dice", "remoteok"]` for constrained strings
- TYPE_CHECKING guard: used for importing types that cause circular dependencies (see `base.py`)

**Classes:**
- Names: PascalCase (e.g., `BasePlatform`, `JobScorer`, `DicePlatform`)
- Abstract classes: `Base` prefix (e.g., `BasePlatform`)
- Platform-specific: `{Platform}Platform` (e.g., `IndeedPlatform`, `DicePlatform`)
- Data models: simple noun names (e.g., `Job`, `SearchQuery`, `CandidateProfile`)
- Enum classes: singular noun (e.g., `JobStatus`)

**Enums:**
- Values: snake_case strings (e.g., `JobStatus.DISCOVERED`, `JobStatus.SCORED`)
- Define as `class JobStatus(str, Enum)` to inherit from both str and Enum for JSON serialization

## Code Style

**Formatting:**
- Line length: 100 characters (see `pyproject.toml` `line-length = 100`)
- Indentation: 4 spaces (Python default)
- String formatting: f-strings preferred (e.g., `f"{url}?q={query}"`)
- Multi-line strings: triple quotes for docstrings and long text blocks

**Linting:**
- Tool: ruff (configured in `pyproject.toml`)
- Select rules: `["E", "F", "I", "UP", "B", "SIM"]` (errors, warnings, imports, upgrades, bugbear, simplify)
- Target: Python 3.11+
- Run: `ruff check` (implied by pyproject.toml config)

**Imports:**
- Order: stdlib → third-party → local
- Organization: alphabetically within each group
- Example from `scorer.py`:
  ```python
  from __future__ import annotations

  from config import Config
  from models import CandidateProfile, Job, JobStatus
  ```

**Docstrings:**
- Module level: Triple-quoted docstring at top (e.g., `"""Job scoring engine — rates jobs 1-5 against candidate profile."""`)
- Class level: Docstring immediately after class definition (e.g., `class JobScorer:\n    """Score jobs 1-5 per the CLAUDE.md rubric."""`)
- Method level: Docstring for complex methods with Args/Returns blocks
- Format: single line for simple descriptions; multi-line for detailed explanations with sections
- Example from `form_filler.py`:
  ```python
  def fill_form(self, page: Page, resume_path: Path | None = None) -> dict[str, str]:
      """Scan and fill form fields on *page*.

      Returns:
          dict mapping field description → value that was filled.
      """
  ```

## Import Organization

**Order:**
1. `from __future__ import annotations` (first line after module docstring)
2. Standard library imports (`import json`, `from pathlib import Path`)
3. Third-party imports (`from playwright.sync_api import ...`, `from pydantic import ...`)
4. Local imports (`from config import Config`, `from models import Job`)

**Path Aliases:**
- No import aliases configured; use full module paths
- Relative imports: not used; all imports are absolute (`from config import`, not `from . import`)

**TYPE_CHECKING Guard:**
- Used to avoid circular imports for type hints
- Example from `base.py`:
  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from playwright.sync_api import BrowserContext, Page
      from models import Job, SearchQuery
  ```

## Error Handling

**Patterns:**

1. **Playwright timeout errors:**
   - Import as: `from playwright.sync_api import TimeoutError as PwTimeout`
   - Catch specifically: `except PwTimeout as exc:`
   - Pattern: capture screenshot, log message, raise with context
   - Example from `dice.py`:
     ```python
     except PwTimeout as exc:
         self.screenshot("login_timeout")
         raise RuntimeError(f"Dice login timeout: {exc}") from exc
     ```

2. **HTTP errors (httpx):**
   - Catch both HTTPError and ValueError
   - Example from `remoteok.py`:
     ```python
     except (httpx.HTTPError, ValueError) as exc:
         print(f"  RemoteOK API error: {exc}")
         return []
     ```

3. **Validation failures (Pydantic):**
   - Use `@field_validator` decorator for model-level validation
   - Example from `models.py`:
     ```python
     @field_validator("salary_max")
     @classmethod
     def salary_max_gte_min(cls, v: int | None, info) -> int | None:
         if v is not None and info.data.get("salary_min") is not None:
             if v < info.data["salary_min"]:
                 raise ValueError("salary_max must be >= salary_min")
         return v
     ```

4. **Generic exception handling:**
   - Use `except Exception:` only for non-fatal operations (e.g., screenshot on error, element existence checks)
   - Example from `base.py`:
     ```python
     def element_exists(self, selector: str, timeout: int = 5000) -> bool:
         try:
             self.page.wait_for_selector(selector, timeout=timeout)
             return True
         except Exception:
             return False
     ```

5. **Resource cleanup:**
   - Use try/finally or context managers
   - Example from `stealth.py`:
     ```python
     def close_browser(pw: Playwright, context: BrowserContext) -> None:
         try:
             context.close()
         except Exception:
             pass
         try:
             pw.stop()
         except Exception:
             pass
     ```

## Logging

**Framework:** `print()` for all logging (no logging module configured)

**Patterns:**
- Use print statements with formatted output for status messages
- Indent levels using spaces for hierarchy (e.g., `print(f"    page {page_num}:...")`)
- Human-readable separators: `"=" * 60` for section breaks, `"-" * 60` for subsections
- Example from `orchestrator.py`:
  ```python
  print("=" * 60)
  print("  JOB SEARCH AUTOMATION PIPELINE")
  print("=" * 60)
  print("\n[Phase 0] Environment Setup")
  print("-" * 60)
  ```

**When to log:**
- Phase transitions (setup, login, search, score, apply)
- Search result counts (e.g., `print(f"  Dice: searching '{query.query}' …")`)
- Login success/failure states
- Job card extraction counts (e.g., `print(f"    page {page_num}: {len(cards)} cards")`)
- Error messages before raising exceptions
- Human-interactive checkpoints with formatted instructions

## Comments

**When to Comment:**
- Complex regex patterns or selector logic (e.g., `INDEED_SEARCH_PARAMS` includes explanation of opaque vs. stable parameters)
- Non-obvious heuristics (e.g., form field keyword matching in `form_filler.py`)
- Platform-specific quirks and known issues
- Example from `indeed_selectors.py`:
  ```python
  # If the remote filter stops working, re-capture the sc value by clicking
  # the Remote pill in the browser and copying the sc= param from the URL.
  ```

**Avoid:**
- Comments stating the obvious (e.g., `# increment counter` on `i += 1`)
- Redundant comments that repeat what code says
- Out-of-date comments (keep aligned with code changes)

**Docstring style:**
- Use `"""` for module, class, and method docstrings
- Multi-line docstrings have summary line, blank line, then details
- Include Args/Returns sections for complex functions
- Example from `form_filler.py`:
  ```python
  def fill_form(self, page: Page, resume_path: Path | None = None) -> dict[str, str]:
      """Scan and fill form fields on *page*.

      Returns:
          dict mapping field description → value that was filled.
      """
  ```

## Function Design

**Size:**
- Prefer methods under 50 lines
- Abstract complex operations into `_private()` helpers (e.g., `_identify()`, `_value_for()`, `_parse()`)
- Example: `form_filler.py` `fill_form()` is ~50 lines; extraction logic delegates to `_identify()` and `_value_for()`

**Parameters:**
- Avoid more than 4 parameters; use `| None` for optional params
- Use keyword arguments for optional config
- Example from `stealth.py`:
  ```python
  def get_browser_context(
      platform: str,
      headless: bool = True,
      viewport: dict | None = None,
  ) -> tuple[Playwright, BrowserContext]:
  ```

**Return Values:**
- Return single value or tuple for multiple returns
- Prefer explicit types over `Any`
- Return `None` implicitly; use `-> None` for no return value
- Return collections (list, dict, set) when aggregating results
- Example from `scorer.py`:
  ```python
  def score_batch(self, jobs: list[Job]) -> list[Job]:
      """Score all jobs in-place, sort descending."""
  ```

**Method structure (platform classes):**
- Abstract methods first (interface contract)
- Public methods next (main API)
- Private/helper methods last (implementation details)
- Use section markers: `# ── Section Name ──────`
- Example from `base.py`:
  ```python
  # ── Abstract methods ─────────────────────────────────────────────────
  @abstractmethod
  def login(self) -> bool: ...

  # ── Utility methods ──────────────────────────────────────────────────
  def human_delay(self, delay_type: str = "nav") -> None: ...
  ```

## Module Design

**Exports:**
- Import what you use; no `from module import *`
- Explicit is better than implicit
- Platform modules export single primary class (e.g., `IndeedPlatform`, `DicePlatform`)
- Config module exports `Config` class and loads all environment variables on import
- Models module exports enum + data classes

**Barrel Files:**
- `platforms/__init__.py` is empty (minimal imports)
- `webapp/__init__.py` is empty
- Import directly from submodules (e.g., `from platforms.indeed import IndeedPlatform`)

**Module-level code:**
- Configuration loaded at import time (e.g., `Config.ensure_directories()` at end of `config.py`)
- Singleton instances created at module level (e.g., `_stealth = Stealth()` in `stealth.py`)
- Lazy loading of platform classes in orchestrator to avoid unnecessary browser setup

## Config & Constants

**Location:** `config.py` with `Config` class
- All environment variables loaded once via `load_dotenv()`
- Platform credentials: `Config.DICE_EMAIL`, `Config.INDEED_EMAIL`
- Directories: `Config.PROJECT_ROOT`, `Config.BROWSER_SESSIONS_DIR`, etc.
- Timing: `Config.NAV_DELAY_MIN`, `Config.NAV_DELAY_MAX`, etc.
- Candidate profile: `Config.CANDIDATE` (CandidateProfile instance)

**Selector isolation:**
- Platform selectors live in `{platform}_selectors.py`
- Never hardcode selectors in platform classes
- Example: `indeed_selectors.py` contains `INDEED_SELECTORS`, `INDEED_URLS`, `INDEED_SEARCH_PARAMS`

**Secrets:**
- Never commit `.env` files
- Load via `python-dotenv` with `load_dotenv()`
- Access as `os.getenv("VAR_NAME")` with None fallback

---

*Convention analysis: 2026-02-07*
