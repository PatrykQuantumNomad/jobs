---
phase: 20-foundation-and-configuration
plan: 01
subsystem: ui
tags: [astro, tailwind-v4, oklch, fontsource, opengraph, twitter-card, seo]

# Dependency graph
requires: []
provides:
  - "Astro v5 project in /site with base:/jobs and trailingSlash:always"
  - "Tailwind v4 CSS-first config via @tailwindcss/vite (no tailwind.config.js)"
  - "@theme design tokens: primary blues + surface grays (OKLCH), Inter + DM Sans fonts"
  - "BaseLayout.astro with full OG/Twitter Card meta tags using absolute URLs"
  - "ClientRouter (Astro 5 view transitions) in layout head"
  - "Placeholder OG image (1200x630 primary-600 blue)"
  - "Root .gitignore updated with node_modules/, site/dist/, site/.astro/"
affects: [21-core-sections, 22-engineering-depth, 23-cicd-deployment, 24-polish-animations]

# Tech tracking
tech-stack:
  added: [astro@5.17, tailwindcss@4.1, "@tailwindcss/vite@4.1", "@fontsource-variable/inter", "@fontsource-variable/dm-sans"]
  patterns: [css-first-tailwind-v4, oklch-design-tokens, astro-client-router, fontsource-variable-fonts]

key-files:
  created:
    - site/astro.config.mjs
    - site/package.json
    - site/tsconfig.json
    - site/src/styles/global.css
    - site/src/layouts/BaseLayout.astro
    - site/src/pages/index.astro
    - site/public/og-image.png
  modified:
    - .gitignore

key-decisions:
  - "Tailwind v4 via @tailwindcss/vite (not deprecated @astrojs/tailwind)"
  - "CSS-first @theme tokens (no tailwind.config.js needed)"
  - "OKLCH color values for perceptually uniform palette"
  - "ClientRouter (Astro 5 rename of ViewTransitions)"
  - "Fontsource variable fonts (self-hosted, no Google Fonts CDN)"

patterns-established:
  - "Design tokens: @theme block in global.css with --color-primary-* and --color-surface-* naming"
  - "Font families: --font-sans (Inter) for body, --font-display (DM Sans) for headings"
  - "Layout pattern: BaseLayout.astro accepts title/description/image props, constructs absolute URLs"
  - "SEO: OG + Twitter Card meta tags in BaseLayout with absolute URLs via new URL(path, Astro.site)"

# Metrics
duration: 4min
completed: 2026-02-13
---

# Phase 20 Plan 01: Foundation and Configuration Summary

**Astro v5 project with Tailwind v4 CSS-first config, OKLCH design tokens (professional blues/grays), Inter + DM Sans self-hosted fonts, and BaseLayout with complete OG/Twitter Card SEO meta tags**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-13T20:20:27Z
- **Completed:** 2026-02-13T20:24:44Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Scaffolded Astro v5 project in `/site` with `base: "/jobs"` and `trailingSlash: "always"` for GitHub Pages deployment
- Configured Tailwind v4 via `@tailwindcss/vite` with CSS-first `@theme` design tokens (11-shade primary blues + 11-shade surface grays using OKLCH values)
- Created BaseLayout with full OpenGraph and Twitter Card meta tags producing absolute `https://patrykgolabek.github.io/jobs/` URLs
- Self-hosted Inter Variable (body) and DM Sans Variable (display) fonts via @fontsource -- no external CDN dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Astro project with Tailwind v4 and design tokens** - `b6d0a9a` (feat)
2. **Task 2: Create BaseLayout with SEO meta tags and minimal index page** - `acb4f20` (feat)

## Files Created/Modified
- `site/astro.config.mjs` - Astro config with site URL, base path, trailingSlash, Tailwind vite plugin
- `site/package.json` - Project deps: astro, tailwindcss, @tailwindcss/vite, fontsource fonts
- `site/tsconfig.json` - TypeScript config extending astro/tsconfigs/strict
- `site/src/styles/global.css` - Tailwind v4 import + @theme design tokens (primary blues, surface grays, font families)
- `site/src/layouts/BaseLayout.astro` - HTML shell with OG/Twitter meta tags, font imports, global CSS, ClientRouter
- `site/src/pages/index.astro` - Landing page using BaseLayout with placeholder content
- `site/public/og-image.png` - 1200x630 placeholder OG image (primary-600 blue)
- `.gitignore` - Added node_modules/, site/dist/, site/.astro/ entries

## Decisions Made
- Used `@tailwindcss/vite` directly instead of deprecated `@astrojs/tailwind` integration -- Tailwind v4 requires this approach
- Used CSS-first `@theme` block for design tokens -- no `tailwind.config.js` needed with Tailwind v4
- Chose OKLCH color values for perceptually uniform color palette
- Used `ClientRouter` (not `ViewTransitions`) -- renamed in Astro 5
- Self-hosted fonts via @fontsource-variable instead of Google Fonts CDN for privacy and performance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Astro scaffolder CLI prompted for git init interactively -- resolved by passing `--no-git` flag

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Foundation complete: Astro project builds successfully, all design tokens defined, BaseLayout with SEO ready
- Phase 21 (Core Sections and Responsive Design) can begin building on BaseLayout and design tokens
- All asset paths use `/jobs/` base prefix correctly

## Self-Check: PASSED

All 8 created files verified on disk. Both task commits (b6d0a9a, acb4f20) verified in git log.

---
*Phase: 20-foundation-and-configuration*
*Completed: 2026-02-13*
