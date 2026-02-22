---
phase: quick
plan: 007
type: execute
wave: 1
depends_on: []
files_modified:
  - core/interview_prep.py
  - webapp/app.py
  - webapp/templates/job_detail.html
  - webapp/templates/partials/interview_questions_result.html
autonomous: true
requirements: [QUICK-007]

must_haves:
  truths:
    - "User can click a button on the job detail page to generate interview questions"
    - "Claude CLI produces structured interview questions based on job description"
    - "Generated questions appear on the page without a full reload"
  artifacts:
    - path: "core/interview_prep.py"
      provides: "Interview question generation via Claude CLI"
      exports: ["generate_interview_questions", "InterviewQuestions"]
    - path: "webapp/templates/partials/interview_questions_result.html"
      provides: "htmx partial rendering interview questions"
  key_links:
    - from: "webapp/app.py"
      to: "core/interview_prep.py"
      via: "import and await generate_interview_questions()"
      pattern: "generate_interview_questions"
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/interview-questions"
      via: "hx-post button"
      pattern: "hx-post.*interview-questions"
---

<objective>
Add an "Interview Prep" button to the job detail page that generates tailored interview questions using Claude CLI (subprocess) based on the job description.

Purpose: Help the user prepare for interviews by generating role-specific questions derived from the actual job posting, using the same Claude CLI structured output pattern as ai_scorer.py and resume_ai/tailor.py.
Output: A new `core/interview_prep.py` module, a new htmx endpoint, a partial template, and the button wired into the existing job detail page.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/ai_scorer.py (pattern: Pydantic model + system prompt + cli_run() async call)
@claude_cli/client.py (the async subprocess wrapper: cli_run(system_prompt, user_message, output_model, model))
@webapp/app.py (endpoint patterns: htmx POST returning HTML partial, same pattern as ai_rescore_endpoint)
@webapp/templates/job_detail.html (where the button goes — in the AI tools section or new section)
@webapp/templates/partials/ai_score_result.html (pattern for result partial template)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create interview question generation module</name>
  <files>core/interview_prep.py</files>
  <action>
Create `core/interview_prep.py` following the exact pattern of `core/ai_scorer.py`:

1. Define a Pydantic model `InterviewQuestions` with these fields:
   - `technical_questions: list[str]` — 5-7 technical questions specific to the technologies and skills mentioned in the job description (e.g., "How would you design a distributed caching layer for a high-throughput API?")
   - `behavioral_questions: list[str]` — 3-5 behavioral/situational questions based on the role's responsibilities (e.g., "Describe a time you led a cross-functional team through a critical production incident")
   - `company_specific_questions: list[str]` — 2-3 questions the candidate should ask the interviewer, showing research into the company/role
   - `key_topics: list[str]` — 5-8 key technical topics the candidate should review before the interview

2. Write a `SYSTEM_PROMPT` that instructs Claude to:
   - Analyze the job description for required skills, technologies, and responsibilities
   - Generate questions that a real interviewer at this company would likely ask
   - Make technical questions specific (not generic "tell me about REST APIs" but specific to the stack in the JD)
   - Make behavioral questions reference the actual responsibilities in the posting
   - Suggest thoughtful candidate questions that demonstrate genuine interest

3. Write an `async def generate_interview_questions(job_description: str, job_title: str, company_name: str, model: str = "sonnet") -> InterviewQuestions` function that:
   - Calls `cli_run()` from `claude_cli` with the system prompt, a user message containing the job description/title/company, and the `InterviewQuestions` output model
   - Wraps `CLIError` in `RuntimeError` (same pattern as `ai_scorer.py`)

Use absolute imports only. Use `from claude_cli import run as cli_run` and `from claude_cli.exceptions import CLIError`.
  </action>
  <verify>
Run `python -c "from core.interview_prep import generate_interview_questions, InterviewQuestions; print('OK')"` — should print OK without errors.
Run `uv run ruff check core/interview_prep.py` — no lint errors.
  </verify>
  <done>Module exists with InterviewQuestions Pydantic model and async generate_interview_questions() function that calls Claude CLI, following the same pattern as core/ai_scorer.py.</done>
</task>

<task type="auto">
  <name>Task 2: Add endpoint, partial template, and button to job detail page</name>
  <files>webapp/app.py, webapp/templates/partials/interview_questions_result.html, webapp/templates/job_detail.html</files>
  <action>
**A. Create the htmx partial template** at `webapp/templates/partials/interview_questions_result.html`:

Render the `InterviewQuestions` result in a clean card layout with:
- A "Technical Questions" section with numbered list of technical questions
- A "Behavioral Questions" section with numbered list
- A "Questions to Ask the Interviewer" section with bullet list
- A "Key Topics to Review" section with pill/tag-style layout (similar to how tags are shown on job_detail.html)
- Use Tailwind classes consistent with the existing UI (text-sm, gray-700, etc.)

Template receives context variables: `technical_questions`, `behavioral_questions`, `company_specific_questions`, `key_topics`.

**B. Add the POST endpoint** in `webapp/app.py`:

Add a new endpoint `@app.post("/jobs/{dedup_key:path}/interview-questions")` — place it BEFORE the catch-all `GET /jobs/{dedup_key:path}` route (near the other AI endpoints like `ai_rescore_endpoint`).

Follow the exact pattern of `ai_rescore_endpoint`:
1. Look up job via `db.get_job(dedup_key)`, return 404 if not found
2. Guard: description must be >= 50 chars (same check as ai_rescore)
3. Import `generate_interview_questions` from `core.interview_prep`
4. Call `await generate_interview_questions(description, job["title"], job["company"])`
5. Log activity: `db.log_activity(dedup_key, "interview_prep", detail="Generated interview questions")`
6. Return `templates.TemplateResponse` with the partial template, passing the model fields as context
7. Wrap in try/except, return error HTML div on failure (same pattern as ai_rescore)

Do NOT use SSE for this — it is a simple request/response like AI rescore (the generation takes ~10-15 seconds, same as scoring). Use `hx-indicator` for a spinner.

**C. Add the button to `job_detail.html`**:

Add a new section AFTER the "AI Resume Tools" section (before "Generated Documents") in the full-width sections area at the bottom. Create an "Interview Prep" card with:
- Header: "Interview Prep" (same uppercase tracking-wider style as other section headers)
- A button: "Generate Questions" styled with `bg-gray-800 text-white` (same style as the AI Rescore button)
- `hx-post="/jobs/{{ job.dedup_key | urlencode }}/interview-questions"`
- `hx-target="#interview-prep-result"` and `hx-swap="innerHTML"`
- `hx-indicator="#interview-prep-spinner"` with a spinner div showing "Generating interview questions... 10-15 seconds"
- `hx-disabled-elt="this"` to prevent double-clicks
- A `<div id="interview-prep-result"></div>` for the response
  </action>
  <verify>
Run `uv run ruff check webapp/app.py` — no lint errors.
Run `uv run python -c "from webapp.app import app; print('routes:', len(app.routes))"` — app loads without import errors.
Start the server with `uv run jobs-web` and verify the job detail page renders with the new Interview Prep section visible (the button should appear). No need to test the actual generation (requires Claude CLI auth).
  </verify>
  <done>
Job detail page shows an "Interview Prep" section with a "Generate Questions" button. Clicking it POSTs to the new endpoint, which calls Claude CLI to generate structured interview questions and returns them as an htmx partial. Activity is logged. Error states are handled gracefully.
  </done>
</task>

</tasks>

<verification>
1. `uv run ruff check core/interview_prep.py webapp/app.py` passes with no errors
2. `uv run ruff format --check core/interview_prep.py webapp/app.py` passes
3. `python -c "from core.interview_prep import generate_interview_questions, InterviewQuestions"` succeeds
4. `python -c "from webapp.app import app"` succeeds (no import errors)
5. Job detail page at `/jobs/{any_key}` renders with the Interview Prep section and button visible
</verification>

<success_criteria>
- core/interview_prep.py exists with InterviewQuestions model and generate_interview_questions() async function
- webapp/app.py has POST /jobs/{dedup_key}/interview-questions endpoint
- webapp/templates/partials/interview_questions_result.html renders structured questions
- webapp/templates/job_detail.html has Interview Prep section with Generate Questions button
- All lint checks pass
- Server starts without errors
</success_criteria>

<output>
After completion, create `.planning/quick/007-add-button-to-generate-interview-questio/007-SUMMARY.md`
</output>
