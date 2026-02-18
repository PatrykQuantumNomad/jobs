---
phase: 006-improve-resume-ai-prompts-and-fix-pdf-ou
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - resume_ai/models.py
  - resume_ai/tailor.py
  - webapp/templates/resume/resume_template.html
  - tests/resume_ai/test_models.py
  - tests/resume_ai/test_tailor.py
autonomous: true
requirements: [PROMPT-IMPROVE, PDF-FIX]

must_haves:
  truths:
    - "LLM is instructed to extract and weave JD keywords into bullet rephrasing"
    - "LLM is instructed to write role-specific summaries referencing company and role"
    - "TailoredResume model includes keyword_alignment field tracking JD keywords addressed"
    - "PDF sections do not break mid-element across pages"
    - "PDF links are clickable in generated output"
    - "PDF has professional typography and spacing for 2-page max layout"
    - "All existing tests still pass with the new keyword_alignment field"
  artifacts:
    - path: "resume_ai/tailor.py"
      provides: "Enhanced SYSTEM_PROMPT with keyword extraction and role-specific summary instructions"
      contains: "keyword_alignment"
    - path: "resume_ai/models.py"
      provides: "keyword_alignment field on TailoredResume"
      contains: "keyword_alignment"
    - path: "webapp/templates/resume/resume_template.html"
      provides: "Improved CSS for PDF rendering with page-break, spacing, and link fixes"
      contains: "page-break-inside"
  key_links:
    - from: "resume_ai/tailor.py"
      to: "resume_ai/models.py"
      via: "TailoredResume import with keyword_alignment field"
      pattern: "keyword_alignment"
    - from: "webapp/templates/resume/resume_template.html"
      to: "resume_ai/renderer.py"
      via: "Jinja2 template rendering"
      pattern: "resume_template.html"
---

<objective>
Improve resume AI tailoring quality and fix PDF layout issues.

Purpose: The current AI prompts produce generic professional summaries and weak keyword matching. The PDF template has spacing/overflow/page-break issues. Both problems reduce the quality of generated resumes.
Output: Enhanced SYSTEM_PROMPT with explicit keyword extraction and role-specific summary instructions, new keyword_alignment model field, and a polished PDF template with proper WeasyPrint pagination and typography.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@resume_ai/tailor.py
@resume_ai/models.py
@resume_ai/renderer.py
@resume_ai/validator.py
@webapp/templates/resume/resume_template.html
@tests/resume_ai/test_models.py
@tests/resume_ai/test_tailor.py
@tests/resume_ai/test_renderer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enhance AI prompts and add keyword_alignment model field</name>
  <files>resume_ai/models.py, resume_ai/tailor.py, tests/resume_ai/test_models.py, tests/resume_ai/test_tailor.py</files>
  <action>
**1. Add `keyword_alignment` field to `TailoredResume` in `resume_ai/models.py`:**

Add a new field after `tailoring_notes`:
```python
keyword_alignment: list[str] = Field(
    default_factory=list,
    description=(
        "List of specific keywords and phrases extracted from the job description "
        "that were naturally incorporated into the tailored resume content. "
        "Each entry should be the exact keyword/phrase from the JD."
    ),
)
```

Use `default_factory=list` so existing code that constructs TailoredResume without this field still works (backward compatible).

**2. Rewrite `SYSTEM_PROMPT` in `resume_ai/tailor.py`:**

Keep ALL existing ABSOLUTE RULES (anti-fabrication, lines 1-4) exactly as-is. Keep the FORMATTING section exactly as-is.

Replace the "WHAT YOU MAY DO" section with an enhanced version that adds three new instruction blocks:

```
KEYWORD EXTRACTION (do this first):
1. Read the job description carefully and identify the top 10-15 keywords and
   phrases that represent core requirements (technologies, methodologies,
   domain terms, soft skills like "cross-functional collaboration").
2. Note which keywords already appear in the original resume (these just need
   emphasis via reordering) and which do NOT appear but have equivalent
   experience (these need rephrasing to bridge the gap).
3. List the keywords you addressed in the keyword_alignment output field.

PROFESSIONAL SUMMARY — ROLE-SPECIFIC, NOT GENERIC:
- Write the summary specifically for this role at this company.
- Open with the candidate's most relevant title/identity that matches the JD
  (e.g., "Platform engineering leader" not just "experienced engineer").
- Reference the company by name and connect the candidate's specific
  strengths to what the role demands.
- Weave in 3-5 top JD keywords naturally — never keyword-stuff.
- Include one quantified achievement from the resume that is most relevant.
- BAD: "Experienced engineer with a passion for technology."
- GOOD: "Platform engineering leader with 10+ years building Kubernetes-native
  infrastructure at scale, bringing deep GKE and Terraform expertise to
  {company_name}'s cloud modernization mission."

BULLET POINT OPTIMIZATION:
- For each achievement bullet, ask: "Does this use the JD's language?"
- Where the candidate has equivalent experience, rephrase the bullet to use
  the JD's terminology while preserving the factual claim.
  Example: If JD says "observability" and resume says "monitoring" for the
  same concept, rephrase to "observability" (this is allowed rephrasing,
  NOT fabrication).
- Front-load bullets with action verbs that match the JD's tone.
- Prioritize bullets that demonstrate the JD's stated requirements.
```

Keep all existing "WHAT YOU MAY DO" items (reorder sections, reorder bullets, rephrase for clarity, adjust summary, reorder skills, expand acronyms) but integrate them under the new structure above. The existing items become part of the expanded instructions rather than being removed.

**3. Enhance the `user_message` in `tailor_resume()`:**

Update the user_message to explicitly request keyword alignment output:
```python
user_message = (
    f"## Original Resume\n\n{resume_text}\n\n"
    f"## Target Job Description\n\n{job_description}\n\n"
    f"## Target Role\n\n"
    f"- **Job Title:** {job_title}\n"
    f"- **Company:** {company_name}\n\n"
    f"## Instructions\n\n"
    f"Tailor this resume for the {job_title} role at {company_name}. "
    f"Follow the KEYWORD EXTRACTION, PROFESSIONAL SUMMARY, and BULLET POINT "
    f"OPTIMIZATION instructions from your system prompt. "
    f"Populate the keyword_alignment field with the JD keywords you addressed."
)
```

**4. Update tests:**

In `tests/resume_ai/test_models.py`:
- Update `TestTailoredResume.test_model_dump_keys` to include `"keyword_alignment"` in the expected keys set.
- Add a test `test_keyword_alignment_defaults_to_empty_list` that constructs a TailoredResume without keyword_alignment and asserts it defaults to `[]`.
- Add a test `test_keyword_alignment_accepts_list` that constructs with `keyword_alignment=["kubernetes", "terraform"]` and asserts the value.

In `tests/resume_ai/test_tailor.py`:
- The `_make_tailored_resume()` helper does NOT need updating (default_factory=list handles it).
- Add a test in `TestFormatResumeAsText` or `TestTailorResume` that verifies the SYSTEM_PROMPT contains the new keyword instruction text: `assert "KEYWORD EXTRACTION" in SYSTEM_PROMPT` and `assert "keyword_alignment" in SYSTEM_PROMPT`.
  </action>
  <verify>
Run `uv run pytest tests/resume_ai/test_models.py tests/resume_ai/test_tailor.py -v` and confirm all tests pass including new ones. Run `uv run ruff check resume_ai/models.py resume_ai/tailor.py` to confirm no lint errors.
  </verify>
  <done>
TailoredResume has keyword_alignment field defaulting to empty list. SYSTEM_PROMPT contains explicit keyword extraction, role-specific summary, and bullet optimization instructions while preserving all anti-fabrication rules. User message explicitly requests keyword alignment. All tests pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix PDF template CSS for professional layout and proper pagination</name>
  <files>webapp/templates/resume/resume_template.html</files>
  <action>
Rewrite the `<style>` block in `resume_template.html` with the following improvements. Keep the HTML structure identical -- only change CSS.

**Page setup:**
```css
@page {
    size: letter;
    margin: 0.5in 0.6in;  /* Slightly tighter to fit more content */
}
```

**Body typography improvements:**
```css
body {
    font-family: 'Calibri', 'Carlito', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #2d2d2d;
    -webkit-font-smoothing: antialiased;
}
```

**Heading improvements -- subtle accent color and better spacing:**
```css
h1 {
    font-size: 20pt;
    font-weight: 700;
    text-align: center;
    color: #1a1a1a;
    letter-spacing: 0.5pt;
    margin: 0;
}

h2 {
    font-size: 11pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1pt;
    color: #1a365d;           /* Dark navy accent for section headers */
    border-bottom: 1.5pt solid #1a365d;
    padding-bottom: 3pt;
    margin-top: 12pt;
    margin-bottom: 6pt;
}
```

**Contact info and links -- ensure clickable PDFs:**
```css
.contact-info {
    text-align: center;
    font-size: 9pt;
    color: #4a5568;
    margin-top: 4pt;
    line-height: 1.6;
}

.contact-info a {
    color: #2563eb;
    text-decoration: underline;  /* Underline links so they're obviously clickable in PDF */
}

/* Explicit link styling for WeasyPrint PDF rendering */
a {
    color: #2563eb;
    text-decoration: underline;
}
a[href]::after {
    content: none;  /* Prevent WeasyPrint from appending URL text after links */
}
```

**Page-break-inside: avoid on ALL section types (not just experience):**
```css
.experience-entry {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-bottom: 10pt;
}

.skills-section {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-bottom: 3pt;
}

.projects-list {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-top: 4pt;
}

.projects-list li {
    margin-bottom: 3pt;
}

.education-text {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-top: 4pt;
}
```

**Keep sections together with their headers:**
```css
h2 {
    /* (add to existing h2 rule) */
    page-break-after: avoid;
    break-after: avoid;
}
```

**Improved list styling:**
```css
ul {
    margin: 3pt 0;
    padding-left: 14pt;
}

li {
    margin-bottom: 2pt;
    line-height: 1.4;
}
```

**Job header improvements for better alignment:**
```css
.job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-top: 6pt;
    margin-bottom: 2pt;
}

.job-title {
    font-weight: 700;
    color: #1a1a1a;
}

.job-company {
    font-weight: 600;
    color: #2d3748;
}

.job-period {
    font-style: italic;
    color: #718096;
    font-size: 9pt;
    white-space: nowrap;
}
```

**Summary text:**
```css
.summary-text {
    margin-bottom: 4pt;
    text-align: justify;  /* Justified text looks more professional in PDF */
    hyphens: auto;
}
```

**Skill category styling:**
```css
.skill-category {
    font-weight: 700;
    color: #1a365d;  /* Match section header accent */
}
```

**Overflow safety -- prevent content from bleeding off page:**
```css
body {
    /* (add to existing body rule) */
    overflow-wrap: break-word;
    word-wrap: break-word;
}
```

Do NOT change any HTML structure or Jinja2 template logic. Only modify CSS within the `<style>` tag.
  </action>
  <verify>
Run `uv run pytest tests/resume_ai/test_renderer.py -v` to confirm renderer tests still pass (they use mock templates so CSS changes don't affect them). Visually inspect by searching the template file for `page-break-inside: avoid` to confirm it appears on `.experience-entry`, `.skills-section`, `.projects-list`, and `.education-text`.
  </verify>
  <done>
PDF template has: page-break-inside/break-inside avoid on all major sections (experience, skills, projects, education). Section headers prevent page-break-after. Links are underlined and clickable. Typography uses dark navy accent color for section headers. Justified summary text. Proper overflow handling. Tighter margins for better 2-page fit. WeasyPrint-compatible CSS properties used throughout.
  </done>
</task>

</tasks>

<verification>
1. `uv run pytest tests/resume_ai/ -v` -- all resume_ai tests pass
2. `uv run ruff check resume_ai/ webapp/templates/` -- no lint errors
3. `uv run ruff format --check resume_ai/` -- formatting correct
4. Grep for anti-fabrication rules still present: "MUST NOT" appears 4+ times in SYSTEM_PROMPT
5. Grep for keyword_alignment in models.py and tailor.py
6. Grep for page-break-inside in resume_template.html -- appears 4+ times
</verification>

<success_criteria>
- SYSTEM_PROMPT contains KEYWORD EXTRACTION, PROFESSIONAL SUMMARY, and BULLET POINT OPTIMIZATION instruction blocks
- All 4 ABSOLUTE RULES (anti-fabrication) preserved verbatim
- TailoredResume.keyword_alignment field exists with default_factory=list
- User message references company name and job title explicitly
- PDF template has page-break-inside: avoid on experience, skills, projects, education
- Links in PDF are underlined and use proper href styling
- Section headers use accent color and prevent orphaned headers (page-break-after: avoid)
- All existing + new tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/006-improve-resume-ai-prompts-and-fix-pdf-ou/006-01-SUMMARY.md`
</output>
