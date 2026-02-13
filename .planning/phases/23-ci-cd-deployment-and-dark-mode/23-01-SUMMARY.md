---
phase: 23-ci-cd-deployment-and-dark-mode
plan: 01
subsystem: infra
tags: [github-actions, ci-cd, astro, sitemap, json-ld, seo, github-pages]

# Dependency graph
requires:
  - phase: 20-foundation-and-configuration
    provides: Astro project structure, BaseLayout, astro.config.mjs
provides:
  - GitHub Pages deployment workflow (deploy-site.yml)
  - Python CI path isolation (site/** ignored)
  - Sitemap generation via @astrojs/sitemap
  - JSON-LD SoftwareApplication structured data
affects: [23-02, 23-03, 24-polish-and-animations]

# Tech tracking
tech-stack:
  added: ["@astrojs/sitemap"]
  patterns: ["GitHub Actions path-based workflow isolation", "JSON-LD structured data in Astro layout"]

key-files:
  created:
    - ".github/workflows/deploy-site.yml"
  modified:
    - ".github/workflows/ci.yml"
    - "site/astro.config.mjs"
    - "site/src/layouts/BaseLayout.astro"
    - "site/package.json"
    - "site/package-lock.json"

key-decisions:
  - "Path-based workflow isolation: site/** triggers deploy, Python CI ignores site/**"
  - "Deploy workflow also triggers on .github/workflows/deploy-site.yml changes"
  - "Concurrency group 'pages' with cancel-in-progress: false for safe deploys"

patterns-established:
  - "Workflow path isolation: separate triggers for site vs Python code changes"
  - "JSON-LD in BaseLayout head: structured data on every page via layout inheritance"

# Metrics
duration: 3min
completed: 2026-02-13
---

# Phase 23 Plan 01: CI/CD and SEO Foundations Summary

**GitHub Actions deploy-to-Pages workflow with path-isolated CI, @astrojs/sitemap integration, and SoftwareApplication JSON-LD structured data**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-13T22:18:19Z
- **Completed:** 2026-02-13T22:21:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created deploy-site.yml with two-job build+deploy pipeline for GitHub Pages
- Added path-based isolation so site changes only trigger deploy, Python changes only trigger CI
- Integrated @astrojs/sitemap producing sitemap-index.xml and sitemap-0.xml on build
- Added SoftwareApplication JSON-LD structured data in BaseLayout head for SEO

## Task Commits

Each task was committed atomically:

1. **Task 1: GitHub Actions workflows and CI path isolation** - `6a9aae2` (feat)
2. **Task 2: Sitemap integration, JSON-LD, and astro.config.mjs** - `d7f9c3e` (feat)

## Files Created/Modified
- `.github/workflows/deploy-site.yml` - GitHub Pages deployment workflow with Astro build action
- `.github/workflows/ci.yml` - Added paths-ignore for site/** on push and pull_request triggers
- `site/astro.config.mjs` - Added @astrojs/sitemap import and integrations array
- `site/src/layouts/BaseLayout.astro` - Added JSON-LD SoftwareApplication schema in head
- `site/package.json` - Added @astrojs/sitemap dependency
- `site/package-lock.json` - Lock file updated with sitemap dependency tree

## Decisions Made
- Deploy workflow triggers on both `site/**` and `.github/workflows/deploy-site.yml` changes for workflow self-testing
- Concurrency group "pages" with `cancel-in-progress: false` to avoid interrupted deployments
- JSON-LD placed after Twitter Card meta tags and before ClientRouter for clean head ordering

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. GitHub Pages must be enabled in repository settings when ready to deploy (Settings > Pages > Source: GitHub Actions).

## Next Phase Readiness
- Deploy workflow ready; will auto-trigger on next push to main with site/** changes
- CI correctly ignores site-only changes
- SEO foundations (sitemap + structured data) in place for first deploy
- Ready for 23-02 (dark mode) and 23-03 (remaining deployment polish)

## Self-Check: PASSED

- FOUND: .github/workflows/deploy-site.yml
- FOUND: .github/workflows/ci.yml
- FOUND: site/astro.config.mjs
- FOUND: site/src/layouts/BaseLayout.astro
- FOUND: 23-01-SUMMARY.md
- FOUND: commit 6a9aae2 (Task 1)
- FOUND: commit d7f9c3e (Task 2)

---
*Phase: 23-ci-cd-deployment-and-dark-mode*
*Completed: 2026-02-13*
