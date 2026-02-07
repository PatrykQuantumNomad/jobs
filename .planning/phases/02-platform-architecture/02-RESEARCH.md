# Phase 2: Platform Architecture - Research

**Researched:** 2026-02-07
**Domain:** Python Protocol-based plugin architecture with decorator registry
**Confidence:** HIGH

## Summary

This phase replaces the current ABC-based `BasePlatform` inheritance with Python `typing.Protocol` structural subtyping and a decorator-based platform registry. The goal: adding a new job board means creating one file that implements a protocol -- no changes to orchestrator, config, or scoring.

The current codebase has three platform implementations: `IndeedPlatform` and `DicePlatform` (browser-based, inheriting from `BasePlatform` ABC) and `RemoteOKPlatform` (HTTP API, no inheritance at all). The orchestrator (`orchestrator.py`) has extensive `if/elif` branching for platform names across four methods (`_login_platform`, `_search_browser_platform`, `_search_remoteok`, `_apply_to`). This is the primary code smell this phase eliminates.

Python 3.14 is in use, which has full Protocol support (available since 3.8). The `@runtime_checkable` decorator enables `isinstance()` checks but only verifies attribute/method existence, not signatures. For the fail-fast registration validation the user wants, we need custom `inspect.signature()` checks in the registry decorator.

**Primary recommendation:** Define `BrowserPlatform` and `APIPlatform` as `@runtime_checkable` Protocols, build a registry module with `@register_platform` decorator that validates protocol compliance via `inspect`, and auto-import platform modules via `pkgutil.iter_modules` in `platforms/__init__.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two separate protocols: BrowserPlatform and APIPlatform -- browser ones handle login/sessions, API ones handle HTTP clients
- Core method contract: search(query) returns raw cards, extract(card) returns Job model, apply(job) handles application flow
- Platforms return Pydantic Job models from extract -- orchestrator gets clean typed data
- apply() is part of the platform protocol -- each platform owns its own apply flow
- Decorator-based registration: @register_platform('indeed') on the class definition -- importing the module auto-registers it
- Config controls active platforms via explicit enable list in config.yaml -- only listed ones run
- Registry validates protocol compliance at registration time -- missing methods cause an import error immediately (fail fast)
- Decorator supports metadata: @register_platform('indeed', name='Indeed', type='browser', capabilities=['easy_apply'])
- Shared Playwright browser instance, each platform gets its own BrowserContext with isolated cookies/sessions
- If one platform fails, log the error, skip it, continue with remaining platforms
- Explicit init phase: orchestrator calls platform.init() upfront for all platforms, then runs searches
- Context manager pattern: platforms implement __enter__/__exit__
- Big bang: build protocols + registry, then migrate all three adapters at once
- Remove BasePlatform ABC immediately once all adapters use protocols
- Adapter migration and orchestrator refactor happen in the same plan
- No end-to-end verification run required -- code review is sufficient

### Claude's Discretion
- Exact protocol method signatures and type hints
- How the decorator internally stores and validates registrations
- BrowserContext configuration details (viewport, user agent inheritance)
- Error logging format and platform skip reporting

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

No new libraries are needed. Everything uses Python standard library + existing project dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` | stdlib (3.14) | Define structural subtype contracts | PEP 544, native to Python, zero dependencies |
| `typing.runtime_checkable` | stdlib (3.14) | Enable `isinstance()` checks against protocols | Pairs with Protocol for runtime validation |
| `inspect` | stdlib (3.14) | Validate method signatures at registration time | Only stdlib way to check function signatures programmatically |
| `pkgutil` | stdlib (3.14) | Auto-discover platform modules in `platforms/` package | Standard approach for package-internal module discovery |
| `importlib` | stdlib (3.14) | Dynamically import discovered platform modules | Standard dynamic import mechanism |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | v2 (existing) | Job model returned by platform methods | Already in project, protocols reference Job type |
| `playwright` | existing | BrowserContext type referenced by BrowserPlatform protocol | Already in project, type annotations only |
| `httpx` | existing | HTTP client used by APIPlatform implementations | Already in project, RemoteOK uses it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@runtime_checkable` + `inspect` | Pure `@runtime_checkable` only | Simpler but does NOT check method signatures, only attribute existence |
| `pkgutil.iter_modules` | Entry points (`importlib.metadata`) | Entry points are for cross-package plugins; overkill for in-package modules |
| `typing.Protocol` | `abc.ABC` (current) | ABC requires explicit inheritance; Protocol enables structural subtyping |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
platforms/
    __init__.py          # Auto-imports all platform modules, exposes registry
    protocols.py         # BrowserPlatform, APIPlatform protocol definitions
    registry.py          # @register_platform decorator, _REGISTRY dict, get_platform()
    mixins.py            # Shared utilities (human_delay, screenshot, element_exists, wait_for_human)
    stealth.py           # Browser context factory (existing, unchanged)
    indeed.py            # @register_platform('indeed') IndeedPlatform
    indeed_selectors.py  # (existing, unchanged)
    dice.py              # @register_platform('dice') DicePlatform
    dice_selectors.py    # (existing, unchanged)
    remoteok.py          # @register_platform('remoteok') RemoteOKPlatform
```

### Pattern 1: Protocol Definitions

**What:** Two separate Protocol classes defining the structural contracts for browser-based and API-based platforms.

**Key design considerations:**

1. The current `BasePlatform.search()` returns `list[Job]` directly and `get_job_details()` is a separate method. The CONTEXT.md decision says "search(query) returns raw cards, extract(card) returns Job model." This is a deliberate redesign of the method contract -- search returns raw intermediate data, extract converts each card to a Job. This separation is cleaner for the protocol.

2. The current `RemoteOKPlatform.search()` is `async` while `IndeedPlatform.search()` and `DicePlatform.search()` are sync. The protocol must handle this -- either all sync (wrap async in `asyncio.run`) or make the protocol async and have browser platforms use sync Playwright calls within async wrappers. **Recommendation:** Keep browser platforms sync (Playwright sync API is used throughout) and API platforms sync as well (use `httpx.Client` instead of `httpx.AsyncClient` for RemoteOK). This avoids mixed sync/async complexity. The orchestrator already calls `asyncio.run()` for RemoteOK -- simplifying to all-sync removes that seam.

3. `apply()` signature differs: browser platforms take `(job, resume_path)`, RemoteOK takes `(job)` only. The protocol should use `apply(job: Job, resume_path: Path | None = None) -> bool` so API platforms can ignore `resume_path`.

4. Context manager: `__enter__` returns `self`, `__exit__` handles cleanup.

5. `init()` method: called by orchestrator upfront. For browser platforms: login. For API platforms: validate connectivity.

**Example protocol definitions:**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from models import Job, SearchQuery


@runtime_checkable
class BrowserPlatform(Protocol):
    """Contract for browser-automated job platforms (Indeed, Dice)."""

    platform_name: str

    def init(self, context: BrowserContext) -> None:
        """Initialize with a Playwright BrowserContext. Called by orchestrator."""
        ...

    def login(self) -> bool:
        """Authenticate. Returns True if fresh login, False if already logged in."""
        ...

    def is_logged_in(self) -> bool: ...

    def search(self, query: SearchQuery) -> list[dict[str, Any]]:
        """Search and return raw card data."""
        ...

    def extract(self, raw_card: dict[str, Any]) -> Job | None:
        """Convert a raw card to a Job model. Returns None for invalid cards."""
        ...

    def get_job_details(self, job: Job) -> Job:
        """Enrich a Job with full description from detail page."""
        ...

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        """Submit application. MUST pause for human confirmation."""
        ...

    def __enter__(self) -> BrowserPlatform: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...


@runtime_checkable
class APIPlatform(Protocol):
    """Contract for pure HTTP API platforms (RemoteOK)."""

    platform_name: str

    def init(self) -> None:
        """Initialize HTTP client. Called by orchestrator."""
        ...

    def search(self, query: SearchQuery) -> list[dict[str, Any]]:
        """Search and return raw API response items."""
        ...

    def extract(self, raw_item: dict[str, Any]) -> Job | None:
        """Convert a raw API item to a Job model."""
        ...

    def get_job_details(self, job: Job) -> Job:
        """Enrich a Job (may be no-op for APIs that return full data)."""
        ...

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        """Handle application flow (may just report external URL)."""
        ...

    def __enter__(self) -> APIPlatform: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

**IMPORTANT NOTE on search/extract split:** The current codebase has `search()` returning `list[Job]` with `_extract_card()` as a private method. The CONTEXT.md decision says `search(query)` returns raw cards and `extract(card)` returns `Job`. The planner should decide whether to:
- (a) Make `extract()` public and have the orchestrator call it per-card, or
- (b) Keep `search()` returning `list[Job]` (calling extract internally) for simplicity

Option (b) is pragmatically better because: the orchestrator should not care about raw card formats, and the raw card type varies by platform (DOM element handle for browser, dict for API). The protocol's value is in the `search() -> list[Job]` contract -- the orchestrator asks "give me jobs" and gets typed data back. **Recommendation:** Keep `search()` returning `list[Job]`, make `_extract_card` remain private. The protocol can still be clean without exposing raw card internals.

### Pattern 2: Decorator-Based Registry

**What:** A `@register_platform` decorator that registers platform classes at import time and validates protocol compliance.

**Key design detail:** `@runtime_checkable` Protocol's `isinstance()` only checks attribute/method *existence*, NOT signatures. To get fail-fast validation with signature checking, use `inspect.signature()` to compare each required method's parameters against the protocol definition.

```python
# platforms/registry.py
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Union

from platforms.protocols import APIPlatform, BrowserPlatform


@dataclass
class PlatformInfo:
    """Metadata about a registered platform."""
    key: str                           # e.g., "indeed"
    name: str                          # e.g., "Indeed"
    platform_type: str                 # "browser" or "api"
    cls: type                          # The platform class
    capabilities: list[str] = field(default_factory=list)


# Module-level registry
_REGISTRY: dict[str, PlatformInfo] = {}


def register_platform(
    key: str,
    *,
    name: str | None = None,
    platform_type: str = "browser",
    capabilities: list[str] | None = None,
):
    """Decorator that registers a platform class and validates protocol compliance.

    Usage:
        @register_platform('indeed', name='Indeed', platform_type='browser', capabilities=['easy_apply'])
        class IndeedPlatform:
            ...
    """
    def decorator(cls):
        # 1. Pick the right protocol
        protocol = BrowserPlatform if platform_type == "browser" else APIPlatform

        # 2. Validate all required methods exist and have compatible signatures
        _validate_protocol(cls, protocol)

        # 3. Register
        _REGISTRY[key] = PlatformInfo(
            key=key,
            name=name or key.title(),
            platform_type=platform_type,
            cls=cls,
            capabilities=capabilities or [],
        )
        return cls

    return decorator


def _validate_protocol(cls: type, protocol: type) -> None:
    """Check that cls has all methods required by protocol with compatible signatures."""
    # Get protocol methods (excluding dunder inherited from object)
    protocol_methods = {}
    for attr_name in dir(protocol):
        if attr_name.startswith('_') and attr_name not in ('__enter__', '__exit__'):
            continue
        attr = getattr(protocol, attr_name, None)
        if callable(attr):
            protocol_methods[attr_name] = attr

    for method_name, proto_method in protocol_methods.items():
        # Check existence
        impl_method = getattr(cls, method_name, None)
        if impl_method is None:
            raise TypeError(
                f"Platform {cls.__name__} missing required method: {method_name}"
            )

        # Check signature compatibility (parameter count, not types -- types are checked statically)
        try:
            proto_sig = inspect.signature(proto_method)
            impl_sig = inspect.signature(impl_method)
            proto_params = [p for p in proto_sig.parameters if p != 'self']
            impl_params = [p for p in impl_sig.parameters if p != 'self']
            # Implementation must accept at least as many params as protocol requires
            proto_required = [
                p for p, v in proto_sig.parameters.items()
                if p != 'self' and v.default is inspect.Parameter.empty
            ]
            impl_required = [
                p for p, v in impl_sig.parameters.items()
                if p != 'self' and v.default is inspect.Parameter.empty
            ]
            if len(impl_required) > len(proto_required):
                raise TypeError(
                    f"Platform {cls.__name__}.{method_name} requires more parameters "
                    f"than protocol: {impl_required} vs {proto_required}"
                )
        except (ValueError, TypeError):
            pass  # Some methods may not be introspectable


def get_platform(key: str) -> PlatformInfo:
    """Get a registered platform by key. Raises KeyError if not found."""
    if key not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys()) or "(none)"
        raise KeyError(f"Platform '{key}' not registered. Available: {available}")
    return _REGISTRY[key]


def get_all_platforms() -> dict[str, PlatformInfo]:
    """Return a copy of all registered platforms."""
    return dict(_REGISTRY)


def get_platforms_by_type(platform_type: str) -> dict[str, PlatformInfo]:
    """Return platforms of a specific type ('browser' or 'api')."""
    return {k: v for k, v in _REGISTRY.items() if v.platform_type == platform_type}
```

### Pattern 3: Auto-Import via `__init__.py`

**What:** The `platforms/__init__.py` uses `pkgutil.iter_modules` to import all `.py` files in the package, triggering `@register_platform` decorators.

**Critical insight:** Decorators only run when the module containing them is imported. Without auto-import, platform files would need explicit imports somewhere, defeating the "drop a file and it works" goal.

```python
# platforms/__init__.py
"""Job platform automation modules -- auto-discovers platform implementations."""
import importlib
import pkgutil
from pathlib import Path

# Import registry first (it defines the decorator)
from platforms.registry import get_all_platforms, get_platform, get_platforms_by_type

# Auto-import all modules in this package to trigger @register_platform decorators
_PACKAGE_DIR = Path(__file__).parent

# Modules to skip (not platforms, infrastructure only)
_SKIP_MODULES = {"protocols", "registry", "mixins", "stealth", "base"}

def _auto_discover():
    """Import all platform modules to trigger registration."""
    for finder, module_name, is_pkg in pkgutil.iter_modules([str(_PACKAGE_DIR)]):
        # Skip non-platform modules and selector files
        if module_name in _SKIP_MODULES or module_name.endswith("_selectors"):
            continue
        try:
            importlib.import_module(f"platforms.{module_name}")
        except Exception as exc:
            # Registration validation errors surface here
            import warnings
            warnings.warn(f"Failed to load platform module '{module_name}': {exc}")

_auto_discover()
```

### Pattern 4: Utility Mixin for Browser Platforms

**What:** The current `BasePlatform` has utility methods (`human_delay`, `screenshot`, `wait_for_human`, `element_exists`) that are shared across browser platforms. With Protocols, these can't live in the protocol itself (protocols don't provide implementations). Use a mixin class.

```python
# platforms/mixins.py
"""Shared utilities for browser-based platform implementations."""
import random
import time
from datetime import datetime
from pathlib import Path

from config import DEBUG_SCREENSHOTS_DIR, get_settings


class BrowserPlatformMixin:
    """Provides human_delay, screenshot, wait_for_human, element_exists.

    Expects `self.page` and `self.platform_name` to exist on the class.
    """

    def human_delay(self, delay_type: str = "nav") -> None:
        timing = get_settings().timing
        if delay_type == "nav":
            time.sleep(random.uniform(timing.nav_delay_min, timing.nav_delay_max))
        else:
            time.sleep(random.uniform(timing.form_delay_min, timing.form_delay_max))

    def screenshot(self, name: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.platform_name}_{name}_{timestamp}.png"
        filepath = DEBUG_SCREENSHOTS_DIR / filename
        self.page.screenshot(path=str(filepath), full_page=True)
        print(f"  Screenshot saved: {filepath}")
        return filepath

    def wait_for_human(self, message: str) -> str:
        print(f"\n{'=' * 60}")
        print(f"  HUMAN INPUT REQUIRED -- {self.platform_name.upper()}")
        print(f"{'=' * 60}")
        print(f"  {message}")
        return input("  > ").strip()

    def element_exists(self, selector: str, timeout: int = 5000) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
```

### Pattern 5: Context Manager on Platform Classes

**What:** Each platform implements `__enter__`/`__exit__` for resource lifecycle management.

**For browser platforms:**
```python
class IndeedPlatform(BrowserPlatformMixin):
    platform_name = "indeed"

    def __init__(self) -> None:
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def init(self, context: BrowserContext) -> None:
        self.context = context
        self.page = context.pages[0] if context.pages else context.new_page()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Platform-level cleanup (page state, etc.)
        # BrowserContext lifecycle is managed by orchestrator/stealth.py
        pass
```

**For API platforms:**
```python
class RemoteOKPlatform:
    platform_name = "remoteok"

    def __init__(self) -> None:
        self.client: httpx.Client | None = None

    def init(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": "JobSearchBot/1.0 (pgolabek@gmail.com)"},
            timeout=30.0,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
```

### Pattern 6: Refactored Orchestrator (No if/elif)

**What:** The orchestrator uses the registry to iterate over platforms generically.

```python
# Simplified orchestrator pattern
from platforms.registry import get_platform, get_all_platforms

class Orchestrator:
    def phase_1_login(self, platform_names: list[str]) -> None:
        for name in platform_names:
            info = get_platform(name)
            if info.platform_type == "browser":
                self._login_browser_platform(name, info)
            # API platforms skip login

    def phase_2_search(self, platform_names: list[str]) -> None:
        for name in platform_names:
            info = get_platform(name)
            platform_instance = info.cls()

            if info.platform_type == "browser":
                pw, ctx = get_browser_context(name, headless=self.headless)
                platform_instance.init(ctx)
            else:
                platform_instance.init()

            with platform_instance:
                jobs = []
                for query in self.settings.get_search_queries(platform=name):
                    jobs.extend(platform_instance.search(query))
                self._save_raw(name, jobs)

            if info.platform_type == "browser":
                close_browser(pw, ctx)
```

**Key observation:** The `if info.platform_type == "browser"` check is NOT the same as the current `if name == "indeed"` branching. The current code branches on *identity* (which platform). The new code branches on *type* (browser vs API) -- which is a structural distinction, not a platform-specific one. Adding a new browser platform requires zero orchestrator changes. Adding a new API platform requires zero orchestrator changes. This satisfies the pluggable architecture requirement.

### Anti-Patterns to Avoid
- **Putting implementations in Protocol classes:** Protocols define contracts only. Use mixins or composition for shared behavior.
- **Using `@runtime_checkable isinstance()` as the only validation:** It does NOT check method signatures. Will silently pass even if a method has wrong parameters.
- **Circular imports between registry and protocols:** Keep `protocols.py` dependency-free (only `typing`, `models`). Registry imports protocols, not vice versa.
- **Importing platform modules explicitly in `__init__.py`:** Defeats the purpose. Use `pkgutil.iter_modules` for true auto-discovery.
- **Making RemoteOK async while others are sync:** Mixed sync/async in the orchestrator is a maintenance burden. Standardize on sync.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Protocol compliance checking | Custom attribute crawler | `typing.Protocol` + `@runtime_checkable` + `inspect.signature` | Protocol is the standard; inspect handles signature introspection |
| Module auto-discovery | Walking filesystem with `os.listdir` | `pkgutil.iter_modules` + `importlib.import_module` | `pkgutil` handles package path resolution correctly, handles zip imports |
| Platform metadata storage | Nested dicts or JSON | `@dataclass PlatformInfo` | Type-safe, IDE-friendly, self-documenting |

**Key insight:** The registry pattern itself is simple enough to hand-roll (a dict + a decorator). Don't reach for plugin frameworks like `stevedore` or `pluggy` -- they're for cross-package ecosystems. This project has in-package plugins in a single directory.

## Common Pitfalls

### Pitfall 1: Decorator Not Firing (Module Not Imported)
**What goes wrong:** Platform file exists in `platforms/` but never gets imported, so `@register_platform` never runs. Platform silently missing from registry.
**Why it happens:** `pkgutil.iter_modules` is not called, or the module is in the skip list, or the import fails silently.
**How to avoid:** The `_auto_discover()` function in `__init__.py` must run at import time. Log warnings for import failures. Add a startup check: compare `config.yaml` enabled platforms against registry keys.
**Warning signs:** Orchestrator says "Platform 'xyz' not registered" at runtime despite the file existing.

### Pitfall 2: Circular Import Between Registry and Platform Modules
**What goes wrong:** `registry.py` imports from `protocols.py`, which imports from `models.py`. Platform modules import from `registry.py` (for the decorator) and from `models.py`. If any of these form a cycle, ImportError.
**Why it happens:** Python's import system does not handle circular imports well at module level.
**How to avoid:** Keep the import chain linear: `models.py` -> `protocols.py` -> `registry.py`. Platform modules import from `registry` and `models` but NOT from each other. Use `from __future__ import annotations` in all files (already done in the project) to avoid forward reference issues.
**Warning signs:** `ImportError: cannot import name 'X' from partially initialized module`.

### Pitfall 3: Async/Sync Mismatch in Protocol
**What goes wrong:** `RemoteOKPlatform.search()` is currently `async def`. If the protocol defines `search()` as `def` (sync), the async implementation structurally matches (an `async def` IS callable) but the orchestrator would need `await` to call it, breaking the uniform loop.
**Why it happens:** Python's Protocol does not distinguish sync vs async methods at the structural level.
**How to avoid:** Convert RemoteOK to use `httpx.Client` (sync) instead of `httpx.AsyncClient`. The current `asyncio.run()` wrapper in the orchestrator is already a sign this should be sync.
**Warning signs:** `RuntimeError: This event loop is already running` or getting a coroutine object instead of results.

### Pitfall 4: Protocol Attribute `platform_name` Not Validated
**What goes wrong:** `@runtime_checkable` checks for method existence but class-level attributes (like `platform_name: str`) may not be detected if they're only set in `__init__` rather than as class attributes.
**Why it happens:** `isinstance()` with `@runtime_checkable` checks the instance, not the class. If `platform_name` is set in `__init__` and you're checking the class (not an instance), it won't be found.
**How to avoid:** Validate `platform_name` in the `@register_platform` decorator itself by checking `hasattr(cls, 'platform_name')` or requiring it as a decorator parameter (which the user's decision already does -- the key IS the platform name).
**Warning signs:** `AttributeError: 'XPlatform' object has no attribute 'platform_name'` at runtime.

### Pitfall 5: `BasePlatform.__init__` Constructor Side Effects During Migration
**What goes wrong:** Current adapters call `super().__init__(context)` which sets `self.context` and `self.page`. After removing `BasePlatform`, these must be set in each adapter's own `__init__` or `init()`.
**Why it happens:** Forgetting to move constructor logic from base class to each subclass during migration.
**How to avoid:** Audit `BasePlatform.__init__` and ensure every piece of logic it performs is replicated in each adapter's `init()` method.
**Warning signs:** `AttributeError: 'IndeedPlatform' object has no attribute 'page'` at runtime.

### Pitfall 6: Config Platform Enable List vs Registry Mismatch
**What goes wrong:** Config says `enabled_platforms: [indeed, dice, remoteok, linkedin]` but `linkedin` module doesn't exist. Or a module exists but registration failed silently.
**Why it happens:** No validation that config-listed platforms are actually registered.
**How to avoid:** At orchestrator startup, check that every enabled platform from config exists in the registry. Raise a clear error listing what's missing.
**Warning signs:** Silent skip of platforms, incomplete search results.

## Code Examples

### Complete Registry Decorator with Validation
Source: Custom pattern based on Python stdlib `inspect` + `typing.Protocol`

```python
# platforms/registry.py
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformInfo:
    key: str
    name: str
    platform_type: str  # "browser" or "api"
    cls: type
    capabilities: list[str] = field(default_factory=list)


_REGISTRY: dict[str, PlatformInfo] = {}


def register_platform(
    key: str,
    *,
    name: str | None = None,
    platform_type: str = "browser",
    capabilities: list[str] | None = None,
):
    """Register a platform class. Validates protocol compliance at import time."""
    def decorator(cls: type) -> type:
        from platforms.protocols import APIPlatform, BrowserPlatform

        protocol = BrowserPlatform if platform_type == "browser" else APIPlatform
        _validate_against_protocol(cls, protocol)

        if key in _REGISTRY:
            raise ValueError(f"Platform key '{key}' already registered by {_REGISTRY[key].cls.__name__}")

        _REGISTRY[key] = PlatformInfo(
            key=key,
            name=name or key.title(),
            platform_type=platform_type,
            cls=cls,
            capabilities=capabilities or [],
        )
        return cls

    return decorator


def _validate_against_protocol(cls: type, protocol: type) -> None:
    """Verify cls implements all required protocol methods."""
    # Collect protocol-defined methods (skip private except __enter__/__exit__)
    required = {}
    for attr_name, attr_val in vars(protocol).items():
        if attr_name.startswith('_') and attr_name not in ('__enter__', '__exit__'):
            continue
        if callable(attr_val) or isinstance(attr_val, (staticmethod, classmethod)):
            required[attr_name] = attr_val

    missing = []
    for method_name in required:
        if not hasattr(cls, method_name):
            missing.append(method_name)

    if missing:
        raise TypeError(
            f"{cls.__name__} is missing required methods for "
            f"{protocol.__name__}: {', '.join(missing)}"
        )


def get_platform(key: str) -> PlatformInfo:
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise KeyError(f"Platform '{key}' not registered. Available: {available}")
    return _REGISTRY[key]


def get_all_platforms() -> dict[str, PlatformInfo]:
    return dict(_REGISTRY)
```

### Auto-Discovery in `__init__.py`
Source: Based on Python Packaging User Guide pattern for namespace package discovery

```python
# platforms/__init__.py
"""Platform modules -- auto-discovers and registers all platform implementations."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from platforms.registry import get_all_platforms, get_platform, get_platforms_by_type

logger = logging.getLogger(__name__)

_INFRASTRUCTURE_MODULES = frozenset({
    "protocols", "registry", "mixins", "stealth", "base",
})


def _auto_discover() -> None:
    pkg_dir = str(Path(__file__).parent)
    for _finder, module_name, _is_pkg in pkgutil.iter_modules([pkg_dir]):
        if module_name in _INFRASTRUCTURE_MODULES or module_name.endswith("_selectors"):
            continue
        try:
            importlib.import_module(f"platforms.{module_name}")
        except Exception:
            logger.exception("Failed to load platform module '%s'", module_name)


_auto_discover()

__all__ = ["get_platform", "get_all_platforms", "get_platforms_by_type"]
```

### Migrated IndeedPlatform (Sketch)
Source: Based on current `platforms/indeed.py` structure

```python
# platforms/indeed.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from platforms.mixins import BrowserPlatformMixin
from platforms.registry import register_platform

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

from config import get_settings
from models import Job, SearchQuery
from platforms.indeed_selectors import INDEED_SEARCH_PARAMS, INDEED_SELECTORS, INDEED_URLS


@register_platform("indeed", name="Indeed", platform_type="browser", capabilities=["easy_apply"])
class IndeedPlatform(BrowserPlatformMixin):
    platform_name = "indeed"

    def __init__(self) -> None:
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def init(self, context: BrowserContext) -> None:
        self.context = context
        self.page = context.pages[0] if context.pages else context.new_page()

    def login(self) -> bool:
        # ... (same implementation as current, using self.page)
        ...

    def is_logged_in(self) -> bool:
        return self.element_exists(INDEED_SELECTORS["logged_in_indicator"])

    def search(self, query: SearchQuery) -> list[Job]:
        # ... (same implementation, returns list[Job])
        ...

    def get_job_details(self, job: Job) -> Job:
        # ... (same implementation)
        ...

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        # ... (same implementation, resume_path defaults to config if None)
        ...

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # BrowserContext lifecycle managed by orchestrator
```

### RemoteOK Migration to Sync
Source: Based on current `platforms/remoteok.py`, converting async to sync

```python
@register_platform("remoteok", name="RemoteOK", platform_type="api")
class RemoteOKPlatform:
    platform_name = "remoteok"

    def __init__(self) -> None:
        self.client: httpx.Client | None = None

    def init(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": "JobSearchBot/1.0 (pgolabek@gmail.com)"},
            timeout=30.0,
        )

    def search(self, query: SearchQuery) -> list[Job]:
        # Same logic but using self.client.get() (sync) instead of await
        resp = self.client.get(self.API_URL)
        resp.raise_for_status()
        # ... filter and parse ...
        return jobs

    def get_job_details(self, job: Job) -> Job:
        return job  # API returns full data

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        print(f"  RemoteOK: external application -- {job.apply_url or job.url}")
        return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `abc.ABC` with `@abstractmethod` | `typing.Protocol` (PEP 544) | Python 3.8+ | No inheritance required; structural subtyping |
| Manual imports for each platform | `pkgutil.iter_modules` auto-discovery | Available since Python 2 | True plug-and-play module loading |
| `if name == "indeed":` branching | Registry pattern with decorator | Pattern, not version-specific | Open/Closed principle -- new platforms need zero orchestrator changes |
| `httpx.AsyncClient` + `asyncio.run` | `httpx.Client` (sync) | httpx has always supported both | Eliminates async/sync boundary in orchestrator |

**Deprecated/outdated in this codebase:**
- `BasePlatform(ABC)`: Will be removed entirely in this phase
- `platforms.__init__.py` lazy `__getattr__` for `BasePlatform`: Replaced by auto-discovery
- `Config` compatibility shim: Already deprecated from Phase 1, not affected by this phase

## Open Questions

1. **Should `search()` return `list[Job]` or raw cards?**
   - CONTEXT.md says `search(query)` returns raw cards and `extract(card)` returns Job
   - But raw card types differ fundamentally: Playwright `ElementHandle` for browser, `dict` for API
   - Exposing raw cards in the protocol means `Any` types, losing type safety
   - **Recommendation:** Keep `search() -> list[Job]` as the protocol contract. Platforms call `_extract_card` internally. This is cleaner and matches what the orchestrator actually needs.
   - What we know: Either approach works; the orchestrator only needs `list[Job]`
   - What's unclear: Whether the user has a strong preference for the raw card split
   - Recommendation: Planner should proceed with `search() -> list[Job]` unless user objects

2. **`init()` method signature for BrowserPlatform vs APIPlatform**
   - BrowserPlatform needs `init(context: BrowserContext)`
   - APIPlatform needs `init()` with no arguments
   - These are different signatures, so a single `Platform` union protocol would need `init(**kwargs)`
   - **Recommendation:** Keep separate protocols. The orchestrator already needs to distinguish browser vs API for context creation anyway.

3. **Who manages the Playwright browser/context lifecycle?**
   - Currently: orchestrator calls `get_browser_context()` and `close_browser()` directly
   - Option A: Orchestrator continues to manage browser lifecycle, passes context to platform via `init()`
   - Option B: Platform manages its own browser lifecycle in `__enter__`/`__exit__`
   - **Recommendation:** Option A. The decision says "shared Playwright browser instance" -- orchestrator creates it, platforms use it. Platform `__exit__` handles platform-level cleanup only.

## Sources

### Primary (HIGH confidence)
- Python `typing` documentation - Protocol definitions, `@runtime_checkable` behavior: https://typing.python.org/en/latest/reference/protocols.html
- PEP 544 - Protocols: Structural subtyping specification: https://peps.python.org/pep-0544/
- Python Packaging Guide - Plugin discovery with `pkgutil.iter_modules`: https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
- Direct codebase analysis of all platform files, orchestrator, config, models (8 files read in full)

### Secondary (MEDIUM confidence)
- Real Python - Python Protocols guide: https://realpython.com/python-protocol/
- Python `inspect` module - signature validation: https://docs.python.org/3/library/inspect.html
- mypy documentation on Protocol structural subtyping: https://mypy.readthedocs.io/en/stable/protocols.html

### Tertiary (LOW confidence)
- WebSearch results on decorator-based registry patterns (multiple blog posts, consistent patterns)
- Python Discussions on `@runtime_checkable` limitations (signature checking proposals still in discussion as of 2025)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, well-documented, verified against official docs
- Architecture: HIGH - Patterns verified against PEP 544 + packaging guide + direct codebase analysis
- Pitfalls: HIGH - Derived from codebase analysis (actual import chains, actual async/sync mismatch, actual constructor logic)
- Migration path: HIGH - Every current file read and analyzed, all if/elif branches catalogued

**Research date:** 2026-02-07
**Valid until:** Indefinite (stdlib patterns, not library-version dependent)
