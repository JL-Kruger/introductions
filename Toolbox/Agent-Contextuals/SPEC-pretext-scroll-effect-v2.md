# Implementation Spec: Pretext Scroll-Driven Text Effect
### Delivered as `*-content.html` — transparent background, iframe-ready

---

## 0. Layout Constants

```javascript
const BODY_SIZE    = 16      // px — base font size for body text
const LH           = 1.5    // unitless line-height multiplier
const BASE_LINE_PX = BODY_SIZE * LH   // 24px — one line-height in px
const FOCAL_RATIO  = 0.22   // focal zone as fraction of container height
const EDGE         = 0.78   // |d| < EDGE → stable zone
let   COL          = 680    // px — actual rendered column width, set by ResizeObserver
```

`COL` is not a constant — it is measured from the live DOM via `ResizeObserver` and updated on every container resize. The `680` is only a placeholder used before the first measurement fires. See Section 9 (Init).

---

## 1. What the Effect Is

Every **visual line** in the document is a separate DOM element styled according to its distance `d` from a fixed **focal zone** at `FOCAL_RATIO` down the viewport.

- **Stable zone** (`|d| < EDGE`): element's own **type-colour** (see §5), full opacity, base font size
- **Top edge zone** (`d < -EDGE`): type-colour → yellow → lime → dark green, fading to `0.439` opacity, shrinking to `0.72×` at `d = -1`
- **Bottom edge zone** (`d > +EDGE`): type-colour → yellow → orange → dark red, fading to `0.439` opacity, growing to `1.78×` at `d = +1`
- Yellow `#f2c62a` appears as a transitional colour in both edge zones; it is not the stable colour
- **Rich elements** (separators, critters, media buttons, html-assets): opacity + scale only — no colour applied, their internal SVG colours are untouched
- The effect is scroll-driven only — no CSS transitions, no timers on text

---

## 2. Gradient System

One `requestAnimationFrame` loop drives **six shared gradient elements** defined once in the page `<defs>`. All SVG strokes reference one of these by ID. The loop updates only six `gradientTransform` attributes per tick regardless of how many decorated elements are on the page.

### 2.1 Stop Palettes

**Shimmer** — 11-stop fire palette:
```
#00000000  #44220438  #69190d70  #a52c16a8  #eb7513e0
#f2c62aff
#5e9a0ee0  #0e4d0ea8  #07372070  #44220438  #00000000
```
Offsets: 0% 10% 20% 33% 44% 55% 66% 77% 88% 94% 100%

**Shine** — 3-stop white flash:
```
#e8e2da00  #e8e2daff  #e8e2da00
```

### 2.2 The Six Shared Gradients

All use `gradientUnits="objectBoundingBox"`. Stops are **defined fully inline** on each element — no `href` cross-references (better browser compatibility). Rotation pivot is always `(0.5, 0.5)`.

| ID | Stops | Category | Angle offset |
|---|---|---|---|
| `shimmer-org-h` | Fire palette | Organics, wider than tall | +0° |
| `shimmer-org-v` | Fire palette | Organics, taller than wide | +90° |
| `shimmer-geo`   | Fire palette | Geometrics | +44° |
| `shimmer-sta`   | White shine  | Statics (shine suits bright structural elements) | +88° |
| `shimmer-oth`   | Fire palette | Everything else | +144° |
| `shine-org-h`   | White shine  | Organics h — shine variant | +0° |

### 2.3 The rAF Loop

```javascript
const GRAD_IDS = [
  { id: 'shimmer-org-h', off:   0 },
  { id: 'shimmer-org-v', off:  90 },
  { id: 'shimmer-geo',   off:  44 },
  { id: 'shimmer-sta',   off:  88 },
  { id: 'shimmer-oth',   off: 144 },
  { id: 'shine-org-h',   off:   0 },
]
const GRAD_BASE  = 360 / 32    // deg/s — quartered from earlier 360/8
const GRAD_HOVER = 360 / 2
const GRAD_CLICK = 720         // 360 / 0.5

let gradAngle = 0, gradSpeed = GRAD_BASE, gradTarget = GRAD_BASE, gradLast = null

function gradTick(ts) {
  if (gradLast === null) gradLast = ts
  const dt = Math.min((ts - gradLast) / 1000, 0.05)
  gradLast = ts
  gradSpeed += (gradTarget - gradSpeed) * Math.min(6 * dt, 1)
  gradAngle  = (gradAngle + gradSpeed * dt) % 360
  GRAD_IDS.forEach(({ id, off }) => {
    const a = (gradAngle + off) % 360
    document.getElementById(id)
      ?.setAttribute('gradientTransform', `rotate(${a.toFixed(2)},0.5,0.5)`)
  })
  requestAnimationFrame(gradTick)
}
```

**Scroll contribution** — called from the scroll handler:
```javascript
gradAngle = (gradAngle + scrollDeltaPx * 0.025) % 360
```

### 2.4 Per-Element Hover / Click

```javascript
function registerGradientInteraction(el) {
  el.addEventListener('mouseenter', () => { gradTarget = GRAD_HOVER })
  el.addEventListener('mouseleave', () => { gradTarget = GRAD_BASE  })
  el.addEventListener('touchstart', () => { gradTarget = GRAD_HOVER }, { passive: true })
  el.addEventListener('touchend',   () => { gradTarget = GRAD_BASE  }, { passive: true })
  el.addEventListener('click', () => {
    gradTarget = GRAD_CLICK
    setTimeout(() => { gradTarget = GRAD_BASE }, 600)
  })
}
```

---

## 3. SVG Asset Pipeline

All visual assets (separators, critters, animated logos) ship as `*-glow.sg` files produced by Inkscape. The page builder processes them before embedding.

### 3.1 Source Files

| Pattern | Role |
|---|---|
| `jl-site_separatorN-glow.svg` | Full-width decorative separator (N = 1-8), Insert a line break before and after this element |
| `jl-site_critterN-glow.svg` | Character (N = 1-3) SVG displayed beside a media button, OR on its own, aligned right, with a line break before and two line breaks after.  |
| `jl-site_logoN.svg` | Animated logo (N = 1-3). 1 is displayed centered, fullwidth with two linebraks before and after, 2 works like a critter, 3 is used like a large icon for cards and other elements |

### 3.2 Gradient Rewiring

Animated HTML files contain their own gradient animation loop using IDs named `glow-master` and `glow-applied-N`. These are rewired to the shared shimmer pool.

**Sublayer label → shared gradient mapping:**

| `inkscape:label` on sublayer | Shared gradient assigned |
|---|---|
| `organics-glow` | `shimmer-org-h` or `shimmer-org-v` (from viewBox aspect ratio) |
| `geometrics-glow` | `shimmer-geo` |
| `statics-glow` | `shimmer-oth` |

**Algorithm (Python):**

```python
def _rewire_glow(svg):
    org = 'shimmer-org-v' if height > width else 'shimmer-org-h'
    label_map = {
        'organics-glow':   org,
        'geometrics-glow': 'shimmer-geo',
        'statics-glow':    'shimmer-oth',
    }
    # Walk line-by-line, tracking active sublayer label
    # For each glow-applied-N id found in url(#...), assign its shimmer target
    # Then: replace all url(#glow-applied-N) → url(#shimmer-X)
    # Strip <linearGradient id="glow-master|glow-applied-N"> defs entirely
```

### 3.3 Separators and Critters — Inline Injection

After rewiring:

1. **Set dimensions**: `width="100%" height="100%"` — parent `.line` wrapper controls sizing via `em` units driven by the scroll system
2. **Scope IDs**: prefix every local `id`, `url(#...)`, `href="#..."` with `{s|c}{index}-` (e.g. `s0-path42`) to prevent cross-element ID collisions. Skip shared pool IDs (`shimmer-*`, `shine-*`)
3. **Strip** if the source is an html with <svg> elements, remove animated HTML file's own `<html>`, `<head>`, `<body>`, `<style>`, `<script>` and keep only the processed `<svg>` element

Result should be a clean SVG string stored in the `SVGS` dict.

### 3.4 HTML Assets — Iframe Injection

For `html-asset` block types (e.g. the animated logo), the **entire HTML file** is stored as-is in the `SVGS` dict. At runtime it is embedded via `iframe.srcdoc`, which allows the file's own JavaScript animation to run in an isolated context. No SVG extraction or gradient rewiring is applied.

---

## 4. SVGS Storage and the `</script>` Escape Rule

The `SVGS` dict is serialised with `json.dumps` and embedded directly in the page `<script>` block:

```javascript
const SVGS = { "jl-site_separator1": "<svg ...>...</svg>", ... }
```

**Critical:** After `json.dumps`, all `</` sequences must be replaced with `<\/` before embedding:

```python
svgs_json = json.dumps(svgs, ensure_ascii=False).replace('</', '\\/')
```

`json.dumps` correctly escapes backslashes, backticks, `${`, and quotes. The `<\/` replacement is additionally required because the browser's HTML tokeniser scans `<script>` blocks for the raw byte sequence `</script>` before any JavaScript parsing occurs. Any `</script>` appearing inside a JSON string value — including from an embedded animated HTML file — will terminate the script block prematurely, causing the remaining JS to render as visible page text.

`<\/` is valid JSON (the `\/` escape decodes to `/` at runtime), so all injected content is correct after JSON.parse.

The same `_safe_json()` helper is applied to `const BLOCKS` for future-proofing.

---

## 5. Per-Type Colours

Each text element type has a **base colour** used in the stable zone. Outside the stable zone, all types transition through the same ramps (starting from their base colour at the stable edge).

```javascript
const TYPE_COLORS = {
  h1:         '#eb7513',   // Tagesschrift — orange
  h2:         '#5e9a0e',   // Walter Turncoat — green
  h3:         '#5e9a0e',
  h4:         '#a52c16',   // Walter Turncoat — dark red
  h5:         '#a52c16',
  h6:         '#a52c16',
  blockquote: '#f2c62a',   // Protest Revolution — yellow
  paragraph:  '#e8e2da',   // Overlock — cream
}
```

Each `.line` element stores its base colour in `data-base-color="#rrggbb"`. The colour transform reads this and uses it as the `t=0` anchor for the ramp:

```javascript
function getTransform(d, bc) {
  bc = bc || { r:232, g:226, b:218 }   // cream fallback
  if (d > -EDGE && d < EDGE)
    return { color: `rgb(${bc.r},${bc.g},${bc.b})`, opacity: 1.0 }
  const cream = { r:232, g:226, b:218 }
  const ABOVE = [  // t=0 at stable edge (cream), t=1 at top of viewport
    { t:0.00, r:cream.r, g:cream.g, b:cream.b, a:1.000 },
    { t:0.25, r:242,     g:198,     b: 42,      a:1.000 },
    { t:0.50, r: 94,     g:154,     b: 14,      a:0.878 },
    { t:0.75, r: 14,     g: 77,     b: 14,      a:0.659 },
    { t:1.00, r:  7,     g: 55,     b: 32,      a:0.439 },
  ]
  const BELOW = [
    { t:0.00, r:cream.r, g:cream.g, b:cream.b, a:1.000 },
    { t:0.25, r:242,     g:198,     b: 42,      a:1.000 },
    { t:0.50, r:235,     g:117,     b: 19,      a:0.878 },
    { t:0.75, r:165,     g: 44,     b: 22,      a:0.659 },
    { t:1.00, r:105,     g: 25,     b: 13,      a:0.439 },
  ]
  if (d < -EDGE) return interpStops(ABOVE, (-d - EDGE) / (1 - EDGE))
  return interpStops(BELOW, (d - EDGE) / (1 - EDGE))
}
```

---

## 6. Inline Markup — Bold and Links

Text values in YAML may contain `**bold**` and `[link text](url)` (combinable as `**[bold link](url)**`). These are processed in two passes:

**Pass 1 — Measure (strip markers):**
`extractMarkup(raw)` walks the raw string, strips `**...**` and `[...](...)` markers, and records spans `{ start, end, type, href? }` in the clean string's coordinate space. Nested markup (link inside bold) is handled by recursing into the bold content via `_extractSpans`. The clean string is passed to Pretext for measurement.

**Pass 2 — Render (re-apply per line):**
`applyMarkupToLine(lineText, lineStart, spans)` builds an event list (open/close at span boundaries), sorts by position (closes before opens at same position), and walks a tag stack. When a span closes out of order (overlap case), it closes all tags above it in the stack, closes the target, then reopens the ones above. This produces valid nested HTML without invalid overlap.

```javascript
// Result examples:
// "**bold**"                    → <strong>bold</strong>
// "[link](url)"                 → <a href="url">link</a>
// "**text [link](url) more**"   → <strong>text <a href="url">link</a> more</strong>
```

---

## 7. Typography

```html
<link href="https://fonts.googleapis.com/css2?family=Overlock:ital,wght@0,400;0,700;1,400
&family=Tagesschrift&family=Walter+Turncoat&family=Protest+Revolution&display=swap"
rel="stylesheet">
```

| Role | Family | Weight | Pretext font string |
|---|---|---|---|
| Body / paragraph | Overlock | **400** | `"400 20px Overlock"` |
| Blockquote / quote | Protest Revolution | 400 | `"400 24px 'Protest Revolution'"` |
| H1 | Tagesschrift | 400 | `"400 56px Tagesschrift"` |
| H2–H6 | Walter Turncoat | 400 | `"400 36px 'Walter Turncoat'"` (H2), `28px` (H3–H6) |
| Mono / code | Courier | 400 | `"400 18px Courier"` |

Fonts are **never bold** unless the source text uses `**double stars**`. Body text is Overlock 400, not 700.

Base sizes (stored in `data-base-size`, used as Pretext `fontSize`):

| Type | px |
|---|---|
| paragraph | 16 |
| blockquote | 22 |
| H1 | 56 |
| H2 | 36 |
| H3–H6 | 28 |

---

## 8. Pretext Integration

```html
<script type="importmap">
{"imports":{"@chenglou/pretext":"https://esm.sh/@chenglou/pretext"}}
</script>
<script type="module">
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'
```

`COL` is set by ResizeObserver (§9) before `buildDOM()` is called. Text lines use `white-space: nowrap` — Pretext calculates wrap points once at base font size.

```javascript
function buildTextBlock(text, font, baseSize, extraClass, baseColor) {
  const { clean, spans } = extractMarkup(text)     // strip **bold** and [links]
  const prepared = prepareWithSegments(clean, font)
  const { lines } = layoutWithLines(prepared, COL, baseSize * LH)
  let pos = 0
  lines.forEach(l => {
    const div = makeTextLine(applyMarkupToLine(l.text, pos, spans), baseSize, baseColor)
    if (extraClass) div.classList.add(extraClass)
    area.appendChild(div)
    pos += l.text.length
    if (pos < clean.length && clean[pos] === ' ') pos++
  })
}
```

---

## 9. Init — ResizeObserver Pattern

`clientWidth` can return 0 when read synchronously inside an iframe before layout is flushed. `ResizeObserver` fires when the box model is ready.

```javascript
await document.fonts.ready
sc.addEventListener('scroll', () => {
  if (!ticking) { requestAnimationFrame(updateLines); ticking = true }
}, { passive: true })

let roInitialized = false
function doInit(w) {
  COL = w
  buildDOM(); updateLines()
  if (!roInitialized) { roInitialized = true; requestAnimationFrame(gradTick) }
}

new ResizeObserver(entries => {
  const w = entries[0].contentRect.width
  if (w <= 0) return
  if (!roInitialized) doInit(w)
  else if (Math.abs(w - COL) > 2) { COL = w; buildDOM(); updateLines() }
}).observe(areaEl)

// Fallback: if layout already available synchronously
const _w0 = areaEl.getBoundingClientRect().width
if (_w0 > 0 && !roInitialized) doInit(_w0)
```

ResizeObserver also handles container resize — no separate `window.resize` listener needed.

---

## 10. Rich Element Load / Unload - NEEDS DEBUGGING

Rich elements (separators, critters, media buttons, html-assets) are lazily inserted and removed as the user scrolls.

### Load trigger
- `LOAD_M = 2 × BASE_LINE_PX` (60px) — element must be this far inside the container to load
- **Direction bias**: if scrolling toward an element and it is within `2 × LOAD_M` of the edge it's approaching from, load it early so it's settled before reaching the focal zone

```javascript
const elTop        = el.offsetTop
const enteringBottom = delta > 0 && elTop > scrollTop + vh - LOAD_M*2 && elTop <= scrollTop + vh
const enteringTop    = delta < 0 && elTop < scrollTop + LOAD_M*2     && elTop >= scrollTop
const clearlyInView  = elTop >= scrollTop + LOAD_M && elTop <= scrollTop + vh - LOAD_M
const shouldLoad     = clearlyInView || enteringBottom || enteringTop
```

### Unload trigger
- `KEEP_M = 6 × BASE_LINE_PX` (180px) — element must scroll this far outside the viewport before unloading
- Uses **element bottom edge** (`el.offsetTop + el.offsetHeight`) so long elements (e.g. credit tables) stay loaded while being read

```javascript
const bot    = elTop + el.offsetHeight
const inKeep = bot >= scrollTop - KEEP_M && elTop <= scrollTop + vh + KEEP_M
if (loaded && !inKeep) removeRichContent(el)
```

### Entrance / exit animation
- **In**: `opacity 0→1`, `scale 0.88→1` over 880ms, cubic-bezier spring `(0.34, 1.56, 0.64, 1)`
- **Out**: `opacity 1→0`, `scale 1→0.88` over 400ms ease; element cleared after 420ms

### Unload guard
`data-anim="out"` is set when an exit animation begins and cleared when the DOM is cleaned up. Load checks bail if this flag is set, preventing a re-load triggering during an exit animation (which would cause a flicker at boundary scroll positions).

---

## 11. Keyboard Scroll

The scroll container responds to keyboard input:

| Key | Behaviour |
|---|---|
| `↑` / `↓` | Scroll one line (30px), instant |
| `Space` / `PageDown` | Scroll 88% of viewport height, smooth |
| `Shift+Space` / `PageUp` | Scroll 88% of viewport height up, smooth |
| `Home` | Jump to top, smooth |
| `End` | Jump to bottom, smooth |
| `Escape` | Close lightbox |

Input is suppressed when focus is inside `<input>`, `<textarea>`, or `contenteditable`. Also suppressed while the lightbox is open (except Escape).

---

## 12. Layout and CSS

```css
body { background: transparent; }  /* iframe-ready — no opaque background */

#scroll-container {
  height: 100vh;
  overflow-y: scroll;
  scroll-behavior: auto;
}

#content-area {
  width: 88%;          /* relative — fills the iframe's viewport */
  max-width: 680px;    /* caps at design width on wide screens */
  margin: 0 auto;
  padding: 30vh 0;
  overflow: visible;   /* allow growing text to extend beyond column */
}

.line {
  display: block;
  line-height: 1.5;
  white-space: nowrap;         /* Pretext wraps once at base size; browser must not re-wrap */
  will-change: color, opacity, font-size;
  overflow: visible;
}
.line a         { color: #5e9a0e !important; text-decoration: underline; }
.line a:hover   { color: #eb7513 !important; }
.line a:visited { color: #a52c16 !important; }

/* Rich wrappers — height in em so they scale with scroll-driven font-size */
.rich-line      { display: block; overflow: visible; will-change: opacity, font-size; }
.separator-line { height: 1em;  display: flex; align-items: center; justify-content: center; }
.critter-line   { height: 4em;  display: flex; align-items: center; gap: 0.8em; }
.button-line    { height: 2em;  display: flex; align-items: center; }

/* Credits tables — sit inside .line with white-space override */
.table-block    { white-space: normal !important; overflow-x: auto; padding: 0.5em 0; }
.credits-table  { width: 100%; border-collapse: collapse; font-size: 0.82em; }
.credits-table th { opacity: 0.55; font-weight: 400; text-transform: uppercase;
                    font-size: 0.78em; letter-spacing: 0.08em; border-bottom: 1px solid rgba(232,226,218,.15); }
.credits-table td { padding: 0.16em 1.2em 0.16em 0; vertical-align: top; line-height: 1.35; }

/* HTML-asset iframe */
.html-asset-line { display: flex !important; height: auto !important;
                   align-items: center; justify-content: center; padding: 1em 0; }
.html-asset-line svg { max-width: 100%; height: auto; display: block; }

/* Media caption */
.media-caption { font-size: 0.82em; font-style: italic; opacity: 0.6;
                 white-space: normal; line-height: 1.4; padding: 0.3em 0 0.6em; }
```

---

## 13. Content Schema — `*-content.yaml`

Pages are authored in YAML and built to HTML by `contentpage-builder.py`. The template file is `contentpage-template.yaml`.

### Meta

```yaml
meta:
  title: "Page Title"
  slug: page-slug      # output filename: page-slug.html
```

### Block Types

| `type` | Required fields | Notes |
|---|---|---|
| `heading` | `level` (1–6), `text` | Supports inline `**bold**` and `[link](url)` |
| `paragraph` | `text` | YAML `>` for flow, `\|` to preserve explicit line breaks |
| `special` | `text` | Renders in Protest Revolution / `#f2c62a`. Optional `attribution` string. |
| `separator` | `svg` | SVG key string matching a registered asset (e.g. `jl-site-separator5.svg`) |
| `critter` | `svg` | SVG key string matching a registered asset (e.g. `jl-site-critter2.svg`) |
| `media` | `src` | Renders as a media button → lightbox. Optional `critter` (SVG key), `caption` and `text` (button label). |
| `link-row` | `links` | Array of `{text, href}` objects. Renders as a flex row of styled links. |
| `gallery` | `src`, `text` | Renders as a media button → lightbox. Optional `critter` (SVG key) |
| `image` | `src`, `alt-text` | Renders centered either 100% or fit to container width. |
| `thumbnail` | `src` | Renders in a centered circle with shimmer stroke and either 100px wide or fit to container width. |
| `button` | `text`, `href` | |
| `table` | `headers`, `row` | [comma], [separated], [cells]. Pretext should render row-by-row just like line-by-line  |
| `html-asset` | `text`, `href` | For injecting pre-built animated HTML assets. Inserted inserted inline — builder renders the HTML asset directly |

### Inline Formatting (inside `text:` values)

| Pattern | Output |
|---|---|
| `**bold text**` | `<strong>bold text</strong>` |
| `[label](url)` | `<a href="url">label</a>` |
| `**[bold link](url)**` | `<strong><a href="url">bold link</a></strong>` |
| `**text [link](url) more**` | `<strong>text <a href="url">link</a> more</strong>` |

YAML scalar style guide:
- `text: >` — folded: single newlines → spaces. Use for all prose.
- `text: |` — literal: newlines preserved. Use only for sign-offs or verse.
- `text: "..."` — quoted: for short single-line values.

---

## 14. Page Builder — `contentpage-builder.py`

A standalone Python GUI (`tkinter`). Requires `pyyaml` (`pip install pyyaml`). No separate template file needed — the HTML template is hardcoded.

### GUI

- **SVG Assets Dir**: folder containing `.svg` and `*-animated.html` files
- **Output Dir**: where `slug.html` files are written
- **Queue**: accepts individual files or whole folders (prefers `*-content.*` files)
- **Build Selected / Build All**: run in a background thread; log coloured green/yellow/red

### Build Pipeline

1. Parse `*-content.yaml` (or legacy `*-content.md`) → `meta`, `blocks`
2. Walk blocks, load and process assets from the SVG Assets Dir → `svgs` dict
3. For separators/critters: `extract_from_animated_html()` → rewire → scope → clean SVG string
4. For html-assets: `_load_html_asset()` → raw HTML file (iframe srcdoc will run it as-is)
5. Substitute `__TITLE__`, `__BLOCKS__`, `__SVGS__` into hardcoded template
6. `_safe_json()` on all embedded JSON: `json.dumps` + `.replace('</', '\\/')`
7. Write `{slug}.html` to output dir

### Asset Search Order

For each SVG key, the builder tries in order:
1. `{key}-glow.svg` (exact)
2. Fuzzy: any `*.svg` whose stem contains `key`
3. Fuzzy: any `*-animated.html` whose stem contains `key`

Missing assets are logged as `WARN` and the block renders with a white box in place of its visual element.

---

## 15. Miscellaneous Notes for Agents

1. **`COL` is dynamic** — measured by ResizeObserver, not a constant. Never hardcode 680 as a layout width.
2. **Every visual text line** is `<div class="line" data-base-size="N" data-base-color="#rrggbb">` — one div per Pretext output line, never per paragraph.
3. **`white-space: nowrap`** on `.line` is intentional. Pretext calculated the wrap; the browser must not redo it as font-size changes.
4. **Rich elements** are `<div class="line rich-line {type}-line" data-rich="true">` — height in `em` multiples, lazy-loaded on scroll.
5. **Anchor point**: text lines use centre-Y; rich elements use top-edge Y.
6. **Stable zone** is per-type coloured (see §5), not uniformly cream. Cream is the paragraph/default fallback only.
7. **Ramps start from cream** at the stable-zone boundary, regardless of each element's type colour. Type colour is the *stable* state; outside the zone everything fades through the same palette.
8. **Gradient base speed is 360°/32s** (not 360°/8s). Hover: 360°/2s. Click: 360°/0.5s.
9. **Six shared gradients** with inline stops (no `href`). Shimmer pool: `shimmer-org-h/v`, `shimmer-geo`, `shimmer-sta`, `shimmer-oth`. Shine: `shine-org-h`.
10. **Load zone**: 2-line margin inside viewport + direction-bias pre-load. **Unload zone**: 6-line buffer outside, measured to element bottom edge.
11. **`data-anim="out"` guard** on rich elements — prevents re-load during exit animation.
12. **`</` → `<\/`** in all embedded JSON — the HTML tokeniser terminates `<script>` blocks on the literal bytes `</script>` regardless of JS string context.
13. **Inline markup** (`**bold**`, `[link](url)`) is stripped before Pretext measurement and re-applied line-by-line after layout, using a span-stack renderer that handles nested/overlapping markup correctly.
14. **Table cells** support `*(italic)*` (single-star, CSS-em) and `**bold**` — bold is applied first to avoid asterisk bleed.
15. **Background is `transparent`** — pages live inside iframes. The lightbox inner is the only element with `background: #000`.
16. **HTML-asset blocks** use `iframe srcdoc` — the full HTML file is embedded; the iframe's own JS runs normally. Do not attempt innerHTML injection of full HTML documents.
17. The deliverable is a **single self-contained HTML file** per page, with all content and SVG data embedded as JSON. No external files needed at render time except fonts (Google Fonts CDN) and Pretext (esm.sh).
