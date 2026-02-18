---
phase: 006-improve-resume-ai-prompts-and-fix-pdf-ou
plan: 01
subsystem: resume-ai
tags: [claude-cli, pydantic, weasyprint, pdf, prompt-engineering, css]

requires:
  - phase: 005-fix-resume-pdf-header-name
    provides: "Resume PDF rendering and anti-fabrication validation"
provides:
  - "Enhanced SYSTEM_PROMPT with keyword extraction, role-specific summary, and bullet optimization"
  - "keyword_alignment field on TailoredResume for JD keyword tracking"
  - "Professional PDF template with proper pagination, typography, and clickable links"
affects: [resume-ai, webapp-templates]

tech-stack:
  added: []
  patterns: ["Keyword extraction as first step in resume tailoring", "page-break-inside/break-inside avoid for WeasyPrint pagination"]

key-files:
  created: []
  modified:
    - resume_ai/models.py
    - resume_ai/tailor.py
    - webapp/templates/resume/resume_template.html
    - tests/resume_ai/test_models.py
    - tests/resume_ai/test_tailor.py

key-decisions:
  - "Renamed 'WHAT YOU MAY DO' to 'WHAT YOU MAY ALSO DO' to integrate with new instruction blocks"
  - "Used default_factory=list for keyword_alignment for backward compatibility"
  - "Dark navy (#1a365d) accent color for section headers and skill categories in PDF"

patterns-established:
  - "Structured prompt sections: KEYWORD EXTRACTION -> PROFESSIONAL SUMMARY -> BULLET POINT OPTIMIZATION"
  - "page-break-inside: avoid on all major resume sections for WeasyPrint"

requirements-completed: [PROMPT-IMPROVE, PDF-FIX]

duration: 3min
completed: 2026-02-18
---

# Quick Task 006: Improve Resume AI Prompts and Fix PDF Output Summary

**Enhanced SYSTEM_PROMPT with keyword extraction, role-specific summary, and bullet optimization instructions plus professional PDF template with WeasyPrint pagination and clickable links**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-18T00:04:51Z
- **Completed:** 2026-02-18T00:08:11Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- SYSTEM_PROMPT now has explicit KEYWORD EXTRACTION (top 10-15 JD keywords), PROFESSIONAL SUMMARY (role-specific, company-referenced), and BULLET POINT OPTIMIZATION (JD terminology bridging) instruction blocks
- All 4 ABSOLUTE RULES (anti-fabrication) preserved exactly as-is
- New `keyword_alignment` field on TailoredResume tracks which JD keywords were addressed (defaults to empty list for backward compatibility)
- PDF template improved with page-break-inside avoid on all 4 section types, dark navy accent headers, clickable underlined links, justified summary text, and tighter margins for 2-page fit

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance AI prompts and add keyword_alignment model field** - `5278731` (feat)
2. **Task 2: Fix PDF template CSS for professional layout and proper pagination** - `bd51728` (feat)

## Files Created/Modified
- `resume_ai/models.py` - Added keyword_alignment field with default_factory=list
- `resume_ai/tailor.py` - Rewrote SYSTEM_PROMPT with keyword extraction, summary, and bullet optimization blocks; enhanced user_message
- `webapp/templates/resume/resume_template.html` - Professional CSS with pagination, typography, and link fixes
- `tests/resume_ai/test_models.py` - Added keyword_alignment default and explicit value tests; updated expected keys
- `tests/resume_ai/test_tailor.py` - Added SYSTEM_PROMPT content assertions for new instruction blocks

## Decisions Made
- Renamed "WHAT YOU MAY DO" to "WHAT YOU MAY ALSO DO" to clearly separate the new structured instruction blocks from the existing general permissions
- Used `default_factory=list` for `keyword_alignment` so all existing code that constructs TailoredResume without this field continues working
- Chose dark navy (#1a365d) for section header accent color to be professional and print-friendly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification Results

- All 81 resume_ai tests pass (27 model/tailor + 4 renderer + 15 extractor/diff + 35 validator/tracker)
- Ruff lint clean, Ruff format clean
- "MUST NOT" appears 4 times in SYSTEM_PROMPT (all anti-fabrication rules preserved)
- `keyword_alignment` appears in models.py and tailor.py
- `page-break-inside: avoid` appears 4 times in template (experience, skills, projects, education)

---
*Quick Task: 006-improve-resume-ai-prompts-and-fix-pdf-ou*
*Completed: 2026-02-18*
