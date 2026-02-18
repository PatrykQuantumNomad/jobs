# ATS Parsing Compatibility Research

**Scope:** How ATS systems parse PDF resumes; what HTML/CSS patterns to avoid when generating PDFs with WeasyPrint for resume_ai/renderer.py and resume_template.html.

---

## 1. How ATS Systems Parse PDFs

ATS systems use text-extraction libraries (not OCR) against text-based PDFs. The text extraction reads the PDF's content stream in order — typically top-to-bottom, left-to-right based on character coordinates in the PDF file. This is where layout problems bite:

- **Multi-column layouts**: the extractor reads across both columns simultaneously, jumbling left-column text with right-column text at the same vertical position.
- **Text boxes / floating objects**: positioned outside normal flow, these are often extracted at the end of the document or skipped entirely.
- **Headers/footers**: most ATS strip or ignore PDF header/footer regions. Contact info placed in HTML `<header>` that WeasyPrint renders as a page header region will disappear.
- **Tables**: cells are extracted row-by-row rather than column-by-column, scrambling the reading order.
- **Image-based PDFs**: completely unreadable. WeasyPrint generates text-based PDFs by default — this is fine.
- **Scanned PDFs**: N/A for WeasyPrint output.

**Key stat:** 58% of recruiters (Jobscan 2023) reported poorly formatted PDFs caused parsing failures.

---

## 2. Font Requirements

### Safe fonts (universally parsed correctly)
- Arial, Helvetica, Calibri, Carlito (open-source Calibri substitute)
- Georgia, Times New Roman, Cambria, Garamond, Palatino
- Tahoma, Verdana

### Font size guidance
- Body text: 10–12pt
- Section headings: 11–14pt
- Name header: 16–22pt

### What breaks ATS
- Script/decorative fonts (ligatures can confuse text extraction)
- Custom web fonts not embedded in the PDF — ATS may see garbled characters
- Fonts that use ligatures (`fi`, `fl`) — some parsers can't split ligatures back into individual characters

### WeasyPrint specifics
- WeasyPrint embeds and subsets fonts automatically — good for portability
- Use system fonts (Arial, Calibri) or web-safe fallbacks so the correct font renders
- Setting `text-rendering: optimizeSpeed` disables ligatures — useful for ATS safety (though rarely needed with standard fonts)

**Current template uses:** `'Calibri', 'Carlito', 'Helvetica Neue', Arial` — **this is correct and safe.**

---

## 3. Section Header Naming Conventions

ATS systems are trained to recognize specific section labels. Non-standard labels cause sections to be miscategorized or ignored.

### Required standard headers (use these exact names or close variants)

| Section | ATS-safe names |
|---|---|
| Work history | `Work Experience`, `Professional Experience`, `Experience` |
| Education | `Education` |
| Skills | `Skills`, `Technical Skills`, `Core Competencies` |
| Summary | `Professional Summary`, `Summary`, `Profile` |
| Certifications | `Certifications`, `Licenses & Certifications` (must be its own section) |
| Projects | `Projects`, `Key Projects` |

### What breaks ATS section recognition
- Creative/unique names: "My Journey", "What I've Built", "Tech Arsenal"
- Combining sections: "Skills & Certifications" in one heading — ATS won't find certifications in the skills scoring bucket
- Using icons/graphics as section dividers instead of text headers

### Platform-specific behavior
- **Greenhouse**: does NOT handle abbreviations (writes MBA but JD says Masters of Business Administration → no match)
- **Workday**: does NOT handle verb tenses or plural words — affects keyword matching but not section parsing
- **Taleo**: exact keyword matching only — acronyms and spelled-out forms are treated as different terms

**Current template sections:** Professional Summary, Technical Skills, Work Experience, Key Projects, Education — **all ATS-safe.**

---

## 4. Single-Column vs Multi-Column Layout

### The short answer
Single-column is safest, but **modern ATS (Greenhouse, Workday, Lever, iCIMS) can handle two-column layouts** when they are built with CSS columns, not HTML tables or text boxes.

### What breaks two-column parsing
- HTML `<table>` for layout (cells scrambled during extraction)
- CSS `position: absolute` or `position: fixed` to place sidebar content
- CSS `float` to create columns
- Visually reordered content via `order` (flexbox) or `grid-column` — document source order ≠ visual order; ATS reads source order

### What works in two-column layouts (if needed)
- CSS `column-count: 2` on a container (native column flow)
- Flexbox where source order matches visual order (no `order` property changes)
- Simple CSS Grid where source order matches visual order

### Recommendation for this project
**Keep single-column layout.** The resume template is single-column; do not introduce sidebar columns. The `.job-header` flex row (title + date aligned left/right) is **safe** because it's a single row of content, not a full-page sidebar.

---

## 5. Table vs Non-Table Layouts

### Tables break ATS because
Text extraction reads table cells row-by-row. A two-column skills table becomes: `Python  3 years  JavaScript  5 years` parsed as one mangled string instead of individual skills with durations.

### Safer alternatives
- Bullet lists (`<ul>`) for skills — each skill on its own line
- Comma-separated or pipe-separated inline skills within a `<p>` (still parseable)
- Definition-style: `<strong>Category:</strong> skill1, skill2` in a plain paragraph

### Verdict
**Never use `<table>` for layout or content in resume HTML.** Use `<ul>`, `<p>`, and styled `<div>` elements.

**Current template:** Skills rendered as comma-separated category lines — **safe.**

---

## 6. Common ATS Systems — Parsing Behavior Summary

| ATS | PDF Support | Column Handling | Key Quirks |
|---|---|---|---|
| **Greenhouse** | Good | Handles clean CSS columns | No abbreviation expansion; frequency-based keyword scoring |
| **Workday** | Good | Handles simple layouts | No verb tense or plural matching; prefers left-aligned text |
| **Lever** | Good (modern) | Cannot handle tables or columns | Strictest on formatting |
| **Taleo** | OK (older versions prefer .docx) | Struggles with complex layouts | Exact keyword matching only; acronyms ≠ full phrases |
| **iCIMS** | Good | Handles native columns | Issues with merged table cells and text boxes |

### Practical implication for keyword writing in prompts
- Write both the acronym AND the full term (e.g., "Kubernetes (K8s)") to satisfy both Taleo-style and Greenhouse-style systems
- Use the JD's exact verb tense and phrasing where possible (Workday matches exact phrases)
- Avoid only using abbreviations for certifications

---

## 7. HTML/CSS Patterns to Avoid in WeasyPrint PDF Generation

These patterns produce PDFs that parse poorly in ATS:

### AVOID — Layout patterns

```css
/* AVOID: Absolute/fixed positioning for content */
.sidebar { position: absolute; left: 0; top: 100px; }

/* AVOID: Float-based columns */
.left-col { float: left; width: 40%; }

/* AVOID: CSS order property reordering content */
.item { order: 3; }  /* visual != source order */

/* AVOID: CSS column-count on large content blocks */
.skills { column-count: 2; }  /* creates multi-column text flow */
```

### AVOID — Content placement

```html
<!-- AVOID: Contact info in page header/footer -->
<!-- WeasyPrint's @page header/footer regions are ignored by ATS -->

<!-- AVOID: Important text in <img> alt text -->
<!-- AVOID: Content inside SVG elements -->
<!-- AVOID: Text placed via CSS content: '' pseudo-elements for actual information -->
```

### AVOID — Typography

```css
/* AVOID: Ligature-heavy fonts for body text */
font-family: 'Playfair Display';  /* ornate ligatures */

/* AVOID: Custom downloaded fonts that may not embed cleanly */
@font-face { src: url('obscure-font.woff2'); }
```

### SAFE — Recommended patterns

```css
/* SAFE: Flexbox for single-row horizontal alignment (title + date) */
.job-header {
    display: flex;
    justify-content: space-between;
}

/* SAFE: Single-column flow with explicit breaks */
.experience-entry {
    page-break-inside: avoid;
    break-inside: avoid;
}

/* SAFE: Section headers prevent orphaning */
h2 {
    page-break-after: avoid;
    break-after: avoid;
}

/* SAFE: Standard system fonts */
body { font-family: 'Calibri', 'Carlito', Arial, sans-serif; }
```

```html
<!-- SAFE: Contact info in main document body, not page header -->
<div class="contact-info">email | phone | city</div>

<!-- SAFE: Links with proper href attributes -->
<a href="https://linkedin.com/in/name">LinkedIn</a>

<!-- SAFE: Bullets as plain <ul><li> elements -->
<ul><li>Achievement text here</li></ul>
```

### WeasyPrint-specific notes

1. **Text flow order**: WeasyPrint uses HTML source order as the PDF content stream order. ATS parsers read the content stream. Source order must equal logical reading order.

2. **PDF/UA mode** (`pdf_variant="pdf/ua-1"` parameter): generates tagged PDFs with semantic structure tags. While ATS systems don't use accessibility tags directly, using tagged PDF means the document structure is explicit and well-ordered. Consider enabling for better long-term compatibility.

3. **`a[href]::after { content: none; }`**: WeasyPrint by default appends URL text after links in print mode. This adds noisy duplicate URLs to the extracted text. Always suppress with this CSS rule.

4. **Page margins**: Keep margins >= 0.5in. Content that bleeds outside the PDF page box can be truncated by some ATS.

5. **WeasyPrint does NOT render headers/footers** from CSS `@page { @top-center {...} }` into the document content flow — they go into the page decoration layer. Do not put contact info there.

---

## Summary: Actionable Rules for resume_template.html

### Must have
- [ ] All contact info in `<body>` flow, not `@page` header decorations
- [ ] Single-column body layout (no `float`, no `column-count`, no `position: absolute` for content)
- [ ] Standard fonts only: Calibri/Carlito, Arial, Helvetica
- [ ] `page-break-inside: avoid` + `break-inside: avoid` on `.experience-entry`, `.skills-section`, `.projects-list`, `.education-text`
- [ ] `page-break-after: avoid` + `break-after: avoid` on `h2` elements (prevent orphaned headers)
- [ ] `a[href]::after { content: none; }` to suppress URL text duplication
- [ ] Section headers use standard ATS-recognized names (Work Experience, Education, Skills, etc.)

### Nice to have (already in 006-PLAN.md)
- [ ] `.job-header` with `display: flex; justify-content: space-between` — safe (single row, source = visual order)
- [ ] Links are underlined and colored for PDF clickability
- [ ] `overflow-wrap: break-word` on body to prevent text overflow

### Do not add
- Sidebar columns for contact info or skills
- HTML `<table>` for any layout purpose
- Absolute/fixed positioned elements for content
- Custom downloaded web fonts

---

## Sources

- [Jobscan: ATS Formatting Mistakes](https://www.jobscan.co/blog/ats-formatting-mistakes/)
- [Resumly: Best Practices for PDF Resumes to Avoid ATS Errors](https://www.resumly.ai/blog/best-practices-for-pdf-resumes-to-avoid-ats-errors)
- [Resumemate: Tables, Columns & Text Boxes — Do They Break ATS?](https://www.resumemate.io/blog/tables-columns-text-boxes-do-they-break-ats-safer-layouts/)
- [Yotru: Resume Columns ATS — Single vs Double Column](https://yotru.com/blog/resume-columns-ats-single-vs-double-column)
- [Interview Guys: What ATS Looks for in Resumes (2025)](https://blog.theinterviewguys.com/what-ats-looks-for-in-resumes/)
- [Greenhouse/Lever/Workday AI Screening Integration Guide](https://www.hragentlabs.com/blog/greenhouse-lever-workday-ai-resume-screening-integration-guide)
- [Skillhub: ATS Optimization Guide (Taleo, Workday)](https://skillhub.com/blog/ats-optimization-guide)
- [WeasyPrint: Common Use Cases Documentation](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html)
- [WeasyPrint: PDF/UA Accessibility Issue #1088](https://github.com/Kozea/WeasyPrint/issues/1088)
- [Resumeadapter: ATS Resume Formatting Rules 2026](https://www.resumeadapter.com/blog/ats-resume-formatting-rules-2026)
