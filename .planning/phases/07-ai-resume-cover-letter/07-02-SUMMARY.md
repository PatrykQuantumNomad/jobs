---
phase: 07-ai-resume-cover-letter
plan: 02
subsystem: ai
tags: [anthropic, structured-outputs, resume-tailoring, cover-letter, anti-fabrication, pydantic]

# Dependency graph
requires:
  - phase: 07-01
    provides: "TailoredResume, CoverLetter, SkillSection, WorkExperience Pydantic models"
provides:
  - "tailor_resume() -- Anthropic structured output resume tailoring with anti-fabrication guardrails"
  - "generate_cover_letter() -- Anthropic structured output cover letter generation"
  - "validate_no_fabrication() -- Layer 3 post-generation entity comparison validator"
  - "format_resume_as_text() -- TailoredResume to ATS plain text converter"
  - "format_cover_letter_as_text() -- CoverLetter to displayable text converter"
affects: [07-03, 07-04]

# Tech tracking
tech-stack:
  added: [anthropic SDK (messages.parse with output_format)]
  patterns: [structured output via Pydantic schema, anti-fabrication 3-layer architecture, temperature=0 for factual accuracy]

key-files:
  created:
    - resume_ai/tailor.py
    - resume_ai/cover_letter.py
    - resume_ai/validator.py
  modified: []

key-decisions:
  - "Temperature=0 for resume tailoring (max factual accuracy), 0.3 for cover letter (natural writing)"
  - "Stop-word filtering in entity extraction to prevent false positives from sentence-start capitalization"
  - "Validator works on plain text (not Pydantic models) for flexibility -- can validate any text pair"
  - "Conservative company detection (at/for patterns + multi-word capitalized) with stop-word filter to minimize false positives"
  - "Known tech keywords set (~100 terms) for skill extraction covers project's domain comprehensively"

patterns-established:
  - "Anthropic parse pattern: client.messages.parse(output_format=PydanticModel) for typed LLM output"
  - "Anti-fabrication architecture: Layer 1 (system prompt) + Layer 2 (temperature=0) + Layer 3 (entity validation)"
  - "Error handling pattern: catch AuthenticationError for API key issues, APIError for general failures"

# Metrics
duration: 6min
completed: 2026-02-07
---

# Phase 7 Plan 02: LLM Tailoring Engine Summary

**Resume tailoring and cover letter generation via Anthropic structured outputs with 3-layer anti-fabrication guardrails (prompt constraints + temperature=0 + entity validation)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-07T22:36:41Z
- **Completed:** 2026-02-07T22:43:04Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- Resume tailoring function that reorders skills/achievements to match job descriptions while strictly forbidding fabrication via system prompt + temperature=0
- Cover letter generation with temperature=0.3 for natural tone, using Anthropic structured outputs for schema-compliant output
- Post-generation anti-fabrication validator that programmatically compares entities (companies, skills, metrics) between original and tailored text
- Format helpers for both resume (ATS section headers) and cover letter (paragraph-formatted text with candidate name)

## Task Commits

Each task was committed atomically:

1. **Task 1: Resume tailoring with anti-fabrication guardrails** - `52eed00` (feat)
2. **Task 2: Cover letter generation and post-generation anti-fabrication validator** - `c0af28a` (feat)

## Files Created/Modified

- `resume_ai/tailor.py` - Resume tailoring via Anthropic messages.parse() with TailoredResume output_format, anti-fabrication system prompt, temperature=0
- `resume_ai/cover_letter.py` - Cover letter generation via Anthropic messages.parse() with CoverLetter output_format, temperature=0.3
- `resume_ai/validator.py` - Post-generation entity extraction and comparison (companies, skills, metrics) with ValidationResult model

## Decisions Made

- **Temperature=0 for resume, 0.3 for cover letter:** Resume tailoring needs maximum factual accuracy (zero creativity in facts), while cover letters benefit from slightly more natural language variation. This matches the research recommendation.
- **Validator works on plain text strings:** Rather than coupling to Pydantic model types, the validator accepts any text pair. This means it can validate both tailored resumes and cover letters against the original resume, and is easily testable.
- **Stop-word filtering for company detection:** The entity extraction initially produced false positives for sentence-start capitalized words like "Using Python" being detected as company names. Added a comprehensive stop-word set (~140 common English words) to filter these out.
- **Conservative company detection:** Prefer fewer false positives over catching every fabricated company. Skills and metrics detection is more aggressive since those are the most dangerous types of fabrication in resume context.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed false positives in entity extraction company detection**
- **Found during:** Task 2 (validator implementation)
- **Issue:** The `at_for_pattern` with `re.IGNORECASE` flag captured lowercase words after "at/for" as company names. Additionally, capitalized sentence-start words like "Using" were matched as company name parts.
- **Fix:** Removed IGNORECASE from capture group (using `(?i:at|for)` for trigger words only), added stop-word filtering for both the multi-word capitalized pattern and the at/for pattern.
- **Files modified:** `resume_ai/validator.py`
- **Verification:** "Using Python, I worked at Google" no longer produces false positives. All 3 test scenarios pass.
- **Committed in:** `c0af28a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness -- without the fix, the validator would flag legitimate resume reordering as fabrication.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required. The `ANTHROPIC_API_KEY` environment variable is needed at runtime but was already part of the project setup.

## Next Phase Readiness

- Core LLM functions ready for integration with dashboard endpoints (07-03)
- Anti-fabrication validator ready for use in the tailor/generate pipeline
- Format helpers ready for diff view and PDF rendering in dashboard
- Both functions accept configurable model parameter for easy model switching

## Self-Check: PASSED

- FOUND: resume_ai/tailor.py
- FOUND: resume_ai/cover_letter.py
- FOUND: resume_ai/validator.py
- FOUND: commit 52eed00
- FOUND: commit c0af28a

---
*Phase: 07-ai-resume-cover-letter*
*Completed: 2026-02-07*
