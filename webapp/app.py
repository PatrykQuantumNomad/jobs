"""Job Tracker Web Dashboard — FastAPI + htmx + SQLite."""

from __future__ import annotations

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp import db

logger = logging.getLogger(__name__)

app = FastAPI(title="Job Tracker")

BASE_DIR = Path(__file__).parent
RESUMES_TAILORED_DIR = Path("resumes/tailored")
DEFAULT_RESUME_PATH = "resumes/Patryk_Golabek_Resume_ATS.pdf"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["parse_json"] = lambda s: json.loads(s) if isinstance(s, str) and s else (s if s else {})
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

STATUSES = [
    "discovered", "scored", "saved", "applied",
    "phone_screen", "technical", "final_interview",
    "offer", "rejected", "withdrawn", "ghosted",
]


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    q: str = Query(""),
    score: int | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    stats = db.get_stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "jobs": jobs,
            "stats": stats,
            "statuses": STATUSES,
            "filters": {
                "q": q,
                "score": score,
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
    score: int | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    return templates.TemplateResponse(
        "partials/job_rows.html",
        {"request": request, "jobs": jobs, "statuses": STATUSES},
    )


@app.post("/bulk/status", response_class=HTMLResponse)
async def bulk_status_update(
    request: Request,
    job_keys: Annotated[list[str], Form()] = [],
    bulk_status: str = Form(""),
    q: str = Form(""),
    score: int | None = Form(None),
    platform: str | None = Form(None),
    status: str | None = Form(None),
    sort: str = Form("score"),
    dir: str = Form("desc"),
):
    if bulk_status and job_keys:
        for key in job_keys:
            db.update_job_status(key, bulk_status)
    # Re-fetch with current filters and return updated table body
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    return templates.TemplateResponse(
        "partials/job_rows.html",
        {"request": request, "jobs": jobs, "statuses": STATUSES},
    )


@app.get("/export/csv")
async def export_csv(
    q: str = Query(""),
    score: int | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    output = io.StringIO()
    fields = [
        "title", "company", "location", "salary_display", "platform",
        "status", "score", "url", "posted_date", "created_at",
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
    score: int | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("score"),
    dir: str = Query("desc"),
):
    jobs = db.get_jobs(
        search=q if q else None,
        score_min=score,
        platform=platform,
        status=status,
        sort_by=sort,
        sort_dir=dir,
    )
    fields = [
        "title", "company", "location", "salary_display", "platform",
        "status", "score", "url", "apply_url", "posted_date",
        "created_at", "notes",
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


@app.post("/jobs/{dedup_key:path}/tailor-resume", response_class=HTMLResponse)
async def tailor_resume_endpoint(request: Request, dedup_key: str):
    """Tailor the candidate's resume for a specific job posting via LLM."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    try:
        from resume_ai.extractor import extract_resume_text
        from resume_ai.tailor import tailor_resume, format_resume_as_text
        from resume_ai.diff import generate_resume_diff_html, wrap_diff_html
        from resume_ai.renderer import render_resume_pdf as _render_resume_pdf
        from resume_ai.tracker import save_resume_version as _save_resume_version
        from resume_ai.validator import validate_no_fabrication

        # Resolve resume path
        resume_path = DEFAULT_RESUME_PATH
        try:
            from config import get_settings
            settings = get_settings()
            if settings.candidate_resume_path:
                resume_path = settings.candidate_resume_path
        except Exception:
            pass  # Fall back to default

        # Extract original resume text
        resume_text = extract_resume_text(resume_path)

        # Call LLM via thread to avoid blocking the event loop
        tailored = await asyncio.to_thread(
            tailor_resume,
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Generate tailored text and diff
        tailored_text = format_resume_as_text(tailored)
        diff_html = generate_resume_diff_html(resume_text, tailored_text)
        diff_styled = wrap_diff_html(diff_html)

        # Run post-generation anti-fabrication validation
        validation = validate_no_fabrication(resume_text, tailored_text)

        # Generate PDF
        company_slug = job["company"].replace(" ", "_")[:30]
        filename = f"Patryk_Golabek_Resume_{company_slug}_{date.today().isoformat()}.pdf"
        RESUMES_TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_TAILORED_DIR / filename

        contact_info = "pgolabek@gmail.com | 416-708-9839 | Springwater, ON, Canada"
        _render_resume_pdf(tailored, "Patryk Golabek", contact_info, output_path)

        # Track version
        _save_resume_version(
            job_dedup_key=dedup_key,
            resume_type="resume",
            file_path=str(output_path),
            original_resume_path=str(resume_path),
            model_used="claude-sonnet-4-5-20250929",
        )

        # Log activity
        db.log_activity(dedup_key, "resume_tailored", detail=f"Generated tailored resume: {filename}")

        return templates.TemplateResponse(
            "partials/resume_diff.html",
            {
                "request": request,
                "diff_html": diff_styled,
                "download_url": f"/resumes/tailored/{filename}",
                "tailoring_notes": tailored.tailoring_notes,
                "filename": filename,
                "validation_valid": validation.is_valid,
                "validation_warnings": validation.warnings,
            },
        )

    except Exception as exc:
        logger.exception("Resume tailoring failed for %s", dedup_key)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-400 text-red-800 px-4 py-3 rounded">'
            f'<p class="font-bold">Error</p>'
            f'<p class="text-sm">{exc}</p>'
            f"</div>"
        )


@app.post("/jobs/{dedup_key:path}/cover-letter", response_class=HTMLResponse)
async def cover_letter_endpoint(request: Request, dedup_key: str):
    """Generate a cover letter for a specific job posting via LLM."""
    job = db.get_job(dedup_key)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)

    try:
        from resume_ai.extractor import extract_resume_text
        from resume_ai.cover_letter import generate_cover_letter
        from resume_ai.renderer import render_cover_letter_pdf as _render_cover_letter_pdf
        from resume_ai.tracker import save_resume_version as _save_cover_version

        # Resolve resume path
        resume_path = DEFAULT_RESUME_PATH
        try:
            from config import get_settings
            settings = get_settings()
            if settings.candidate_resume_path:
                resume_path = settings.candidate_resume_path
        except Exception:
            pass

        # Extract resume text
        resume_text = extract_resume_text(resume_path)

        # Call LLM via thread to avoid blocking
        letter = await asyncio.to_thread(
            generate_cover_letter,
            resume_text=resume_text,
            job_description=job["description"] or "",
            job_title=job["title"],
            company_name=job["company"],
        )

        # Generate PDF
        company_slug = job["company"].replace(" ", "_")[:30]
        filename = f"Patryk_Golabek_CoverLetter_{company_slug}_{date.today().isoformat()}.pdf"
        RESUMES_TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_TAILORED_DIR / filename

        _render_cover_letter_pdf(
            letter,
            candidate_name="Patryk Golabek",
            candidate_email="pgolabek@gmail.com",
            candidate_phone="416-708-9839",
            output_path=output_path,
        )

        # Track version
        _save_cover_version(
            job_dedup_key=dedup_key,
            resume_type="cover_letter",
            file_path=str(output_path),
            original_resume_path=str(resume_path),
            model_used="claude-sonnet-4-5-20250929",
        )

        # Log activity
        db.log_activity(dedup_key, "cover_letter_generated", detail=f"Generated cover letter: {filename}")

        return HTMLResponse(
            f'<div class="bg-green-50 border border-green-400 text-green-800 px-4 py-3 rounded mb-4">'
            f'<p class="text-sm font-medium">Cover letter generated successfully</p>'
            f"</div>"
            f'<a href="/resumes/tailored/{filename}" '
            f'class="inline-block bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700" '
            f"download>Download Cover Letter ({filename})</a>"
        )

    except Exception as exc:
        logger.exception("Cover letter generation failed for %s", dedup_key)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-400 text-red-800 px-4 py-3 rounded">'
            f'<p class="font-bold">Error</p>'
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
        "partials/resume_versions.html",
        {"request": request, "versions": versions},
    )


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
        "job_detail.html",
        {
            "request": request,
            "job": job,
            "statuses": STATUSES,
            "activity": activity,
        },
    )


@app.post("/jobs/{dedup_key:path}/status")
async def update_status(dedup_key: str, status: str = Form(...)):
    db.update_job_status(dedup_key, status)
    label = status.replace("_", " ").title()
    response = HTMLResponse(
        f'<span class="status-badge status-{status}">{label}</span>'
    )
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
        "run_history.html",
        {"request": request, "runs": runs},
    )


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
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
    "saved", "applied", "phone_screen", "technical",
    "final_interview", "offer", "rejected", "withdrawn", "ghosted",
]


@app.get("/kanban", response_class=HTMLResponse)
async def kanban_page(request: Request):
    columns: dict[str, list[dict]] = {}
    for status in KANBAN_STATUSES:
        columns[status] = db.get_jobs(status=status, sort_by="score", sort_dir="desc")
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        "kanban.html",
        {
            "request": request,
            "kanban_statuses": KANBAN_STATUSES,
            "columns": columns,
            "stats": stats,
            "enhanced_stats": enhanced,
            "statuses": STATUSES,
        },
    )


@app.get("/api/stats-cards", response_class=HTMLResponse)
async def stats_cards(request: Request):
    stats = db.get_stats()
    enhanced = db.get_enhanced_stats()
    return templates.TemplateResponse(
        "partials/stats_cards.html",
        {
            "request": request,
            "stats": stats,
            "enhanced_stats": enhanced,
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run("webapp.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
