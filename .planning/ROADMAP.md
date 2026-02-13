# Roadmap: JobFlow

## Milestones

- SHIPPED **v1.0 MVP** -- Phases 1-8 (shipped 2026-02-08)
- SHIPPED **v1.1 Test Web App** -- Phases 9-15 (shipped 2026-02-08)
- SHIPPED **v1.2 Claude CLI Agent Integration** -- Phases 16-19 (shipped 2026-02-11)
- ACTIVE **v1.3 Project Showcase Site** -- Phases 20-24

## Phases

<details>
<summary>SHIPPED v1.0 MVP (Phases 1-8) -- SHIPPED 2026-02-08</summary>

- [x] Phase 1: Config Externalization (3/3 plans) -- completed 2026-02-07
- [x] Phase 2: Platform Architecture (2/2 plans) -- completed 2026-02-07
- [x] Phase 3: Discovery Engine (3/3 plans) -- completed 2026-02-07
- [x] Phase 4: Scheduled Automation (2/2 plans) -- completed 2026-02-07
- [x] Phase 5: Dashboard Core (4/4 plans) -- completed 2026-02-07
- [x] Phase 6: Dashboard Analytics (2/2 plans) -- completed 2026-02-07
- [x] Phase 7: AI Resume & Cover Letter (4/4 plans) -- completed 2026-02-07
- [x] Phase 8: One-Click Apply (4/4 plans) -- completed 2026-02-08

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>SHIPPED v1.1 Test Web App (Phases 9-15) -- SHIPPED 2026-02-08</summary>

- [x] Phase 9: Test Infrastructure (2/2 plans) -- completed 2026-02-08
- [x] Phase 10: Unit Tests (3/3 plans) -- completed 2026-02-08
- [x] Phase 11: Database Integration Tests (2/2 plans) -- completed 2026-02-08
- [x] Phase 12: Web & API Integration Tests (3/3 plans) -- completed 2026-02-08
- [x] Phase 13: Config Integration Tests (1/1 plan) -- completed 2026-02-08
- [x] Phase 14: CI Pipeline (1/1 plan) -- completed 2026-02-08
- [x] Phase 15: E2E Tests (2/2 plans) -- completed 2026-02-08

Full details: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

<details>
<summary>SHIPPED v1.2 Claude CLI Agent Integration (Phases 16-19) -- SHIPPED 2026-02-11</summary>

- [x] Phase 16: CLI Wrapper Foundation (2/2 plans) -- completed 2026-02-11
- [x] Phase 17: AI Scoring (2/2 plans) -- completed 2026-02-11
- [x] Phase 18: Resume Tailoring via CLI + SSE (1/1 plan) -- completed 2026-02-11
- [x] Phase 19: Cover Letter via CLI + SSE & Cleanup (2/2 plans) -- completed 2026-02-11

Full details: [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)

</details>

### v1.3 Project Showcase Site (Phases 20-24)

#### Phase 20: Foundation and Configuration

**Goal:** A working Astro project exists in `/site` with correct base path, professional design tokens, self-hosted fonts, and a BaseLayout that produces valid social sharing previews -- the foundation every subsequent phase builds on.

**Dependencies:** None (first phase of milestone)

**Requirements:** SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, DSGN-01, SEO-01, SEO-02

**Plans:** 1 plan

Plans:
- [x] 20-01-PLAN.md — Scaffold Astro project with Tailwind v4, design tokens, BaseLayout with SEO meta tags, and minimal index page

**Success Criteria:**
1. Running `npm run dev` inside `/site` serves a page at `localhost:4321/jobs/` with the correct base path prefix visible in all asset URLs
2. Running `npm run build && npm run preview` produces identical output to dev (no broken paths, no missing assets)
3. The page renders with the professional blues/grays palette and Inter/DM Sans fonts (visually distinct from the user's personal site)
4. Viewing page source shows complete OpenGraph and Twitter Card meta tags with absolute URLs
5. The root `.gitignore` includes `node_modules/`, `site/dist/`, and `site/.astro/` entries

---

#### Phase 21: Core Sections and Responsive Design

**Goal:** Visitors see a complete, credible project page with hero, metrics, feature showcase, tech stack, and footer -- the "table stakes" content that communicates project quality in under 30 seconds.

**Dependencies:** Phase 20 (BaseLayout, palette, fonts, ScreenshotFrame primitives)

**Requirements:** CONT-01, CONT-02, CONT-03, CONT-04, CONT-09, DSGN-02, DSGN-04

**Plans:** 2 plans

Plans:
- [x] 21-01-PLAN.md — ScreenshotFrame component, SVG icon library, Hero section, and Stats bar (above the fold)
- [x] 21-02-PLAN.md — Features grid, TechStack badges, Footer, and full page composition with responsive verification

**Success Criteria:**
1. Above the fold shows a headline, subheadline, dashboard screenshot in a browser mockup frame, and a "View on GitHub" button that links to the repository
2. A stats bar displays at least 4 key metrics (LOC, tests, coverage, platforms) in a visually distinct row
3. A feature grid presents 6-8 cards organized by category (Discovery, Intelligence, Dashboard, Automation) with icons and descriptions
4. A tech stack section shows technology badges with role labels and a footer contains GitHub and personal site links
5. The page layout is usable at 375px mobile, 768px tablet, and 1440px desktop widths without horizontal scroll or overlapping elements

---

#### Phase 22: Engineering Depth Sections

**Goal:** Technically-minded visitors (engineers, hiring managers reviewing code quality) find architecture details, real code examples, project history, and a quick start guide that demonstrate engineering depth beyond a typical portfolio page.

**Dependencies:** Phase 21 (page structure, section composition pattern established)

**Requirements:** CONT-05, CONT-06, CONT-07, CONT-08

**Plans:** 2 plans

Plans:
- [x] 22-01-PLAN.md — Architecture pipeline diagram and Code Snippets with Shiki syntax highlighting
- [x] 22-02-PLAN.md — Timeline, QuickStart, and full page composition with all 9 sections

**Success Criteria:**
1. An architecture/pipeline section visually communicates the 5-phase flow (setup, login, search, score, apply) as a diagram or visual sequence
2. A code snippets section shows 2-3 syntax-highlighted examples (platform Protocol, scoring engine, decorator registry) that are readable and correctly formatted
3. A milestone timeline displays v1.0, v1.1, and v1.2 with per-milestone stats (LOC, tests, features) telling the build story
4. A quick start section presents a 5-step setup guide (clone, install, configure, run, dashboard) that a developer could follow to run the project

---

#### Phase 23: CI/CD, Deployment, and Dark Mode

**Goal:** The site is deployed to GitHub Pages, accessible at the public URL with all assets loading, Python CI is not disrupted by site changes, and the site supports both light and dark color schemes.

**Dependencies:** Phase 22 (all content sections complete -- deploying a content-complete site)

**Requirements:** DPLY-01, DPLY-02, DPLY-03, DPLY-04, DSGN-03, SEO-03, SEO-04

**Plans:** 3 plans

Plans:
- [ ] 23-01-PLAN.md — GitHub Actions deploy workflow, CI path isolation, sitemap integration, and JSON-LD structured data
- [ ] 23-02-PLAN.md — Dark mode infrastructure and dark: utility classes on all section components
- [ ] 23-03-PLAN.md — Deployment verification: enable Pages, push, and verify production site

**Success Criteria:**
1. Pushing a change to `site/**` on main triggers the deploy workflow and the site is accessible at `username.github.io/jobs/` with all sections, images, and styles loading correctly
2. Pushing a change to Python files (outside `site/`) does NOT trigger the deploy workflow, and pushing site-only changes does NOT trigger the Python CI workflow
3. The site respects `prefers-color-scheme` and/or provides a toggle -- dark mode renders all sections with readable contrast and correct colors
4. Viewing page source shows JSON-LD structured data using SoftwareApplication schema with correct project metadata
5. A sitemap.xml is generated and accessible at the deployed URL

---

#### Phase 24: Polish and Animations

**Goal:** The page feels alive and memorable with a terminal demo that shows the product in action, smooth scroll navigation, and subtle entrance animations that signal craftsmanship.

**Dependencies:** Phase 23 (site deployed and functional -- polish is additive)

**Requirements:** PLSH-01, PLSH-02, PLSH-03

**Success Criteria:**
1. An animated terminal section simulates `python orchestrator.py` output with a typing effect, showing pipeline phases executing with realistic timing
2. Sections fade in as the visitor scrolls down the page, with animations triggered only when elements enter the viewport (not on page load)
3. Clicking a navigation link smoothly scrolls to the target section with visible animation rather than instant jumping

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Config Externalization | v1.0 | 3/3 | Complete | 2026-02-07 |
| 2. Platform Architecture | v1.0 | 2/2 | Complete | 2026-02-07 |
| 3. Discovery Engine | v1.0 | 3/3 | Complete | 2026-02-07 |
| 4. Scheduled Automation | v1.0 | 2/2 | Complete | 2026-02-07 |
| 5. Dashboard Core | v1.0 | 4/4 | Complete | 2026-02-07 |
| 6. Dashboard Analytics | v1.0 | 2/2 | Complete | 2026-02-07 |
| 7. AI Resume & Cover Letter | v1.0 | 4/4 | Complete | 2026-02-07 |
| 8. One-Click Apply | v1.0 | 4/4 | Complete | 2026-02-08 |
| 9. Test Infrastructure | v1.1 | 2/2 | Complete | 2026-02-08 |
| 10. Unit Tests | v1.1 | 3/3 | Complete | 2026-02-08 |
| 11. Database Integration Tests | v1.1 | 2/2 | Complete | 2026-02-08 |
| 12. Web & API Integration Tests | v1.1 | 3/3 | Complete | 2026-02-08 |
| 13. Config Integration Tests | v1.1 | 1/1 | Complete | 2026-02-08 |
| 14. CI Pipeline | v1.1 | 1/1 | Complete | 2026-02-08 |
| 15. E2E Tests | v1.1 | 2/2 | Complete | 2026-02-08 |
| 16. CLI Wrapper Foundation | v1.2 | 2/2 | Complete | 2026-02-11 |
| 17. AI Scoring | v1.2 | 2/2 | Complete | 2026-02-11 |
| 18. Resume Tailoring via CLI + SSE | v1.2 | 1/1 | Complete | 2026-02-11 |
| 19. Cover Letter via CLI + SSE & Cleanup | v1.2 | 2/2 | Complete | 2026-02-11 |
| 20. Foundation and Configuration | v1.3 | 1/1 | Complete | 2026-02-13 |
| 21. Core Sections and Responsive Design | v1.3 | 2/2 | Complete | 2026-02-13 |
| 22. Engineering Depth Sections | v1.3 | 2/2 | Complete | 2026-02-13 |
| 23. CI/CD, Deployment, and Dark Mode | v1.3 | 0/3 | Pending | -- |
| 24. Polish and Animations | v1.3 | 0/? | Pending | -- |
