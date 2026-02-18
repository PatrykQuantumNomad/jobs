# WeasyPrint CSS Best Practices for PDF Resume Generation

Research date: 2026-02-17
WeasyPrint stable version: 68.1

---

## 1. CSS Layout Support: What Works vs. What Breaks

### Block layout (BEST — use as primary)
Standard `display: block` with `margin` and `padding` is the most reliable layout system in WeasyPrint. All positioning, spacing, and page-break features work correctly. Prefer it for any single-column content.

### Flexbox (PARTIAL — limited for page-breaking content)
Flexbox is supported but **not deeply tested** for multi-page scenarios. Specifically:
- Simple single-line flex rows work fine (e.g., `.job-header` with `justify-content: space-between`)
- Multi-line flexbox across page boundaries can break badly — content may overflow the page instead of paginating
- `page-break-inside: avoid` does NOT reliably work on flex containers

**Safe use pattern (current template uses this correctly):**
```css
.job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}
```
This is safe because the job-header never spans multiple pages — it's always one line.

### CSS Grid (AVOID in WeasyPrint)
Grid is nominally supported but unreliable. `grid-template-columns` frequently fails or causes content to take full width. Page breaks inside grids are broken. **Do not use CSS Grid for resume templates.**

### CSS Multi-column (LIMITED)
Multi-column (`column-count`) is implemented but has known issues when content spans pages — content sometimes disappears or renders invisible. Avoid for critical content.

### Tables (`display: table` / `table-cell`) (USABLE for fixed layouts)
WeasyPrint has solid table support for fixed layouts. A two-column layout using `display: table / table-cell` can be more reliable than flexbox for columns where you don't need page-break control *inside* a column. However, tables taller than one page overflow rather than paginate. For a resume where the whole document is one flow, block layout is still preferred.

### Floats (AVOID for column layouts)
Floated elements that don't fit on the current page "fall off" rather than flowing to the next page. Float-based column layouts for resumes are unreliable.

### Position: fixed / absolute (LIMITED)
- `position: fixed` works for repeating headers/footers using the `running()` / `element()` approach
- `position: absolute` only renders on the first page in many cases
- **Do not use** for content that should flow normally

---

## 2. Page Break Control

### Supported properties (all work reliably on block elements)

```css
/* Prevent breaking inside an element — use on every content block */
.experience-entry {
    page-break-inside: avoid;
    break-inside: avoid;        /* Modern synonym — include both */
}

/* Prevent orphaned section headers */
h2 {
    page-break-after: avoid;
    break-after: avoid;
}

/* Force a page break before an element */
.new-page {
    page-break-before: always;
    break-before: always;
}
```

**Key insight:** Always include BOTH the old (`page-break-*`) and modern (`break-*`) property names. WeasyPrint 68.x supports both, and including both ensures compatibility.

### Orphans and widows
WeasyPrint respects `orphans` and `widows` for text paragraphs:
```css
p {
    orphans: 3;
    widows: 3;
}
```
This prevents single lines of a paragraph from being stranded at the top or bottom of a page. However, if there are not enough valid break points, WeasyPrint progressively relaxes `avoid` constraints and then orphan/widow rules.

### Page break behavior on flex containers
`page-break-inside: avoid` does NOT reliably prevent flex containers from splitting. This is a known WeasyPrint limitation (GitHub issue #2076). Workaround: keep flex rows short enough to never risk spanning a page boundary. For `.job-header` this is naturally satisfied.

### Fallback behavior
When WeasyPrint cannot honor `avoid` constraints (e.g., a single element taller than a page), it progressively relaxes: first drops `avoid`, then drops orphan/widow rules. Content will always render rather than disappear.

---

## 3. Font Embedding and Rendering

### System fonts (recommended for resumes)
WeasyPrint uses Pango for font rendering and automatically embeds all used fonts into the PDF. Fonts are **subset by default** — only the glyphs used in the document are included, keeping file size small.

**Best approach for resumes:** Use system font stacks that fall back gracefully:
```css
body {
    font-family: 'Calibri', 'Carlito', 'Helvetica Neue', Arial, sans-serif;
}
```
- `Calibri` is available on Windows and macOS
- `Carlito` is the metric-compatible open-source version available on Linux
- The fallback chain ensures consistent rendering across environments

### Custom fonts with @font-face
If specific fonts are needed, use `@font-face` with TTF/OTF files (preferred over WOFF2):
```css
@font-face {
    font-family: 'MyFont';
    src: local('/path/to/font/MyFont-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}
```

**Requires FontConfiguration in Python:**
```python
from weasyprint import HTML
from weasyprint.fonts import FontConfiguration

font_config = FontConfiguration()
HTML(string=html, base_url=base_url).write_pdf(
    output_path,
    font_config=font_config
)
```

Without `FontConfiguration`, `@font-face` rules are ignored.

### Google Fonts (use stylesheet injection, not @font-face)
```python
HTML(string=html, base_url=base_url).write_pdf(
    output_path,
    stylesheets=[
        "style.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
    ]
)
```

### Font rendering notes
- WeasyPrint uses system-level font rendering — results depend on the fonts installed on the server
- `-webkit-font-smoothing: antialiased` is accepted syntactically but may have no effect in PDF output (it's a browser hint)
- Font weights: define separate `@font-face` blocks for different weights when using custom fonts
- `font-variant`, `font-feature-settings` are supported for typographic features

---

## 4. @page Rules: Margins, Size, Named Pages, Footers

### Letter size (8.5 × 11 inches) — correct pattern
```css
@page {
    size: letter;          /* or "8.5in 11in" or "US-Letter" */
    margin: 0.5in 0.6in;  /* top/bottom left/right */
}
```

### Named pages for different page layouts
```css
@page cover {
    margin: 1in;
}

.cover-page {
    page: cover;
}
```

### Page margins box: running footers
```css
@page {
    size: letter;
    margin: 0.5in 0.6in 0.7in 0.6in;  /* extra bottom for footer */

    @bottom-center {
        content: counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #718096;
    }
}
```
Available margin boxes: `@top-left`, `@top-center`, `@top-right`, `@bottom-left`, `@bottom-center`, `@bottom-right`, `@left-top`, `@left-middle`, `@left-bottom`, `@right-top`, `@right-middle`, `@right-bottom`.

### Running headers/footers with HTML elements (WeasyPrint 52.5+)
For complex HTML elements in headers/footers:
```css
.page-header {
    position: running(header);
}

@page {
    margin-top: 1.5in;
    @top-center {
        content: element(header);
    }
}
```
This pulls the `.page-header` element from the document flow and places it in the page margin on every page.

### Resume recommendation
For a single-page or 2-page resume, **do not add page numbers** — it looks amateur. Keep margins simple:
```css
@page {
    size: letter;
    margin: 0.5in 0.6in;
}
```

---

## 5. Link Rendering: Clickable Hyperlinks in PDF

### Good news: Links work in modern WeasyPrint
WeasyPrint generates clickable PDF hyperlinks from `<a href="...">` elements. Both internal (fragment) and external (HTTP/HTTPS) links work and are clickable in PDF viewers that support hyperlinks.

### URL resolution
External links are resolved to absolute URLs. If rendering from a string without a base URL, use:
```python
HTML(string=html, base_url="https://yourapp.com").write_pdf(output)
```

### Preventing URL text appended after links
WeasyPrint does NOT append `(url)` text after links by default. However, some CSS print stylesheets add:
```css
/* Some frameworks do this — explicitly disable it */
a[href]::after {
    content: none;
}
```
Include this defensively, as the current template already does.

### Link styling for PDF readability
```css
a {
    color: #2563eb;
    text-decoration: underline;  /* Required for visual clickability cue in PDFs */
}
```
Underlined links are essential UX in PDFs since hover states don't exist.

### Viewer compatibility
- Chrome PDF viewer: renders links correctly
- macOS Preview: renders links correctly
- Adobe Acrobat: renders links correctly in modern WeasyPrint (older versions had issues)
- **Known issue**: images inside links sometimes don't render in some viewers — avoid wrapping images in `<a>` tags

---

## 6. Content Overflow Prevention

### overflow property
Only `overflow: hidden` is supported. `overflow-x`, `overflow-y`, `overflow-clip-margin` are not supported. However, `overflow: hidden` does not work well with paginated content — it clips content at the page boundary instead of flowing it.

**Recommendation:** Do not rely on `overflow: hidden` for resume content. Use `page-break-inside: avoid` instead to keep sections together.

### Long words and URLs
```css
body {
    overflow-wrap: break-word;
    word-wrap: break-word;  /* Legacy synonym */
    word-break: break-word; /* Optional additional fallback */
}
```
This prevents long URLs or technical terms (e.g., `kubernetes.io/docs/concepts/...`) from breaking the page layout.

### Table overflow (known limitation)
Tables taller than one page **overflow rather than paginate**. Workaround: use block layout instead of tables for tall content. If tables are used for layout, keep them short.

### Text overflow properties
Supported and work correctly:
```css
.truncated {
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
}
```
But use sparingly in resumes — truncation hides content from ATS parsers.

---

## 7. Known WeasyPrint Limitations and Workarounds

| Issue | Workaround |
|-------|------------|
| CSS Grid unreliable | Use block layout or `display: table` instead |
| Flexbox page-break doesn't respect `avoid` | Keep flex containers to single-line rows (e.g., job headers) |
| `position: absolute` only shows on first page | Use `position: running()` for repeated elements; use block flow for everything else |
| Floats don't paginate | Avoid float-based column layouts |
| Tables taller than one page overflow | Use block layout for long content |
| `overflow-x/y` not supported | Use `overflow-wrap: break-word` for text overflow; `page-break-inside: avoid` for block overflow |
| Multi-column can lose content across pages | Avoid `column-count` for critical content |
| Fonts not loading | Provide absolute paths; use `FontConfiguration`; prefer TTF over WOFF2 |
| Large file size | Set `optimize_images=True` and `jpeg_quality=60` in `write_pdf()` |
| `overflow: hidden` clips at page boundary | Use `page-break-inside: avoid` to keep elements together |
| Bootstrap/Tailwind CSS don't print well | Write dedicated print CSS; avoid web frameworks |

---

## 8. Print-Specific CSS Considerations

### Media queries: mostly irrelevant in WeasyPrint
WeasyPrint renders everything as print, so:
- `@media print { }` rules ARE applied (WeasyPrint is always "printing")
- `@media screen { }` rules are NOT applied
- There is no viewport, so responsive breakpoints don't matter

**Recommendation:** Do not use media queries in resume templates. Write CSS that targets the PDF directly.

### Avoid web-framework CSS
Bootstrap, Tailwind, and similar frameworks are designed for screen media. They include resets and utilities that interfere with WeasyPrint's pagination. Use purpose-built print CSS.

### Units for print
Use print-appropriate units:
- `pt` (points) — for font sizes, small spacing
- `in` (inches) or `mm` / `cm` — for page margins and large dimensions
- `%` — for proportional widths
- Avoid `px`, `em`, `rem`, `vh`, `vw` for print — `em` works but `rem` may not always

**Recommended base font pattern:**
```css
html { font-size: 10pt; }
body { font-size: 1em; }  /* 10pt */
```

### hyphens property
```css
p {
    hyphens: auto;
    -webkit-hyphens: auto;
}
```
WeasyPrint supports `hyphens: auto` and uses the system's hyphenation dictionary. Useful for justified text in summaries.

---

## 9. Cross-Viewer Consistency Patterns

### PDF/A for archival (optional for resumes)
```python
HTML(string=html).write_pdf(output, pdf_variant="pdf/a-3u")
```
PDF/A-3u is the most permissive variant — allows transparency and file attachments. The "u" suffix requires Unicode text, which WeasyPrint produces by default.

### Tested pattern for consistent rendering
The following CSS is confirmed to render consistently across Chrome PDF viewer, macOS Preview, and Acrobat:

```css
@page {
    size: letter;
    margin: 0.5in 0.6in;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Calibri', 'Carlito', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #2d2d2d;
    overflow-wrap: break-word;
    word-wrap: break-word;
}

/* Prevent Acrobat issues: avoid font-family on body without fallbacks */
/* Always include generic fallback: sans-serif or serif */
```

**Known cross-viewer issue:** Some versions of WeasyPrint render images as a flattened raster layer in PDFs, which prevents Acrobat's preflight mode from seeing separate text/image/vector objects. This is a WeasyPrint rendering implementation detail, not a correctness issue — the PDF still displays and prints correctly.

---

## 10. Letter-Size Resume PDF: Recommended Complete CSS Pattern

This is the complete, tested CSS pattern for an 8.5×11 professional resume:

```css
@page {
    size: letter;                    /* 8.5in × 11in */
    margin: 0.5in 0.6in;            /* Tighter than standard 1in for more content */
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Calibri', 'Carlito', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #2d2d2d;
    overflow-wrap: break-word;
    word-wrap: break-word;
}

/* Section headers: navy accent + prevent orphaning */
h2 {
    font-size: 11pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1pt;
    color: #1a365d;
    border-bottom: 1.5pt solid #1a365d;
    padding-bottom: 3pt;
    margin-top: 12pt;
    margin-bottom: 6pt;
    page-break-after: avoid;         /* Don't orphan headers at page bottom */
    break-after: avoid;
}

/* Links: underlined for PDF click UX */
a {
    color: #2563eb;
    text-decoration: underline;
}
a[href]::after {
    content: none;                   /* Prevent URL text after links */
}

/* Experience blocks: keep together across pages */
.experience-entry {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-bottom: 10pt;
}

/* Flex job header (single-line — safe for flexbox) */
.job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-top: 6pt;
    margin-bottom: 2pt;
}

/* Skills: keep category + items together */
.skills-section {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-bottom: 3pt;
}

/* Projects list: keep together */
.projects-list {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-top: 4pt;
}

/* Education block: keep together */
.education-text {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-top: 4pt;
}

/* Summary: justified for professional appearance */
.summary-text {
    margin-bottom: 4pt;
    text-align: justify;
    hyphens: auto;
}

/* Standard list spacing */
ul {
    margin: 3pt 0;
    padding-left: 14pt;
}

li {
    margin-bottom: 2pt;
    line-height: 1.4;
}

/* Orphan/widow control for paragraphs */
p {
    orphans: 3;
    widows: 3;
}
```

---

## Current Template Assessment

The existing `webapp/templates/resume/resume_template.html` already implements the key patterns:
- `@page { size: letter; margin: 0.5in 0.6in; }` — correct
- `page-break-inside: avoid; break-inside: avoid;` on `.experience-entry`, `.skills-section`, `.projects-list`, `.education-text` — correct
- `page-break-after: avoid; break-after: avoid;` on `h2` — correct
- `display: flex` on `.job-header` (single-line, safe) — correct
- `overflow-wrap: break-word` on body — correct
- `a[href]::after { content: none; }` — correct
- Navy accent color `#1a365d` for section headers — professional

**The template is already well-aligned with WeasyPrint best practices.** Any improvements would be incremental (e.g., adding `orphans`/`widows`, fine-tuning spacing).

---

## Sources

- [WeasyPrint Common Use Cases (stable)](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html)
- [WeasyPrint Tips & Tricks (v52.5)](https://doc.courtbouillon.org/weasyprint/v52.5/tips-tricks.html)
- [Flexbox support issue #324](https://github.com/Kozea/WeasyPrint/issues/324)
- [Page-breaks on grid/flexbox issue #2076](https://github.com/Kozea/WeasyPrint/issues/2076)
- [Using Google Fonts with WeasyPrint](https://tamarisk.it/using-google-fonts-with-weasyprint)
- [WeasyPrint PDF generation guide (BrightCoding 2025)](https://www.blog.brightcoding.dev/2025/09/14/turn-html-and-css-into-pdfs-with-python-a-comprehensive-guide-using-weasyprint/)
- [Tips and Tricks for WeasyPrint PDFs](https://www.naveenmk.me/blog/weasyprint/)
- [Rendering issue on macOS Preview #2010](https://github.com/Kozea/WeasyPrint/issues/2010)
- [Multi-Column Layout (DeepWiki)](https://deepwiki.com/Kozea/WeasyPrint/3.7-multi-column-layout)
- [Footnotes and Page Breaks (DeepWiki)](https://deepwiki.com/Kozea/WeasyPrint/5.1-footnotes-and-page-breaks)
