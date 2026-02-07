# Phase 4: Scheduled Automation - Research

**Researched:** 2026-02-07
**Domain:** macOS launchd scheduling, unattended pipeline execution, run history logging
**Confidence:** HIGH

## Summary

Phase 4 adds scheduled automation so the job search pipeline runs daily without manual CLI invocation. The platform is macOS, which means **launchd** (via LaunchAgents) is the correct and only recommended scheduling mechanism -- Apple has deprecated cron in favor of launchd for over a decade.

The implementation requires three coordinated changes: (1) extending the existing `ScheduleConfig` placeholder in `config.yaml` to accept human-readable schedule expressions, (2) a Python-based plist generator that translates those expressions into launchd `StartCalendarInterval` XML and installs them into `~/Library/LaunchAgents/`, and (3) a `run_history` table in the existing SQLite database plus a `--scheduled` CLI flag on `orchestrator.py` that skips all `input()` calls and logs run metadata.

The biggest design constraint is that **browser-based platforms (Indeed, Dice) require human interaction for CAPTCHA/login on first run**, but scheduled runs must execute without any stdin interaction. The existing pipeline has three `input()` call sites that would block an unattended run forever. Scheduled mode must either skip these platforms when sessions are stale, or handle the failure gracefully and log it.

**Primary recommendation:** Use Python's stdlib `plistlib` to generate launchd plist files from the `ScheduleConfig` model. Add a `--scheduled` flag to `orchestrator.py` that suppresses all `input()` calls, forces headless mode, and logs run outcomes to a `run_history` SQLite table. Expose run history on the existing web dashboard.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `plistlib` | stdlib | Generate macOS launchd plist XML files | Built into Python -- no dependency needed. Produces valid Apple plist XML via `plistlib.dump()`. |
| `logging` | stdlib | Structured run logging for scheduled executions | Already partially used in `platforms/__init__.py`. Standard Python logging with `RotatingFileHandler` for file output. |
| `sqlite3` | stdlib | Run history table in existing `jobs.db` | Already the database backend. Adding a `run_history` table is a natural extension. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` | stdlib | Run `launchctl` commands to load/unload agents | Needed for `launchctl bootstrap`/`bootout` when installing/removing the schedule. |
| `shutil` | stdlib | Copy/remove plist files in `~/Library/LaunchAgents/` | For install/uninstall of the generated plist. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `plistlib` (stdlib) | Manual XML string templates | `plistlib` is type-safe and handles escaping; raw XML is fragile and error-prone. Use `plistlib`. |
| launchd `StartCalendarInterval` | `StartInterval` (seconds-based) | `StartInterval` only does fixed intervals (e.g., "every 3600 seconds"), not "daily at 8am". `StartCalendarInterval` maps directly to cron-like scheduling. Use `StartCalendarInterval`. |
| launchd | `crontab` (via `python-crontab`) | Apple has deprecated cron on macOS. launchd is the officially supported mechanism and handles wake-from-sleep catch-up (missed runs fire on next wake). Use launchd. |
| launchd | `APScheduler` / `schedule` (Python) | These are in-process schedulers that require a long-running Python process. launchd is OS-level -- the pipeline process starts, runs, and exits. No daemon to keep alive. Use launchd. |
| Single `run_history` table | Separate log files per run | SQLite table is queryable from the dashboard, supports filtering/aggregation, and lives alongside existing job data. Log files can supplement but should not replace structured history. |

**Installation:**
```bash
# No new dependencies required -- all stdlib
# Existing requirements.txt is sufficient
```

## Architecture Patterns

### Recommended Project Structure
```
project-root/
├── scheduler.py              # NEW: plist generator + launchctl management
├── config.py                 # MODIFIED: ScheduleConfig model populated
├── config.yaml               # MODIFIED: schedule section populated
├── orchestrator.py            # MODIFIED: --scheduled flag, run history logging
├── webapp/
│   ├── db.py                 # MODIFIED: run_history table + queries
│   └── app.py                # MODIFIED: run history dashboard endpoint
│   └── templates/
│       └── run_history.html  # NEW: run history view
└── job_pipeline/
    ├── jobs.db               # EXISTING: gains run_history table
    └── logs/                 # NEW: rotating log files for scheduled runs
        └── pipeline.log
```

### Pattern 1: Plist Generation with `plistlib`
**What:** Generate a valid launchd plist XML file from Python dict using `plistlib.dump()`.
**When to use:** When the user runs `python scheduler.py install` to set up their schedule.
**Example:**
```python
# Source: Python stdlib plistlib docs + Apple launchd.plist(5) man page
import plistlib
from pathlib import Path

LABEL = "com.jobflow.pipeline"

def generate_plist(
    python_path: str,
    project_root: str,
    hour: int,
    minute: int,
    log_dir: str,
) -> dict:
    """Build a launchd plist dict for StartCalendarInterval scheduling."""
    return {
        "Label": LABEL,
        "ProgramArguments": [
            python_path,
            f"{project_root}/orchestrator.py",
            "--scheduled",
        ],
        "WorkingDirectory": project_root,
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "StandardOutPath": f"{log_dir}/pipeline.log",
        "StandardErrorPath": f"{log_dir}/pipeline.err",
        "EnvironmentVariables": {
            "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin",
            "VIRTUAL_ENV": f"{project_root}/.venv",
        },
        "ProcessType": "Background",
    }

def write_plist(plist_data: dict, dest: Path) -> None:
    with open(dest, "wb") as f:
        plistlib.dump(plist_data, f)
```

### Pattern 2: Unattended Mode Flag
**What:** A `--scheduled` CLI flag that modifies pipeline behavior for non-interactive execution.
**When to use:** Every scheduled run. The flag controls three behaviors: (1) force headless, (2) skip `input()` calls (skip login if session stale, skip apply phase entirely), (3) write structured run log.
**Example:**
```python
# In orchestrator.py
parser.add_argument(
    "--scheduled",
    action="store_true",
    help="Unattended mode: headless, no input prompts, logs run history",
)

# In Orchestrator.__init__:
self.scheduled = scheduled
if scheduled:
    self.headless = True  # Force headless in scheduled mode
```

### Pattern 3: Run History in SQLite
**What:** A `run_history` table that records when each pipeline run happened, what it found, and whether it succeeded.
**When to use:** Written at the end of every pipeline run (both manual and scheduled).
**Example:**
```python
# In webapp/db.py
RUN_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'manual',   -- 'manual' | 'scheduled'
    platforms_searched TEXT NOT NULL,       -- JSON array
    total_raw INTEGER DEFAULT 0,
    total_scored INTEGER DEFAULT 0,
    new_jobs INTEGER DEFAULT 0,            -- jobs not seen before
    errors TEXT DEFAULT '[]',              -- JSON array of error strings
    status TEXT NOT NULL DEFAULT 'success', -- 'success' | 'partial' | 'failed'
    duration_seconds REAL DEFAULT 0.0
);
"""
```

### Pattern 4: launchctl Install/Uninstall
**What:** CLI commands to install (load) and uninstall (unload) the launchd agent.
**When to use:** User runs `python scheduler.py install` or `python scheduler.py uninstall`.
**Example:**
```python
import subprocess
import os

PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

def install_schedule():
    """Copy plist to ~/Library/LaunchAgents/ and load it."""
    write_plist(plist_data, PLIST_DEST)
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_DEST)],
        check=True,
    )

def uninstall_schedule():
    """Unload and remove the plist."""
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(PLIST_DEST)],
        check=False,  # May fail if not loaded
    )
    PLIST_DEST.unlink(missing_ok=True)
```

### Anti-Patterns to Avoid
- **Using cron on macOS:** Apple deprecated cron years ago. launchd is the only supported mechanism. launchd also handles missed runs (fires on wake from sleep), which cron does not.
- **Long-running Python daemon for scheduling:** APScheduler/schedule require a persistent process. launchd launches the script, it runs, it exits. No daemon management overhead.
- **Absolute paths to Homebrew Python in plist:** The venv Python binary at `.venv/bin/python` already resolves to the correct interpreter. Use the venv path, not `/opt/homebrew/bin/python3`.
- **Using `$HOME` in plist paths:** launchd does NOT expand shell variables like `$HOME` or `~` in plist values. All paths must be absolute and fully resolved. Use `Path.home()` in Python to resolve before writing.
- **Ignoring `input()` calls in scheduled mode:** If the pipeline hits `input()` in a scheduled run (no stdin), it will hang forever. The launchd job will appear stuck. Every `input()` call site must be guarded.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plist XML generation | String-template XML | `plistlib.dump()` (stdlib) | Handles escaping, encoding, proper XML formatting automatically. String templates are fragile and produce invalid XML on edge cases. |
| Cron expression parsing | Custom time parser | `ScheduleConfig` Pydantic model with `hour`/`minute` integer fields | The schedule config is simple (daily at H:M). No need for full cron expression parsing. |
| Log file rotation | Custom file management | `logging.handlers.RotatingFileHandler` (stdlib) | Handles rotation, backup count, max file size. Rolling your own risks filling disk. |
| launchctl load/unload | Manual shell scripts | `subprocess.run(["launchctl", ...])` | Python subprocess is sufficient. Shell scripts add an unnecessary layer. |
| Run history persistence | JSON files per run | SQLite `run_history` table in existing `jobs.db` | Queryable, aggregatable, displayable on the existing dashboard without additional infrastructure. |

**Key insight:** This phase is primarily integration and configuration work, not new algorithmic complexity. Every component needed (plist generation, logging, SQLite, subprocess) is in Python's standard library. The complexity lies in correctly wiring the unattended mode and handling the `input()` blocking sites.

## Common Pitfalls

### Pitfall 1: `input()` Blocks Hang Scheduled Runs Forever
**What goes wrong:** The pipeline has three `input()` calls (orchestrator apply phase, Indeed login, mixins `wait_for_human`). In a scheduled run with no stdin, these block indefinitely. The launchd job appears stuck, resources are consumed, and no output is produced.
**Why it happens:** The current pipeline assumes an interactive terminal.
**How to avoid:** The `--scheduled` flag must set an `unattended` boolean on the Orchestrator. Every `input()` call site must check this flag. In unattended mode: (a) `phase_4_apply` is skipped entirely, (b) if Indeed/Dice login is required (session expired), skip that platform and log a warning, (c) `wait_for_human` raises an exception or returns a default.
**Warning signs:** A launchd job that runs but never completes. Check `launchctl list | grep jobflow`.

### Pitfall 2: launchd Does Not Expand Shell Variables
**What goes wrong:** Using `$HOME`, `~`, or `$VIRTUAL_ENV` in plist values produces literal strings, not expanded paths. The job fails because paths don't resolve.
**Why it happens:** launchd is not a shell. It does not perform variable expansion.
**How to avoid:** Always resolve paths to absolute strings in Python before writing the plist. Use `Path.home().resolve()` and `Path.cwd().resolve()`.
**Warning signs:** "No such file or directory" in StandardErrorPath output.

### Pitfall 3: Python Virtualenv Not Activated in launchd Context
**What goes wrong:** The scheduled job runs with the system Python (or no Python at all) instead of the project's venv. Dependencies are missing, imports fail.
**Why it happens:** launchd does not source `.bashrc` or activate any virtualenv.
**How to avoid:** In `ProgramArguments`, use the **absolute path** to the venv's Python binary (e.g., `/Users/patrykattc/work/jobs/.venv/bin/python`). This binary automatically uses the venv's site-packages without activation.
**Warning signs:** `ModuleNotFoundError` for `pydantic`, `playwright`, etc. in the error log.

### Pitfall 4: Working Directory Not Set
**What goes wrong:** The pipeline uses relative paths (e.g., `config.yaml`, `browser_sessions/`, `job_pipeline/`). Without `WorkingDirectory` in the plist, launchd starts the process in `/`, and all relative paths fail.
**Why it happens:** launchd defaults working directory to `/` unless specified.
**How to avoid:** Always set `WorkingDirectory` in the plist to the project root.
**Warning signs:** "config.yaml not found" or database created at `/job_pipeline/jobs.db`.

### Pitfall 5: SQLite Concurrent Access Between Dashboard and Pipeline
**What goes wrong:** If the web dashboard (FastAPI) and the scheduled pipeline run write to `jobs.db` simultaneously, one may get a "database is locked" error.
**Why it happens:** SQLite allows only one writer at a time. The existing code already uses WAL mode (`PRAGMA journal_mode=WAL`), which helps but doesn't eliminate contention.
**How to avoid:** WAL mode (already enabled) handles this well for the expected load (one writer, one reader). The pipeline writes are brief and sequential. Add a `busy_timeout` pragma (e.g., 5000ms) so SQLite retries instead of failing immediately on lock contention.
**Warning signs:** "database is locked" errors in scheduled run logs.

### Pitfall 6: Log Files Grow Unbounded
**What goes wrong:** `StandardOutPath`/`StandardErrorPath` in launchd append to the file on every run. Over weeks/months, these files grow large.
**Why it happens:** launchd does not rotate logs.
**How to avoid:** Use Python's `RotatingFileHandler` for application-level logging (inside the pipeline). For launchd stdout/stderr, point them to a `logs/` directory and document that the user should periodically clean them, or redirect them to `/dev/null` since application logging captures everything.
**Warning signs:** Large files in `job_pipeline/logs/`.

### Pitfall 7: Playwright Fails in Headless Mode on macOS
**What goes wrong:** Playwright's Chromium may fail to launch in headless mode from a launchd context due to missing display server or sandboxing restrictions.
**Why it happens:** launchd agents run in a different environment than interactive terminals. Some Chrome flags or sandbox settings may conflict.
**How to avoid:** Use `channel="chrome"` (system Chrome, already configured in `stealth.py`) with `headless=True`. Test the scheduled job manually first with `launchctl kickstart`. If issues arise, add `--no-sandbox` to browser args.
**Warning signs:** Playwright crash errors in the error log mentioning display or sandbox.

## Code Examples

Verified patterns from official sources:

### Generating a launchd plist with plistlib
```python
# Source: Python stdlib plistlib documentation
import plistlib
from pathlib import Path

plist_data = {
    "Label": "com.jobflow.pipeline",
    "ProgramArguments": [
        str(Path.home() / "work/jobs/.venv/bin/python"),
        str(Path.home() / "work/jobs/orchestrator.py"),
        "--scheduled",
    ],
    "WorkingDirectory": str(Path.home() / "work/jobs"),
    "StartCalendarInterval": {
        "Hour": 8,
        "Minute": 0,
    },
    "StandardOutPath": str(Path.home() / "work/jobs/job_pipeline/logs/pipeline.log"),
    "StandardErrorPath": str(Path.home() / "work/jobs/job_pipeline/logs/pipeline.err"),
    "ProcessType": "Background",
}

plist_path = Path.home() / "Library/LaunchAgents/com.jobflow.pipeline.plist"
with open(plist_path, "wb") as f:
    plistlib.dump(plist_data, f)
```

### Installing/Uninstalling with launchctl
```python
# Source: Apple launchd.plist(5) man page, launchctl(1) man page
import os
import subprocess

def install(plist_path: Path) -> None:
    uid = os.getuid()
    # Modern launchctl API (macOS 10.10+)
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
        check=True,
    )
    print(f"Installed: {plist_path.name}")

def uninstall(plist_path: Path) -> None:
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(plist_path)],
        check=False,
    )
    plist_path.unlink(missing_ok=True)
    print(f"Uninstalled: {plist_path.name}")

def status() -> str:
    """Check if the job is loaded."""
    result = subprocess.run(
        ["launchctl", "list", "com.jobflow.pipeline"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return "loaded"
    return "not loaded"
```

### ScheduleConfig Pydantic Model
```python
# Extends the existing placeholder in config.py
from pydantic import BaseModel, Field, field_validator

class ScheduleConfig(BaseModel):
    """Top-level ``schedule:`` section of config.yaml."""

    enabled: bool = False
    hour: int = Field(default=8, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    weekdays: list[int] | None = Field(
        default=None,
        description="Days of week to run (0=Sun, 1=Mon, ..., 6=Sat). None = daily.",
    )

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for day in v:
                if not (0 <= day <= 6):
                    raise ValueError(f"Weekday must be 0-6, got {day}")
        return v
```

### config.yaml schedule section
```yaml
# -- Schedule Configuration -------------------------------------------------
schedule:
  enabled: true        # Set to true and run 'python scheduler.py install'
  hour: 8              # Hour (0-23) to run the pipeline
  minute: 0            # Minute (0-59) to run the pipeline
  # weekdays: [1,2,3,4,5]  # Optional: limit to specific days (0=Sun, 6=Sat)
                            # Omit for daily execution
```

### Guarding input() Calls for Unattended Mode
```python
# In orchestrator.py -- phase_4_apply
def phase_4_apply(self) -> None:
    if self.scheduled:
        print("  Scheduled mode: skipping apply phase (requires human approval)")
        return
    # ... existing interactive apply logic ...

# In platforms/indeed.py -- login
def login(self, timeout: int = 30000) -> bool:
    if self.is_logged_in():
        return False
    # In unattended mode, cannot perform interactive login
    if self._unattended:
        raise RuntimeError(
            "Indeed session expired. Run manually to re-authenticate."
        )
    # ... existing interactive login ...

# In platforms/mixins.py -- wait_for_human
def wait_for_human(self, message: str) -> str:
    if getattr(self, '_unattended', False):
        raise RuntimeError(f"Human input required but running in unattended mode: {message}")
    # ... existing interactive prompt ...
```

### Run History Recording
```python
# In webapp/db.py
def record_run(
    started_at: str,
    finished_at: str,
    mode: str,
    platforms_searched: list[str],
    total_raw: int,
    total_scored: int,
    new_jobs: int,
    errors: list[str],
    status: str,
    duration_seconds: float,
) -> None:
    import json
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO run_history
               (started_at, finished_at, mode, platforms_searched,
                total_raw, total_scored, new_jobs, errors, status, duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                started_at, finished_at, mode,
                json.dumps(platforms_searched),
                total_raw, total_scored, new_jobs,
                json.dumps(errors), status, duration_seconds,
            ),
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `launchctl load/unload` | `launchctl bootstrap/bootout gui/{uid}` | macOS 10.10 (2014) | Old commands still work but are deprecated. Use new API for forward compatibility. |
| cron on macOS | launchd `StartCalendarInterval` | macOS 10.4 (2005) | cron is deprecated, launchd is the only supported mechanism. launchd handles sleep/wake catch-up. |
| Manual plist XML editing | `plistlib.dump()` | Python 3.4+ | Stdlib produces correct XML. No need for manual editing or string templates. |

**Deprecated/outdated:**
- `launchctl load ~/Library/LaunchAgents/foo.plist`: Replaced by `launchctl bootstrap gui/{uid} /path/to/plist`. The old form still works but may be removed in future macOS versions.
- cron on macOS: Still technically functional but unsupported by Apple. Does not integrate with macOS power management (sleep/wake).
- `plistlib.readPlist()`/`writePlist()`: Removed in Python 3.12. Use `plistlib.load()`/`plistlib.dump()`.

## Open Questions

1. **Browser platform behavior in scheduled headless mode**
   - What we know: Playwright headless works in CI environments and from terminal. The existing `stealth.py` uses `channel="chrome"` (system Chrome) with `headless` parameter.
   - What's unclear: Whether system Chrome launched from a launchd agent context on macOS Tahoe (26.x) has any sandboxing restrictions that differ from terminal launches. macOS has tightened security progressively.
   - Recommendation: Test with `launchctl kickstart gui/{uid}/com.jobflow.pipeline` before relying on scheduled runs. If Chrome fails, add `--no-sandbox` to browser args or restrict scheduled runs to API-only platforms (RemoteOK).

2. **How to propagate unattended flag to platform adapters**
   - What we know: The Orchestrator creates platform instances. The `input()` calls are in `platforms/indeed.py`, `platforms/mixins.py`, and `orchestrator.py`.
   - What's unclear: The cleanest way to pass `unattended=True` through to platform instances without changing the Protocol signatures.
   - Recommendation: Add an `_unattended` attribute on platform instances after construction (duck-typing). Or pass it through `init()` as an optional kwarg that platforms can ignore. The simplest approach is to set it as an attribute on the platform instance right after construction in the Orchestrator, before calling any methods.

3. **Notification on scheduled run failure**
   - What we know: Run history is logged to SQLite. The dashboard can display it.
   - What's unclear: Whether the user wants active notifications (email, desktop notification) when a scheduled run fails, or passive checking via dashboard.
   - Recommendation: Start with passive (dashboard only). macOS `osascript` can generate desktop notifications as a future enhancement. Keep the scope minimal for Phase 4.

## Sources

### Primary (HIGH confidence)
- [Apple launchd.plist(5) man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) - `StartCalendarInterval` keys, `ProcessType`, `EnvironmentVariables`, `StandardOutPath`/`StandardErrorPath`, `WorkingDirectory`
- [Python plistlib documentation](https://docs.python.org/3/library/plistlib.html) - `plistlib.dump()` API for generating plist XML
- [Python logging.handlers documentation](https://docs.python.org/3/library/logging.handlers.html) - `RotatingFileHandler` for log rotation
- [SQLite WAL documentation](https://sqlite.org/wal.html) - Concurrent read/write behavior with WAL mode
- Existing codebase: `config.py` (ScheduleConfig placeholder at line 111), `orchestrator.py` (input() at line 370), `platforms/indeed.py` (input() at line 74), `platforms/mixins.py` (input() at line 85), `webapp/db.py` (WAL mode at line 86-89)

### Secondary (MEDIUM confidence)
- [launchd.info tutorial](https://www.launchd.info/) - Verified against man page for plist structure
- [alexwlchan: macOS LaunchAgent examples](https://alexwlchan.net/til/2025/macos-launchagent-examples/) - Real-world examples verified against official docs
- [alvinalexander: launchd StartCalendarInterval examples](https://alvinalexander.com/mac-os-x/launchd-plist-examples-startinterval-startcalendarinterval/) - XML structure examples cross-verified with man page

### Tertiary (LOW confidence)
- [Playwright GitHub Issue #5469](https://github.com/microsoft/playwright/issues/5469) - Reports of macOS cron/launchd issues with Playwright (2021, may be resolved in current versions)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, no external dependencies. plistlib, logging, sqlite3 are stable, well-documented APIs.
- Architecture: HIGH - launchd is the definitive macOS scheduling mechanism. The pattern of plist generation + launchctl management is well-established. The `--scheduled` flag pattern is straightforward.
- Pitfalls: HIGH - All pitfall items are verified from official docs (variable expansion, PATH, working directory). The `input()` blocking issue is verified from reading the actual codebase.
- Playwright in launchd: MEDIUM - Works in CI/headless contexts, but macOS-specific launchd behavior under Tahoe security model is less documented. Flagged as open question.

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (stable domain -- launchd API has not changed significantly in years)
