# Architecture Patterns

**Domain:** Self-hosted job search automation tool (evolution from monolith to extensible system)
**Researched:** 2026-02-07
**Confidence:** HIGH (based on current codebase analysis + verified patterns)

## Current Architecture Assessment

The existing codebase is a well-structured monolith with clear separation of concerns:

```
orchestrator.py          (pipeline controller - 5 phases)
  |
  +-- config.py          (hardcoded Config class, .env credentials)
  +-- scorer.py          (weighted scoring against CandidateProfile)
  +-- form_filler.py     (heuristic label-matching form filler)
  +-- models.py          (Pydantic v2: Job, SearchQuery, CandidateProfile)
  |
  +-- platforms/
  |     base.py          (ABC: login, search, get_job_details, apply)
  |     stealth.py       (Playwright persistent context factory)
  |     indeed.py        (IndeedPlatform extends BasePlatform)
  |     dice.py          (DicePlatform extends BasePlatform)
  |     remoteok.py      (RemoteOKPlatform - standalone, no BasePlatform)
  |     *_selectors.py   (isolated DOM selectors per platform)
  |
  +-- webapp/
        app.py           (FastAPI dashboard)
        db.py            (SQLite with raw SQL)
        templates/       (Jinja2 + htmx)
```

### What Works Well (Preserve)

1. **BasePlatform ABC** -- Clean interface contract for browser-based platforms (login, search, get_job_details, apply). This is the right abstraction boundary.
2. **Selector isolation** -- DOM selectors in separate `*_selectors.py` files means selector churn does not touch business logic.
3. **Pydantic models** -- Job, SearchQuery, CandidateProfile are well-defined. Dedup logic lives on the model.
4. **Human-in-the-loop checkpoints** -- Apply flow requires explicit human confirmation before submission.
5. **Phase-based pipeline** -- Clear mental model: setup, login, search, score, apply.

### What Needs Evolution

1. **Hardcoded platform list** -- Orchestrator has `if name == "indeed"` / `elif name == "dice"` branching. Adding a platform means editing orchestrator.py.
2. **RemoteOK does not extend BasePlatform** -- It is an API-based platform that cannot use the browser-based ABC. Need a second adapter interface.
3. **Config is a static class** -- All config is hardcoded class attributes or .env. No user-editable config file. CandidateProfile is hardcoded in models.py.
4. **No AI integration** -- Scoring is keyword-matching. No LLM-based resume tailoring or intelligent matching.
5. **Single apply mode** -- The apply flow is always semi-automatic (human confirms). No auto-apply or manual-only modes.
6. **Dashboard is read-only + import** -- No ability to trigger searches, manage config, or initiate applications from the dashboard.
7. **No event/notification system** -- Dashboard does not know when pipeline runs complete.

---

## Recommended Architecture

### High-Level Component Map

```
                     +------------------+
                     |   config.toml    |  <-- User-editable configuration
                     |   .env           |  <-- Secrets only
                     +--------+---------+
                              |
                     +--------v---------+
                     |  AppSettings     |  <-- pydantic-settings: TOML + .env + env vars
                     |  (layered config)|
                     +--------+---------+
                              |
          +-------------------+-------------------+
          |                                       |
+---------v----------+               +-----------v-----------+
|    Orchestrator     |               |    FastAPI Dashboard   |
|   (pipeline engine) |<--- SSE ----->|   (webapp/ + htmx)    |
+---------+----------+               +-----------+-----------+
          |                                       |
          |  +------------------------------------+
          |  |
+---------v--v-------+
|  Platform Registry  |  <-- Auto-discovers platform adapters
+----+----+----+-----+
     |    |    |
     v    v    v
  Indeed Dice RemoteOK  LinkedIn  ... (future)
     |    |    |
     v    v    v
+----+----+----+-----+
|   Job Pipeline DB   |  <-- SQLite (single source of truth)
+----+----+-----------+
     |    |
     v    v
+---------v----------+     +------------------+
|   Scorer           |     |  AI Resume       |
|   (weighted +      |     |  Tailorer        |
|    optional LLM)   |     |  (LiteLLM)       |
+--------------------+     +------------------+
          |                         |
          v                         v
+-------------------------------------+
|   Apply Engine                       |
|   (auto / semi-auto / manual modes)  |
+--------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Owns Files |
|-----------|---------------|-------------------|------------|
| **AppSettings** | Load and validate all configuration from TOML + .env + env vars | All components read from it | `config.toml`, `settings.py` |
| **Platform Registry** | Discover, register, and instantiate platform adapters | Orchestrator asks it for platform instances | `platforms/registry.py` |
| **Platform Adapters** | Search, extract, get details for one job board | Registry creates them; Orchestrator calls them | `platforms/{name}.py` |
| **Orchestrator** | Run the 5-phase pipeline, coordinate all components | Registry, Scorer, ApplyEngine, DB, Dashboard (via SSE) | `orchestrator.py` |
| **Scorer** | Rate jobs 1-5 against candidate profile | Reads AppSettings for profile; optionally calls LLM | `scorer.py` |
| **AI Resume Tailorer** | Generate tailored resumes per job using LLM | Reads Job + CandidateProfile; writes to resumes/tailored/ | `ai/resume_tailorer.py` |
| **Apply Engine** | Execute apply flow with mode awareness (auto/semi/manual) | Platform adapters, FormFiller, Dashboard (for confirmations) | `apply_engine.py` |
| **Dashboard** | Web UI for viewing jobs, managing config, triggering actions | Reads DB; receives SSE from Orchestrator; calls API endpoints | `webapp/` |
| **Job Pipeline DB** | Persist all job data, application status, run history | All components read/write | `webapp/db.py` (evolve to use models) |

---

## Pattern 1: Platform Registry with Auto-Discovery

**What:** A registry that auto-discovers platform adapters from the `platforms/` directory, eliminating `if/elif` branching in the orchestrator.

**Why:** Adding a new platform should mean creating one file in `platforms/`, not editing orchestrator.py. The current approach has hardcoded platform names in at least 6 places across orchestrator.py and config.py.

**How it works:**

```python
# platforms/registry.py
from __future__ import annotations
import importlib
import pkgutil
from pathlib import Path
from typing import Protocol, runtime_checkable

@runtime_checkable
class BrowserPlatform(Protocol):
    """Contract for browser-based platforms (Indeed, Dice)."""
    platform_name: str
    def login(self) -> bool: ...
    def search(self, query) -> list: ...
    def get_job_details(self, job) -> object: ...
    def apply(self, job, resume_path) -> bool: ...

@runtime_checkable
class APIPlatform(Protocol):
    """Contract for API-based platforms (RemoteOK)."""
    platform_name: str
    async def search(self, query) -> list: ...
    def get_job_details(self, job) -> object: ...

# Registry: maps name -> class
_registry: dict[str, type] = {}

def register(cls):
    """Decorator: register a platform adapter."""
    name = getattr(cls, 'platform_name', cls.__name__.lower())
    _registry[name] = cls
    return cls

def get_platform(name: str) -> type:
    """Retrieve registered platform class by name."""
    if name not in _registry:
        raise KeyError(f"Unknown platform: {name}. Available: {list(_registry.keys())}")
    return _registry[name]

def available_platforms() -> list[str]:
    return list(_registry.keys())

def discover_platforms():
    """Import all modules in platforms/ to trigger @register decorators."""
    package_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name not in ('base', 'registry', 'stealth') \
           and not module_info.name.endswith('_selectors'):
            importlib.import_module(f"platforms.{module_info.name}")
```

Each platform adapter self-registers:

```python
# platforms/indeed.py
from platforms.registry import register

@register
class IndeedPlatform(BasePlatform):
    platform_name = "indeed"
    ...
```

**Orchestrator then becomes:**

```python
from platforms.registry import discover_platforms, get_platform, available_platforms

class Orchestrator:
    def __init__(self):
        discover_platforms()  # Auto-import all platform modules

    def phase_2_search(self, platform_names: list[str]):
        for name in platform_names:
            PlatformClass = get_platform(name)
            # Instantiation differs by type (browser vs API)
            ...
```

**Build order implication:** This is the FIRST thing to build because every subsequent feature (apply modes, dashboard actions, config) depends on platforms being dynamically discoverable.

**Confidence:** HIGH -- This is the standard Python plugin pattern documented in the [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/). The decorator + `pkgutil.iter_modules` approach is simpler than entry_points for a single-repo project.

---

## Pattern 2: Dual Platform Protocols (Browser vs API)

**What:** Two separate protocol interfaces for browser-based platforms (Playwright) and API-based platforms (httpx). Both feed into the same pipeline.

**Why:** RemoteOK currently does NOT extend BasePlatform because it has no browser context. Forcing it into the browser ABC would be wrong. But they need a common pipeline interface.

**Architecture:**

```
                     PlatformProtocol (common)
                    /                        \
      BrowserPlatform                    APIPlatform
      (has context, page,                (has httpx client,
       login, stealth)                    no browser needed)
      /       \                           /
   Indeed    Dice                    RemoteOK   LinkedIn(future)
```

The key insight: **the Orchestrator does not need to know which type a platform is.** It calls `search()` and `get_job_details()` on whatever the registry returns. The difference is in instantiation (browser platforms need a Playwright context; API platforms do not).

```python
# Common interface that both types satisfy
class PlatformProtocol(Protocol):
    platform_name: str
    def search(self, query: SearchQuery) -> list[Job]: ...
    def get_job_details(self, job: Job) -> Job: ...

# Browser platforms additionally have:
class BrowserPlatformProtocol(PlatformProtocol, Protocol):
    def login(self) -> bool: ...
    def apply(self, job: Job, resume_path: Path) -> bool: ...

# API platforms may have async methods, handled by the orchestrator
```

**Resolution for sync/async mismatch:** RemoteOK is currently async. Either:
- (A) Make RemoteOK synchronous (simplest -- httpx supports sync too), or
- (B) Have the Orchestrator detect async platforms and `asyncio.run()` their methods (current approach, works fine)

**Recommendation:** Option (A) -- make RemoteOK sync. The async advantage is minimal for a single-user tool making a handful of API calls. This eliminates the sync/async split in the orchestrator.

**Confidence:** HIGH -- follows from existing codebase structure analysis.

---

## Pattern 3: Externalized Configuration with pydantic-settings

**What:** Replace the hardcoded `Config` class with a layered configuration system: `config.toml` (user-editable) + `.env` (secrets) + environment variables (overrides).

**Why:** Currently, everything from search queries to candidate profile to timing delays is hardcoded in Python files. A user cannot customize without editing source code.

**How it works with [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):**

```toml
# config.toml -- the single user-editable configuration file

[candidate]
first_name = "Patryk"
last_name = "Golabek"
email = "pgolabek@gmail.com"
phone = "416-708-9839"
location = "Springwater, ON, Canada"
years_experience = "17+"
desired_salary_usd = 200000
target_titles = [
    "Senior Software Engineer",
    "Principal Engineer",
    "Staff Engineer",
]
tech_keywords = ["kubernetes", "python", "terraform", "langchain"]

[search]
queries = [
    '"Principal Engineer" Kubernetes',
    '"Staff Engineer" platform engineering',
]
max_pages = 5
recency_days = 14

[scoring]
min_score_to_save = 3
min_score_to_apply = 4

[platforms.indeed]
enabled = true
[platforms.dice]
enabled = true
[platforms.remoteok]
enabled = true

[apply]
mode = "semi-auto"  # "auto" | "semi-auto" | "manual"
resume = "resumes/Patryk_Golabek_Resume_ATS.pdf"

[ai]
enabled = false
provider = "ollama"  # or "openai", "anthropic"
model = "llama3.1"

[timing]
nav_delay_min = 2.0
nav_delay_max = 5.0
form_delay_min = 1.0
form_delay_max = 2.0
```

```python
# settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings import TomlConfigSettingsSource

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file="config.toml",
        env_file=".env",
        env_nested_delimiter="__",
    )

    candidate: CandidateSettings
    search: SearchSettings
    scoring: ScoringSettings
    platforms: dict[str, PlatformSettings]
    apply: ApplySettings
    ai: AISettings
    timing: TimingSettings

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        return (
            kwargs["init_settings"],
            kwargs["env_settings"],
            kwargs["dotenv_settings"],
            TomlConfigSettingsSource(settings_cls),
        )
```

**Priority order (highest to lowest):**
1. Init kwargs (programmatic overrides)
2. Environment variables (e.g., `AI__PROVIDER=openai`)
3. `.env` file (secrets: `DICE_PASSWORD=xxx`)
4. `config.toml` (user configuration)

**Key principle:** Secrets (passwords, API keys) stay in `.env`. Everything else goes in `config.toml`.

**Migration from current Config class:**
- `Config.CANDIDATE` -> `settings.candidate`
- `Config.DEFAULT_SEARCH_QUERIES` -> `settings.search.queries`
- `Config.NAV_DELAY_MIN` -> `settings.timing.nav_delay_min`
- `Config.DICE_EMAIL` / `Config.DICE_PASSWORD` -> stay in `.env`

**Build order implication:** Build this SECOND (after platform registry) because all other components need it.

**Confidence:** HIGH -- pydantic-settings has built-in TOML support via `TomlConfigSettingsSource` since v2.x. Verified in [official docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

---

## Pattern 4: Apply Engine with Mode Awareness

**What:** An `ApplyEngine` that supports three modes -- auto, semi-auto, and manual -- each with different human-in-the-loop behavior.

**Why:** The current apply flow is hardcoded semi-auto (always asks for human confirmation). For high-confidence matches (score 5, Easy Apply), full automation saves time. For external ATS (RemoteOK), manual is the only option.

**Mode definitions:**

| Mode | Behavior | When to Use |
|------|----------|-------------|
| **auto** | Fill form + submit without asking. Screenshot before/after for audit trail. | Score 5 + Easy Apply on Indeed/Dice. User explicitly opts in. |
| **semi-auto** | Fill form + present to human + wait for "SUBMIT" confirmation. | Default. Score 4-5 jobs. Current behavior. |
| **manual** | Open the job URL in browser. User does everything. Tool tracks status. | External ATS (RemoteOK), non-Easy Apply, or user preference. |

**Architecture:**

```python
# apply_engine.py
from enum import Enum

class ApplyMode(str, Enum):
    AUTO = "auto"
    SEMI_AUTO = "semi-auto"
    MANUAL = "manual"

class ApplyEngine:
    def __init__(self, settings: AppSettings):
        self.default_mode = ApplyMode(settings.apply.mode)

    def apply(self, job: Job, platform, resume_path: Path) -> ApplyResult:
        mode = self._resolve_mode(job, platform)

        if mode == ApplyMode.MANUAL:
            return self._manual_apply(job)
        elif mode == ApplyMode.SEMI_AUTO:
            return self._semi_auto_apply(job, platform, resume_path)
        elif mode == ApplyMode.AUTO:
            return self._auto_apply(job, platform, resume_path)

    def _resolve_mode(self, job: Job, platform) -> ApplyMode:
        """Determine effective mode based on job, platform, and config."""
        # External ATS (RemoteOK) is always manual
        if not hasattr(platform, 'apply') or job.platform == "remoteok":
            return ApplyMode.MANUAL

        # Non-Easy Apply jobs degrade to semi-auto at most
        if not job.easy_apply and self.default_mode == ApplyMode.AUTO:
            return ApplyMode.SEMI_AUTO

        return self.default_mode
```

**Key design decisions:**
- Mode is a per-run global setting from config, not per-job. Simpler mental model.
- Mode can be **degraded** by the engine (auto -> semi-auto for non-Easy Apply), never **escalated** (manual never becomes auto).
- Auto mode still takes screenshots before submission for audit.
- All modes update job status in the DB.

**Build order implication:** Build AFTER platform registry and config (depends on both).

**Confidence:** HIGH -- simple state logic, no external dependencies.

---

## Pattern 5: AI Resume Tailoring via LiteLLM

**What:** An AI component that takes a Job + CandidateProfile and produces a tailored resume, using any LLM provider through [LiteLLM](https://docs.litellm.ai/docs/) abstraction.

**Why:** The candidate has multiple strong differentiators (pre-1.0 K8s, LangFlow PR, SickKids research). Different jobs need different emphasis. Doing this manually per job does not scale.

**Architecture:**

```python
# ai/resume_tailorer.py
from litellm import completion

class ResumeTailorer:
    def __init__(self, settings: AISettings):
        self.provider = settings.provider  # "ollama", "openai", "anthropic"
        self.model = settings.model        # "llama3.1", "gpt-4o", "claude-3-5-sonnet"

    def tailor(self, job: Job, profile: CandidateSettings, base_resume_text: str) -> TailoredResume:
        """Generate a tailored resume for a specific job."""
        prompt = self._build_prompt(job, profile, base_resume_text)

        response = completion(
            model=f"{self.provider}/{self.model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._parse_response(response, job)
```

**Why LiteLLM over direct API calls:**
- Provider-agnostic: Switch between Ollama (free, local) and OpenAI/Anthropic by changing one config field
- OpenAI-compatible interface: Same `completion()` call regardless of provider
- Supports 100+ LLM providers
- Cost tracking built in
- Handles retries and error normalization

**Why NOT LangChain/LangGraph here:**
- Resume tailoring is a single prompt-response interaction, not a multi-step agent workflow
- LangChain adds complexity without value for this use case
- LiteLLM is 90% lighter than LangChain for direct LLM calls

**Resume generation pipeline:**

```
Job Description (text)
       +
CandidateProfile (from config.toml)
       +
Base Resume (PDF -> extracted text)
       |
       v
  LLM Prompt: "Given this job description and candidate profile,
               produce a tailored professional summary and
               reorder skills/experience for relevance"
       |
       v
  Structured JSON Response:
    { summary: str, skills_order: list, experience_highlights: list }
       |
       v
  Resume Template (Jinja2 -> HTML -> PDF via weasyprint or Playwright)
       |
       v
  resumes/tailored/{company}_{title}.pdf
```

**Key design decisions:**
- AI is optional. Default config: `ai.enabled = false`. Tool works fully without it.
- Use Ollama as default provider (free, local, no API key needed).
- Resume output is PDF. Use Playwright (already a dependency) for HTML-to-PDF conversion.
- AI does NOT write the entire resume -- it reorders/emphasizes existing content from the base resume. This prevents hallucination of fake experience.

**Build order implication:** Build LAST. This is additive and does not block any other component.

**Confidence:** MEDIUM -- LiteLLM API is well-documented ([PyPI](https://pypi.org/project/litellm/)). Resume template generation with Playwright PDF is proven. The prompt engineering for quality tailoring will need iteration.

---

## Pattern 6: Enhanced Dashboard with SSE Pipeline Notifications

**What:** Evolve the dashboard from a read-only viewer to a command center that receives real-time pipeline updates and can trigger actions.

**Why:** Currently the dashboard is disconnected from the pipeline. User runs `python orchestrator.py` in terminal, then opens browser to see results. The two should be connected.

**Architecture evolution:**

```
Current:
  Terminal (orchestrator.py) --> JSON files --> Dashboard (reads JSON, imports to SQLite)

Target:
  Dashboard triggers pipeline via API --> Orchestrator runs --> SSE events to Dashboard
  Dashboard also: view jobs, change status, trigger apply, edit config
```

**SSE for real-time updates (not WebSockets):**

Use [sse-starlette](https://github.com/sysid/sse-starlette) with FastAPI. SSE is simpler than WebSockets for this use case because communication is one-directional (server -> client). The dashboard only needs to receive updates ("search found 5 new jobs", "scoring complete", "application submitted").

```python
# webapp/events.py
import asyncio
from sse_starlette.sse import EventSourceResponse

class PipelineEventBus:
    """Simple in-process event bus for pipeline -> dashboard communication."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.remove(queue)

    async def publish(self, event_type: str, data: dict):
        for queue in self._subscribers:
            await queue.put({"event": event_type, "data": data})
```

```python
# webapp/app.py
@app.get("/events")
async def pipeline_events(request: Request):
    queue = event_bus.subscribe()

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield {"event": event["event"], "data": json.dumps(event["data"])}
        except asyncio.CancelledError:
            event_bus.unsubscribe(queue)

    return EventSourceResponse(event_generator())
```

htmx SSE integration on the frontend:

```html
<div hx-ext="sse" sse-connect="/events">
    <div sse-swap="pipeline_progress">
        <!-- Updated in real-time as pipeline runs -->
    </div>
</div>
```

**New dashboard capabilities:**

| Feature | Endpoint | Method |
|---------|----------|--------|
| Trigger full pipeline | `POST /api/pipeline/run` | Starts orchestrator in background thread |
| Trigger single-platform search | `POST /api/pipeline/search/{platform}` | Runs search phase only |
| View/edit config | `GET/PUT /api/config` | Read/write config.toml |
| Trigger apply for a job | `POST /api/jobs/{key}/apply` | Runs apply engine for one job |
| Trigger AI resume tailor | `POST /api/jobs/{key}/tailor-resume` | Generates tailored resume |
| Pipeline run history | `GET /api/runs` | Past pipeline executions |
| SSE event stream | `GET /events` | Real-time pipeline updates |

**Build order implication:** Evolve incrementally. First add SSE + pipeline trigger. Then add config management. Then apply/tailor actions.

**Confidence:** HIGH for SSE + htmx pattern (well-documented: [fastapi-sse-htmx example](https://github.com/vlcinsky/fastapi-sse-htmx)). MEDIUM for full dashboard API (scope is flexible).

---

## Data Flow

### Discovery Flow (Search Pipeline)

```
config.toml (search queries, platform list)
     |
     v
Orchestrator.phase_2_search()
     |
     +--- Platform Registry ---+--- IndeedPlatform.search() --> list[Job]
     |                         +--- DicePlatform.search()   --> list[Job]
     |                         +--- RemoteOKPlatform.search()--> list[Job]
     |
     v
Orchestrator.phase_3_score()
     |
     +--- JobScorer.score_batch(all_jobs) --> scored list[Job]
     |
     v
DB.upsert_jobs(scored_jobs)
     |
     +--- SSE event: "scoring_complete" --> Dashboard
```

### Application Flow

```
User selects job in Dashboard (or CLI)
     |
     v
ApplyEngine.apply(job, platform, resume_path)
     |
     +--- _resolve_mode(job, platform) --> ApplyMode
     |
     +--- [if AI enabled] ResumeTailorer.tailor(job) --> tailored PDF
     |
     +--- mode == AUTO:
     |      platform.apply(job, resume) --> submit without confirmation
     |      Screenshot before/after
     |
     +--- mode == SEMI_AUTO:
     |      platform.apply(job, resume) --> FormFiller fills form
     |      wait_for_human("SUBMIT") --> user confirms
     |
     +--- mode == MANUAL:
     |      Open job URL in browser
     |      User applies manually
     |      Tool tracks status only
     |
     v
DB.update_job_status(job.dedup_key, "applied" | "skipped")
     |
     +--- SSE event: "application_submitted" --> Dashboard
```

### Configuration Flow

```
config.toml (user edits directly, or via Dashboard UI)
     +
.env (secrets: DICE_PASSWORD, OPENAI_API_KEY)
     +
Environment variables (overrides, e.g., AI__PROVIDER=openai)
     |
     v
AppSettings (pydantic-settings: TOML + .env + env vars, layered)
     |
     +--- Orchestrator reads: platform list, search queries
     +--- Scorer reads: candidate profile, tech keywords, scoring thresholds
     +--- ApplyEngine reads: apply mode, resume path
     +--- ResumeTailorer reads: AI provider, model
     +--- Stealth reads: timing delays
     +--- Dashboard reads: all (for config editor UI)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Over-Engineering the Plugin System

**What:** Using entry_points, namespace packages, or separate pip-installable packages for platform plugins.

**Why bad:** This is a single-repo, single-user tool. The entry_points machinery is designed for ecosystem-scale plugin distribution (think: pytest plugins, Flask extensions). It adds packaging complexity for zero benefit here.

**Instead:** Use the simple decorator + `pkgutil.iter_modules` auto-discovery pattern shown in Pattern 1. A new platform is one file in `platforms/` with a `@register` decorator. No setup.py changes, no package installs.

### Anti-Pattern 2: Separate Databases

**What:** Having JSON files, SQLite, and maybe another store for different data.

**Why bad:** Currently, the pipeline writes JSON files which the dashboard imports into SQLite. This dual-storage creates sync issues and stale data.

**Instead:** Make SQLite the single source of truth from the start. The orchestrator writes directly to SQLite (via the db module). JSON files become optional exports, not the primary storage.

### Anti-Pattern 3: Async Everything

**What:** Making all platform adapters async because RemoteOK is currently async.

**Why bad:** Playwright's sync API is simpler to debug and already works. The orchestrator runs platforms sequentially (one at a time in a single browser). Async adds complexity without performance benefit for a single-user tool.

**Instead:** Make RemoteOK synchronous (httpx supports sync). Keep the entire pipeline synchronous. The only async code should be in the FastAPI dashboard (which is natively async).

### Anti-Pattern 4: LLM in the Critical Path

**What:** Making AI resume tailoring a required step before every application.

**Why bad:** LLM calls are slow (2-10 seconds), unreliable (rate limits, timeouts), and expensive (if using paid APIs). Blocking the apply flow on AI makes the tool fragile.

**Instead:** AI tailoring is a separate, optional, async action. User clicks "Tailor Resume" in the dashboard for a specific job. The tool generates it in the background. The apply flow uses whatever resume is available (base or tailored).

### Anti-Pattern 5: God Object Config

**What:** Having one giant AppSettings object that every component imports directly.

**Why bad:** Creates hidden dependencies. Every module depends on the full config shape.

**Instead:** Each component receives only the settings section it needs via dependency injection:
- `Scorer(scoring_settings, candidate_settings)` not `Scorer(app_settings)`
- `ResumeTailorer(ai_settings)` not `ResumeTailorer(app_settings)`

---

## Scalability Considerations

This is a single-user, local tool. "Scalability" means: how does it handle more platforms, more jobs, and more automation without architectural changes?

| Concern | Current (3 platforms) | At 10 platforms | At 1000+ jobs/run |
|---------|----------------------|-----------------|-------------------|
| Platform registration | Hardcoded if/elif | Registry auto-discovers | Same (registry scales) |
| Search execution | Sequential | Sequential (fine for 10) | Parallelize per-platform if needed |
| Scoring | In-memory batch | In-memory batch | Stream to DB, score in batches |
| Dashboard rendering | Full page load | Full page load | Add pagination (trivial with SQLite LIMIT/OFFSET) |
| Apply automation | One-at-a-time | One-at-a-time | One-at-a-time (intentional -- anti-bot) |
| SQLite | Single file | Single file | WAL mode handles concurrent reads fine |

The architecture does NOT need to handle multi-user, multi-tenant, or distributed execution. Keep it simple.

---

## Suggested Build Order

Based on dependency analysis between components:

```
Phase 1: Platform Registry + Config Externalization
         (Foundation -- everything depends on these)
         |
Phase 2: DB as Single Source of Truth + Apply Engine Modes
         (Core pipeline improvements)
         |
Phase 3: Dashboard SSE + Pipeline Trigger from Dashboard
         (Connect the two halves of the tool)
         |
Phase 4: AI Resume Tailoring
         (Additive feature, no dependencies on it)
```

**Dependency graph:**

```
Platform Registry ---+---> Apply Engine (needs to resolve platform type)
                     |
Config Externalization --+--> Scorer (reads scoring config)
                         +--> Apply Engine (reads apply mode)
                         +--> AI Tailorer (reads AI config)
                         +--> Dashboard (config editor)
                         |
DB Consolidation --------+--> Dashboard (reads/writes directly)
                         +--> Orchestrator (writes directly to DB)
                         |
SSE Events --------------+--> Dashboard (receives events)
                         +--> Orchestrator (publishes events)
                         |
AI Resume Tailoring -----+--> Dashboard (trigger button)
                              (standalone, depends only on config)
```

**Critical path:** Registry -> Config -> DB -> Dashboard SSE. AI is fully parallel/independent.

---

## Sources

- [Python Packaging Guide: Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) -- Plugin architecture patterns (HIGH confidence)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) -- TOML + layered config (HIGH confidence)
- [Implementing the Registry Pattern with Decorators in Python](https://medium.com/@tihomir.manushev/implementing-the-registry-pattern-with-decorators-in-python-de8daf4a452a) -- Decorator registry (MEDIUM confidence)
- [LiteLLM Documentation](https://docs.litellm.ai/docs/) -- Provider-agnostic LLM abstraction (HIGH confidence)
- [fastapi-sse-htmx Example](https://github.com/vlcinsky/fastapi-sse-htmx) -- SSE + htmx integration (HIGH confidence)
- [Resume Matcher (GitHub)](https://github.com/srbhr/Resume-Matcher) -- LiteLLM-based resume tailoring architecture (MEDIUM confidence)
- [python-statemachine](https://python-statemachine.readthedocs.io/en/latest/readme.html) -- State machine for workflow modes (MEDIUM confidence, considered but not recommended for simplicity)
- [Pydantic Settings 2025: A Clean Way to Handle Configs](https://levelup.gitconnected.com/pydantic-settings-2025-a-clean-way-to-handle-configs-f1c432030085) -- Practical pydantic-settings patterns (MEDIUM confidence)
