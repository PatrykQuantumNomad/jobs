"""Main job search pipeline — coordinates search, scoring, and application."""

from __future__ import annotations

import asyncio
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
from models import Job, JobStatus
from scorer import JobScorer


class Orchestrator:
    """Five-phase pipeline: setup -> login -> search -> score -> apply."""

    def __init__(self, headless: bool = True) -> None:
        self.settings = get_settings()
        self.scorer = JobScorer(
            profile=self.settings.build_candidate_profile(),
            weights=self.settings.scoring.weights,
        )
        self.discovered_jobs: list[Job] = []
        self.headless = headless
        self._failed_logins: set[str] = set()

    # -- Full pipeline -------------------------------------------------------

    def run(self, platforms: list[str] | None = None) -> None:
        if platforms is None:
            platforms = self.settings.enabled_platforms()

        print("=" * 60)
        print("  JOB SEARCH AUTOMATION PIPELINE")
        print("=" * 60)

        self.phase_0_setup()
        self.phase_1_login(platforms)
        self.phase_2_search(platforms)
        self.phase_3_score()
        self.phase_4_apply()

        self._print_summary()

    # -- Phase 0: environment validation -------------------------------------

    def phase_0_setup(self) -> None:
        print("\n[Phase 0] Environment Setup")
        print("-" * 60)

        v = sys.version_info
        print(f"  Python {v.major}.{v.minor}.{v.micro}")

        if not (PROJECT_ROOT / ".env").exists():
            print("  ERROR: .env not found -- copy .env.example and fill in credentials")
            sys.exit(1)

        print("  Credentials:")
        for p in ("indeed", "dice", "remoteok"):
            ok = self.settings.validate_platform_credentials(p)
            print(f"    {p:10s} {'OK' if ok else 'MISSING'}")

        ensure_directories()

        resume_path = PROJECT_ROOT / self.settings.candidate_resume_path
        if not resume_path.exists():
            print(f"  WARNING: ATS resume not found at {resume_path}")

        print("  Setup complete.")

    # -- Phase 1: login ------------------------------------------------------

    def phase_1_login(self, platforms: list[str]) -> None:
        print("\n[Phase 1] Platform Login")
        print("-" * 60)

        if "indeed" in platforms and self.settings.validate_platform_credentials("indeed"):
            self._login_platform("indeed")

        if "dice" in platforms and self.settings.validate_platform_credentials("dice"):
            self._login_platform("dice")

        if "remoteok" in platforms:
            print("  RemoteOK: no login required")

    def _login_platform(self, name: str) -> None:
        from platforms.stealth import close_browser, get_browser_context

        pw, ctx = None, None
        try:
            pw, ctx = get_browser_context(name, headless=self.headless)

            if name == "indeed":
                from platforms.indeed import IndeedPlatform
                IndeedPlatform(ctx).login()
            elif name == "dice":
                from platforms.dice import DicePlatform
                DicePlatform(ctx).login()
        except Exception as exc:
            print(f"  {name}: login failed -- {exc}")
            print(f"  Skipping {name} for this run.")
            self._failed_logins.add(name)
        finally:
            if pw and ctx:
                close_browser(pw, ctx)

    # -- Phase 2: search -----------------------------------------------------

    def phase_2_search(self, platforms: list[str]) -> None:
        print("\n[Phase 2] Job Search")
        print("-" * 60)

        for name in ("indeed", "dice"):
            if name not in platforms:
                continue
            if name in self._failed_logins:
                print(f"  Skipping {name} (login failed)")
                continue
            if not self.settings.validate_platform_credentials(name):
                continue
            jobs = self._search_browser_platform(name)
            self._save_raw(name, jobs)

        if "remoteok" in platforms:
            jobs = asyncio.run(self._search_remoteok())
            self._save_raw("remoteok", jobs)

    def _search_browser_platform(self, name: str) -> list[Job]:
        from platforms.stealth import close_browser, get_browser_context

        queries = self.settings.get_search_queries(platform=name)
        all_jobs: list[Job] = []

        pw, ctx = get_browser_context(name, headless=self.headless)

        if name == "indeed":
            from platforms.indeed import IndeedPlatform
            platform = IndeedPlatform(ctx)
        else:
            from platforms.dice import DicePlatform
            platform = DicePlatform(ctx)

        for q in queries:
            try:
                found = platform.search(q)
                for job in found:
                    job = platform.get_job_details(job)
                    all_jobs.append(job)
            except RuntimeError as exc:
                print(f"  {name}: error on '{q.query}' -- {exc}")
                continue

        close_browser(pw, ctx)
        return all_jobs

    async def _search_remoteok(self) -> list[Job]:
        from platforms.remoteok import RemoteOKPlatform

        platform = RemoteOKPlatform()
        queries = self.settings.get_search_queries(platform="remoteok")
        all_jobs: list[Job] = []

        for q in queries:
            jobs = await platform.search(q)
            all_jobs.extend(jobs)

        await platform.close()
        return all_jobs

    def _save_raw(self, platform: str, jobs: list[Job]) -> None:
        path = JOB_PIPELINE_DIR / f"raw_{platform}.json"
        data = [j.model_dump(mode="json") for j in jobs]
        path.write_text(json.dumps(data, indent=2, default=str))
        print(f"  Saved {len(jobs)} raw jobs -> {path}")

    # -- Phase 3: score & deduplicate ----------------------------------------

    def phase_3_score(self) -> None:
        print("\n[Phase 3] Scoring & Deduplication")
        print("-" * 60)

        all_jobs = self._load_raw_results()
        print(f"  Total raw jobs: {len(all_jobs)}")

        unique = self._deduplicate(all_jobs)
        print(f"  After dedup:    {len(unique)}")

        scored = self.scorer.score_batch(unique)

        filtered = [j for j in scored if (j.score or 0) >= 3]
        print(f"  Score 3+:       {len(filtered)}")

        self._save_scored(filtered)
        self._save_descriptions(filtered)
        self._write_tracker(filtered)

        self.discovered_jobs = filtered

    def _load_raw_results(self) -> list[Job]:
        jobs: list[Job] = []
        for name in ("indeed", "dice", "remoteok"):
            path = JOB_PIPELINE_DIR / f"raw_{name}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            for item in data:
                jobs.append(Job(**item))
        return jobs

    def _deduplicate(self, jobs: list[Job]) -> list[Job]:
        seen: dict[str, Job] = {}
        for job in jobs:
            key = job.dedup_key()
            if key not in seen:
                seen[key] = job
            else:
                existing = seen[key]
                # Prefer the version with more data
                has_salary = bool(job.salary_min or job.salary_max)
                existing_has = bool(existing.salary_min or existing.salary_max)
                if (has_salary and not existing_has) or (
                    len(job.description) > len(existing.description)
                ):
                    seen[key] = job
        return list(seen.values())

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
                f"**Salary:** ${job.salary_min:,}--${job.salary_max:,}\n"
                if job.salary_min
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
            sal = (
                f"${j.salary_min // 1000}K--${j.salary_max // 1000}K"
                if j.salary_min and j.salary_max
                else "N/A"
            )
            lines.append(
                f"| {j.score} | {j.company} | {j.title} | "
                f"{j.location} | {sal} | {j.platform} | {j.status} |\n"
            )

        path.write_text("".join(lines))
        print(f"  Tracker updated -> {path}")

    # -- Phase 4: apply (human-in-the-loop) ----------------------------------

    def phase_4_apply(self) -> None:
        print("\n[Phase 4] Application (Human-in-the-Loop)")
        print("-" * 60)

        top = [j for j in self.discovered_jobs if (j.score or 0) >= 4]
        if not top:
            print("  No jobs scored 4+. Review score-3 jobs in tracker.md.")
            return

        print(f"\n  {len(top)} top-scoring jobs:\n")
        for idx, j in enumerate(top, 1):
            sal = (
                f"${j.salary_min // 1000}K--${j.salary_max // 1000}K"
                if j.salary_min and j.salary_max
                else "N/A"
            )
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
        from platforms.stealth import close_browser, get_browser_context

        print(f"\n  Applying: {job.company} -- {job.title}")
        resume = PROJECT_ROOT / self.settings.candidate_resume_path

        if job.platform == "remoteok":
            print(f"  External application required: {job.apply_url or job.url}")
            return

        headless = False  # visible for human oversight
        pw, ctx = get_browser_context(job.platform, headless=headless)

        try:
            if job.platform == "indeed":
                from platforms.indeed import IndeedPlatform
                success = IndeedPlatform(ctx).apply(job, resume)
            elif job.platform == "dice":
                from platforms.dice import DicePlatform
                success = DicePlatform(ctx).apply(job, resume)
            else:
                success = False

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

    # -- Summary -------------------------------------------------------------

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


# -- Helpers -----------------------------------------------------------------


def _sanitize(text: str) -> str:
    """Make text safe for filenames."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return safe.strip().replace(" ", "_")[:60]


# -- CLI entry point ---------------------------------------------------------


def main() -> None:
    import argparse

    from pydantic import ValidationError

    parser = argparse.ArgumentParser(description="Job Search Automation Pipeline")
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["indeed", "dice", "remoteok"],
        default=None,
        help="Platforms to search (default: all enabled in config.yaml)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed (visible) mode for debugging",
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

    Orchestrator(headless=not args.headed).run(platforms=args.platforms)


if __name__ == "__main__":
    main()
