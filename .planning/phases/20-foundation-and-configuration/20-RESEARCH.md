# Phase 20: Foundation and Configuration - Research

**Researched:** 2026-02-13
**Domain:** Astro static site scaffolding, Tailwind CSS v4 theming, self-hosted fonts, SEO meta tags
**Confidence:** HIGH

## Summary

Phase 20 establishes the `/site` Astro project that all subsequent showcase phases build on. The core stack is Astro 5 (stable, latest ~5.16.x) with Tailwind CSS v4 via `@tailwindcss/vite`, Fontsource variable fonts (Inter + DM Sans), and a BaseLayout with OpenGraph/Twitter Card meta tags.

The Astro + Tailwind v4 integration is well-documented and straightforward: install `tailwindcss` + `@tailwindcss/vite`, add the Vite plugin to `astro.config.mjs`, create a global CSS file with `@import "tailwindcss"` and a `@theme` block for design tokens. Fonts are self-hosted via `@fontsource-variable/*` packages imported in the layout. The `ClientRouter` component (renamed from `ViewTransitions`) enables SPA-like transitions.

The main pitfall areas are: (1) Tailwind v4 `<style>` blocks in `.astro` components cannot access `@theme` variables without a `@reference` import -- the recommendation is to use utility classes in markup and CSS variables in style blocks, avoiding `@apply`; (2) the `base` path must be consistently used for all internal links via `import.meta.env.BASE_URL`; (3) OpenGraph images require absolute URLs constructed with `new URL(path, Astro.site)`.

**Primary recommendation:** Use `npm create astro@latest -- --template minimal` to scaffold, then manually add Tailwind v4 via `@tailwindcss/vite` plugin and Fontsource font imports. Keep all design tokens in a single `global.css` `@theme` block. Build the BaseLayout to accept SEO props and construct absolute URLs from `Astro.site`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `astro` | ^5.16 | Static site framework | Official stable release; v6 is beta only |
| `tailwindcss` | ^4.1 | Utility-first CSS | v4 ships OKLCH colors, CSS-first config, `@theme` |
| `@tailwindcss/vite` | ^4.1 | Vite plugin for Tailwind v4 | Official Tailwind-recommended integration for Vite-based frameworks (replaces `@astrojs/tailwind`) |
| `@fontsource-variable/inter` | ^5.2 | Self-hosted Inter variable font | Body font; supports weights 100-900, optical sizing |
| `@fontsource-variable/dm-sans` | ^5.2 | Self-hosted DM Sans variable font | Display font; supports weights 100-900, optical sizing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `astro:transitions` (built-in) | — | Client-side routing + view transitions | Import `ClientRouter` in BaseLayout `<head>` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fontsource packages | Astro experimental fonts API | Experimental flag, API may change before stable. Fontsource is proven and stable. |
| `@tailwindcss/vite` | `@astrojs/tailwind` integration | `@astrojs/tailwind` is deprecated for Tailwind v4. Must use Vite plugin directly. |
| Astro 5 stable | Astro 6 beta | v6 has redesigned dev server and perf improvements but is beta-only (6.0-beta-6). Not suitable for production. |
| Manual OG meta tags | `astro-seo` package | Extra dependency for something achievable with 10 lines of HTML meta tags. Not worth it for a single-page site. |

**Installation:**
```bash
cd site
npm create astro@latest . -- --template minimal --no-install
npm install tailwindcss @tailwindcss/vite @fontsource-variable/inter @fontsource-variable/dm-sans
```

## Architecture Patterns

### Recommended Project Structure

```
site/
├── astro.config.mjs          # Astro config (base, site, trailingSlash, vite plugins)
├── package.json
├── tsconfig.json
├── public/
│   └── og-image.png           # OG image (1200x630, static asset)
└── src/
    ├── layouts/
    │   └── BaseLayout.astro   # HTML shell, meta tags, fonts, global CSS, ClientRouter
    ├── pages/
    │   └── index.astro        # Single page (imports BaseLayout)
    └── styles/
        └── global.css         # @import "tailwindcss" + @theme design tokens + font imports
```

### Pattern 1: Astro Config for GitHub Pages Subpath

**What:** Configure `base`, `site`, and `trailingSlash` for `/jobs/` deployment.
**When to use:** Always -- this is the foundation config.
**Example:**

```javascript
// astro.config.mjs
// Source: https://docs.astro.build/en/guides/deploy/github/
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://patrykgolabek.github.io",
  base: "/jobs",
  trailingSlash: "always",
  vite: {
    plugins: [tailwindcss()],
  },
});
```

**Key behavior:** With `trailingSlash: 'always'` and `base: '/jobs'`, `import.meta.env.BASE_URL` returns `"/jobs/"` (trailing slash included). All internal links and asset references must use this prefix.

### Pattern 2: Global CSS with Tailwind v4 @theme Design Tokens

**What:** Single CSS file that imports Tailwind, defines the color palette, and registers font families.
**When to use:** Always -- Tailwind v4 replaces `tailwind.config.js` with CSS-first `@theme`.
**Example:**

```css
/* src/styles/global.css */
/* Source: https://tailwindcss.com/docs/installation/framework-guides/astro */
@import "tailwindcss";

@theme {
  /* Professional blues palette (distinct from personal site orange/teal) */
  --color-primary-50: oklch(0.97 0.014 254.604);
  --color-primary-100: oklch(0.932 0.032 255.585);
  --color-primary-200: oklch(0.882 0.059 254.128);
  --color-primary-300: oklch(0.809 0.105 251.813);
  --color-primary-400: oklch(0.707 0.165 254.624);
  --color-primary-500: oklch(0.623 0.214 259.815);
  --color-primary-600: oklch(0.546 0.245 262.881);
  --color-primary-700: oklch(0.488 0.243 264.376);
  --color-primary-800: oklch(0.424 0.199 265.638);
  --color-primary-900: oklch(0.379 0.146 265.522);
  --color-primary-950: oklch(0.282 0.091 267.935);

  /* Gray palette for text, borders, backgrounds */
  --color-surface-50: oklch(0.984 0.003 247.858);
  --color-surface-100: oklch(0.968 0.007 247.896);
  --color-surface-200: oklch(0.929 0.013 255.508);
  --color-surface-300: oklch(0.869 0.022 252.894);
  --color-surface-400: oklch(0.704 0.04 256.788);
  --color-surface-500: oklch(0.554 0.046 257.417);
  --color-surface-600: oklch(0.446 0.043 257.281);
  --color-surface-700: oklch(0.372 0.044 257.287);
  --color-surface-800: oklch(0.279 0.041 260.031);
  --color-surface-900: oklch(0.208 0.042 265.755);
  --color-surface-950: oklch(0.129 0.042 264.695);

  /* Font families */
  --font-sans: "Inter Variable", ui-sans-serif, system-ui, sans-serif;
  --font-display: "DM Sans Variable", ui-sans-serif, system-ui, sans-serif;
}
```

### Pattern 3: BaseLayout with SEO Props

**What:** Layout component that accepts title, description, image props and outputs complete HTML with OG/Twitter meta tags.
**When to use:** Every page uses this layout.
**Example:**

```astro
---
// src/layouts/BaseLayout.astro
// Source: https://docs.astro.build/en/guides/fonts/
import "@fontsource-variable/inter";
import "@fontsource-variable/dm-sans";
import "../styles/global.css";
import { ClientRouter } from "astro:transitions";

interface Props {
  title: string;
  description: string;
  image?: string;
}

const {
  title,
  description,
  image = "/og-image.png",
} = Astro.props;

const canonicalURL = new URL(Astro.url.pathname, Astro.site);
const absoluteImageURL = new URL(image, Astro.site);
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="generator" content={Astro.generator} />

    <!-- Primary Meta Tags -->
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonicalURL} />

    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:url" content={canonicalURL} />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content={absoluteImageURL} />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:url" content={canonicalURL} />
    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />
    <meta name="twitter:image" content={absoluteImageURL} />

    <ClientRouter />
  </head>
  <body class="bg-surface-50 text-surface-900 font-sans antialiased">
    <slot />
  </body>
</html>
```

### Pattern 4: Font Import in Layout

**What:** Import Fontsource variable packages in the layout frontmatter, then reference via `@theme` font families.
**When to use:** Fonts imported once in BaseLayout, available everywhere.
**Example:**

```astro
---
// In BaseLayout.astro frontmatter
import "@fontsource-variable/inter";       // Registers @font-face for Inter Variable
import "@fontsource-variable/dm-sans";     // Registers @font-face for DM Sans Variable
---
```

Then in CSS / Tailwind:
- Body text: `class="font-sans"` (uses `--font-sans` = Inter Variable)
- Headings: `class="font-display"` (uses `--font-display` = DM Sans Variable)

### Anti-Patterns to Avoid

- **Using `@apply` in Astro `<style>` blocks:** Tailwind v4 processes each `<style>` block separately. Without `@reference`, `@apply` fails with "Cannot apply unknown utility class". Use utility classes in markup instead.
- **Using `@astrojs/tailwind` integration:** Deprecated for Tailwind v4. Use `@tailwindcss/vite` directly in `vite.plugins`.
- **Hardcoding `/jobs/` prefix in links:** Use `import.meta.env.BASE_URL` to get the base path dynamically. Hardcoding breaks if the base ever changes.
- **Using relative image URLs in OG tags:** Social crawlers need absolute URLs. Always use `new URL(path, Astro.site)`.
- **Creating `tailwind.config.js`:** Tailwind v4 uses CSS-first configuration via `@theme`. No JS config file needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS utility framework | Custom utility CSS | Tailwind CSS v4 `@theme` | Thousands of utilities, responsive, dark mode built in |
| Font hosting/loading | Download .woff2 files manually | `@fontsource-variable/*` packages | Handles @font-face, subsetting, variable axes automatically |
| View transitions | Custom page transition JS | `ClientRouter` from `astro:transitions` | Built into Astro, handles fallbacks, works with static sites |
| Color palette generation | Manually pick 11 shades | Use Tailwind's default OKLCH blue/slate values as starting point | Perceptually uniform, tested for accessibility contrast |
| OG meta tag management | Complex meta tag component | Simple props + `new URL()` | Only 1 page, don't need a full SEO framework |

**Key insight:** This is a single-page static site. Every "don't hand-roll" decision should bias toward simplicity. No SEO libraries, no font optimization libraries, no meta tag frameworks -- just Astro primitives and Tailwind defaults with customized tokens.

## Common Pitfalls

### Pitfall 1: Tailwind v4 @theme Variables Not Available in <style> Blocks

**What goes wrong:** Using `@apply bg-primary-500` in an Astro component's `<style>` block throws "Cannot apply unknown utility class: bg-primary-500".
**Why it happens:** Tailwind v4 processes each `<style>` block as a separate CSS module. It has no knowledge of `@theme` definitions from `global.css`.
**How to avoid:** Style with utility classes in HTML markup (`class="bg-primary-500"`). If you must use `<style>`, use CSS variables (`background-color: var(--color-primary-500)`) or add `@reference "../styles/global.css"` at the top of the style block.
**Warning signs:** Build errors mentioning "unknown utility class" in `.astro` files.

### Pitfall 2: Base Path Not Applied to Links and Assets

**What goes wrong:** Internal links like `<a href="/about/">` resolve to `/about/` instead of `/jobs/about/`. Assets in `public/` don't load.
**Why it happens:** Astro's `base` config affects page routing but doesn't auto-prefix all href attributes. Only `import.meta.env.BASE_URL` provides the prefix.
**How to avoid:** For internal links, prepend `import.meta.env.BASE_URL`. For assets in `public/`, Astro's built-in asset handling respects `base` automatically. For imported assets (via `import`), Astro handles the path. For hardcoded paths in HTML, you must prefix manually.
**Warning signs:** 404 errors in browser console during `npm run dev` or `npm run preview`.

### Pitfall 3: OG Image URLs Are Relative

**What goes wrong:** Social media crawlers (Facebook, Twitter, LinkedIn) show no preview image because `og:image` contains a relative path like `/og-image.png`.
**Why it happens:** Forgetting to construct absolute URLs. Crawlers cannot resolve relative URLs without a base.
**How to avoid:** Always use `new URL(imagePath, Astro.site)` to produce fully qualified URLs like `https://patrykgolabek.github.io/jobs/og-image.png`. This requires `site` to be set in `astro.config.mjs`.
**Warning signs:** Sharing the URL on social media shows no image preview. Can test with Facebook Sharing Debugger or Twitter Card Validator.

### Pitfall 4: Missing `site` Config Breaks Absolute URL Construction

**What goes wrong:** `new URL(path, Astro.site)` throws at build time because `Astro.site` is `undefined`.
**Why it happens:** The `site` property in `astro.config.mjs` was not set.
**How to avoid:** Always set `site: "https://patrykgolabek.github.io"` in the config. This is required for OG tags, canonical URLs, and later for sitemap generation.
**Warning signs:** Build errors or runtime TypeError about undefined URL base.

### Pitfall 5: trailingSlash + base Interaction Confusion

**What goes wrong:** `import.meta.env.BASE_URL` returns `/jobs/` (with trailing slash) when `trailingSlash: 'always'`, but developer concatenates another `/` producing `//` in URLs.
**Why it happens:** The trailing slash behavior of `BASE_URL` is determined by `trailingSlash` config, not by what you write in `base`.
**How to avoid:** With `trailingSlash: 'always'`, `BASE_URL` is `/jobs/`. When building paths, don't add an extra slash: use `` `${import.meta.env.BASE_URL}page/` `` not `` `${import.meta.env.BASE_URL}/page/` ``.
**Warning signs:** Double slashes in URLs (`/jobs//page/`) visible in browser address bar or page source.

### Pitfall 6: Fontsource Import Order

**What goes wrong:** Font imports in `global.css` via `@import` don't work as expected because Tailwind's `@import "tailwindcss"` must be the first import.
**Why it happens:** Tailwind v4 requires its `@import` to come first in the file.
**How to avoid:** Import Fontsource packages in the Astro layout frontmatter (JavaScript import), not in the CSS file. The CSS file should only contain `@import "tailwindcss"` and `@theme` block. Font family names are then referenced in `@theme` via `--font-sans` and `--font-display`.
**Warning signs:** Fonts not rendering despite being installed; no `@font-face` rules in compiled CSS.

## Code Examples

### Complete astro.config.mjs

```javascript
// Source: https://docs.astro.build/en/guides/deploy/github/ + https://tailwindcss.com/docs/installation/framework-guides/astro
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://patrykgolabek.github.io",
  base: "/jobs",
  trailingSlash: "always",
  vite: {
    plugins: [tailwindcss()],
  },
});
```

### Constructing Absolute URLs for OG Tags

```astro
---
// Source: https://docs.astro.build/en/reference/configuration-reference/
const canonicalURL = new URL(Astro.url.pathname, Astro.site);
const ogImageURL = new URL("/jobs/og-image.png", Astro.site);
// Result: https://patrykgolabek.github.io/jobs/og-image.png
---
<meta property="og:url" content={canonicalURL} />
<meta property="og:image" content={ogImageURL} />
```

### Minimal Index Page Using BaseLayout

```astro
---
// src/pages/index.astro
import BaseLayout from "../layouts/BaseLayout.astro";
---

<BaseLayout
  title="JobFlow - Job Search Automation"
  description="Self-hosted pipeline that scrapes job boards, scores matches, and automates applications."
>
  <main class="max-w-4xl mx-auto px-4 py-16">
    <h1 class="font-display text-4xl font-bold text-primary-900">
      JobFlow
    </h1>
    <p class="mt-4 text-lg text-surface-600">
      From discovery to application in one tool.
    </p>
  </main>
</BaseLayout>
```

### .gitignore Additions

```gitignore
# Astro site
node_modules/
site/dist/
site/.astro/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@astrojs/tailwind` integration | `@tailwindcss/vite` Vite plugin | Tailwind v4 (Jan 2025) | `@astrojs/tailwind` is deprecated; must use Vite plugin |
| `tailwind.config.js` (JavaScript) | `@theme` block in CSS | Tailwind v4 (Jan 2025) | No JS config needed; all tokens defined in CSS |
| `<ViewTransitions />` component | `<ClientRouter />` component | Astro 5.x | Renamed; import from `astro:transitions` |
| RGB/HSL color values | OKLCH color values | Tailwind v4 (Jan 2025) | Perceptually uniform, wider gamut colors |
| `stealth_sync(page)` | `Stealth().apply_stealth_sync(page)` | playwright-stealth 2.0.1 | N/A for this phase (Python side) |

**Deprecated/outdated:**
- `@astrojs/tailwind`: Replaced by `@tailwindcss/vite` for Tailwind v4+
- `<ViewTransitions />`: Renamed to `<ClientRouter />` in current Astro 5
- `tailwind.config.js` / `tailwind.config.ts`: Replaced by CSS-first `@theme` in Tailwind v4
- Astro experimental fonts API: Still experimental as of Astro 5.7+; use Fontsource instead

## Open Questions

1. **OG Image Asset**
   - What we know: OG images should be 1200x630px, placed in `public/` folder, referenced with absolute URLs.
   - What's unclear: The actual OG image doesn't exist yet. A placeholder gradient or simple branded image is needed for Phase 20.
   - Recommendation: Create a simple placeholder `og-image.png` (solid color with text, or a gradient). Real screenshot-based OG image can be created later when dashboard screenshots are available (noted as a blocker in STATE.md).

2. **Exact GitHub Username for `site` Config**
   - What we know: The personal site is `patrykgolabek.dev`, which suggests the GitHub username.
   - What's unclear: The exact GitHub Pages URL format (could be `username.github.io` or a custom domain).
   - Recommendation: Use `https://patrykgolabek.github.io` as the `site` value. The `base: '/jobs'` handles the repository subpath. Can be updated when deploying in Phase 23.

3. **Color Palette Exact Values**
   - What we know: Must be "professional blues/grays" distinct from personal site (orange/teal) and networking-tools (dark orange).
   - What's unclear: The exact OKLCH values for a custom palette vs. using Tailwind's default blue/slate.
   - Recommendation: Start with Tailwind's built-in blue palette for `primary` and slate palette for `surface` as the baseline. These are already professional blues/grays and are perceptually optimized. Custom tuning can happen after visual review. Name them `primary-*` and `surface-*` (not `blue-*` and `slate-*`) so the semantic names survive any future palette changes.

## Sources

### Primary (HIGH confidence)
- [Astro Configuration Reference](https://docs.astro.build/en/reference/configuration-reference/) - `base`, `trailingSlash`, `site`, `vite` config verified
- [Tailwind CSS v4 Astro Installation Guide](https://tailwindcss.com/docs/installation/framework-guides/astro) - Official install steps verified
- [Tailwind CSS v4 Theme Variables](https://tailwindcss.com/docs/theme) - `@theme` syntax, color namespaces, font families verified
- [Tailwind CSS v4 Colors](https://tailwindcss.com/docs/customizing-colors) - OKLCH palette syntax, default blue/slate values verified
- [Tailwind CSS v4 Compatibility](https://tailwindcss.com/docs/compatibility) - `@reference` directive, `<style>` block limitations verified
- [Astro GitHub Pages Deployment](https://docs.astro.build/en/guides/deploy/github/) - `site` + `base` config, Actions workflow verified
- [Astro View Transitions](https://docs.astro.build/en/guides/view-transitions/) - `ClientRouter` rename from `ViewTransitions` verified
- [Astro Fonts Guide](https://docs.astro.build/en/guides/fonts/) - Fontsource import pattern verified
- [Fontsource Inter Install](https://fontsource.org/fonts/inter/install) - Package name, import, font-family value verified
- [Fontsource DM Sans Install](https://fontsource.org/fonts/dm-sans/install) - Package name, import, font-family value verified
- [@fontsource-variable/inter npm](https://www.npmjs.com/package/@fontsource-variable/inter) - Version 5.2.8, axes confirmed
- [@fontsource-variable/dm-sans npm](https://www.npmjs.com/package/@fontsource-variable/dm-sans) - Version 5.2.8, axes confirmed

### Secondary (MEDIUM confidence)
- [Astro npm versions](https://www.npmjs.com/package/astro?activeTab=versions) - Latest stable ~5.16.x confirmed
- [Tailwind CSS npm](https://www.npmjs.com/package/tailwindcss) - Latest stable 4.1.18 confirmed
- [Astro Experimental Fonts API](https://docs.astro.build/en/reference/experimental-flags/fonts/) - Experimental status confirmed, not recommended for production
- [Astro January 2026 Update](https://astro.build/blog/whats-new-january-2026/) - Astro 5.17 release noted

### Tertiary (LOW confidence)
- [Astro 6 Beta Blog](https://astro.build/blog/astro-6-beta/) - v6 beta features noted; not recommended for use

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and npm. Versions confirmed current.
- Architecture: HIGH - Project structure follows official Astro + Tailwind v4 guides. Patterns verified with multiple sources.
- Pitfalls: HIGH - `@theme`/`<style>` block issue verified in Tailwind v4 compatibility docs. Base path behavior verified in Astro config docs. OG absolute URL requirement is well-documented.

**Research date:** 2026-02-13
**Valid until:** 2026-03-13 (30 days - stable ecosystem, no major releases expected)
