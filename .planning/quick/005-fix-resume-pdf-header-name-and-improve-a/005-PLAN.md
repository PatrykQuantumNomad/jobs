---
phase: quick-005
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .env
  - webapp/app.py
  - resume_ai/validator.py
  - tests/resume_ai/test_validator.py
autonomous: true
requirements: [FIX-PDF-NAME, FIX-VALIDATOR-FP]
must_haves:
  truths:
    - "Resume PDF header shows the real candidate name, not 'Candidate'"
    - "Cover letter PDF header shows the real candidate name, not 'Candidate'"
    - "Name fallback extracts from resume filename when env vars are unset"
    - "Resume section headers (PROFESSIONAL SUMMARY, WORK EXPERIENCE, etc.) are not flagged as fabricated companies"
    - "Skills mentioned in the job description are not flagged as fabricated when they appear in the tailored resume"
    - "Acronym expansions (e.g., GKE -> Google Kubernetes Engine) do not trigger false positives"
  artifacts:
    - path: ".env"
      provides: "CANDIDATE_FIRST_NAME and CANDIDATE_LAST_NAME env vars"
      contains: "CANDIDATE_FIRST_NAME"
    - path: "webapp/app.py"
      provides: "Smart name fallback from resume filename"
      contains: "_name_from_resume_path"
    - path: "resume_ai/validator.py"
      provides: "Improved entity extraction with section header exclusion and JD-aware allowlist"
      contains: "_SECTION_HEADERS"
    - path: "tests/resume_ai/test_validator.py"
      provides: "Tests for false positive prevention"
  key_links:
    - from: "webapp/app.py"
      to: "core/config.py"
      via: "build_candidate_profile() and candidate_resume_path"
      pattern: "settings\\.build_candidate_profile|candidate_resume_path"
    - from: "resume_ai/validator.py"
      to: "webapp/app.py"
      via: "validate_no_fabrication with job_description parameter"
      pattern: "validate_no_fabrication.*job_description"
---

<objective>
Fix two issues with the resume/cover letter generation pipeline:

1. PDF headers show "Candidate" instead of the real name because CANDIDATE_FIRST_NAME and CANDIDATE_LAST_NAME env vars are missing from .env. Add them, and add a smart fallback that extracts the name from the resume filename path when env vars are unset.

2. Anti-fabrication validator produces false positives from resume section headers (e.g., "PROFESSIONAL SUMMARY" matched as a company), ATS-standard terms, and skills that appear in the job description (which are expected in tailored output). Add section header exclusions, acronym-expansion awareness, and a job-description-aware allowlist.

Purpose: Make resume generation produce correct candidate names and stop blocking valid tailored resumes with false fabrication warnings.
Output: Updated .env, webapp/app.py, resume_ai/validator.py, tests/resume_ai/test_validator.py
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@webapp/app.py
@resume_ai/validator.py
@core/config.py
@tests/resume_ai/test_validator.py
@.env
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix PDF candidate name — add env vars and smart fallback</name>
  <files>.env, webapp/app.py</files>
  <action>
  1. Add to `.env` (after the existing CANDIDATE_YOUTUBE line):
     ```
     CANDIDATE_FIRST_NAME=Patryk
     CANDIDATE_LAST_NAME=Golabek
     ```

  2. In `webapp/app.py`, add a helper function `_name_from_resume_path(path: str) -> str` near the top of the file (after imports, before route definitions). This function:
     - Takes a resume path string like "resumes/Patryk_Golabek_Resume.pdf"
     - Extracts the filename stem: "Patryk_Golabek_Resume"
     - Strips common suffixes: "Resume", "CV", "Cover_Letter", "CoverLetter" (case-insensitive)
     - Replaces underscores with spaces and strips
     - Returns the cleaned name, or empty string if extraction fails
     - Example: "resumes/Patryk_Golabek_Resume.pdf" -> "Patryk Golabek"

  3. Update the name resolution on line ~294 (resume tailor) to use the fallback chain:
     ```python
     candidate_name = (
         f"{profile.first_name} {profile.last_name}".strip()
         or _name_from_resume_path(settings.candidate_resume_path)
         or "Candidate"
     )
     ```

  4. Apply the same fix on line ~485 (cover letter generation) — same three-level fallback chain.

  Do NOT change core/config.py or the CandidateProfile model — this is purely .env + app.py changes.
  </action>
  <verify>
  - `uv run ruff check webapp/app.py` passes with no errors
  - `uv run ruff format --check webapp/app.py` passes
  - `grep CANDIDATE_FIRST_NAME .env` shows "Patryk"
  - `uv run python -c "from webapp.app import _name_from_resume_path; print(_name_from_resume_path('resumes/Patryk_Golabek_Resume.pdf'))"` outputs "Patryk Golabek"
  </verify>
  <done>
  - .env contains CANDIDATE_FIRST_NAME=Patryk and CANDIDATE_LAST_NAME=Golabek
  - Both resume and cover letter PDF generation use three-level name fallback: env vars -> resume filename -> "Candidate"
  - _name_from_resume_path correctly extracts "Patryk Golabek" from "resumes/Patryk_Golabek_Resume.pdf"
  </done>
</task>

<task type="auto">
  <name>Task 2: Reduce anti-fabrication validator false positives</name>
  <files>resume_ai/validator.py, tests/resume_ai/test_validator.py</files>
  <action>
  In `resume_ai/validator.py`:

  1. Add a `_SECTION_HEADERS` set near the top (after `_TECH_KEYWORDS`):
     ```python
     _SECTION_HEADERS: set[str] = {
         "professional summary", "work experience", "technical skills",
         "professional experience", "education", "certifications",
         "projects", "skills", "summary", "objective", "achievements",
         "core competencies", "key achievements", "career highlights",
         "additional information", "volunteer experience", "publications",
         "awards", "honors", "references", "contact information",
     }
     ```

  2. Add an `_ACRONYM_EXPANSIONS` dict mapping common acronyms to their full forms:
     ```python
     _ACRONYM_EXPANSIONS: dict[str, list[str]] = {
         "gke": ["google kubernetes engine"],
         "eks": ["elastic kubernetes service", "amazon eks"],
         "aks": ["azure kubernetes service"],
         "gcp": ["google cloud platform", "google cloud"],
         "aws": ["amazon web services"],
         "ci/cd": ["continuous integration", "continuous deployment", "continuous delivery"],
         "sso": ["single sign-on", "single sign on"],
         "etl": ["extract transform load"],
         "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
         "llm": ["large language model"],
         "ml": ["machine learning"],
         "ai": ["artificial intelligence"],
         "k8s": ["kubernetes"],
         "sqs": ["simple queue service", "amazon sqs"],
         "ec2": ["elastic compute cloud", "amazon ec2"],
         "s3": ["simple storage service", "amazon s3"],
     }
     ```

  3. In `_extract_entities()`, after the company extraction section, filter out section headers:
     ```python
     # Filter out resume section headers from companies
     companies = {c for c in companies if c not in _SECTION_HEADERS}
     ```

  4. Update `validate_no_fabrication()` signature to accept an optional `job_description: str = ""` parameter. Before computing diffs:
     - Extract entities from job_description text using `_extract_entities(job_description)`
     - Compute `jd_skills = jd_entities["skills"]`
     - When computing new_skills, subtract both original AND JD skills:
       `new_skills = sorted(tailored_entities["skills"] - original_entities["skills"] - jd_skills)`
     - Also filter new_skills: for each skill in new_skills, check if it's an acronym expansion of something in original_entities["skills"] (using _ACRONYM_EXPANSIONS), and remove it if so. Vice versa: if original has a full form and tailored uses the acronym, don't flag it.

  5. In `_extract_entities()`, for the ALL_CAPS pattern, add a filter to skip 2-letter words that are common English words (e.g., "IT", "OR", "AT", "TO", "IN", "ON", "OF", "DO", "UP", "MY", "NO", "SO", "AN", "AM", "BE") to reduce skill noise.

  In `webapp/app.py`:

  6. Update the call to `validate_no_fabrication` on line ~286 to pass the job description:
     ```python
     validation = validate_no_fabrication(resume_text, tailored_text, job_description=job["description"] or "")
     ```

  In `tests/resume_ai/test_validator.py`:

  7. Add these test cases to the existing test classes:

     In `TestExtractEntities`:
     - `test_section_headers_not_companies`: Text containing "PROFESSIONAL SUMMARY" and "WORK EXPERIENCE" should NOT have those in companies set.
     - `test_short_caps_words_not_skills`: Text with "IT department" or "DO this" should not have "it" or "do" in skills (2-letter common English words filtered).

     In `TestAntiFabrication`:
     - `test_jd_skills_not_flagged`: original has "Python, Kubernetes", tailored has "Python, Kubernetes, Terraform", but job_description also mentions "Terraform" -> is_valid=True, no new skills.
     - `test_section_headers_not_flagged_as_companies`: original has plain text, tailored has "PROFESSIONAL SUMMARY\nExperience with Python" -> no new companies from the header.
     - `test_acronym_expansion_not_flagged`: original has "GKE" in text, tailored has "Google Kubernetes Engine" -> should not flag "google kubernetes engine" as a new company. Implement by checking _ACRONYM_EXPANSIONS in company filtering too: if a new company matches an expansion of an acronym present in original skills, filter it out.
     - `test_jd_param_is_optional`: Calling `validate_no_fabrication(text, text)` without job_description still works (backward compatible).

  Ensure all new tests follow the existing pattern with `@pytest.mark.unit` on the class.
  </action>
  <verify>
  - `uv run ruff check resume_ai/validator.py` passes
  - `uv run ruff format --check resume_ai/validator.py` passes
  - `uv run pytest tests/resume_ai/test_validator.py -v` — all tests pass (existing + new)
  - `uv run pytest -m unit -x` — full unit test suite still passes
  </verify>
  <done>
  - Section headers like "PROFESSIONAL SUMMARY" are not flagged as fabricated companies
  - Skills from the job description are allowlisted and not flagged as fabricated
  - Acronym expansions (GKE -> Google Kubernetes Engine) do not trigger false positives
  - Short common-English ALL_CAPS words (IT, OR, etc.) are not extracted as skills
  - All existing tests still pass (backward compatible)
  - 4+ new tests covering the false positive prevention scenarios
  </done>
</task>

</tasks>

<verification>
- `uv run ruff check .` passes across all modified files
- `uv run pytest tests/resume_ai/test_validator.py -v` — all validator tests pass
- `uv run pytest -m unit -x` — full unit suite passes
- Manually verify: `grep CANDIDATE_FIRST_NAME .env` returns "Patryk"
</verification>

<success_criteria>
- PDF resume and cover letter generation uses the real candidate name "Patryk Golabek" from .env
- If env vars were removed, the fallback would extract "Patryk Golabek" from the resume filename path
- Anti-fabrication validator no longer flags section headers, JD-sourced skills, or acronym expansions as fabrications
- All existing and new tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/005-fix-resume-pdf-header-name-and-improve-a/005-SUMMARY.md`
</output>
