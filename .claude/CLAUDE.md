# Job Search Automation — Patryk Golabek

## Project Purpose

This project is a code harness for automating job search discovery and application
across Indeed, Dice, and RemoteOK. It is designed to be operated by Claude Code
agent teams, where parallel teammates each own a platform-specific module and
coordinate through a shared task list.

## Agent Team Configuration

Enable agent teams before running any workflow:

```json
// ~/.claude/settings.json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Team Structure

When executing job search workflows, spawn an agent team with this structure:

| Teammate | Domain | Owns Files |
|----------|--------|------------|
| **Lead (you)** | Orchestration, scoring, human-in-the-loop | `orchestrator.py`, `scorer.py`, `tracker.md` |
| **Indeed Teammate** | Indeed search + Easy Apply automation | `platforms/indeed.py`, `platforms/indeed_selectors.py` |
| **Dice Teammate** | Dice search + Easy Apply automation | `platforms/dice.py`, `platforms/dice_selectors.py` |
| **RemoteOK Teammate** | RemoteOK API + redirect handling | `platforms/remoteok.py` |

Each teammate loads this CLAUDE.md automatically. Teammates work independently
on their platform and report discovered jobs back to the lead for scoring.

### Teammate Spawn Prompt Template

```
Create an agent team for job search execution:
- Indeed teammate: Run Indeed search using the harness in platforms/indeed.py.
  Search all queries from CLAUDE.md. Extract jobs, score them, save to
  job_pipeline/discovered_jobs.json. Pause on CAPTCHA — screenshot and report.
- Dice teammate: Run Dice search using platforms/dice.py. Same queries,
  same output format. Dice has weaker anti-bot — standard delays sufficient.
- RemoteOK teammate: Query the RemoteOK API using platforms/remoteok.py.
  Filter by tags matching our tech stack. Same output format.

Coordinate through the shared task list. When all searches complete,
I will synthesize results, deduplicate, score, and present top matches
for human approval before any applications.
```

---

## Human-in-the-Loop Checkpoints

These are non-negotiable. The agent must STOP and wait for human input at each:

1. **CAPTCHA / Cloudflare challenge during login** → screenshot, report, wait
2. **Email or SMS verification** → report, wait for human to complete
3. **Before submitting ANY application** → display job title, company, salary, match score, and wait for explicit "yes"
4. **When selectors fail** → screenshot to `debug_screenshots/`, report before retrying
5. **When credentials are missing** → report and skip that platform entirely
6. **Before uploading resume** → confirm which resume version to use

---

## Directory Structure

```
project-root/
├── .claude/
│   ├── CLAUDE.md                      # This file — single source of truth
│   └── agents/                        # Subagent definitions
│       ├── platform-scout.md
│       ├── job-scorer.md
│       └── resume-tailor.md
├── platforms/
│   ├── __init__.py
│   ├── base.py                        # Abstract base: login, search, extract, apply
│   ├── stealth.py                     # Browser context factory with anti-detection
│   ├── indeed.py                      # Indeed: Playwright + stealth
│   ├── indeed_selectors.py            # Indeed DOM selectors (isolated for easy update)
│   ├── dice.py                        # Dice: Playwright
│   ├── dice_selectors.py              # Dice DOM selectors
│   └── remoteok.py                    # RemoteOK: pure HTTP API
├── orchestrator.py                    # Pipeline entry point: search → score → apply
├── scorer.py                          # Job scoring against candidate profile
├── form_filler.py                     # Generic form-filling logic
├── models.py                          # Pydantic models: Job, SearchQuery, CandidateProfile
├── config.py                          # Environment loading, search queries, platform config
├── requirements.txt
├── README.md                          # Usage instructions
├── browser_sessions/                  # Persistent Playwright sessions (gitignored)
├── webapp/
│   ├── app.py                         # FastAPI web dashboard
│   ├── db.py                          # SQLite database layer
│   └── templates/                     # Jinja2 + htmx templates
├── job_pipeline/                      # Output directory (auto-created)
│   ├── jobs.db                        # SQLite database (web dashboard)
│   ├── raw_{platform}.json            # Raw results per platform
│   ├── discovered_jobs.json           # All deduplicated jobs scoring 3+
│   ├── tracker.md                     # Summary table of scored jobs
│   └── descriptions/                  # Full job descriptions as markdown
├── debug_screenshots/                 # Error/debug screenshots (auto-created)
├── resumes/
│   ├── Patryk_Golabek_Resume_ATS.pdf  # Default resume
│   ├── Patryk_Golabek_Resume.pdf      # Standard version
│   └── tailored/                      # Per-company tailored versions
└── .env                               # Credentials (gitignored, never committed)
```

---

## Automation Stack

**Runtime:** Python 3.11+
**Browser automation:** Playwright with `playwright-stealth` plugin
**HTTP client:** `httpx` (async) for RemoteOK API
**Data models:** Pydantic v2
**Web dashboard:** FastAPI + Jinja2/htmx + SQLite (local job tracker at `localhost:8000`)
**Supplementary scraper:** `python-jobspy` for broader Indeed/LinkedIn discovery (optional)

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### Stealth Configuration

All browser automation uses `playwright-stealth` 2.0.1+ with system Chrome to
reduce detection. See `platforms/stealth.py` for the full implementation.

Key anti-detection measures:
- `channel="chrome"` — uses system Chrome instead of Playwright's bundled Chromium (Google blocks OAuth in automation-detected browsers)
- `ignore_default_args=["--enable-automation"]` — removes the automation flag
- `args=["--disable-blink-features=AutomationControlled"]` — hides automation control
- `playwright-stealth` 2.0.1 API: `Stealth().apply_stealth_sync(page)` (not the old `stealth_sync(page)`)

### Browser Automation Rules

1. **Session persistence:** Always use `launch_persistent_context()` with per-platform user data directory.
2. **Human-in-the-loop for CAPTCHA:** If CAPTCHA, Cloudflare challenge, or email verification detected — STOP and ask human. Never attempt bypass.
3. **Rate limiting:** 2–5 seconds randomized delay between page navigations. 1–2 seconds between form interactions.
4. **Screenshots on failure:** On selector failure or unexpected page state, save screenshot to `debug_screenshots/` and report.
5. **Credentials from environment:** Always load from `.env` via `python-dotenv`. If missing, skip platform.
6. **Application confirmation:** Before ANY submit button — present job details to human, wait for explicit approval.
7. **Selector verification:** Selectors change frequently. Verify elements exist before interaction. If not found, inspect page content to discover new selectors. Log changes.

---

## Credentials

Stored in `.env` (never committed):

```env
# Indeed — session-based Google auth (no password needed)
INDEED_EMAIL=pgolabek@gmail.com

# Dice — email + password login
DICE_EMAIL=pgolabek@gmail.com
DICE_PASSWORD=<your-password>
```

Loaded via `config.py` using `python-dotenv`. Indeed uses Google OAuth —
on first run, the browser opens for manual login, then the session is cached
in `browser_sessions/indeed/` for future runs.

---

## Platform Reference

### Indeed (indeed.com)

**Anti-bot level:** HIGH — Cloudflare Turnstile, fingerprinting, behavioral analysis

| Item | Value |
|------|-------|
| Login URL | `https://secure.indeed.com/auth` |
| Login flow | Google OAuth — manual login on first run, session cached afterward. May trigger CAPTCHA. |
| Search URL | `https://www.indeed.com/jobs?q={query}&l={location}&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11&fromage=14&sort=date` |
| Remote filter | `remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11` |
| Recency filter | `fromage=14` (14 days) |
| Sort | `sort=date` (newest first) |

**Selectors (last verified 2026-02-06 — see `platforms/indeed_selectors.py` for current values):**

Key selector notes:
- `job_card`: use `div.job_seen_beacon` only (NOT `[data-jk]` which also matches bare `<a>` elements)
- `data-jk` attribute lives on the `<a>` tag inside `h2.jobTitle`, not on the card wrapper
- ~50% of cards have bogus `data-jk` values (`fedcba9876543210` pattern) that produce 404 pages
- 404 detail pages have title `"Not Found | Indeed"` — detect and skip

**Apply flow:** Multi-step form. Uses profile resume if uploaded to Indeed. Look for "Apply now" or "Indeed Apply" button.

### Dice (dice.com)

**Anti-bot level:** LOW — Standard delays sufficient, no CAPTCHA reported

| Item | Value |
|------|-------|
| Login URL | `https://www.dice.com/dashboard/login` |
| Login flow | Two-step: email → "Continue" → password → "Sign In". Redirects to `/dashboard` on success. |
| Search URL | `https://www.dice.com/jobs?q={query}&location=Remote&radius=30&radiusUnit=mi&page=1&pageSize=20&filters.postedDate=SEVEN&filters.workplaceTypes=Remote&language=en` |
| Remote filter | `filters.workplaceTypes=Remote` |
| Recency filter | `filters.postedDate=ONE` (24h), `THREE` (3d), `SEVEN` (7d) |
| Easy Apply filter | `&easyApply=true` |

**Selectors (last verified 2026-02-06 — see `platforms/dice_selectors.py` for current values):**

Key selector notes:
- Dice migrated to React with `data-testid` attributes. Old `dhi-search-card` and `[data-cy=...]` selectors are ALL gone.
- `job_card`: `[data-testid='job-card']` with `data-id` (hash) and `data-job-guid` (UUID used in detail URLs)
- `title`: `[data-testid='job-search-job-detail-link']`
- `company`: `a[href*='company-profile']` — pick the link with visible text (not "Company Logo")
- Location/salary are NOT in dedicated elements — parse from `card.inner_text()`
- Easy Apply: detected by "Easy Apply" text in card content
- Job description on detail page: `div[class*='jobDescription']` (CSS modules class)
- `is_logged_in()` uses URL check (`/login` not in url), NOT DOM selectors
- Salary format: `"USD 224,400.00 - 283,800.00 per year"` or `"$175000"`

**Apply flow:** "Easy Apply" button on job detail page (`[data-testid='apply-button']`). Single form, auto-fills from Dice profile.

### RemoteOK (remoteok.com)

**Anti-bot level:** NONE — Public API, no auth required

| Item | Value |
|------|-------|
| API endpoint | `GET https://remoteok.com/api` |
| Auth | None |
| Rate limit | Be polite — include User-Agent header |
| Data delay | 24 hours behind real-time |

**API response format:**
```python
# Response is a JSON array. Index 0 is legal/metadata. Jobs start at index 1.
# Each job object:
{
    "id": int,
    "slug": str,
    "epoch": int,
    "date": str,           # ISO format
    "company": str,
    "company_logo": str,
    "position": str,        # Job title
    "tags": [str],          # e.g., ["python", "react", "kubernetes"]
    "description": str,     # Full HTML description
    "location": str,
    "salary_min": int,
    "salary_max": int,
    "apply_url": str,       # Redirect URL to company's career page
    "url": str,             # RemoteOK listing URL
}
```

**Apply flow:** RemoteOK has no built-in apply. `apply_url` redirects to the company's external ATS (Lever, Greenhouse, Ashby, etc.). Each company's apply page is different — requires generic form-filling logic.

---

## Candidate Profile

### Contact Information

| Field | Value |
|-------|-------|
| Name | Patryk Golabek |
| Email | pgolabek@gmail.com |
| Phone | 416-708-9839 |
| Location | Springwater, ON, Canada |
| GitHub (Personal) | https://github.com/PatrykQuantumNomad |
| GitHub (Company) | https://github.com/TranslucentComputing |
| YouTube | https://www.youtube.com/@TranslucentComputing |
| Blog | https://mykubert.com/blog |
| Company Blog | https://translucentcomputing.com/blog |

### Target Roles

**Primary titles:**
- Senior Software Engineer
- Principal Engineer
- Staff Engineer
- Platform Engineering Lead
- DevOps Lead
- Engineering Manager (Platform/Infrastructure)

**Industries:** Any
**Location:** Remote (primary), Hybrid within Ontario (secondary)
**Compensation:** $200K+ USD (or CAD equivalent)

### Application Form Field Mapping

When filling application forms, use these values:

| Field | Value |
|-------|-------|
| First Name | Patryk |
| Last Name | Golabek |
| Email | pgolabek@gmail.com |
| Phone | 416-708-9839 |
| Location / City | Springwater, ON, Canada |
| LinkedIn | [leave blank if not set] |
| GitHub / Portfolio | https://github.com/TranslucentComputing |
| Website | https://mykubert.com |
| Years of Experience | 17+ |
| Current Title | Co-Founder & CTO |
| Current Company | Translucent Computing Inc. |
| Work Authorization | Authorized to work in Canada. May require sponsorship for US roles. |
| Willing to Relocate | No (remote preferred) |
| Desired Salary | $200,000+ USD (adjust to CAD equivalent if Canadian role) |
| Start Date | Available immediately / 2 weeks notice |
| Education | Bachelor's degree in Computer Science |
| Resume File | resumes/Patryk_Golabek_Resume_ATS.pdf |
| How did you hear? | Job board (Indeed/Dice/RemoteOK as applicable) |

**Form filling rules:**
- For "Are you authorized to work in [country]?" on US roles — answer honestly: may need sponsorship.
- For diversity / voluntary self-identification — select "Prefer not to answer" or skip if optional.
- For "Do you have experience with X?" — check the Technical Skills section below. If listed, answer Yes.
- NEVER fabricate experience or qualifications.

---

## Key Differentiators

### Technical Leadership
- 17+ years across healthcare, fintech, cloud infrastructure
- Co-Founder & CTO of Translucent Computing Inc. (15 years)
- Secured $1.2M in IRAP and client funding
- Led cross-functional engineering teams (up to 4 dev teams)

### Kubernetes Expertise
- **Pre-1.0 Kubernetes adopter** — rare and valuable differentiator
- Multi-cloud: GKE, EKS, AKS
- Full GitOps: Terraform, Terragrunt, Atlantis
- Production observability: Prometheus, Grafana, Loki, Falco, OpenCost

### AI/ML & Agentic AI
- **LangFlow contributor:** 86-commit PR (#7346) — SSO/Keycloak, Prometheus monitoring
- Kubert AI Platform: open-source agentic AI for Kubernetes operations
- LangGraph, LangChain, multi-agent orchestration
- Production AI systems at fiscal.ai and Benee-fit

### Research & Publications
- **CNN+LSTM deep learning research** at SickKids Hospital
- "Early Detection of Late-Onset Neonatal Sepsis Using Minimal Physiological Features"
- Predicted sepsis 24 hours before clinical diagnosis

### Content Creator
- Active YouTube channel with live coding streams
- Featured webinar: "Masterclass: Build a Production-Ready Kubernetes Slack Bot with DevSpace"
- Published author on Agentic AI, DevOps, Apache Airflow

---

## Technical Skills Summary

**Platform & Cloud:**
Kubernetes (GKE, EKS, AKS, kind), Terraform, Terragrunt, Atlantis, Helm, DevSpace, Calico, Linkerd, GCP Cloud Composer, AWS (Lambda, SQS)

**AI/ML:**
LangGraph, LangChain, LangFlow, OpenAI/Anthropic/Gemini APIs, Ollama, Crawl4AI, TensorFlow/Keras (CNN, LSTM), RAG, multi-agent orchestration

**Data & Workflow:**
Apache Airflow, GCP Cloud Composer, PostgreSQL, Redis, Elasticsearch, Kafka, ETL/data pipelines

**Backend:**
Python (FastAPI, Celery, SQLAlchemy, Slack Bolt), Java (Spring Boot), Go, TypeScript

**DevSecOps:**
GitOps, Cloud Build, GitHub Actions, BATS, pytest, testcontainers, Prometheus, Grafana, Loki, Falco, Vault, Keycloak

**Frontend:**
Next.js 15, React 19, TypeScript, TailwindCSS, Angular, shadcn/ui

---

## Key Projects to Highlight

### Open Source
1. **LangFlow PR #7346** — 86 commits, SSO/Keycloak, Prometheus/OpenTelemetry
2. **kubert-assistant-lite** — Agentic AI for Kubernetes operations
3. **webinar-slack-bot** — Production Slack bot with FastAPI, K8s deployment
4. **kps-graph-agent** — LangGraph-based agent
5. **kps-cluster-deployment** — Terraform GKE provisioning
6. **kps-observability-package** — Full observability stack

### Healthcare
- SickKids LONS Research (CNN+LSTM sepsis detection)
- SickKids Legacy Data (500M+ records migration)
- TEKStack Health (SMART-on-FHIR HIE)
- CALIPER, SSPedi, Brain Tumour Bank

### Fintech
- Wippy Pay (BNPL ecosystem, 4 dev teams)
- fiscal.ai (Agentic AI web scraping)

---

## Search Queries

Use across all platforms, adapted to each platform's URL encoding:

```
"Principal Engineer" Kubernetes remote
"Staff Engineer" platform engineering remote
"DevOps Lead" Kubernetes cloud infrastructure
"Platform Engineering Lead" AI ML
"Engineering Manager" infrastructure cloud remote
"Staff Engineer" agentic AI LLM
"Principal Engineer" healthcare technology
"DevOps Lead" fintech cloud native
"Senior Engineer" Kubernetes platform
"Staff Software Engineer" cloud native remote
```

---

## Match Scoring Rubric

| Score | Criteria |
|-------|----------|
| **5** | Title match + tech stack overlap (K8s, AI/ML, cloud) + remote + senior level + $200K+ range |
| **4** | Title match + partial tech overlap + remote + senior level |
| **3** | Related title + some tech overlap + remote or Ontario hybrid |
| **2** | Tangentially related + limited overlap |
| **1** | Minimal relevance |

**Workflow rules:**
- Score 4–5 → present to human for application approval
- Score 3 → record for manual review
- Score 1–2 → log but do not act

---

## Resume & Cover Letter

### Resume Location
- **ATS-optimized (default):** `resumes/Patryk_Golabek_Resume_ATS.pdf`
- **Standard:** `resumes/Patryk_Golabek_Resume.pdf`

### ATS Best Practices
- No tables in skills section (use plain text with category labels)
- Expand acronyms on first use (e.g., "Google Kubernetes Engine (GKE)")
- Standard section headers: PROFESSIONAL SUMMARY, TECHNICAL SKILLS, WORK EXPERIENCE
- Contact info in body text, not headers/footers
- Calibri font, 10–12pt body, 14–16pt headers
- Quantify achievements with metrics

### Tailoring Resume for a Role
1. Read the job description
2. Identify key requirements and keywords
3. Adjust Professional Summary to match
4. Reorder skills to prioritize what the role needs
5. Emphasize relevant projects
6. Expand all acronyms from the job posting
7. Save as: `resumes/tailored/Patryk_Golabek_Resume_{CompanyName}.pdf`

### Cover Letter Guidelines
- Open with specific interest in the company/role
- Highlight 2–3 most relevant achievements with metrics
- Connect experience to their specific tech stack
- Mention open-source contributions (LangFlow, Kubert)
- Reference content creation if relevant (YouTube, blogs)
- Keep to one page

---

## Running the Pipeline

```bash
# All platforms
python orchestrator.py

# Select platforms
python orchestrator.py --platforms indeed remoteok

# Headed mode (visible browser for debugging)
python orchestrator.py --platforms indeed --headed
```

### Pipeline Phases

| Phase | Description |
|-------|-------------|
| **0 - Setup** | Validates Python version, credentials, creates output directories |
| **1 - Login** | Opens persistent browser context per platform, uses cached sessions |
| **2 - Search** | Runs 10 search queries per platform, extracts cards, fetches descriptions |
| **3 - Score** | Deduplicates by title+company, scores 1-5, saves results to `job_pipeline/` |
| **4 - Apply** | Presents 4+ scoring jobs for human approval, handles Easy Apply flow |

Raw results are saved per-platform (`raw_indeed.json`, etc.) before scoring.
Final scored results go to `discovered_jobs.json` and `tracker.md`.

### Web Dashboard

```bash
# Start the dashboard (SQLite-backed job tracker)
python -m webapp.app
# Open http://127.0.0.1:8000

# Stop the server
# Ctrl+C in the terminal, or:
pkill -f "uvicorn webapp.app"
```

The dashboard imports pipeline JSON results into SQLite, lets you filter by
score/platform/status, view full descriptions, update application status, and add notes.

---

## Notes

- 2-page resume format preferred
- ATS optimization is critical (no tables, expanded acronyms)
- "Pre-1.0 Kubernetes adopter" is a strong differentiator — always highlight
- 86-commit LangFlow contribution shows sustained open-source engagement
- SickKids research adds credibility for ML/AI roles