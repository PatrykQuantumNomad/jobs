"""Manage the macOS launchd scheduled job for the pipeline.

Provides ``install``, ``uninstall``, and ``status`` subcommands to create and
manage a launchd user agent that runs the pipeline on a configurable schedule.

Usage::

    python scheduler.py install    # Generate plist and load the agent
    python scheduler.py uninstall  # Unload the agent and remove the plist
    python scheduler.py status     # Check whether the agent is loaded
"""

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from config import get_settings

# -- Constants -----------------------------------------------------------------

LABEL = "com.jobflow.pipeline"
PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

PROJECT_ROOT = Path(__file__).parent.resolve()


# -- Plist generation ----------------------------------------------------------


def generate_plist(settings) -> dict:
    """Build the launchd plist dictionary from *settings*.schedule.

    All paths are absolute -- no ``~``, ``$HOME``, or shell variables.
    """
    sched = settings.schedule
    python_path = str(Path(sys.executable).resolve())
    orchestrator_path = str(PROJECT_ROOT / "orchestrator.py")
    log_dir = PROJECT_ROOT / "job_pipeline" / "logs"

    # StartCalendarInterval: single dict for daily, list of dicts for weekdays
    if sched.weekdays is not None:
        calendar_interval = [
            {"Hour": sched.hour, "Minute": sched.minute, "Weekday": day} for day in sched.weekdays
        ]
    else:
        calendar_interval = {"Hour": sched.hour, "Minute": sched.minute}

    return {
        "Label": LABEL,
        "ProgramArguments": [python_path, orchestrator_path, "--scheduled"],
        "WorkingDirectory": str(PROJECT_ROOT),
        "StartCalendarInterval": calendar_interval,
        "StandardOutPath": str(log_dir / "pipeline.log"),
        "StandardErrorPath": str(log_dir / "pipeline.err"),
        "EnvironmentVariables": {
            "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin",
        },
        "ProcessType": "Background",
    }


def write_plist(plist_data: dict, dest: Path) -> None:
    """Write *plist_data* to *dest* using ``plistlib``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        plistlib.dump(plist_data, f)


# -- Commands ------------------------------------------------------------------


def install_schedule() -> None:
    """Generate the launchd plist and load the agent."""
    settings = get_settings()

    if not settings.schedule.enabled:
        print("ERROR: schedule.enabled is false in config.yaml.")
        print("  Set 'enabled: true' in the schedule section first.")
        sys.exit(1)

    # Ensure log directory exists
    log_dir = PROJECT_ROOT / "job_pipeline" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    plist_data = generate_plist(settings)
    write_plist(plist_data, PLIST_DEST)
    print(f"  Plist written: {PLIST_DEST}")

    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_DEST)],
        check=True,
    )

    sched = settings.schedule
    days_desc = "daily"
    if sched.weekdays:
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        days_desc = ", ".join(day_names[d] for d in sched.weekdays)

    print(f"  Installed: {LABEL}")
    print(f"  Schedule:  {sched.hour:02d}:{sched.minute:02d} ({days_desc})")
    print(f"  Logs:      {log_dir}/")


def uninstall_schedule() -> None:
    """Unload the launchd agent and remove the plist file."""
    uid = os.getuid()

    # bootout may fail if not loaded -- that is fine
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}/{LABEL}"],
        check=False,
        capture_output=True,
    )

    PLIST_DEST.unlink(missing_ok=True)
    print(f"  Uninstalled: {LABEL}")
    print(f"  Plist removed: {PLIST_DEST}")


def show_status() -> None:
    """Report whether the launchd agent is loaded."""
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Parse exit status from launchctl list output
        lines = result.stdout.strip().split("\n")
        print(f"  {LABEL}: LOADED")
        for line in lines:
            print(f"    {line}")
    else:
        print(f"  {LABEL}: NOT LOADED")


# -- CLI entry point -----------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage scheduled pipeline runs via macOS launchd",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("install", help="Generate plist and load the launchd agent")
    sub.add_parser("uninstall", help="Unload the agent and remove the plist")
    sub.add_parser("status", help="Check whether the agent is loaded")

    args = parser.parse_args()

    if args.command == "install":
        install_schedule()
    elif args.command == "uninstall":
        uninstall_schedule()
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
