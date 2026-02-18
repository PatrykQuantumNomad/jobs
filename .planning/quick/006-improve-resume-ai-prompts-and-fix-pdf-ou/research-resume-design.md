# Resume Design & Typography Research (2025–2026)

Research for task 006: Improve resume AI prompts and fix PDF output quality.

---

## 1. Optimal Font Choices for Professional Resumes

### Recommendation: Sans-serif for tech/engineering roles

**Why sans-serif:** Sans-serif fonts are easier to read on digital screens and in ATS parsing. They convey modernity and clarity, which is appropriate for tech/engineering.

**Top choices (in priority order):**
1. **Inter** — Modern, geometric, excellent screen rendering, designed for UI/code contexts. Best choice for software engineers.
2. **Lato** — Humanist sans-serif, warm but professional, widely used in tech resumes.
3. **Calibri** — Microsoft default, universally available, ATS-safe.
4. **Helvetica / Arial** — Classic, highly legible, ATS-friendly. Helvetica preferred for PDFs.
5. **Roboto** — Google's font, used in Android/Material design; familiar to tech recruiters.

**Font pairing rule:** Maximum 2 fonts — preferably **one font family** with different weights. Use `font-weight: 700` (bold) for headers, `font-weight: 400` (regular) for body, `font-weight: 300` (light) for metadata/dates.

**Avoid:** Decorative fonts (Comic Sans, Courier, papyrus), anything requiring custom @font-face from CDN in production PDFs (increases size and can fail).

**CSS declaration (WeasyPrint-safe):**
```css
body {
  font-family: "Inter", "Lato", "Helvetica Neue", Arial, sans-serif;
}
```

---

## 2. Font Sizes for Resume Elements

| Element               | Size     | Weight   | Notes                                    |
|-----------------------|----------|----------|------------------------------------------|
| Candidate name        | 22–26pt  | 700 bold | Largest element on page                  |
| Section headers       | 13–14pt  | 700 bold | ALL CAPS or title case + color accent    |
| Job title (role held) | 11–12pt  | 600/700  | Bold to distinguish from employer name   |
| Company name          | 11–12pt  | 400      | Regular or italic                        |
| Dates / location      | 10–11pt  | 400      | Right-aligned, lighter color or italic   |
| Body / bullet text    | 10–11pt  | 400      | The readable baseline — never < 10pt     |
| Contact info / links  | 10–11pt  | 400      | Inline in header row                     |

**CSS equivalents (pt → px at 96dpi for screen, pt is direct for print/PDF):**
```css
.candidate-name  { font-size: 24pt; font-weight: 700; }
.section-header  { font-size: 13pt; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.job-title       { font-size: 11pt; font-weight: 700; }
.company-name    { font-size: 11pt; font-weight: 400; }
.date-location   { font-size: 10pt; font-weight: 400; color: #555; }
.body-text       { font-size: 10.5pt; font-weight: 400; }
```

---

## 3. Spacing: Margins, Line Height, Section Gaps

### Page Margins
- **Standard:** 1 inch (25.4mm) all sides — most professional, gives breathing room
- **Tight:** 0.75 inch (19mm) — acceptable when content doesn't fit 1-page
- **Minimum:** 0.5 inch (12.7mm) — only at top, never sides (content feels crammed)

**CSS @page rule:**
```css
@page {
  size: Letter;  /* or A4 for international */
  margin: 25.4mm 20mm 20mm 20mm;  /* top right bottom left */
}
```

### Line Height
- **Body text:** `line-height: 1.35` — sweet spot between density and readability
- **Bullet lists:** `line-height: 1.3` — slightly tighter since items are short
- **Section headers:** `line-height: 1.2` — compact for visual distinction
- **Candidate name:** `line-height: 1.1` — large text needs tighter line height

```css
body        { line-height: 1.35; }
ul          { line-height: 1.3; }
h2          { line-height: 1.2; }
```

### Section & Element Gaps
```css
/* Between major sections (e.g., Experience → Education) */
.section       { margin-bottom: 14pt; }

/* Between job entries within a section */
.job-entry     { margin-bottom: 10pt; }

/* Space between bullets */
li             { margin-bottom: 2pt; }

/* Space above section header */
h2             { margin-top: 12pt; margin-bottom: 4pt; }

/* Space between company name row and first bullet */
.job-header    { margin-bottom: 3pt; }
```

---

## 4. Color: Professional Accent Colors

### Color Philosophy
- Maximum 2–3 colors: primary text (black/near-black), one accent, optional light gray for metadata
- Use color on: name, section headers, horizontal dividers — NEVER on body text bullets

### Recommended Accent Colors with Hex Values

| Color Name        | Hex       | Industry Fit                     | Contrast on white |
|-------------------|-----------|----------------------------------|-------------------|
| Deep Navy         | `#1B3A6B` | Tech, Finance, Engineering       | AAA (WCAG)        |
| Steel Blue        | `#2563EB` | Tech, Startups, SaaS             | AA (WCAG)         |
| Slate Gray        | `#334155` | All industries, very safe        | AAA               |
| Teal              | `#0D9488` | Tech, Healthcare, Creative       | AA                |
| Charcoal          | `#374151` | Conservative industries          | AAA               |
| Forest Green      | `#166534` | Engineering, Sustainability      | AAA               |
| Warm Graphite     | `#1F2937` | Near-black, ultra-professional   | AAA               |

**Recommended for senior tech roles:** Deep Navy `#1B3A6B` or Steel Blue `#2563EB` as primary accent with Warm Graphite `#1F2937` for main text.

### CSS Color System
```css
:root {
  --text-primary:   #1F2937;   /* near-black body text */
  --text-secondary: #6B7280;   /* dates, location, metadata */
  --accent:         #1B3A6B;   /* name, section headers, dividers */
  --divider:        #D1D5DB;   /* horizontal rule color */
  --background:     #FFFFFF;
}
```

### Accessibility
- All recommended colors above meet WCAG AA minimum (4.5:1 contrast ratio) on white
- Never convey meaning through color alone (e.g., don't color-code bullet importance)
- Avoid: red, orange, yellow (low contrast), neon/bright colors

---

## 5. Visual Hierarchy Techniques for PDF Resumes

### Hierarchy Levels (6 levels for a resume)
1. **Candidate name** — largest, boldest element
2. **Section headers** — bold, uppercase, color accent, divider line below
3. **Job title** — bold, slightly larger than body
4. **Company name + dates** — same size as title, regular weight, different styling
5. **Bullet points** — standard body size, regular weight
6. **Supplementary info** — smaller, lighter color (certifications, links, dates)

### Techniques
- **Weight contrast:** 700 (headers) vs 400 (body) vs 300 (metadata) — the most powerful tool
- **Size contrast:** 3–4pt difference between levels is sufficient
- **Color contrast:** Accent color for structural elements only
- **Whitespace:** Consistent section gaps signal hierarchy changes
- **Letter-spacing:** `letter-spacing: 0.08–0.1em` on uppercase section headers adds refinement
- **Section dividers:** Thin `1px` horizontal rule (e.g., `border-bottom: 1px solid #D1D5DB`) under section header — clean and ATS-safe

### What to AVOID for visual hierarchy
- Tables for layout (ATS can't parse them reliably)
- Icons/graphics/logos
- Colored boxes or background fills on sections
- Multiple font families (more than 2)
- Gradients
- Multi-column layouts (ATS reads left-to-right, top-to-bottom linearly)

---

## 6. Section Ordering for Senior Tech/Engineering Resumes

### Recommended Order (> 10 years experience)

**Page 1 (the important stuff):**
1. **Header** — Name, title/tagline, contact row (email, phone, location, LinkedIn, GitHub)
2. **Professional Summary** — 3–5 lines, quantified highlights, tailored to job
3. **Skills** — grouped by category (Languages, Frameworks, Cloud, Tools) — 10–15 items max
4. **Experience** — reverse chronological, most recent 2–3 roles in detail

**Page 2 (supporting evidence):**
5. **Continued Experience** — older roles with fewer bullets (2–3 max for roles > 10 years old)
6. **Notable Projects / Open Source** — especially if GitHub is strong
7. **Education** — degree, school, year (no GPA unless exceptional/recent)
8. **Certifications** — AWS, GCP, Kubernetes, etc.
9. **Publications / Talks** (optional, if relevant)

### Rules
- Keep most recent role's bullets rich (4–6 bullets); older roles get 2–3 bullets
- Skills section before Experience is recommended for senior engineers — it gives recruiters instant signal
- Education goes near the bottom (experience outweighs education for 10+ year engineers)
- A brief professional summary IS worthwhile for senior engineers (1 paragraph showing scope of impact)

---

## 7. Bullet Point Best Practices

### Structure
**Formula:** `[Strong Action Verb] + [What you did] + [Result/Impact with metric]`

**Examples:**
- "Architected microservices migration reducing deployment time by 60% and cutting infrastructure costs by $120K/year"
- "Led team of 8 engineers delivering payment platform processing $2B annually"

### Length
- **1–2 lines per bullet** — never 3+ lines (won't be read)
- **Aim for ~80–120 characters** per bullet
- One main achievement per bullet — don't chain multiple things with "and"

### Action Verbs (strong openers for senior engineers)
```
Architected  |  Engineered  |  Designed    |  Led
Spearheaded  |  Scaled      |  Optimized   |  Reduced
Delivered    |  Launched    |  Migrated    |  Refactored
Mentored     |  Established |  Automated   |  Increased
Partnered    |  Integrated  |  Modernized  |  Drove
```

### Weak verbs to AVOID
`Helped, Worked on, Responsible for, Assisted, Participated in, Contributed to`

### Quantification
- Use numbers whenever possible: %, $, time saved, team size, users, scale
- If metric is confidential, use relative terms: "~40% reduction", "multi-million dollar"
- 3–4 quantified bullets per role is ideal; 50%+ bullets should have metrics

### CSS for bullets
```css
ul {
  padding-left: 14pt;
  margin: 3pt 0 6pt 0;
}
li {
  margin-bottom: 2.5pt;
  line-height: 1.3;
}
li::marker {
  content: "▪ ";  /* subtle square bullet — modern alternative to circle */
  color: var(--accent);
}
```

---

## 8. Two-Page Resume Layout

### Page 1 (critical, must-read)
- Full header with contact info
- Professional summary (3–5 lines)
- Skills section
- Most recent 2 roles (full detail, 4–6 bullets each)
- Do NOT split a job entry across pages

### Page 2 (supporting detail)
- Small "running header" with name + page 2 notation
- Earlier experience (3+ roles, 2–3 bullets each)
- Older roles can be collapsed: "Company | Role | Year–Year" with no bullets
- Projects / Open Source
- Education
- Certifications

### Page Break Rules (CSS)
```css
/* Prevent job entries from splitting across pages */
.job-entry {
  page-break-inside: avoid;
  break-inside: avoid;
}

/* Force new page at second section if needed */
.page-break {
  page-break-before: always;
  break-before: page;
}

/* Prevent orphaned headers */
h2 {
  page-break-after: avoid;
  break-after: avoid;
}
```

### WeasyPrint note
WeasyPrint supports `break-inside: avoid` and `break-before: page` from CSS Fragmentation. Prefer the unprefixed `break-*` properties over the deprecated `page-break-*` properties (though WeasyPrint supports both).

---

## 9. Contact Info and Links Layout

### What to Include (in order of importance)
1. **Full name** — largest text on page
2. **Job title / tagline** — e.g., "Senior Software Engineer | Platform & Infrastructure" (optional, under name)
3. **Email** — professional address (firstname@domain.com)
4. **Phone** — with country code if applying internationally
5. **Location** — City, State (no full address needed)
6. **LinkedIn** — shortened URL: `linkedin.com/in/firstnamelastname`
7. **GitHub** — `github.com/username`
8. **Portfolio/website** (optional)

### Layout Pattern
```
[FULL NAME — 24pt bold]
[Job Title Tagline — 11pt regular]

email@domain.com  |  +1 (555) 123-4567  |  City, State  |  linkedin.com/in/name  |  github.com/name
```

Use `|` or `·` as separators. The entire contact row should fit on one line at 10–11pt.

### CSS for Contact Header
```css
.contact-row {
  display: flex;
  justify-content: center;  /* or flex-start for left-aligned */
  gap: 12pt;
  font-size: 10pt;
  color: var(--text-secondary);
  margin-top: 4pt;
}
.contact-row a {
  color: var(--accent);
  text-decoration: none;
}
```

### ATS Note
Include full URLs as text (not just hyperlinks), since some ATS systems strip HTML links. WeasyPrint renders hyperlinks clickable in PDF, but the text value should be the full URL.

---

## 10. Modern vs Dated Resume Design

### What Looks MODERN (2025)
- Single accent color used consistently and sparingly
- Clean horizontal dividers (thin 1px line) between sections
- Generous whitespace — breathing room between sections
- Name as the only large text, everything else at controlled sizes
- Tight information density on Experience (bullets are punchy, not padded)
- Left-aligned text throughout (NOT centered body text)
- Skills shown as clean text groups, NOT as progress bars or skill meters
- No photo (in US/UK/Canada — photos are actively discouraged)
- Subtle letter-spacing on uppercase section headers

### What Looks DATED
- Skills progress bars / percentage meters (meaningless and ATS-hostile)
- Objective statements ("I am seeking a position where I can grow...")
- Photos on US/UK resumes
- Tables for layout
- Multiple colors or color backgrounds on sections
- Icons everywhere (phone icon, email icon, etc.)
- Centered body text
- Serif fonts like Times New Roman
- "References available upon request" line
- Cluttered header with too many personal details (no DOB, no marital status)
- Two-column layouts (looks great visually, ATS reads it scrambled)
- Dense walls of text in Experience section

### The "Clean and Modern" Formula
```
✓ One font family (Inter or Lato) with 2–3 weights
✓ One accent color (deep navy or steel blue)
✓ Consistent margins (20–25mm)
✓ Section headers: UPPERCASE, bold, accent color, thin rule below
✓ Bullet points: concise, quantified, strong verbs
✓ Whitespace: let the page breathe
✗ No tables, no columns, no graphics
✗ No more than 2 colors
✗ No decorative elements
```

---

## CSS Template Skeleton (for WeasyPrint)

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
/* NOTE: For production WeasyPrint, use locally hosted fonts instead of CDN */

@page {
  size: Letter;
  margin: 22mm 18mm 18mm 18mm;
}

:root {
  --text-primary:   #1F2937;
  --text-secondary: #6B7280;
  --accent:         #1B3A6B;
  --divider:        #D1D5DB;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.35;
  color: var(--text-primary);
  background: #fff;
}

/* === HEADER === */
.resume-header {
  text-align: left;
  margin-bottom: 14pt;
  padding-bottom: 10pt;
  border-bottom: 2px solid var(--accent);
}

.candidate-name {
  font-size: 24pt;
  font-weight: 700;
  color: var(--accent);
  line-height: 1.1;
}

.candidate-tagline {
  font-size: 11pt;
  font-weight: 400;
  color: var(--text-secondary);
  margin-top: 2pt;
}

.contact-row {
  font-size: 10pt;
  color: var(--text-secondary);
  margin-top: 5pt;
}

.contact-row a {
  color: var(--accent);
  text-decoration: none;
}

/* === SECTIONS === */
.section {
  margin-bottom: 14pt;
  break-inside: avoid;
}

h2.section-title {
  font-size: 11pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  border-bottom: 1px solid var(--divider);
  padding-bottom: 2pt;
  margin-bottom: 8pt;
  break-after: avoid;
}

/* === JOB ENTRIES === */
.job-entry {
  margin-bottom: 10pt;
  break-inside: avoid;
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 3pt;
}

.job-title {
  font-size: 11pt;
  font-weight: 700;
}

.job-company {
  font-size: 11pt;
  font-weight: 400;
  color: var(--text-secondary);
}

.job-dates {
  font-size: 10pt;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* === BULLETS === */
ul.bullets {
  padding-left: 14pt;
  margin: 3pt 0 0 0;
}

ul.bullets li {
  margin-bottom: 2pt;
  line-height: 1.3;
}

/* === SKILLS === */
.skills-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3pt 10pt;
  font-size: 10.5pt;
}

.skill-category {
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

/* === PAGE 2 RUNNING HEADER === */
.page-header-secondary {
  display: none;  /* shown only on page 2 via page-break logic */
  font-size: 9pt;
  color: var(--text-secondary);
  text-align: right;
  margin-bottom: 10pt;
}

/* === PAGE BREAKS === */
.page-break-before {
  break-before: page;
}

.no-break {
  break-inside: avoid;
}
```

---

## Key Sources

- [Best Resume Fonts 2026 - Microsoft Word Blog](https://word.cloud.microsoft/create/en/blog/best-resume-fonts/)
- [Top 7 Best Fonts for Resumes 2025 - CandyCV](https://www.candycv.com/how-to/top-7-best-fonts-for-resumes-in-2025-craft-a-winning-first-impression-10)
- [Resume Margins, Spacing & Layout Rules - Vocationic](https://vocationic.com/resume-margins-spacing-layout-rules-for-a-clean-design.html)
- [Best Spacing Ratios for Resume Readability - Resumee](https://www.myresumee.com/blog/vdx-the-best-spacing-ratios-for-modern-resume-readability)
- [Resume Margins & Fonts Guide 2026 - AI ResumeGuru](https://airesume.guru/blog/resume-margins-fonts-spacing)
- [40+ Resume Color Schemes - Design Shack](https://designshack.net/articles/graphics/resume-color-schemes/)
- [Best Resume Colors 2025 - ResumeUp AI](https://resumeup.ai/best-resume-colors)
- [Senior Software Engineer Resume - TechInterviewHandbook](https://www.techinterviewhandbook.org/resume/)
- [Two-Page Resume Format - MyPerfectResume](https://www.myperfectresume.com/career-center/resumes/how-to/two-page-resume)
- [Resume Bullet Points Guide - ResumeWorded](https://resumeworded.com/resume-bullet-points)
- [Modern Resume Formatting 5 Principles - ResuFit](https://www.resufit.com/blog/modern-resume-formatting-5-design-principles-that-will-make-your-resume-stand-out/)
- [WeasyPrint Tips and Tricks - NaveenMK](https://www.naveenmk.me/blog/weasyprint/)
- [WeasyPrint Common Use Cases - Official Docs](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html)
- [Resume Header Best Practices - Rezi](https://www.rezi.ai/posts/resume-header)
- [What Should a Resume Look Like 2025 - Teal](https://www.tealhq.com/post/best-looking-resume)
