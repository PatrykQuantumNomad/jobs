---
phase: quick
plan: 001
type: execute
wave: 1
depends_on: []
files_modified:
  - config.py
  - webapp/app.py
  - design/architecture.md
autonomous: true

must_haves:
  truths:
    - "Legacy Config class shim no longer exists in config.py"
    - "webapp/app.py does not mount an empty /static directory"
    - "design/architecture.md accurately reflects current codebase health"
  artifacts:
    - path: "config.py"
      provides: "Clean config module with no legacy shim"
      contains: "get_settings"
    - path: "webapp/app.py"
      provides: "Dashboard app without dead static mount"
    - path: "design/architecture.md"
      provides: "Updated health dashboard and recommendations"
  key_links: []
---

<objective>
Clean up three technical debt items flagged in design/architecture.md: remove the unused legacy Config class shim from config.py, remove the dead static files mount from webapp/app.py, and update the architecture doc to reflect the resolved state.

Purpose: Eliminate dead code and keep architecture documentation accurate.
Output: Three files cleaned up, zero functional change.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@config.py
@webapp/app.py
@design/architecture.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove legacy Config class shim and dead static mount</name>
  <files>config.py, webapp/app.py</files>
  <action>
  In config.py:
  - Delete lines 340-411 (the backward compatibility shim comment block and the entire `Config` class).
  - Keep everything above line 340 intact. There is nothing after line 411, so just truncate.
  - Verified: zero consumers remain (`grep -rn "from config import Config"` returns nothing).

  In webapp/app.py:
  - Remove line 37: `app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")`
  - Remove the `StaticFiles` import from line 21 (it is only used for that mount). The import line is:
    `from fastapi.staticfiles import StaticFiles`
  - Verified: no templates reference `/static/` paths, the directory is empty.
  </action>
  <verify>
  Run: `python -c "from config import get_settings; print('config OK')"` -- must succeed.
  Run: `python -c "from config import Config"` -- must raise ImportError or AttributeError.
  Run: `python -c "from webapp.app import app; print('app OK')"` -- must succeed.
  Run: `grep -n "StaticFiles\|static" webapp/app.py` -- should return zero hits for StaticFiles, and no /static mount line.
  Run: `grep -n "class Config" config.py` -- should return zero hits.
  </verify>
  <done>
  config.py has no Config class. webapp/app.py has no StaticFiles import or /static mount. Both modules import cleanly without errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update architecture.md health dashboard and recommendations</name>
  <files>design/architecture.md</files>
  <action>
  In the Phase 12 "Codebase Health Dashboard" table (line 195):
  - Change the **Technical Debt** row from:
    `| **Technical Debt** | 🟡 | Legacy Config shim class (config.py:346) still exists. Only 1 TODO/FIXME. webapp/static/ directory missing (mounted but empty). |`
    to:
    `| **Technical Debt** | ✅ | Only 1 TODO/FIXME across the codebase. No legacy shims. No dead mounts. |`

  In the Recommendations section (line 226, recommendation #4):
  - Replace recommendation #4 entirely. Change from:
    `4. **Remove the legacy Config class shim:** config.py:346-411 maintains a backward-compatibility class that delegates to AppSettings. The docstring says "will be removed after Phase 1, Plan 02-03" -- this migration appears complete since all modules already import get_settings() directly.`
    to:
    `4. ~~Remove the legacy Config class shim~~ -- **DONE.** Removed in technical debt cleanup (2026-02-08). All modules use `get_settings()` directly.`
  </action>
  <verify>
  Run: `grep "Legacy Config shim" design/architecture.md` -- should return zero hits.
  Run: `grep "Technical Debt.*✅" design/architecture.md` -- should match the updated row.
  Run: `grep "DONE.*Config" design/architecture.md` -- should match the resolved recommendation.
  </verify>
  <done>
  architecture.md Technical Debt status is green (checkmark). Recommendation #4 is marked as resolved. Documentation accurately reflects the current codebase state.
  </done>
</task>

</tasks>

<verification>
- `python -c "from config import get_settings; print('OK')"` succeeds
- `python -c "from webapp.app import app; print('OK')"` succeeds
- No references to `Config` class remain in any .py file
- No `StaticFiles` import in webapp/app.py
- architecture.md Technical Debt row shows green checkmark
- architecture.md recommendation #4 shows DONE
</verification>

<success_criteria>
Three dead code / documentation items resolved. Zero functional regression -- config module and webapp still import and run correctly. Architecture documentation accurately reflects the cleaned-up state.
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-technical-debt/001-SUMMARY.md`
</output>
