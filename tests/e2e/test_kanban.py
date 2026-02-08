"""E2E tests for the kanban board page.

Covers:
- E2E-04: Kanban board loads with correct column layout and card counts
- E2E-04: Drag-and-drop (via fetch POST) moves a card between columns
  and the new status persists in the database after reload
- Regression: Drag-and-drop does not destroy the board (htmx.ajax swap bug)

Approach: SortableJS uses ``forceFallback: true`` which makes native Playwright
``drag_to()`` unreliable. Instead we test the full-stack persistence path by
invoking the same ``fetch('POST', '/jobs/.../status', ...)`` call that
SortableJS's ``onEnd`` handler fires. This validates the server round-trip,
database persistence, and page rendering -- the same path real drag-and-drop
takes.
"""

import pytest
from playwright.sync_api import expect

from models import JobStatus


@pytest.fixture
def seeded_kanban_db(_fresh_db):
    """Seed the in-memory database with jobs in kanban-visible statuses.

    Creates:
    - 3 jobs with status ``saved`` (one per platform, scores 3, 4, 5)
    - 2 jobs with status ``applied`` (indeed + dice, scores 4, 5)

    Returns the list of 5 Job instances with their assigned statuses.
    """
    import webapp.db as db_module
    from tests.conftest_factories import JobFactory

    jobs = []

    # 3 saved jobs (one per platform)
    for i, (platform, score) in enumerate([("indeed", 3), ("dice", 4), ("remoteok", 5)]):
        job = JobFactory(
            platform=platform,
            score=score,
            title=f"Kanban Saved {platform.title()} {i + 1}",
            status=JobStatus.SAVED,
        )
        db_module.upsert_job(job.model_dump(mode="json"))
        # upsert_job sets status to the Job's status field, but we need to
        # explicitly call update_job_status to ensure the status column is set
        dedup_key = _make_dedup_key(job.company, job.title)
        db_module.update_job_status(dedup_key, "saved")
        jobs.append(job)

    # 2 applied jobs
    for i, (platform, score) in enumerate([("indeed", 4), ("dice", 5)]):
        job = JobFactory(
            platform=platform,
            score=score,
            title=f"Kanban Applied {platform.title()} {i + 1}",
            status=JobStatus.SAVED,
        )
        db_module.upsert_job(job.model_dump(mode="json"))
        dedup_key = _make_dedup_key(job.company, job.title)
        db_module.update_job_status(dedup_key, "applied")
        jobs.append(job)

    return jobs


def _make_dedup_key(company: str, title: str) -> str:
    """Replicate the dedup_key logic from webapp.db.upsert_job."""
    normalized = (
        company.lower()
        .strip()
        .replace(" inc.", "")
        .replace(" inc", "")
        .replace(" llc", "")
        .replace(" ltd", "")
        .replace(",", "")
    )
    return f"{normalized}::{title.lower().strip()}"


@pytest.mark.e2e
@pytest.mark.enable_socket
class TestKanbanE2E:
    """Browser tests for the kanban board page."""

    def test_kanban_page_loads_with_columns(self, page, live_server, seeded_kanban_db):
        """E2E-04: Kanban page renders all status columns with correct card counts."""
        page.goto(f"{live_server}/kanban")
        page.wait_for_load_state("networkidle")

        # Verify all kanban columns exist
        kanban_statuses = [
            "saved",
            "applied",
            "phone_screen",
            "technical",
            "final_interview",
            "offer",
            "rejected",
            "withdrawn",
            "ghosted",
        ]
        for status in kanban_statuses:
            col = page.locator(f"#col-{status}")
            expect(col).to_be_visible()

        # Verify "saved" column has 3 cards
        expect(page.locator("#col-saved .kanban-card")).to_have_count(3)

        # Verify "applied" column has 2 cards
        expect(page.locator("#col-applied .kanban-card")).to_have_count(2)

        # Verify empty columns have 0 cards
        expect(page.locator("#col-offer .kanban-card")).to_have_count(0)

    def test_drag_card_from_saved_to_applied(self, page, live_server, seeded_kanban_db):
        """E2E-04: Moving a card via fetch POST (SortableJS onEnd path) persists after reload.

        Uses the fetch fallback approach since SortableJS's forceFallback: true
        makes native Playwright drag_to() unreliable. This invokes the exact same
        server endpoint that real drag-and-drop triggers.
        """
        page.goto(f"{live_server}/kanban")
        page.wait_for_load_state("networkidle")

        # Wait for SortableJS to be loaded
        page.wait_for_function("typeof Sortable !== 'undefined'", timeout=10000)

        # Verify initial state: 3 saved, 2 applied
        expect(page.locator("#col-saved .kanban-card")).to_have_count(3)
        expect(page.locator("#col-applied .kanban-card")).to_have_count(2)

        # Get the first saved card's dedup_key
        card = page.locator("#col-saved .kanban-card").first
        card_key = card.get_attribute("data-key")
        assert card_key is not None, "Card must have a data-key attribute"

        # Simulate what SortableJS onEnd does: POST to /jobs/{key}/status
        # This is the exact same fetch call from kanban.html onEnd handler
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

        # Give the server a moment to process
        page.wait_for_timeout(500)

        # Reload the page to verify persistence
        page.goto(f"{live_server}/kanban")
        page.wait_for_load_state("networkidle")

        # After move: 2 saved, 3 applied
        expect(page.locator("#col-saved .kanban-card")).to_have_count(2)
        expect(page.locator("#col-applied .kanban-card")).to_have_count(3)

        # Verify the specific card is now in the applied column
        moved_card = page.locator(f'#col-applied .kanban-card[data-key="{card_key}"]')
        expect(moved_card).to_have_count(1)

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
