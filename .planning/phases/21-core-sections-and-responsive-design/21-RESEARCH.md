# Phase 21: Core Sections and Responsive Design - Research

**Researched:** 2026-02-13
**Domain:** Astro component composition, Tailwind v4 responsive grid layouts, browser mockup frames, section-based single-page architecture
**Confidence:** HIGH

## Summary

Phase 21 builds the visible content sections on top of the Phase 20 foundation (BaseLayout, Tailwind v4 `@theme` tokens, self-hosted fonts). The scope is six sections: hero with browser mockup, stats bar, feature grid, tech stack badges, and footer -- plus responsive design at three breakpoints. All content is static HTML rendered by Astro components with Tailwind utility classes; no JavaScript runtime is needed.

The key technical decisions are: (1) each section is its own `.astro` component in `src/components/sections/` composed into `index.astro`, (2) icons are inline SVGs using Astro's native SVG import (stable since 5.7, project has 5.17.2), (3) the browser mockup "ScreenshotFrame" is a pure-CSS/Tailwind component with three colored dots in a title bar, (4) responsive layout uses Tailwind's default breakpoints (`md:` at 768px, `lg:` at 1024px, `xl:` at 1280px) with mobile-first approach, and (5) anchor links for navigation use bare `#section-id` fragments (no base path prefix needed for hash navigation).

The main risk areas are: getting responsive grid behavior correct across three breakpoints without over-engineering, ensuring the ScreenshotFrame component looks polished with a placeholder gradient (real screenshots come later), and maintaining the design token discipline (only `primary-*` and `surface-*` colors, `font-sans` and `font-display` families).

**Primary recommendation:** Build each section as a standalone Astro component with typed Props, compose them sequentially in `index.astro`, use Tailwind responsive grid classes for layout (no custom CSS breakpoints), and use Astro's native SVG import for all icons. Avoid `<style>` blocks entirely -- use utility classes in markup per Tailwind team recommendation.

## Standard Stack

### Core (already installed from Phase 20)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `astro` | 5.17.2 | Static site framework, component rendering | Installed in Phase 20; SVG imports stable since 5.7 |
| `tailwindcss` | 4.1.18 | Utility-first CSS, responsive grid, design tokens | Installed in Phase 20; `@theme` tokens already defined |
| `@tailwindcss/vite` | 4.1.18 | Vite plugin for Tailwind v4 | Installed in Phase 20 |

### Supporting (no new dependencies)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Astro SVG import (built-in) | -- | Inline SVG icons as components | Import `.svg` files directly; pass `width`, `height`, `fill` as props |
| Tailwind responsive prefixes (built-in) | -- | Breakpoint-specific styles | `md:` (768px), `lg:` (1024px), `xl:` (1280px) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native SVG imports | `astro-icon` package | Extra dependency for something Astro handles natively since 5.7. Not worth it for ~10 icons. |
| Native SVG imports | `lucide-astro` icon library | Adds a dependency and 800+ icons when we need ~15. Inline SVGs give full control. |
| Inline SVG files | `node-html-parser` + dynamic import pattern | Over-engineered for a small number of icons. Native SVG import is simpler. |
| Utility classes in markup | `<style>` blocks with `@reference` | Tailwind team recommends against `<style>` blocks; each one runs Tailwind separately, slowing builds. |

**Installation:** No new packages needed. Phase 20's dependencies cover everything.

## Architecture Patterns

### Recommended Project Structure

```
site/src/
├── components/
│   ├── sections/
│   │   ├── Hero.astro          # CONT-01: headline, subheadline, CTA, ScreenshotFrame
│   │   ├── Stats.astro         # CONT-02: metrics bar (LOC, tests, coverage, platforms)
│   │   ├── Features.astro      # CONT-03: 6-8 feature cards in responsive grid
│   │   ├── TechStack.astro     # CONT-04: technology badges with role labels
│   │   └── Footer.astro        # CONT-09: GitHub link, personal site, contact
│   └── ui/
│       └── ScreenshotFrame.astro  # DSGN-04: browser mockup with placeholder gradient
├── icons/
│   ├── search.svg              # Discovery category
│   ├── brain.svg               # Intelligence category
│   ├── layout.svg              # Dashboard category
│   ├── zap.svg                 # Automation category
│   ├── github.svg              # GitHub CTA + footer
│   └── ...                     # Other section icons
├── layouts/
│   └── BaseLayout.astro        # (from Phase 20)
├── pages/
│   └── index.astro             # Composes all sections
└── styles/
    └── global.css              # (from Phase 20) @theme tokens
```

### Pattern 1: Section Component with Typed Props

**What:** Each content section is a self-contained Astro component with its own data, accepting minimal config props if needed.
**When to use:** Every section in Phase 21.
**Example:**

```astro
---
// src/components/sections/Stats.astro

interface Props {
  class?: string;
}

const { class: className } = Astro.props;

const stats = [
  { value: "18K+", label: "Lines of Code" },
  { value: "581", label: "Tests" },
  { value: "80%+", label: "Coverage" },
  { value: "3", label: "Platforms" },
];
---

<section id="stats" class:list={["py-12 bg-primary-900 text-white", className]}>
  <div class="max-w-6xl mx-auto px-4">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
      {stats.map((stat) => (
        <div>
          <div class="font-display text-4xl font-bold">{stat.value}</div>
          <div class="mt-1 text-sm text-primary-200 uppercase tracking-wider">{stat.label}</div>
        </div>
      ))}
    </div>
  </div>
</section>
```

### Pattern 2: Page Composition (Section Stacking)

**What:** The index page imports all section components and stacks them vertically.
**When to use:** `index.astro` -- the single page.
**Example:**

```astro
---
// src/pages/index.astro
import BaseLayout from "../layouts/BaseLayout.astro";
import Hero from "../components/sections/Hero.astro";
import Stats from "../components/sections/Stats.astro";
import Features from "../components/sections/Features.astro";
import TechStack from "../components/sections/TechStack.astro";
import Footer from "../components/sections/Footer.astro";
---

<BaseLayout
  title="JobFlow — Job Search Automation"
  description="Self-hosted pipeline that scrapes job boards, scores matches against your profile, and automates applications. 18K LOC, 581 tests, 3 platforms."
>
  <Hero />
  <Stats />
  <Features />
  <TechStack />
  <Footer />
</BaseLayout>
```

### Pattern 3: Native SVG Icon Import

**What:** Import `.svg` files directly as Astro components (stable since Astro 5.7).
**When to use:** All icons in feature cards, tech badges, footer links.
**Example:**

```astro
---
// In any Astro component
import SearchIcon from "../../icons/search.svg";
import GithubIcon from "../../icons/github.svg";
---

<SearchIcon width="24" height="24" class="text-primary-500" />
<GithubIcon width="20" height="20" fill="currentColor" />
```

**Key behavior:** Astro inlines the SVG into the HTML output. Props like `width`, `height`, `fill`, `stroke`, and `class` override the original SVG attributes. Zero JavaScript runtime.

**Important:** SVG files must use `currentColor` for fill/stroke to pick up the parent element's text color via Tailwind classes.

### Pattern 4: ScreenshotFrame (Browser Mockup)

**What:** A reusable browser window chrome component with title bar dots, optional URL text, and a slot for content.
**When to use:** Hero section dashboard screenshot placeholder (DSGN-04).
**Example:**

```astro
---
// src/components/ui/ScreenshotFrame.astro
interface Props {
  url?: string;
  class?: string;
}

const { url = "localhost:8000/dashboard", class: className } = Astro.props;
---

<div class:list={["rounded-lg overflow-hidden shadow-2xl border border-surface-200", className]}>
  <!-- Title bar -->
  <div class="flex items-center gap-2 px-4 py-3 bg-surface-100 border-b border-surface-200">
    <div class="flex gap-1.5">
      <span class="w-3 h-3 rounded-full bg-red-400"></span>
      <span class="w-3 h-3 rounded-full bg-yellow-400"></span>
      <span class="w-3 h-3 rounded-full bg-green-400"></span>
    </div>
    <div class="flex-1 text-center">
      <span class="text-xs text-surface-400 font-mono">{url}</span>
    </div>
  </div>
  <!-- Content area -->
  <div class="aspect-video bg-gradient-to-br from-primary-500/20 to-primary-700/20">
    <slot />
  </div>
</div>
```

**Note:** The `red-400`, `yellow-400`, `green-400` colors for the traffic light dots are Tailwind v4 defaults that are NOT overridden by the `@theme` block (the theme only defines `primary-*` and `surface-*`). This means the default Tailwind color palette values for `red`, `yellow`, `green` are still available since they were not reset. This is correct behavior -- `@theme` in Tailwind v4 only overrides the namespaces you define; other namespaces keep their defaults.

### Pattern 5: Responsive Grid for Feature Cards

**What:** Mobile-first grid that starts at 1 column, expands to 2 at `md`, and 3 at `lg`.
**When to use:** Feature grid (CONT-03) with 6-8 cards.
**Example:**

```astro
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {features.map((feature) => (
    <div class="p-6 rounded-xl bg-white border border-surface-200">
      <div class="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center text-primary-600">
        <!-- Icon renders here -->
      </div>
      <h3 class="mt-4 font-display text-lg font-semibold text-surface-900">{feature.title}</h3>
      <p class="mt-2 text-sm text-surface-600 leading-relaxed">{feature.description}</p>
    </div>
  ))}
</div>
```

### Pattern 6: Anchor Link Navigation (Single Page)

**What:** Sections have `id` attributes; navigation uses bare hash fragments.
**When to use:** Any in-page link (hero CTA linking to features, nav menu in future phases).
**Example:**

```html
<!-- Hash links do NOT need import.meta.env.BASE_URL prefix -->
<a href="#features">See Features</a>
<a href="#tech-stack">Tech Stack</a>

<!-- External links DO need full URLs -->
<a href="https://github.com/patrykgolabek/jobs" target="_blank" rel="noopener noreferrer">
  View on GitHub
</a>
```

**Key insight:** Hash fragments (`#id`) are handled entirely by the browser and are not affected by Astro's `base` path configuration. The `base` prefix is only needed for page-to-page navigation and asset URLs, not for same-page anchor navigation.

### Anti-Patterns to Avoid

- **Using `<style>` blocks in section components:** Each `<style>` block forces Tailwind to run again. Use utility classes in markup. If you absolutely must scope CSS, use `var(--color-primary-500)` directly, not `@apply`.
- **Using `@apply` without `@reference`:** Will fail with "Cannot apply unknown utility class" in Astro `<style>` blocks. Simply avoid `@apply` entirely.
- **Creating a custom breakpoint system:** The default Tailwind breakpoints (`md: 768px`, `lg: 1024px`, `xl: 1280px`) map perfectly to the required test widths (375px=mobile/default, 768px=tablet/`md:`, 1440px=desktop/`xl:` and above). No custom breakpoints needed.
- **Prefixing anchor links with `import.meta.env.BASE_URL`:** Hash fragments are client-side; `#features` works correctly regardless of base path.
- **Installing icon libraries:** For 10-15 simple icons, native SVG import is simpler and has zero dependencies.
- **Hardcoding GitHub URLs without `target="_blank"`:** External links should include `target="_blank" rel="noopener noreferrer"` for security and UX.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser mockup frame | Complex CSS with pseudo-elements | Simple Tailwind flexbox with colored dots + rounded corners | 15 lines of HTML, looks professional, no edge cases |
| Icon system | Dynamic import + parse pipeline | Astro native SVG import (`import Icon from "./icon.svg"`) | Built into Astro 5.7+, zero-config, type-safe |
| Responsive grid | Custom media queries, CSS grid from scratch | Tailwind's `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | Battle-tested, mobile-first, consistent spacing |
| Stats counter animation | Custom JS counter library | Static numbers (animation is Phase 24 scope) | Phase 21 focuses on content layout, not animation |
| Color/spacing system | Custom CSS variables | Tailwind's `@theme` tokens (already defined in Phase 20) | Consistent, responsive, no duplication |

**Key insight:** Phase 21 is about content and layout, not interactivity. Every component should be pure HTML rendered by Astro with Tailwind utility classes. Animations (PLSH-02) and smooth scroll (PLSH-03) are Phase 24 scope.

## Common Pitfalls

### Pitfall 1: Tailwind Default Colors Lost After @theme Override

**What goes wrong:** Using `bg-red-400` for the browser mockup dots produces no color because the dev assumes `@theme` overrides wipe all default colors.
**Why it happens:** Confusion about `@theme` scoping. Tailwind v4's `@theme` only overrides the namespaces you explicitly define.
**How to avoid:** The project's `@theme` block defines `--color-primary-*` and `--color-surface-*` only. This means ALL other default Tailwind colors (`red`, `yellow`, `green`, `blue`, `slate`, etc.) remain available. Using `bg-red-400` for the mockup dots works fine.
**Warning signs:** Colors like `bg-red-400` not rendering. Check if the namespace was explicitly overridden in `@theme`.
**Confidence:** HIGH -- verified via Tailwind v4 theme documentation.

### Pitfall 2: ScreenshotFrame Aspect Ratio Breaks on Mobile

**What goes wrong:** The browser mockup content area has a fixed `height` that overflows or looks squished on narrow screens.
**Why it happens:** Using fixed pixel heights instead of responsive sizing.
**How to avoid:** Use `aspect-video` (16:9) on the content area. This scales proportionally with the container width. On mobile, the frame will be narrower but maintain proportions.
**Warning signs:** Horizontal scrollbar appears at 375px width; mockup looks distorted.

### Pitfall 3: Feature Grid Cards Uneven Heights

**What goes wrong:** Cards in the feature grid have varying heights because descriptions are different lengths, creating a ragged bottom edge.
**Why it happens:** CSS Grid with `auto` row sizing creates rows that match the tallest item, but Flexbox doesn't.
**How to avoid:** Use CSS Grid (`grid grid-cols-*`), not Flexbox, for the feature card layout. Grid automatically creates equal-height rows. If you want each card to fill its grid cell vertically, add `h-full` or let grid handle it.
**Warning signs:** Cards in the same row have different heights; visual misalignment.

### Pitfall 4: Text Overflow on Mobile Stats Bar

**What goes wrong:** Long labels like "Lines of Code" wrap awkwardly or overflow at 375px width with 4 columns.
**Why it happens:** Four columns at 375px means each column is ~80px wide -- too narrow for labels.
**How to avoid:** Use `grid-cols-2 md:grid-cols-4` so mobile shows a 2x2 grid and tablet/desktop shows a single row.
**Warning signs:** Text truncation, overlapping text, or horizontal scroll at 375px.

### Pitfall 5: GitHub CTA Link Missing Repository Path

**What goes wrong:** The "View on GitHub" button links to `https://github.com/` or a wrong repo.
**Why it happens:** Placeholder URL left in during development.
**How to avoid:** Define the GitHub URL as a constant at the top of the hero section or in a shared constants file. Verify it links to the actual repository.
**Warning signs:** Clicking the CTA goes to the wrong page or 404s.

### Pitfall 6: SVG Icons Not Picking Up Color Classes

**What goes wrong:** Adding `class="text-primary-500"` to an SVG icon component has no effect on the icon color.
**Why it happens:** The SVG file has hardcoded `fill` or `stroke` values (e.g., `fill="#000000"`) instead of `currentColor`.
**How to avoid:** Ensure SVG source files use `fill="currentColor"` and/or `stroke="currentColor"`. Alternatively, pass `fill="currentColor"` as a prop to the SVG component, which overrides the file's attribute.
**Warning signs:** Icons appear black or have their original color regardless of Tailwind text color classes.

### Pitfall 7: Footer Links Missing rel="noopener noreferrer"

**What goes wrong:** External links to GitHub and personal site open without security attributes.
**Why it happens:** Forgetting `rel` attribute on `target="_blank"` links.
**How to avoid:** Always pair `target="_blank"` with `rel="noopener noreferrer"` on external links.
**Warning signs:** Browser security warnings or penalized Lighthouse score.

## Code Examples

### Complete ScreenshotFrame Component

```astro
---
// src/components/ui/ScreenshotFrame.astro
// Source: Browser mockup pattern from Tailwind CSS community + DevDojo
interface Props {
  url?: string;
  class?: string;
}

const { url = "localhost:8000/dashboard", class: className } = Astro.props;
---

<div class:list={["rounded-lg overflow-hidden shadow-2xl border border-surface-200", className]}>
  <div class="flex items-center gap-2 px-4 py-3 bg-surface-100 border-b border-surface-200">
    <div class="flex gap-1.5">
      <span class="w-3 h-3 rounded-full bg-red-400"></span>
      <span class="w-3 h-3 rounded-full bg-yellow-400"></span>
      <span class="w-3 h-3 rounded-full bg-green-400"></span>
    </div>
    <div class="flex-1 text-center">
      <span class="text-xs text-surface-400 font-mono">{url}</span>
    </div>
  </div>
  <div class="aspect-video bg-gradient-to-br from-primary-600/10 via-primary-400/20 to-primary-700/10">
    <slot />
  </div>
</div>
```

### Feature Card Data Structure

```astro
---
// Data array for the feature grid (CONT-03)
// Categories: Discovery, Intelligence, Dashboard, Automation
const features = [
  {
    category: "Discovery",
    icon: "search",
    title: "Multi-Platform Scraping",
    description: "Scrapes Indeed, Dice, and RemoteOK with Playwright and stealth automation. Handles login, pagination, and deduplication.",
  },
  {
    category: "Discovery",
    icon: "filter",
    title: "Smart Filtering",
    description: "Configurable search queries with location, salary range, and keyword filters. YAML-driven, no code changes needed.",
  },
  {
    category: "Intelligence",
    icon: "brain",
    title: "AI-Powered Scoring",
    description: "Claude CLI scores each job 1-5 against your candidate profile with explainable breakdowns.",
  },
  {
    category: "Intelligence",
    icon: "file-text",
    title: "Resume Tailoring",
    description: "Generates role-specific resumes via Claude with anti-fabrication validation. Never invents experience.",
  },
  {
    category: "Dashboard",
    icon: "layout",
    title: "Web Dashboard",
    description: "FastAPI + htmx real-time dashboard with Kanban board, analytics, and search management.",
  },
  {
    category: "Dashboard",
    icon: "bar-chart",
    title: "Analytics & Insights",
    description: "Score distribution, platform breakdown, salary ranges, and application funnel metrics.",
  },
  {
    category: "Automation",
    icon: "zap",
    title: "One-Click Apply",
    description: "Background apply engine with SSE progress streaming and human-in-the-loop confirmation gates.",
  },
  {
    category: "Automation",
    icon: "shield",
    title: "Safety First",
    description: "Never auto-submits without approval. CAPTCHA detection, credential gating, and screenshot debugging.",
  },
];
---
```

### Tech Stack Badge Pattern

```astro
---
// Technology badges for CONT-04
const technologies = [
  { name: "Python 3.14", role: "Runtime", icon: "python" },
  { name: "Playwright", role: "Automation", icon: "playwright" },
  { name: "FastAPI", role: "Backend", icon: "fastapi" },
  { name: "SQLite", role: "Database", icon: "database" },
  { name: "htmx", role: "Frontend", icon: "htmx" },
  { name: "Claude CLI", role: "AI Engine", icon: "brain" },
];
---

<section id="tech-stack" class="py-20 bg-surface-50">
  <div class="max-w-6xl mx-auto px-4 text-center">
    <h2 class="font-display text-3xl font-bold text-surface-900">Built With</h2>
    <p class="mt-3 text-surface-600">The tools that power the pipeline</p>
    <div class="mt-12 flex flex-wrap justify-center gap-6">
      {technologies.map((tech) => (
        <div class="flex flex-col items-center gap-2 px-6 py-4 rounded-xl bg-white border border-surface-200 shadow-sm">
          <div class="w-12 h-12 rounded-lg bg-primary-50 flex items-center justify-center text-primary-600">
            <!-- SVG icon here -->
          </div>
          <span class="font-display font-semibold text-surface-900">{tech.name}</span>
          <span class="text-xs text-surface-500 uppercase tracking-wider">{tech.role}</span>
        </div>
      ))}
    </div>
  </div>
</section>
```

### Responsive Layout Verification Pattern

The three required breakpoints map to Tailwind defaults:

| Required Test Width | Tailwind Strategy | Approach |
|-------------------|------------------|----------|
| 375px (mobile) | Default (no prefix) | Single column, stacked layout |
| 768px (tablet) | `md:` prefix | 2-column grids, side-by-side content |
| 1440px (desktop) | `xl:` or `lg:` prefix | 3+ column grids, max-width containers |

```html
<!-- Example: hero section responsive layout -->
<section class="py-16 md:py-24 lg:py-32">
  <div class="max-w-6xl mx-auto px-4 md:px-8">
    <!-- Content stacks on mobile, flexes on tablet+ -->
    <div class="flex flex-col lg:flex-row lg:items-center lg:gap-12">
      <div class="lg:w-1/2">
        <!-- Text content -->
      </div>
      <div class="mt-8 lg:mt-0 lg:w-1/2">
        <!-- ScreenshotFrame -->
      </div>
    </div>
  </div>
</section>
```

### Complete Footer Pattern

```astro
---
// src/components/sections/Footer.astro (CONT-09)
import GithubIcon from "../../icons/github.svg";

const currentYear = new Date().getFullYear();
const links = {
  github: "https://github.com/patrykgolabek/jobs",
  personalSite: "https://patrykgolabek.dev",
};
---

<footer class="py-12 bg-surface-900 text-surface-300">
  <div class="max-w-6xl mx-auto px-4">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
      <div>
        <span class="font-display text-lg font-semibold text-white">JobFlow</span>
        <p class="mt-1 text-sm text-surface-400">From discovery to application in one tool.</p>
      </div>
      <div class="flex items-center gap-6">
        <a
          href={links.github}
          target="_blank"
          rel="noopener noreferrer"
          class="text-surface-400 hover:text-white transition-colors"
        >
          <GithubIcon width="20" height="20" fill="currentColor" />
          <span class="sr-only">GitHub</span>
        </a>
        <a
          href={links.personalSite}
          target="_blank"
          rel="noopener noreferrer"
          class="text-sm text-surface-400 hover:text-white transition-colors"
        >
          patrykgolabek.dev
        </a>
      </div>
    </div>
    <div class="mt-8 pt-8 border-t border-surface-700 text-center text-sm text-surface-500">
      &copy; {currentYear} Patryk Golabek. All rights reserved.
    </div>
  </div>
</footer>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `experimental: { svg: true }` flag | Native SVG imports (no flag needed) | Astro 5.7 (April 2025) | Remove experimental flag; `.svg` files import as components by default |
| `astro-icon` package for inline SVGs | Native SVG imports | Astro 5.7 (April 2025) | Extra dependency no longer needed for basic inline SVGs |
| `tailwind.config.js` screens | `@theme { --breakpoint-* }` in CSS | Tailwind v4 (Jan 2025) | Breakpoints defined in CSS, not JS config |
| Fixed-height containers | `aspect-video` / `aspect-square` utilities | Tailwind v3.0+ (stable in v4) | Intrinsic aspect ratios without custom CSS |
| `@apply` in component styles | Utility classes in markup | Tailwind v4 recommendation | Avoids `@reference` requirement, improves build perf |

**Deprecated/outdated:**
- `experimental: { svg: true }` in `astro.config.mjs`: Must be removed if present; SVG import is stable since 5.7
- `@astrojs/tailwind` integration: Replaced by `@tailwindcss/vite` (already handled in Phase 20)
- `<ViewTransitions />` component: Renamed to `<ClientRouter />` (already handled in Phase 20)

## Open Questions

1. **Exact GitHub Repository URL**
   - What we know: The personal site is `patrykgolabek.dev`, GitHub username appears to be `patrykgolabek`, and the repo is in `/Users/patrykattc/work/jobs/`
   - What's unclear: The exact GitHub repo URL (could be `patrykgolabek/jobs` or a different name)
   - Recommendation: Use `https://github.com/patrykgolabek/jobs` as default. The planner should use a constant that can be updated easily.

2. **SVG Icon Source Files**
   - What we know: Need ~10-15 simple icons for features (search, brain, layout, zap, shield, etc.), tech logos (Python, Playwright), and UI elements (GitHub, external link)
   - What's unclear: Where to source the SVG files from
   - Recommendation: Create simple, minimal SVG icons by hand or derive from open-source icon sets (Lucide, Heroicons, Feather Icons are MIT-licensed). For tech logos (Python, FastAPI), use simplified single-color versions. Each SVG should use `currentColor` for fill/stroke.

3. **Real Dashboard Screenshots**
   - What we know: STATE.md notes "Screenshot capture workflow not specified" as a blocker
   - What's unclear: When real screenshots will be available
   - Recommendation: Phase 21 uses a placeholder gradient inside ScreenshotFrame. This is explicitly acceptable -- the requirements say "placeholder screenshot" and DSGN-04 says "placeholder gradient content". Real screenshots are a future enhancement (CONT-10 in future requirements).

4. **Feature Card Count and Content**
   - What we know: CONT-03 specifies "6-8 cards covering Discovery, Intelligence, Dashboard, and Automation categories"
   - What's unclear: Exact feature titles and descriptions
   - Recommendation: Use 8 cards (2 per category) for visual balance in the 2x4 or 3-column grid. The code examples section above provides suggested content based on the actual project features.

## Sources

### Primary (HIGH confidence)
- [Astro Components Documentation](https://docs.astro.build/en/basics/astro-components/) - Component structure, Props interface, slots, composition patterns verified
- [Astro Experimental SVG (now stable)](https://docs.astro.build/en/reference/experimental-flags/svg/) - SVG import API, props, stable since 5.7 verified
- [Tailwind CSS v4 Responsive Design](https://tailwindcss.com/docs/responsive-design) - Default breakpoints (sm/md/lg/xl/2xl), mobile-first approach, `@theme` customization verified
- [Tailwind CSS v4 Grid Template Columns](https://tailwindcss.com/docs/grid-template-columns) - `grid-cols-*` utilities, responsive grid patterns verified
- [Tailwind CSS v4 Compatibility (style blocks)](https://tailwindcss.com/docs/compatibility) - `@reference` directive, recommendation to avoid `<style>` blocks, CSS variables alternative verified
- [Tailwind CSS v4 Customizing Screens](https://tailwindcss.com/docs/screens) - `--breakpoint-*` theme variables, default values in rem verified

### Secondary (MEDIUM confidence)
- [DevDojo: Creating Browser Mockups in TailwindCSS](https://devdojo.com/post/tnylea/creating-browser-mockups-in-tailwindcss) - Browser mockup pattern with colored dots, title bar, content area
- [Astro 5.7 Blog Post (SVG stabilization)](https://astro.build/blog/astro-570/) - Confirmation that SVG import moved from experimental to stable
- [Using SVGs as Astro Components](https://ellodave.dev/blog/article/using-svgs-as-astro-components-and-inline-css/) - Alternative SVG pattern (pre-native support); confirms native approach is simpler

### Tertiary (LOW confidence)
- None. All findings verified with primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; all libraries verified installed at exact versions (Astro 5.17.2, Tailwind 4.1.18)
- Architecture: HIGH - Component composition patterns verified via Astro official docs; responsive grid patterns verified via Tailwind official docs
- Pitfalls: HIGH - `@theme` scoping behavior verified in Tailwind v4 docs; `<style>` block limitations verified in compatibility docs; responsive grid patterns are well-documented
- SVG imports: HIGH - Native SVG import stable since Astro 5.7; project has 5.17.2

**Research date:** 2026-02-13
**Valid until:** 2026-03-13 (30 days -- stable ecosystem, no breaking changes expected)
