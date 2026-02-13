# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-13)

**Core value:** From discovery to application in one tool -- reliably find relevant jobs, present them clearly, make applying frictionless.
**Current focus:** v1.3 Project Showcase Site -- GitHub Pages marketing landing page showcasing JobFlow as a portfolio centerpiece.

## Current Position

Phase: 22 -- Engineering Depth Sections COMPLETE
Plan: 22-02 COMPLETE (2/2 plans)
Status: Phase 22 complete. All engineering depth sections built and composed. Ready for Phase 23.
Last activity: 2026-02-13 -- Completed 22-02 (Timeline, QuickStart, page composition)

Progress: [██████░░░░] 60% (3/5 phases)

### v1.3 Phase Overview

| Phase | Name | Requirements | Status |
|-------|------|-------------|--------|
| 20 | Foundation and Configuration | 8 | Complete |
| 21 | Core Sections and Responsive Design | 7 | Complete |
| 22 | Engineering Depth Sections | 4 | Complete |
| 23 | CI/CD, Deployment, and Dark Mode | 7 | Pending |
| 24 | Polish and Animations | 3 | Pending |

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 24 (+ 6 docs/verification)
- Average duration: 4.2 min per plan
- Total execution time: ~126 min

**Velocity (v1.1):**
- Total plans completed: 14
- Total tests written: 428
- Timeline: 1 day (2026-02-08)

**Velocity (v1.2):**

| Plan | Duration | Tasks | Files | Tests |
|------|----------|-------|-------|-------|
| 16-01 | 8 min | 2 | 9 | 31 |
| 16-02 | 5 min | 2 | 9 | 563 (full suite) |
| 17-01 | 5 min | 2 | 6 | 569 (full suite) |
| 17-02 | 3 min | 2 | 3 | 569 (full suite) |
| 18-01 | 5 min | 2 | 4 | 575 (full suite) |
| 19-01 | 4 min | 2 | 5 | 581 (full suite) |
| 19-02 | 3 min | 1 | 4 | 575 (full suite) |

**Velocity (v1.3):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| 20-01 | 4 min | 2 | 8 |
| 21-01 | 4 min | 2 | 16 |
| 21-02 | 3 min | 2 | 4 |
| 22-01 | 2 min | 2 | 3 |
| 22-02 | 2 min | 2 | 3 |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (23 entries across v1.0 + v1.1 + v1.2, plus 3 pending for v1.3).

v1.3 decisions:
- Astro for site (not Starlight) -- marketing-forward, not docs-heavy
- Same-repo /site folder -- one repo, GitHub Pages from subfolder
- Blues/grays professional palette -- distinct from personal site (orange) and networking-tools (dark orange)
- Tailwind v4 via @tailwindcss/vite (not deprecated @astrojs/tailwind)
- CSS-first @theme tokens with OKLCH values (no tailwind.config.js)
- ClientRouter (Astro 5 rename of ViewTransitions)
- Self-hosted fonts via @fontsource-variable (no Google Fonts CDN)
- GitHub icon uses fill (filled logo) vs stroke (Feather/Lucide style) for other UI icons
- Stats 2-col mobile / 4-col tablet+ grid to prevent text overflow at 375px
- ScreenshotFrame gradient placeholder with slot for future screenshot injection
- Icon components stored in data arrays for clean map-based rendering
- Footer uses <footer> element (not <section>) for semantic HTML landmarks
- Features grid uses CSS Grid for equal-height rows (not Flexbox)
- Horizontal scroll (overflow-x-auto) over wrapping for code blocks
- github-dark-default Shiki theme on bg-surface-900 for code section visual break
- Curated real source code excerpts for code snippet showcase (not fabricated)
- Narrower max-w-3xl container for text-heavy Timeline and QuickStart sections
- Vertical timeline at all breakpoints -- natural reading flow, no mobile breakpoint changes needed

### Pending Todos

None.

### Blockers/Concerns

- Screenshot capture workflow not specified (need running app for dashboard/kanban/analytics screenshots)
- OG image creation tool not decided (Figma, Canva, or screenshot + crop)
- Terminal animation implementation approach TBD (typed.js vs custom -- Phase 24)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Fix technical debt: remove Config shim, dead static mount, update arch docs | 2026-02-08 | 9f7f3de | [001-fix-technical-debt](./quick/001-fix-technical-debt/) |
| 002 | Fix CI: increase test coverage from 62.61% to 80%+ (115 new tests) | 2026-02-08 | bf35a16 | [002-fix-ci-increase-test-coverage-from-62-61](./quick/002-fix-ci-increase-test-coverage-from-62-61/) |
| 003 | Fix kanban drag-and-drop destroying board (htmx.ajax swap bug) | 2026-02-08 | 31dc69b | [003-fix-kanban-drag-and-drop-status-switchin](./quick/003-fix-kanban-drag-and-drop-status-switchin/) |

## Session Continuity

Last session: 2026-02-13
Stopped at: Completed 22-02-PLAN.md (Timeline, QuickStart, page composition). Phase 22 complete. Ready for Phase 23.
Resume file: .planning/phases/22-engineering-depth-sections/
