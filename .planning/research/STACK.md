# Technology Stack: GitHub Pages Showcase Site

**Project:** JobFlow -- Marketing-forward GitHub Pages showcase site
**Researched:** 2026-02-13
**Overall confidence:** HIGH

## Executive Summary

This is a static marketing site living in `/site` within the existing JobFlow repo. The stack is deliberately minimal: Astro 5 (stable) + Tailwind CSS v4 + Fontsource self-hosted fonts, deployed via `withastro/action@v5` to GitHub Pages. No SSR, no CMS, no database. The user already has two working Astro sites (patrykgolabek.dev with Astro 5.3 + GSAP + Tailwind, and networking-tools with Astro 5.6 + Starlight), so the toolchain is familiar -- the main decisions are about what to keep lightweight vs. what to carry over from the portfolio site.

Key decision: **Use CSS-only animations with a tiny IntersectionObserver script instead of GSAP.** The portfolio site uses GSAP (3.14.x, ~60KB) + ScrollTrigger for heavy particle canvas and complex timeline animations. A showcase site needs simple fade-in-on-scroll and subtle hover effects -- achievable with CSS `@keyframes` + a ~20-line `IntersectionObserver` snippet. This keeps the site at near-zero JavaScript, which is the whole point of Astro.

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Astro | 5.17.2 | Static site generator | Latest stable. Astro 6 is in beta (6.0.0-beta.11 as of Feb 2026) -- do NOT use for a production showcase. The user already runs Astro 5.3 and 5.6 on other sites, so the DX is identical. Astro 5 has everything needed: `astro:assets` image optimization, View Transitions, content collections. |
| Node.js | 22 LTS | Runtime for builds | Required by `withastro/action@v5` (default). Astro 6 will require Node 22+ anyway, so this future-proofs. |

### CSS & Styling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Tailwind CSS | 4.1.18 | Utility-first CSS | User already uses Tailwind on patrykgolabek.dev. Tailwind v4 uses CSS-first configuration (`@theme` directive in CSS) instead of `tailwind.config.js`. Installed via `@tailwindcss/vite` plugin -- the old `@astrojs/tailwind` integration is deprecated for v4. |
| `@tailwindcss/vite` | 4.1.18 | Vite plugin for Tailwind v4 | The official integration path for Astro 5.2+. Replaces the deprecated `@astrojs/tailwind` package. Added to `astro.config.mjs` under `vite.plugins`. |

**Tailwind v4 Configuration (CSS-first, no config file):**

```css
/* src/styles/global.css */
@import "tailwindcss";

@theme {
  /* Professional blues/grays palette */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-200: #bfdbfe;
  --color-primary-300: #93c5fd;
  --color-primary-400: #60a5fa;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;
  --color-primary-800: #1e40af;
  --color-primary-900: #1e3a8a;

  --color-gray-50: #f8fafc;
  --color-gray-100: #f1f5f9;
  --color-gray-200: #e2e8f0;
  --color-gray-300: #cbd5e1;
  --color-gray-400: #94a3b8;
  --color-gray-500: #64748b;
  --color-gray-600: #475569;
  --color-gray-700: #334155;
  --color-gray-800: #1e293b;
  --color-gray-900: #0f172a;
  --color-gray-950: #020617;

  /* Typography scale */
  --font-sans: "Inter Variable", "Inter", system-ui, sans-serif;
  --font-display: "DM Sans Variable", "DM Sans", system-ui, sans-serif;
}
```

**Astro config integration:**

```javascript
// astro.config.mjs
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://<username>.github.io",
  base: "/jobs",
  integrations: [sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
```

### Typography (Self-Hosted Fonts)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `@fontsource-variable/inter` | 5.2.8 | Body text (variable font) | Clean, highly legible geometric sans-serif designed for UI. Variable font means one file covers all weights (400-700). Inter pairs excellently with blue/gray palettes for professional tech products. Self-hosting eliminates Google Fonts latency and privacy concerns. |
| `@fontsource-variable/dm-sans` | 5.2.8 | Display headings (variable font) | Geometric sans-serif with slightly more character than Inter. The user already uses DM Sans on patrykgolabek.dev, so it provides brand consistency across their web presence. Use for hero headings and section titles. |

**Font pairing rationale:** Inter (body) + DM Sans (headings) is a proven tech product pairing. Both are geometric sans-serifs but DM Sans has enough visual distinction for headings. This is deliberately different from the portfolio site's DM Sans + Bricolage Grotesque to give JobFlow its own identity while sharing a font the user already favors.

**Usage:**

```astro
---
// In base layout
import "@fontsource-variable/inter";
import "@fontsource-variable/dm-sans";
---
```

### Animations

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| CSS `@keyframes` + `animation` | native | Fade/slide-in effects | Zero dependencies. CSS animations are hardware-accelerated and don't block the main thread. Sufficient for fade-in-on-scroll, slide-up, subtle hover effects. |
| `IntersectionObserver` | native browser API | Trigger animations on scroll | ~20 lines of vanilla JS in a `<script>` tag. Add `.animate-on-scroll` class to elements, observer adds `.is-visible` when they enter viewport. No library needed. |
| Astro View Transitions | built-in | Page navigation animations | Built into Astro. Import `<ViewTransitions />` in the base layout for smooth page-to-page transitions. Zero JS bundle cost (handled by browser API with Astro's polyfill). |

**Why NOT GSAP:** GSAP is 100% free now (Webflow acquisition, April 2025), so licensing isn't the issue. The issue is proportionality. GSAP core (~28KB gzipped) + ScrollTrigger (~12KB) = ~40KB of JS for a site that needs fade-in-on-scroll effects. The portfolio site justifies GSAP because it has particle canvas, complex timelines, and staggered morphing animations. A showcase site with a hero, feature grid, and screenshots does not. Keep JavaScript at near-zero -- that's Astro's entire value proposition.

**Why NOT CSS scroll-driven animations (`animation-timeline: view()`):** The spec is excellent but Firefox still doesn't support it (behind a flag as of Feb 2026). Safari just landed it in Safari 26 beta. A polyfill exists but defeats the purpose of avoiding JS. IntersectionObserver has universal browser support and is the pragmatic choice today.

**Scroll animation pattern:**

```astro
<script>
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  document.querySelectorAll(".animate-on-scroll").forEach((el) => observer.observe(el));
</script>

<style is:global>
  .animate-on-scroll {
    opacity: 0;
    transform: translateY(1.5rem);
    transition: opacity 0.6s ease-out, transform 0.6s ease-out;
  }
  .animate-on-scroll.is-visible {
    opacity: 1;
    transform: translateY(0);
  }
</style>
```

### Image Optimization

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `astro:assets` (`<Image />`) | built-in | Responsive image optimization | Built into Astro. Automatically generates WebP, sets explicit width/height (prevents CLS), lazy-loads by default. No external service needed. |
| `<Picture />` component | built-in | Multi-format responsive images | For hero and screenshot images where AVIF + WebP fallback matters. Generates `<picture>` with `<source>` for each format. |
| sharp | 0.34.5 | Image processing engine | Astro's default image processing backend. Installed automatically as a dependency. Handles WebP/AVIF conversion at build time. |

**Usage for screenshots:**

```astro
---
import { Image } from "astro:assets";
import dashboard from "../assets/screenshots/dashboard.png";
---
<Image
  src={dashboard}
  alt="JobFlow dashboard showing scored job listings"
  widths={[400, 800, 1200]}
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 600px"
  format="webp"
  quality={85}
/>
```

### SEO & Meta

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@astrojs/sitemap` | 3.7.0 | Sitemap generation | Auto-generates sitemap-index.xml at build time. Required `site` in astro.config.mjs (already set for GitHub Pages). |

### Deployment

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `withastro/action` | v5 | GitHub Actions build + deploy | Official Astro GitHub Action. Supports the `path` parameter for monorepo/subdirectory setups (critical: the site lives at `/site`, not repo root). Auto-detects package manager from lockfile. Defaults to Node 22. |
| `actions/deploy-pages` | v4 | GitHub Pages deployment | Standard GitHub Pages deployment action. Used in the deploy job after withastro/action builds. |
| `actions/checkout` | v5 | Repository checkout | Standard checkout action. |

**GitHub Actions workflow (`/.github/workflows/deploy-site.yml`):**

```yaml
name: Deploy Showcase Site to GitHub Pages
on:
  push:
    branches: [main]
    paths: ["site/**"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v5
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

**Key detail:** The `paths: ["site/**"]` filter means the workflow only triggers when files in the `/site` directory change -- it won't run on Python code changes to the main app.

### Development Tooling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| TypeScript | 5.9.3 | Type checking (optional) | Astro has built-in TypeScript support. Use `.astro` files with typed frontmatter. Not strictly required for a small static site, but prevents typos in props/data. |
| `@astrojs/check` | 0.9.6 | Astro-specific type checking | Validates `.astro` file types, catches template errors. Run with `astro check`. |

## What NOT to Add

| Library | Why Not |
|---------|---------|
| GSAP | Overkill for fade-in-on-scroll effects. Adds ~40KB JS. Use CSS animations + IntersectionObserver instead. Reserve GSAP for the portfolio site where complex timelines justify it. |
| `@astrojs/tailwind` | **Deprecated** for Tailwind v4. Use `@tailwindcss/vite` instead. The old integration is only maintained as a convenience for migration -- it adds no functionality. |
| `@astrojs/react` / `@astrojs/svelte` | No interactive components needed. A showcase site is static content: hero, features, screenshots. Astro components handle everything. Adding a UI framework adds build complexity and JS bundle size for zero benefit. |
| `@astrojs/mdx` | Not a docs site (that's what Starlight is for). Content is hardcoded in Astro components, not authored in MDX. Keep it simple. |
| Astro Content Collections | No blog, no dynamic content. The site has ~5 hardcoded pages. Content collections add abstraction overhead without benefit at this scale. |
| `astro-icon` | Icon libraries add dependencies. For a showcase site with ~10-15 icons, inline SVGs or a single sprite sheet is simpler and more performant. |
| Framer Motion / Motion.dev | React dependency. This is an Astro-only site with no React. |
| AOS (Animate On Scroll) | 5.7KB core + 23.3KB CSS for something achievable with 20 lines of vanilla JS + CSS. |
| Google Fonts CDN | Self-hosted via Fontsource is faster (no DNS lookup, no external connection) and more privacy-respecting. |
| Astro 6 beta | Currently at beta.11 (Feb 2026). Stable release is weeks away but not here yet. For a showcase site that needs to work reliably, stick with the battle-tested 5.17.x line. Upgrade path to 6.x is straightforward when it stabilizes. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | Astro 5.17 | Next.js, Remix | Astro is purpose-built for content-first static sites. No React runtime shipped to client. User already has Astro expertise. |
| CSS | Tailwind v4 | Vanilla CSS, UnoCSS | User already uses Tailwind. v4's CSS-first config is cleaner than v3. Utility classes speed up development for marketing layouts. |
| Animations | CSS + IntersectionObserver | GSAP, Motion.dev, AOS | Proportional to the task. Near-zero JS. See detailed rationale above. |
| Fonts | Fontsource (self-hosted) | Google Fonts CDN | Faster, no external requests, privacy-preserving. Standard practice for Astro sites. |
| Deployment | withastro/action@v5 | Manual build + deploy, Netlify, Vercel | Must be GitHub Pages per requirements. Official action handles everything, including the `path` parameter for subdirectory builds. |
| Font: Body | Inter | Work Sans, Source Sans Pro | Inter is the de facto standard for tech product UIs. Exceptional legibility, full variable font support. |
| Font: Display | DM Sans | Bricolage Grotesque, Space Grotesk | DM Sans is already in the user's font repertoire (portfolio site). Professional feel without being generic. Distinct enough from Inter for headings. |

## Color Palette: Professional Blues/Grays

Based on Tailwind's built-in blue and slate scales, tuned for a professional tech product:

| Token | Hex | Usage |
|-------|-----|-------|
| `primary-500` | `#3b82f6` | Primary buttons, links, accents |
| `primary-600` | `#2563eb` | Button hover, active states |
| `primary-700` | `#1d4ed8` | Dark mode primary |
| `primary-900` | `#1e3a8a` | Hero background gradient end |
| `gray-50` | `#f8fafc` | Page background (light) |
| `gray-100` | `#f1f5f9` | Card backgrounds, alternating sections |
| `gray-700` | `#334155` | Body text |
| `gray-900` | `#0f172a` | Headings, hero text |
| `gray-950` | `#020617` | Dark hero background |

**Deliberately NOT warm orange/teal** (that's the portfolio site) or **orange accent** (that's the networking-tools site). Blue/gray gives JobFlow its own professional identity separate from the user's other projects.

## Project Structure

```
/site
  astro.config.mjs
  package.json
  tsconfig.json
  src/
    layouts/
      Base.astro          # HTML shell, fonts, global CSS, ViewTransitions
    pages/
      index.astro         # Hero + feature showcase + demo + tech stack + quick start
    components/
      Hero.astro
      FeatureCard.astro
      ScreenshotShowcase.astro
      DemoVideo.astro
      TechStack.astro
      QuickStart.astro
      Footer.astro
    styles/
      global.css          # Tailwind import + @theme + custom animations
    assets/
      screenshots/        # Dashboard, scoring, apply engine screenshots
      logo.svg            # JobFlow logo
  public/
    favicon.svg
    og-image.png          # OpenGraph preview image
```

## Installation

```bash
# From repo root
cd site

# Initialize (if starting fresh)
npm create astro@latest . -- --template minimal

# Core
npm install astro@5.17.2
npm install tailwindcss@4.1.18 @tailwindcss/vite@4.1.18

# Fonts (self-hosted, variable)
npm install @fontsource-variable/inter@5.2.8
npm install @fontsource-variable/dm-sans@5.2.8

# Integrations
npm install @astrojs/sitemap@3.7.0

# Dev tooling (optional but recommended)
npm install -D typescript@5.9.3 @astrojs/check@0.9.6

# Image optimization (auto-installed by Astro, but pin if needed)
npm install sharp@0.34.5
```

**Total new dependencies: 8 packages** (3 runtime, 2 fonts, 1 integration, 2 dev). Deliberately lean.

## Sources

- [Astro GitHub Releases](https://github.com/withastro/astro/releases) -- Astro 5.17.2 confirmed as latest stable (HIGH confidence, verified via npm)
- [Astro 6 Beta Blog Post](https://astro.build/blog/astro-6-beta/) -- Beta status, not production-ready (HIGH confidence, official blog)
- [Tailwind CSS v4 Installation for Astro](https://tailwindcss.com/docs/installation/framework-guides/astro) -- Official `@tailwindcss/vite` approach, replaces `@astrojs/tailwind` (HIGH confidence, official docs)
- [@astrojs/tailwind Deprecation](https://docs.astro.build/en/guides/integrations-guide/tailwind/) -- Deprecated for v4, use Vite plugin instead (HIGH confidence, official docs)
- [Astro GitHub Pages Deployment Guide](https://docs.astro.build/en/guides/deploy/github/) -- `withastro/action@v5`, `path` parameter, `base` config (HIGH confidence, official docs)
- [withastro/action GitHub Repo](https://github.com/withastro/action) -- v5 inputs: path, node-version, package-manager, build-cmd, cache (HIGH confidence, official repo)
- [Astro Image Optimization](https://docs.astro.build/en/guides/images/) -- `<Image />`, `<Picture />`, responsive images, WebP/AVIF (HIGH confidence, official docs)
- [GSAP Free Announcement](https://webflow.com/blog/gsap-becomes-free) -- GSAP 100% free after Webflow acquisition, April 2025 (HIGH confidence, official blog)
- [CSS Scroll-Driven Animations MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations) -- `view()` function, Firefox behind flag (MEDIUM confidence, MDN)
- [Fontsource](https://fontsource.org/docs/getting-started/introduction) -- Self-hosted font packages via npm (HIGH confidence, official docs)
- npm registry: All version numbers verified via `npm view <package> version` on 2026-02-13 (HIGH confidence)
