# Job Search Automation

Automated job discovery across Indeed, Dice, and RemoteOK with scoring, deduplication, and human-in-the-loop application flow.

## Quick Start

```bash
# 1. Install UV (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync
uv run playwright install chromium

# 3. Configure credentials
cp .env.example .env
# Edit .env with your Indeed email and Dice credentials

# 4. Run the pipeline
uv run jobs-scrape
```

## Requirements

- [UV](https://docs.astral.sh/uv/) (package manager)
- Python 3.11+ (UV installs and manages this automatically via `.python-version`)
- Google Chrome installed (used via `channel="chrome"` for stealth)

## Usage

### Full Pipeline (all platforms)

```bash
uv run jobs-scrape
```

### Select Specific Platforms

```bash
uv run jobs-scrape --platforms indeed
uv run jobs-scrape --platforms remoteok
uv run jobs-scrape --platforms indeed remoteok
uv run jobs-scrape --platforms indeed dice remoteok
```

### Headed Mode (visible browser for debugging)

```bash
uv run jobs-scrape --platforms indeed --headed
```

## Web Dashboard

View and track discovered jobs in a local web app (FastAPI + SQLite + htmx).

### Start the server

```bash
uv run jobs-web
# Open http://127.0.0.1:8000
```

### Stop the server

Press `Ctrl+C` in the terminal, or:

```bash
pkill -f "uvicorn webapp.app"
```

### Import pipeline results

Click "Import Pipeline Results" in the nav bar, or run the pipeline first and then import. The dashboard lets you filter by score/platform/status, view full job descriptions, update application status, and add notes.

## Pipeline Phases

The orchestrator runs 5 phases sequentially:

| Phase | Description |
| ------- | ------------- |
| **0 - Setup** | Validates Python version, credentials, directories |
| **1 - Login** | Opens browser, logs into Indeed/Dice (uses cached sessions) |
| **2 - Search** | Runs 10 search queries per platform, extracts job cards |
| **3 - Score** | Deduplicates across platforms, scores 1-5 based on fit |
| **4 - Apply** | Presents top jobs (4+) for human approval before applying |

## Platform Details

### Indeed

- **Auth:** Google OAuth (manual first login, session cached afterward)
- **Anti-bot:** HIGH - uses Playwright stealth + system Chrome
- **First run:** Browser opens, you log in via Google, press Enter in terminal

### Dice

- **Auth:** Email + password from `.env`
- **Anti-bot:** LOW - standard delays sufficient

### RemoteOK

- **Auth:** None required (public API)
- **Anti-bot:** None - pure HTTP, no browser needed

## Credentials (`.env`)

```env
# Indeed - Google auth (session-based, email for reference only)
INDEED_EMAIL=your@email.com

# Dice - email + password login
DICE_EMAIL=your@email.com
DICE_PASSWORD=your-password
```

## Output Files

All results are written to `job_pipeline/`:

| File | Contents |
| ------ | ---------- |
| `raw_indeed.json` | Raw Indeed results before scoring |
| `raw_dice.json` | Raw Dice results before scoring |
| `raw_remoteok.json` | Raw RemoteOK results before scoring |
| `discovered_jobs.json` | All deduplicated jobs scoring 3+ |
| `tracker.md` | Summary table of all scored jobs |
| `descriptions/{company}_{title}.md` | Full job descriptions |

## Scoring Rubric

| Score | Criteria |
| ------- | ---------- |
| **5** | Title match + tech stack overlap + remote + senior level + $200K+ |
| **4** | Title match + partial tech overlap + remote + senior level |
| **3** | Related title + some tech overlap + remote or Ontario hybrid |
| **2** | Tangentially related + limited overlap |
| **1** | Minimal relevance |

Jobs scoring 4-5 are presented for application. Score 3 logged for manual review.

## Development

### Linting & Formatting

```bash
uv run ruff check .        # lint
uv run ruff check --fix .  # lint and auto-fix
uv run ruff format .       # format
```

### Testing

```bash
uv run pytest
```

### Adding a dependency

```bash
uv add <package>           # runtime dependency
uv add --group dev <package>  # dev-only dependency
```

## Project Structure

```bash
.
├── pyproject.toml          # Project config, dependencies, scripts
├── uv.lock                 # Locked dependency versions
├── .python-version         # Python version (managed by UV)
├── orchestrator.py         # Main pipeline (uv run jobs-scrape)
├── config.py               # Environment, credentials, search queries
├── models.py               # Pydantic models (Job, SearchQuery, CandidateProfile)
├── scorer.py               # Job scoring against candidate profile
├── form_filler.py          # Generic form-filling logic
├── platforms/
│   ├── base.py             # Abstract base class for platforms
│   ├── stealth.py          # Browser context factory with anti-detection
│   ├── indeed.py           # Indeed search + Easy Apply
│   ├── indeed_selectors.py # Indeed DOM selectors (update when they change)
│   ├── dice.py             # Dice search + Easy Apply
│   ├── dice_selectors.py   # Dice DOM selectors
│   └── remoteok.py         # RemoteOK API client
├── webapp/
│   ├── app.py              # FastAPI web dashboard (uv run jobs-web)
│   ├── db.py               # SQLite database layer
│   └── templates/          # Jinja2 + htmx templates
├── job_pipeline/           # Output directory (auto-created)
├── browser_sessions/       # Persistent Playwright sessions (auto-created)
├── debug_screenshots/      # Error screenshots (auto-created)
├── resumes/                # Resume PDFs
│   └── tailored/           # Per-company tailored versions
└── .env                    # Credentials (never commit)
```

## Reset Pipeline Data

To wipe all discovered jobs and start fresh (empty database, no raw files):

```bash
rm -rf job_pipeline/jobs.db job_pipeline/jobs.db-shm job_pipeline/jobs.db-wal
rm -f job_pipeline/raw_*.json job_pipeline/discovered_jobs.json job_pipeline/tracker.md
rm -f job_pipeline/descriptions/*.md
```

The database and output files are recreated automatically the next time you run the pipeline or start the web dashboard.

## Troubleshooting

### Indeed login fails / Cloudflare challenge

Run in headed mode (`--headed`) and solve the CAPTCHA manually in the browser window. The session is cached for future runs.

### "Not Found" on Indeed detail pages

~50% of Indeed cards have bogus tracking IDs that produce 404s. These are automatically detected and skipped. Valid jobs still get full descriptions.

### Google blocks OAuth ("controlled by automated test software")

The stealth config uses `channel="chrome"` (system Chrome) with automation flags disabled. If Google still blocks, clear `browser_sessions/indeed/` and re-login.

### Selectors break (0 jobs extracted)

Indeed and Dice change their DOM frequently. Update selectors in `platforms/indeed_selectors.py` or `platforms/dice_selectors.py`. Run with `--headed` to visually inspect the page.
