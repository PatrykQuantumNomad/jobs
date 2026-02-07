---
phase: 07-ai-resume-cover-letter
plan: 01
subsystem: ai, database
tags: [anthropic, pymupdf4llm, weasyprint, pydantic, sqlite, resume, cover-letter]

# Dependency graph
requires:
  - phase: 03-discovery-engine
    provides: "SQLite database layer (webapp/db.py) and get_conn() pattern"
provides:
  - "resume_ai package with Pydantic structured output models (TailoredResume, CoverLetter)"
  - "PDF text extraction via pymupdf4llm (extract_resume_text)"
  - "resume_versions SQLite table for version tracking"
  - "Tracker CRUD functions (save_resume_version, get_versions_for_job, get_all_versions)"
  - "anthropic, pymupdf4llm, weasyprint dependencies installed"
affects: [07-02-PLAN, 07-03-PLAN, 07-04-PLAN]

# Tech tracking
tech-stack:
  added: [anthropic 0.79.0, pymupdf4llm 0.2.9, weasyprint 68.1]
  patterns: [structured-output-models, pdf-to-markdown-extraction, version-tracking-crud]

key-files:
  created:
    - resume_ai/__init__.py
    - resume_ai/models.py
    - resume_ai/extractor.py
    - resume_ai/tracker.py
  modified:
    - pyproject.toml
    - webapp/db.py

key-decisions:
  - "Field(description=...) on every Pydantic model field for LLM structured output guidance"
  - "WorkExperience.achievements reorder-only constraint documented in Field description"
  - "resume_versions table uses job_dedup_key FK to jobs table for referential integrity"
  - "get_all_versions() LEFT JOINs jobs table to enrich with title/company metadata"

patterns-established:
  - "Pydantic models as LLM output schemas with Field descriptions for guidance"
  - "pymupdf4llm.to_markdown() for PDF-to-Markdown extraction"
  - "Resume version tracking via SQLite with CRUD functions in resume_ai/tracker.py"

# Metrics
duration: 4min
completed: 2026-02-07
---

# Phase 7 Plan 01: Foundation Summary

**Pydantic structured output models (TailoredResume, CoverLetter) with pymupdf4llm PDF extraction and SQLite resume version tracking**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-07T22:29:26Z
- **Completed:** 2026-02-07T22:33:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Four Pydantic v2 models (SkillSection, WorkExperience, TailoredResume, CoverLetter) with LLM-guiding Field descriptions on every field
- PDF text extraction producing structured Markdown from the actual ATS resume (7016 chars extracted successfully)
- SQLite migration v6 adding resume_versions table with foreign key to jobs and index on job_dedup_key
- Tracker CRUD functions (save, get_for_job, get_all) with LEFT JOIN job enrichment, verified end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependencies, package structure, and Pydantic models** - `ada9b63` (feat)
2. **Task 2: Resume version tracker with SQLite migration** - `02f8373` (feat)

## Files Created/Modified
- `resume_ai/__init__.py` - Package marker
- `resume_ai/models.py` - TailoredResume, CoverLetter, SkillSection, WorkExperience Pydantic models with Field descriptions
- `resume_ai/extractor.py` - extract_resume_text() using pymupdf4llm.to_markdown()
- `resume_ai/tracker.py` - save_resume_version(), get_versions_for_job(), get_all_versions() CRUD
- `pyproject.toml` - Added anthropic, pymupdf4llm, weasyprint dependencies and resume_ai package
- `webapp/db.py` - Schema v6 migration with resume_versions table and index

## Decisions Made
- Used `Field(description=...)` on every Pydantic model field to guide LLM structured output generation
- WorkExperience achievements field explicitly documents reorder-only constraint (no fabrication)
- resume_versions table uses FOREIGN KEY to jobs(dedup_key) for referential integrity
- get_all_versions() uses LEFT JOIN (not INNER JOIN) so orphaned versions are still returned

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration.** The ANTHROPIC_API_KEY environment variable must be set in `.env` before Plans 02-04 can call the LLM. Source: https://console.anthropic.com/settings/keys

## Next Phase Readiness
- resume_ai package fully importable with models, extractor, and tracker
- All three new dependencies (anthropic, pymupdf4llm, weasyprint) installed and verified
- SQLite schema at v6 with resume_versions table ready for Plan 02 (LLM tailoring engine)
- PDF extraction confirmed working against actual ATS resume (7016 chars Markdown output)
- No blockers for Plan 02

## Self-Check: PASSED

- [x] resume_ai/__init__.py exists
- [x] resume_ai/models.py exists
- [x] resume_ai/extractor.py exists
- [x] resume_ai/tracker.py exists
- [x] pyproject.toml modified
- [x] webapp/db.py modified
- [x] Commit ada9b63 exists (Task 1)
- [x] Commit 02f8373 exists (Task 2)

---
*Phase: 07-ai-resume-cover-letter*
*Completed: 2026-02-07*
