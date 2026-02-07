"""Generic form-filling logic with heuristic field matching."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from config import Config
from models import CandidateProfile

if TYPE_CHECKING:
    from playwright.sync_api import Page


# Keyword → profile field mapping.  Each key maps to a list of substrings
# that, when found in a form field's label/name/id/placeholder, indicate
# which candidate value to use.
_FIELD_KEYWORDS: dict[str, list[str]] = {
    "first_name": ["first name", "firstname", "fname", "given name"],
    "last_name": ["last name", "lastname", "lname", "surname", "family name"],
    "email": ["email", "e-mail"],
    "phone": ["phone", "telephone", "mobile", "cell"],
    "location": ["city", "location", "address"],
    "github": ["github", "portfolio", "code repository"],
    "website": ["website", "personal site", "blog", "url"],
    "experience": ["years of experience", "years experience", "how many years"],
    "current_title": ["current title", "current role", "job title"],
    "current_company": ["current company", "current employer", "company name"],
    "salary": ["desired salary", "salary expectation", "expected compensation"],
    "start_date": ["start date", "available", "notice period", "availability"],
    "education": ["education", "degree", "university", "school"],
    "authorization": [
        "authorized to work",
        "work authorization",
        "visa",
        "legally authorized",
    ],
    "relocate": ["willing to relocate", "relocation", "open to relocation"],
    "hear_about": ["how did you hear", "where did you find", "referral source"],
}


class FormFiller:
    """Fill application forms by matching field labels to candidate data.

    NEVER auto-submits.  Returns a summary of what was filled for human review.
    """

    def __init__(self, profile: CandidateProfile | None = None) -> None:
        self.profile = profile or Config.CANDIDATE

    def fill_form(self, page: Page, resume_path: Path | None = None) -> dict[str, str]:
        """Scan and fill form fields on *page*.

        Returns:
            dict mapping field description → value that was filled.
        """
        filled: dict[str, str] = {}
        inputs = page.query_selector_all("input, textarea, select")

        for elem in inputs:
            try:
                field_type = elem.get_attribute("type") or ""
                if field_type in ("hidden", "submit", "button", "image"):
                    continue

                # File upload
                if field_type == "file" and resume_path:
                    elem.set_input_files(str(resume_path))
                    filled["resume_upload"] = str(resume_path)
                    continue

                # Identify field
                field_key = self._identify(elem)
                if not field_key:
                    continue

                value = self._value_for(field_key)
                if not value:
                    continue

                # Fill the appropriate input type
                tag = elem.evaluate("el => el.tagName").lower()
                if tag == "select":
                    try:
                        elem.select_option(label=value)
                    except Exception:
                        continue
                elif field_type == "checkbox":
                    if value.lower() in ("yes", "true", "1"):
                        elem.check()
                    else:
                        elem.uncheck()
                elif field_type == "radio":
                    elem_val = (elem.get_attribute("value") or "").lower()
                    if value.lower() in elem_val:
                        elem.check()
                else:
                    elem.fill(value)

                filled[field_key] = value
            except Exception:
                continue

        return filled

    # ── Private ──────────────────────────────────────────────────────────

    def _identify(self, elem) -> str | None:
        """Try to match an element to a known field key."""
        clues: list[str] = []
        for attr in ("name", "id", "placeholder", "aria-label"):
            val = elem.get_attribute(attr)
            if val:
                clues.append(val.lower())

        # Try to find an associated <label>
        elem_id = elem.get_attribute("id")
        if elem_id:
            try:
                label = elem.evaluate(
                    "(el) => {"
                    "  const lbl = document.querySelector("
                    f"    'label[for=\"{elem_id}\"]'"
                    "  );"
                    "  return lbl ? lbl.innerText : '';"
                    "}"
                )
                if label:
                    clues.append(label.lower())
            except Exception:
                pass

        combined = " ".join(clues)
        for key, keywords in _FIELD_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return key
        return None

    def _value_for(self, key: str) -> str | None:
        p = self.profile
        mapping: dict[str, str] = {
            "first_name": p.first_name,
            "last_name": p.last_name,
            "email": p.email,
            "phone": p.phone,
            "location": p.location,
            "github": p.github,
            "website": p.website,
            "experience": p.years_experience,
            "current_title": p.current_title,
            "current_company": p.current_company,
            "salary": p.desired_salary,
            "start_date": p.start_date,
            "education": p.education,
            "authorization": p.work_authorization,
            "relocate": p.willing_to_relocate,
            "hear_about": "Job board",
        }
        return mapping.get(key)
