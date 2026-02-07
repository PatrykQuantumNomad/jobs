---
phase: 04-scheduled-automation
plan: 01
subsystem: infra
tags: [launchd, scheduler, plist, unattended, cli]

# Dependency graph
requires:
  - phase: 01-config-externalization
    provides: "AppSettings with ScheduleConfig placeholder, config.yaml, get_settings()"
  - phase: 02-platform-architecture
    provides: "BrowserPlatformMixin with wait_for_human, platform registry"
provides:
  - "ScheduleConfig model with hour/minute/weekdays validation"
  - "--scheduled CLI flag for unattended pipeline execution"
  - "scheduler.py CLI for launchd plist install/uninstall/status"
  - "All input() sites guarded with _unattended RuntimeError"
affects: [04-scheduled-automation, dashboard-core]

# Tech tracking
tech-stack:
  added: [plistlib, launchctl]
  patterns: ["_unattended flag propagation from orchestrator to platform instances", "launchd plist generation with absolute paths"]

key-files:
  created: [scheduler.py]
  modified: [config.py, config.yaml, orchestrator.py, platforms/mixins.py, platforms/indeed.py]

key-decisions:
  - "Use getattr(self, '_unattended', False) for backward compatibility -- platforms may not have the attribute set"
  - "sys.executable resolved via Path().resolve() for absolute venv Python path in plist"
  - "launchctl bootstrap/bootout (not legacy load/unload) for modern macOS agent management"

patterns-established:
  - "_unattended flag: orchestrator sets on platform instances, checked before any input() call"
  - "Plist generation: all paths absolute, no shell variables, plistlib.dump()"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 4 Plan 01: Scheduler Config, Unattended Mode, and Launchd CLI Summary

**ScheduleConfig model with Pydantic validation, --scheduled flag skipping human interaction, and scheduler.py CLI for macOS launchd agent management**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T19:47:37Z
- **Completed:** 2026-02-07T19:51:47Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ScheduleConfig model validates hour (0-23), minute (0-59), and weekdays (0-6 list or None) with Pydantic field_validator
- config.yaml schedule section populated with real defaults (enabled: false, hour: 8, minute: 0)
- --scheduled flag forces headless mode, skips phase_4_apply, and propagates _unattended to all platform instances
- All 3 input() call sites guarded: orchestrator apply (early return), indeed login (RuntimeError), mixins wait_for_human (RuntimeError)
- scheduler.py generates valid launchd plist with absolute paths and supports install/uninstall/status subcommands

## Task Commits

Each task was committed atomically:

1. **Task 1: Populate ScheduleConfig model and config.yaml, add --scheduled flag and guard all input() sites** - `3b8bfa9` (feat)
2. **Task 2: Create scheduler.py with plist generation, install, uninstall, and status commands** - `ab405cd` (feat)

## Files Created/Modified
- `scheduler.py` - CLI tool for launchd plist generation, install, uninstall, status
- `config.py` - ScheduleConfig model with enabled/hour/minute/weekdays fields and validation
- `config.yaml` - Schedule section with real defaults replacing empty {}
- `orchestrator.py` - --scheduled flag, phase_4_apply guard, _unattended propagation
- `platforms/mixins.py` - wait_for_human() guard for unattended mode
- `platforms/indeed.py` - login() guard for unattended mode (expired session)

## Decisions Made
- Used `getattr(self, '_unattended', False)` for backward compatibility -- platforms may not always have the attribute set
- Used `sys.executable` resolved to absolute path for venv Python in plist ProgramArguments
- Used `launchctl bootstrap/bootout` (modern API) instead of deprecated `load/unload`
- Plist generation ensures zero shell variables ($HOME, ~) -- all paths are Path.resolve() absolutes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Scheduler foundation complete, ready for Plan 04-02 (run history table and /runs dashboard page)
- scheduler.py install/uninstall are functional but schedule.enabled defaults to false -- user must enable in config.yaml before installing
- Run history logging (mentioned in --scheduled help text) will be implemented in Plan 04-02

---
*Phase: 04-scheduled-automation*
*Completed: 2026-02-07*
