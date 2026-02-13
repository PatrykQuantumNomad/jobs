# Domain Pitfalls: Adding an Astro Showcase Site to an Existing Python Repo with GitHub Pages Deployment

**Domain:** Adding a marketing-forward GitHub Pages showcase site (Astro in `/site` subfolder) to an existing Python job search automation repository
**Researched:** 2026-02-13
**Confidence:** HIGH (grounded in Astro official deploy docs, GitHub Pages documentation, verified GitHub issues for base path bugs, Evil Martians devtool landing page study, and analysis of existing repo structure)

---

## Critical Pitfalls

Mistakes that cause broken deployments, invisible pages, or require structural rework.

---

### Pitfall 1: Base Path Misconfiguration Breaks Every Asset, Link, and Image on the Deployed Site

**What goes wrong:** GitHub Pages project sites serve from `https://username.github.io/repo-name/`, not from root. Astro generates all asset URLs relative to `/` by default. Without configuring `base: '/repo-name'` in `astro.config.mjs`, the deployed site loads a blank page -- CSS, JavaScript, images, and internal links all 404 because they resolve to `https://username.github.io/style.css` instead of `https://username.github.io/repo-name/style.css`.

This is the single most reported issue when deploying Astro to GitHub Pages as a project site. The Astro docs explicitly state: "Set a value for `base` that specifies the repository for your website so that Astro understands your website's root is `/my-repo` rather than the default `/`."

The insidious part: **everything works perfectly in local development** (`astro dev` serves from `/`), so this only breaks in production. The developer builds locally, sees a beautiful site, pushes, and gets a white page.

Additionally, `base` only affects Astro-generated paths. Static assets referenced with absolute paths in your templates (`/images/hero.png`) are NOT automatically prefixed. You must use `import.meta.env.BASE_URL` or relative paths for every asset reference.

**Why it happens:** Astro's development server always serves from root (`localhost:4321/`). The `base` config only takes effect during build. There is no development-time simulation of the base path, so the mismatch is invisible until deployment.

**Consequences:**
- Deployed site is a blank white page (no CSS/JS loads)
- Images show broken icons
- Internal navigation links go to 404 pages
- OG images in social shares point to non-existent URLs
- Developer wastes a deploy cycle debugging what looks like a build failure but is a config issue

**Prevention:**
1. Set `base` in `astro.config.mjs` from the very first commit:
   ```javascript
   export default defineConfig({
     site: 'https://patrykattc.github.io',
     base: '/jobs',
   });
   ```

2. Never use absolute paths for static assets. Always use `import.meta.env.BASE_URL`:
   ```astro
   <img src={`${import.meta.env.BASE_URL}images/screenshot.png`} alt="Dashboard" />
   ```
   Or import images through Astro's asset pipeline (preferred -- handles optimization too):
   ```astro
   import heroImage from '../assets/hero.png';
   <Image src={heroImage} alt="Dashboard screenshot" />
   ```

3. For internal links, always prefix with base:
   ```astro
   <a href={`${import.meta.env.BASE_URL}features/`}>Features</a>
   ```
   Or use Astro's built-in link handling which respects `base` automatically.

4. Add a `preview` script that simulates the base path locally. Use `astro preview` after building, which serves the built output with the base path applied -- this catches base path issues before deploying.

5. Add `astro-link-validator` integration to catch broken links at build time:
   ```bash
   npm install astro-link-validator
   ```

**Detection (warning signs):**
- Site looks perfect in `astro dev` but blank after deployment
- Browser DevTools Network tab shows 404s for CSS/JS files
- `astro preview` works but `astro dev` shows different behavior
- Images load in dev but break in production

**Phase:** Project setup (first phase). The `base` config must be correct before any content or design work begins. Every template and component authored without `base` consideration will need fixing later.

**Confidence:** HIGH -- verified against [Astro GitHub Pages deployment docs](https://docs.astro.build/en/guides/deploy/github/), [Astro base path issue #4229](https://github.com/withastro/astro/issues/4229), and [Astro image asset path issue #6504](https://github.com/withastro/astro/issues/6504).

---

### Pitfall 2: Custom Domain Later Makes Base Path a Liability -- Design for Both or Pick One

**What goes wrong:** The project starts with `base: '/jobs'` for the GitHub Pages project site URL (`patrykattc.github.io/jobs`). Later, you decide to add a custom domain (e.g., `jobflow.patrykgolabek.dev`). With a custom domain, the site serves from root -- `base` must be removed or set to `'/'`. But every template, every image reference, every internal link was written with the base path prefix. Removing `base` breaks all the `import.meta.env.BASE_URL` references that now resolve to `/` instead of `/jobs/`.

The two configurations are mutually exclusive:
- **Project site:** `site: 'https://patrykattc.github.io'`, `base: '/jobs'`
- **Custom domain:** `site: 'https://jobflow.patrykgolabek.dev'`, no `base` (or `base: '/'`)

Switching between them requires changing `astro.config.mjs` AND verifying that no template has hardcoded `/jobs/` in any URL. If you later want to support both (project path AND custom domain), there is no clean solution -- you deploy two builds or pick one.

**Why it happens:** GitHub Pages project sites and custom domain sites have fundamentally different URL structures. The `base` config is a global setting that affects every generated URL. There is no "auto-detect" mode.

**Consequences:**
- Migration from project path to custom domain breaks all internal links
- Hardcoded base paths in templates survive the config change and create broken URLs
- OG meta tags, sitemap, canonical URLs all point to wrong domain
- If you add a custom domain via GitHub settings without updating astro config, the CNAME file overwrites your deploy and serves a broken site

**Prevention:**
1. **Decide now:** If a custom domain is likely within 6 months, skip the base path entirely and start with the custom domain from day one. Add a CNAME file in `site/public/CNAME` with the domain.

2. If starting with the project path (recommended for MVP -- no DNS setup needed), enforce discipline:
   - NEVER hardcode `/jobs/` in any template. Always use `import.meta.env.BASE_URL`.
   - Use Astro's `<Image>` component for images (path resolution is automatic).
   - Use relative links where possible (they are base-agnostic).

3. Add a build-time check that greps for hardcoded base paths:
   ```bash
   # In CI or pre-build script
   if grep -r '"/jobs/' site/src/ --include="*.astro" --include="*.tsx"; then
     echo "ERROR: Hardcoded base path found. Use import.meta.env.BASE_URL instead."
     exit 1
   fi
   ```

4. Document the config switch procedure in the site README so the custom domain migration is a known, planned operation.

**Detection (warning signs):**
- Templates contain literal `/jobs/` instead of `BASE_URL` references
- Someone adds a CNAME in GitHub repo settings without updating astro config
- Links work on the project site but would break if base were removed

**Phase:** Project setup (first phase). This is an architectural decision, not a code decision. Pick a strategy and document it before writing any templates.

**Confidence:** HIGH -- verified against [Astro GitHub Pages deploy docs](https://docs.astro.build/en/guides/deploy/github/) which explicitly distinguish project site vs. custom domain configuration and state "Do not set a value for `base`" when using a custom domain.

---

### Pitfall 3: GitHub Actions Workflow Conflicts -- Two Workflows, One Pages Deployment Target

**What goes wrong:** The repo already has `.github/workflows/ci.yml` for Python CI (lint, test, coverage). Adding a deploy workflow for the Astro site creates a second workflow that also triggers on push to `main`. If both workflows try to deploy to GitHub Pages (unlikely but possible through misconfiguration), or if the Pages deployment workflow fails and blocks the CI workflow (due to concurrency groups), the development flow breaks.

More concretely: the `withastro/action@v5` workflow requires specific GitHub Pages permissions (`pages: write`, `id-token: write`) and the GitHub Pages source must be set to "GitHub Actions" in repo settings (not "Deploy from branch"). Changing this setting affects ALL workflows in the repo. If someone accidentally configures the CI workflow with Pages permissions or the deploy workflow triggers on PRs (not just main), PRs will attempt to deploy preview builds that overwrite production.

The `withastro/action@v5` also needs a `path` parameter pointing to the `/site` subfolder. If this is missing or wrong, it tries to build from the repo root (which has `pyproject.toml`, not `package.json`) and fails with a confusing npm/node error.

**Why it happens:** GitHub Pages is a repo-level setting with a single deployment target. Multiple workflows can interact with it. The Astro deploy action assumes the project is at the repo root by default.

**Consequences:**
- CI workflow runs on PRs that also trigger (and fail) the Pages deploy
- Deploy workflow tries to build from repo root, fails with "no package.json found"
- Pages deployment source setting change breaks expectations for the CI workflow
- Concurrent pushes to main cause deploy race conditions

**Prevention:**
1. Name the deploy workflow clearly and restrict triggers:
   ```yaml
   # .github/workflows/deploy-site.yml
   name: Deploy Site
   on:
     push:
       branches: [main]
       paths:
         - 'site/**'  # Only trigger when site files change
     workflow_dispatch: {}  # Manual trigger for debugging
   ```

2. Use `withastro/action@v5` with the `path` parameter:
   ```yaml
   - uses: withastro/action@v5
     with:
       path: ./site
   ```

3. Add a concurrency group specific to Pages deployment to prevent race conditions:
   ```yaml
   concurrency:
     group: pages
     cancel-in-progress: false  # Don't cancel in-progress deploys
   ```

4. Do NOT add `paths` filter to the existing CI workflow -- Python tests should still run on every push. Only the deploy workflow should be path-filtered.

5. Set GitHub Pages source to "GitHub Actions" in repo settings ONCE, and document this in the project README.

**Detection (warning signs):**
- Deploy workflow fails with "Cannot find module" or "package.json not found"
- CI workflow shows Pages-related permission warnings
- Every Python code change triggers a site rebuild
- PRs show a "Deploy Site" check that fails

**Phase:** CI/CD setup phase. The workflow file should be committed alongside the initial Astro project scaffold.

**Confidence:** HIGH -- verified against [withastro/action GitHub repo](https://github.com/withastro/action) which documents the `path` parameter for monorepo use, and [GitHub Pages custom workflows docs](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

---

## Moderate Pitfalls

Mistakes that cause degraded UX, SEO problems, or wasted development time.

---

### Pitfall 4: Trailing Slash Behavior on GitHub Pages Causes Silent 301 Redirects and Performance Degradation

**What goes wrong:** GitHub Pages redirects URLs without trailing slashes to URLs with trailing slashes. Visiting `patrykattc.github.io/jobs/features` triggers a 301 redirect to `patrykattc.github.io/jobs/features/`. This redirect adds 15-80ms per navigation (measured: 20% overhead in good network conditions, up to 60% on 3G/4G). If your Astro config uses `trailingSlash: 'never'` (Astro's default), every internal link generates URLs WITHOUT trailing slashes, and every single page navigation incurs this redirect penalty.

**Why it happens:** GitHub Pages serves static files from directories. When a URL like `/features` maps to a directory `/features/index.html`, the server redirects to `/features/` before serving the file. Astro's default `trailingSlash: 'ignore'` doesn't prevent this -- it just means Astro doesn't care, but GitHub Pages does.

**Consequences:**
- Every page navigation is 15-80ms slower due to 301 redirect
- Lighthouse performance scores are reduced
- Cumulative effect on multi-page visits is significant (5 pages = 75-400ms wasted)
- SEO crawlers see redirect chains as a minor negative signal

**Prevention:**
1. Set `trailingSlash: 'always'` in `astro.config.mjs`:
   ```javascript
   export default defineConfig({
     site: 'https://patrykattc.github.io',
     base: '/jobs',
     trailingSlash: 'always',
   });
   ```

2. Ensure all internal links include trailing slashes. Astro will enforce this at build time when `trailingSlash: 'always'` is set.

3. Test with `astro preview` (not `astro dev`) to verify trailing slash behavior matches production.

**Detection (warning signs):**
- Browser DevTools Network tab shows 301 redirects on every page navigation
- Lighthouse flags "Avoid multiple page redirects" in performance audit
- Page transitions feel slightly sluggish compared to local development

**Phase:** Project setup. Set `trailingSlash: 'always'` in the initial config alongside `base` and `site`.

**Confidence:** HIGH -- verified by [detailed analysis at justoffbyone.com](https://justoffbyone.com/posts/trailing-slash-tax/) which measured the specific performance impact, and confirmed against [Astro trailing slash config docs](https://docs.astro.build/en/reference/configuration-reference/).

---

### Pitfall 5: Missing or Incorrect OG Meta Tags Make Social Shares Show Generic Previews

**What goes wrong:** Someone shares the JobFlow showcase page on LinkedIn, Twitter/X, or Discord. Instead of showing a branded preview card with a title, description, and image, the share shows a generic link or pulls random text from the page. This happens because:

1. `og:image` requires an **absolute URL** (e.g., `https://patrykattc.github.io/jobs/og-image.png`). A relative path like `/og-image.png` is ignored by social crawlers.
2. `og:url` must match the canonical URL. If `og:url` says `https://patrykattc.github.io/og-image.png` (missing `/jobs/` base path), crawlers fetch the wrong URL.
3. The `og:image` dimensions matter: Twitter/X requires at least 300x157px, LinkedIn recommends 1200x627px. An image that is too small is ignored.
4. OG tags must be in the static HTML. If they are injected by client-side JavaScript, social crawlers will not see them. (Astro SSG renders them statically, so this is fine -- but worth knowing.)

For GitHub Pages specifically: users have reported that [GitHub Pages with Cloudflare](https://community.cloudflare.com/t/github-pages-with-cloudflare-results-in-no-open-graph-data/519891) sometimes strips OG data. If Cloudflare is in the path (for the personal domain), OG tags may not be visible to crawlers.

**Why it happens:** Social media crawlers are extremely literal about URL resolution. They do not follow base paths, relative URLs, or redirects the way browsers do. The `og:image` must be a fully qualified, directly accessible URL that returns an image.

**Consequences:**
- Social shares show no image or wrong image -- significantly reduces click-through rate
- The og:url mismatch causes share counts to split between two URLs (with and without base path)
- Twitter/X Cards validator shows errors, preventing rich card rendering
- First impressions of the project on social media are unprofessional

**Prevention:**
1. Use `Astro.site` (which includes the full URL with base) for all OG URLs:
   ```astro
   ---
   const ogImageUrl = new URL('/jobs/og-image.png', Astro.site).href;
   const canonicalUrl = new URL(Astro.url.pathname, Astro.site).href;
   ---
   <meta property="og:image" content={ogImageUrl} />
   <meta property="og:url" content={canonicalUrl} />
   <link rel="canonical" href={canonicalUrl} />
   ```

2. Create a properly sized OG image (1200x630px) and place it in `site/public/` so it is served as a static asset.

3. Add all four required OG properties to every page: `og:title`, `og:type`, `og:image`, `og:url`.

4. Add Twitter Card meta tags alongside OG tags:
   ```html
   <meta name="twitter:card" content="summary_large_image" />
   <meta name="twitter:image" content={ogImageUrl} />
   ```

5. Validate OG tags after deployment using:
   - [Twitter Card Validator](https://cards-dev.twitter.com/validator)
   - [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
   - [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)

6. Add OG tag validation to the CI build step -- check that every HTML file in `dist/` has the required OG properties.

**Detection (warning signs):**
- Sharing the URL on Discord/Slack shows no preview card
- Twitter/X validator shows "card not found" errors
- OG image URL returns 404 when accessed directly
- `og:url` and `canonical` point to different URLs

**Phase:** Design/content phase. OG tags should be in the base layout template from the start, not added as an afterthought.

**Confidence:** HIGH -- verified against [Open Graph Protocol specification](https://ogp.me/) and [GitHub Pages + Cloudflare OG issue](https://community.cloudflare.com/t/github-pages-with-cloudflare-results-in-no-open-graph-data/519891).

---

### Pitfall 6: Developer Tool Showcase Page That Reads Like Documentation Instead of a Landing Page

**What goes wrong:** A developer builds a showcase page for their project and fills it with technical details: architecture diagrams, API descriptions, config file examples, dependency lists. The page reads like a README rendered in HTML. Visitors (recruiters, hiring managers, other developers evaluating the project) land on the page, see a wall of text, and leave within 3 seconds without understanding what the project does or why it matters.

Evil Martians' [study of 100 devtool landing pages](https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025) found that effective pages share these patterns:
- **Centered hero** with big bold headline + supporting visual directly below
- **Action-focused copy** that goes into "how" not "why" (developers already know the problem)
- **Visual product proof** -- animated GIFs, screenshots, or video showing the actual UI
- **Breathing room** -- clean layout with max-width container, generous whitespace

Anti-patterns that kill developer landing pages:
- Feature lists without visual context
- Walls of text explaining the problem (developers know the problem)
- No screenshots or product visuals
- Burying the "what does it look like" below the fold
- Generic stock imagery instead of actual product UI

**Why it happens:** Developers default to explaining the technical "what" because that is what they know best. They write for themselves (someone who already understands the project) rather than for the visitor (someone encountering it for the first time).

**Consequences:**
- High bounce rate -- visitors leave without engaging
- Portfolio visitors (recruiters, hiring managers) don't understand the project's scope or quality
- The site adds no value over the GitHub README
- Time spent building the site is wasted if nobody engages with it

**Prevention:**
1. **Hero section formula:** One sentence explaining what JobFlow does + one sentence explaining why it matters + screenshot or GIF of the dashboard.

2. **Show, don't tell:** Replace every feature description with a screenshot or short GIF. "AI-powered resume tailoring" means nothing without showing the actual tailored resume output.

3. **Above the fold:** The visitor must see a product screenshot within the first viewport (no scrolling). If they have to scroll to see what the product looks like, most will leave.

4. **Limit text:** Each section should have a headline (5-8 words) and a subhead (1-2 sentences). No paragraphs. Use bullet points sparingly.

5. **CTA clarity:** The primary action is "View on GitHub." Make it prominent. Secondary: "Read the docs" or "See architecture."

6. **Mobile-first:** Over 50% of portfolio traffic comes from mobile (recruiters browsing on phones). Test on mobile FIRST, not as an afterthought.

**Detection (warning signs):**
- The page has more text than images
- No screenshot is visible without scrolling
- The hero section describes the tech stack instead of the user benefit
- The page takes more than 10 seconds to read from top to bottom (too long)
- Friends/colleagues say "looks cool but what does it actually do?"

**Phase:** Content/design phase. Write content BEFORE building templates. The content structure drives the component structure, not the other way around.

**Confidence:** HIGH -- based on [Evil Martians' 100 devtool landing page study](https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025) and standard landing page best practices.

---

### Pitfall 7: Node.js Tooling Pollution in a Python-First Repository

**What goes wrong:** Adding Astro to `/site` introduces `package.json`, `package-lock.json`, `node_modules/`, `astro.config.mjs`, `tsconfig.json`, and potentially `.npmrc` into a repo that is otherwise pure Python. Several things can go wrong:

1. **`.gitignore` missing `node_modules/`**: The current `.gitignore` has Python-specific entries but no Node.js entries. If `node_modules/` is not ignored, someone accidentally commits 200MB+ of Node dependencies.

2. **Root-level confusion**: Running `npm install` from the repo root (instead of `/site`) creates a `node_modules/` and `package-lock.json` in the root directory, polluting the Python project structure. This can happen when someone sees a `package.json` reference in CI and runs `npm install` from the wrong directory.

3. **IDE confusion**: VS Code and other editors may try to apply TypeScript/JavaScript linting rules to the Python files, or Python linting to Astro files. The root-level `.vscode/settings.json` may need workspace-specific overrides.

4. **`uv` / pip vs npm dependency confusion**: New contributors may not understand that the project has two dependency systems. Running `uv sync` installs Python deps; `npm install` in `/site` installs JS deps. Neither installs the other.

**Why it happens:** Most repos are single-language. Adding a second language ecosystem to a subfolder is a monorepo pattern that requires explicit boundary management.

**Consequences:**
- 200MB `node_modules/` committed to git (repo becomes uncloneable)
- Root-level `package-lock.json` from accidental `npm install` at wrong directory
- CI fails because it only installs Python deps, not Node deps (or vice versa)
- Contributors are confused about which commands to run where

**Prevention:**
1. Update `.gitignore` at repo root immediately:
   ```gitignore
   # Node.js (site/ subfolder)
   node_modules/
   site/dist/
   site/.astro/
   ```

2. Keep ALL Node.js files inside `/site`. No root-level `package.json`, no root-level `tsconfig.json`.

3. Add a `site/README.md` with clear setup instructions:
   ```markdown
   ## Site Development
   cd site && npm install && npm run dev
   ```

4. In CI, explicitly `cd site` before running Node.js commands. The `withastro/action@v5` handles this with the `path` parameter.

5. Add `/site` to the `.vscode/settings.json` exclude patterns for Python linting tools, and vice versa.

6. Commit `site/package-lock.json` to the repo (Astro deploy action requires it), but NEVER commit a root-level `package-lock.json`.

**Detection (warning signs):**
- `git status` shows 10,000+ new files (node_modules was added)
- Root directory has both `pyproject.toml` and `package.json`
- CI log shows "npm warn" or "package.json not found" errors
- `ruff` tries to lint `.astro` files

**Phase:** Project setup (first phase). Update `.gitignore` and establish the `/site` boundary before scaffolding the Astro project.

**Confidence:** HIGH -- standard monorepo hygiene, verified against [gitignore best practices for node_modules](https://www.geeksforgeeks.org/git/how-to-ignore-node_modules-folder-in-git/).

---

### Pitfall 8: Large Unoptimized Images Destroy Page Load Performance on GitHub Pages

**What goes wrong:** The showcase page features screenshots of the JobFlow dashboard, the Kanban board, the resume tailoring UI, etc. The developer takes full-resolution screenshots (2560x1600 on a Retina display) and drops them into the `/site/src/assets/` directory as PNGs. Each screenshot is 1-4MB. The page has 5-8 screenshots. Total page weight: 10-25MB. On a mobile connection, the page takes 15-30 seconds to load. Lighthouse performance score: 20/100.

GitHub Pages has a soft bandwidth limit of 100GB/month. If the page gets shared on HackerNews or Reddit and receives 10,000 visits, that is 100-250GB of bandwidth from images alone -- potentially triggering GitHub's fair use policy.

Astro has built-in image optimization via the `<Image>` component and Sharp, but Sharp has a history of build failures in CI environments ([withastro/astro#9345](https://github.com/withastro/astro/issues/9345), [withastro/astro#14531](https://github.com/withastro/astro/issues/14531)). If Sharp fails, Astro falls back to unoptimized images silently (or errors out, depending on configuration).

**Why it happens:** Screenshots from high-DPI displays are naturally large. Developers don't notice the file size because their local dev server loads instantly. The performance impact only becomes visible on real networks.

**Consequences:**
- Page loads in 15-30 seconds on mobile (visitors leave after 3)
- Lighthouse performance score below 50
- GitHub Pages bandwidth limit reached with moderate traffic
- Sharp build failure in CI causes either broken images or build errors

**Prevention:**
1. Use Astro's `<Image>` component for all images -- it generates WebP/AVIF versions at appropriate sizes:
   ```astro
   import { Image } from 'astro:assets';
   import dashboard from '../assets/dashboard.png';
   <Image src={dashboard} alt="Dashboard" width={800} format="webp" />
   ```

2. Pre-optimize screenshots before committing. Resize to max 1600px wide, compress to WebP:
   ```bash
   # Example with ImageMagick
   convert screenshot.png -resize 1600x -quality 85 screenshot.webp
   ```

3. Keep total image payload under 2MB for the entire page. Target: each image under 200KB.

4. Use lazy loading for below-the-fold images:
   ```astro
   <Image src={screenshot} alt="Feature" loading="lazy" />
   ```

5. Add Sharp as an explicit dependency in `site/package.json` to prevent the "missing Sharp" error:
   ```bash
   cd site && npm install sharp
   ```

6. If Sharp causes CI build failures, configure a passthrough image service as fallback:
   ```javascript
   // astro.config.mjs
   import { passthroughImageService } from 'astro/config';
   export default defineConfig({
     image: { service: passthroughImageService() },
   });
   ```
   But this means images are served unoptimized -- so pre-optimize them manually.

7. For animated demos, use GIFs sparingly (huge file size) or MP4 videos with `<video>` tags (much smaller).

**Detection (warning signs):**
- `ls -lh site/src/assets/` shows files over 500KB
- Lighthouse performance score below 70
- `astro build` takes unusually long (Sharp processing large images)
- CI build fails with "Could not find Sharp" error
- Page load exceeds 5 seconds on throttled network

**Phase:** Content/asset creation phase. Establish image optimization pipeline before adding screenshots to the site.

**Confidence:** HIGH -- verified against [Astro image docs](https://docs.astro.build/en/guides/images/), [Sharp missing error docs](https://docs.astro.build/en/reference/errors/missing-sharp/), and [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

---

## Minor Pitfalls

Mistakes that cause annoyance, confusion, or minor issues.

---

### Pitfall 9: CSS Dev/Build Inconsistency with Base Path in url() References

**What goes wrong:** CSS `url()` references (for fonts, background images) behave differently between `astro dev` and `astro build` when `base` is configured. In development, `url('/fonts/Inter.woff2')` works because there is no base path. In production build, Astro rewrites CSS `url()` paths to include the base, but the rewriting is inconsistent -- [Astro issue #14585](https://github.com/withastro/astro/issues/14585) documents cases where CSS `url()` is replaced to include base path during build but NOT during dev, causing fonts and backgrounds to load in production but 404 in development, or vice versa.

**Prevention:**
1. Use relative paths in CSS `url()` references where possible.
2. Import fonts and assets through Astro's asset pipeline rather than CSS `url()`.
3. Test with `astro preview` (which serves the built output) as the final check, not just `astro dev`.

**Phase:** Design/styling phase. Establish font and asset loading strategy early.

**Confidence:** MEDIUM -- documented in [Astro issue #14585](https://github.com/withastro/astro/issues/14585), behavior may be fixed in newer Astro versions.

---

### Pitfall 10: Forgetting to Commit package-lock.json Causes Non-Deterministic CI Builds

**What goes wrong:** The developer adds `site/package-lock.json` to `.gitignore` (thinking "lockfiles are generated"), or simply forgets to commit it. The Astro deploy action runs `npm ci` which REQUIRES `package-lock.json` to exist. Without it, the build falls back to `npm install` with potentially different dependency versions, or fails outright.

The Astro docs explicitly warn: "You should commit your package manager's automatically generated lockfile to your repository."

**Prevention:**
1. Commit `site/package-lock.json` to the repo.
2. Do NOT add `*.lock` or `package-lock.json` to `.gitignore`.
3. Use `npm ci` in CI workflows (which the Astro action does by default) to ensure deterministic installs.

**Phase:** Project setup. Commit the lockfile with the initial scaffold.

**Confidence:** HIGH -- [Astro deploy docs](https://docs.astro.build/en/guides/deploy/github/) explicitly state this requirement.

---

### Pitfall 11: 404 Page Not Working on GitHub Pages Project Sites

**What goes wrong:** Astro supports custom 404 pages via `src/pages/404.astro`. For GitHub Pages user sites (`username.github.io`), this works automatically -- GitHub serves `404.html` for unknown routes. But for project sites, the 404 page must be at the base path (`/jobs/404.html`), and GitHub Pages may not serve it correctly for routes within the project path. The user visits `patrykattc.github.io/jobs/nonexistent` and gets GitHub's default 404 page instead of the custom one.

**Prevention:**
1. Create `src/pages/404.astro` in the Astro project.
2. Test the 404 behavior after deployment by visiting a known-bad URL.
3. If the custom 404 doesn't work for project sites, add a client-side redirect in the layout that detects missing routes.

**Phase:** Polish phase. Not critical for initial launch but important for professional appearance.

**Confidence:** MEDIUM -- [Astro 404 + trailing slash issue #7616](https://github.com/withastro/astro/issues/7616) documents edge cases, but behavior may vary.

---

### Pitfall 12: Responsive Design Tested Only on Desktop

**What goes wrong:** The developer builds the showcase page on a large monitor, tweaks it until it looks great at 1440px+, and deploys. Recruiters and colleagues access it on mobile (phone or tablet) and see overlapping text, images that overflow the viewport, horizontal scroll, or text too small to read. Given that portfolio/showcase links are often shared via LinkedIn (mobile app) or Slack (mobile), mobile traffic can be 40-60% of visits.

**Prevention:**
1. Use Tailwind/CSS responsive utilities from the start. Design mobile-first, enhance for desktop.
2. Test at 375px (iPhone SE), 390px (iPhone 14), 768px (iPad), and 1440px (desktop) during development.
3. Use `astro dev` and Chrome DevTools device toolbar throughout development, not just at the end.
4. Keep the layout simple: single-column on mobile, optionally two-column on desktop. Complex grids break on small screens.
5. Ensure touch targets (buttons, links) are at least 44x44px on mobile.

**Phase:** Design phase. Start with mobile wireframes before desktop.

**Confidence:** HIGH -- standard web development best practice, reinforced by Evil Martians study noting extensive responsive CSS requirements in successful devtool pages.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Project setup / scaffold | Base path not configured | CRITICAL | Set `base: '/jobs'` and `trailingSlash: 'always'` in initial config |
| Project setup / scaffold | `.gitignore` missing `node_modules/` | CRITICAL | Update root `.gitignore` before `npm install` |
| Project setup / scaffold | Lockfile not committed | MODERATE | Commit `site/package-lock.json` with initial scaffold |
| CI/CD setup | Deploy workflow missing `path: ./site` | CRITICAL | Use `withastro/action@v5` with explicit `path` parameter |
| CI/CD setup | Deploy triggers on every push, not just site changes | MODERATE | Add `paths: ['site/**']` filter to deploy workflow |
| CI/CD setup | Sharp build failure in GitHub Actions | MODERATE | Install Sharp explicitly or use passthrough image service |
| Content / asset creation | Unoptimized screenshots (>500KB each) | MODERATE | Pre-optimize to WebP, use Astro `<Image>` component |
| Content / design | Page reads like README, no product visuals | MODERATE | Hero screenshot above fold, show don't tell |
| Content / design | No responsive design testing | MODERATE | Mobile-first design, test at 375px minimum |
| OG / SEO | Missing or relative og:image URL | MODERATE | Use absolute URLs via `Astro.site`, validate with social debug tools |
| OG / SEO | og:url missing base path | MODERATE | Construct og:url from `Astro.site` + `Astro.url.pathname` |
| Custom domain migration | Hardcoded base paths in templates | MODERATE | Always use `import.meta.env.BASE_URL`, never literal `/jobs/` |
| Polish | Custom 404 not working for project path | MINOR | Test after deployment, add fallback if needed |
| Polish | CSS url() inconsistency with base path | MINOR | Use asset imports instead of CSS url() for fonts/images |

---

## Sources

### Verified (HIGH confidence)
- [Astro GitHub Pages Deploy Guide](https://docs.astro.build/en/guides/deploy/github/) -- base path, site config, custom domain, CNAME, lockfile requirement
- [Astro Configuration Reference](https://docs.astro.build/en/reference/configuration-reference/) -- trailingSlash, base, site options
- [Astro Images Documentation](https://docs.astro.build/en/guides/images/) -- Image component, Sharp, optimization
- [Astro Missing Sharp Error](https://docs.astro.build/en/reference/errors/missing-sharp/) -- Sharp installation, passthrough fallback
- [GitHub Pages Limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) -- 100GB bandwidth, 1GB repo, 10 builds/hour
- [GitHub Pages Custom Workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) -- Actions-based deployment
- [withastro/action GitHub repo](https://github.com/withastro/action) -- `path` parameter for monorepo builds
- [Open Graph Protocol specification](https://ogp.me/) -- required properties, URL requirements
- [Evil Martians: 100 Devtool Landing Pages Study](https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025) -- hero patterns, visual content, messaging

### Cross-referenced (MEDIUM confidence)
- [Trailing Slash Tax on GitHub Pages](https://justoffbyone.com/posts/trailing-slash-tax/) -- performance measurements (20-60% overhead)
- [Astro base path issue #4229](https://github.com/withastro/astro/issues/4229) -- asset paths not respecting base
- [Astro image asset path issue #6504](https://github.com/withastro/astro/issues/6504) -- image URLs not resolved with base
- [Astro CSS url() base path issue #14585](https://github.com/withastro/astro/issues/14585) -- dev/build inconsistency
- [Astro 404 + trailing slash issue #7616](https://github.com/withastro/astro/issues/7616) -- custom 404 edge cases
- [Astro Sharp build issue #9345](https://github.com/withastro/astro/issues/9345) -- Sharp 0.33.0 build failures
- [Astro Sharp Docker issue #14531](https://github.com/withastro/astro/issues/14531) -- Sharp missing in CI/Docker
- [Starlight base/site discussion #2158](https://github.com/withastro/starlight/discussions/2158) -- community confusion about base vs site
- [GitHub Pages + Cloudflare OG data issue](https://community.cloudflare.com/t/github-pages-with-cloudflare-results-in-no-open-graph-data/519891) -- OG tags stripped by proxy
- [Static assets with Astro base config](https://spuxx.dev/blog/2023/astro-assets-base/) -- BASE_URL workaround for static assets
- [Gitignore node_modules best practices](https://www.geeksforgeeks.org/git/how-to-ignore-node_modules-folder-in-git/) -- recursive ignore pattern
