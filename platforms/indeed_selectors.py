"""Indeed.com DOM selectors — isolated for easy updates.

Indeed changes selectors frequently.  If automation breaks, update here first.
Last verified: 2026-02-06
"""

INDEED_SELECTORS: dict[str, str] = {
    # Authentication
    "login_email": "#ifl-InputFormField-3",
    "login_password": "#ifl-InputFormField-7",
    "login_submit": "button[type='submit']",
    "logged_in_indicator": "[data-gnav-element-name='AccountMenu'], #AccountMenu",
    # Search results
    "job_card": "div.job_seen_beacon",
    "title": "h2.jobTitle a span, .jobTitle span",
    "title_link": "h2.jobTitle a, .jobTitle a",
    "company": "[data-testid='company-name'], .companyName",
    "location": "[data-testid='text-location'], .companyLocation",
    "salary": "[data-testid='attribute_snippet_testid'], .salary-snippet",
    "posted_date": "[data-testid='myJobsStateDate'], .date",
    # Job detail
    "job_description": "#jobDescriptionText, .jobsearch-jobDescriptionText",
    "apply_button": (
        "button[id*='indeedApply'], .indeed-apply-button, button:has-text('Apply now')"
    ),
    # Application flow
    "resume_upload": "input[type='file'][accept*='pdf']",
    "submit_application": (
        "button:has-text('Submit application'), button[type='submit']:has-text('Submit')"
    ),
    # Error / challenge detection
    "captcha_frame": "iframe[title*='recaptcha'], iframe[src*='captcha']",
    "cloudflare_challenge": ".cf-browser-verification, #cf-wrapper",
    "email_verification": "text='verify your email', text='verification code'",
}

INDEED_URLS: dict[str, str] = {
    "base": "https://www.indeed.com",
    "login": "https://secure.indeed.com/auth",
    "search": "https://www.indeed.com/jobs",
}

# Indeed search URL parameters fall into two categories:
#
# STABLE / EXPLICIT — safe to construct programmatically:
#   q, l, fromage, salaryType, sort
#
# OPAQUE / INTERNAL — UI-driven blobs, capture from browser, don't generate:
#   sc  (encodes Remote, Easy Apply, Urgently Hiring, etc.)
#       e.g. sc=0kf:attr(DSQF7);  →  Remote filter ON
#       DSQF7 is Indeed's internal attribute ID for remote jobs.
#       This value disappears entirely when Remote is unchecked.
#
# If the remote filter stops working, re-capture the sc value by clicking
# the Remote pill in the browser and copying the sc= param from the URL.

INDEED_SEARCH_PARAMS: dict[str, str] = {
    # Opaque — captured from Indeed UI (2026-02-07)
    "remote_filter": "sc=0kf%3Aattr%28DSQF7%29%3B",
    # Stable / explicit
    "recency_14d": "fromage=14",
    "sort_date": "sort=date",
}
