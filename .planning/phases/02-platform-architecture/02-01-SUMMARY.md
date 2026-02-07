---
phase: 02-platform-architecture
plan: 01
subsystem: platform-infrastructure
tags: [protocols, registry, mixin, pluggable-architecture, decorator]

# Dependency graph
requires:
  - 01-config-externalization (get_settings, DEBUG_SCREENSHOTS_DIR)
provides:
  - BrowserPlatform and APIPlatform Protocol classes
  - "@register_platform decorator with fail-fast validation"
  - PlatformInfo dataclass for registry entries
  - BrowserPlatformMixin with shared browser utilities
affects:
  - 02-02 (platform adapter migration will use protocols, registry, mixin)
  - 02-03 (orchestrator refactor will use registry to discover platforms)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Protocol-based contracts instead of ABC inheritance"
    - "Decorator-based registry with import-time validation"
    - "Mixin for shared utilities (composition over inheritance)"

# File tracking
key-files:
  created:
    - platforms/protocols.py
    - platforms/registry.py
    - platforms/mixins.py
  modified: []

# Decisions
decisions:
  - key: protocol-method-signatures
    decision: "BrowserPlatform.init(context) receives BrowserContext; APIPlatform.init() takes no args"
    rationale: "Clean separation -- orchestrator provides context to browser platforms, API platforms self-initialize"
  - key: validation-approach
    decision: "inspect.signature() compares required parameter counts, not types"
    rationale: "Type comparison is unreliable with forward refs and TYPE_CHECKING imports; parameter count catches the most common errors (extra required params that would break callers)"
  - key: lazy-protocol-import
    decision: "Registry imports protocols lazily inside the decorator function"
    rationale: "Decorator runs at platform module import time; eager import would create circular dependencies"

# Metrics
duration: 3 min
completed: 2026-02-07
---

# Phase 02 Plan 01: Protocol Definitions, Registry, and Mixin Summary

**Protocol-based platform contracts with decorator registry and fail-fast validation using inspect.signature**

## What Was Built

Three foundational infrastructure files that enable the pluggable platform architecture:

1. **`platforms/protocols.py`** -- Two `@runtime_checkable` Protocol classes defining the contracts all platform adapters must implement:
   - `BrowserPlatform` -- 8 methods (init, login, is_logged_in, search, get_job_details, apply, __enter__, __exit__) plus `platform_name` attribute
   - `APIPlatform` -- 6 methods (init, search, get_job_details, apply, __enter__, __exit__) plus `platform_name` -- no login/is_logged_in since API platforms don't authenticate via browser

2. **`platforms/registry.py`** -- Decorator-based registry with validation:
   - `@register_platform(key, name=, platform_type=, capabilities=)` decorator
   - `_validate_against_protocol()` using `inspect.signature()` to check method existence and parameter count compatibility
   - `PlatformInfo` dataclass storing key, name, platform_type, cls, capabilities
   - `get_platform()`, `get_all_platforms()`, `get_platforms_by_type()` accessors
   - Duplicate key detection (raises ValueError)
   - Lazy protocol import inside decorator to avoid circular dependencies

3. **`platforms/mixins.py`** -- `BrowserPlatformMixin` with four utility methods extracted from `BasePlatform`:
   - `human_delay(delay_type)` -- randomized nav/form delays from settings.timing
   - `screenshot(name)` -- full-page capture to debug_screenshots/
   - `wait_for_human(message)` -- blocking stdin prompt for human-in-the-loop
   - `element_exists(selector, timeout)` -- non-throwing selector check

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create Protocol definitions and registry | df9e444 | platforms/protocols.py, platforms/registry.py |
| 2 | Create BrowserPlatformMixin | 3876ee6 | platforms/mixins.py |

## Decisions Made

1. **Protocol method signatures**: `BrowserPlatform.init(context)` receives BrowserContext from orchestrator; `APIPlatform.init()` takes no arguments. Clean separation of concerns.

2. **Validation approach**: `inspect.signature()` compares required parameter counts rather than types. Type comparison is unreliable with forward references and TYPE_CHECKING imports; parameter count catches the most common integration errors.

3. **Lazy protocol import in registry**: The `@register_platform` decorator imports protocols lazily inside the decorator function, not at module level. This avoids circular dependencies since the decorator executes at platform module import time.

4. **Import chain**: Strictly linear `models -> protocols -> registry` with no cycles. Mixin imports from `config` only.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

All success criteria verified:
- `protocols.py` defines `BrowserPlatform` and `APIPlatform` as `@runtime_checkable` Protocol classes
- `registry.py` provides `@register_platform` decorator with fail-fast protocol validation via inspect
- `mixins.py` provides `BrowserPlatformMixin` with all four `BasePlatform` utility methods
- Import chain is linear: models -> protocols -> registry (no cycles)
- All files importable without errors
- Fail-fast validation catches missing methods with descriptive TypeError
- Duplicate key detection raises ValueError
- `get_platform()` raises helpful KeyError listing available platforms

## Next Phase Readiness

Plan 02-02 (Platform Adapter Migration) can proceed immediately. The protocols, registry, and mixin are ready to receive the Indeed, Dice, and RemoteOK adapter migrations.

## Self-Check: PASSED
