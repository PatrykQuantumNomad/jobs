---
phase: 23-ci-cd-deployment-and-dark-mode
plan: 02
subsystem: ui
tags: [dark-mode, tailwind-v4, custom-variant, theme-toggle, localStorage, FOUC]

# Dependency graph
requires:
  - phase: 20-foundation-and-configuration
    provides: "Tailwind v4 @theme tokens, BaseLayout, global.css"
  - phase: 21-core-sections-and-responsive-design
    provides: "Section components with light mode classes"
  - phase: 22-engineering-depth-sections
    provides: "CodeSnippets, Timeline, QuickStart sections"
provides:
  - "@custom-variant dark directive for data-theme-based dark mode"
  - "ThemeToggle component with sun/moon icons and localStorage persistence"
  - "FOUC-preventing is:inline theme script in BaseLayout head"
  - "ClientRouter astro:after-swap theme persistence"
  - "dark: class variants on all 9 sections + ScreenshotFrame"
affects: [24-polish-and-animations]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tailwind v4 @custom-variant for dark mode via data-theme attribute"
    - "is:inline script before stylesheets to prevent FOUC"
    - "Separate astro:after-swap script for ClientRouter persistence"
    - "Sun/moon SVG toggle with hidden/dark:block visibility switching"

key-files:
  created:
    - site/src/components/ui/ThemeToggle.astro
  modified:
    - site/src/styles/global.css
    - site/src/layouts/BaseLayout.astro
    - site/src/components/ui/ScreenshotFrame.astro
    - site/src/components/sections/Hero.astro
    - site/src/components/sections/Features.astro
    - site/src/components/sections/TechStack.astro
    - site/src/components/sections/Architecture.astro
    - site/src/components/sections/CodeSnippets.astro
    - site/src/components/sections/Timeline.astro
    - site/src/components/sections/QuickStart.astro
    - site/src/components/sections/Footer.astro
    - site/src/pages/index.astro

key-decisions:
  - "data-theme attribute on html element (not class-based) for Tailwind v4 @custom-variant compatibility"
  - "Two separate scripts: is:inline for FOUC prevention, non-inline for astro:after-swap"
  - "ThemeToggle placed as fixed top-right z-50 element (always visible regardless of scroll)"

patterns-established:
  - "Dark mode color mapping: bg-white->dark:bg-surface-950, bg-surface-50->dark:bg-surface-900, text-surface-900->dark:text-surface-50"
  - "Already-dark sections (Stats, CodeSnippets, Footer) get dark:bg-surface-950 for deepened dark mode"

# Metrics
duration: 5min
completed: 2026-02-13
---

# Phase 23 Plan 02: Dark Mode Summary

**Full dark mode with @custom-variant dark directive, FOUC-preventing theme scripts, ThemeToggle with sun/moon icons, and dark: utility pairs on all 9 sections + ScreenshotFrame**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-13T22:21:18Z
- **Completed:** 2026-02-13T22:25:50Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Tailwind v4 dark mode via @custom-variant dark directive with data-theme attribute selector
- FOUC prevention with is:inline script executing before any CSS loads
- ThemeToggle component with sun/moon SVG icons, localStorage persistence, and astro:after-swap support
- All 9 section components + ScreenshotFrame have complete dark: class pairs for backgrounds, text, borders, and hover states
- Build produces 46 dark mode CSS rules targeting [data-theme=dark]

## Task Commits

Each task was committed atomically:

1. **Task 1: Dark mode infrastructure** - `a9c0070` (feat)
2. **Task 2: Dark mode classes on all sections** - `62a85b6` (feat)

## Files Created/Modified
- `site/src/styles/global.css` - Added @custom-variant dark directive between @import and @theme
- `site/src/layouts/BaseLayout.astro` - Added is:inline FOUC script, astro:after-swap script, dark body classes
- `site/src/components/ui/ThemeToggle.astro` - New: sun/moon toggle button with localStorage persistence
- `site/src/components/ui/ScreenshotFrame.astro` - Added dark: variants for border, title bar bg, URL text
- `site/src/components/sections/Hero.astro` - Added dark: variants for h1, p, "See Features" button
- `site/src/components/sections/Features.astro` - Added dark: variants for section bg, cards, icons, text
- `site/src/components/sections/TechStack.astro` - Added dark: variants for section bg, badges, icons, text
- `site/src/components/sections/Architecture.astro` - Added dark: variants for section bg, phase names, arrows
- `site/src/components/sections/CodeSnippets.astro` - Added dark:bg-surface-950 for deepened dark mode
- `site/src/components/sections/Timeline.astro` - Added dark: variants for section bg, timeline line, tags
- `site/src/components/sections/QuickStart.astro` - Added dark: variants for section bg, headings, text
- `site/src/components/sections/Footer.astro` - Added dark:bg-surface-950 for deepened dark mode
- `site/src/pages/index.astro` - Added ThemeToggle import and fixed top-right placement

## Decisions Made
- Used data-theme attribute (not .dark class) because Tailwind v4 @custom-variant requires a CSS selector approach, and data attributes are more semantic than classes for state
- Two separate theme scripts in BaseLayout: is:inline runs synchronously before paint (FOUC prevention), non-inline handles ClientRouter page swaps
- ThemeToggle uses hidden/dark:block visibility pattern for SVG icons rather than JS-toggled classes, ensuring correct icon shows immediately based on CSS

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Dark mode fully functional with system preference detection, manual toggle, and localStorage persistence
- All sections render with readable contrast in both light and dark modes
- Ready for Phase 24 (Polish and Animations) which may add transitions to the theme toggle

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 23-ci-cd-deployment-and-dark-mode*
*Completed: 2026-02-13*
