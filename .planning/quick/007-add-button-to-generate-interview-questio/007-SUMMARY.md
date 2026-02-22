---
phase: quick
plan: 007
subsystem: ai, webapp
tags: [claude-cli, interview-prep, pydantic, htmx, structured-output]

# Dependency graph
requires:
  - phase: 16-claude-cli-integration
    provides: "claude_cli async subprocess wrapper with typed Pydantic output"
  - phase: quick-004
    provides: "Redesigned job detail page layout with section cards"
provides:
  - "Interview question generation module (core/interview_prep.py)"
  - "POST /jobs/{dedup_key}/interview-questions endpoint"
  - "Interview Prep section with Generate Questions button on job detail"
affects: [webapp, core]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Claude CLI structured output for interview prep (same as ai_scorer.py)"

key-files:
  created:
    - core/interview_prep.py
    - webapp/templates/partials/interview_questions_result.html
  modified:
    - webapp/app.py
    - webapp/templates/job_detail.html

key-decisions:
  - "Used simple request/response pattern (not SSE) since generation takes ~10-15s, same as AI rescore"
  - "Placed Interview Prep section between AI Resume Tools and Generated Documents sections"

patterns-established:
  - "Interview prep follows same Claude CLI structured output pattern as ai_scorer.py and resume_ai/tailor.py"

requirements-completed: [QUICK-007]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Quick Task 007: Add Interview Prep Button Summary

**Interview question generation via Claude CLI with Pydantic structured output, htmx endpoint, and button on job detail page**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T23:28:02Z
- **Completed:** 2026-02-22T23:31:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created `core/interview_prep.py` with `InterviewQuestions` Pydantic model and `generate_interview_questions()` async function
- Added POST `/jobs/{dedup_key}/interview-questions` endpoint with description length guard, activity logging, and error handling
- Created `interview_questions_result.html` partial with structured question layout (technical, behavioral, company-specific, key topics)
- Added "Interview Prep" section with "Generate Questions" button to job detail page with htmx integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create interview question generation module** - `e62071e` (feat)
2. **Task 2: Add endpoint, partial template, and button to job detail page** - `e9ec08f` (feat)

## Files Created/Modified
- `core/interview_prep.py` - InterviewQuestions Pydantic model + generate_interview_questions() async function using Claude CLI
- `webapp/app.py` - POST /jobs/{dedup_key}/interview-questions endpoint
- `webapp/templates/partials/interview_questions_result.html` - htmx partial rendering structured interview questions
- `webapp/templates/job_detail.html` - Interview Prep section with Generate Questions button

## Decisions Made
- Used simple request/response (not SSE) since generation time (~10-15s) matches AI rescore behavior
- Placed Interview Prep section between AI Resume Tools and Generated Documents in the full-width area

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Uses existing Claude CLI authentication.

## Next Phase Readiness
- Interview prep feature is fully wired and ready to use
- Could be extended in future to persist generated questions to database

## Self-Check: PASSED

All files exist, all commits verified.

---
*Plan: quick-007*
*Completed: 2026-02-22*
