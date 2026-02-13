# Project Research Summary

**Project:** JobFlow — GitHub Pages Showcase Site
**Domain:** Marketing-forward static site for technical portfolio project
**Researched:** 2026-02-13
**Confidence:** HIGH

## Executive Summary

This is a marketing landing page for an 18K LOC Python job automation platform, deployed as a static site to GitHub Pages from the existing repository. The recommended approach is a self-contained Astro 5 project in `/site` with Tailwind v4, self-hosted fonts (Inter + DM Sans), and near-zero JavaScript. The entire page is a single-scroll marketing surface showcasing the product through screenshots, metrics (581 tests, 80%+ coverage), and a visual pipeline walkthrough. The site lives alongside the Python app without any runtime integration — it describes the product but doesn't call it.

The critical architectural decision is treating `/site` as a completely independent subfolder with its own package.json, CI workflow, and deployment pipeline. This prevents toolchain contamination between Python (uv, ruff, pytest) and Node.js (npm, astro, tailwind). The biggest risk is base path misconfiguration — GitHub Pages project sites serve from `username.github.io/jobs/`, not root, so every asset, link, and meta tag must account for the `/jobs/` prefix or the deployed site will be a blank page. This only breaks in production (works perfectly in dev), making it an insidious first-time mistake.

The MVP is a three-tier build: (1) credible project page with hero, stats, features, tech stack; (2) engineering depth with architecture diagram, code snippets, milestone timeline; (3) polish with animated terminal demo and scroll effects. Defer any live demo (requires credentials), blog section (maintenance burden), or JavaScript framework (overkill for static content). The showcase itself is a code sample — sloppy CSS or slow load times undermine the credibility of the Python project.

## Key Findings

### Recommended Stack

Deliberately minimal stack optimized for fast load times and zero runtime JavaScript. Astro 5.17.2 (latest stable) with Tailwind CSS v4 (CSS-first configuration via `@theme` directive, no config file). Image optimization via built-in `astro:assets` with Sharp backend (generates AVIF + WebP + responsive srcset at build time). Fonts self-hosted via Fontsource (Inter for body, DM Sans for headings) to eliminate Google Fonts latency. Animations achieved with CSS `@keyframes` + a ~20-line `IntersectionObserver` script — NO GSAP (the portfolio site uses GSAP for complex particle canvas, but a showcase site with simple fade-in-on-scroll effects doesn't justify 40KB of animation library).

**Core technologies:**
- **Astro 5.17.2**: Static site generator — Astro 6 is in beta, not production-ready. User already runs Astro on two sites (portfolio + networking tools), so DX is familiar.
- **Tailwind CSS v4 + @tailwindcss/vite**: Utility CSS via new Vite plugin — the old `@astrojs/tailwind` integration is deprecated for v4.
- **Self-hosted fonts (Fontsource)**: Inter (body) + DM Sans (headings) — self-hosting is faster and privacy-preserving vs. Google Fonts CDN.
- **withastro/action@v5**: Official GitHub Action for build + deploy — supports `path: ./site` parameter for subfolder builds (critical for monorepo).
- **CSS animations + IntersectionObserver**: Zero-dependency scroll animations — proportional to the task, unlike GSAP which is overkill here.

**What NOT to add:**
- ~~GSAP~~ — Adds 40KB JS for effects achievable with 20 lines of vanilla JS
- ~~@astrojs/tailwind~~ — Deprecated for v4, use `@tailwindcss/vite` instead
- ~~React/Vue/Svelte integrations~~ — No interactive components needed, Astro components handle everything
- ~~Astro 6 beta~~ — Currently at beta.11, stable release weeks away

### Expected Features

The showcase site is not the product — it's a marketing surface presenting the product to recruiters, hiring managers, and fellow engineers. The audience needs to understand in 30 seconds: "This person built something serious." The feature set is divided into table stakes (expected on any polished project page), differentiators (what makes it stand out), and anti-features (explicit don'ts).

**Must have (table stakes):**
- **Hero section with value proposition** — What JobFlow does + why it matters in under 8 seconds. Headline + subheadline + "View on GitHub" CTA.
- **Screenshots/visual proof** — 87% of hiring managers consider portfolios more valuable when they can SEE the work. Dashboard, kanban board, SSE streaming, analytics.
- **Stats/metrics bar** — Concrete numbers create instant credibility: "18K LOC, 581 tests, 80%+ coverage, 3 platforms, Built in 3 days."
- **Tech stack section** — Logo + name + one-word role (e.g., "FastAPI — API & Dashboard").
- **Architecture diagram** — Clean system diagram showing pipeline flow (scrape → score → dashboard → apply).
- **Responsive design + dark mode** — Recruiters view on mobile, developers expect dark mode by default.

**Should have (differentiators):**
- **Animated terminal demo** — Simulated `python orchestrator.py` output showing phases executing with typing effect. Most impactful differentiator — shows "this actually works" without requiring installation.
- **Milestone timeline** — "v1.0: MVP in 1 day. v1.1: 428 tests. v1.2: Claude CLI." Shows velocity and iteration discipline. The "built in 1 day" fact is extraordinary and should be highlighted.
- **Code snippets with syntax highlighting** — Show the `@register_platform` decorator pattern, Pydantic model, scoring engine. Demonstrates code quality directly.
- **"How it works" walkthrough** — 4-5 step visual: Configure → Discover → Score → Review → Apply. Tells a story vs. feature grid.
- **Scroll-triggered animations** — Subtle fade/slide-in (200-300ms, not aggressive) signals polish. IntersectionObserver + CSS classes, no library.

**Defer (anti-features — explicitly avoid):**
- ~~Live demo / hosted instance~~ — Requires credentials, either fake (undermines trust) or insecure.
- ~~Blog / content section~~ — A blog with 1-2 posts looks abandoned. Maintenance burden.
- ~~Pricing / signup / waitlist~~ — JobFlow is a personal tool, not a product. Commercial framing is misleading.
- ~~Complex JavaScript framework~~ — React/Vue for a single static page is poor judgment about tool selection.
- ~~Testimonials~~ — Fake testimonials are obviously fake. Use verifiable quality signals instead (test count, coverage).

**Content dependencies (blocking):**
Screenshots (dashboard, kanban, analytics, SSE streaming), architecture diagram, terminal output script, feature copywriting (headline, subheadline, 8 feature descriptions). Total prep: ~4 hours before writing any HTML.

### Architecture Approach

Self-contained Astro project in `/site` subfolder with zero runtime integration with the Python app. The site describes the product but doesn't call it — the only connection is screenshots manually captured from the running dashboard and committed to `site/src/assets/screenshots/`. Two completely independent systems with separate CI workflows: Python CI (pytest + ruff) skips on site-only changes via `paths-ignore: ['site/**']`, and Astro deploy triggers only on `paths: ['site/**']` changes.

**Major components:**
1. **BaseLayout.astro** — HTML shell, meta tags (OG/Twitter), fonts, global CSS, dark mode, canonical URLs using `Astro.site` + `Astro.url.pathname`.
2. **Section components** — Hero, Features, Pipeline, Screenshots, TechStack, CTA, Footer. Each self-contained, composed in `pages/index.astro`. No React/Vue — pure Astro components compile to zero JavaScript.
3. **UI primitives** — Button, Badge, Card, ScreenshotFrame (browser chrome mockup). Small, no dependencies on each other.
4. **Image optimization pipeline** — PNGs in `src/assets/screenshots/` → Sharp generates AVIF + WebP + responsive `srcset` at build time → served with explicit width/height to prevent CLS.
5. **GitHub Actions deploy workflow** — `withastro/action@v5` with `path: ./site` builds from subfolder, `actions/deploy-pages@v4` deploys artifact. Separate concurrency group (`pages`) from CI (`${{ github.workflow }}-${{ github.ref }}`).

**Critical patterns:**
- **Base path awareness**: Every link/asset must account for `/jobs/` prefix via `import.meta.env.BASE_URL` or Astro's asset imports.
- **Commit lockfile, gitignore node_modules**: `site/package-lock.json` committed (withastro/action needs it), `node_modules/` recursively ignored.
- **Trailing slash always**: GitHub Pages redirects URLs without trailing slashes (301, 15-80ms penalty) — set `trailingSlash: 'always'` in config.
- **Props down, no state**: Section components receive data via props or define inline. No stores, no fetch calls. All content known at build time.

### Critical Pitfalls

1. **Base path misconfiguration breaks every asset/link/image** — Without `base: '/jobs'` in `astro.config.mjs`, the deployed site is a blank page (CSS/JS/images all 404). This only breaks in production (works perfectly in dev). Prevention: Set `base` from first commit, use `import.meta.env.BASE_URL` for assets, test with `astro preview` before deploying.

2. **Custom domain later makes base path a liability** — Project site needs `base: '/jobs'`, custom domain needs no base. Switching requires changing config AND verifying no template has hardcoded `/jobs/`. Prevention: Decide now (likely project path for MVP), NEVER hardcode base paths, always use `BASE_URL`.

3. **GitHub Actions workflow conflicts** — Two workflows (CI + deploy) both trigger on push to main. Missing `path: ./site` in `withastro/action` tries to build from repo root (finds `pyproject.toml`, not `package.json`) and fails. Prevention: Deploy workflow has `paths: ['site/**']` filter, CI has `paths-ignore: ['site/**']`, deploy uses `path: ./site` parameter.

4. **Missing or incorrect OG meta tags** — Social shares show no preview without absolute `og:image` URL and matching `og:url`. Relative paths ignored by crawlers. Prevention: Use `new URL('/jobs/og-image.png', Astro.site).href` for all OG URLs, create 1200x630px image in `public/`, validate with Twitter/LinkedIn debug tools.

5. **Developer tool showcase reads like documentation** — Wall of text explaining architecture instead of hero + screenshot above fold. 87% of hiring managers value portfolios when they can SEE the work. Prevention: One-sentence headline, dashboard screenshot in first viewport (no scrolling), show don't tell, limit text per section.

6. **Large unoptimized images destroy page load** — Full-resolution Retina screenshots (2560x1600, 1-4MB each) → total page weight 10-25MB → 15-30s load on mobile. Prevention: Use Astro `<Image>` component (generates WebP/AVIF + responsive srcset), pre-optimize to max 1600px wide, target <200KB per image, lazy-load below-fold.

7. **Node.js tooling pollution in Python repo** — Missing `node_modules/` in `.gitignore` → someone commits 200MB deps. Root-level `npm install` creates `package-lock.json` at wrong level. Prevention: Update `.gitignore` before `npm install`, keep ALL Node files inside `/site`, commit `site/package-lock.json` but NEVER root-level.

8. **Trailing slash behavior on GitHub Pages** — URLs without trailing slashes redirect (301, 15-80ms penalty). Astro default `trailingSlash: 'ignore'` doesn't prevent this. Prevention: Set `trailingSlash: 'always'` from start, test with `astro preview`.

## Implications for Roadmap

Based on research, suggested phase structure follows a bottom-up build order: foundation (config + project scaffold) → primitives (layout + UI components) → content (sections + assets) → infrastructure (CI/CD + deployment).

### Phase 1: Foundation & Configuration
**Rationale:** Base path misconfiguration is the #1 critical pitfall and only manifests in production. Setting `base: '/jobs'`, `trailingSlash: 'always'`, and `site` correctly from the start prevents rework on every template.

**Delivers:** Scaffolded Astro project in `/site` with correct `astro.config.mjs` (base path, site URL, Tailwind integration), committed lockfile, updated `.gitignore` (node_modules, site/dist).

**Addresses:**
- Pitfall 1 (base path misconfiguration)
- Pitfall 2 (custom domain decision — document now)
- Pitfall 7 (Node.js tooling pollution)
- Pitfall 8 (trailing slash redirects)
- Pitfall 10 (lockfile not committed)

**Stack elements:** Astro 5.17.2, Tailwind v4 via @tailwindcss/vite, Fontsource fonts

**Validation:** `npm run dev` serves at `localhost:4321/jobs/` (note base path), `npm run build && npm run preview` shows correct paths.

### Phase 2: Layout & UI Primitives
**Rationale:** BaseLayout establishes OG meta tags (pitfall 4) and responsive design foundation (pitfall 12). UI primitives (Button, Badge, Card, ScreenshotFrame) have no dependencies on each other so can be built quickly before sections.

**Delivers:** BaseLayout.astro with OG/Twitter meta (absolute URLs via `Astro.site`), font loading, global CSS with Tailwind `@theme` config (blue/gray palette, Inter/DM Sans), dark mode support. UI components: Button, Badge, Card, Section wrapper, ScreenshotFrame (browser chrome mockup).

**Addresses:**
- Pitfall 4 (OG meta tags)
- Pitfall 12 (responsive design)
- Feature: Dark mode (table stakes)
- Feature: Clean typography (table stakes)

**Architecture component:** BaseLayout, UI primitives layer

**Validation:** OG tags validate on Twitter/LinkedIn debug tools, responsive at 375px/768px/1440px.

### Phase 3: Content Assets & Section Components
**Rationale:** Screenshots are the highest-impact content dependency (pitfall 5, feature research). Section components depend on UI primitives from Phase 2. Can parallelize screenshot capture and section component structure.

**Delivers:**
- Screenshots captured: dashboard (light/dark), kanban board, analytics, SSE streaming
- Images optimized (<200KB each) and placed in `src/assets/screenshots/`
- Section components: Hero (with screenshot above fold), Features (grid with icons), Pipeline (system diagram), Screenshots (gallery with ScreenshotFrame), TechStack (logos), CTA (GitHub link), Footer
- Composed in `pages/index.astro`

**Addresses:**
- Pitfall 5 (showcase reads like docs — hero + screenshot above fold)
- Pitfall 6 (unoptimized images — use Astro Image component, pre-optimize)
- Features: Hero, screenshots, stats bar, tech stack, architecture diagram (all table stakes)

**Architecture component:** Section components layer, image optimization pipeline

**Dependencies:** Running Python app locally for screenshot capture, architecture diagram creation (Excalidraw/Mermaid)

**Validation:** `astro build` succeeds, preview shows all images load, page weight <2MB total, Lighthouse performance >70.

### Phase 4: CI/CD & Deployment
**Rationale:** Workflow conflicts (pitfall 3) are critical but independent of site content. Deploy workflow must be correct before first push or the site won't deploy.

**Delivers:**
- `.github/workflows/deploy-site.yml` with `withastro/action@v5` (path: ./site), `actions/deploy-pages@v4`, concurrency group `pages`, paths filter `['site/**']`
- Modified `.github/workflows/ci.yml` with `paths-ignore: ['site/**']`
- GitHub Pages enabled (Settings > Pages > Source: GitHub Actions)
- Deployed site accessible at `patrykattc.github.io/jobs/`

**Addresses:**
- Pitfall 3 (workflow conflicts)
- Stack element: withastro/action@v5 deployment

**Architecture component:** GitHub Actions deploy workflow

**Validation:** Deploy succeeds, site loads with no 404s on assets, Python CI skips on site-only changes, deploy triggers on site changes.

### Phase 5: Polish & Differentiators (Optional)
**Rationale:** Site is shippable after Phase 4 (credible project page). Phase 5 adds differentiators that make it memorable but aren't required for launch.

**Delivers:**
- Animated terminal demo (typed.js or custom script simulating pipeline output)
- Milestone timeline section (v1.0 → v1.1 → v1.2 with stats)
- Code snippets section (platform protocol, decorator registry, scoring engine) with Prism.js
- Scroll-triggered fade-in animations (IntersectionObserver + CSS)
- Before/after comparison table
- Performance optimization (target Lighthouse 100/100/100/100)

**Addresses:**
- Features: Animated terminal demo, milestone timeline, code snippets, scroll animations (all differentiators)
- Feature: Performance metrics (differentiator)

**Defer if time-constrained:** This phase is incremental polish, not core functionality.

### Phase Ordering Rationale

- **Phase 1 before everything**: Base path config mistakes require reworking every template. Must be correct from first commit.
- **Phase 2 before Phase 3**: Section components depend on BaseLayout (for layout wrapper) and UI primitives (Button, Card, ScreenshotFrame). Bottom-up dependency order.
- **Phase 3 before Phase 4**: No point deploying an empty site. Content must exist before CI/CD setup.
- **Phase 4 is independent**: Could be set up earlier (no code dependency) but makes more sense after content exists for validation.
- **Phase 5 is purely incremental**: Site is shippable without it. Build if time permits.

**Grouping rationale:**
- Foundation (Phase 1) addresses config pitfalls that affect all downstream work
- Build (Phases 2-3) follows Astro component architecture (layout → primitives → sections → pages)
- Deploy (Phase 4) is infrastructure, not code
- Polish (Phase 5) adds nice-to-haves after MVP is complete

**Avoids pitfalls:**
- Phases 1-3 systematically address all 8 critical/moderate pitfalls before deploy
- Phase 4 validates the deployment before adding polish
- Phase 5 ensures MVP isn't delayed by nice-to-haves

### Research Flags

**Phases with standard patterns (skip research-phase):**
- **Phase 1**: Astro project scaffold is well-documented, user has done this twice before (portfolio + networking-tools).
- **Phase 2**: BaseLayout and UI components follow standard Astro patterns, Tailwind v4 documented in official guides.
- **Phase 4**: GitHub Actions deploy via withastro/action is the official path, extensively documented.

**Phases likely needing deeper research:**
- **Phase 3 (if screenshot workflow is complex)**: If product has many surfaces to capture or screenshot standardization is unclear, may need research on visual asset creation workflow.
- **Phase 5 (terminal animation)**: Animated terminal demo pattern is unique — might need brief research on typed.js vs custom implementation if pursued.

**Overall:** Most phases follow well-documented Astro patterns. Research completed here should be sufficient for planning and execution without additional research phases.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Astro 5.17.2 latest stable verified via npm, Tailwind v4 official docs, user has two existing Astro sites, all versions verified. |
| Features | HIGH | Patterns derived from analysis of Tailwind/Astro/Supabase/shadcn homepages plus Evil Martians 100-devtool study (official research). Table stakes vs differentiators grounded in recruiter preference data. |
| Architecture | HIGH | Based on Astro official deploy docs, withastro/action v5 source, GitHub Actions docs, existing repo structure analysis. Self-contained subfolder is standard monorepo pattern. |
| Pitfalls | HIGH | All critical pitfalls verified against Astro official docs, GitHub Pages docs, or GitHub issues with reproduction cases. Base path issue is #1 reported problem for Astro on GitHub Pages. |

**Overall confidence:** HIGH

All research grounded in official documentation (Astro, GitHub Pages, Tailwind) or authoritative sources (Evil Martians study, Open Graph spec). Version numbers verified via npm on 2026-02-13. User has existing Astro expertise (two production sites). Stack is deliberately minimal (5 core dependencies) and well-understood.

### Gaps to Address

- **Custom domain decision**: Research assumes project path (`/jobs/`) but doesn't know if user plans custom domain within 6 months. Need to confirm during planning (affects base path config).

- **Screenshot capture workflow**: Research identifies screenshots as critical content dependency (~4 hours prep) but doesn't specify tooling. Need to confirm during Phase 3 planning: browser DevTools capture, screenshot tools (CleanShot X, etc.), retina vs standard resolution, light/dark mode variants.

- **CI Sharp build failures**: Research documents Sharp build failure pattern (withastro/astro#9345, #14531) but doesn't know if it will manifest in this repo's CI. Mitigation planned (explicit Sharp install OR passthrough image service fallback) but won't know which is needed until Phase 4.

- **OG image creation**: Research specifies 1200x630px OG image in `public/og-image.png` but doesn't specify creation tool or design. Need to address during content prep: design tool (Figma, Canva, screenshot + crop), branding elements to include.

- **Terminal animation implementation**: Research identifies animated terminal demo as highest-impact differentiator but doesn't commit to typed.js vs custom implementation. Need to evaluate during Phase 5 planning: bundle size, animation control, maintenance complexity.

All gaps are execution details, not architectural uncertainties. Core approach (self-contained Astro site in `/site` with GitHub Pages deploy) is HIGH confidence.

## Sources

### Primary (HIGH confidence)
- [Astro GitHub Pages Deployment Guide](https://docs.astro.build/en/guides/deploy/github/) — base path, site config, custom domain, lockfile requirement
- [Astro Configuration Reference](https://docs.astro.build/en/reference/configuration-reference/) — trailingSlash, base, site, image options
- [Astro Images Guide](https://docs.astro.build/en/guides/images/) — Image/Picture components, Sharp, src/ vs public/, responsive images
- [Tailwind CSS v4 Installation for Astro](https://tailwindcss.com/docs/installation/framework-guides/astro) — @tailwindcss/vite approach, @astrojs/tailwind deprecation
- [withastro/action GitHub Repo](https://github.com/withastro/action) — v5 inputs: path, node-version, package-manager
- [GitHub Pages Limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) — 100GB bandwidth, 1GB repo, 10 builds/hour
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions) — paths, paths-ignore filters
- [Open Graph Protocol Specification](https://ogp.me/) — required properties, URL requirements
- [Evil Martians: 100 Devtool Landing Pages Study](https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025) — hero patterns, visual content, messaging
- npm registry version checks (2026-02-13) — all versions verified

### Secondary (MEDIUM confidence)
- [Trailing Slash Tax on GitHub Pages](https://justoffbyone.com/posts/trailing-slash-tax/) — 15-80ms redirect penalty measurements
- [Astro base path issue #4229](https://github.com/withastro/astro/issues/4229) — asset paths not respecting base
- [Astro CSS url() base path issue #14585](https://github.com/withastro/astro/issues/14585) — dev/build inconsistency
- [Astro Sharp build issue #9345](https://github.com/withastro/astro/issues/9345) — Sharp 0.33.0 build failures
- [GitHub Pages + Cloudflare OG issue](https://community.cloudflare.com/t/github-pages-with-cloudflare-results-in-no-open-graph-data/519891) — OG tags stripped by proxy
- [Codecademy portfolio guide](https://www.codecademy.com/resources/blog/software-developer-portfolio-tips) — 87% hiring managers value portfolios stat

### Aggregated from Research Files
All sources documented in STACK.md (49 lines), FEATURES.md (13 lines), ARCHITECTURE.md (8 lines), and PITFALLS.md (24 lines) are incorporated by reference.

---
*Research completed: 2026-02-13*
*Ready for roadmap: yes*
