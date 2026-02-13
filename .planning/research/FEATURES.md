# Feature Landscape: Project Showcase Site

**Domain:** Marketing-forward GitHub Pages showcase site for a technical portfolio project
**Researched:** 2026-02-13
**Overall confidence:** HIGH (patterns derived from analysis of Tailwind CSS, Astro, Supabase, shadcn/ui, Cal.com homepages plus recruiter/hiring manager research)

## Context

JobFlow is a shipped 18K LOC Python project with 581 tests across 3 milestones. The showcase site is not the product itself -- it is a marketing surface that presents the product to recruiters, hiring managers, and fellow engineers. The audience is someone who lands on this page from a resume link or GitHub profile and needs to understand in 30 seconds: "This person built something serious."

---

## Table Stakes

Features visitors expect on a polished project showcase. Missing = the site feels amateur or incomplete, undermining the "serious engineer" signal.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Hero section with value proposition** | First thing visitors see. Must communicate what JobFlow does and why it matters in under 8 seconds. Headline + subheadline + primary CTA (e.g., "View on GitHub"). Every reference site (Tailwind, Astro, Supabase, shadcn/ui) leads with this. | Low | Copywriting | One sentence: what it is. One sentence: why it matters. Do NOT write a paragraph. |
| **Feature overview section** | Visitors need to understand capabilities at a glance. Grid or card layout showing 6-8 core features with icons and one-line descriptions. Standard on every project site studied. | Low | Icon set, feature copy | Group into logical categories: Discovery, Intelligence, Dashboard, Automation |
| **Screenshots / visual proof** | 87% of hiring managers consider portfolios more valuable than resumes when evaluating technical skills -- but only when they can SEE the work. Screenshots of the dashboard, kanban board, analytics, SSE streaming in action. | Medium | Must capture high-quality screenshots of all major UI surfaces | This is the single highest-impact content dependency. Without screenshots the site is just claims. |
| **Architecture / system diagram** | Engineers and technical hiring managers want to understand how the system is structured. A clean diagram showing the pipeline flow (scrape -> score -> dashboard -> apply) and component boundaries. | Medium | Create diagram (Excalidraw, Mermaid, or hand-drawn SVG) | One diagram, not five. Show the full pipeline at a high level. |
| **Tech stack section** | Visitors want to know what technologies you chose and that you can articulate why. List with logos/icons: Python, Playwright, FastAPI, SQLite, htmx, Claude CLI, etc. | Low | Tech logos/icons | Keep it scannable. Logo + name + one-word role (e.g., "FastAPI -- API & Dashboard") |
| **Quality signals / badges** | Build passing, test count, coverage percentage, lines of code. These are the "at a glance" credibility indicators. Shields.io badges are the standard. Projects without them look unfinished. | Low | CI pipeline already exists, shields.io badge URLs | Place prominently near hero or in a dedicated stats bar. 581 tests, 80%+ coverage, 18K LOC are strong numbers. |
| **Stats / metrics bar** | Concrete numbers create instant credibility: "18K lines of code", "581 tests", "3 platforms", "80%+ coverage", "Built in 3 days". Supabase and Astro both use prominent metric sections. | Low | Accurate project stats | Use large typography. Numbers are more persuasive than prose. |
| **GitHub link (prominent)** | The entire point is driving viewers to the repo. Must be unmissable -- in the nav, in the hero CTA, in the footer. GitHub Pages sites without prominent repo links are suspicious. | Low | GitHub repo URL | Primary CTA should be "View Source on GitHub", not a generic button |
| **Responsive design** | Recruiters often view on mobile (from email links). A showcase site that breaks on mobile is disqualifying. | Low | Standard CSS | Use modern CSS (Grid, Container Queries). No need for a framework -- this is a static single page. |
| **Dark mode support** | Expected on developer-facing sites in 2026. Every reference site studied supports it. Tailwind CSS, shadcn/ui, and Astro all default to dark. Absence feels dated. | Low-Med | CSS custom properties, prefers-color-scheme media query | Default to dark (developer audience). Toggle optional but nice. |
| **Clean typography and spacing** | The site IS the portfolio piece. If the CSS is sloppy, visitors question the code quality. Professional font pairing, consistent spacing, readable line lengths. | Low | Font selection (Inter or similar) | This is a showcase of engineering quality. The site's own code is part of the portfolio. |
| **Footer with contact/links** | GitHub, LinkedIn, email. Standard navigation element. Missing = dead end. | Low | Personal links | Keep minimal. Not a full "about me" -- this is a project page. |

## Differentiators

Features that elevate the showcase from "adequate project page" to "this person clearly knows what they're doing." Not expected, but valued -- especially by engineering peers.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Animated terminal / pipeline demo** | Show the CLI pipeline running with a typing animation effect. Simulates `python orchestrator.py` output showing phases executing. This is the "live demo" equivalent for a CLI tool. Libraries like typed.js make this straightforward. Immediately signals "this actually works" without requiring visitors to install anything. | Medium | Script the terminal output, typed.js or custom JS | Most impactful differentiator. A 15-second animation showing the pipeline phases (Setup -> Login -> Search -> Score -> Apply) with realistic output counts is worth more than 500 words of description. |
| **Before/after narrative** | "Without JobFlow: 2 hours/day on job boards. With JobFlow: 19 scored matches delivered to your dashboard overnight." Concrete problem -> solution framing. Supabase does this well ("Build in a weekend, scale to millions"). | Low | Copywriting | Frame around the pain point: manual job searching is tedious, repetitive, and error-prone. |
| **Interactive architecture diagram** | Hover/click on pipeline stages to see details about each component. Transforms a static diagram into an explorable system overview. Shows the engineer thinks about UX even for documentation. | Medium-High | SVG with JS interactions, or CSS-only hover states | Can be done with pure CSS hover states on an SVG -- no framework needed. Fall back to static diagram if time-constrained. |
| **Code snippets with syntax highlighting** | Show 2-3 carefully chosen code samples: the `@register_platform` decorator pattern, a Pydantic model, the scoring engine. Demonstrates code quality directly. Tailwind CSS uses code examples extensively and effectively. | Low-Med | Prism.js or highlight.js, curated code samples | Choose snippets that show design decisions, not boilerplate. The platform Protocol + decorator registry is ideal -- it shows extensibility thinking. |
| **"How it works" walkthrough** | 4-5 step visual walkthrough: Configure -> Discover -> Score -> Review -> Apply. Each step with a screenshot or illustration and 1-2 sentences. Astro and Tailwind both structure their homepages around "how it works" narratives. | Medium | Screenshots of each pipeline stage | This is more persuasive than a feature grid because it tells a story. |
| **Milestone timeline / build narrative** | "v1.0: MVP in 1 day. v1.1: 428 tests + CI. v1.2: Claude CLI integration." Shows velocity, iteration discipline, and growing sophistication. This is uniquely powerful for a portfolio piece -- it demonstrates engineering process, not just output. | Low | Milestone data (already documented in MILESTONES.md) | Use a visual timeline. Include stats per milestone. The "built in 1 day" fact for v1.0 is extraordinary and should be highlighted. |
| **Scroll-triggered animations** | Sections fade/slide in as the visitor scrolls. Subtle motion signals polish. Can be done with CSS `@scroll-timeline` or IntersectionObserver + CSS classes. No library needed. | Low-Med | IntersectionObserver JS (~20 lines) | Keep animations subtle and fast (200-300ms). Aggressive animation feels like a template, not a serious project. |
| **Performance metrics** | Lighthouse score badge, page weight, load time. A showcase site that itself scores 100/100 on Lighthouse demonstrates front-end competency even though the main project is Python. | Low | Run Lighthouse after deployment | Target: 100 Performance, 100 Accessibility, 100 Best Practices, 100 SEO. Achievable for a static site with no framework. |
| **Comparison table vs manual process** | Feature matrix: Manual Job Search vs JobFlow. Rows: time spent, jobs reviewed, match quality, resume customization, application tracking. Makes the value proposition concrete and scannable. | Low | Content creation | Effective for non-technical viewers (recruiters) who may not appreciate the architecture. |

## Anti-Features

Features to explicitly NOT build. These either waste time, undermine credibility, or distract from the goal.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Live demo / hosted instance** | JobFlow requires credentials (Indeed login, Claude CLI auth). A live demo is either fake (undermines trust) or a security nightmare. Interactive demos grew 35% in 2025 for SaaS, but this is a personal tool, not SaaS. | Use animated terminal demo + screenshots + video walkthrough instead. Show the tool working without exposing real credentials. |
| **Blog / content section** | This is a project showcase, not a personal site. A blog with 1-2 posts looks abandoned. Content maintenance is a liability. | Link to the GitHub repo's README and docs. If you write about the project, do it on your actual blog or dev.to. |
| **Pricing / signup / waitlist** | JobFlow is a personal tool, not a product. Any commercial framing is misleading and confusing. | "View Source on GitHub" as the primary CTA. Self-hosted, open-source framing. |
| **Complex JavaScript framework** | React/Vue/Svelte for a single static page is overkill. Adds bundle size, build complexity, and signals poor judgment about tool selection. The site itself is a code sample. | Plain HTML + CSS + minimal vanilla JS. Maybe a static site generator (Astro, 11ty) if multi-page, but a single-page showcase needs no framework. |
| **Testimonials / social proof from users** | This is a personal project. Fake testimonials are obviously fake. "Used by 0 companies" is not social proof. | Use quality signals instead: test count, coverage, LOC, build status, milestone velocity. These are verifiable and more credible than quotes. |
| **Newsletter / email capture** | No audience to nurture. An email form on a portfolio project page looks desperate. | GitHub stars and repo follows are the natural engagement mechanism. |
| **Multi-page site** | Unnecessary complexity. Recruiters will not click through 5 pages. Everything should be visible in one scroll. | Single-page with smooth scroll navigation to sections. Anchor links in the nav. |
| **Heavy animations / parallax** | Looks like a template. Undermines the "serious engineer" signal. Motion should be functional (draw attention to key content), not decorative. | Subtle scroll-triggered fades. One animated terminal demo. That's it. |
| **ChatGPT / AI chatbot widget** | Trendy but useless on a project showcase. What would it answer? It's a gimmick. | Clear, well-written copy that answers questions before they're asked. |
| **Video auto-play** | Jarring UX. Slows page load. Often blocked by browsers. | Optional video with play button, or animated terminal demo that runs on scroll-into-view. |

## Feature Dependencies

```
Screenshots (capture) --> Hero section (needs hero image)
Screenshots (capture) --> Feature overview (needs feature illustrations)
Screenshots (capture) --> "How it works" walkthrough (needs stage screenshots)
Architecture diagram (create) --> Architecture section
Terminal output script --> Animated terminal demo
Copywriting (headline, subheadline, feature descriptions) --> Every text section
Tech logos/icons --> Tech stack section
CI badges (shields.io URLs) --> Quality signals section
Milestone data (from MILESTONES.md) --> Timeline section
Code snippet selection --> Code examples section
```

**Critical path:** Screenshots and copywriting block the most sections. The animated terminal demo and architecture diagram can be built in parallel.

## Content Assets Required (Pre-Build)

These must exist BEFORE the site can be built. They are the primary constraint.

| Asset | Description | Effort | Blocking |
|-------|-------------|--------|----------|
| Dashboard screenshot (light + dark) | Main job listing view with data | 15 min | Hero, Features |
| Kanban board screenshot | Drag-and-drop board with jobs in multiple columns | 15 min | Features, How it works |
| Analytics screenshot | Chart.js charts with meaningful data | 15 min | Features |
| SSE streaming screenshot or GIF | Resume/cover letter generation with progress events visible | 30 min | Features, differentiator |
| Terminal pipeline output | Real or representative CLI output from `python orchestrator.py` | 15 min | Terminal demo |
| Architecture diagram | Pipeline flow diagram (Excalidraw or Mermaid) | 45 min | Architecture section |
| Feature copy | Headline, subheadline, 8 feature descriptions, comparison table | 60 min | Every section |
| Code snippets (2-3) | Platform protocol, scoring engine, decorator registry | 30 min | Code examples section |

**Total content prep estimate:** ~4 hours before any HTML is written.

## MVP Recommendation

Build in this order, stopping when time runs out. Each tier is independently shippable.

### Tier 1: Credible Project Page (minimum viable showcase)
1. **Hero section** with headline, subheadline, GitHub CTA, and one dashboard screenshot
2. **Stats bar** (18K LOC, 581 tests, 80%+ coverage, 3 platforms)
3. **Feature grid** (6-8 features with icons and one-liners)
4. **Tech stack row** (logos + names)
5. **Footer** with GitHub + LinkedIn + email

**Why this first:** Gets a professional page live. Every section after this is incremental improvement.

### Tier 2: Engineering Depth (what impresses technical viewers)
6. **Architecture diagram** section
7. **Code snippets** section (2-3 examples with syntax highlighting)
8. **Milestone timeline** (v1.0 -> v1.1 -> v1.2 with stats)
9. **Quality badges** (Shields.io build, coverage, Python version)

**Why this second:** Adds the technical depth that differentiates from "template portfolio page." The milestone timeline in particular is unique to this project and tells the build story.

### Tier 3: Polish and Delight (what makes it memorable)
10. **Animated terminal demo** (typed.js pipeline simulation)
11. **"How it works" walkthrough** (5-step visual narrative)
12. **Dark mode toggle**
13. **Scroll-triggered section animations**
14. **Before/after comparison** or comparison table

**Why this last:** These are differentiators, not requirements. A site with Tiers 1+2 is already strong. Tier 3 makes it outstanding.

### Defer Indefinitely
- Live demo / hosted instance
- Blog / content section
- Multi-page structure
- Video production
- Any JavaScript framework

## Audience-Specific Value

| Audience | What They Care About | Key Sections |
|----------|---------------------|--------------|
| **Recruiters** (non-technical) | "Is this impressive? Does it look professional? Can I understand what it does?" | Hero, stats bar, comparison table, screenshots |
| **Hiring managers** (semi-technical) | "Did they build something real? How complex is it? Do they ship?" | Feature grid, milestone timeline, stats bar, architecture diagram |
| **Engineering peers** (technical) | "Is the code good? Are the design decisions sound? Would I want to work with this person?" | Code snippets, architecture diagram, tech stack, test coverage, platform protocol pattern |
| **Themselves** (future reference) | "I can point anyone to this link and they'll understand what I built." | Everything -- the site is the canonical description of the project |

## Sources

- Tailwind CSS homepage analysis (https://tailwindcss.com/) -- sections, code examples, feature grid patterns [HIGH confidence, direct analysis]
- Astro homepage analysis (https://astro.build/) -- stats, social proof, CTA patterns [HIGH confidence, direct analysis]
- shadcn/ui homepage analysis (https://ui.shadcn.com/) -- dashboard preview, component demo patterns [HIGH confidence, direct analysis]
- Supabase hero section pattern (https://supabase.com/) -- "Build in a weekend, Scale to millions" value prop structure [HIGH confidence, direct analysis]
- typed.js terminal animation library (https://github.com/mattboldt/typed.js) -- animated terminal demo implementation [HIGH confidence, well-established library]
- Shields.io badge service (https://shields.io/) -- quality signal badges [HIGH confidence, industry standard]
- GitHub community discussion on portfolio engagement (https://github.com/orgs/community/discussions/169760) -- 40% engagement increase from personal sites [MEDIUM confidence, community data]
- Final Round AI article on GitHub as portfolio (https://www.finalroundai.com/articles/github-developer-portfolio) -- recruiter preferences, quality signals [MEDIUM confidence, single source]
- Codecademy portfolio guide (https://www.codecademy.com/resources/blog/software-developer-portfolio-tips) -- 87% hiring managers value portfolios over resumes [MEDIUM confidence, single source]
- TODO Group guide on marketing open source projects (https://todogroup.org/resources/guides/marketing-open-source-projects/) -- authentic presentation patterns [MEDIUM confidence]
