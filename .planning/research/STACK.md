# Technology Stack: Milestone 2 Additions

**Project:** Job Search Automation
**Researched:** 2026-02-07
**Scope:** Additional libraries needed beyond the existing working stack

## Existing Stack (Not Re-researched)

Already installed and working:

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ (running on 3.14) | Runtime |
| Playwright | >=1.58.0 | Browser automation |
| playwright-stealth | >=2.0.1 | Anti-detection |
| httpx | >=0.27.0 | Async HTTP (RemoteOK) |
| Pydantic | >=2.0.0 | Data models |
| python-dotenv | >=1.0.0 | Env loading |
| python-jobspy | >=1.1.0 | Supplementary scraping |
| FastAPI | >=0.115.0 | Web dashboard |
| uvicorn | >=0.34.0 | ASGI server |
| Jinja2 | >=3.1.0 | HTML templating |
| python-multipart | >=0.0.18 | Form parsing |
| htmx | 2.0.4 (CDN) | Frontend interactivity |
| Tailwind CSS | CDN (play) | Styling |
| SQLite | stdlib | Database |

---

## New Dependencies: Recommended Stack

### 1. AI / LLM Integration

#### anthropic (Python SDK)

| Field | Value |
|-------|-------|
| Package | `anthropic` |
| Version | `>=0.78.0` |
| Purpose | Resume tailoring, intelligent job scoring, cover letter generation |
| Confidence | HIGH |

**Why Anthropic/Claude:** The project owner already uses Claude Code and has Anthropic API access. Claude excels at structured text generation (resume bullet points, keyword extraction) and has strong instruction-following for "rewrite this section to highlight X." No need for a second LLM provider.

**Why NOT OpenAI:** Adding a second API dependency increases config complexity for no gain. The project is single-user; there is no need for provider abstraction or fallback. If the user later wants OpenAI as an option, the abstraction is straightforward.

**Why NOT local models (Ollama):** Resume tailoring requires high-quality prose generation. Local models produce noticeably worse output for structured professional writing. The latency tradeoff (seconds vs. minutes) matters for interactive dashboard use.

**How it will be used:**
- Extract keywords and requirements from job descriptions (structured JSON output)
- Rewrite resume Professional Summary to match a specific role
- Reorder and rephrase skill bullets to match job requirements
- Generate tailored cover letters
- Enhance job scoring with semantic matching (supplement the existing keyword scorer)

**API cost estimate:** ~$0.01-0.05 per resume tailoring (one Sonnet call with ~4K input + ~2K output). At 10-20 tailored resumes per search run, that is $0.10-1.00 per run. Negligible for a single user.

```bash
pip install anthropic>=0.78.0
```

**Source:** [anthropic on PyPI](https://pypi.org/project/anthropic/), [GitHub](https://github.com/anthropics/anthropic-sdk-python)

---

### 2. PDF Processing (Read + Write)

#### PyMuPDF (fitz) -- PDF Text Extraction

| Field | Value |
|-------|-------|
| Package | `PyMuPDF` |
| Version | `>=1.26.7` |
| Purpose | Extract text content from existing PDF resumes |
| Confidence | HIGH |

**Why PyMuPDF:** It is the fastest Python PDF text extractor, preserves document structure better than alternatives, handles multi-column layouts, and automatically cleans whitespace. The existing resume is a formatted PDF -- PyMuPDF will extract the text content that gets sent to the LLM for tailoring.

**Why NOT pdfplumber:** Slower, more dependencies, and PyMuPDF handles the same use cases better for text extraction specifically.

**Why NOT pymupdf4llm:** Adds an unnecessary abstraction layer. The resume is a simple PDF (not a complex multi-table academic paper). Direct PyMuPDF text extraction is sufficient. If markdown-formatted extraction is later needed, pymupdf4llm is a thin wrapper that can be added trivially.

```bash
pip install PyMuPDF>=1.26.7
```

**Source:** [PyMuPDF on PyPI](https://pypi.org/project/PyMuPDF/), [Documentation](https://pymupdf.readthedocs.io/)

#### WeasyPrint -- PDF Generation from HTML/CSS

| Field | Value |
|-------|-------|
| Package | `weasyprint` |
| Version | `>=68.1` |
| Purpose | Generate tailored PDF resumes from HTML+CSS templates |
| Confidence | HIGH |

**Why WeasyPrint:** The project already uses Jinja2 for HTML templating. WeasyPrint converts HTML+CSS to PDF, meaning resume templates can be built with the same Jinja2 skills used in the dashboard. It supports CSS Flexbox for layout, `@media print` for print-specific styles, and produces ATS-parseable PDFs (real text, not images). The pipeline is: Jinja2 template + tailored content data -> HTML -> WeasyPrint -> PDF.

**Why NOT ReportLab:** ReportLab requires learning a separate layout API (Platypus). For resume generation, HTML/CSS templates are more maintainable, more familiar, and easier to iterate on. ReportLab's strength (complex charts and graphics) is irrelevant for resumes.

**Why NOT fpdf2:** fpdf2 has no HTML/CSS support. You would be positioning every text element manually. That defeats the purpose of template-driven generation.

**Why NOT python-docx-template (DOCX approach):** DOCX requires Word/LibreOffice for preview and is harder to render in a web dashboard. HTML templates can be previewed in-browser before PDF generation. Also, ATS systems handle PDFs more reliably than DOCX.

**Why NOT wkhtmltopdf/pdfkit:** wkhtmltopdf is abandoned (last release 2020) and requires a binary dependency. WeasyPrint is pure Python (with minor C deps for font rendering) and actively maintained.

**System dependency note:** WeasyPrint requires system libraries for font rendering (Pango, GDK-PixBuf). On macOS: `brew install pango gdk-pixbuf libffi`. On Ubuntu: `apt install libpango-1.0-0 libgdk-pixbuf-2.0-0`. This is a one-time setup cost.

```bash
# System deps (macOS)
brew install pango gdk-pixbuf libffi

# Python package
pip install weasyprint>=68.1
```

**Source:** [WeasyPrint on PyPI](https://pypi.org/project/weasyprint/), [WeasyPrint.org](https://weasyprint.org/)

---

### 3. Configuration System

#### pydantic-settings + PyYAML

| Field | Value |
|-------|-------|
| Package | `pydantic-settings[yaml]` |
| Version | `>=2.12.0` |
| Purpose | Type-safe YAML config file loading with env override |
| Confidence | HIGH |

| Field | Value |
|-------|-------|
| Package | `PyYAML` |
| Version | `>=6.0.3` |
| Purpose | YAML parsing (required by pydantic-settings YAML source) |
| Confidence | HIGH |

**Why pydantic-settings:** The project already uses Pydantic v2 for data models. pydantic-settings extends this with `BaseSettings` classes that load from multiple sources (YAML file, environment variables, .env files) with a defined priority order. This replaces the current hardcoded `Config` class in `config.py` with a user-editable YAML file while keeping full type validation.

**Why YAML (not TOML or JSON):**
- YAML supports comments (critical for self-documenting config files that new users will edit)
- YAML is more readable for nested structures (candidate profile, search queries, platform settings)
- TOML's flat structure is awkward for deeply nested config like per-platform selectors
- JSON does not support comments

**Why NOT a custom YAML loader:** pydantic-settings has `YamlConfigSettingsSource` built in (since v2.x). It provides type validation, default values, environment variable overrides, and nested model support out of the box. Writing a custom loader would duplicate all of this.

**Architecture:** The source priority order will be:
1. Environment variables (highest -- for secrets like passwords)
2. `.env` file (convenience for credentials)
3. `config.yaml` (user-editable settings -- search queries, candidate profile, platform config)
4. Defaults in the Pydantic model (fallback)

This means credentials stay in `.env` (gitignored) while everything else lives in `config.yaml` (version-controllable, human-readable).

```bash
pip install "pydantic-settings[yaml]>=2.12.0"
# PyYAML is pulled in by the [yaml] extra
```

**Source:** [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/), [Pydantic docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [PyYAML on PyPI](https://pypi.org/project/PyYAML/)

---

### 4. Dashboard Polish

#### Alpine.js -- Client-Side Interactivity

| Field | Value |
|-------|-------|
| Package | Alpine.js (CDN, no pip install) |
| Version | `3.15.x` |
| Purpose | Client-side UI interactions (dropdowns, modals, toggles, search filtering) |
| Confidence | HIGH |

**Why Alpine.js:** The dashboard already uses htmx for server-driven interactions. Alpine.js complements htmx perfectly for *client-side* behavior: dropdown menus, modal dialogs (confirm apply, preview resume), toggle panels, and instant client-side search filtering. Together they eliminate the need for React/Vue/any build step.

**Why NOT more htmx:** htmx requires a server round-trip for every interaction. Opening a dropdown menu or toggling a panel should not hit the server. Alpine handles these purely client-side at ~17KB.

**Why NOT hyperscript:** Hyperscript (from the htmx team) is still labeled experimental. Alpine.js has a much larger ecosystem, better documentation, and more community examples.

**Why NOT React/Vue/Svelte:** The project uses server-rendered Jinja2 templates. Adding a JavaScript framework would require a build step (Vite/webpack), a separate frontend codebase, and API endpoints. The existing htmx + Jinja2 approach is simpler and works well for a single-user tool. Alpine.js adds the missing client-side interactivity without any build step.

```html
<!-- Add to base.html <head> -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15/dist/cdn.min.js"></script>
```

**Source:** [Alpine.js](https://alpinejs.dev/), [GitHub releases](https://github.com/alpinejs/alpine/releases)

#### Tailwind CSS (Standalone CLI) -- Replace CDN

| Field | Value |
|-------|-------|
| Package | Tailwind CSS standalone CLI binary |
| Version | `4.x` |
| Purpose | Production CSS build (replaces CDN play script) |
| Confidence | MEDIUM |

**Why replace the CDN:** The current `<script src="https://cdn.tailwindcss.com">` is the Tailwind "Play CDN" meant for prototyping. It works but: (a) requires internet connection, (b) generates CSS at runtime in the browser (slower first paint), (c) cannot use custom Tailwind config or plugins, (d) adds ~300KB to every page load.

**Why standalone CLI (not npm):** The project is Python-only. Adding Node.js as a build dependency just for CSS is unnecessary overhead. The standalone CLI is a single binary (~40MB) with zero dependencies. Download it, run it, done.

**How it works:** Run `tailwindcss -i input.css -o static/style.css --watch` during development. The output CSS file is served statically by FastAPI. No Node.js needed.

**When to do this:** This is a polish item, not blocking. The CDN approach works fine for now. Move to standalone CLI when the dashboard has stabilized and is ready for "production" use.

```bash
# macOS ARM64
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64
mv tailwindcss-macos-arm64 ./tailwindcss
```

**Source:** [Tailwind CLI docs](https://tailwindcss.com/docs/installation/tailwind-cli), [GitHub releases](https://github.com/tailwindlabs/tailwindcss/releases)

---

### 5. Markdown Rendering (Job Descriptions in Dashboard)

#### markdown (or markdown-it-py) -- Already have markdownify

| Field | Value |
|-------|-------|
| Package | `markdown` |
| Version | `>=3.7` |
| Purpose | Render job description markdown to HTML in the dashboard |
| Confidence | MEDIUM |

**Note:** The project already has `markdownify` (0.13.1) installed, which converts HTML *to* markdown. For the reverse (rendering markdown descriptions as formatted HTML in the dashboard), the `markdown` library or a Jinja2 filter is needed.

**Why:** Job descriptions stored as markdown (from the scraping pipeline) need to render as formatted HTML in the job detail view. Currently the raw text is displayed. A Jinja2 filter using the `markdown` library would handle this.

**Alternative:** Use `markdownify` in reverse with `beautifulsoup4` -- but this is backwards. The `markdown` library is the standard tool for markdown-to-HTML.

```bash
pip install markdown>=3.7
```

**Source:** [Markdown on PyPI](https://pypi.org/project/Markdown/)

---

## Libraries Explicitly NOT Recommended

| Library | Why Not |
|---------|---------|
| **LangChain/LangGraph** | Massive dependency tree (100+ packages) for what amounts to one API call. The resume tailoring pipeline is: extract text -> send to Claude -> parse response. That is 10 lines of code with the anthropic SDK. LangChain adds orchestration complexity with zero benefit for this use case. |
| **openai** | Adding a second LLM provider doubles the config surface. The user already has Anthropic access. If multi-provider is later needed, add it then. |
| **Ollama/local LLMs** | Resume prose quality matters. Local 7B models produce noticeably worse professional writing than Claude Sonnet. The cost difference ($0.05/resume vs. free) is negligible for a single user. |
| **Selenium** | Playwright is already in use and is strictly superior (faster, auto-wait, better debugging). |
| **BeautifulSoup4** | Already using Playwright for DOM parsing. Adding BS4 for HTML parsing is redundant -- Playwright's page.query_selector_all() handles the same job. |
| **SQLAlchemy** | The database is SQLite with 5 queries. Raw SQL with sqlite3 stdlib is simpler and already works. SQLAlchemy would be warranted if migrating to PostgreSQL or adding complex relationships, but neither is planned. |
| **Celery/RQ** | Task queue for a single-user tool is over-engineering. The orchestrator runs synchronously (intentionally -- for human-in-the-loop checkpoints). Background job processing is not needed. |
| **React/Vue/Svelte** | Requires build tooling, separate frontend codebase, and API endpoints. htmx + Alpine.js achieves the same result for a single-user dashboard with zero build step. |
| **stevedore** | Python plugin framework from OpenStack. Massive for what we need. The pluggable platform architecture only needs Python's stdlib `importlib` with a simple registry pattern. Three platforms (Indeed, Dice, RemoteOK) do not justify a plugin framework. |
| **pydantic-settings-yaml** | Third-party wrapper. Unnecessary -- pydantic-settings has built-in `YamlConfigSettingsSource` support. |

---

## Pluggable Platform Architecture: No New Library Needed

The current `BasePlatform` ABC in `platforms/base.py` is already 80% of a plugin system. To make platforms pluggable:

1. Add a `PLATFORM_REGISTRY` dict in `platforms/__init__.py`
2. Each platform module registers itself on import
3. `config.yaml` lists enabled platforms
4. The orchestrator iterates over enabled platforms from the registry

This requires zero new dependencies. Python's `importlib.import_module()` (stdlib) handles dynamic loading if needed. The three existing platforms do not warrant a full plugin framework.

**Confidence:** HIGH -- This is a standard Python pattern, no external library needed.

---

## ATS Form Filling: Architecture, Not Libraries

The current `FormFiller` in `form_filler.py` uses keyword matching to identify form fields. For diverse ATS platforms (Greenhouse, Lever, Ashby), the approach should be:

1. **ATS detection:** Identify which ATS hosts the application page (URL patterns: `boards.greenhouse.io`, `jobs.lever.co`, `jobs.ashbyhq.com`)
2. **Per-ATS selector modules:** Like the existing `indeed_selectors.py` and `dice_selectors.py`, create `greenhouse_selectors.py`, `lever_selectors.py`, `ashby_selectors.py`
3. **Fallback to generic:** The existing heuristic `FormFiller` serves as the fallback for unknown ATS platforms

This is an architectural pattern, not a library decision. Playwright (already installed) handles all the form interaction. The intelligence is in the selectors and the field-matching logic.

**Enhancement with LLM:** For truly unknown forms, Claude can analyze the page DOM (sent as simplified HTML) and return a field mapping. This uses the `anthropic` SDK already recommended above.

**Confidence:** MEDIUM -- ATS selectors change frequently. The per-ATS approach is well-understood, but maintaining selectors is ongoing work (same challenge as Indeed/Dice selectors today).

---

## Complete New Dependencies

### pyproject.toml additions

```toml
[project]
dependencies = [
    # ... existing deps ...

    # AI resume tailoring
    "anthropic>=0.78.0",

    # PDF processing
    "PyMuPDF>=1.26.7",
    "weasyprint>=68.1",

    # Configuration system
    "pydantic-settings[yaml]>=2.12.0",

    # Markdown rendering in dashboard
    "markdown>=3.7",
]
```

### CDN additions to base.html

```html
<!-- Alpine.js for client-side interactivity -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15/dist/cdn.min.js"></script>
```

### System dependencies (one-time setup)

```bash
# macOS (for WeasyPrint)
brew install pango gdk-pixbuf libffi

# Ubuntu/Debian (for WeasyPrint)
sudo apt install libpango-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev
```

---

## Installation Command (All New Dependencies)

```bash
pip install "anthropic>=0.78.0" "PyMuPDF>=1.26.7" "weasyprint>=68.1" "pydantic-settings[yaml]>=2.12.0" "markdown>=3.7"
```

---

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| anthropic SDK | HIGH | Verified version on PyPI (0.78.0, Feb 5 2026). Well-documented, actively maintained. |
| PyMuPDF | HIGH | Verified version on PyPI (1.26.7). Industry standard for Python PDF extraction. |
| WeasyPrint | HIGH | Verified version on PyPI (68.1, Feb 6 2026). Proven HTML-to-PDF pipeline with Jinja2. |
| pydantic-settings | HIGH | Verified version on PyPI (2.12.0). Built-in YAML support confirmed via official docs. |
| PyYAML | HIGH | Verified version on PyPI (6.0.3). Stable, universally used. |
| Alpine.js | HIGH | Verified version 3.15.x. CDN delivery, no pip dependency. Widely adopted with htmx. |
| Tailwind standalone CLI | MEDIUM | Version 4.x confirmed. This is a polish step, not blocking. CDN works fine initially. |
| markdown | MEDIUM | Standard library, verified. Low risk but might not be needed if descriptions are stored as HTML. |
| Plugin architecture (no lib) | HIGH | Standard Python pattern, stdlib only. |
| ATS form filling (no lib) | MEDIUM | Architecture is sound but ATS selectors require ongoing maintenance and live testing. |

---

## Sources

- [anthropic on PyPI](https://pypi.org/project/anthropic/) - v0.78.0 (Feb 5, 2026)
- [PyMuPDF on PyPI](https://pypi.org/project/PyMuPDF/) - v1.26.7
- [WeasyPrint on PyPI](https://pypi.org/project/weasyprint/) - v68.1 (Feb 6, 2026)
- [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/) - v2.12.0
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - YamlConfigSettingsSource
- [PyYAML on PyPI](https://pypi.org/project/PyYAML/) - v6.0.3
- [Alpine.js](https://alpinejs.dev/) - v3.15.x
- [Tailwind CSS releases](https://github.com/tailwindlabs/tailwindcss/releases) - v4.x
- [htmx releases](https://github.com/bigskysoftware/htmx/releases) - current 2.0.x
- [Python Packaging Guide: Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- [WeasyPrint + Jinja2 resume generation](https://medium.com/@engineering_holistic_ai/using-weasyprint-and-jinja2-to-create-pdfs-from-html-and-css-267127454dbd)
- [LLM resume tailoring approaches](https://github.com/ramansrivastava/resume-tailoring-agent)
- [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
