"""Dice.com DOM selectors — isolated for easy updates.

Last verified: 2026-02-06 (live DOM inspection via Chrome DevTools)
"""

DICE_SELECTORS: dict[str, str] = {
    # Authentication
    "login_email": "input[type='email'], input[name='email']",
    "login_continue": "button:has-text('Continue'), button[type='submit']",
    "login_password": "input[type='password'], input[name='password']",
    "login_submit": "button:has-text('Sign In'), button:has-text('Log In'), button[type='submit']",
    # Search results
    "job_card": "[data-testid='job-card']",
    "title": "[data-testid='job-search-job-detail-link']",
    "company_link": "a[href*='company-profile']",
    # Job detail
    "job_description": "div[class*='jobDescription']",
    "apply_button": "[data-testid='apply-button']",
    # Application flow
    "resume_upload": "input[type='file']",
    "submit_application": ("button:has-text('Submit Application'), button[type='submit']"),
}

DICE_URLS: dict[str, str] = {
    "base": "https://www.dice.com",
    "login": "https://www.dice.com/dashboard/login",
    "search": "https://www.dice.com/jobs",
}

DICE_SEARCH_PARAMS: dict[str, str] = {
    "remote_filter": "filters.workplaceTypes=Remote",
    "recency_1d": "filters.postedDate=ONE",
    "recency_3d": "filters.postedDate=THREE",
    "recency_7d": "filters.postedDate=SEVEN",
    "easy_apply": "easyApply=true",
}
