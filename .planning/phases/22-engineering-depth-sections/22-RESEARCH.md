# Phase 22: Engineering Depth Sections - Research

**Researched:** 2026-02-13
**Domain:** Astro build-time syntax highlighting (Shiki), CSS-only pipeline/timeline visuals, section composition patterns
**Confidence:** HIGH

## Summary

Phase 22 adds four new sections to the existing single-page site: Architecture/Pipeline, Code Snippets, Milestone Timeline, and Quick Start. These build on the established Phase 21 patterns -- self-contained Astro section components in `src/components/sections/`, composed into `index.astro` inside `<main>`, using Tailwind utility classes exclusively (no `<style>` blocks).

The most technically interesting requirement is CONT-06 (code snippets with syntax highlighting). Astro ships with Shiki (v3.22.0 already in `node_modules` as a transitive dependency) and exposes a built-in `<Code />` component via `import { Code } from 'astro:components'`. This renders at build time, producing inline-styled HTML with zero client-side JavaScript. The component accepts `code`, `lang`, and `theme` props. The `github-dark-default` theme is available and pairs well with the blues/grays palette.

The other three sections (CONT-05, CONT-07, CONT-08) are pure content/layout work using established patterns: data arrays mapped over in templates with Tailwind grid and flexbox. The architecture pipeline diagram (CONT-05) is best implemented as a horizontal stepper/flow using CSS flexbox with connecting lines (pseudo-elements or border-based), not an SVG or image. The milestone timeline (CONT-07) uses a vertical or horizontal timeline pattern with milestone markers. The quick start (CONT-08) is a numbered step list with code blocks -- using `<Code />` for the bash commands.

No new npm dependencies are needed. Everything is achievable with Astro's built-in `<Code />` component + Tailwind utility classes.

**Primary recommendation:** Use Astro's built-in `<Code />` component with `github-dark-default` theme for all syntax-highlighted code blocks. Build the architecture pipeline as a CSS flexbox stepper with `before`/`after` pseudo-element connectors (these require a small `<style>` exception or Tailwind arbitrary values). Build timeline and quick start as data-driven section components following the Phase 21 map pattern.

## Standard Stack

### Core (already installed from Phase 20 -- NO new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `astro` | 5.17.2 | `<Code />` built-in component for syntax highlighting | Ships Shiki internally; `import { Code } from 'astro:components'` |
| `tailwindcss` | 4.1.18 | Layout, typography, responsive design | All section styling via utility classes |
| `shiki` | 3.22.0 | Syntax highlighting engine (transitive dep of Astro) | Already in node_modules; powers `<Code />` component |

### Supporting (no new dependencies)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Astro `<Code />` component (built-in) | -- | Build-time syntax highlighting | CONT-06 code snippets, CONT-08 quick start bash commands |
| Tailwind pseudo-element utilities | -- | Pipeline connector lines between steps | `before:` and `after:` variants for visual connectors |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Astro `<Code />` | `astro-expressive-code` package | Richer features (line numbers, line highlighting, diff markers, copy button) but adds a dependency. `<Code />` is sufficient for 2-3 static snippets on a marketing page. |
| Astro `<Code />` | Prism.js or highlight.js | Client-side JS -- antithetical to zero-JS static site. Astro's Shiki runs at build time. |
| CSS flexbox pipeline | SVG diagram | SVG is more visually flexible but harder to make responsive and harder to maintain as text. CSS flexbox scales naturally with viewport. |
| CSS flexbox pipeline | Mermaid.js | Requires JS runtime or a build-time rendering step. Overkill for a 5-step linear flow. |
| Inline code strings | Imported `.py` files via `fs.readFileSync` | Over-engineered; the code snippets are curated excerpts, not full files. Hardcoded strings are intentional -- we pick the best 15-25 lines to show, not the entire file. |

**Installation:** No new packages needed. Phase 20's dependencies cover everything.

## Architecture Patterns

### Recommended Project Structure (additions to Phase 21)

```
site/src/
├── components/
│   ├── sections/
│   │   ├── Hero.astro          # (Phase 21 -- unchanged)
│   │   ├── Stats.astro         # (Phase 21 -- unchanged)
│   │   ├── Features.astro      # (Phase 21 -- unchanged)
│   │   ├── TechStack.astro     # (Phase 21 -- unchanged)
│   │   ├── Architecture.astro  # NEW: CONT-05 pipeline diagram
│   │   ├── CodeSnippets.astro  # NEW: CONT-06 syntax-highlighted examples
│   │   ├── Timeline.astro      # NEW: CONT-07 milestone timeline
│   │   ├── QuickStart.astro    # NEW: CONT-08 setup guide
│   │   └── Footer.astro        # (Phase 21 -- unchanged)
│   └── ui/
│       └── ScreenshotFrame.astro  # (Phase 21 -- unchanged)
├── icons/
│   ├── (existing icons from Phase 21)
│   └── (may need 2-3 new icons: arrow-right, clock, git-branch, terminal, etc.)
├── layouts/
│   └── BaseLayout.astro        # (Phase 20 -- unchanged)
├── pages/
│   └── index.astro             # MODIFIED: add 4 new section imports
└── styles/
    └── global.css              # (Phase 20 -- unchanged, possibly add pipeline connector styles)
```

### Pattern 1: Astro `<Code />` Component for Syntax Highlighting

**What:** Astro's built-in component that renders syntax-highlighted code at build time using Shiki. Zero client-side JavaScript.
**When to use:** CONT-06 (code snippets section) and CONT-08 (quick start bash commands).
**Example:**

```astro
---
import { Code } from 'astro:components';

const protocolCode = `@runtime_checkable
class BrowserPlatform(Protocol):
    """Contract for browser-automated job platforms."""
    platform_name: str

    def search(self, query: SearchQuery) -> list[Job]:
        """Search and return scored Job models."""
        ...

    def get_job_details(self, job: Job) -> Job:
        """Enrich a Job with full description."""
        ...`;
---

<Code code={protocolCode} lang="python" theme="github-dark-default" />
```

**Key behaviors:**
- Renders at build time -- output is inline-styled HTML, no JS shipped to client
- Does NOT inherit markdown `shikiConfig` -- must pass `theme` explicitly per instance
- `lang` accepts any Shiki language identifier (e.g., `"python"`, `"bash"`, `"yaml"`)
- `theme` accepts any bundled Shiki theme name (e.g., `"github-dark-default"`, `"github-dark"`, `"dark-plus"`)
- `wrap` prop enables word wrapping (useful for mobile responsiveness)
- Output is a `<pre>` element with `<code>` inside, both with inline `style` attributes

**Confidence:** HIGH -- verified via Astro official docs and Shiki package in node_modules.

### Pattern 2: CSS Flexbox Pipeline Stepper (Architecture Diagram)

**What:** A horizontal row of step boxes connected by lines/arrows, representing the 5-phase pipeline.
**When to use:** CONT-05 architecture/pipeline section.
**Example:**

```astro
---
const phases = [
  { step: "1", name: "Setup", description: "Config, credentials, browser context" },
  { step: "2", name: "Login", description: "Platform authentication, session restore" },
  { step: "3", name: "Search", description: "Multi-platform job discovery" },
  { step: "4", name: "Score", description: "AI + rule-based match scoring" },
  { step: "5", name: "Apply", description: "Human-approved application submission" },
];
---

<section id="architecture" class="py-20 bg-white">
  <div class="max-w-6xl mx-auto px-4">
    <h2 class="font-display text-3xl font-bold text-surface-900 text-center">
      How It Works
    </h2>
    <p class="mt-3 text-surface-600 text-center max-w-2xl mx-auto">
      A five-phase pipeline from configuration to application
    </p>
    <div class="mt-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      {phases.map((phase, i) => (
        <div class="flex items-center gap-4 md:flex-col md:items-center md:gap-2 md:flex-1 md:text-center">
          <div class="w-12 h-12 rounded-full bg-primary-600 text-white flex items-center justify-center font-display font-bold text-lg shrink-0">
            {phase.step}
          </div>
          <div>
            <div class="font-display font-semibold text-surface-900">{phase.name}</div>
            <div class="text-sm text-surface-500">{phase.description}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
</section>
```

**Connector approach:** The connecting lines between steps can be implemented with:
- Option A: A horizontal `border-t` on a wrapper `div` behind the circles using absolute positioning
- Option B: Tailwind `before:` pseudo-elements with `before:content-[''] before:absolute before:h-0.5 before:bg-primary-300`
- Option C: Arrow SVG icons between steps (simplest, most explicit, no pseudo-element complexity)

**Recommendation:** Use Option C (arrow icons between steps) for simplicity. On mobile, stack vertically with a downward arrow or simple vertical line.

**Responsive behavior:**
- Desktop (`md:+`): Horizontal row with connectors
- Mobile: Vertical stack, each step is a row with number + text

### Pattern 3: Data-Driven Timeline (Milestone History)

**What:** A vertical timeline showing project milestones with dates, stats, and descriptions.
**When to use:** CONT-07 milestone timeline.
**Example:**

```astro
---
const milestones = [
  {
    version: "v1.0",
    title: "MVP",
    date: "Feb 7, 2026",
    stats: "6,705 LOC | 8 phases | 24 plans",
    description: "Full pipeline: config, scraping, scoring, dashboard, AI resume, one-click apply",
    features: ["Multi-platform scraping", "Scoring engine", "Web dashboard", "AI resume tailoring", "One-click apply"],
  },
  {
    version: "v1.1",
    title: "Test Suite",
    date: "Feb 8, 2026",
    stats: "5,639 test LOC | 428 tests | 80%+ coverage",
    description: "Comprehensive test infrastructure with CI pipeline",
    features: ["Unit tests", "Integration tests", "E2E browser tests", "GitHub Actions CI"],
  },
  {
    version: "v1.2",
    title: "Claude CLI Integration",
    date: "Feb 11, 2026",
    stats: "581 tests | 15 requirements | 7 plans",
    description: "Replaced SDK with Claude CLI subprocess for all AI features",
    features: ["Claude CLI wrapper", "AI scoring", "SSE streaming", "Anti-fabrication validation"],
  },
];
---
```

**Layout pattern:** Use a left-aligned vertical timeline with a connecting line:
- A vertical line on the left (or center on desktop) using `border-l` or a thin `div`
- Milestone markers (dots or version badges) on the line
- Content cards to the right of each marker

### Pattern 4: Numbered Step List (Quick Start)

**What:** A sequential numbered list with instructions and code blocks.
**When to use:** CONT-08 quick start section.
**Example:**

```astro
---
import { Code } from 'astro:components';

const steps = [
  { title: "Clone the repository", code: "git clone https://github.com/patrykgolabek/jobs.git\ncd jobs", lang: "bash" },
  { title: "Install dependencies", code: "pip install -r requirements.txt\nplaywright install chromium", lang: "bash" },
  { title: "Configure your profile", code: "cp config.example.yaml config.yaml\n# Edit config.yaml with your preferences", lang: "bash" },
  { title: "Run the pipeline", code: "python orchestrator.py --platforms indeed remoteok", lang: "bash" },
  { title: "Open the dashboard", code: "python -m webapp.app\n# Visit localhost:8000", lang: "bash" },
];
---
```

Each step renders as: numbered circle + title + `<Code />` block. This mirrors the pipeline pattern but is content-focused rather than visual.

### Pattern 5: Section Composition (Updated index.astro)

**What:** Add the 4 new sections to `index.astro` in the correct order.
**When to use:** After all section components are built.
**Example ordering:**

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
import Hero from "../components/sections/Hero.astro";
import Stats from "../components/sections/Stats.astro";
import Features from "../components/sections/Features.astro";
import TechStack from "../components/sections/TechStack.astro";
import Architecture from "../components/sections/Architecture.astro";
import CodeSnippets from "../components/sections/CodeSnippets.astro";
import Timeline from "../components/sections/Timeline.astro";
import QuickStart from "../components/sections/QuickStart.astro";
import Footer from "../components/sections/Footer.astro";
---

<BaseLayout
  title="JobFlow — Job Search Automation"
  description="Self-hosted pipeline that scrapes job boards, scores matches against your profile, and automates applications. 18K LOC, 581 tests, 3 platforms."
>
  <main>
    <Hero />
    <Stats />
    <Features />
    <TechStack />
    <Architecture />
    <CodeSnippets />
    <Timeline />
    <QuickStart />
  </main>
  <Footer />
</BaseLayout>
```

**Section ordering rationale:**
1. Hero / Stats / Features / TechStack -- already built (Phase 21), above-the-fold content
2. Architecture -- "How It Works" follows naturally after "What It Does" (Features)
3. CodeSnippets -- deep technical proof after the high-level architecture
4. Timeline -- build story / project history provides narrative context
5. QuickStart -- actionable next step for interested developers
6. Footer -- anchors the bottom

### Anti-Patterns to Avoid

- **Importing full source files for code snippets:** The snippets should be curated 15-25 line excerpts that show design decisions, not dump entire files. Hardcode the excerpt strings in the component.
- **Using `<style>` blocks for code snippet containers:** Stick with Tailwind utility classes. The `<Code />` component handles its own inline styles. Wrapper elements use Tailwind.
- **Building an interactive SVG diagram with JS:** The architecture section is a static visual. CSS flexbox with numbered circles and connecting lines is sufficient. Interactive diagrams are out of scope (CONT-13 is a future requirement).
- **Installing `astro-expressive-code` for 2-3 code blocks:** The built-in `<Code />` component handles this without an extra dependency. Expressive Code is for docs-heavy sites with dozens of code blocks.
- **Making the timeline horizontally scrollable on mobile:** Stack vertically instead. Horizontal scroll is a poor mobile UX pattern.
- **Using `@apply` in a `<style>` block for pipeline connectors:** If pseudo-elements are needed, use Tailwind's `before:` and `after:` arbitrary value variants, or add a minimal rule in `global.css`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syntax highlighting | Custom regex-based highlighter | Astro `<Code />` with Shiki | Shiki handles 200+ languages, dozens of themes, proper tokenization. Build-time, zero JS. |
| Code snippet formatting | Manual `<pre>` + `<code>` with CSS classes | Astro `<Code />` component | Inline styles generated by Shiki, no CSS maintenance |
| Pipeline diagram | SVG with manual path drawing | CSS flexbox stepper with Tailwind | Responsive by default, text-based, maintainable |
| Timeline visualization | D3.js or charting library | CSS border + Tailwind layout | Static content, no interaction needed |

**Key insight:** Phase 22 is content-heavy, not technically complex. The only non-trivial piece is the `<Code />` component integration, and Astro handles that natively. Everything else is layout and copywriting.

## Common Pitfalls

### Pitfall 1: `<Code />` Component Theme Not Applied

**What goes wrong:** Code blocks render with no syntax highlighting or unexpected colors.
**Why it happens:** The `<Code />` component does NOT inherit the Markdown `shikiConfig` from `astro.config.mjs`. Each instance needs an explicit `theme` prop.
**How to avoid:** Always pass `theme="github-dark-default"` (or your chosen theme) as a prop to every `<Code />` instance. Define a wrapper component or a constant for the theme name to keep it DRY.
**Warning signs:** Code blocks render as plain monospace text with no colors.
**Confidence:** HIGH -- documented in Astro official docs.

### Pitfall 2: Code Block Overflow on Mobile

**What goes wrong:** Long code lines extend beyond the viewport at 375px, causing horizontal scroll on the entire page.
**Why it happens:** `<pre>` elements do not wrap by default. The `<Code />` component outputs a `<pre>` block.
**How to avoid:** Either (a) pass `wrap` prop to `<Code />` to enable word wrapping, or (b) wrap the `<Code />` component in a container with `overflow-x-auto` to add a horizontal scrollbar only on the code block. Option (b) is generally better for code readability -- developers expect scrollable code blocks, not wrapped code.
**Warning signs:** Horizontal scrollbar on the entire page at mobile width.
**Confidence:** HIGH.

### Pitfall 3: Pipeline Connectors Break on Responsive Transition

**What goes wrong:** Horizontal connector lines between pipeline steps don't disappear or transform when the layout switches from horizontal (desktop) to vertical (mobile).
**Why it happens:** Pseudo-elements or border-based connectors are set up for one direction only.
**How to avoid:** Two approaches: (1) Use arrow icon components between steps and conditionally show horizontal vs vertical arrows with `hidden md:block` / `block md:hidden`. (2) Use a completely different layout for mobile (vertical list) vs desktop (horizontal stepper) with responsive Tailwind classes.
**Warning signs:** Connector lines pointing in wrong direction at certain breakpoints; overlapping elements.

### Pitfall 4: Code Snippet Strings with Backticks/Template Literals

**What goes wrong:** JavaScript template literal syntax `${}` inside code strings gets interpolated by Astro's JSX-like template engine.
**Why it happens:** Astro templates process `{}` as expressions.
**How to avoid:** For Python code snippets (the main use case here), this is not an issue. If bash snippets contain `${}`, use `String.raw` or escape with `\$`. Alternatively, define code strings as constants in the frontmatter with plain template literals (backtick strings don't process `${}` inside Astro frontmatter, only in the template body).
**Warning signs:** Code snippets show `undefined` where `${variable}` was expected, or syntax errors during build.

### Pitfall 5: Inconsistent Section Backgrounds

**What goes wrong:** Adjacent sections have the same background color, making them visually merge with no clear boundary.
**Why it happens:** Not planning the alternating light/dark pattern across all sections.
**How to avoid:** Map out background colors for ALL sections (including the 4 new ones) before building. Existing Phase 21 pattern:
- Hero: `bg-surface-50` (default body)
- Stats: `bg-primary-900` (dark accent)
- Features: `bg-white`
- TechStack: `bg-surface-50`
- (new) Architecture: `bg-white` (matches Features pattern)
- (new) CodeSnippets: `bg-surface-900` or `bg-surface-800` (dark -- complements dark code theme)
- (new) Timeline: `bg-white` or `bg-surface-50`
- (new) QuickStart: `bg-surface-50` or `bg-white`
- Footer: `bg-surface-900` (already dark)

**Key insight:** The code snippets section naturally wants a dark background to match the `github-dark-default` Shiki theme. This creates a nice visual break in the page flow.

### Pitfall 6: Milestone Data Inconsistency

**What goes wrong:** Stats shown in the timeline don't match the actual project data from STATE.md/PROJECT.md.
**Why it happens:** Copy-paste errors or not checking the source of truth.
**How to avoid:** Use the verified data from PROJECT.md:
- v1.0: shipped Feb 8, 8 phases, 24 plans, 6,705 LOC (Python + HTML)
- v1.1: shipped Feb 8, 7 phases, 14 plans, 428 tests, 80%+ coverage
- v1.2: shipped Feb 11, 4 phases, 7 plans, 581 tests total, 18,022 LOC total
**Warning signs:** Numbers don't add up or contradict each other.

## Code Examples

### Complete Code Snippet with Wrapper

```astro
---
// CONT-06: Code snippets section
import { Code } from 'astro:components';

const THEME = "github-dark-default";

const snippets = [
  {
    title: "Platform Protocol",
    filename: "platforms/protocols.py",
    description: "Runtime-checkable Protocol defining the contract every platform adapter must implement",
    lang: "python",
    code: `@runtime_checkable
class BrowserPlatform(Protocol):
    """Contract for browser-automated job platforms."""
    platform_name: str

    def init(self, context: "BrowserContext") -> None: ...
    def login(self) -> bool: ...
    def is_logged_in(self) -> bool: ...
    def search(self, query: SearchQuery) -> list[Job]: ...
    def get_job_details(self, job: Job) -> Job: ...
    def apply(self, job: Job, resume_path: Path | None = None) -> bool: ...`,
  },
  {
    title: "Decorator Registry",
    filename: "platforms/registry.py",
    description: "Fail-fast decorator that validates platform adapters against the Protocol at import time",
    lang: "python",
    code: `def register_platform(key: str, *, name: str | None = None,
                       platform_type: str = "browser") -> Any:
    def decorator(cls: type) -> type:
        from platforms.protocols import APIPlatform, BrowserPlatform

        protocol = BrowserPlatform if platform_type == "browser" else APIPlatform
        _validate_against_protocol(cls, protocol)  # TypeError if missing methods

        _REGISTRY[key] = PlatformInfo(
            key=key, name=name or key.title(),
            platform_type=platform_type, cls=cls,
        )
        return cls
    return decorator`,
  },
  {
    title: "Scoring Engine",
    filename: "scorer.py",
    description: "Weighted multi-factor scoring with explainable breakdowns per job",
    lang: "python",
    code: `class JobScorer:
    """Score jobs 1-5 against candidate profile."""

    def _compute(self, job: Job) -> tuple[int, ScoreBreakdown]:
        w = self.weights
        title_pts = self._title_score(job.title)
        tech_pts, matched = self._tech_score_with_keywords(job)
        remote_pts = self._location_score(job.location)
        salary_pts = self._salary_score(job)

        raw = (title_pts * w.title_match / 2.0
             + tech_pts * w.tech_overlap / 2.0
             + remote_pts * w.remote
             + salary_pts * w.salary)

        total = 5 if raw >= 5 else 4 if raw >= 4 else 3 if raw >= 3 else 2 if raw >= 2 else 1
        return total, ScoreBreakdown(
            title_points=title_pts, tech_points=tech_pts,
            tech_matched=matched, remote_points=remote_pts,
            salary_points=salary_pts, total=total,
        )`,
  },
];
---

<section id="code" class="py-20 bg-surface-900">
  <div class="max-w-6xl mx-auto px-4">
    <h2 class="font-display text-3xl font-bold text-white text-center">
      Under the Hood
    </h2>
    <p class="mt-3 text-surface-400 text-center max-w-2xl mx-auto">
      Real code from the codebase -- design patterns that enable extensibility
    </p>
    <div class="mt-12 space-y-8">
      {snippets.map((snippet) => (
        <div class="rounded-xl overflow-hidden border border-surface-700">
          <div class="px-6 py-4 bg-surface-800">
            <h3 class="font-display font-semibold text-white">{snippet.title}</h3>
            <p class="mt-1 text-sm text-surface-400">{snippet.description}</p>
            <span class="mt-1 text-xs text-surface-500 font-mono">{snippet.filename}</span>
          </div>
          <div class="overflow-x-auto">
            <Code code={snippet.code} lang={snippet.lang} theme={THEME} />
          </div>
        </div>
      ))}
    </div>
  </div>
</section>
```

### Pipeline Stepper with Arrow Connectors

```astro
---
// CONT-05: Architecture pipeline diagram
import ArrowRightIcon from "../../icons/arrow-right.svg";

const phases = [
  { step: "1", name: "Setup", desc: "Config & credentials" },
  { step: "2", name: "Login", desc: "Platform auth" },
  { step: "3", name: "Search", desc: "Job discovery" },
  { step: "4", name: "Score", desc: "Match scoring" },
  { step: "5", name: "Apply", desc: "Application submit" },
];
---

<section id="architecture" class="py-20 bg-white">
  <div class="max-w-6xl mx-auto px-4">
    <!-- Desktop: horizontal flow -->
    <div class="hidden md:flex items-center justify-between">
      {phases.map((phase, i) => (
        <>
          <div class="flex flex-col items-center text-center flex-1">
            <div class="w-14 h-14 rounded-full bg-primary-600 text-white flex items-center justify-center font-display font-bold text-xl">
              {phase.step}
            </div>
            <div class="mt-3 font-display font-semibold text-surface-900">{phase.name}</div>
            <div class="mt-1 text-sm text-surface-500">{phase.desc}</div>
          </div>
          {i < phases.length - 1 && (
            <div class="text-primary-300 mx-2 shrink-0">
              <ArrowRightIcon width="24" height="24" />
            </div>
          )}
        </>
      ))}
    </div>
    <!-- Mobile: vertical list -->
    <div class="md:hidden space-y-6">
      {phases.map((phase) => (
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-primary-600 text-white flex items-center justify-center font-display font-bold shrink-0">
            {phase.step}
          </div>
          <div>
            <div class="font-display font-semibold text-surface-900">{phase.name}</div>
            <div class="text-sm text-surface-500">{phase.desc}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
</section>
```

### Quick Start with Code Blocks

```astro
---
import { Code } from 'astro:components';

const THEME = "github-dark-default";

const steps = [
  { num: "1", title: "Clone the repository", code: "git clone https://github.com/patrykgolabek/jobs.git && cd jobs", lang: "bash" },
  { num: "2", title: "Install dependencies", code: "pip install -r requirements.txt && playwright install chromium", lang: "bash" },
  { num: "3", title: "Configure your profile", code: "cp config.example.yaml config.yaml\n# Edit config.yaml with your search queries, target titles, and tech keywords", lang: "bash" },
  { num: "4", title: "Run the pipeline", code: "python orchestrator.py --platforms indeed remoteok", lang: "bash" },
  { num: "5", title: "Open the dashboard", code: "python -m webapp.app\n# Visit http://localhost:8000", lang: "bash" },
];
---

<section id="quickstart" class="py-20 bg-surface-50">
  <div class="max-w-3xl mx-auto px-4">
    <h2 class="font-display text-3xl font-bold text-surface-900 text-center">Quick Start</h2>
    <p class="mt-3 text-surface-600 text-center">Up and running in five steps</p>
    <div class="mt-12 space-y-8">
      {steps.map((step) => (
        <div>
          <div class="flex items-center gap-3 mb-3">
            <span class="w-8 h-8 rounded-full bg-primary-600 text-white flex items-center justify-center font-display font-bold text-sm shrink-0">
              {step.num}
            </span>
            <h3 class="font-display font-semibold text-surface-900">{step.title}</h3>
          </div>
          <div class="ml-11 rounded-lg overflow-hidden">
            <Code code={step.code} lang={step.lang} theme={THEME} />
          </div>
        </div>
      ))}
    </div>
  </div>
</section>
```

## Code Snippet Selection

The three code snippets for CONT-06 should demonstrate design decisions, not boilerplate. Based on analysis of the actual codebase:

### Recommended Snippets

| Snippet | Source File | Lines | What It Shows |
|---------|------------|-------|---------------|
| **Platform Protocol** | `platforms/protocols.py` | ~15 | Runtime-checkable Protocol pattern -- extensibility via duck typing, not inheritance |
| **Decorator Registry** | `platforms/registry.py` | ~15 | Fail-fast validation at import time -- new platforms get immediate feedback on missing methods |
| **Scoring Engine** | `scorer.py` | ~18 | Weighted multi-factor computation with explainable breakdown -- transparent, auditable scoring |

### Why These Three

1. **Protocol** shows the system is designed for extension (not a monolith)
2. **Registry** shows metaprogramming discipline (fail fast, not fail at runtime)
3. **Scorer** shows domain logic with real business rules (not just CRUD)

Together, they tell the story: "extensible architecture + disciplined validation + meaningful domain logic."

### Snippet Length Guidance

Each snippet should be 12-20 lines. Long enough to show the pattern, short enough to be readable in a browser without scrolling. Trim imports, docstrings, and helper methods. Keep the core logic.

## Milestone Data (Verified Source of Truth)

Data extracted from PROJECT.md and ROADMAP.md (verified 2026-02-13):

| Milestone | Shipped | Phases | Plans | Key Stats | Headline Feature |
|-----------|---------|--------|-------|-----------|-----------------|
| v1.0 MVP | Feb 8 | 8 | 24 | 6,705 LOC | Full pipeline: scrape, score, dashboard, AI resume, apply |
| v1.1 Test Suite | Feb 8 | 7 | 14 | 428 tests, 80%+ coverage | Comprehensive testing + CI |
| v1.2 Claude CLI | Feb 11 | 4 | 7 | 581 tests, 18K+ LOC total | SDK replaced with CLI subprocess |

**Notable narrative points:**
- v1.0 and v1.1 shipped on the same day (Feb 8) -- shows velocity
- v1.2 shipped 3 days later -- shows rapid iteration
- Test count grew 428 -> 581 across v1.1 and v1.2
- Total LOC grew from 6,705 to 18,022 across all milestones

## New Icons Needed

Phase 22 may need 1-2 new SVG icons not present in the Phase 21 icon set:

| Icon | Usage | Source |
|------|-------|--------|
| `arrow-right` | Pipeline step connectors (CONT-05) | Simple right-pointing chevron/arrow, stroke-based |
| `chevron-down` | Mobile pipeline vertical connectors (optional) | Simple downward chevron |

These can be minimal inline SVGs (3-5 lines each) or sourced from Lucide (MIT license). The existing icon pattern (import as SVG component, pass `width`/`height`/`fill` props) applies.

Alternatively, the arrow can be a unicode character (`→`) or a Tailwind border triangle, avoiding the need for additional SVG files entirely.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prism.js client-side highlighting | Astro `<Code />` with Shiki (build-time) | Astro 2.0+ (2023) | Zero JS, faster page loads, no FOUC |
| `highlight.js` with manual `<pre>` setup | Astro `<Code />` component | Astro built-in | No configuration needed, just import and use |
| Custom CSS timeline components | Tailwind utility-based timelines | Tailwind v4 (2025) | More responsive utilities, easier pseudo-element styling |
| SVG/Canvas diagrams for pipelines | CSS flexbox steppers | Modern CSS (2024+) | Responsive by default, text-selectable, accessible |

**Deprecated/outdated:**
- `@astrojs/prism` integration: Still works but Shiki is the default and preferred highlighter
- Manual Shiki setup (`getHighlighter()` API): Not needed when using the built-in `<Code />` component

## Open Questions

1. **Code snippet theme for dark mode (Phase 23)**
   - What we know: `github-dark-default` works well on a `bg-surface-900` dark section. When dark mode is added in Phase 23, the light sections will also go dark.
   - What's unclear: Whether to use a single theme for all modes or switch themes with `prefers-color-scheme`
   - Recommendation: Use `github-dark-default` for now. It works on both light and dark backgrounds. Dark code blocks are universally expected by developers. Revisit in Phase 23 if needed.

2. **Pipeline section naming: "Architecture" vs "How It Works"**
   - What we know: CONT-05 says "Architecture/pipeline diagram." The Features section is titled "What It Does."
   - What's unclear: Best heading for the target audience (recruiters + engineers)
   - Recommendation: Use "How It Works" as the visible heading (accessible to non-technical viewers) with `id="architecture"` for the anchor link (technical). The content is a pipeline diagram, which is understandable without the word "architecture."

3. **Section ordering within Phase 22's new content**
   - What we know: The 4 new sections go after TechStack and before Footer
   - What's unclear: Optimal ordering of Architecture vs Code vs Timeline vs QuickStart
   - Recommendation: Architecture -> Code -> Timeline -> QuickStart. This follows a narrative arc: how it works (high level) -> how it's built (code) -> how it evolved (timeline) -> how to use it (quickstart).

## Sources

### Primary (HIGH confidence)
- [Astro Syntax Highlighting Guide](https://docs.astro.build/en/guides/syntax-highlighting/) -- `<Code />` component usage, theme prop, wrap prop, Shiki integration details
- [Astro Built-in Components Reference](https://docs.astro.build/en/reference/components-reference/) -- `<Code />` props (code, lang, theme, wrap, inline, transformers, defaultColor)
- Shiki package in `site/node_modules/shiki` -- version 3.22.0, `github-dark-default` theme verified present
- Phase 21 completed components -- established section composition pattern, icon import pattern, responsive grid pattern (verified by reading source files)
- PROJECT.md / ROADMAP.md / STATE.md -- milestone data, LOC counts, test counts, dates (verified 2026-02-13)
- Actual source files (`protocols.py`, `registry.py`, `scorer.py`) -- code snippet content verified against real codebase

### Secondary (MEDIUM confidence)
- [HyperUI Step Components](https://www.hyperui.dev/components/application/steps) -- Tailwind CSS v4 step indicator patterns, responsive stepper layouts
- [Flowbite Timeline Components](https://flowbite.com/docs/components/timeline/) -- Tailwind timeline patterns with vertical line connectors
- [Shiki Themes Documentation](https://shiki.style/themes) -- theme naming conventions, available theme list

### Tertiary (LOW confidence)
- None. All findings verified with primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; Astro `<Code />` component and Shiki verified in node_modules
- Architecture patterns: HIGH - All patterns follow established Phase 21 conventions; `<Code />` API verified via official Astro docs
- Code snippet content: HIGH - All three snippets verified against actual source files in the codebase
- Pipeline/timeline layout: HIGH - Standard CSS flexbox/grid patterns with Tailwind utilities; responsive behavior well-understood
- Pitfalls: HIGH - Code block overflow, theme inheritance, section backgrounds all verified through documentation or testing

**Research date:** 2026-02-13
**Valid until:** 2026-03-13 (30 days -- stable ecosystem, no breaking changes expected)
