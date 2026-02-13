# Requirements: JobFlow Showcase Site

**Defined:** 2026-02-13
**Core Value:** From discovery to application in one tool -- the showcase site must communicate this clearly and make visitors understand the engineering depth in under 30 seconds.

## v1.3 Requirements

Requirements for the GitHub Pages project showcase site. Each maps to roadmap phases.

### Setup

- [ ] **SETUP-01**: Astro project scaffolded in `/site` with `base: '/jobs'` and `trailingSlash: 'always'`
- [ ] **SETUP-02**: Tailwind CSS v4 configured via `@tailwindcss/vite` with professional blues/grays `@theme` palette
- [ ] **SETUP-03**: Self-hosted Inter (body) + DM Sans (display) fonts via Fontsource variable packages
- [ ] **SETUP-04**: `.gitignore` updated with `node_modules/`, `site/dist/`, `site/.astro/`
- [ ] **SETUP-05**: BaseLayout component with HTML shell, meta tags, font loading, global CSS, ViewTransitions

### Content

- [ ] **CONT-01**: Hero section with headline, subheadline, dashboard placeholder screenshot, and "View on GitHub" CTA
- [ ] **CONT-02**: Stats bar displaying key metrics (18K LOC, 581 tests, 80%+ coverage, 3 platforms)
- [ ] **CONT-03**: Feature grid with 6-8 cards covering Discovery, Intelligence, Dashboard, and Automation categories
- [ ] **CONT-04**: Tech stack section with technology badges (Python, Playwright, FastAPI, SQLite, htmx, Claude CLI) and one-word role labels
- [ ] **CONT-05**: Architecture/pipeline diagram section showing the 5-phase flow (setup -> login -> search -> score -> apply)
- [ ] **CONT-06**: Code snippets section with 2-3 syntax-highlighted examples (platform Protocol pattern, scoring engine, decorator registry)
- [ ] **CONT-07**: Milestone timeline showing v1.0 -> v1.1 -> v1.2 build story with stats per milestone
- [ ] **CONT-08**: Quick start section with 5-step setup guide (clone, install, configure, run, dashboard)
- [ ] **CONT-09**: Footer with GitHub repo link, personal site link (patrykgolabek.dev), and contact info

### Design

- [ ] **DSGN-01**: Professional blues/grays color palette distinct from personal site (orange/teal) and networking-tools (dark orange)
- [ ] **DSGN-02**: Responsive design tested at 375px (mobile), 768px (tablet), and 1440px (desktop) breakpoints
- [ ] **DSGN-03**: Dark mode support with `prefers-color-scheme` detection and optional toggle
- [ ] **DSGN-04**: Browser mockup ScreenshotFrame component with placeholder gradient content

### Deployment

- [ ] **DPLY-01**: GitHub Actions `deploy-site.yml` with `withastro/action@v5` and `path: ./site`
- [ ] **DPLY-02**: Deploy workflow triggers only on `site/**` changes via path filter
- [ ] **DPLY-03**: Python CI workflow updated with `paths-ignore: ['site/**']` to skip on site-only changes
- [ ] **DPLY-04**: Site accessible at `username.github.io/jobs/` after deployment with all assets loading correctly

### SEO

- [ ] **SEO-01**: OpenGraph meta tags with absolute URLs (og:title, og:image, og:url, og:description)
- [ ] **SEO-02**: Twitter Card meta tags for summary_large_image rendering
- [ ] **SEO-03**: JSON-LD structured data using SoftwareApplication schema
- [ ] **SEO-04**: Sitemap generated via `@astrojs/sitemap` integration

### Polish

- [ ] **PLSH-01**: Animated terminal demo simulating CLI pipeline output with typing effect
- [ ] **PLSH-02**: Scroll-triggered fade-in animations via IntersectionObserver + CSS transitions
- [ ] **PLSH-03**: Smooth scroll navigation with anchor links to page sections from nav bar

## Future Requirements

### Content Enhancements (v1.4+)

- **CONT-10**: Real dashboard screenshots replacing placeholders
- **CONT-11**: Animated GIF or video walkthrough of the full pipeline
- **CONT-12**: Before/after comparison table (manual job search vs JobFlow)
- **CONT-13**: Interactive architecture diagram with hover states on pipeline stages

### Platform Expansion

- **PLAT-01**: Custom domain setup (e.g., jobflow.patrykgolabek.dev)
- **PLAT-02**: Lighthouse 100/100/100/100 score validation

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live demo / hosted instance | Requires credentials (Indeed login, Claude CLI auth). Security risk. |
| Blog / content section | Project showcase, not a personal site. Blog belongs on patrykgolabek.dev. |
| Multi-page site | Recruiters won't click through 5 pages. Single-page with anchor navigation. |
| React/Vue/Svelte components | Zero-JS static page. Astro components handle everything. |
| Newsletter / email capture | No audience to nurture. GitHub stars are the engagement mechanism. |
| Testimonials / social proof | Personal project. Fake testimonials destroy credibility. Use quality signals (test count, coverage) instead. |
| Heavy animations / parallax | Looks like a template. Undermines "serious engineer" signal. Keep subtle. |
| GSAP or animation libraries | 40KB+ JS for effects achievable with IntersectionObserver + CSS. Disproportionate. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 20 | Pending |
| SETUP-02 | Phase 20 | Pending |
| SETUP-03 | Phase 20 | Pending |
| SETUP-04 | Phase 20 | Pending |
| SETUP-05 | Phase 20 | Pending |
| CONT-01 | Phase 21 | Pending |
| CONT-02 | Phase 21 | Pending |
| CONT-03 | Phase 21 | Pending |
| CONT-04 | Phase 21 | Pending |
| CONT-05 | Phase 22 | Pending |
| CONT-06 | Phase 22 | Pending |
| CONT-07 | Phase 22 | Pending |
| CONT-08 | Phase 22 | Pending |
| CONT-09 | Phase 21 | Pending |
| DSGN-01 | Phase 20 | Pending |
| DSGN-02 | Phase 21 | Pending |
| DSGN-03 | Phase 23 | Pending |
| DSGN-04 | Phase 21 | Pending |
| DPLY-01 | Phase 23 | Pending |
| DPLY-02 | Phase 23 | Pending |
| DPLY-03 | Phase 23 | Pending |
| DPLY-04 | Phase 23 | Pending |
| SEO-01 | Phase 20 | Pending |
| SEO-02 | Phase 20 | Pending |
| SEO-03 | Phase 23 | Pending |
| SEO-04 | Phase 23 | Pending |
| PLSH-01 | Phase 24 | Pending |
| PLSH-02 | Phase 24 | Pending |
| PLSH-03 | Phase 24 | Pending |

**Coverage:**
- v1.3 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-13*
*Last updated: 2026-02-13 after initial definition*
