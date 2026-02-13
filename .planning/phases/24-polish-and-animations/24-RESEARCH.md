# Phase 24: Polish and Animations - Research

**Researched:** 2026-02-13
**Domain:** Frontend animations, scroll behavior, terminal simulation (Astro 5 + Tailwind v4 + vanilla JS)
**Confidence:** HIGH

## Summary

Phase 24 adds three polish features to the existing Astro site: an animated terminal demo (PLSH-01), scroll-triggered fade-in animations (PLSH-02), and smooth scroll navigation from anchor links (PLSH-03). All three are achievable with zero external dependencies using IntersectionObserver, CSS transitions, and `scroll-behavior: smooth`.

The terminal demo is the most complex deliverable. Rather than importing a library like Termynal (~220 lines, unmaintained, last meaningful update years ago), a custom implementation of ~80-100 lines of JS achieves the exact same effect with full control over styling and timing. The output should simulate the actual `orchestrator.py` pipeline output (verified from source: Phase 0-4 print statements with realistic data). The terminal component should be a new Astro section placed between Hero and Stats, or embedded within the Hero section to replace the gradient placeholder in ScreenshotFrame.

Scroll-triggered animations are the simplest: a single IntersectionObserver script (~30 lines) that adds/removes a CSS class when sections enter the viewport, combined with CSS opacity/transform transitions. Must respect `prefers-reduced-motion`.

Smooth scrolling requires `scroll-behavior: smooth` on `html` (one CSS line) plus a nav bar with anchor links -- which does NOT currently exist on the site. PLSH-03 explicitly calls for "anchor links to page sections from nav bar," so a minimal sticky nav bar must be created as part of this phase.

**Primary recommendation:** Build all three features as vanilla JS in Astro `<script>` tags with CSS transitions. No libraries. Custom terminal demo with async/await typing. Sticky nav bar with 5-6 anchor links. IntersectionObserver for fade-ins. Total JS: ~150-200 lines across all features.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| IntersectionObserver API | Web API (Baseline) | Detect when sections enter viewport | Native browser API, no polyfill needed since 2019 |
| `scroll-behavior: smooth` | CSS (Baseline March 2022) | Smooth anchor scrolling | Zero-JS solution, widely supported |
| `async/await` | ES2017+ | Terminal typing animation sequencing | Clean sequential animation without callback chains |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS `@keyframes` | CSS3 | Cursor blink animation in terminal | Standard CSS animation for repeating effects |
| CSS `transition` | CSS3 | Fade-in/slide-up on scroll | Hardware-accelerated opacity + transform transitions |
| `prefers-reduced-motion` | Media Query (Baseline) | Accessibility: disable animations for motion-sensitive users | Always check before animating |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom terminal typing | Termynal.js (~220 lines, MIT) | Unmaintained, HTML-attribute API is convenient but inflexible for custom orchestrator output styling. Custom is ~80 lines for exact same effect with full control |
| Custom terminal typing | typed.js (11.4KB min) | Overkill -- designed for typing/backspacing text strings, not terminal output simulation. Also violates zero-JS-library constraint |
| IntersectionObserver | AOS (Animate on Scroll) | 14KB library for something achievable in 30 lines. Violates no-animation-library constraint |
| `scroll-behavior: smooth` | JavaScript `scrollIntoView({behavior: 'smooth'})` | More control over timing, but unnecessary complexity. CSS solution works perfectly for anchor links |
| `scroll-behavior: smooth` | smoothscroll-polyfill | Only needed for pre-2022 browsers, irrelevant in 2026 |

**Installation:**
```bash
# No packages to install -- all native browser APIs
```

## Architecture Patterns

### Recommended Project Structure
```
site/src/
├── components/
│   ├── sections/
│   │   └── TerminalDemo.astro    # New: animated terminal section
│   └── ui/
│       └── NavBar.astro          # New: sticky nav with anchor links
├── styles/
│   └── global.css                # Add scroll-behavior, fade-in transitions
└── pages/
    └── index.astro               # Add NavBar, TerminalDemo, data-animate attrs
```

### Pattern 1: IntersectionObserver Class Toggle for Fade-Ins
**What:** A single observer watches all elements with a `data-animate` attribute. When they enter the viewport, add a class that triggers CSS transitions.
**When to use:** Any element that should fade/slide in on scroll.
**Example:**
```javascript
// In a <script> tag (Astro-processed, runs once)
function initScrollAnimations() {
  const prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;
  if (prefersReducedMotion) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
          observer.unobserve(entry.target); // Once only
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
  );

  document.querySelectorAll('[data-animate]').forEach((el) => {
    observer.observe(el);
  });
}

initScrollAnimations();
document.addEventListener('astro:page-load', initScrollAnimations);
```

```css
/* In global.css */
[data-animate] {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}

[data-animate].animate-in {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  [data-animate] {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
```

### Pattern 2: Terminal Typing with async/await
**What:** Sequential line-by-line output with per-character typing for input lines and instant reveal for output lines.
**When to use:** The terminal demo section.
**Example:**
```javascript
async function typeTerminal(container) {
  const lines = container.querySelectorAll('[data-line]');
  for (const line of lines) {
    const type = line.dataset.line; // "input" | "output" | "progress"
    const text = line.dataset.text;
    const delay = parseInt(line.dataset.delay || '0', 10);

    if (delay) await wait(delay);

    if (type === 'input') {
      line.textContent = '';
      line.style.visibility = 'visible';
      for (const char of text) {
        line.textContent += char;
        await wait(30 + Math.random() * 40); // 30-70ms per char
      }
    } else {
      line.style.visibility = 'visible';
      line.textContent = text;
    }
  }
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
```

### Pattern 3: Astro Script Lifecycle with ClientRouter
**What:** Scripts that need to reinitialize after client-side navigation.
**When to use:** All animation scripts in this phase.
**Example:**
```javascript
// Pattern: init + lifecycle event listener
function init() { /* setup observers, animations */ }
init();
document.addEventListener('astro:page-load', init);
```
**Note:** `astro:page-load` fires on initial load AND after every client-side navigation. This replaces `DOMContentLoaded` when using ClientRouter. Do NOT use `data-astro-rerun` -- the `astro:page-load` pattern is the recommended approach per Astro docs.

### Pattern 4: Sticky Nav Bar with Scroll Spy (Optional Enhancement)
**What:** Fixed nav bar at top with links to section anchors, active state based on scroll position.
**When to use:** PLSH-03 requires nav bar with anchor links.
**Example:**
```html
<nav class="fixed top-0 left-0 right-0 z-40 bg-white/80 dark:bg-surface-950/80 backdrop-blur-sm border-b border-surface-200 dark:border-surface-800">
  <div class="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
    <span class="font-display font-bold text-surface-900 dark:text-surface-50">JobFlow</span>
    <div class="hidden md:flex items-center gap-6">
      <a href="#features" class="text-sm text-surface-600 dark:text-surface-300 hover:text-primary-600">Features</a>
      <a href="#architecture" class="text-sm text-surface-600 dark:text-surface-300 hover:text-primary-600">How It Works</a>
      <a href="#code" class="text-sm text-surface-600 dark:text-surface-300 hover:text-primary-600">Code</a>
      <a href="#timeline" class="text-sm text-surface-600 dark:text-surface-300 hover:text-primary-600">Timeline</a>
      <a href="#quickstart" class="text-sm text-surface-600 dark:text-surface-300 hover:text-primary-600">Quick Start</a>
    </div>
  </div>
</nav>
```

### Anti-Patterns to Avoid
- **Animating everything:** Only sections should fade in, not individual elements within sections. Over-animation looks like a template, not craftsmanship (per project constraints: "Heavy animations / parallax looks like a template")
- **Layout-triggering animations:** Never animate `width`, `height`, `top`, `left`. Only animate `opacity` and `transform` (GPU-accelerated, no layout recalculation)
- **Forgetting reduced motion:** Every animation must have a `prefers-reduced-motion: reduce` fallback that makes content immediately visible
- **Using `data-astro-rerun`:** This forces `is:inline` and prevents Astro from processing the script. Use `astro:page-load` lifecycle event instead
- **Terminal animation on every visit:** Use IntersectionObserver to start terminal animation only when scrolled into view, not on page load. Also consider a `data-animated` flag to prevent re-running if user scrolls away and back

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Smooth scrolling | Custom JS scroll animation with easing | `scroll-behavior: smooth` CSS property | Native, zero-JS, respected by all modern browsers. Custom JS adds 20-40 lines for identical effect |
| Viewport detection | Manual scroll event listener with `getBoundingClientRect()` | `IntersectionObserver` API | Scroll listeners fire 60+ times/sec causing jank. IO is async, batched, and GPU-friendly |
| Cursor blink | JavaScript `setInterval` toggle | CSS `@keyframes` animation | Pure CSS, no JS needed, hardware-accelerated |

**Key insight:** Every animation in this phase has a native CSS/browser API solution. The only JavaScript needed is: (1) IntersectionObserver setup (~30 lines), (2) terminal typing logic (~80 lines), (3) optional scroll spy for nav active state (~30 lines). Total: ~140 lines. Any library would add more weight than the custom code.

## Common Pitfalls

### Pitfall 1: Flash of Unanimated Content (FOUC)
**What goes wrong:** Elements with `opacity: 0` for scroll animation are invisible if JavaScript fails to load. User sees a blank page.
**Why it happens:** CSS sets initial state to invisible, but JavaScript never runs to reveal them.
**How to avoid:** Use `<noscript>` styles OR set initial state in CSS that works without JS: the `[data-animate]` selector only applies `opacity: 0` when a `.js-enabled` class is on `<html>`. The script adds this class immediately.
**Warning signs:** Blank sections visible during slow page load.

### Pitfall 2: Terminal Animation Replaying on Every Scroll
**What goes wrong:** User scrolls past terminal, scrolls back up, animation starts over from scratch.
**Why it happens:** IntersectionObserver fires every time element enters viewport.
**How to avoid:** Set a flag (`container.dataset.animated = 'true'`) after first play. Check flag in observer callback. Optionally: `observer.unobserve(container)` after first trigger.
**Warning signs:** Animation stuttering when scrolling up/down near the terminal section.

### Pitfall 3: Scroll-to Target Hidden Behind Fixed Nav
**What goes wrong:** Clicking "Features" in nav scrolls to `#features` but the section heading is hidden behind the fixed nav bar.
**Why it happens:** Anchor scroll targets the element's top edge, but the nav bar overlaps it.
**How to avoid:** Add `scroll-margin-top` to all section elements equal to nav bar height (e.g., `scroll-margin-top: 4rem`). This is a CSS-only fix, no JS needed.
**Warning signs:** Section headings not visible after clicking nav links.

### Pitfall 4: Animations Not Working After ClientRouter Navigation
**What goes wrong:** User navigates away and back (if site becomes multi-page in future), animations don't re-trigger.
**Why it happens:** Astro ClientRouter doesn't re-execute bundled scripts on soft navigation.
**How to avoid:** Use `astro:page-load` event listener pattern (documented in Pattern 3 above). This fires on both initial load and after every navigation.
**Warning signs:** Animations work on first visit but not after navigating back.

### Pitfall 5: Dark Mode Terminal Contrast
**What goes wrong:** Terminal looks fine in light mode but washed out or hard to read in dark mode.
**Why it happens:** Terminal backgrounds are typically dark. In dark mode, the surrounding page is also dark, reducing visual contrast between terminal and page.
**How to avoid:** Use a slightly different dark shade for terminal vs page background. Terminal: `bg-surface-950` with a subtle border. Or keep terminal always-dark regardless of theme (terminals are naturally dark).
**Warning signs:** Terminal section doesn't visually "pop" from surrounding content in dark mode.

### Pitfall 6: ThemeToggle Z-Index Conflict with NavBar
**What goes wrong:** The existing ThemeToggle (`fixed top-4 right-4 z-50`) overlaps or conflicts with a new fixed nav bar.
**Why it happens:** Both are fixed-position elements at the top of the page.
**How to avoid:** Move ThemeToggle INTO the nav bar component. Nav bar at z-40 contains the toggle. Remove the standalone fixed positioning from index.astro.
**Warning signs:** Toggle button overlapping nav bar text, or being hidden behind it.

## Code Examples

Verified patterns from official sources and codebase analysis:

### Terminal Demo Data (from orchestrator.py source)
```javascript
// Lines derived from actual orchestrator.py print statements
const terminalLines = [
  { type: 'input', text: '$ python orchestrator.py --platforms indeed remoteok', delay: 0 },
  { type: 'output', text: '============================================================', delay: 300 },
  { type: 'output', text: '  JOB SEARCH AUTOMATION PIPELINE', delay: 50 },
  { type: 'output', text: '============================================================', delay: 50 },
  { type: 'output', text: '', delay: 200 },
  { type: 'output', text: '[Phase 0] Environment Setup', delay: 300 },
  { type: 'output', text: '------------------------------------------------------------', delay: 50 },
  { type: 'output', text: '  Python 3.14.0', delay: 200 },
  { type: 'output', text: '  Credentials:', delay: 100 },
  { type: 'output', text: '    indeed    OK', delay: 150 },
  { type: 'output', text: '    remoteok  OK', delay: 150 },
  { type: 'output', text: '  Setup complete.', delay: 200 },
  { type: 'output', text: '', delay: 100 },
  { type: 'output', text: '[Phase 1] Platform Login', delay: 300 },
  { type: 'output', text: '------------------------------------------------------------', delay: 50 },
  { type: 'output', text: '  Indeed: logged in', delay: 800 },
  { type: 'output', text: '  RemoteOK: no login required', delay: 200 },
  { type: 'output', text: '', delay: 100 },
  { type: 'output', text: '[Phase 2] Job Search', delay: 300 },
  { type: 'output', text: '------------------------------------------------------------', delay: 50 },
  { type: 'output', text: '  Indeed: 22 jobs found', delay: 1200 },
  { type: 'output', text: '  RemoteOK: 91 jobs found', delay: 600 },
  { type: 'output', text: '', delay: 100 },
  { type: 'output', text: '[Phase 3] Scoring & Deduplication', delay: 300 },
  { type: 'output', text: '------------------------------------------------------------', delay: 50 },
  { type: 'output', text: '  Total raw jobs: 113', delay: 200 },
  { type: 'output', text: '  After dedup:    106', delay: 400 },
  { type: 'output', text: '  Score 3+:       19', delay: 600 },
  { type: 'output', text: '', delay: 100 },
  { type: 'output', text: '============================================================', delay: 300 },
  { type: 'output', text: '  PIPELINE COMPLETE', delay: 50 },
  { type: 'output', text: '============================================================', delay: 50 },
  { type: 'output', text: '  Total scored jobs (3+): 19', delay: 100 },
  { type: 'output', text: '  Score 5: 3  |  Score 4: 8', delay: 100 },
  { type: 'output', text: '============================================================', delay: 50 },
];
```

### Smooth Scroll CSS (one line in global.css)
```css
/* Source: MDN scroll-behavior -- Baseline Widely Available since March 2022 */
html {
  scroll-behavior: smooth;
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}
```

### Scroll Margin for Fixed Nav
```css
/* Prevent fixed nav from hiding scroll targets */
section[id] {
  scroll-margin-top: 4rem; /* Match nav bar height (h-14 = 3.5rem + buffer) */
}
```

### Stagger Delay for Child Animations
```css
/* Optional: stagger children within a section for cascading effect */
[data-animate] > * {
  transition-delay: calc(var(--stagger, 0) * 100ms);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery `scrollTop()` animate | `scroll-behavior: smooth` CSS | Baseline March 2022 | Zero JS needed for smooth scrolling |
| `scroll` event + `getBoundingClientRect()` | `IntersectionObserver` API | Baseline March 2019 | Async, no main-thread jank |
| GSAP ScrollTrigger (40KB+) | IntersectionObserver + CSS transitions | N/A (always available) | Zero dependency, ~30 lines JS |
| typed.js / Termynal library | Custom async/await typing (~80 lines) | N/A | Full control, no dependency, exact same effect |
| `@starting-style` for entry animations | IntersectionObserver class toggle | `@starting-style` still limited | IO pattern has universal support, `@starting-style` has gotchas with specificity |

**Deprecated/outdated:**
- `scroll` event listeners for viewport detection: replaced by IntersectionObserver
- jQuery `.animate()` for scrolling: replaced by CSS `scroll-behavior`
- AOS library: unnecessary overhead for CSS class toggle pattern
- `@starting-style` for scroll animations: not designed for this purpose (it's for element creation, not viewport entry)

## Open Questions

1. **Terminal Demo Placement**
   - What we know: PLSH-01 says "animated terminal section." The Hero currently has a ScreenshotFrame with gradient placeholder.
   - What's unclear: Should the terminal replace the ScreenshotFrame gradient placeholder, or be a separate new section below Hero?
   - Recommendation: Replace the ScreenshotFrame gradient content. The terminal output inside a browser-mockup frame is visually compelling and immediately communicates what the product does. No need for a separate section.

2. **Nav Bar Scope**
   - What we know: PLSH-03 explicitly requires "anchor links to page sections from nav bar." No nav bar currently exists.
   - What's unclear: How feature-rich should the nav be? Mobile hamburger? Scroll spy active states? Logo?
   - Recommendation: Minimal sticky nav: logo text "JobFlow" left, 5-6 anchor links right (hidden on mobile, visible md+). ThemeToggle moves into the nav bar. No hamburger menu needed for a single-page site -- mobile users scroll naturally. Optional: scroll spy to highlight active section.

3. **Animation Trigger: Once vs Repeat**
   - What we know: Best practice is fire-once (unobserve after first intersection).
   - What's unclear: Should terminal replay if user scrolls away and back?
   - Recommendation: Terminal plays once (set flag, unobserve). Section fade-ins play once. This matches "subtle" and "craftsmanship" signals.

## Sources

### Primary (HIGH confidence)
- MDN `scroll-behavior` reference: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/scroll-behavior -- Baseline Widely Available since March 2022
- MDN IntersectionObserver API: https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API -- Baseline since March 2019
- Astro View Transitions docs: https://docs.astro.build/en/guides/view-transitions/ -- `astro:page-load` lifecycle, `data-astro-rerun` behavior
- Astro Template Directives: https://docs.astro.build/en/reference/directives-reference/ -- `is:inline`, script handling
- Codebase: `/Users/patrykattc/work/jobs/orchestrator.py` -- actual pipeline print output for terminal demo content
- Codebase: all section components -- verified current section IDs, existing anchor links, no nav bar exists

### Secondary (MEDIUM confidence)
- Termynal.js source: https://github.com/ines/termynal -- ~220 lines, async/await typing pattern, MIT license, informed custom implementation approach
- Astro Bag of Tricks (community): https://events-3bg.pages.dev/jotter/astro/scripts/ -- script re-execution patterns with ClientRouter
- IntersectionObserver animation patterns: https://coolcssanimation.com/how-to-trigger-a-css-animation-on-scroll/ -- class toggle pattern, prefers-reduced-motion handling

### Tertiary (LOW confidence)
- None. All findings verified with primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All browser APIs are Baseline (widely available). No libraries needed. Verified on MDN.
- Architecture: HIGH - Patterns are standard (IO class toggle, async/await typing, CSS scroll-behavior). Verified against Astro docs for ClientRouter compatibility.
- Pitfalls: HIGH - Common issues (FOUC, scroll-margin-top, reduced motion, z-index conflicts) are well-documented and verifiable from codebase inspection.

**Research date:** 2026-02-13
**Valid until:** 2026-03-13 (stable -- browser APIs don't change)
