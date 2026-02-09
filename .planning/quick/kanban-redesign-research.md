# Kanban Board Redesign -- Design Research

> Research compiled from Dribbble, Flowbite, TailwindFlex, Eleken, and top design system references.
> Date: 2026-02-08

---

## 1. Design Patterns Observed

### Common Across Top Kanban Designs

1. **Colored left-border accent on cards** -- A 3-4px colored left border strip indicates the card's status/priority at a glance. This is the single most common pattern across Dribbble shots and production tools (Jira, Linear, ClickUp).

2. **Column headers with colored dot/pill + count** -- Column titles use a small colored circle or pill badge next to the status name, with a count in parentheses. Never just plain text.

3. **Subtle column backgrounds** -- Columns use very light tinted backgrounds (gray-50 to gray-100 range), NOT white. This creates visual separation without harshness.

4. **Card elevation hierarchy** -- Cards at rest use `shadow-sm`; on hover they elevate to `shadow-md`; while dragging they get `shadow-xl` with slight scale-up. This three-tier elevation communicates interactivity.

5. **Compact card density** -- Most boards favor compact cards (3 lines of info max) with expand-on-click for details. Information is ruthlessly prioritized: title > company/assignee > metadata tags.

6. **Grouped terminal states** -- Boards with many columns (7+) visually de-emphasize terminal/done states (narrower columns, reduced opacity, or collapsed by default).

7. **Horizontal scroll with sticky first column** -- When columns overflow, the board scrolls horizontally. Some designs pin the first column.

8. **Drag handles are implicit** -- Most modern Kanban UIs use `cursor-grab` on the entire card rather than explicit 6-dot handles. The entire card is the drag target.

9. **Empty state per column** -- Empty columns show a dashed border placeholder with muted text like "Drop items here" or "No items yet."

10. **Score/priority as visual weight** -- High-priority items use bolder colors, larger type, or accent backgrounds. Low-priority items are visually quieter.

---

## 2. Color & Theming

### Recommended Status Color Palette (9 Columns)

Each status gets a **semantic color family** from Tailwind's palette. The color is used in three places: column header dot, card left-border accent, and the status badge.

| Status | Role | Tailwind Family | Dot/Border | Badge BG | Badge Text |
|---|---|---|---|---|---|
| **Saved** | Neutral start | `slate` | `bg-slate-400` | `bg-slate-100` | `text-slate-700` |
| **Applied** | Active progress | `blue` | `bg-blue-500` | `bg-blue-100` | `text-blue-700` |
| **Phone Screen** | Early interview | `amber` | `bg-amber-500` | `bg-amber-100` | `text-amber-700` |
| **Technical** | Mid interview | `orange` | `bg-orange-500` | `bg-orange-100` | `text-orange-700` |
| **Final Interview** | Late interview | `pink` | `bg-pink-500` | `bg-pink-100` | `text-pink-700` |
| **Offer** | Success | `emerald` | `bg-emerald-500` | `bg-emerald-100` | `text-emerald-700` |
| **Rejected** | Terminal negative | `red` | `bg-red-400` | `bg-red-50` | `text-red-600` |
| **Withdrawn** | Terminal neutral | `gray` | `bg-gray-400` | `bg-gray-100` | `text-gray-600` |
| **Ghosted** | Terminal unknown | `violet` | `bg-violet-400` | `bg-violet-50` | `text-violet-600` |

### Score Colors (1-5 Scale)

| Score | Color | Class | Visual Treatment |
|---|---|---|---|
| 5 | Emerald | `text-emerald-600 font-bold` | Strong emphasis, filled star icon |
| 4 | Blue | `text-blue-600 font-bold` | Good emphasis |
| 3 | Gray | `text-gray-500 font-semibold` | Neutral |
| 2 | Gray light | `text-gray-400` | De-emphasized |
| 1 | Gray lighter | `text-gray-300` | Barely visible |

### Board Background

Use `bg-gray-100` for the board area (slightly darker than page background `bg-gray-50`) to create a recessed "workspace" feel.

---

## 3. Card Design

### Recommended Card Layout (Visual Hierarchy)

```
+-----------------------------------------------+
| [4px colored left border]                      |
|                                                |
|  Senior DevOps Engineer            [4/5 score] |
|  Acme Corp                                     |
|  [indeed pill]  [Remote]  [$150-180k]          |
|                                                |
+-----------------------------------------------+
```

**Hierarchy (top to bottom, left to right):**
1. **Job title** -- `text-sm font-semibold text-gray-900 truncate` (primary info)
2. **Score** -- Top-right corner, colored by score value (quick visual scan)
3. **Company** -- `text-xs text-gray-500` (secondary info)
4. **Metadata row** -- Platform pill + optional location + optional salary (tertiary info)

### Card CSS Structure

```
Card container:
  bg-white rounded-lg border border-gray-200
  shadow-sm hover:shadow-md transition-shadow duration-200
  cursor-grab active:cursor-grabbing
  border-l-4 border-l-{status-color}

Inner padding:
  p-3 (12px all sides)

Title row (flex between):
  Left: text-sm font-semibold text-gray-900 leading-tight truncate
  Right: score badge

Company:
  text-xs text-gray-500 mt-1 truncate

Metadata row:
  flex items-center gap-1.5 mt-2 flex-wrap

Platform pill:
  text-[10px] font-medium px-1.5 py-0.5 rounded-full
  bg-{platform-color}-50 text-{platform-color}-600

Location/Salary (optional):
  text-[10px] text-gray-400
```

### Platform Badge Colors

| Platform | BG | Text |
|---|---|---|
| Indeed | `bg-indigo-50` | `text-indigo-600` |
| Dice | `bg-teal-50` | `text-teal-600` |
| RemoteOK | `bg-amber-50` | `text-amber-600` |

---

## 4. Column & Board Layout

### Handling 9 Columns

9 columns is a lot. Key strategies observed in designs with many columns:

1. **Two-tier layout** -- Group columns into "Active Pipeline" (Saved through Offer = 6 columns) and "Terminal" (Rejected, Withdrawn, Ghosted = 3 columns). Terminal columns can be:
   - Narrower (`min-w-[220px]` vs `min-w-[280px]`)
   - Visually quieter (reduced opacity, gray-toned headers)
   - Collapsible (click to expand/collapse)

2. **Column minimum widths** -- Active columns: `min-w-[260px] w-[260px]`. Terminal columns: `min-w-[220px] w-[220px]`.

3. **Scroll behavior** -- `overflow-x-auto` on the board container with `pb-4` for scrollbar space. Consider `scroll-snap-type: x mandatory` for snapping.

4. **Column header anatomy:**

```
[Colored dot]  Status Name  (count)
```

- Dot: `w-2.5 h-2.5 rounded-full bg-{color}-500`
- Name: `text-sm font-semibold text-gray-700`
- Count: `text-xs text-gray-400 font-medium`

5. **Empty column state:**

```html
<div class="border-2 border-dashed border-gray-200 rounded-lg
            flex items-center justify-center min-h-[100px]
            text-xs text-gray-400">
    No jobs yet
</div>
```

### Column Container Structure

```
Board wrapper:
  bg-gray-100 rounded-xl p-4 -mx-4
  flex gap-3 overflow-x-auto pb-4

Column:
  min-w-[260px] w-[260px] flex-shrink-0 flex flex-col

Column header:
  flex items-center gap-2 mb-3 px-1

Card list (drop zone):
  flex-1 space-y-2 min-h-[200px]
  bg-gray-50/50 rounded-lg p-2
  transition-colors duration-200
```

---

## 5. Drag-and-Drop UX

### SortableJS Configuration

```javascript
{
    group: 'kanban',
    animation: 200,            // Slightly longer for smoothness
    ghostClass: 'kanban-ghost',
    dragClass: 'kanban-drag',
    chosenClass: 'kanban-chosen',
    forceFallback: true,        // Consistent cross-browser behavior
    fallbackTolerance: 3,       // Prevent accidental drags on click
    scrollSensitivity: 80,      // Start scrolling near edges
    scrollSpeed: 12,
}
```

### Visual States

**1. Idle state (default):**
- Card: `shadow-sm border border-gray-200`
- Cursor: `cursor-grab`

**2. Hover state:**
- Card: `shadow-md border-gray-300` (slight elevation)
- Transition: `transition-shadow duration-200`

**3. Chosen/grabbed state** (`.kanban-chosen`):
- Card: `ring-2 ring-blue-400 ring-offset-2 shadow-lg`
- Cursor: `cursor-grabbing`

**4. Ghost/placeholder** (`.kanban-ghost`):
- In the source position: `opacity-30 bg-blue-50 border-2 border-dashed border-blue-300`
- This shows "where the card came from"

**5. Drag element** (`.kanban-drag`):
- The floating card: `shadow-2xl rotate-2 scale-105`
- Slight rotation + scale creates a "picked up" tactile feel

**6. Drop zone active** -- When a dragged card hovers over a column:
- Column background: `bg-blue-50/50` (light blue tint)
- Apply via SortableJS `onMove` callback or CSS `:has()` if supported

### CSS for Drag States

```css
.kanban-ghost {
    opacity: 0.3;
    background: #eff6ff;  /* blue-50 */
    border: 2px dashed #93c5fd;  /* blue-300 */
    border-radius: 0.5rem;
}

.kanban-drag {
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    transform: rotate(2deg) scale(1.05);
    z-index: 50;
}

.kanban-chosen {
    box-shadow: 0 0 0 2px #60a5fa, 0 0 0 4px white;  /* blue ring */
}
```

---

## 6. Micro-interactions

### Hover Effects

- **Card hover:** `shadow-sm -> shadow-md` with `transition-shadow duration-200`
- **Card link hover:** Title text shifts from `text-gray-900` to `text-blue-700`
- **Score hover:** Could show tooltip with score breakdown (future enhancement)

### Transitions

- **Card appearing (new import):** `animate-fadeIn` -- fade in from below
- **Card moving between columns:** SortableJS `animation: 200` handles this
- **Column count update:** Brief flash with `transition-colors` when count changes
- **Status change success:** Brief green flash on the card border

### Column Count Animations

When a card moves between columns, animate the count change:
```css
.col-count-changed {
    animation: pulse 0.3s ease-in-out;
}
@keyframes pulse {
    50% { transform: scale(1.2); color: #3b82f6; }
}
```

### Empty Column Transition

When last card leaves a column, fade in the empty placeholder:
```css
.kanban-list:empty::after {
    content: 'No jobs';
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100px;
    color: #9ca3af;
    font-size: 0.75rem;
    border: 2px dashed #e5e7eb;
    border-radius: 0.5rem;
    margin: 0.25rem;
    animation: fadeIn 0.3s ease-in;
}
```

---

## 7. Concrete Tailwind Implementation Notes

### What to Change from Current Implementation

#### Current Weaknesses (from reading the templates)

1. **Cards are plain white rectangles** -- No left-border accent, no hover elevation, no score positioning
2. **Column headers use only status-badge pills** -- Missing the colored dot, count is outside the visual group
3. **No drag visual feedback** -- Only `opacity-30` ghost, no rotation/scale on drag element
4. **Terminal columns same width as active** -- All 9 columns compete equally for space
5. **No empty column state** -- Empty columns are just blank gray boxes
6. **Score colors defined in custom CSS** -- Could use Tailwind utilities instead
7. **Platform not visually differentiated** -- Plain gray text, no pill/badge

#### New Card Template (`kanban_card.html`)

```html
<div class="kanban-card bg-white rounded-lg border border-gray-200 shadow-sm
            hover:shadow-md transition-shadow duration-200
            cursor-grab active:cursor-grabbing
            border-l-4 border-l-{{ status_color }}
            p-3"
     data-key="{{ job.dedup_key }}">
    <a href="/jobs/{{ job.dedup_key }}" class="block no-underline">
        <div class="flex items-start justify-between gap-2">
            <div class="font-semibold text-sm text-gray-900 leading-tight truncate
                        hover:text-blue-700 transition-colors">
                {{ job.title }}
            </div>
            {% if job.score %}
            <span class="text-xs font-bold {{ score_class }} shrink-0">
                {{ job.score }}/5
            </span>
            {% endif %}
        </div>
        <div class="text-xs text-gray-500 mt-1 truncate">{{ job.company }}</div>
        <div class="flex items-center gap-1.5 mt-2 flex-wrap">
            <span class="text-[10px] font-medium px-1.5 py-0.5 rounded-full
                         {{ platform_badge_class }}">
                {{ job.platform }}
            </span>
            {% if job.location %}
            <span class="text-[10px] text-gray-400">{{ job.location }}</span>
            {% endif %}
            {% if job.salary %}
            <span class="text-[10px] text-gray-400">{{ job.salary }}</span>
            {% endif %}
        </div>
    </a>
</div>
```

#### New Column Header Pattern

```html
<div class="flex items-center gap-2 mb-3 px-1">
    <span class="w-2.5 h-2.5 rounded-full {{ dot_color }}"></span>
    <span class="text-sm font-semibold text-gray-700">
        {{ status.replace('_', ' ').title() }}
    </span>
    <span class="col-count text-xs text-gray-400 font-medium bg-gray-200
                 rounded-full px-2 py-0.5">
        {{ columns[status] | length }}
    </span>
</div>
```

#### Status-to-Tailwind Color Mapping (Jinja2)

This should be handled in the backend or via a Jinja2 macro/dict:

```python
STATUS_COLORS = {
    "saved":           {"dot": "bg-slate-400",   "border": "border-l-slate-400",   "badge_bg": "bg-slate-100",   "badge_text": "text-slate-700"},
    "applied":         {"dot": "bg-blue-500",    "border": "border-l-blue-500",    "badge_bg": "bg-blue-100",    "badge_text": "text-blue-700"},
    "phone_screen":    {"dot": "bg-amber-500",   "border": "border-l-amber-500",   "badge_bg": "bg-amber-100",   "badge_text": "text-amber-700"},
    "technical":       {"dot": "bg-orange-500",  "border": "border-l-orange-500",  "badge_bg": "bg-orange-100",  "badge_text": "text-orange-700"},
    "final_interview": {"dot": "bg-pink-500",    "border": "border-l-pink-500",    "badge_bg": "bg-pink-100",    "badge_text": "text-pink-700"},
    "offer":           {"dot": "bg-emerald-500", "border": "border-l-emerald-500", "badge_bg": "bg-emerald-100", "badge_text": "text-emerald-700"},
    "rejected":        {"dot": "bg-red-400",     "border": "border-l-red-400",     "badge_bg": "bg-red-50",      "badge_text": "text-red-600"},
    "withdrawn":       {"dot": "bg-gray-400",    "border": "border-l-gray-400",    "badge_bg": "bg-gray-100",    "badge_text": "text-gray-600"},
    "ghosted":         {"dot": "bg-violet-400",  "border": "border-l-violet-400",  "badge_bg": "bg-violet-50",   "badge_text": "text-violet-600"},
}
```

#### Tailwind CDN Configuration

Since we use Tailwind CDN, dynamic class names like `border-l-blue-500` need to be in a safelist or present as full strings (not interpolated). The simplest approach: output them as full class strings from the backend via template context, or use inline styles for the dynamic border color.

**Recommended approach:** Pass the hex color value and use `style="border-left-color: {{ color }}"` for the card left border, while keeping Tailwind classes for everything else:

```html
<div class="... border-l-4" style="border-left-color: {{ status_hex }}">
```

#### Key Tailwind Classes Summary

```
Board:       bg-gray-100 rounded-xl p-4 flex gap-3 overflow-x-auto pb-4
Column:      min-w-[260px] w-[260px] flex-shrink-0
Terminal:    min-w-[220px] w-[220px] opacity-70
Card list:   space-y-2 min-h-[200px] rounded-lg p-2
Card:        bg-white rounded-lg border border-gray-200 shadow-sm p-3
             hover:shadow-md transition-shadow duration-200
             cursor-grab active:cursor-grabbing border-l-4
Ghost:       opacity-30 (+ custom CSS for dashed blue border)
Drag:        shadow-2xl (+ custom CSS for rotate + scale)
Score 5:     text-emerald-600 font-bold
Score 4:     text-blue-600 font-bold
Score 3:     text-gray-500 font-semibold
Score 2:     text-gray-400
Score 1:     text-gray-300
```

---

## 8. Implementation Priority

Recommended order of changes (each can be shipped independently):

1. **Card left-border accent + score repositioning** -- Biggest visual impact, minimal code change
2. **Column header redesign** -- Colored dots + count pills
3. **Drag-and-drop visual polish** -- Ghost/drag CSS classes
4. **Platform badge pills** -- Colored per-platform
5. **Terminal column de-emphasis** -- Narrower width + reduced opacity
6. **Empty column states** -- CSS `:empty` pseudo-element
7. **Board background** -- Recessed gray-100 workspace
8. **Micro-interactions** -- Hover transitions, count animations

---

## Sources

- [Dribbble Kanban tags](https://dribbble.com/tags/kanban-board)
- [Flowbite Kanban Board](https://flowbite.com/application-ui/demo/pages/kanban/)
- [TailwindFlex Interactive Kanban](https://tailwindflex.com/@quentin/interactive-kanban-board)
- [Eleken Drag-and-Drop UI](https://www.eleken.co/blog-posts/drag-and-drop-ui)
- [SortableJS Ghost Styling](https://github.com/SortableJS/Sortable/issues/794)
- [Tailwind CSS Colors](https://tailwindcss.com/docs/colors)
- [Semantic Tailwind Colors](https://www.subframe.com/blog/how-to-setup-semantic-tailwind-colors)
- [Card UI Design Examples 2025](https://bricxlabs.com/blogs/card-ui-design-examples)
- [UI/UX Design Trends 2026](https://www.index.dev/blog/ui-ux-design-trends)
- [Personal Kanban for Job Hunting](https://kanbanzone.com/2023/personal-kanban-for-job-hunting/)
