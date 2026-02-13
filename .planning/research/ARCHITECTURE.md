# Architecture Patterns

**Domain:** Astro static site integration within an existing Python repo for GitHub Pages deployment
**Researched:** 2026-02-13
**Confidence:** HIGH (based on Astro official docs, withastro/action v5.2.0 source, GitHub Actions docs, existing repo analysis)

## Recommended Architecture

### System Overview: Existing Repo + New Site

**Current repo structure (Python app at root):**
```
jobs/
  orchestrator.py
  config.py, models.py, scorer.py, ...
  platforms/
  webapp/
  resume_ai/
  tests/
  pyproject.toml, uv.lock
  .github/workflows/ci.yml          <-- existing CI (pytest + ruff)
  .planning/
  .gitignore
```

**Target structure (add /site subfolder):**
```
jobs/
  orchestrator.py                    # Python app (unchanged)
  config.py, models.py, ...         # Python app (unchanged)
  platforms/, webapp/, resume_ai/   # Python app (unchanged)
  tests/                            # Python tests (unchanged)
  pyproject.toml, uv.lock           # Python tooling (unchanged)
  .github/workflows/
    ci.yml                          # Python CI (unchanged, add path filter)
    deploy-site.yml                 # NEW: Astro build + GitHub Pages deploy
  site/                             # NEW: Astro project (self-contained)
    astro.config.mjs
    package.json
    package-lock.json               # MUST commit (withastro/action detects it)
    tsconfig.json
    src/
      assets/                       # Optimized images (screenshots, logos)
        screenshots/
      components/                   # Reusable Astro components
        sections/                   # Page sections (Hero, Features, etc.)
        ui/                         # Small UI primitives (Button, Badge, etc.)
      layouts/
        BaseLayout.astro            # HTML shell, meta, fonts, global styles
      pages/
        index.astro                 # Single-page marketing site
      styles/
        global.css                  # Tailwind + custom properties
    public/
      favicon.svg
      CNAME                         # If using custom domain
  .gitignore                        # Updated: add node_modules/ and site/dist/
```

### Key Architectural Decision: Self-Contained Subfolder

The `/site` directory is a **complete, independent Astro project**. It has its own `package.json`, its own `node_modules/`, its own build output. The Python app and the Astro site share nothing at build time. This is the correct approach because:

1. **No toolchain contamination** -- Python tooling (uv, ruff, pytest) never touches `/site`. Node tooling (npm, astro) never touches the repo root.
2. **Independent CI** -- The Python CI workflow and the Pages deploy workflow trigger on different path globs and run completely independently.
3. **No package.json at root** -- Avoids confusing Python developers with JS tooling at the root level. No risk of `node_modules/` polluting the repo root.
4. **withastro/action supports this natively** -- The `path` parameter was designed for exactly this use case.

### Component Map

```
                    EXISTING (unchanged)              NEW
               +------------------------+
               |  .github/workflows/    |
               |    ci.yml (MODIFIED:   |
               |    add paths filter)   |
               +------------------------+
               |    deploy-site.yml     |  <-- NEW workflow
               +----------+------------+
                          |
             withastro/action@v5
             path: ./site
                          |
               +----------v------------+
               |   site/               |  <-- NEW directory (entire Astro project)
               |   astro.config.mjs    |
               |   package.json        |
               |   src/                |
               |     pages/index.astro |
               |     layouts/          |
               |     components/       |
               |     assets/           |
               |     styles/           |
               +----------+------------+
                          |
                   astro build
                          |
               +----------v------------+
               |   site/dist/          |  <-- Build output (gitignored)
               +----------+------------+
                          |
             actions/deploy-pages@v4
                          |
               +----------v------------+
               | username.github.io/   |
               | jobs/                 |  <-- Live site
               +-----------------------+
```

### Component Boundaries

| Component | Responsibility | Status | Communicates With |
|-----------|---------------|--------|-------------------|
| `site/` | Self-contained Astro project, all frontend code | **NEW** | None (fully independent) |
| `site/astro.config.mjs` | Site URL, base path, image optimization config | **NEW** | Astro build process |
| `site/src/pages/index.astro` | Single marketing page, imports section components | **NEW** | Layouts, section components |
| `site/src/layouts/BaseLayout.astro` | HTML shell, meta tags, OG tags, fonts, global CSS | **NEW** | Pages |
| `site/src/components/sections/` | Hero, Features, Pipeline, Screenshots, CTA sections | **NEW** | BaseLayout via slot |
| `site/src/components/ui/` | Button, Badge, Card, ScreenshotFrame primitives | **NEW** | Section components |
| `site/src/assets/screenshots/` | Dashboard screenshots (optimized at build via Sharp) | **NEW** | Section components via import |
| `.github/workflows/deploy-site.yml` | Astro build + GitHub Pages deployment | **NEW** | withastro/action, deploy-pages |
| `.github/workflows/ci.yml` | Python CI (add path filter to skip on site-only changes) | **MODIFIED** | No new dependencies |
| `.gitignore` | Add `node_modules/` and `site/dist/` | **MODIFIED** | N/A |

## New Components: Detailed Design

### 1. `site/astro.config.mjs` -- Configuration

```javascript
// site/astro.config.mjs
import { defineConfig } from 'astro/config';

export default defineConfig({
  // For project pages: username.github.io/jobs/
  site: 'https://username.github.io',
  base: '/jobs',

  // If using custom domain instead:
  // site: 'https://jobflow.dev',
  // base: '/',

  image: {
    // Sharp is the default service -- no config needed
    // Enable responsive image styles globally
    responsiveStyles: true,
  },

  build: {
    // Default 'dist' is fine -- withastro/action knows where to find it
    // assets: '_astro'  (default, fine)
  },

  // No integrations needed for a pure static marketing site
  // Tailwind via @astrojs/tailwind only if using Tailwind (recommended)
});
```

**Critical: base path configuration.**

For a repo named `jobs` deployed to `username.github.io/jobs/`, set `base: '/jobs'`. This prefixes all internal links and asset paths. Every `<a href>` and `<img src>` in the built site will be relative to `/jobs/`.

If using a custom domain (e.g., `jobflow.dev`), drop the `base` or set it to `'/'`. Add a `public/CNAME` file with the domain.

**The withastro/action handles this automatically** if you use the `actions/configure-pages` step upstream. The GitHub starter workflow passes `--site` and `--base` as CLI args to the build command. However, the simpler approach (hardcode in config) is better because it also works in local dev (`npm run dev` serves at `localhost:4321/jobs/`).

### 2. `.github/workflows/deploy-site.yml` -- Pages Deployment

```yaml
name: Deploy Site

on:
  push:
    branches: [main]
    paths:
      - 'site/**'
  workflow_dispatch:        # Manual trigger for first deploy or debugging

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages              # Different from CI's group (${{ github.workflow }}-...)
  cancel-in-progress: false # Let deployments finish (don't cancel mid-deploy)

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Install, build, and upload site
        uses: withastro/action@v5
        with:
          path: ./site      # Astro project is in /site subfolder

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Key design decisions:**

- **`paths: ['site/**']`** -- Only triggers when files in `/site` change. Python code changes do not trigger a deploy. This is the native GitHub Actions path filter (not `dorny/paths-filter`), which is sufficient here because we want workflow-level filtering, not job-level.
- **`workflow_dispatch`** -- Allows manual triggering for the initial setup or when debugging. Important for the first deploy before any `site/` commits exist.
- **`concurrency: group: pages`** -- Uses a DIFFERENT group name than the CI workflow. The CI uses `${{ github.workflow }}-${{ github.ref }}` which resolves to `CI-refs/heads/main`. The deploy uses `pages`. They never conflict.
- **`cancel-in-progress: false`** -- For Pages deploys, let the current deployment finish. Unlike CI where you want to cancel stale runs, a half-deployed site is worse than waiting.
- **`path: ./site`** -- The withastro/action detects the `package-lock.json` inside `./site`, installs dependencies there, runs `astro build` there, and uploads `./site/dist/` as the Pages artifact.
- **No `actions/configure-pages` step needed** -- The withastro/action handles Pages artifact upload internally. The starter workflow uses configure-pages only when building manually (not using withastro/action).

### 3. `.github/workflows/ci.yml` -- Modified (Add Path Filter)

```yaml
# EXISTING ci.yml -- add paths-ignore to skip on site-only changes
name: CI

on:
  push:
    branches: [main]
    paths-ignore:
      - 'site/**'
  pull_request:
    branches: [main]
    paths-ignore:
      - 'site/**'

# ... rest unchanged
```

**Why `paths-ignore` instead of `paths`:** The CI workflow should run on ALL changes EXCEPT site-only changes. Using `paths` would require listing every Python directory, which is fragile. `paths-ignore: ['site/**']` is the inverse -- "run unless ONLY site files changed." If a commit touches both `site/` and `scorer.py`, CI still runs.

### 4. `.gitignore` Updates

```gitignore
# Node (site subfolder)
node_modules/
site/dist/
site/.astro/
```

Adding `node_modules/` at the root level of `.gitignore` recursively ignores all `node_modules/` directories anywhere in the repo tree, including `site/node_modules/`. No need for a separate `.gitignore` inside `site/`.

### 5. Astro Component Architecture (Marketing Site)

#### Layout Layer

```
site/src/layouts/
  BaseLayout.astro        # HTML <head>, OG meta, fonts, global CSS, <slot/>
```

**BaseLayout.astro** handles:
- HTML lang, charset, viewport
- Page title (via prop), OG tags (title, description, image)
- Google Fonts or local font loading
- Global CSS import
- Dark/light mode (via `prefers-color-scheme` or manual toggle)
- Canonical URL construction using `Astro.site` + `Astro.url.pathname`

```astro
---
// site/src/layouts/BaseLayout.astro
interface Props {
  title: string;
  description: string;
  ogImage?: string;
}

const { title, description, ogImage = '/og-default.png' } = Astro.props;
const canonicalURL = new URL(Astro.url.pathname, Astro.site);
---
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content={description} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:image" content={new URL(ogImage, Astro.site)} />
  <link rel="canonical" href={canonicalURL} />
  <link rel="icon" type="image/svg+xml" href={`${import.meta.env.BASE_URL}favicon.svg`} />
</head>
<body>
  <slot />
</body>
</html>
```

**Note:** `import.meta.env.BASE_URL` is critical for project pages. All static asset references in HTML must use it so paths work under `/jobs/` prefix.

#### Section Components (Page Sections)

```
site/src/components/sections/
  Hero.astro              # Above-the-fold: headline, subtitle, CTA buttons
  Features.astro          # Grid of feature cards (scraping, scoring, dashboard, AI, apply)
  Pipeline.astro          # Visual pipeline diagram (scrape -> score -> review -> apply)
  Screenshots.astro       # Dashboard screenshot gallery with browser chrome frames
  TechStack.astro         # Technology badges/logos
  CTA.astro               # Final call-to-action (GitHub link, getting started)
  Footer.astro            # Links, license, attribution
```

Each section is a self-contained Astro component. The page composes them:

```astro
---
// site/src/pages/index.astro
import BaseLayout from '../layouts/BaseLayout.astro';
import Hero from '../components/sections/Hero.astro';
import Features from '../components/sections/Features.astro';
import Pipeline from '../components/sections/Pipeline.astro';
import Screenshots from '../components/sections/Screenshots.astro';
import TechStack from '../components/sections/TechStack.astro';
import CTA from '../components/sections/CTA.astro';
import Footer from '../components/sections/Footer.astro';
---
<BaseLayout title="JobFlow" description="AI-powered job search automation">
  <Hero />
  <Features />
  <Pipeline />
  <Screenshots />
  <TechStack />
  <CTA />
  <Footer />
</BaseLayout>
```

**No React/Vue needed.** A marketing landing page is entirely static. Astro components compile to zero JavaScript by default. Interactive elements (smooth scroll, mobile menu toggle) use vanilla JS in `<script>` tags within Astro components -- no framework hydration needed.

#### UI Primitives

```
site/src/components/ui/
  Button.astro            # <a> styled as button, with variant prop (primary/secondary/ghost)
  Badge.astro             # Tech stack badges, status indicators
  Card.astro              # Feature card wrapper
  ScreenshotFrame.astro   # Browser chrome mockup wrapping a screenshot image
  Section.astro           # Consistent section wrapper (padding, max-width, id for anchor)
```

### 6. Image Optimization Pipeline

**Strategy:** Store screenshots as PNGs in `site/src/assets/screenshots/`. Astro's built-in image service (Sharp) optimizes them at build time.

```astro
---
// Inside Screenshots.astro or ScreenshotFrame.astro
import { Picture } from 'astro:assets';
import dashboardImg from '../../assets/screenshots/dashboard.png';
---
<Picture
  src={dashboardImg}
  formats={['avif', 'webp']}
  widths={[400, 800, 1200]}
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 80vw, 1200px"
  alt="JobFlow dashboard showing scored job listings with filtering and search"
  class="rounded-lg shadow-xl"
/>
```

**How it works:**

1. **Source images** go in `src/assets/` (NOT `public/`). Images in `src/assets/` are processed by Sharp. Images in `public/` are served as-is.
2. **`<Picture>` component** generates a `<picture>` element with multiple `<source>` tags (avif, webp) and a `<img>` fallback (original format).
3. **`formats={['avif', 'webp']}`** -- AVIF for modern browsers (best compression), WebP for broad support, original PNG as fallback. Order matters: list most modern first.
4. **`widths={[400, 800, 1200]}`** -- Generates three size variants. Browser picks the best one based on viewport and device pixel ratio.
5. **`sizes` attribute** -- Tells the browser how wide the image will be rendered at each breakpoint, so it can pick the right `srcset` entry without waiting for CSS.
6. **Layout shift prevention** -- Astro automatically infers `width` and `height` from the source image and includes them in the `<img>` tag, preventing CLS.

**Image workflow for screenshots:**

```
1. Take screenshot of running dashboard (locally)
2. Save as PNG in site/src/assets/screenshots/dashboard.png
3. Astro build generates:
   site/dist/_astro/dashboard.abc123.avif (400w, 800w, 1200w)
   site/dist/_astro/dashboard.abc123.webp (400w, 800w, 1200w)
   site/dist/_astro/dashboard.abc123.png  (fallback)
4. HTML references the hashed filenames automatically
```

No external image CDN. No manual conversion. No separate image optimization step.

## Patterns to Follow

### Pattern 1: Base Path Awareness in All Links

**What:** Every internal link and asset reference must account for the `/jobs/` base path prefix.

**When:** Always, when deploying as a project page (not a custom domain).

**How:**
```astro
<!-- CORRECT: Use import.meta.env.BASE_URL for static assets in HTML -->
<link rel="icon" href={`${import.meta.env.BASE_URL}favicon.svg`} />

<!-- CORRECT: Anchor links for same-page navigation -->
<a href="#features">Features</a>  <!-- Hash links don't need base -->

<!-- CORRECT: Imported images (Astro handles path automatically) -->
import logo from '../assets/logo.svg';
<img src={logo.src} alt="Logo" />

<!-- WRONG: Hardcoded absolute path (breaks on project pages) -->
<link rel="icon" href="/favicon.svg" />
```

Astro automatically prefixes paths for imported assets and `<Image>`/`<Picture>` components. Manual HTML `href`/`src` attributes need `import.meta.env.BASE_URL` explicitly.

### Pattern 2: Section Component Data Flow (Props Down, No State)

**What:** Section components receive data via props or define data inline. No stores, no client-side state, no fetch calls.

**Why:** This is a static marketing page. All content is known at build time. Astro components run at build time and produce static HTML.

**Example:**
```astro
---
// site/src/components/sections/Features.astro
const features = [
  {
    icon: '🔍',
    title: 'Multi-Platform Discovery',
    description: 'Scrapes Indeed, Dice, and RemoteOK simultaneously.',
  },
  {
    icon: '🎯',
    title: 'Smart Scoring',
    description: 'Weighted scoring against your profile. 1-5 scale with explanations.',
  },
  // ...
];
---
<section id="features">
  <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
    {features.map(f => (
      <div class="p-6 rounded-lg border">
        <span class="text-3xl">{f.icon}</span>
        <h3 class="text-xl font-bold mt-4">{f.title}</h3>
        <p class="mt-2 text-gray-600">{f.description}</p>
      </div>
    ))}
  </div>
</section>
```

### Pattern 3: Separate Concurrency Groups for CI and Deploy

**What:** CI and deploy workflows use different `concurrency.group` names.

**Why:** If they share a group, a site deploy could cancel a running CI check (or vice versa). Each workflow protects its own domain.

```yaml
# ci.yml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}  # "CI-refs/heads/main"
  cancel-in-progress: true                          # Cancel stale CI runs

# deploy-site.yml
concurrency:
  group: pages                                      # "pages"
  cancel-in-progress: false                         # Let deploys finish
```

### Pattern 4: Commit the Lockfile, Gitignore node_modules

**What:** `site/package-lock.json` is committed. `node_modules/` is gitignored.

**Why:** The withastro/action auto-detects the package manager by scanning for a lockfile. If it finds `package-lock.json` in the `path` directory, it uses `npm`. If it finds `pnpm-lock.yaml`, it uses `pnpm`. No lockfile = action fails or falls back unpredictably.

```gitignore
# .gitignore (at repo root)
node_modules/      # Covers site/node_modules/ recursively
site/dist/         # Build output
site/.astro/       # Astro cache
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: package.json at Repo Root

**What:** Putting Astro's `package.json` at the repo root alongside `pyproject.toml`.

**Why bad:** Confuses contributors. Python devs run `uv sync` at root. If there is a `package.json` there too, editors auto-detect it as a JS project. ESLint, Prettier, and other JS tools may activate. CI may try to install npm deps at the wrong level. Keep the worlds separate.

**Instead:** All Node tooling lives inside `site/`. `cd site && npm install` is the only npm command needed.

### Anti-Pattern 2: Sharing CI and Deploy in One Workflow

**What:** Adding the Astro build job to the existing `ci.yml` workflow.

**Why bad:** Different triggers (Python CI runs on all code; site deploy runs only on `site/**`). Different permissions (deploy needs `pages: write` + `id-token: write`; CI needs neither). Different concurrency semantics. Mixing them creates complex conditional logic and permission escalation.

**Instead:** Two separate workflow files. Clean separation. Each workflow has exactly the permissions it needs.

### Anti-Pattern 3: Using `public/` for Screenshot Images

**What:** Putting dashboard screenshots in `site/public/screenshots/` instead of `site/src/assets/screenshots/`.

**Why bad:** Images in `public/` are served as-is with no optimization. A 2MB PNG stays a 2MB PNG. No AVIF/WebP conversion. No responsive `srcset` generation. No automatic width/height for CLS prevention.

**Instead:** All images that benefit from optimization go in `src/assets/`. Only truly static files (favicon, CNAME, robots.txt) go in `public/`.

### Anti-Pattern 4: Hardcoded Paths Without Base URL

**What:** Writing `href="/about"` or `src="/images/logo.png"` in templates.

**Why bad:** On a project page at `username.github.io/jobs/`, the path `/about` resolves to `username.github.io/about` (wrong). It should be `username.github.io/jobs/about`.

**Instead:** Use `import.meta.env.BASE_URL` for manual paths. Use Astro's `<Image>` / `<Picture>` for images (handles paths automatically). Hash links (`#features`) are fine as-is.

### Anti-Pattern 5: Adding Framework Integrations for Simple Interactivity

**What:** Installing `@astrojs/react` or `@astrojs/vue` to add a mobile menu toggle or smooth scroll.

**Why bad:** Adds ~40KB+ of framework JS to what should be a zero-JS static page. Marketing landing pages have trivial interactivity needs.

**Instead:** Use Astro's built-in `<script>` tag for vanilla JS. Astro bundles and optimizes `<script>` tags at build time.

```astro
<!-- Inside a component -->
<button id="mobile-menu-toggle">Menu</button>
<nav id="mobile-menu" class="hidden">...</nav>

<script>
  document.getElementById('mobile-menu-toggle')?.addEventListener('click', () => {
    document.getElementById('mobile-menu')?.classList.toggle('hidden');
  });
</script>
```

## Data Flow

There is **no runtime data flow** between the Python app and the Astro site. They are completely independent:

```
Python App (localhost:8000)          Astro Site (username.github.io/jobs/)
================================     ================================
Dynamic web app                      Static HTML/CSS/images
FastAPI + SQLite + htmx              Pre-rendered at build time
Runs locally on user machine         Hosted on GitHub Pages CDN
Contains real job data               Contains marketing copy + screenshots
Private (localhost only)             Public (anyone can visit)
```

The only connection is **content**: screenshots of the running dashboard are captured manually and committed to `site/src/assets/screenshots/`. The site describes what the Python app does, but does not call it, fetch from it, or depend on it at build time.

## Integration Points: Existing vs New Code

### Files Modified

| File | What Changes | Why |
|------|-------------|-----|
| `.github/workflows/ci.yml` | Add `paths-ignore: ['site/**']` to push and pull_request triggers | Skip Python CI on site-only changes |
| `.gitignore` | Add `node_modules/`, `site/dist/`, `site/.astro/` | Ignore Node artifacts |

### Files Created

| File | Purpose | Depends On |
|------|---------|-----------|
| `.github/workflows/deploy-site.yml` | Astro build + GitHub Pages deployment | withastro/action@v5, deploy-pages@v4 |
| `site/astro.config.mjs` | Site/base config, image optimization | Astro |
| `site/package.json` | Dependencies (astro, @astrojs/tailwind if used) | npm |
| `site/package-lock.json` | Lockfile (MUST commit for action detection) | npm |
| `site/tsconfig.json` | TypeScript config (Astro defaults) | Astro |
| `site/src/pages/index.astro` | Marketing page (composes sections) | Layout, all section components |
| `site/src/layouts/BaseLayout.astro` | HTML shell, meta, OG, fonts, global CSS | Astro |
| `site/src/components/sections/Hero.astro` | Above-the-fold section | BaseLayout, UI components |
| `site/src/components/sections/Features.astro` | Feature grid | UI components |
| `site/src/components/sections/Pipeline.astro` | Visual pipeline diagram | UI components |
| `site/src/components/sections/Screenshots.astro` | Dashboard screenshot gallery | ScreenshotFrame, astro:assets |
| `site/src/components/sections/TechStack.astro` | Technology badges | UI components |
| `site/src/components/sections/CTA.astro` | Call-to-action with GitHub link | UI components |
| `site/src/components/sections/Footer.astro` | Footer with links | None |
| `site/src/components/ui/Button.astro` | Link styled as button | None |
| `site/src/components/ui/Badge.astro` | Tech/status badge | None |
| `site/src/components/ui/Card.astro` | Feature card wrapper | None |
| `site/src/components/ui/Section.astro` | Consistent section wrapper | None |
| `site/src/components/ui/ScreenshotFrame.astro` | Browser chrome mockup | astro:assets Picture |
| `site/src/assets/screenshots/*.png` | Dashboard screenshots | Manual capture |
| `site/src/styles/global.css` | Global styles, CSS custom properties | Tailwind (optional) |
| `site/public/favicon.svg` | Site favicon | None |

### Dependencies Between New Components

```
.github/workflows/deploy-site.yml (standalone -- no code dependency)

site/astro.config.mjs (foundation -- configures build)
  |
  v
site/src/layouts/BaseLayout.astro (depends on config for base URL)
  |
  v
site/src/pages/index.astro (imports layout + all sections)
  |
  +---> site/src/components/sections/Hero.astro
  |       |
  |       +---> site/src/components/ui/Button.astro
  |
  +---> site/src/components/sections/Features.astro
  |       |
  |       +---> site/src/components/ui/Card.astro
  |
  +---> site/src/components/sections/Screenshots.astro
  |       |
  |       +---> site/src/components/ui/ScreenshotFrame.astro
  |       |       |
  |       |       +---> site/src/assets/screenshots/*.png (via astro:assets)
  |       |
  |       +---> astro:assets Picture component
  |
  +---> site/src/components/sections/Pipeline.astro
  +---> site/src/components/sections/TechStack.astro
  +---> site/src/components/sections/CTA.astro
  +---> site/src/components/sections/Footer.astro
```

## Build Order

```
Step 1: Scaffold Astro project in /site
    |   npm create astro@latest (or manual setup)
    |   Configure astro.config.mjs with site + base
    |   Commit package.json + package-lock.json
    |   Verify: npm run dev serves at localhost:4321/jobs/
    v
Step 2: Create BaseLayout.astro
    |   HTML head, meta tags, font loading, global CSS
    |   Verify: pages render with correct <head>
    v
Step 3: Create UI primitives (Button, Badge, Card, Section, ScreenshotFrame)
    |   Small, no dependencies on each other
    |   These can be built in parallel
    v
Step 4: Create section components (Hero, Features, Pipeline, TechStack, CTA, Footer)
    |   Depend on: UI primitives from step 3
    |   Content is placeholder initially, refined later
    v
Step 5: Create Screenshots section + capture actual screenshots
    |   Depends on: ScreenshotFrame (step 3), running Python app locally
    |   Save PNGs to site/src/assets/screenshots/
    |   Use <Picture> component with formats=['avif', 'webp']
    v
Step 6: Compose index.astro (import layout + all sections)
    |   Depends on: steps 2, 3, 4, 5
    |   Verify: npm run build succeeds, preview looks correct
    v
Step 7: Update .gitignore + ci.yml paths-ignore
    |   No code dependency, but needed before first push
    v
Step 8: Create deploy-site.yml workflow
    |   Depends on: site/ existing and building successfully
    |   Verify: enable GitHub Pages (Settings > Pages > GitHub Actions)
    v
Step 9: Push to main, verify deployment
    |   Check: site accessible at username.github.io/jobs/
    |   Check: all images load, links work, base path correct
    |   Check: Python CI still runs on Python changes
    |   Check: Python CI skips on site-only changes
```

**Rationale:** Steps 1-2 establish the foundation. Steps 3-5 build components bottom-up (primitives before sections). Step 6 is composition. Steps 7-9 are infrastructure and deployment. Steps 3-4 can be parallelized. Step 5 requires the running Python app for screenshots, so it has an external dependency.

## GitHub Pages Setup (One-Time Manual Steps)

Before the workflow can deploy, you must configure the repo:

1. Go to repo **Settings > Pages**
2. Under "Build and deployment", select **Source: GitHub Actions** (not "Deploy from a branch")
3. This enables the `actions/deploy-pages@v4` action to deploy

No other manual setup needed. The withastro/action handles everything else.

## Scalability Considerations

| Concern | At Launch | At 10 pages | At 50+ pages |
|---------|-----------|-------------|-------------|
| Build time | <10s (single page) | ~30s | Consider incremental builds |
| Image processing | <5s (few screenshots) | ~20s (Sharp parallelizes) | Add `cache: true` in action (default) |
| Deploy artifact size | <5MB | ~15MB | GitHub Pages limit: 1GB |
| Base path complexity | Manageable (one page) | More internal links to manage | Consider content collections |

For a single marketing landing page, none of these are concerns. The Astro build cache (enabled by default in withastro/action) speeds up subsequent builds by caching optimized images.

## Sources

- [Astro Deploy to GitHub Pages Guide](https://docs.astro.build/en/guides/deploy/github/) -- Official deployment docs (HIGH confidence)
- [withastro/action GitHub](https://github.com/withastro/action) -- v5.2.0, action.yml parameters (HIGH confidence)
- [Astro Configuration Reference](https://docs.astro.build/en/reference/configuration-reference/) -- site, base, trailingSlash, image config (HIGH confidence)
- [Astro Images Guide](https://docs.astro.build/en/guides/images/) -- Image/Picture components, src/ vs public/, responsive images (HIGH confidence)
- [Astro Project Structure](https://docs.astro.build/en/basics/project-structure/) -- Directory conventions (HIGH confidence)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions) -- paths, paths-ignore filters (HIGH confidence)
- [GitHub Actions Concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency) -- Concurrency group naming (HIGH confidence)
- [GitHub starter-workflows/pages/astro.yml](https://github.com/actions/starter-workflows/blob/main/pages/astro.yml) -- Official starter template (HIGH confidence)
