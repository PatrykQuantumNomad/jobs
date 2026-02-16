"""Apply engine -- orchestrates apply flows in a background thread with event emission.

Runs Playwright-based or external ATS apply flows in a background thread while
emitting real-time progress events to an ``asyncio.Queue`` consumed by the
dashboard via Server-Sent Events.

Thread safety: ``loop.call_soon_threadsafe(queue.put_nowait, event)`` bridges
the synchronous Playwright thread to the asynchronous FastAPI event loop.
"""

import asyncio
import contextlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from apply_engine.config import ApplyMode
from apply_engine.dedup import is_already_applied
from apply_engine.events import ApplyEvent, ApplyEventType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ApplyEngine:
    """Orchestrates apply flows in a background thread, emitting events to an async queue."""

    def __init__(self, settings=None) -> None:
        # Lazy-load settings from config.get_settings() if not provided
        if settings is None:
            from core.config import get_settings

            self._settings = get_settings()
        else:
            self._settings = settings

        # Semaphore(1) for apply serialization -- only one apply at a time
        self._semaphore = asyncio.Semaphore(1)

        # Active sessions: dedup_key -> event queue
        self._sessions: dict[str, asyncio.Queue] = {}

        # Confirmation events: dedup_key -> threading.Event (for dashboard confirm)
        self._confirmations: dict[str, threading.Event] = {}

    # ── Public async API ──────────────────────────────────────────────────

    async def apply(self, job: dict, mode: str, queue: asyncio.Queue) -> None:
        """Start an apply flow for *job*, emitting events to *queue*.

        Acquires the semaphore so only one apply runs at a time.
        Delegates to ``_apply_sync`` in a background thread.
        """
        dedup_key = job.get("dedup_key", "")
        try:
            async with self._semaphore:
                # Register session
                self._sessions[dedup_key] = queue
                self._confirmations[dedup_key] = threading.Event()

                # Check duplicate
                already = is_already_applied(dedup_key)
                if already:
                    self._emit_sync(
                        queue,
                        ApplyEvent(
                            type=ApplyEventType.ERROR,
                            message=(
                                f"Already applied to this job"
                                f" (status: {already.get('status', 'unknown')})"
                            ),
                            job_dedup_key=dedup_key,
                        ),
                    )
                    return

                # Thread-safe emitter: capture running event loop
                loop = asyncio.get_running_loop()
                emit = self._make_emitter(queue, loop)

                # Run synchronous apply in background thread
                await asyncio.to_thread(self._apply_sync, job, mode, emit)
        except Exception as exc:
            logger.exception("Apply flow failed for %s", dedup_key)
            self._emit_sync(
                queue,
                ApplyEvent(
                    type=ApplyEventType.ERROR,
                    message=f"Apply failed: {exc}",
                    job_dedup_key=dedup_key,
                ),
            )
        finally:
            # Cleanup
            self._sessions.pop(dedup_key, None)
            self._confirmations.pop(dedup_key, None)
            self._emit_sync(
                queue,
                ApplyEvent(
                    type=ApplyEventType.DONE,
                    message="Apply flow complete",
                    job_dedup_key=dedup_key,
                ),
            )

    # ── Emitter factory ──────────────────────────────────────────────────

    def _make_emitter(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> Callable:
        """Return a function that safely emits events from a background thread.

        Uses ``loop.call_soon_threadsafe()`` to bridge the sync thread to the
        async event loop without blocking.
        """

        def emit(event: ApplyEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event.model_dump())

        return emit

    @staticmethod
    def _emit_sync(queue: asyncio.Queue, event: ApplyEvent) -> None:
        """Emit an event from the async context (not from background thread)."""
        with contextlib.suppress(Exception):
            queue.put_nowait(event.model_dump())

    # ── Synchronous apply (runs in background thread) ─────────────────

    def _apply_sync(self, job: dict, mode: str, emit: Callable) -> None:
        """Execute the apply flow synchronously in a background thread.

        Determines platform, resolves resume, and dispatches to the
        appropriate apply method (browser or external form).
        """
        dedup_key = job.get("dedup_key", "")
        platform_name = job.get("platform", "")

        try:
            # Log start
            try:
                from webapp.db import log_activity

                log_activity(dedup_key, "apply_started", detail=f"mode={mode}")
            except Exception:
                pass

            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message=(
                        f"Starting apply for {job.get('title', '?')}"
                        f" at {job.get('company', '?')}..."
                    ),
                    job_dedup_key=dedup_key,
                )
            )

            # Resolve resume path
            resume_path = self._get_resume_path(dedup_key)
            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message=f"Using resume: {resume_path.name}",
                    job_dedup_key=dedup_key,
                )
            )

            # Get platform info from registry
            from platforms.registry import get_platform

            try:
                platform_info = get_platform(platform_name)
            except KeyError:
                emit(
                    ApplyEvent(
                        type=ApplyEventType.ERROR,
                        message=f"Unknown platform: {platform_name}",
                        job_dedup_key=dedup_key,
                    )
                )
                return

            # API platform (e.g., remoteok) -- use external form fill
            if platform_info.platform_type == "api":
                emit(
                    ApplyEvent(
                        type=ApplyEventType.PROGRESS,
                        message="External ATS application flow...",
                        job_dedup_key=dedup_key,
                    )
                )
                self._fill_external_form(job, mode, emit)
                return

            # Browser platform (indeed, dice)
            self._apply_browser(job, mode, emit, platform_info, resume_path)

        except Exception as exc:
            logger.exception("Error in _apply_sync for %s", dedup_key)
            emit(
                ApplyEvent(
                    type=ApplyEventType.ERROR,
                    message=f"Apply error: {exc}",
                    job_dedup_key=dedup_key,
                )
            )
            try:
                from webapp.db import log_activity

                log_activity(dedup_key, "apply_failed", detail=str(exc))
            except Exception:
                pass

    def _apply_browser(
        self,
        job: dict,
        mode: str,
        emit: Callable,
        platform_info,
        resume_path: Path,
    ) -> None:
        """Apply via browser automation (Indeed, Dice)."""
        from platforms.stealth import close_browser, get_browser_context

        dedup_key = job.get("dedup_key", "")
        apply_cfg = self._settings.apply
        pw = None
        ctx = None

        try:
            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message="Launching browser...",
                    job_dedup_key=dedup_key,
                )
            )

            pw, ctx = get_browser_context(platform_info.key, headless=not apply_cfg.headed_mode)

            # Create platform instance and init
            platform = platform_info.cls()
            platform.init(ctx)

            # Set dashboard mode attributes for event-based confirmation
            platform._confirmation_event = self._confirmations.get(dedup_key)
            platform._dashboard_mode = True

            # Check login
            if not platform.is_logged_in():
                emit(
                    ApplyEvent(
                        type=ApplyEventType.PROGRESS,
                        message="Logging in...",
                        job_dedup_key=dedup_key,
                    )
                )
                platform.login()
                if not platform.is_logged_in():
                    emit(
                        ApplyEvent(
                            type=ApplyEventType.ERROR,
                            message="Login failed -- cannot proceed with apply",
                            job_dedup_key=dedup_key,
                        )
                    )
                    return

            # Check easy_apply mode constraint
            if mode == ApplyMode.EASY_APPLY_ONLY and not job.get("easy_apply"):
                emit(
                    ApplyEvent(
                        type=ApplyEventType.ERROR,
                        message="Job does not support Easy Apply (mode: easy_apply_only)",
                        job_dedup_key=dedup_key,
                    )
                )
                return

            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message="Navigating to job page...",
                    job_dedup_key=dedup_key,
                )
            )

            # Screenshot before submit
            if apply_cfg.screenshot_before_submit:
                try:
                    screenshot_path = platform.screenshot("pre_apply")
                    emit(
                        ApplyEvent(
                            type=ApplyEventType.PROGRESS,
                            message="Pre-apply screenshot captured",
                            screenshot_path=str(screenshot_path),
                            job_dedup_key=dedup_key,
                        )
                    )
                except Exception:
                    pass

            # Confirm before submit
            if apply_cfg.confirm_before_submit:
                emit(
                    ApplyEvent(
                        type=ApplyEventType.AWAITING_CONFIRM,
                        message=(
                            f"Ready to apply for {job.get('title', '?')}"
                            f" at {job.get('company', '?')}. Confirm?"
                        ),
                        job_dedup_key=dedup_key,
                    )
                )
                confirmed = platform.wait_for_confirmation(
                    "Ready to submit application?", timeout=300
                )
                if not confirmed:
                    emit(
                        ApplyEvent(
                            type=ApplyEventType.ERROR,
                            message="Confirmation timed out",
                            job_dedup_key=dedup_key,
                        )
                    )
                    return
                emit(
                    ApplyEvent(
                        type=ApplyEventType.CONFIRMED,
                        message="User confirmed -- submitting application",
                        job_dedup_key=dedup_key,
                    )
                )

            # Build Job model from dict for platform.apply()
            from core.models import Job

            job_model = Job(**{k: v for k, v in job.items() if k in Job.model_fields})
            result = platform.apply(job_model, resume_path)

            if result:
                emit(
                    ApplyEvent(
                        type=ApplyEventType.PROGRESS,
                        message="Application submitted successfully!",
                        job_dedup_key=dedup_key,
                    )
                )
                try:
                    from webapp.db import log_activity

                    log_activity(dedup_key, "apply_completed")
                except Exception:
                    pass
            else:
                emit(
                    ApplyEvent(
                        type=ApplyEventType.ERROR,
                        message="Application submission returned failure",
                        job_dedup_key=dedup_key,
                    )
                )

        finally:
            if pw and ctx:
                close_browser(pw, ctx)

    def _fill_external_form(self, job: dict, mode: str, emit: Callable) -> None:
        """Handle external ATS apply (e.g., RemoteOK jobs with apply_url)."""
        dedup_key = job.get("dedup_key", "")
        apply_url = job.get("apply_url") or job.get("url", "")
        apply_cfg = self._settings.apply

        if not apply_cfg.ats_form_fill_enabled:
            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message=f"ATS form fill disabled. Apply manually: {apply_url}",
                    job_dedup_key=dedup_key,
                )
            )
            return

        from platforms.stealth import close_browser, get_browser_context

        pw = None
        ctx = None
        try:
            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message=f"Opening external ATS: {apply_url}",
                    job_dedup_key=dedup_key,
                )
            )

            pw, ctx = get_browser_context("ats_form", headless=not apply_cfg.headed_mode)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(apply_url, timeout=apply_cfg.ats_form_fill_timeout * 1000)

            # Fill form
            from core.form_filler import FormFiller

            filler = FormFiller()
            resume_path = self._get_resume_path(dedup_key)
            fields_filled = filler.fill_form(page, resume_path)

            emit(
                ApplyEvent(
                    type=ApplyEventType.PROGRESS,
                    message=f"Filled {len(fields_filled)} form fields",
                    fields_filled=fields_filled,
                    job_dedup_key=dedup_key,
                )
            )

            # Confirm before submit
            if apply_cfg.confirm_before_submit:
                emit(
                    ApplyEvent(
                        type=ApplyEventType.AWAITING_CONFIRM,
                        message=(
                            f"External form filled for {job.get('title', '?')}. Confirm submit?"
                        ),
                        job_dedup_key=dedup_key,
                    )
                )
                # Wait via threading.Event directly (already in sync context)
                confirmation_event = self._confirmations.get(dedup_key)
                if confirmation_event:
                    confirmed = confirmation_event.wait(timeout=300)
                    if not confirmed:
                        emit(
                            ApplyEvent(
                                type=ApplyEventType.ERROR,
                                message="Confirmation timed out",
                                job_dedup_key=dedup_key,
                            )
                        )
                        return

            # Screenshot
            if apply_cfg.screenshot_before_submit:
                try:
                    from datetime import datetime

                    from core.config import DEBUG_SCREENSHOTS_DIR

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_file = (
                        DEBUG_SCREENSHOTS_DIR / f"ats_{dedup_key[:20]}_{timestamp}.png"
                    )
                    page.screenshot(path=str(screenshot_file), full_page=True)
                    emit(
                        ApplyEvent(
                            type=ApplyEventType.PROGRESS,
                            message="Form screenshot captured",
                            screenshot_path=str(screenshot_file),
                            job_dedup_key=dedup_key,
                        )
                    )
                except Exception:
                    pass

            try:
                from webapp.db import log_activity

                log_activity(dedup_key, "apply_completed", detail="external_ats")
            except Exception:
                pass

        except Exception as exc:
            logger.exception("External form fill failed for %s", dedup_key)
            emit(
                ApplyEvent(
                    type=ApplyEventType.ERROR,
                    message=f"External form fill error: {exc}",
                    job_dedup_key=dedup_key,
                )
            )
        finally:
            if pw and ctx:
                close_browser(pw, ctx)

    # ── Resume resolution ─────────────────────────────────────────────

    def _get_resume_path(self, dedup_key: str) -> Path:
        """Resolve resume path -- check for tailored version, fall back to default ATS."""
        try:
            from webapp.db import get_conn

            with get_conn() as conn:
                row = conn.execute(
                    """SELECT file_path FROM resume_versions
                       WHERE job_dedup_key = ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (dedup_key,),
                ).fetchone()

            if row:
                tailored = Path(row["file_path"])
                if tailored.exists():
                    return tailored
        except Exception:
            pass

        # Default ATS resume
        return Path(self._settings.candidate_resume_path)

    # ── Dashboard interaction ─────────────────────────────────────────

    def confirm(self, dedup_key: str) -> bool:
        """Confirm an apply that is awaiting user confirmation.

        Sets the threading.Event so the background thread proceeds.
        Returns True if session found and event set, False otherwise.
        """
        event = self._confirmations.get(dedup_key)
        if event is not None:
            event.set()
            return True
        return False

    def cancel(self, dedup_key: str) -> bool:
        """Cancel an active apply session.

        Emits a DONE event with cancellation message and cleans up.
        Returns True if session found, False otherwise.
        """
        queue = self._sessions.get(dedup_key)
        if queue is not None:
            self._emit_sync(
                queue,
                ApplyEvent(
                    type=ApplyEventType.DONE,
                    message="Application cancelled by user",
                    job_dedup_key=dedup_key,
                ),
            )
            # Set confirmation event to unblock waiting thread
            event = self._confirmations.get(dedup_key)
            if event is not None:
                event.set()
            self._sessions.pop(dedup_key, None)
            self._confirmations.pop(dedup_key, None)
            return True
        return False

    def get_session_queue(self, dedup_key: str) -> asyncio.Queue | None:
        """Return the active event queue for a session, or None."""
        return self._sessions.get(dedup_key)
