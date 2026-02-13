# Phase 23: CI/CD, Deployment, and Dark Mode - Research

**Researched:** 2026-02-13
**Domain:** GitHub Actions deployment, Tailwind CSS v4 dark mode, Astro integrations (sitemap, JSON-LD)
**Confidence:** HIGH

## Summary

This phase covers three distinct but related concerns: (1) deploying the Astro site to GitHub Pages via a dedicated GitHub Actions workflow, (2) ensuring CI workflow isolation between Python tests and site deployment, and (3) adding dark mode support with theme toggle persistence across ClientRouter navigations.

The deployment story is straightforward -- `withastro/action@v5` handles the Astro build natively with a `path: ./site` parameter for monorepo setups. The existing Python CI at `.github/workflows/ci.yml` needs `paths-ignore: ['site/**']` added to both `push` and `pull_request` triggers. The deploy workflow uses `paths: ['site/**']` to only trigger on site changes. The dark mode implementation requires a two-layer approach: (a) semantic color tokens as CSS custom properties overridden via `@media (prefers-color-scheme: dark)`, and (b) a `@custom-variant dark` directive in Tailwind for optional manual toggle support. The site already uses OKLCH-based `@theme` tokens for `primary-*` and `surface-*` palettes, so dark mode requires defining dark variants of these semantic values and adding `dark:` utility classes to every component.

Sitemap generation is handled by `@astrojs/sitemap` (add integration, already has `site` configured). JSON-LD structured data for SoftwareApplication schema is a manual `<script type="application/ld+json">` block in the layout head.

**Primary recommendation:** Use `withastro/action@v5` with `path: ./site` for deployment, Tailwind v4 `@custom-variant dark` with `data-theme` attribute for dark mode (supporting both system preference and manual toggle), and `@astrojs/sitemap` for sitemap generation.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| withastro/action | v5 (5.2.0) | GitHub Actions build + upload for Astro | Official Astro action, handles install/build/upload in one step |
| actions/deploy-pages | v4 | GitHub Pages deployment | Official GitHub action for Pages deployment |
| actions/checkout | v6 | Repository checkout | Standard checkout action (already used in ci.yml) |
| @astrojs/sitemap | latest | Sitemap generation | Official Astro integration, auto-generates sitemap-index.xml + sitemap-0.xml |
| Tailwind CSS | 4.1.18 (installed) | Dark mode utilities | Already installed; `dark:` variant + `@custom-variant` for toggle |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| actions/configure-pages | v5 | Configure GitHub Pages | Only needed if Pages isn't already configured in repo settings |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@custom-variant dark` (selector) | Default `prefers-color-scheme` only | No manual toggle capability; simpler but less user control |
| `data-theme` attribute | `.dark` class | `data-theme` is more semantic, avoids collision with other class-based logic |
| `@astrojs/sitemap` | Manual sitemap.xml | Integration handles multi-page, base path, sitemap-index automatically |

**Installation:**
```bash
cd site && npx astro add sitemap
```

No additional npm packages needed for dark mode (Tailwind v4 dark: variant is built-in). No additional packages for JSON-LD (manual `<script>` tag).

## Architecture Patterns

### GitHub Actions Workflow Structure

```
.github/workflows/
├── ci.yml              # Python CI (add paths-ignore: ['site/**'])
└── deploy-site.yml     # NEW: Astro site deploy (paths: ['site/**'])
```

### Dark Mode CSS Architecture

```
site/src/
├── styles/
│   └── global.css       # @theme tokens + dark mode overrides + @custom-variant
├── layouts/
│   └── BaseLayout.astro # data-theme attribute on <html>, JSON-LD, theme script
└── components/
    ├── ui/
    │   └── ThemeToggle.astro  # NEW: dark mode toggle (web component or inline)
    └── sections/
        └── *.astro      # Add dark: variants to all section components
```

### Pattern 1: Semantic Color Tokens with Dark Override

**What:** Define `@theme` tokens for light mode, then override the underlying CSS variables inside a `@media (prefers-color-scheme: dark)` block or scoped to `[data-theme=dark]`. The `@theme` directive itself is top-level only and cannot be nested, but the CSS custom properties it generates CAN be overridden in any selector/media query.

**When to use:** When you have a design system with OKLCH color tokens that need dark variants.

**Example:**
```css
/* Source: Tailwind CSS v4 docs (tailwindcss.com/docs/theme) + dark-mode docs */
@import "tailwindcss";

@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));

@theme {
  /* Light mode primary palette (blues) -- already defined */
  --color-primary-50: oklch(0.97 0.014 254.604);
  --color-primary-600: oklch(0.546 0.245 262.881);
  /* ... etc */

  /* Light mode surface palette (grays/slate) -- already defined */
  --color-surface-50: oklch(0.984 0.003 247.858);
  --color-surface-900: oklch(0.208 0.042 265.755);
  /* ... etc */

  /* Font families -- already defined, no dark override needed */
  --font-sans: "Inter Variable", ui-sans-serif, system-ui, sans-serif;
  --font-display: "DM Sans Variable", ui-sans-serif, system-ui, sans-serif;
}
```

**Key insight:** `@theme` tokens generate CSS custom properties on `:root`. These properties can then be overridden in `[data-theme=dark]` or `@media (prefers-color-scheme: dark)` selectors. However, the approach for this project should NOT override the `@theme` variables themselves for dark mode -- instead, use Tailwind's `dark:` variant on utility classes (e.g., `dark:bg-surface-900 dark:text-surface-50`). This is the standard Tailwind approach and avoids complexity of runtime variable swapping.

### Pattern 2: Dark Mode with Tailwind `dark:` Utilities (RECOMMENDED)

**What:** Use `dark:` prefix on Tailwind utility classes to specify dark-mode alternatives directly in the HTML.

**When to use:** Always -- this is the standard Tailwind approach.

**Example:**
```html
<!-- Source: tailwindcss.com/docs/dark-mode -->
<!-- Light: white bg, dark text. Dark: dark bg, light text -->
<section class="bg-white dark:bg-surface-900 text-surface-900 dark:text-surface-100">
  <h2 class="text-surface-900 dark:text-white">Title</h2>
  <p class="text-surface-600 dark:text-surface-300">Body text</p>
  <div class="border-surface-200 dark:border-surface-700">Card</div>
</section>
```

### Pattern 3: Theme Toggle with ClientRouter Persistence

**What:** An inline script in `<head>` that reads `localStorage` and system preference, sets `data-theme` on `<html>`, and an `astro:after-swap` listener to re-apply after ClientRouter navigations.

**When to use:** When using Astro's ClientRouter (ViewTransitions) with a manual dark mode toggle.

**Example:**
```html
<!-- Source: astro-tips.dev/recipes/dark-mode/ + tailwindcss.com/docs/dark-mode -->
<script is:inline>
  // Runs on every page load (inline = not deferred)
  ;(function() {
    const stored = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (systemDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
  })();
</script>

<!-- Separate script for ClientRouter re-application -->
<script>
  document.addEventListener('astro:after-swap', () => {
    const stored = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (systemDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
  });
</script>
```

### Anti-Patterns to Avoid

- **Overriding `@theme` variables inside media queries:** `@theme` is top-level only. You CANNOT nest `@theme` inside `@media` or selectors. Use `dark:` utilities or CSS variable overrides instead.
- **Using `is:inline` for the `astro:after-swap` listener:** The `astro:after-swap` script should NOT be `is:inline` -- it needs to be a regular script that Astro processes (deduplicates across navigations). Only the initial theme-setting IIFE should be `is:inline` to run synchronously in `<head>` to prevent FOUC.
- **Forgetting `style.colorScheme`:** Without setting `colorScheme`, browser chrome (scrollbars, form controls) won't respect the theme.
- **Hardcoding `bg-white` instead of using surface tokens:** Sections using `bg-white` will look wrong in dark mode. Use `bg-surface-50 dark:bg-surface-950` or similar.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sitemap generation | Manual XML file | `@astrojs/sitemap` | Handles base path, multi-page, sitemap-index, robots.txt reference |
| Astro build + upload for Pages | Custom build/upload steps | `withastro/action@v5` | Detects package manager from lockfile, caches, handles artifact upload |
| Dark mode FOUC prevention | Custom blocking script | Inline `is:inline` script pattern | Well-established pattern; must run synchronously before paint |
| Theme persistence across navigation | Custom MutationObserver | `astro:after-swap` event | Built into Astro's ClientRouter; fires after DOM swap |
| JSON-LD validation | Custom validation | schema.org validator or Google Rich Results Test | Authoritative validation tools |

**Key insight:** The Astro ecosystem provides official solutions for deployment and sitemap. Dark mode is a CSS + small JS concern that Tailwind v4's `dark:` variant handles natively -- the only custom code needed is the theme toggle and persistence scripts.

## Common Pitfalls

### Pitfall 1: Flash of Unstyled Content (FOUC) on Dark Mode

**What goes wrong:** Page flashes white before dark theme is applied.
**Why it happens:** Theme script runs after paint, or script is deferred/async.
**How to avoid:** Place theme detection as an `is:inline` script in `<head>` BEFORE any stylesheets render. The script must be synchronous and run before first paint.
**Warning signs:** Visible white flash on page load when system is in dark mode.

### Pitfall 2: ClientRouter Resets Theme on Navigation

**What goes wrong:** After clicking a link, theme reverts to light mode.
**Why it happens:** ClientRouter swaps the DOM but doesn't re-run `is:inline` scripts. The new `<html>` element lacks the `data-theme` attribute.
**How to avoid:** Add `astro:after-swap` event listener (NOT `is:inline`) that re-applies theme from localStorage.
**Warning signs:** Theme works on first load but resets on internal navigation.

### Pitfall 3: `paths-ignore` Cannot Be Combined with `paths` on Same Event

**What goes wrong:** Workflow syntax error or unexpected trigger behavior.
**Why it happens:** GitHub Actions does not allow both `paths` and `paths-ignore` on the same event. Must use one or the other, or use `paths` with `!` negation patterns.
**How to avoid:** Use `paths-ignore: ['site/**']` on Python CI, and `paths: ['site/**']` on deploy workflow. Never try to combine both.
**Warning signs:** Workflow triggers when it shouldn't, or fails to trigger.

### Pitfall 4: `bg-white` Hardcoded in Components

**What goes wrong:** Three sections (Features, Architecture, QuickStart) use `bg-white` directly, which won't change in dark mode.
**Why it happens:** `bg-white` is a fixed value, not tied to the dark: variant automatically.
**How to avoid:** Replace `bg-white` with surface token pairs: `bg-white dark:bg-surface-950` or similar.
**Warning signs:** Bright white sections appearing in otherwise dark page.

### Pitfall 5: GitHub Pages Base Path Mismatch

**What goes wrong:** Assets 404 at deployed URL, or links point to wrong paths.
**Why it happens:** Astro config `base: "/jobs"` doesn't match the actual GitHub Pages URL structure.
**How to avoid:** Verify `site` and `base` in `astro.config.mjs` match the actual GitHub repository name and username. Current config has `site: "https://patrykgolabek.github.io"` but the git remote is `PatrykQuantumNomad/jobs`. This MUST be reconciled.
**Warning signs:** 404 errors on CSS, JS, fonts, or images after deployment.

### Pitfall 6: Deploy Workflow Needs Pages Enabled in Repo Settings

**What goes wrong:** Deploy fails with "Pages not configured" error.
**Why it happens:** GitHub Pages must be enabled in repo Settings > Pages with "Source: GitHub Actions" selected.
**How to avoid:** Enable Pages in repo settings BEFORE first deploy. Set source to "GitHub Actions" (not "Deploy from a branch").
**Warning signs:** Deployment step fails with permissions or configuration error.

### Pitfall 7: SVG Icons Not Visible in Dark Mode

**What goes wrong:** SVG icons that use `fill="currentColor"` or hardcoded colors may become invisible against dark backgrounds.
**Why it happens:** Icons inherit text color via `currentColor`, but if parent text color doesn't have a dark variant, icons vanish.
**How to avoid:** Ensure all elements containing icons have both light and dark text color utilities.
**Warning signs:** Missing icons only visible when inspecting DOM.

## Code Examples

Verified patterns from official sources:

### Deploy Workflow (deploy-site.yml)

```yaml
# Source: github.com/withastro/action README + docs.astro.build/en/guides/deploy/github/
name: Deploy Site

on:
  push:
    branches: [main]
    paths: ['site/**']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6
      - name: Build Astro site
        uses: withastro/action@v5
        with:
          path: ./site

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

### Python CI paths-ignore Update

```yaml
# Source: docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions
name: CI

on:
  push:
    branches: [main]
    paths-ignore: ['site/**']
  pull_request:
    branches: [main]
    paths-ignore: ['site/**']
```

### Tailwind v4 Dark Mode Configuration (global.css)

```css
/* Source: tailwindcss.com/docs/dark-mode */
@import "tailwindcss";

@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));

@theme {
  /* Primary palette (blues) -- existing, unchanged */
  --color-primary-50: oklch(0.97 0.014 254.604);
  /* ... all existing primary tokens ... */

  /* Surface palette (grays/slate) -- existing, unchanged */
  --color-surface-50: oklch(0.984 0.003 247.858);
  /* ... all existing surface tokens ... */

  /* Font families -- existing, unchanged */
  --font-sans: "Inter Variable", ui-sans-serif, system-ui, sans-serif;
  --font-display: "DM Sans Variable", ui-sans-serif, system-ui, sans-serif;
}
```

### Dark Mode Theme Script (BaseLayout.astro head)

```html
<!-- Source: astro-tips.dev/recipes/dark-mode/ adapted for data-theme -->
<script is:inline>
  ;(function() {
    const stored = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored === 'dark' || stored === 'light'
      ? stored
      : (systemDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
  })();
</script>
```

### ClientRouter Theme Persistence

```html
<!-- Source: astro-tips.dev/recipes/dark-mode/ -->
<script>
  document.addEventListener('astro:after-swap', () => {
    const stored = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored === 'dark' || stored === 'light'
      ? stored
      : (systemDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
  });
</script>
```

### Astro Sitemap Integration (astro.config.mjs)

```javascript
// Source: docs.astro.build/en/guides/integrations-guide/sitemap/
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://patrykgolabek.github.io",
  base: "/jobs",
  trailingSlash: "always",
  integrations: [sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
```

### JSON-LD Structured Data (in BaseLayout.astro head)

```html
<!-- Source: schema.org/SoftwareApplication -->
<script type="application/ld+json" set:html={JSON.stringify({
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "JobFlow",
  "description": "Self-hosted pipeline that scrapes job boards, scores matches against your profile, and automates applications with human-in-the-loop safety.",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows",
  "url": "https://patrykgolabek.github.io/jobs/",
  "author": {
    "@type": "Person",
    "name": "Patryk Golabek",
    "url": "https://patrykgolabek.dev"
  },
  "softwareVersion": "1.2",
  "license": "https://opensource.org/licenses/MIT",
  "featureList": [
    "Multi-platform job scraping (Indeed, Dice, RemoteOK)",
    "AI-powered job scoring with Claude CLI",
    "Resume tailoring with anti-fabrication validation",
    "Web dashboard with real-time SSE updates",
    "Human-in-the-loop application automation"
  ],
  "runtimePlatform": "Python 3.14",
  "downloadUrl": "https://github.com/patrykgolabek/jobs"
})} />
```

### Dark Mode Color Mapping Strategy

Current component color usage and their dark mode counterparts:

```
LIGHT MODE              → DARK MODE
bg-surface-50           → dark:bg-surface-950
bg-white                → dark:bg-surface-950 (or dark:bg-surface-900)
bg-surface-900          → dark:bg-surface-950 (already dark, minor tweak)
bg-primary-900          → (already dark, keep as-is)
text-surface-900        → dark:text-surface-50
text-surface-600        → dark:text-surface-300
text-surface-500        → dark:text-surface-400
text-surface-400        → dark:text-surface-500 (inverse)
border-surface-200      → dark:border-surface-700
border-surface-300      → dark:border-surface-600
bg-primary-50           → dark:bg-primary-950
bg-primary-100          → dark:bg-primary-900
text-primary-500        → dark:text-primary-400
text-primary-600        → dark:text-primary-400
text-primary-700        → dark:text-primary-300
bg-primary-600          → (keep, good contrast on dark)
border-primary-200      → dark:border-primary-800
border-primary-300      → dark:border-primary-700
```

Sections already dark (CodeSnippets `bg-surface-900`, Footer `bg-surface-900`, Stats `bg-primary-900`) need minimal or no changes.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` darkMode option | `@custom-variant dark` in CSS | Tailwind v4 (Jan 2025) | No JS config file needed |
| `ViewTransitions` component | `ClientRouter` component | Astro 5 (Dec 2024) | Renamed; same functionality |
| `withastro/action@v4` | `withastro/action@v5` | ~mid 2025 | Node 22 default, build caching |
| Manual sitemap XML | `@astrojs/sitemap` | Astro integrations (stable) | Auto-generated from routes |

**Deprecated/outdated:**
- `darkMode: 'class'` in tailwind.config.js: Replaced by `@custom-variant dark` in CSS (Tailwind v4)
- `<ViewTransitions />`: Renamed to `<ClientRouter />` in Astro 5
- `withastro/action@v3/v4`: Superseded by v5 with Node 22 default and build caching

## Open Questions

1. **GitHub username discrepancy**
   - What we know: `astro.config.mjs` has `site: "https://patrykgolabek.github.io"` but `git remote` shows `PatrykQuantumNomad/jobs.git`
   - What's unclear: Which GitHub username actually hosts the Pages site
   - Recommendation: Verify the correct username. The `site` config in astro.config.mjs must match the actual GitHub Pages domain. If the repo is `PatrykQuantumNomad/jobs`, then the URL would be `https://PatrykQuantumNomad.github.io/jobs/` (case matters in Pages). Leave as-is if the user set it intentionally (might be planning to transfer the repo).

2. **Dark mode toggle UI placement**
   - What we know: Requirements say "optional toggle" alongside `prefers-color-scheme` detection
   - What's unclear: Where in the UI to place the toggle (header? footer? floating button?)
   - Recommendation: Add a small sun/moon icon toggle in the top-right corner of the page, fixed position or in a minimal nav bar. Keep it unobtrusive.

3. **Pages environment setup**
   - What we know: The deploy workflow needs `environment: github-pages` and Pages must be enabled in repo settings
   - What's unclear: Whether Pages is already configured in the repo settings
   - Recommendation: Include a manual step in the plan to verify/enable Pages in repo settings with source set to "GitHub Actions"

## Sources

### Primary (HIGH confidence)
- [withastro/action GitHub repository](https://github.com/withastro/action) - v5 inputs, workflow example, path parameter
- [Astro GitHub Pages deploy guide](https://docs.astro.build/en/guides/deploy/github/) - Complete workflow YAML, permissions, environment config
- [Tailwind CSS v4 dark mode docs](https://tailwindcss.com/docs/dark-mode) - `@custom-variant`, selector strategies, three-way toggle
- [Tailwind CSS v4 @theme docs](https://tailwindcss.com/docs/theme) - Theme variable definition, namespaces, inline option, runtime override behavior
- [@astrojs/sitemap docs](https://docs.astro.build/en/guides/integrations-guide/sitemap/) - Installation, configuration, output files
- [GitHub Actions workflow syntax](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions) - paths/paths-ignore filter rules, glob patterns
- [schema.org/SoftwareApplication](https://schema.org/SoftwareApplication) - JSON-LD properties for SoftwareApplication type

### Secondary (MEDIUM confidence)
- [Astro Tips dark mode recipe](https://astro-tips.dev/recipes/dark-mode/) - ClientRouter persistence pattern, theme manager script, astro:after-swap
- [Tailwind CSS v4 GitHub Discussion #15083](https://github.com/tailwindlabs/tailwindcss/discussions/15083) - Community patterns for dark mode with @theme variables

### Tertiary (LOW confidence)
- GitHub Pages username discrepancy needs manual verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official docs for all tools verified, versions confirmed from installed packages
- Architecture: HIGH - Patterns verified from official Astro, Tailwind, and GitHub Actions documentation
- Pitfalls: HIGH - FOUC prevention, ClientRouter persistence, paths-ignore limitations all verified from official docs and community issues
- Dark mode color mapping: MEDIUM - Color mapping strategy is based on standard contrast principles with OKLCH values; specific dark OKLCH values will need visual tuning

**Research date:** 2026-02-13
**Valid until:** 2026-03-13 (stable technologies, 30-day validity)
