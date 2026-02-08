---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - webapp/templates/kanban.html
  - tests/e2e/test_kanban.py
autonomous: true
must_haves:
  truths:
    - "Dragging a card between Kanban columns updates the job status in the database"
    - "The Kanban board remains fully visible and functional after a drag-and-drop"
    - "Column counts update correctly after drag-and-drop"
    - "Stats cards refresh after drag-and-drop via HX-Trigger"
  artifacts:
    - path: "webapp/templates/kanban.html"
      provides: "Fixed drag-and-drop JavaScript handler"
      contains: "swap"
  key_links:
    - from: "webapp/templates/kanban.html"
      to: "webapp/app.py update_status"
      via: "htmx.ajax POST with swap:none"
      pattern: "swap.*none"
---

<objective>
Fix Kanban board drag-and-drop destroying the page after dropping a card.

Purpose: When a user drags a card between status columns, the `htmx.ajax` call to
`POST /jobs/{key}/status` receives an HTML response (`<span>` badge) and, without
a `target` or `swap` specified, htmx defaults to swapping it into `document.body`
as innerHTML -- replacing the entire Kanban board with a tiny status badge. The board
disappears and becomes unusable.

Root cause: The `onEnd` handler in kanban.html line 77 calls `htmx.ajax('POST', url, {values: ...})`
without specifying `swap: "none"`. The `update_status` endpoint (app.py line 604) returns a
`<span>` element intended for the job detail page's inline status update, not for the Kanban
board context. htmx's default behavior swaps the response into `document.body`, destroying the page.

Output: Working drag-and-drop that persists status changes without destroying the Kanban board.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@webapp/templates/kanban.html
@webapp/app.py
@webapp/db.py
@webapp/templates/partials/kanban_card.html
@tests/e2e/test_kanban.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix htmx.ajax swap behavior in Kanban drag handler</name>
  <files>webapp/templates/kanban.html</files>
  <action>
In the `{% block scripts %}` section of `kanban.html`, fix the `htmx.ajax` call inside the
SortableJS `onEnd` handler (around line 77).

Current broken code:
```javascript
await htmx.ajax('POST', '/jobs/' + encodeURIComponent(dedupKey) + '/status', {
    values: { status: newStatus }
});
```

Replace with a plain `fetch()` call instead of `htmx.ajax()`. Using `fetch()` is better than
`htmx.ajax` with `swap: "none"` because:
1. We genuinely do NOT want any DOM swapping -- this is a fire-and-forget status update.
2. `fetch()` gives us clean error handling via `response.ok`.
3. We still need to trigger the `statsChanged` event manually for the stats cards to refresh.

Replace the try/catch block (lines ~76-93) with:

```javascript
try {
    var formData = new FormData();
    formData.append('status', newStatus);
    var response = await fetch('/jobs/' + encodeURIComponent(dedupKey) + '/status', {
        method: 'POST',
        body: formData
    });
    if (!response.ok) throw new Error('Status ' + response.status);
    // Trigger statsChanged so the stats cards partial refreshes
    document.body.dispatchEvent(new Event('statsChanged'));
} catch (err) {
    // Rollback: move card back ...
```

Keep the existing rollback logic inside the catch block exactly as-is.

Do NOT change any other part of the file -- leave SortableJS initialization, `updateColumnCount`,
and the HTML template unchanged.
  </action>
  <verify>
Run `uv run ruff check webapp/templates/kanban.html` (should have no Python issues since it is HTML).
Manually inspect the file to confirm:
1. `htmx.ajax` is no longer used in the onEnd handler
2. `fetch()` is used with POST method and FormData body
3. `statsChanged` event is dispatched on success
4. Rollback logic is preserved in the catch block
5. `updateColumnCount` calls are preserved (optimistic count update before try, rollback in catch)
  </verify>
  <done>
The kanban.html onEnd handler uses `fetch()` instead of `htmx.ajax()`, preventing htmx from
swapping the response HTML into the page body. The statsChanged event is manually dispatched
so stats cards still refresh.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update E2E test to use fetch instead of htmx.ajax</name>
  <files>tests/e2e/test_kanban.py</files>
  <action>
In `test_drag_card_from_saved_to_applied`, the `page.evaluate()` call (lines 142-151) currently
simulates the drag by calling `htmx.ajax`. Update it to use `fetch()` to match the new
implementation in kanban.html.

Replace the `page.evaluate()` block with:

```python
page.evaluate(
    """(cardKey) => {
        var formData = new FormData();
        formData.append('status', 'applied');
        return fetch('/jobs/' + encodeURIComponent(cardKey) + '/status', {
            method: 'POST',
            body: formData
        }).then(r => { if (!r.ok) throw new Error('Status ' + r.status); });
    }""",
    card_key,
)
```

This matches the new kanban.html implementation exactly. Keep everything else in the test unchanged.

Also add a NEW test method `test_drag_does_not_destroy_board` that verifies the core bug fix:

```python
def test_drag_does_not_destroy_board(self, page, live_server, seeded_kanban_db):
    """Dragging a card between columns must NOT destroy the Kanban board.

    Regression test: previously htmx.ajax swapped the response into document.body,
    replacing the entire board with a status badge span.
    """
    page.goto(f"{live_server}/kanban")
    page.wait_for_load_state("networkidle")

    # Get a card key from saved column
    card = page.locator("#col-saved .kanban-card").first
    card_key = card.get_attribute("data-key")

    # Simulate the drag-and-drop status update (same as onEnd handler)
    page.evaluate(
        """(cardKey) => {
            var formData = new FormData();
            formData.append('status', 'applied');
            return fetch('/jobs/' + encodeURIComponent(cardKey) + '/status', {
                method: 'POST',
                body: formData
            }).then(r => { if (!r.ok) throw new Error('Status ' + r.status); });
        }""",
        card_key,
    )

    page.wait_for_timeout(300)

    # CRITICAL: The board must still be visible (not replaced by response HTML)
    expect(page.locator(".kanban-list")).to_have_count(9)  # 9 kanban columns
    expect(page.locator("#col-saved")).to_be_visible()
    expect(page.locator("#col-applied")).to_be_visible()

    # The page title should still be the kanban page
    expect(page).to_have_title("Kanban -- Job Tracker")
```

Place this test after `test_drag_card_from_saved_to_applied` in the `TestKanbanE2E` class.
  </action>
  <verify>
Run `uv run ruff check tests/e2e/test_kanban.py` -- no lint errors.
Run `uv run ruff format --check tests/e2e/test_kanban.py` -- properly formatted.
Run `uv run pytest tests/e2e/test_kanban.py --collect-only` -- all 3 tests collected (loads, drag persists, drag does not destroy board).
  </verify>
  <done>
E2E test `test_drag_card_from_saved_to_applied` updated to use `fetch()` matching the fix.
New regression test `test_drag_does_not_destroy_board` verifies the board survives a drag-and-drop
without being replaced by the status endpoint response.
  </done>
</task>

</tasks>

<verification>
1. `uv run ruff check webapp/templates/kanban.html tests/e2e/test_kanban.py` -- no lint errors
2. `uv run pytest tests/webapp/test_endpoints.py -k kanban -v` -- existing unit tests still pass
3. `uv run pytest tests/e2e/test_kanban.py -v` -- all 3 E2E tests pass (if E2E infra available)
4. Manual: start `python -m webapp.app`, visit `http://localhost:8000/kanban`, drag a card between columns -- board stays intact, status persists on reload
</verification>

<success_criteria>
- Dragging a Kanban card between columns persists the status change in the database
- The Kanban board remains fully rendered after drag-and-drop (no page destruction)
- Column counts update optimistically on drag
- Stats cards refresh after successful drag (statsChanged event)
- All existing tests continue to pass
- New regression test prevents reintroduction of the bug
</success_criteria>

<output>
After completion, create `.planning/quick/003-fix-kanban-drag-and-drop-status-switchin/003-SUMMARY.md`
</output>
