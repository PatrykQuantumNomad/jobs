"""Indeed.com automation using Playwright + stealth.

Anti-bot level: HIGH — Cloudflare Turnstile, fingerprinting, behavioural analysis.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import BrowserContext
from playwright.sync_api import TimeoutError as PwTimeout

from config import Config
from models import Job, SearchQuery
from platforms.base import BasePlatform
from platforms.indeed_selectors import (
    INDEED_SEARCH_PARAMS,
    INDEED_SELECTORS,
    INDEED_URLS,
)


class IndeedPlatform(BasePlatform):
    """Indeed job search and Indeed Apply automation."""

    platform_name = "indeed"

    def __init__(self, context: BrowserContext) -> None:
        super().__init__(context)

    # ── Authentication ───────────────────────────────────────────────────

    def login(self) -> bool:
        """Session-based login — uses cached session or waits for manual Google auth."""
        self.page.goto(INDEED_URLS["base"], timeout=Config.PAGE_LOAD_TIMEOUT)
        self.human_delay("nav")

        if self.is_logged_in():
            print("  Indeed: already logged in (cached session)")
            return False

        # Session expired or first run — need manual login
        print("  Indeed: no active session — opening login page for manual auth")
        self.page.goto(INDEED_URLS["login"], timeout=Config.PAGE_LOAD_TIMEOUT)

        print("  ┌──────────────────────────────────────────────────────┐")
        print("  │  1. Solve the Cloudflare challenge if it appears     │")
        print("  │  2. Log in via Google in the browser window          │")
        print("  │  3. Press ENTER here when you're logged in           │")
        print("  └──────────────────────────────────────────────────────┘")
        input("  Press ENTER after logging in > ")

        # Navigate to homepage to verify session
        self.page.goto(INDEED_URLS["base"], timeout=Config.PAGE_LOAD_TIMEOUT)
        self.human_delay("nav")

        if self.is_logged_in():
            print("  Indeed: login detected — session cached for future runs")
            return True

        self.screenshot("login_failed")
        raise RuntimeError(
            "Indeed login not detected — try again or check the browser window"
        )

    def is_logged_in(self) -> bool:
        return self.element_exists(INDEED_SELECTORS["logged_in_indicator"])

    # ── Search ───────────────────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[Job]:
        jobs: list[Job] = []
        seen_ids: set[str] = set()
        base_url = self._build_search_url(query)
        print(f"  Indeed: searching '{query.query}' …")

        for page_idx in range(query.max_pages):
            url = f"{base_url}&start={page_idx * 10}"
            self.page.goto(url, timeout=Config.PAGE_LOAD_TIMEOUT)
            self.human_delay("nav")

            self._check_challenges(f"search_page_{page_idx + 1}")

            try:
                self.page.wait_for_selector(
                    INDEED_SELECTORS["job_card"], timeout=10_000
                )
            except PwTimeout:
                print(f"    page {page_idx + 1}: no results, stopping")
                break

            cards = self.page.query_selector_all(INDEED_SELECTORS["job_card"])
            new_on_page = 0
            for card in cards:
                job = self._extract_card(card)
                if job is not None and job.id not in seen_ids:
                    seen_ids.add(job.id)
                    jobs.append(job)
                    new_on_page += 1

            print(f"    page {page_idx + 1}: {len(cards)} cards, {new_on_page} new")

            if not cards or new_on_page == 0:
                break

        print(f"  Indeed: {len(jobs)} unique jobs for '{query.query}'")
        return jobs

    def get_job_details(self, job: Job) -> Job:
        if not job.url:
            return job
        try:
            self.page.goto(str(job.url), timeout=Config.PAGE_LOAD_TIMEOUT)
            self.human_delay("nav")

            if self._detect_captcha():
                print(f"    Indeed: CAPTCHA on detail page for {job.title}, skipping")
                return job

            # Detect 404 pages (bogus job IDs produce "Not Found | Indeed")
            page_title = self.page.title() or ""
            if "not found" in page_title.lower():
                print(f"    Indeed: 404 for {job.title}, skipping")
                return job

            # Try multiple description selectors (Indeed changes these)
            desc_selectors = [
                INDEED_SELECTORS["job_description"],
                "#jobsearch-ViewjobPaneWrapper",
                ".jobsearch-JobComponent-description",
                "[data-testid='jobDescriptionText']",
            ]
            for sel in desc_selectors:
                try:
                    self.page.wait_for_selector(sel, timeout=5_000)
                    elem = self.page.query_selector(sel)
                    if elem:
                        job.description = elem.inner_text()
                        break
                except PwTimeout:
                    continue

            if not job.description:
                self.screenshot(f"no_desc_{job.id[:8]}")
                print(
                    f"    Indeed: no description found for {job.title} — screenshot saved"
                )
        except Exception as exc:
            print(f"    Indeed: error fetching details for {job.title} — {exc}")
        return job

    # ── Apply (human-in-the-loop) ────────────────────────────────────────

    def apply(self, job: Job, resume_path: Path) -> bool:
        self.page.goto(str(job.url), timeout=Config.PAGE_LOAD_TIMEOUT)
        self.human_delay("nav")

        if not self.element_exists(INDEED_SELECTORS["apply_button"], timeout=5000):
            print(f"    Indeed: no Indeed Apply button for {job.title}")
            return False

        self.page.click(INDEED_SELECTORS["apply_button"])
        self.human_delay("nav")

        # Resume upload if prompted
        if self.element_exists(INDEED_SELECTORS["resume_upload"], timeout=5000):
            resp = self.wait_for_human(
                f"Resume upload for {job.company} — {job.title}\n"
                f"  File: {resume_path}\n"
                "  Type 'yes' to upload, anything else to skip:"
            )
            if resp.lower() != "yes":
                return False
            self.page.set_input_files(
                INDEED_SELECTORS["resume_upload"], str(resume_path)
            )
            self.human_delay("form")

        # Final confirmation
        self.screenshot("before_submit")
        resp = self.wait_for_human(
            f"Ready to submit to {job.company} — {job.title}\n"
            "  Type 'SUBMIT' to confirm:"
        )
        if resp != "SUBMIT":
            print("    Indeed: cancelled by user")
            return False

        if self.element_exists(INDEED_SELECTORS["submit_application"], timeout=3000):
            self.page.click(INDEED_SELECTORS["submit_application"])
            self.human_delay("nav")
            print(f"    Indeed: submitted application for {job.title}")
            return True

        print("    Indeed: submit button not found")
        return False

    # ── Sponsored card detection ────────────────────────────────────────

    @staticmethod
    def _is_sponsored(card) -> bool:
        """Detect Indeed sponsored/promoted cards that have fake job IDs."""
        try:
            text = card.inner_text()
            # "Sponsored" label appears near the top of promoted cards
            for line in text.split("\n")[:3]:
                if "sponsored" in line.lower().strip():
                    return True
        except Exception:
            pass
        return False

    # ── Challenge detection ──────────────────────────────────────────────

    def _detect_captcha(self) -> bool:
        return self.element_exists(
            INDEED_SELECTORS["captcha_frame"], timeout=2000
        ) or self.element_exists(INDEED_SELECTORS["cloudflare_challenge"], timeout=2000)

    def _detect_email_verification(self) -> bool:
        return self.element_exists(INDEED_SELECTORS["email_verification"], timeout=2000)

    def _check_challenges(self, context: str) -> None:
        """Raise if CAPTCHA or verification is detected."""
        if self._detect_captcha():
            self.screenshot(f"captcha_{context}")
            raise RuntimeError(
                f"Indeed CAPTCHA detected ({context}). "
                "Human intervention required — solve in browser_sessions/indeed/."
            )
        if self._detect_email_verification():
            self.screenshot(f"email_verify_{context}")
            raise RuntimeError(
                f"Indeed email verification required ({context}). "
                "Check pgolabek@gmail.com for verification code."
            )

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_search_url(self, query: SearchQuery) -> str:
        params = {"q": query.query, "l": query.location}
        url = f"{INDEED_URLS['search']}?{urlencode(params)}"
        url += f"&{INDEED_SEARCH_PARAMS['remote_filter']}"
        # Salary filter — Indeed expects salaryType=$XXX,XXX+ (URL-encoded)
        salary = f"${Config.MIN_SALARY:,}+"
        url += f"&{urlencode({'salaryType': salary})}"
        url += f"&{INDEED_SEARCH_PARAMS['recency_14d']}"
        url += f"&{INDEED_SEARCH_PARAMS['sort_date']}"
        return url

    def _extract_card(self, card) -> Job | None:
        try:
            # Skip sponsored/promoted cards — they have fake job IDs that 404
            if self._is_sponsored(card):
                return None

            # data-jk is on the title's <a> tag, not on the card wrapper
            title_link = card.query_selector(INDEED_SELECTORS["title_link"])
            if not title_link:
                return None

            job_id = title_link.get_attribute("data-jk") or ""
            if not job_id:
                return None

            # Get title text from the link's span child (or the link itself)
            title_el = title_link.query_selector("span")
            if title_el:
                title = title_el.inner_text().strip()
            else:
                title = title_link.inner_text().strip()
            if not title:
                return None

            url = f"{INDEED_URLS['base']}/viewjob?jk={job_id}"

            company_el = card.query_selector(INDEED_SELECTORS["company"])
            company = company_el.inner_text().strip() if company_el else "Unknown"

            location_el = card.query_selector(INDEED_SELECTORS["location"])
            location = location_el.inner_text().strip() if location_el else ""

            salary_el = card.query_selector(INDEED_SELECTORS["salary"])
            salary_text = salary_el.inner_text().strip() if salary_el else None
            sal_min, sal_max = _parse_salary(salary_text)

            return Job(
                id=job_id,
                platform="indeed",
                title=title,
                company=company,
                location=location,
                url=url,
                salary=salary_text,
                salary_min=sal_min,
                salary_max=sal_max,
            )
        except Exception as exc:
            print(f"    Indeed: card extraction error — {exc}")
            return None


# ── Module-level helpers ─────────────────────────────────────────────────


def _parse_salary(text: str | None) -> tuple[int | None, int | None]:
    """Parse Indeed salary formats — handles annual and hourly rates."""
    if not text:
        return None, None

    lower = text.lower()

    # Determine multiplier (hourly → annual)
    multiplier = 1
    if "hour" in lower:
        multiplier = 2080  # 40 h/wk × 52 wk
    elif "month" in lower:
        multiplier = 12

    nums = re.findall(r"[\d,.]+", text.replace("$", ""))
    if not nums:
        return None, None

    try:
        values: list[int] = []
        for n in nums[:2]:
            n = n.replace(",", "")
            val = float(n)
            if val < 1000 and multiplier == 1:
                val *= 1000  # likely K notation
            values.append(int(val * multiplier))
        if len(values) == 2:
            return min(values), max(values)
        return values[0], values[0]
    except ValueError:
        return None, None
