"""Dice.com automation using Playwright."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import BrowserContext
from playwright.sync_api import TimeoutError as PwTimeout

from config import get_settings
from models import Job, SearchQuery
from platforms.base import BasePlatform
from platforms.dice_selectors import DICE_SEARCH_PARAMS, DICE_SELECTORS, DICE_URLS


class DicePlatform(BasePlatform):
    """Dice job search and Easy Apply automation.

    Anti-bot level: LOW — standard delays sufficient.
    """

    platform_name = "dice"

    def __init__(self, context: BrowserContext) -> None:
        super().__init__(context)

    # ── Authentication ───────────────────────────────────────────────────

    def login(self) -> bool:
        settings = get_settings()
        if not settings.validate_platform_credentials("dice"):
            raise ValueError("Dice credentials not found in .env")

        timeout = settings.timing.page_load_timeout
        self.page.goto(DICE_URLS["base"], timeout=timeout)
        self.human_delay("nav")

        if self.is_logged_in():
            print("  Dice: already logged in (cached session)")
            return False

        print("  Dice: logging in …")
        self.page.goto(DICE_URLS["login"], timeout=timeout)
        self.human_delay("nav")

        try:
            # Step 1: enter email and click Continue
            self.page.fill(DICE_SELECTORS["login_email"], settings.dice_email)
            self.human_delay("form")
            self.page.click(DICE_SELECTORS["login_continue"])
            self.human_delay("nav")

            # Step 2: wait for password field, fill it, submit
            self.page.wait_for_selector(
                DICE_SELECTORS["login_password"], timeout=15_000
            )
            self.page.fill(DICE_SELECTORS["login_password"], settings.dice_password)
            self.human_delay("form")
            self.page.click(DICE_SELECTORS["login_submit"])
            self.page.wait_for_url("**/dashboard/**", timeout=15_000)

            if not self.is_logged_in():
                self.screenshot("login_failed")
                raise RuntimeError("Dice login failed — check credentials")

            print("  Dice: login successful")
            return True
        except PwTimeout as exc:
            self.screenshot("login_timeout")
            raise RuntimeError(f"Dice login timeout: {exc}") from exc

    def is_logged_in(self) -> bool:
        url = self.page.url
        return "dice.com" in url and "/login" not in url

    # ── Search ───────────────────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[Job]:
        jobs: list[Job] = []
        base_url = self._build_search_url(query)
        timeout = get_settings().timing.page_load_timeout
        print(f"  Dice: searching '{query.query}' …")

        for page_num in range(1, query.max_pages + 1):
            url = f"{base_url}&page={page_num}"
            self.page.goto(url, timeout=timeout)
            self.human_delay("nav")

            try:
                self.page.wait_for_selector(DICE_SELECTORS["job_card"], timeout=10_000)
            except PwTimeout:
                print(f"    page {page_num}: no results, stopping")
                break

            cards = self.page.query_selector_all(DICE_SELECTORS["job_card"])
            print(f"    page {page_num}: {len(cards)} cards")

            for card in cards:
                job = self._extract_card(card)
                if job is not None:
                    jobs.append(job)

            if not cards:
                break

        print(f"  Dice: {len(jobs)} jobs extracted for '{query.query}'")
        return jobs

    def get_job_details(self, job: Job) -> Job:
        try:
            self.page.goto(str(job.url), timeout=get_settings().timing.page_load_timeout)
            self.human_delay("nav")
            self.page.wait_for_selector(
                DICE_SELECTORS["job_description"], timeout=10_000
            )
            elem = self.page.query_selector(DICE_SELECTORS["job_description"])
            if elem:
                job.description = elem.inner_text()
        except PwTimeout:
            print(f"    Dice: timeout fetching details for {job.title}")
        return job

    # ── Apply (human-in-the-loop) ────────────────────────────────────────

    def apply(self, job: Job, resume_path: Path) -> bool:
        self.page.goto(str(job.url), timeout=get_settings().timing.page_load_timeout)
        self.human_delay("nav")

        if not self.element_exists(DICE_SELECTORS["apply_button"], timeout=5000):
            print(f"    Dice: no apply button for {job.title}")
            return False

        self.page.click(DICE_SELECTORS["apply_button"])
        self.human_delay("nav")

        # Resume upload
        if self.element_exists(DICE_SELECTORS["resume_upload"], timeout=5000):
            resp = self.wait_for_human(
                f"Resume upload for {job.company} — {job.title}\n"
                f"  File: {resume_path}\n"
                "  Type 'yes' to upload, anything else to skip:"
            )
            if resp.lower() != "yes":
                return False
            self.page.set_input_files(DICE_SELECTORS["resume_upload"], str(resume_path))
            self.human_delay("form")

        # Final confirmation
        self.screenshot("before_submit")
        resp = self.wait_for_human(
            f"Ready to submit to {job.company} — {job.title}\n"
            f"  Type 'SUBMIT' to confirm:"
        )
        if resp != "SUBMIT":
            print("    Dice: cancelled by user")
            return False

        self.page.click(DICE_SELECTORS["submit_application"])
        self.human_delay("nav")
        print(f"    Dice: submitted application for {job.title}")
        return True

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_search_url(self, query: SearchQuery) -> str:
        params = {
            "q": query.query,
            "location": query.location,
            "radius": "30",
            "radiusUnit": "mi",
            "pageSize": "20",
            "language": "en",
        }
        url = f"{DICE_URLS['search']}?{urlencode(params)}"
        url += f"&{DICE_SEARCH_PARAMS['remote_filter']}"
        url += f"&{DICE_SEARCH_PARAMS['recency_7d']}"
        return url

    def _extract_card(self, card) -> Job | None:
        try:
            title_el = card.query_selector(DICE_SELECTORS["title"])
            if not title_el:
                return None

            title = title_el.inner_text().strip()
            if not title:
                return None

            # Build URL from data-job-guid attribute
            guid = card.get_attribute("data-job-guid") or ""
            if guid:
                url = f"{DICE_URLS['base']}/job-detail/{guid}"
            else:
                href = title_el.get_attribute("href") or ""
                url = href if href.startswith("http") else f"{DICE_URLS['base']}{href}"

            # Company: find company-profile links, pick the one with visible text
            company = "Unknown"
            for link in card.query_selector_all(DICE_SELECTORS["company_link"]):
                text = link.inner_text().strip()
                if text and text != "Company Logo":
                    company = text
                    break

            # Parse location and salary from card inner text
            # Format: "Company\nApply Now\nTitle\nLocation\n•\nDate\nDescription..."
            card_text = card.inner_text()
            location, salary_text = _parse_card_text(card_text, title)
            sal_min, sal_max = _parse_salary(salary_text)

            has_easy = "Easy Apply" in card_text

            return Job(
                platform="dice",
                title=title,
                company=company,
                location=location,
                url=url,
                salary=salary_text,
                salary_min=sal_min,
                salary_max=sal_max,
                easy_apply=has_easy,
            )
        except Exception as exc:
            print(f"    Dice: card extraction error — {exc}")
            return None


# ── Module-level helpers ─────────────────────────────────────────────────


def _parse_card_text(card_text: str, title: str) -> tuple[str, str | None]:
    """Extract location and salary from card innerText.

    Card text format:
        Company
        Apply Now          (or Easy Apply)
        Title
        Location • Date
        Description snippet...
        Full-time           (optional)
        USD 224,400 ...     (optional salary line)
    """
    lines = [ln.strip() for ln in card_text.split("\n") if ln.strip()]
    location = ""
    salary = None

    # Find the title line, location is the next non-bullet line
    for i, line in enumerate(lines):
        if line == title and i + 1 < len(lines):
            loc_line = lines[i + 1]
            # Location line may contain "•" separator with date
            location = loc_line.split("•")[0].strip() if "•" in loc_line else loc_line
            break

    # Look for salary pattern anywhere in the text
    for line in lines:
        if re.search(r"USD\s+[\d,.]", line) or re.search(
            r"\$\d[\d,]+.*per\s+(year|hour)", line
        ):
            salary = line
            break
        if re.match(r"^\$\d[\d,]+$", line):
            salary = line
            break

    return location, salary


def _parse_salary(text: str | None) -> tuple[int | None, int | None]:
    """Parse salary strings like '$150K - $200K', '$150,000 - $200,000',
    or 'USD 224,400.00 - 283,800.00 per year'."""
    if not text:
        return None, None
    cleaned = text.replace("$", "").replace("USD", "").replace(",", "")
    nums = re.findall(r"[\d.]+", cleaned)
    if not nums:
        return None, None
    try:
        values: list[int] = []
        for n in nums[:2]:
            val = float(n)
            # Treat small numbers as K shorthand (e.g., "150K")
            if val < 1000:
                val *= 1000
            values.append(int(val))
        if len(values) == 2:
            return min(values), max(values)
        return values[0], values[0]
    except ValueError:
        return None, None
