"""Job Tracker Web Dashboard — FastAPI + htmx + SQLite."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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
    job = db.get_job(dedup_key)
    label = status.replace("_", " ").title()
    return HTMLResponse(
        f'<span class="status-badge status-{status}">{label}</span>'
    )


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


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    stats = db.get_stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "jobs": [],
            "stats": stats,
            "statuses": STATUSES,
            "filters": {},
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run("webapp.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
