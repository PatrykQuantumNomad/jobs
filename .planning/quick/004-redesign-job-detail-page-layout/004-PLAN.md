---
phase: 004-redesign-job-detail-page-layout
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - webapp/templates/job_detail.html
autonomous: false
requirements: [LAYOUT-01]

must_haves:
  truths:
    - "Job header, description, tags, and notes are grouped in the left column as 'reading' content"
    - "Status change and Apply are grouped together in right column top as 'quick actions'"
    - "AI Analysis, AI Resume Tools, and Generated Documents are combined into one right column card as 'AI Intelligence'"
    - "Activity timeline sits below notes in the left column as user interaction history"
    - "Metadata (IDs, timestamps) sits at the bottom in a full-width footer"
    - "All htmx targets, triggers, endpoints, and interactivity are preserved exactly"
  artifacts:
    - path: "webapp/templates/job_detail.html"
      provides: "Redesigned job detail page layout"
      contains: "grid-cols-1 lg:grid-cols-3"
  key_links:
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/notes"
      via: "hx-post and hx-get for notes form and saved notes list"
      pattern: "hx-(post|get)=\"/jobs/.*/notes\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/status"
      via: "hx-post for status update form"
      pattern: "hx-post=\"/jobs/.*/status\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/ai-rescore"
      via: "hx-post for AI rescore button"
      pattern: "hx-post=\"/jobs/.*/ai-rescore\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/tailor-resume"
      via: "hx-post for tailor resume button"
      pattern: "hx-post=\"/jobs/.*/tailor-resume\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/cover-letter"
      via: "hx-post for cover letter button"
      pattern: "hx-post=\"/jobs/.*/cover-letter\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/resume-versions"
      via: "hx-get for generated documents list"
      pattern: "hx-get=\"/jobs/.*/resume-versions\""
    - from: "webapp/templates/job_detail.html"
      to: "/jobs/{dedup_key}/apply"
      via: "hx-post for apply button"
      pattern: "hx-post=\"/jobs/.*/apply\""
---

<objective>
Reorganize the job detail page (`job_detail.html`) from a scattered layout into a logically grouped 2-column design that matches user intent: left column for reading, right column for actions and AI tools.

Purpose: The current layout scatters related functionality (AI tools in 3 places, actions in 3 places, notes and activity separated). Regrouping by user intent makes the page scannable and reduces cognitive load.

Output: A single redesigned `job_detail.html` with identical interactivity but better information architecture.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@webapp/templates/job_detail.html
@webapp/templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Reorganize job_detail.html into intent-based 2-column layout</name>
  <files>webapp/templates/job_detail.html</files>
  <action>
Rewrite the layout of `webapp/templates/job_detail.html` by rearranging the existing HTML blocks into a new structure. Do NOT change any htmx attributes (`hx-post`, `hx-get`, `hx-target`, `hx-swap`, `hx-trigger`, `hx-indicator`, `hx-vals`, `hx-disabled-elt`), element IDs (`id="..."` attributes), form structures, or Jinja2 template logic. Only move blocks and adjust the grid/container CSS classes.

**New grid:** Change from `grid-cols-1 lg:grid-cols-4` to `grid-cols-1 lg:grid-cols-3` (2:1 ratio = `lg:col-span-2` + `lg:col-span-1`).

**Left column** (`lg:col-span-2 space-y-6`):
1. **Header card** (lines 16-72) -- move as-is, no changes
2. **Description card** (lines 75-82) -- move as-is
3. **Tags card** (lines 120-130) -- move up from after Metadata to right after Description for context proximity
4. **Notes & Activity card** -- combine into ONE card with two sections:
   - First section: Notes form + saved notes (lines 85-112 content, preserve all htmx)
   - Divider: `<div class="border-t my-4"></div>`
   - Second section: Activity timeline (lines 264-316 content, preserve all event rendering). Keep the overflow-y-auto scrollable area for the timeline entries but set `max-h-96` instead of flex-1/flex-col fill behavior since it no longer needs to fill sidebar height
   - Card heading: "Notes & Activity"

**Right column** (`space-y-6`):
1. **Quick Actions card** -- combine Status + Apply into ONE card:
   - Card heading: "Quick Actions"
   - First: Status badge display + status change form (lines 136-155 content)
   - Divider: `<div class="border-t my-4"></div>`
   - Second: Apply mode selector + apply button + apply status (lines 217-261 content, preserve all htmx including `hx-vals='js:...'` and `hx-indicator`)

2. **AI Intelligence card** -- combine AI Analysis + AI Resume Tools + Generated Documents into ONE card:
   - Card heading: "AI Intelligence"
   - First section: AI score display + rescore button + spinner (lines 158-214 content, preserve `id="ai-score-result"` and `id="ai-score-spinner"`)
   - Divider: `<div class="border-t my-4"></div>`
   - Second section: Tailor Resume + Cover Letter buttons + result area (lines 322-345 content, preserve `id="resume-ai-result"` and `hx-disabled-elt`)
   - Divider: `<div class="border-t my-4"></div>`
   - Third section: Generated Documents heading + lazy-loaded list (lines 348-356 content, preserve `id="resume-versions-list"` and `hx-trigger="load, refreshVersions from:body"`)

**Full-width footer** (below the grid, `mt-6`):
1. **Metadata** (line 115-117) -- move to bottom, keep same styling (`text-xs text-gray-400`)

**Critical preservation checklist:**
- `id="notes-status"` -- target for notes form response
- `id="saved-notes-list"` -- target for lazy-loaded notes + hx-trigger="load"
- `id="status-display"` -- target for status update response
- `id="ai-score-result"` -- target for AI rescore response
- `id="ai-score-spinner"` -- indicator for AI rescore loading
- `id="apply-mode"` -- referenced by `hx-vals='js:...'` in apply button
- `id="apply-btn"` -- apply button with conditional disabled state
- `id="apply-spinner"` -- indicator for apply engine loading
- `id="apply-status"` -- target for apply status updates
- `id="resume-ai-result"` -- target for tailor resume / cover letter response
- `id="resume-versions-list"` -- target for generated docs list + hx-trigger="load, refreshVersions from:body"
- `id="notes-input"` -- textarea for notes

Remove the old full-width `mt-6 space-y-6` wrapper div that held AI Resume Tools and Generated Documents (those sections now live inside the right column AI Intelligence card).

All Tailwind utility classes should remain standard -- no custom CSS. Use `bg-white rounded-lg shadow-sm border p-6` for each card wrapper (matching existing card style).
  </action>
  <verify>
Run `uv run python -c "from webapp.app import app; print('Template loads OK')"` to confirm the Jinja2 template parses without syntax errors.

Then verify all htmx IDs are preserved:
```bash
grep -oP 'id="[^"]*"' webapp/templates/job_detail.html | sort
```
Expected IDs (must ALL be present): `ai-score-result`, `ai-score-spinner`, `apply-btn`, `apply-mode`, `apply-status`, `apply-spinner`, `notes-input`, `notes-status`, `resume-ai-result`, `resume-versions-list`, `saved-notes-list`, `status-display`.

Verify all htmx endpoints are preserved:
```bash
grep -oP 'hx-(post|get)="[^"]*"' webapp/templates/job_detail.html | sort
```
Expected endpoints (must ALL be present): notes POST, notes GET, status POST, ai-rescore POST, apply POST, tailor-resume POST, cover-letter POST, resume-versions GET.
  </verify>
  <done>
The job detail page renders with the new 2-column layout: left column has header, description, tags, notes+activity; right column has quick actions (status+apply) and AI intelligence (analysis+resume tools+generated docs); metadata is in a full-width footer. All 12 htmx element IDs are present, all 8 htmx endpoints are wired, and the template parses without errors.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Visual verification of redesigned layout</name>
  <files>webapp/templates/job_detail.html</files>
  <action>Human visually verifies the redesigned layout in browser. No code changes -- this is a verification-only checkpoint.</action>
  <what-built>Reorganized job detail page with intent-based grouping: reading content on left, actions and AI tools on right</what-built>
  <how-to-verify>
    1. Start the web server: `uv run jobs-web`
    2. Navigate to http://localhost:8000
    3. Click on any job from the dashboard to open its detail page
    4. Verify LEFT column contains (top to bottom): Header (title, company, score), Description, Tags, Notes & Activity (combined card with notes form at top, activity timeline below)
    5. Verify RIGHT column contains (top to bottom): Quick Actions (status badge + status dropdown + apply mode + apply button), AI Intelligence (AI score if present + rescore button + tailor resume + cover letter buttons + generated documents list)
    6. Verify FOOTER has metadata (IDs, timestamps) in small gray text
    7. Click "Save Note" -- confirm it still submits and shows status
    8. Change status dropdown and click "Update" -- confirm badge updates
    9. Resize browser to mobile width -- confirm single column stacking
    10. Confirm no visual breakage, missing sections, or broken interactivity
  </how-to-verify>
  <verify>Human confirms layout matches expected grouping and all interactive elements work</verify>
  <done>User has approved the redesigned layout or provided feedback for iteration</done>
  <resume-signal>Type "approved" or describe any layout or functionality issues</resume-signal>
</task>

</tasks>

<verification>
- Template parses without Jinja2 syntax errors
- All 12 htmx element IDs preserved in the output
- All 8 htmx endpoints (hx-post/hx-get URLs) preserved
- Grid uses `grid-cols-1 lg:grid-cols-3` with `lg:col-span-2` left and implicit 1-col right
- No custom CSS added (Tailwind utilities only)
- No backend route changes needed
</verification>

<success_criteria>
Job detail page displays with logical grouping: reading content (header, description, tags, notes+activity) on left; action content (status+apply, AI tools+documents) on right; metadata in footer. All interactive features (notes, status, apply, AI rescore, resume tailoring, cover letter, document list) function identically to before.
</success_criteria>

<output>
After completion, create `.planning/quick/004-redesign-job-detail-page-layout/004-01-SUMMARY.md`
</output>
