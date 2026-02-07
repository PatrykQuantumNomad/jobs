"""Job Tracker Web Dashboard — FastAPI + htmx + SQLite."""

from __future__ import annotations

import csv
import io
import json
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp import db

app = FastAPI(title="Job Tracker")

BASE_DIR = Path(__file__).parent
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
