---
phase: 002-fix-ci-coverage
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/resume_ai/test_models.py
  - tests/resume_ai/test_tailor.py
  - tests/resume_ai/test_cover_letter.py
  - tests/resume_ai/test_diff.py
  - tests/resume_ai/test_extractor.py
  - tests/resume_ai/test_renderer.py
  - tests/resume_ai/test_tracker.py
  - tests/apply_engine/test_engine.py
  - tests/apply_engine/test_dedup.py
  - tests/apply_engine/test_events.py
  - tests/webapp/test_endpoints.py
autonomous: true
must_haves:
  truths:
    - "pytest-cov reports >= 80% total coverage"
    - "All new tests pass on CI (no network calls, no Playwright)"
    - "Existing 417 tests still pass unchanged"
  artifacts:
    - path: "tests/resume_ai/test_tailor.py"
      provides: "Unit tests for tailor_resume, format_resume_as_text"
    - path: "tests/resume_ai/test_cover_letter.py"
      provides: "Unit tests for generate_cover_letter, format_cover_letter_as_text"
    - path: "tests/resume_ai/test_diff.py"
      provides: "Unit tests for generate_resume_diff_html, wrap_diff_html"
    - path: "tests/resume_ai/test_extractor.py"
      provides: "Unit tests for extract_resume_text"
    - path: "tests/resume_ai/test_renderer.py"
      provides: "Unit tests for render_resume_pdf, render_cover_letter_pdf"
    - path: "tests/resume_ai/test_tracker.py"
      provides: "Integration tests for save_resume_version, get_versions_for_job, get_all_versions"
    - path: "tests/apply_engine/test_engine.py"
      provides: "Unit tests for ApplyEngine sync helpers"
    - path: "tests/webapp/test_endpoints.py"
      provides: "Integration tests for untested webapp routes"
  key_links:
    - from: "tests/resume_ai/test_tailor.py"
      to: "resume_ai/tailor.py"
      via: "mock_anthropic fixture"
      pattern: "mock_anthropic"
    - from: "tests/apply_engine/test_engine.py"
      to: "apply_engine/engine.py"
      via: "direct unit testing of sync methods"
      pattern: "ApplyEngine"
---

<objective>
Increase test coverage from 62.61% to >= 80% by adding tests for the three largest uncovered areas: resume_ai/ (141 stmts at 0%), apply_engine/ (207 stmts at ~2%), and untested webapp/app.py routes (~100 stmts).

Purpose: CI is failing because coverage is below the 80% threshold configured in pyproject.toml. These three module areas account for ~448 missed statements -- covering roughly 60% of them (269 stmts) crosses the threshold.

Output: New test files covering resume_ai, apply_engine, and additional webapp endpoints. Total coverage >= 80%.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml (coverage config, test markers, pytest options)
@tests/conftest.py (autouse fixtures: _fresh_db, _block_anthropic, _reset_settings)
@tests/resume_ai/conftest.py (mock_anthropic fixture)
@tests/webapp/conftest.py (client fixture)
@tests/webapp/test_endpoints.py (existing test patterns for webapp routes)
@tests/resume_ai/test_validator.py (existing test patterns for resume_ai)
@resume_ai/models.py (TailoredResume, CoverLetter, SkillSection, WorkExperience Pydantic models)
@resume_ai/tailor.py (tailor_resume, format_resume_as_text)
@resume_ai/cover_letter.py (generate_cover_letter, format_cover_letter_as_text)
@resume_ai/diff.py (generate_resume_diff_html, wrap_diff_html)
@resume_ai/extractor.py (extract_resume_text)
@resume_ai/renderer.py (render_resume_pdf, render_cover_letter_pdf)
@resume_ai/tracker.py (save_resume_version, get_versions_for_job, get_all_versions)
@apply_engine/engine.py (ApplyEngine class with confirm, cancel, _emit_sync, _get_resume_path, _make_emitter)
@apply_engine/dedup.py (is_already_applied)
@apply_engine/events.py (ApplyEvent, ApplyEventType, make_progress_event, make_done_event)
@apply_engine/config.py (ApplyMode, ApplyConfig)
@webapp/app.py (all routes -- kanban, analytics, run_history, stats_cards, resume AI endpoints, apply endpoints are untested)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add tests for resume_ai/ module (141 stmts, 0% -> ~80%+)</name>
  <files>
    tests/resume_ai/test_models.py
    tests/resume_ai/test_tailor.py
    tests/resume_ai/test_cover_letter.py
    tests/resume_ai/test_diff.py
    tests/resume_ai/test_extractor.py
    tests/resume_ai/test_renderer.py
    tests/resume_ai/test_tracker.py
  </files>
  <action>
Create unit and integration tests for all resume_ai submodules. Follow existing patterns from tests/resume_ai/test_validator.py (use @pytest.mark.unit on test classes).

**tests/resume_ai/test_models.py** -- @pytest.mark.unit
Test all four Pydantic models can be instantiated with valid data and that field validation works:
- `SkillSection(category="Backend", skills=["Python", "Go"])` constructs correctly
- `WorkExperience(company="Acme", title="Engineer", period="2020-2024", achievements=["Led team"])` constructs correctly
- `TailoredResume` with all required fields (professional_summary, technical_skills as list[SkillSection], work_experience as list[WorkExperience], key_projects as list[str], education as str, tailoring_notes as str)
- `CoverLetter` with all required fields (greeting, opening_paragraph, body_paragraphs as list[str], closing_paragraph, sign_off)
- Test `model_dump(mode="json")` produces a dict with all keys
- Test missing required fields raise ValidationError

**tests/resume_ai/test_tailor.py** -- @pytest.mark.unit
- `test_tailor_resume_success`: Use `mock_anthropic` fixture. Set `mock_anthropic.messages.parse.return_value` to a MagicMock with `parsed_output` set to a real `TailoredResume` instance. Call `tailor_resume("resume text", "job desc", "Engineer", "Acme")`. Assert it returns the TailoredResume. Assert `messages.parse` was called once with correct model, max_tokens=4096, temperature=0, system=SYSTEM_PROMPT, output_format=TailoredResume.
- `test_tailor_resume_auth_error`: Mock `anthropic.Anthropic` to raise `anthropic.AuthenticationError`. Assert `tailor_resume(...)` raises `RuntimeError` with "ANTHROPIC_API_KEY".
- `test_tailor_resume_api_error`: Mock `messages.parse` to raise `anthropic.APIError`. Assert RuntimeError.
- `test_tailor_resume_no_parsed_output`: Mock `messages.parse` to return response with `parsed_output=None`. Assert RuntimeError with "no parsed output".
- `test_format_resume_as_text`: Create a TailoredResume with known data. Call `format_resume_as_text()`. Assert output contains "PROFESSIONAL SUMMARY", "TECHNICAL SKILLS", "WORK EXPERIENCE", "KEY PROJECTS", "EDUCATION". Assert specific text appears (company, title, skills).

**tests/resume_ai/test_cover_letter.py** -- @pytest.mark.unit
- `test_generate_cover_letter_success`: Same pattern as tailor -- mock `messages.parse` to return CoverLetter. Assert correct return and API call params (max_tokens=2048, temperature=0.3).
- `test_generate_cover_letter_auth_error`: RuntimeError on AuthenticationError.
- `test_generate_cover_letter_no_parsed_output`: RuntimeError on None parsed_output.
- `test_format_cover_letter_as_text`: Create CoverLetter with known fields. Call `format_cover_letter_as_text(letter, "John Doe")`. Assert greeting, opening, body paragraphs, closing, sign-off, and "John Doe" all appear in output. Assert paragraphs are separated by double newlines.

**tests/resume_ai/test_diff.py** -- @pytest.mark.unit
- `test_generate_diff_html_returns_table`: Call `generate_resume_diff_html("line1\nline2", "line1\nline3")`. Assert result contains `<table` and `</table>`.
- `test_generate_diff_html_identical_text`: Same text for both -> result is still valid HTML table.
- `test_wrap_diff_html_adds_css_and_container`: Call `wrap_diff_html("<table>...</table>")`. Assert result contains `<style>`, `class="resume-diff"`, and the original table content.

**tests/resume_ai/test_extractor.py** -- @pytest.mark.unit
- `test_extract_resume_text_file_not_found`: Call `extract_resume_text("/nonexistent/path.pdf")`. Assert FileNotFoundError.
- `test_extract_resume_text_success`: Use `monkeypatch` to patch `pymupdf4llm.to_markdown` to return "# Resume\n\nContent". Create a temporary file with `tmp_path` fixture. Call `extract_resume_text(tmp_path / "test.pdf")` -- but since the function checks existence then calls pymupdf4llm, create the temp file first (`(tmp_path / "test.pdf").write_bytes(b"fake")`), then monkeypatch pymupdf4llm.to_markdown. Assert returns "# Resume\n\nContent".
- `test_extract_resume_text_list_result`: Patch `to_markdown` to return `["page1", "page2"]`. Assert result is `"page1\npage2"`.

**tests/resume_ai/test_renderer.py** -- @pytest.mark.unit
- `test_render_resume_pdf`: Create a TailoredResume instance. Monkeypatch `weasyprint.HTML` to avoid actual PDF generation -- mock `HTML(string=..., base_url=...).write_pdf(...)`. Call `render_resume_pdf(tailored, "John Doe", "email | phone", tmp_path / "out.pdf")`. Assert the function calls `HTML` with string containing the resume data and calls `write_pdf`. Also verify `output_path.parent.mkdir` is called (it creates dirs). NOTE: The renderer uses Jinja2 templates from `webapp/templates/resume/`. The templates may or may not exist in CI. Best approach: monkeypatch `_get_env` to return a Jinja2 Environment with a simple test template, OR monkeypatch the whole `HTML` class. Simplest: monkeypatch `weasyprint.HTML` so `write_pdf` is a no-op, and monkeypatch `_get_env` to return an env with an inline template via `jinja2.DictLoader`. Use `jinja2.Environment(loader=jinja2.DictLoader({"resume_template.html": "{{ name }} {{ summary }}", "cover_letter_template.html": "{{ candidate_name }} {{ greeting }}"}))`.
- `test_render_cover_letter_pdf`: Same pattern with CoverLetter model and `render_cover_letter_pdf`.

**tests/resume_ai/test_tracker.py** -- @pytest.mark.integration (uses DB via _fresh_db autouse)
- `test_save_resume_version_returns_id`: Call `save_resume_version(job_dedup_key="test::job", resume_type="resume", file_path="/tmp/resume.pdf", original_resume_path="/tmp/orig.pdf", model_used="claude-test")`. Assert returns int > 0. First insert a job into DB using `db_module.upsert_job(...)` so the foreign key works (or if no FK constraint, just insert directly).
- `test_get_versions_for_job`: Save two versions for same job, one for different job. Call `get_versions_for_job("test::job")`. Assert returns 2 items, newest first.
- `test_get_all_versions`: Save versions for multiple jobs. Call `get_all_versions(limit=10)`. Assert returns all versions with job metadata (title, company from LEFT JOIN).
- `test_get_versions_empty`: Call `get_versions_for_job("nonexistent")`. Assert returns empty list.
  </action>
  <verify>
Run `uv run pytest tests/resume_ai/ -v --no-header` and confirm all new tests pass. Then run `uv run pytest --cov=resume_ai --cov-report=term-missing --no-header -q` and confirm resume_ai coverage is well above 50%.
  </verify>
  <done>
All resume_ai submodules have meaningful tests. resume_ai/ coverage rises from 0% (except validator at 98%) to >= 70% across the module. No real API calls, no real PDF generation -- all external deps are mocked.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add tests for apply_engine/ and untested webapp routes (~300 stmts)</name>
  <files>
    tests/apply_engine/__init__.py
    tests/apply_engine/test_engine.py
    tests/apply_engine/test_dedup.py
    tests/apply_engine/test_events.py
    tests/webapp/test_endpoints.py
  </files>
  <action>
Create tests for apply_engine module and add tests for untested webapp/app.py routes. Follow existing patterns.

**tests/apply_engine/__init__.py** -- empty file

**tests/apply_engine/test_events.py** -- @pytest.mark.unit
- `test_apply_event_type_values`: Assert all enum values: PROGRESS="progress", AWAITING_CONFIRM="awaiting_confirm", etc.
- `test_apply_event_defaults`: Create `ApplyEvent(type=ApplyEventType.PROGRESS)`. Assert message="", html="", screenshot_path=None, fields_filled={}, job_dedup_key="".
- `test_apply_event_model_dump`: Create event with all fields set. Call `model_dump()`. Assert dict has all expected keys with correct values.
- `test_make_progress_event`: Call `make_progress_event("test msg", job_dedup_key="key1")`. Assert type is PROGRESS, message is "test msg", job_dedup_key is "key1".
- `test_make_done_event`: Call `make_done_event()`. Assert type is DONE, message is "Application submitted successfully". Call with custom message, assert custom message used.

**tests/apply_engine/test_dedup.py** -- @pytest.mark.integration (uses DB)
- `test_is_already_applied_no_job`: Call `is_already_applied("nonexistent::key")`. Assert returns None.
- `test_is_already_applied_discovered_status`: Insert a job with status="discovered". Call `is_already_applied(dedup_key)`. Assert returns None (not applied).
- `test_is_already_applied_applied_status`: Insert a job, update status to "applied". Call `is_already_applied(dedup_key)`. Assert returns dict with status "applied".
- `test_is_already_applied_phone_screen`: Same pattern with "phone_screen" status. Assert returns dict.
- `test_is_already_applied_offer`: Same with "offer" status. Assert returns dict.

**tests/apply_engine/test_engine.py** -- @pytest.mark.unit
Test the synchronous helper methods of ApplyEngine WITHOUT triggering Playwright or browser imports. Use constructor with a mock settings object.

Create a mock settings object:
```python
from unittest.mock import MagicMock
mock_settings = MagicMock()
mock_settings.candidate_resume_path = "/tmp/default_resume.pdf"
mock_settings.apply.default_mode.value = "semi_auto"
```

- `test_confirm_existing_session`: Create engine with mock settings. Manually add a threading.Event to `engine._confirmations["key1"]`. Call `engine.confirm("key1")`. Assert returns True. Assert the event is set.
- `test_confirm_nonexistent_session`: Call `engine.confirm("nonexistent")`. Assert returns False.
- `test_cancel_existing_session`: Create engine. Add an asyncio.Queue to `engine._sessions["key1"]` and a threading.Event to `engine._confirmations["key1"]`. Call `engine.cancel("key1")`. Assert returns True. Assert "key1" removed from _sessions and _confirmations.
- `test_cancel_nonexistent_session`: Call `engine.cancel("nonexistent")`. Assert returns False.
- `test_get_session_queue_exists`: Add queue to _sessions. Call `engine.get_session_queue("key1")`. Assert returns the queue.
- `test_get_session_queue_missing`: Call `engine.get_session_queue("missing")`. Assert returns None.
- `test_emit_sync_puts_event`: Create asyncio.Queue. Create ApplyEvent. Call `ApplyEngine._emit_sync(queue, event)`. Assert `queue.get_nowait()` returns the event dict.
- `test_emit_sync_suppresses_errors`: Call `_emit_sync` with a MagicMock queue whose `put_nowait` raises. Assert no exception propagated.
- `test_get_resume_path_default`: Mock `webapp.db.get_conn` so the SQL query returns no row. Call `engine._get_resume_path("key1")`. Assert returns Path matching settings.candidate_resume_path. Use monkeypatch to patch `webapp.db.get_conn` context manager.
- `test_get_resume_path_tailored_exists`: Mock DB to return a row with file_path pointing to a temp file (use tmp_path). Create that temp file. Assert returns the tailored path.
- `test_make_emitter_returns_callable`: Create engine. Call `engine._make_emitter(asyncio.Queue(), asyncio.get_event_loop())`. Assert result is callable.

**Add to tests/webapp/test_endpoints.py** -- @pytest.mark.integration
Add test classes for the untested routes. Follow existing patterns (_make_job_dict, _compute_dedup_key, client fixture).

TestRunHistoryEndpoint:
- `test_run_history_returns_200`: GET /runs returns 200 with HTML.

TestAnalyticsEndpoint:
- `test_analytics_page_returns_200`: GET /analytics returns 200 with HTML.
- `test_analytics_api_returns_json`: GET /api/analytics returns 200 with JSON.

TestKanbanEndpoint:
- `test_kanban_page_returns_200`: GET /kanban returns 200 with HTML.
- `test_kanban_shows_saved_jobs`: Insert a job, update status to "saved". GET /kanban. Assert job title appears in response.

TestStatsCardsEndpoint:
- `test_stats_cards_returns_200`: GET /api/stats-cards returns 200 with HTML.

TestServeResume:
- `test_serve_nonexistent_resume_returns_404`: GET /resumes/tailored/nonexistent.pdf returns 404.

TestApplyEndpoints:
- `test_trigger_apply_job_not_found`: POST /jobs/nonexistent::key/apply returns 404.
- `test_trigger_apply_already_applied`: Insert job, set status to "applied". POST /jobs/{key}/apply. Assert response contains "Already applied".
- `test_apply_confirm_returns_200`: POST /jobs/test::key/apply/confirm. Assert 200 with "Confirmed" text.
- `test_apply_cancel_returns_200`: POST /jobs/test::key/apply/cancel. Assert 200 with "cancelled" text.

TestResumeVersionsEndpoint:
- `test_resume_versions_returns_200`: GET /jobs/{key}/resume-versions returns 200.
  </action>
  <verify>
Run `uv run pytest tests/apply_engine/ tests/webapp/test_endpoints.py -v --no-header` and confirm all new tests pass alongside existing ones. Run `uv run pytest --cov --cov-report=term-missing --no-header -q` to verify total coverage >= 80%.
  </verify>
  <done>
apply_engine/ module has meaningful tests for events, dedup, and engine helpers. webapp/app.py has tests for kanban, analytics, run history, stats cards, apply, and resume endpoints. Total project coverage is >= 80%, CI passes.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify full test suite passes with >= 80% coverage</name>
  <files></files>
  <action>
Run the complete test suite with coverage to verify the 80% threshold is met:

```bash
uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 -q
```

If coverage is still slightly below 80%, identify the remaining gap from the coverage report and add a few targeted tests for the easiest-to-cover missed lines. Likely candidates:
- `platforms/protocols.py` (60% -> add a test that instantiates/exercises the Protocol)
- `platforms/mixins.py` (27% -> add tests for element_exists, wait_for_confirmation with mock page)
- `webapp/app.py` remaining untested lines

If all 417 existing tests + new tests pass and coverage >= 80%, this task is done.
  </action>
  <verify>
`uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 -q` exits with code 0 (all tests pass, coverage >= 80%).
  </verify>
  <done>
Full test suite passes. Coverage report shows >= 80%. CI will pass with the fail_under=80 threshold. No regressions in existing tests.
  </done>
</task>

</tasks>

<verification>
1. `uv run pytest -q` -- all tests pass (existing 417 + new tests), zero failures
2. `uv run pytest --cov --cov-report=term-missing --cov-fail-under=80 -q` -- exits 0, coverage >= 80%
3. `uv run ruff check .` -- no lint errors in new test files
4. `uv run ruff format --check .` -- no formatting issues
</verification>

<success_criteria>
- Total test coverage >= 80% (up from 62.61%)
- All existing 417 tests still pass
- New tests use @pytest.mark.unit or @pytest.mark.integration markers
- No real API calls (Anthropic, network) -- all mocked
- No real PDF generation (WeasyPrint) -- mocked
- No Playwright/browser imports in apply_engine tests
- `uv run pytest --cov --cov-fail-under=80` exits 0
</success_criteria>

<output>
After completion, create `.planning/quick/002-fix-ci-increase-test-coverage-from-62-61/002-SUMMARY.md`
</output>
