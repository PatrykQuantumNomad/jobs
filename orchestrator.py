"""Main job search pipeline -- coordinates search, scoring, and application."""

from __future__ import annotations

import json
import sys
from datetime import datetime

from config import (
    JOB_DESCRIPTIONS_DIR,
    JOB_PIPELINE_DIR,
    PROJECT_ROOT,
    ensure_directories,
    get_settings,
)
from dedup import fuzzy_deduplicate
from models import Job, JobStatus
from platforms import get_all_platforms, get_browser_context, close_browser
from platforms.registry import get_platform, PlatformInfo
from salary import parse_salary, parse_salary_ints, NormalizedSalary
from scorer import JobScorer
from webapp import db as webdb


class Orchestrator:
    """Five-phase pipeline: setup -> login -> search -> score -> apply."""

    def __init__(self, headless: bool = True, scheduled: bool = False) -> None:
        self.settings = get_settings()
        self.scorer = JobScorer(
            profile=self.settings.build_candidate_profile(),
            weights=self.settings.scoring.weights,
        )
        self.discovered_jobs: list[Job] = []
        self.scheduled = scheduled
        self.headless = headless
        if scheduled:
            self.headless = True  # Force headless in scheduled mode
        self._failed_logins: set[str] = set()
        self.searched_platforms: list[str] = []
        self.run_timestamp: str = ""

    # -- Full pipeline ---------------------------------------------------------

    def run(self, platforms: list[str] | None = None) -> None:
        if platforms is None:
            platforms = self.settings.enabled_platforms()

        # Validate all requested platforms are registered
        for name in platforms:
            get_platform(name)  # Raises KeyError if not registered

        self.run_timestamp = datetime.now().isoformat()

        print("=" * 60)
        print("  JOB SEARCH AUTOMATION PIPELINE")
        print("=" * 60)

        self.phase_0_setup()
        self.phase_1_login(platforms)

        # Track which platforms were actually searched (exclude failed logins)
        self.searched_platforms = [p for p in platforms if p not in self._failed_logins]

        self.phase_2_search(platforms)
        self.phase_3_score()

        # Delta cleanup: remove stale jobs from searched platforms
        if self.searched_platforms:
            stale_count = webdb.remove_stale_jobs(
                self.searched_platforms, self.run_timestamp
            )
            if stale_count:
                print(f"  Removed {stale_count} stale jobs")

        # One-time backfill: score breakdowns for legacy jobs
        self._backfill_breakdowns()

        self.phase_4_apply()

        self._print_summary()

    # -- Phase 0: environment validation ---------------------------------------

    def phase_0_setup(self) -> None:
        print("\n[Phase 0] Environment Setup")
        print("-" * 60)

        v = sys.version_info
        print(f"  Python {v.major}.{v.minor}.{v.micro}")

        if not (PROJECT_ROOT / ".env").exists():
            print("  ERROR: .env not found -- copy .env.example and fill in credentials")
            sys.exit(1)

        print("  Credentials:")
        for name in get_all_platforms():
            ok = self.settings.validate_platform_credentials(name)
            print(f"    {name:10s} {'OK' if ok else 'MISSING'}")

        ensure_directories()

        resume_path = PROJECT_ROOT / self.settings.candidate_resume_path
        if not resume_path.exists():
            print(f"  WARNING: ATS resume not found at {resume_path}")

        print("  Setup complete.")

    # -- Phase 1: login --------------------------------------------------------

    def phase_1_login(self, platforms: list[str]) -> None:
        print("\n[Phase 1] Platform Login")
        print("-" * 60)

        for name in platforms:
            info = get_platform(name)
            if info.platform_type == "api":
                print(f"  {info.name}: no login required")
                continue
            if not self.settings.validate_platform_credentials(name):
                print(f"  {info.name}: credentials missing, skipping")
                self._failed_logins.add(name)
                continue
            self._login_platform(name, info)

    def _login_platform(self, name: str, info: PlatformInfo) -> None:
        pw, ctx = None, None
        try:
            pw, ctx = get_browser_context(name, headless=self.headless)
            platform = info.cls()
            platform.init(ctx)
            platform._unattended = self.scheduled  # Propagate unattended flag
            with platform:
                platform.login()
        except Exception as exc:
            print(f"  {info.name}: login failed -- {exc}")
            print(f"  Skipping {info.name} for this run.")
            self._failed_logins.add(name)
        finally:
            if pw and ctx:
                close_browser(pw, ctx)

    # -- Phase 2: search -------------------------------------------------------

    def phase_2_search(self, platforms: list[str]) -> None:
        print("\n[Phase 2] Job Search")
        print("-" * 60)

        for name in platforms:
            if name in self._failed_logins:
                info = get_platform(name)
                print(f"  Skipping {info.name} (login failed)")
                continue
            info = get_platform(name)
            if info.platform_type == "browser" and not self.settings.validate_platform_credentials(name):
                continue
            jobs = self._search_platform(name, info)
            self._save_raw(name, jobs)

    def _search_platform(self, name: str, info: PlatformInfo) -> list[Job]:
        queries = self.settings.get_search_queries(platform=name)
        all_jobs: list[Job] = []

        platform = info.cls()

        if info.platform_type == "browser":
            pw, ctx = get_browser_context(name, headless=self.headless)
            platform.init(ctx)
        else:
            platform.init()
            pw, ctx = None, None

        platform._unattended = self.scheduled  # Propagate unattended flag

        with platform:
            for q in queries:
                try:
                    found = platform.search(q)
                    if info.platform_type == "browser":
                        for job in found:
                            job = platform.get_job_details(job)
                            all_jobs.append(job)
                    else:
                        all_jobs.extend(found)
                except Exception as exc:
                    print(f"  {info.name}: error on '{q.query}' -- {exc}")
                    continue

        if info.platform_type == "browser" and pw and ctx:
            close_browser(pw, ctx)

        return all_jobs

    def _save_raw(self, platform: str, jobs: list[Job]) -> None:
        path = JOB_PIPELINE_DIR / f"raw_{platform}.json"
        data = [j.model_dump(mode="json") for j in jobs]
        path.write_text(json.dumps(data, indent=2, default=str))
        print(f"  Saved {len(jobs)} raw jobs -> {path}")

    # -- Phase 3: score & deduplicate ------------------------------------------

    def phase_3_score(self) -> None:
        print("\n[Phase 3] Scoring & Deduplication")
        print("-" * 60)

        all_jobs = self._load_raw_results()
        print(f"  Total raw jobs: {len(all_jobs)}")

        # Salary normalization
        for job in all_jobs:
            if job.salary_min is not None or job.salary_max is not None:
                # RemoteOK-style integer salaries
                sal = parse_salary_ints(job.salary_min, job.salary_max)
            else:
                sal = parse_salary(job.salary)

            if sal.min_annual is not None:
                job.salary_min = sal.min_annual
            if sal.max_annual is not None:
                job.salary_max = sal.max_annual
            if sal.display:
                job.salary_display = sal.display
            if sal.currency:
                job.salary_currency = sal.currency

        # Fuzzy deduplication (replaces old exact-match _deduplicate)
        unique = fuzzy_deduplicate(all_jobs)
        print(f"  After dedup:    {len(unique)}")

        # Score with breakdowns
        scored_pairs = self.scorer.score_batch_with_breakdown(unique)

        # Persist to DB with new fields
        for job, breakdown in scored_pairs:
            webdb.upsert_job({
                "id": job.id,
                "platform": job.platform,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "salary": job.salary,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "apply_url": job.apply_url,
                "description": job.description,
                "posted_date": job.posted_date,
                "tags": job.tags,
                "easy_apply": job.easy_apply,
                "score": job.score,
                "status": job.status.value if isinstance(job.status, JobStatus) else job.status,
                "applied_date": job.applied_date,
                "notes": job.notes,
                "score_breakdown": breakdown.to_dict(),
                "company_aliases": job.company_aliases,
                "salary_display": job.salary_display,
                "salary_currency": job.salary_currency,
            })

        scored_jobs = [job for job, _ in scored_pairs]
        filtered = [j for j in scored_jobs if (j.score or 0) >= 3]
        print(f"  Score 3+:       {len(filtered)}")

        self._save_scored(filtered)
        self._save_descriptions(filtered)
        self._write_tracker(filtered)

        self.discovered_jobs = filtered

    def _load_raw_results(self) -> list[Job]:
        jobs: list[Job] = []
        for name in get_all_platforms():
            path = JOB_PIPELINE_DIR / f"raw_{name}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            for item in data:
                jobs.append(Job(**item))
        return jobs

    def _save_scored(self, jobs: list[Job]) -> None:
        path = JOB_PIPELINE_DIR / "discovered_jobs.json"
        data = [j.model_dump(mode="json") for j in jobs]
        path.write_text(json.dumps(data, indent=2, default=str))
        print(f"  Saved scored jobs -> {path}")

    def _save_descriptions(self, jobs: list[Job]) -> None:
        for job in jobs:
            safe_company = _sanitize(job.company)
            safe_title = _sanitize(job.title)
            filename = f"{safe_company}_{safe_title}.md"
            path = JOB_DESCRIPTIONS_DIR / filename

            salary_line = (
                f"**Salary:** {job.salary_display}\n"
                if job.salary_display
                else "**Salary:** Not listed\n"
            )

            content = (
                f"# {job.title} at {job.company}\n\n"
                f"**Platform:** {job.platform}\n"
                f"**Location:** {job.location}\n"
                f"{salary_line}"
                f"**Score:** {job.score}/5\n"
                f"**URL:** {job.url}\n\n"
                "---\n\n"
                f"{job.description}\n"
            )
            path.write_text(content)

    def _write_tracker(self, jobs: list[Job]) -> None:
        path = JOB_PIPELINE_DIR / "tracker.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        counts = {5: 0, 4: 0, 3: 0}
        for j in jobs:
            if j.score in counts:
                counts[j.score] += 1

        lines = [
            "# Job Application Tracker\n",
            f"**Updated:** {now}\n",
            "## Score Breakdown\n",
        ]
        for s in (5, 4, 3):
            lines.append(f"- Score {s}: {counts[s]} jobs\n")

        lines += [
            "\n## All Jobs (Score 3+)\n",
            "| Score | Company | Title | Location | Salary | Platform | Status |\n",
            "|-------|---------|-------|----------|--------|----------|--------|\n",
        ]
        for j in sorted(jobs, key=lambda x: (x.score or 0), reverse=True):
            sal = j.salary_display if j.salary_display else "N/A"
            lines.append(
                f"| {j.score} | {j.company} | {j.title} | "
                f"{j.location} | {sal} | {j.platform} | {j.status} |\n"
            )

        path.write_text("".join(lines))
        print(f"  Tracker updated -> {path}")

    # -- Backfill --------------------------------------------------------------

    def _backfill_breakdowns(self) -> None:
        """One-time backfill: add score breakdowns to legacy scored jobs."""
        def _scorer_fn(job_dict: dict) -> tuple[int, dict]:
            job = Job(**{k: v for k, v in job_dict.items()
                         if k in Job.model_fields and v is not None})
            score, breakdown = self.scorer.score_job_with_breakdown(job)
            return score, breakdown.to_dict()

        count = webdb.backfill_score_breakdowns(_scorer_fn)
        if count:
            print(f"  Backfilled {count} score breakdowns")

    # -- Phase 4: apply (human-in-the-loop) ------------------------------------

    def phase_4_apply(self) -> None:
        if self.scheduled:
            print("\n[Phase 4] Skipped (scheduled mode -- requires human approval)")
            return

        print("\n[Phase 4] Application (Human-in-the-Loop)")
        print("-" * 60)

        top = [j for j in self.discovered_jobs if (j.score or 0) >= 4]
        if not top:
            print("  No jobs scored 4+. Review score-3 jobs in tracker.md.")
            return

        print(f"\n  {len(top)} top-scoring jobs:\n")
        for idx, j in enumerate(top, 1):
            sal = j.salary_display if j.salary_display else "N/A"
            print(f"  {idx}. [{j.score}/5] {j.company} -- {j.title}")
            print(f"     Salary: {sal}  |  Location: {j.location}  |  {j.platform}")
            print(f"     URL: {j.url}\n")

        resp = input("  Enter job numbers to apply (comma-separated), or 'skip': ").strip()
        if resp.lower() == "skip":
            print("  Skipped.")
            return

        try:
            indices = [int(x.strip()) - 1 for x in resp.split(",")]
            selected = [top[i] for i in indices if 0 <= i < len(top)]
        except (ValueError, IndexError):
            print("  Invalid input. Skipping.")
            return

        for job in selected:
            self._apply_to(job)

    def _apply_to(self, job: Job) -> None:
        print(f"\n  Applying: {job.company} -- {job.title}")

        info = get_platform(job.platform)

        if info.platform_type == "api":
            platform = info.cls()
            platform.init()
            with platform:
                platform.apply(job)
            return

        # Browser platform -- visible mode for human oversight
        resume = PROJECT_ROOT / self.settings.candidate_resume_path
        pw, ctx = get_browser_context(job.platform, headless=False)

        try:
            platform = info.cls()
            platform.init(ctx)
            with platform:
                success = platform.apply(job, resume)

            if success:
                job.status = JobStatus.APPLIED
                job.applied_date = datetime.now().isoformat()
                print(f"  Application submitted to {job.company}")
            else:
                print(f"  Application not submitted for {job.company}")
        except Exception as exc:
            print(f"  Application error: {exc}")
        finally:
            close_browser(pw, ctx)

        # Re-save tracker with updated status
        self._write_tracker(self.discovered_jobs)

    # -- Summary ---------------------------------------------------------------

    def _print_summary(self) -> None:
        total = len(self.discovered_jobs)
        applied = sum(1 for j in self.discovered_jobs if j.status == JobStatus.APPLIED)
        score5 = sum(1 for j in self.discovered_jobs if j.score == 5)
        score4 = sum(1 for j in self.discovered_jobs if j.score == 4)

        print("\n" + "=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Total scored jobs (3+): {total}")
        print(f"  Score 5: {score5}  |  Score 4: {score4}")
        print(f"  Applications submitted: {applied}")
        print(f"  Tracker: {JOB_PIPELINE_DIR / 'tracker.md'}")
        print("=" * 60)


# -- Helpers -------------------------------------------------------------------


def _sanitize(text: str) -> str:
    """Make text safe for filenames."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return safe.strip().replace(" ", "_")[:60]


# -- CLI entry point -----------------------------------------------------------


def main() -> None:
    import argparse

    from pydantic import ValidationError

    parser = argparse.ArgumentParser(description="Job Search Automation Pipeline")
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=None,
        help="Platforms to search (default: all enabled in config.yaml)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed (visible) mode for debugging",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Unattended mode: headless, no input prompts, logs run history",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate config.yaml and .env without running the pipeline",
    )
    args = parser.parse_args()

    if args.validate:
        try:
            settings = get_settings()
        except ValidationError as exc:
            print("Config validation FAILED:\n")
            for err in exc.errors():
                loc = " -> ".join(str(part) for part in err["loc"])
                print(f"  {loc}: {err['msg']}")
            sys.exit(1)

        print("Config validation passed.\n")

        # Credential completeness warnings
        if settings.platforms.indeed.enabled and not settings.indeed_email:
            print("  WARNING: Indeed is enabled but INDEED_EMAIL is not set in .env")
        if settings.platforms.dice.enabled:
            if not settings.dice_email:
                print("  WARNING: Dice is enabled but DICE_EMAIL is not set in .env")
            if not settings.dice_password:
                print("  WARNING: Dice is enabled but DICE_PASSWORD is not set in .env")

        print(f"\n  Enabled platforms: {', '.join(settings.enabled_platforms())}")
        print(f"  Search queries:    {len(settings.search.queries)}")
        print(f"  Target titles:     {len(settings.scoring.target_titles)}")
        print(f"  Tech keywords:     {len(settings.scoring.tech_keywords)}")
        sys.exit(0)

    Orchestrator(headless=not args.headed, scheduled=args.scheduled).run(platforms=args.platforms)


if __name__ == "__main__":
    main()
