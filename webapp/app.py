"""Job Tracker Web Dashboard — FastAPI + htmx + SQLite."""

import asyncio
import csv
import io
import json
import logging
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates

from webapp import db

logger = logging.getLogger(__name__)

app = FastAPI(title="Job Tracker")


def _parse_score(value: str | None) -> int | None:
    """Convert a score query/form parameter to int, treating empty string as None."""
    if not value:
        return None
    try:
        return int(value)
    except Exception:
        return None


BASE_DIR = Path(__file__).parent
RESUMES_TAILORED_DIR = Path("resumes/tailored")
DEFAULT_RESUME_PATH = "resumes/Patryk_Golabek_Resume.pdf"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["parse_json"] = lambda s: (
    json.loads(s) if isinstance(s, str) and s else (s or {})
)
STATUSES = [
    "discovered",
    "scored",
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


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    q: str = Query(""),
    score: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    score_int = _parse_score(score)
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score_int,
        platform=platform if platform else None,
        status=status if status else None,
        sort_by=sort,
        sort_dir=dir,
    )
    stats = db.get_stats()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "jobs": jobs,
            "stats": stats,
            "statuses": STATUSES,
            "filters": {
                "q": q,
                "score": score_int,
                "platform": platform,
                "status": status,
                "sort": sort,
                "dir": dir,
            },
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search_jobs(
    request: Request,
    q: str = Query(""),
    score: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=_parse_score(score),
        platform=platform if platform else None,
        status=status if status else None,
        sort_by=sort,
        sort_dir=dir,
    )
    return templates.TemplateResponse(
        request,
        "partials/job_rows.html",
        {"jobs": jobs, "statuses": STATUSES},
    )


@app.post("/bulk/status", response_class=HTMLResponse)
async def bulk_status_update(
    request: Request,
    job_keys: Annotated[list[str] | None, Form()] = None,
    bulk_status: str = Form(""),
    q: str = Form(""),
    score: str | None = Form(None),
    platform: str | None = Form(None),
    status: str | None = Form(None),
    sort: str = Form("score"),
    dir: str = Form("desc"),
):
    if job_keys is None:
        job_keys = []
    if bulk_status and job_keys:
        for key in job_keys:
            db.update_job_status(key, bulk_status)
    # Re-fetch with current filters and return updated table body
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=_parse_score(score),
        platform=platform if platform else None,
        status=status if status else None,
        sort_by=sort,
        sort_dir=dir,
    )
    return templates.TemplateResponse(
        request,
        "partials/job_rows.html",
        {"jobs": jobs, "statuses": STATUSES},
    )


@app.get("/export/csv")
async def export_csv(
    q: str = Query(""),
    score: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=_parse_score(score),
        platform=platform if platform else None,
        status=status if status else None,
        sort_by=sort,
        sort_dir=dir,
    )
    output = io.StringIO()
    fields = [
        "title",
        "company",
        "location",
        "salary_display",
        "platform",
        "status",
        "score",
        "url",
        "posted_date",
        "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        writer.writerow(job)
    output.seek(0)
    filename = f"jobs_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/json")
async def export_json(
    q: str = Query(""),
    score: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=_parse_score(score),
        platform=platform if platform else None,
        status=status if status else None,
        sort_by=sort,
        sort_dir=dir,
    )
    fields = [
        "title",
        "company",
        "location",
        "salary_display",
        "platform",
        "status",
        "score",
        "url",
        "apply_url",
        "posted_date",
        "created_at",
        "notes",
    ]
    export_data = [{k: job.get(k) for k in fields} for job in jobs]
    output = json.dumps(export_data, indent=2)
    filename = f"jobs_export_{date.today().isoformat()}.json"
    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Resume AI endpoints (must be registered BEFORE the catch-all /jobs/{path} GET)
# ---------------------------------------------------------------------------

_resume_sessions: dict[str, asyncio.Queue] = {}
_resume_tasks: dict[str, asyncio.Task] = {}


async def _run_resume_tailor(
    dedup_key: str, job: dict, resume_path: str, queue: asyncio.Queue
) -> None:
    """Background task: run the full resume tailoring pipeline with SSE progress events."""
    from resume_ai.diff import generate_resume_diff_html, wrap_diff_html
    from resume_ai.extractor import extract_resume_text
    from resume_ai.renderer import render_resume_pdf as _render_resume_pdf
    from resume_ai.tailor import format_resume_as_text, tailor_resume
    from resume_ai.tracker import save_resume_version as _save_resume_version
    from resume_ai.validator import validate_no_fabrication

    def _emit(event_type: str, message: str, html: str = "") -> None:
        queue.put_nowait({"type": event_type, "message": message, "html": html})

    try:
        # Stage 1: Extract resume text
        _emit("progress", "Extracting resume text...")
        resume_text = await asyncio.to_thread(extract_resume_text, resume_path)

        # Stage 2: Generate tailored resume via Claude CLI
        _emit("progress", "Generating tailored resume...")
        tailored = await tailor_resume(
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Stage 3: Validate (anti-fabrication)
        _emit("progress", "Validating for fabrication...")
        tailored_text = format_resume_as_text(tailored)
        validation = validate_no_fabrication(resume_text, tailored_text)

        # Stage 4: Render PDF
        _emit("progress", "Rendering PDF...")
        company_slug = job["company"].replace(" ", "_")[:30]
        filename = f"Patryk_Golabek_Resume_{company_slug}_{date.today().isoformat()}.pdf"
        RESUMES_TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_TAILORED_DIR / filename

        contact_info = "pgolabek@gmail.com | 416-708-9839 | Springwater, ON, Canada"
        await asyncio.to_thread(
            _render_resume_pdf, tailored, "Patryk Golabek", contact_info, output_path
        )

        # Save version and log activity (fast sync, ok inline)
        _save_resume_version(
            job_dedup_key=dedup_key,
            resume_type="resume",
            file_path=str(output_path),
            original_resume_path=str(resume_path),
            model_used="claude-sonnet-4-5-20250929",
        )
        db.log_activity(
            dedup_key, "resume_tailored", detail=f"Generated tailored resume: {filename}"
        )

        # Build final result HTML (pre-render the diff partial)
        diff_html = generate_resume_diff_html(resume_text, tailored_text)
        diff_styled = wrap_diff_html(diff_html)
        result_html = templates.get_template("partials/resume_diff.html").render(
            diff_html=diff_styled,
            download_url=f"/resumes/tailored/{filename}",
            tailoring_notes=tailored.tailoring_notes,
            filename=filename,
            validation_valid=validation.is_valid,
            validation_warnings=validation.warnings,
        )

        _emit("done", "Resume tailored successfully", html=result_html)

    except asyncio.CancelledError:
        _emit("done", "Generation cancelled")
        raise
    except Exception as exc:
        logger.exception("Resume tailoring failed for %s", dedup_key)
        _emit("error", f"Resume tailoring failed: {exc}")
        _emit("done", "")


@app.post("/jobs/{dedup_key:path}/tailor-resume", response_class=HTMLResponse)
async def tailor_resume_endpoint(request: Request, dedup_key: str):
    """Trigger resume tailoring via SSE -- returns an SSE-connect div immediately."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    # Double-click protection
    if dedup_key in _resume_sessions:
        return HTMLResponse(
            '<div class="bg-yellow-50 border border-yellow-300 text-yellow-800'
            ' px-4 py-3 rounded">'
            '<p class="text-sm font-medium">Resume generation already in progress...</p>'
            "</div>"
        )

    # Resolve resume path
    resume_path = DEFAULT_RESUME_PATH
    try:
        from config import get_settings

        settings = get_settings()
        if settings.candidate_resume_path:
            resume_path = settings.candidate_resume_path
    except Exception:
        pass  # Fall back to default

    # Create queue and start background task
    queue: asyncio.Queue = asyncio.Queue()
    _resume_sessions[dedup_key] = queue
    task = asyncio.create_task(_run_resume_tailor(dedup_key, job, resume_path, queue))
    _resume_tasks[dedup_key] = task

    # Return SSE-connect HTML
    encoded_key = urllib.parse.quote(dedup_key, safe="")
    return HTMLResponse(
        f'<div hx-ext="sse"'
        f' sse-connect="/jobs/{encoded_key}/tailor-resume/stream"'
        f' sse-swap="progress"'
        f' sse-close="done">'
        f'  <div class="flex items-center gap-2 py-2">'
        f'    <div class="animate-spin h-4 w-4 border-2 border-indigo-500'
        f' border-t-transparent rounded-full"></div>'
        f'    <span class="text-sm text-gray-500">Starting resume tailoring...</span>'
        f"  </div>"
        f"</div>"
    )


@app.get("/jobs/{dedup_key:path}/tailor-resume/stream")
async def resume_tailor_stream(request: Request, dedup_key: str):
    """SSE endpoint streaming real-time resume tailoring progress."""
    from sse_starlette import EventSourceResponse

    queue = _resume_sessions.get(dedup_key)
    if queue is None:
        return HTMLResponse(
            "<p class='text-red-600 text-sm'>No active resume session</p>",
            status_code=404,
        )

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    event_type = event.get("type", "progress")
                    html = templates.get_template("partials/resume_tailor_status.html").render(
                        event=event, dedup_key=dedup_key
                    )
                    yield {"event": event_type, "data": html}
                    if event_type == "done":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            _resume_sessions.pop(dedup_key, None)
            task = _resume_tasks.pop(dedup_key, None)
            if task and not task.done():
                task.cancel()

    return EventSourceResponse(event_generator())


_cover_sessions: dict[str, asyncio.Queue] = {}
_cover_tasks: dict[str, asyncio.Task] = {}


async def _run_cover_letter(
    dedup_key: str, job: dict, resume_path: str, queue: asyncio.Queue
) -> None:
    """Background task: run the full cover letter pipeline with SSE progress events."""
    from resume_ai.cover_letter import format_cover_letter_as_text, generate_cover_letter
    from resume_ai.extractor import extract_resume_text
    from resume_ai.renderer import render_cover_letter_pdf as _render_cover_letter_pdf
    from resume_ai.tracker import save_resume_version as _save_cover_version

    def _emit(event_type: str, message: str, html: str = "") -> None:
        queue.put_nowait({"type": event_type, "message": message, "html": html})

    try:
        # Stage 1: Extract resume text
        _emit("progress", "Extracting resume text...")
        resume_text = await asyncio.to_thread(extract_resume_text, resume_path)

        # Stage 2: Generate cover letter via Claude CLI
        _emit("progress", "Generating cover letter...")
        letter = await generate_cover_letter(
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Stage 3: Render PDF
        _emit("progress", "Rendering PDF...")
        company_slug = job["company"].replace(" ", "_")[:30]
        filename = f"Patryk_Golabek_CoverLetter_{company_slug}_{date.today().isoformat()}.pdf"
        RESUMES_TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_TAILORED_DIR / filename

        await asyncio.to_thread(
            _render_cover_letter_pdf,
            letter,
            "Patryk Golabek",
            "pgolabek@gmail.com",
            "416-708-9839",
            output_path,
        )

        # Save version and log activity (fast sync, ok inline)
        _save_cover_version(
            job_dedup_key=dedup_key,
            resume_type="cover_letter",
            file_path=str(output_path),
            original_resume_path=str(resume_path),
            model_used="claude-sonnet-4-5-20250929",
        )
        db.log_activity(
            dedup_key, "cover_letter_generated", detail=f"Generated cover letter: {filename}"
        )

        # Build final result HTML
        letter_preview = format_cover_letter_as_text(letter, "Patryk Golabek")
        result_html = templates.get_template("partials/cover_letter_result.html").render(
            download_url=f"/resumes/tailored/{filename}",
            filename=filename,
            letter_preview=letter_preview,
        )

        _emit("done", "Cover letter generated successfully", html=result_html)

    except asyncio.CancelledError:
        _emit("done", "Generation cancelled")
        raise
    except Exception as exc:
        logger.exception("Cover letter generation failed for %s", dedup_key)
        _emit("error", f"Cover letter generation failed: {exc}")
        _emit("done", "")


@app.post("/jobs/{dedup_key:path}/cover-letter", response_class=HTMLResponse)
async def cover_letter_endpoint(request: Request, dedup_key: str):
    """Trigger cover letter generation via SSE -- returns an SSE-connect div immediately."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    # Double-click protection
    if dedup_key in _cover_sessions:
        return HTMLResponse(
            '<div class="text-sm text-amber-700 bg-amber-50 border border-amber-300'
            ' px-4 py-3 rounded">'
            "Cover letter generation already in progress..."
            "</div>"
        )

    # Resolve resume path
    resume_path = DEFAULT_RESUME_PATH
    try:
        from config import get_settings

        settings = get_settings()
        if settings.candidate_resume_path:
            resume_path = settings.candidate_resume_path
    except Exception:
        pass  # Fall back to default

    # Create queue and start background task
    queue: asyncio.Queue = asyncio.Queue()
    _cover_sessions[dedup_key] = queue
    task = asyncio.create_task(_run_cover_letter(dedup_key, job, resume_path, queue))
    _cover_tasks[dedup_key] = task

    # Return SSE-connect HTML
    encoded_key = urllib.parse.quote(dedup_key, safe="")
    return HTMLResponse(
        f'<div hx-ext="sse"'
        f' sse-connect="/jobs/{encoded_key}/cover-letter/stream"'
        f' sse-swap="progress"'
        f' sse-close="done">'
        f'  <div class="flex items-center gap-2 py-2">'
        f'    <div class="animate-spin h-4 w-4 border-2 border-emerald-500'
        f' border-t-transparent rounded-full"></div>'
        f'    <span class="text-sm text-gray-500">Starting cover letter generation...</span>'
        f"  </div>"
        f"</div>"
    )


@app.get("/jobs/{dedup_key:path}/cover-letter/stream")
async def cover_letter_stream(request: Request, dedup_key: str):
    """SSE endpoint streaming real-time cover letter generation progress."""
    from sse_starlette import EventSourceResponse

    queue = _cover_sessions.get(dedup_key)
    if queue is None:
        return HTMLResponse(
            "<p class='text-red-600 text-sm'>No active cover letter session</p>",
            status_code=404,
        )

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    event_type = event.get("type", "progress")
                    html = templates.get_template("partials/cover_letter_status.html").render(
                        event=event, dedup_key=dedup_key
                    )
                    yield {"event": event_type, "data": html}
                    if event_type == "done":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            _cover_sessions.pop(dedup_key, None)
            task = _cover_tasks.pop(dedup_key, None)
            if task and not task.done():
                task.cancel()

    return EventSourceResponse(event_generator())


@app.post("/jobs/{dedup_key:path}/ai-rescore", response_class=HTMLResponse)
async def ai_rescore_endpoint(request: Request, dedup_key: str):
    """Score a job using AI semantic analysis via Claude CLI."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    # Guard: description must be substantial enough for analysis
    description = job.get("description") or ""
    if len(description.strip()) < 50:
        return HTMLResponse(
            '<div class="bg-yellow-50 border border-yellow-400 text-yellow-800 px-4 py-3 rounded">'
            '<p class="font-bold">Cannot analyze</p>'
            '<p class="text-sm">Job description is too short for AI analysis. '
            "Try refreshing the job listing first.</p>"
            "</div>"
        )

    try:
        from ai_scorer import score_job_ai
        from resume_ai.extractor import extract_resume_text

        # Resolve resume path (same pattern as tailor_resume_endpoint)
        resume_path = DEFAULT_RESUME_PATH
        try:
            from config import get_settings

            settings = get_settings()
            if settings.candidate_resume_path:
                resume_path = settings.candidate_resume_path
        except Exception:
            pass

        resume_text = extract_resume_text(resume_path)

        # Call AI scorer (natively async via claude_cli)
        result = await score_job_ai(
            resume_text=resume_text,
            job_description=description,
            job_title=job["title"],
            company_name=job["company"],
        )

        # Persist to database
        breakdown = {
            "reasoning": result.reasoning,
            "strengths": result.strengths,
            "gaps": result.gaps,
        }
        db.update_ai_score(dedup_key, result.score, breakdown)

        # Return htmx partial
        return templates.TemplateResponse(
            request,
            "partials/ai_score_result.html",
            {
                "score": result.score,
                "reasoning": result.reasoning,
                "strengths": result.strengths,
                "gaps": result.gaps,
                "scored_at": "just now",
            },
        )

    except Exception as exc:
        logger.exception("AI scoring failed for %s", dedup_key)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-400 text-red-800 px-4 py-3 rounded">'
            f'<p class="font-bold">AI Scoring Error</p>'
            f'<p class="text-sm">{exc}</p>'
            f"</div>"
        )


@app.get("/resumes/tailored/{filename:path}")
async def serve_tailored_resume(filename: str):
    """Serve a generated resume or cover letter PDF for download."""
    file_path = RESUMES_TAILORED_DIR / filename
    if not file_path.exists():
        return HTMLResponse("<h1>File not found</h1>", status_code=404)
    return FileResponse(str(file_path), media_type="application/pdf", filename=filename)


@app.get("/jobs/{dedup_key:path}/resume-versions", response_class=HTMLResponse)
async def resume_versions_endpoint(request: Request, dedup_key: str):
    """Return a partial listing resume versions for a job."""
    from resume_ai.tracker import get_versions_for_job as _get_versions

    versions = _get_versions(dedup_key)
    return templates.TemplateResponse(
        request,
        "partials/resume_versions.html",
        {"versions": versions},
    )


# ---------------------------------------------------------------------------
# Apply engine endpoints (must be registered BEFORE the catch-all /jobs/{path} GET)
# ---------------------------------------------------------------------------

# Lazy-init apply engine (avoid import errors if playwright not installed)
_apply_engine = None


def _get_apply_engine():
    global _apply_engine
    if _apply_engine is None:
        from apply_engine.engine import ApplyEngine

        _apply_engine = ApplyEngine()
    return _apply_engine


async def _run_apply(job: dict, mode: str, queue: asyncio.Queue):
    """Background task: run apply engine and catch errors."""
    engine = _get_apply_engine()
    try:
        await engine.apply(job, mode, queue)
    except Exception as exc:
        from apply_engine.events import ApplyEvent, ApplyEventType

        await queue.put(ApplyEvent(type=ApplyEventType.ERROR, message=str(exc)).model_dump())
        await queue.put(ApplyEvent(type=ApplyEventType.DONE, message="Apply failed").model_dump())


@app.post("/jobs/{dedup_key:path}/apply", response_class=HTMLResponse)
async def trigger_apply(request: Request, dedup_key: str, mode: str = Form("")):
    """Trigger the apply engine for a job, returning SSE connection HTML."""
    # Default mode from settings
    if not mode:
        try:
            from config import get_settings

            mode = get_settings().apply.default_mode.value
        except Exception:
            mode = "semi_auto"

    # Check duplicate
    from apply_engine.dedup import is_already_applied

    already = is_already_applied(dedup_key)
    if already:
        status_label = already.get("status", "unknown").replace("_", " ").title()
        return HTMLResponse(
            f'<div class="bg-yellow-50 border border-yellow-300 text-yellow-800 px-4 py-3 rounded">'
            f'<p class="text-sm font-medium">Already applied</p>'
            f'<p class="text-sm">This job has status: {status_label}</p>'
            f"</div>"
        )

    # Get job
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<p class='text-red-600 text-sm'>Job not found</p>", status_code=404)

    # Create queue and register session
    queue = asyncio.Queue()
    engine = _get_apply_engine()
    engine._sessions[dedup_key] = queue

    # Start background task
    asyncio.create_task(_run_apply(job, mode, queue))

    # Return HTML that establishes SSE connection
    encoded_key = urllib.parse.quote(dedup_key, safe="")
    return HTMLResponse(
        f'<div hx-ext="sse"'
        f' sse-connect="/jobs/{encoded_key}/apply/stream"'
        f' sse-swap="progress"'
        f' sse-close="done">'
        f'  <div id="apply-live-status">'
        f'    <p class="text-sm text-gray-500">Connecting to apply engine...</p>'
        f"  </div>"
        f"</div>"
    )


@app.get("/jobs/{dedup_key:path}/apply/stream")
async def apply_stream(request: Request, dedup_key: str):
    """SSE endpoint streaming real-time apply progress events."""
    from sse_starlette import EventSourceResponse

    engine = _get_apply_engine()
    queue = engine.get_session_queue(dedup_key)
    if queue is None:
        return HTMLResponse(
            "<p class='text-red-600 text-sm'>No active apply session</p>", status_code=404
        )

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    event_type = event.get("type", "progress")
                    html = templates.get_template("partials/apply_status.html").render(
                        event=event, dedup_key=dedup_key
                    )
                    yield {"event": event_type, "data": html}
                    if event_type == "done":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())


@app.post("/jobs/{dedup_key:path}/apply/confirm", response_class=HTMLResponse)
async def apply_confirm(dedup_key: str):
    """Confirm an apply that is awaiting user confirmation."""
    _get_apply_engine().confirm(dedup_key)
    return HTMLResponse(
        '<p class="text-sm text-green-600">Confirmed -- submitting application...</p>'
    )


@app.post("/jobs/{dedup_key:path}/apply/cancel", response_class=HTMLResponse)
async def apply_cancel(dedup_key: str):
    """Cancel an active apply session."""
    _get_apply_engine().cancel(dedup_key)
    return HTMLResponse('<p class="text-sm text-yellow-600">Apply cancelled.</p>')


@app.get("/jobs/{dedup_key:path}", response_class=HTMLResponse)
async def job_detail(request: Request, dedup_key: str):
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    # Mark as viewed on first access (removes NEW badge on next dashboard load)
    if job.get("viewed_at") is None:
        db.mark_viewed(dedup_key)
        db.log_activity(dedup_key, "viewed")

    activity = db.get_activity_log(dedup_key)

    return templates.TemplateResponse(
        request,
        "job_detail.html",
        {
            "job": job,
            "statuses": STATUSES,
            "activity": activity,
        },
    )


@app.post("/jobs/{dedup_key:path}/status")
async def update_status(dedup_key: str, status: str = Form(...)):
    db.update_job_status(dedup_key, status)
    label = status.replace("_", " ").title()
    response = HTMLResponse(f'<span class="status-badge status-{status}">{label}</span>')
    response.headers["HX-Trigger"] = "statsChanged"
    return response


@app.post("/jobs/{dedup_key:path}/notes")
async def update_notes(dedup_key: str, notes: str = Form(...)):
    db.update_job_notes(dedup_key, notes)
    return HTMLResponse('<span class="text-green-600 text-sm">Saved</span>')


@app.post("/import")
async def import_jobs():
    pipeline_dir = Path(__file__).parent.parent / "job_pipeline"
    count = 0

    # Import discovered_jobs.json (scored)
    scored_path = pipeline_dir / "discovered_jobs.json"
    if scored_path.exists():
        data = json.loads(scored_path.read_text())
        count += db.upsert_jobs(data)

    # Also import raw files for any unscored jobs
    for name in ("raw_indeed.json", "raw_dice.json", "raw_remoteok.json"):
        raw_path = pipeline_dir / name
        if raw_path.exists():
            data = json.loads(raw_path.read_text())
            count += db.upsert_jobs(data)

    return RedirectResponse(url="/?imported=" + str(count), status_code=303)


@app.get("/runs", response_class=HTMLResponse)
async def run_history(request: Request):
    runs = db.get_run_history(limit=50)
    return templates.TemplateResponse(
        request,
        "run_history.html",
        {"runs": runs},
    )


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {
            "stats": stats,
            "enhanced_stats": enhanced,
            "analytics_json": json.dumps(enhanced),
        },
    )


@app.get("/api/analytics")
async def analytics_api():
    enhanced = db.get_enhanced_stats()
    return JSONResponse(content=enhanced)


KANBAN_STATUSES = [
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

TERMINAL_STATUSES = {"rejected", "withdrawn", "ghosted"}

STATUS_COLORS: dict[str, dict[str, str]] = {
    "saved": {
        "dot": "bg-slate-400",
        "hex": "#94a3b8",
        "badge_bg": "bg-slate-100",
        "badge_text": "text-slate-700",
    },
    "applied": {
        "dot": "bg-blue-500",
        "hex": "#3b82f6",
        "badge_bg": "bg-blue-100",
        "badge_text": "text-blue-700",
    },
    "phone_screen": {
        "dot": "bg-amber-500",
        "hex": "#f59e0b",
        "badge_bg": "bg-amber-100",
        "badge_text": "text-amber-700",
    },
    "technical": {
        "dot": "bg-orange-500",
        "hex": "#f97316",
        "badge_bg": "bg-orange-100",
        "badge_text": "text-orange-700",
    },
    "final_interview": {
        "dot": "bg-pink-500",
        "hex": "#ec4899",
        "badge_bg": "bg-pink-100",
        "badge_text": "text-pink-700",
    },
    "offer": {
        "dot": "bg-emerald-500",
        "hex": "#10b981",
        "badge_bg": "bg-emerald-100",
        "badge_text": "text-emerald-700",
    },
    "rejected": {
        "dot": "bg-red-400",
        "hex": "#f87171",
        "badge_bg": "bg-red-50",
        "badge_text": "text-red-600",
    },
    "withdrawn": {
        "dot": "bg-gray-400",
        "hex": "#9ca3af",
        "badge_bg": "bg-gray-100",
        "badge_text": "text-gray-600",
    },
    "ghosted": {
        "dot": "bg-violet-400",
        "hex": "#a78bfa",
        "badge_bg": "bg-violet-50",
        "badge_text": "text-violet-600",
    },
}

SCORE_CLASSES: dict[int, str] = {
    5: "text-emerald-600 font-bold",
    4: "text-blue-600 font-bold",
    3: "text-gray-500 font-semibold",
    2: "text-gray-400",
    1: "text-gray-300",
}

PLATFORM_BADGE_CLASSES: dict[str, str] = {
    "indeed": "bg-indigo-50 text-indigo-600",
    "dice": "bg-teal-50 text-teal-600",
    "remoteok": "bg-amber-50 text-amber-600",
}


@app.get("/kanban", response_class=HTMLResponse)
async def kanban_page(request: Request):
    columns: dict[str, list[dict]] = {}
    for status in KANBAN_STATUSES:
        columns[status] = db.get_jobs(status=status, sort_by="score", sort_dir="desc")
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        request,
        "kanban.html",
        {
            "kanban_statuses": KANBAN_STATUSES,
            "columns": columns,
            "stats": stats,
            "enhanced_stats": enhanced,
            "statuses": STATUSES,
            "status_colors": STATUS_COLORS,
            "score_classes": SCORE_CLASSES,
            "platform_badge_classes": PLATFORM_BADGE_CLASSES,
            "terminal_statuses": TERMINAL_STATUSES,
        },
    )


@app.get("/api/stats-cards", response_class=HTMLResponse)
async def stats_cards(request: Request):
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        {
            "stats": stats,
            "enhanced_stats": enhanced,
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run("webapp.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
