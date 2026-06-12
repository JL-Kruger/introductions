# Content Schema — `*-content.yaml`

**Replaces** the current hybrid markdown/custom-tag `.md` format.  
**Goal:** machine-readable, human-editable, unambiguous block structure.

---

## Format

YAML with a metadata header and an explicit `blocks` list.  
Every block has a `type` field. All text values support inline markdown for `**bold**` and `[link text](url)` only — nothing else.

---

## Full Example

```yaml
meta:
  title: My Argument
  slug: my-argument
  description: A case for working together on civic education.

blocks:

  - type: heading
    level: 2
    text: "In favor of working together."

  - type: separator
    svg: sep5

  - type: quote
    text: >
      For the better part of two decades, I have found myself forever
      preoccupied with how humans create vibrant communities of engaged
      citizens who know how to make positive change actually happen.
    attribution: "TLDR for the Article Below."

  - type: paragraph
    text: >
      Healthy democracy requires an engaged citizenry actively choosing to
      keep it alive with every election and by-election.

  - type: paragraph
    text: |
      My lived experience has taught me what it feels like when the entire
      system seems set up to either exploit you, ensnare you or end you,
      when you and your friends sit there wondering
      [what can we do?](https://www.youtube.com/@therenegadelens)
      and every attempt seems to fall apart.

  - type: media
    critter: crit2.svg
    src: "https://1drv.ms/v/c/524eeedbb443c4e2/IQTixEO02-5OIIBSsHQAAAAAAbw7n-U7IVFXR_-eNAmnhio"
    text: "Video: Renegade Lens"

  - type: paragraph
    text: >
      Success, to me, is establishing measurable, practical means by which
      hope and agency can be demonstrably restored to youth facing a far
      more daunting future than I was at their age.

  - type: separator
    svg: sep6

  - type: link-row
    links:
      - text: Email
        href: "#email"
      - text: Current Projects
        href: "#projects"
      - text: Skills & Rates
        href: "#skills"
      - text: Work History
        href: "#work"
      - text: Communities & Collaborators
        href: "#communities"
```

---

## Block Types

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

---


## Block Type: `card-group`

A horizontal (wrapping) row of clickable cards. Each card opens a lightbox
panel containing its `content` blocks. Designed for Skills & Rates tables
but reusable anywhere a set of expandable content panels is needed.

---

### YAML structure

```yaml
- type: card-group
  stroke: shimmer-org-h      # gradient pool ID — see DESIGN.md §4 shared pool
  fill: transparent          # CSS color, rgba string, or palette token name
  cards:
    - title: "Card Title"
      description: "Optional one-line teaser shown on the card face."
      content:               # blocks rendered inside the lightbox panel
        - type: table
          rates_public: true # [rates-block] — see rate-visibility note below
          headers: [Col A, Col B, Col C]
          rows:
            - [cell, cell, cell]
        - type: paragraph
          text: "Optional supporting text inside the lightbox."
```

---

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `stroke` | no | string | Any ID from the shared gradient pool (shimmer-org-h, shimmer-org-v, shimmer-geo, shimmer-sta, shimmer-oth, shine-org-h). Defaults to `shimmer-org-h`. `"none"` suppresses the border. |
| `fill` | no | string | CSS color value or palette token name (soil, pigment, rust, fire, sun, light, meadow, forest, jungle). Defaults to `transparent`. Use `rgba(255,255,255,0.03)` for the content-hub card lift. |
| `cards` | yes | list | One or more card objects. |
| `cards[].title` | yes | string | Inline markdown allowed (bold, link). Walter Turncoat, --light. |
| `cards[].description` | no | string | Short teaser line. Overlock, --light 70% opacity. |
| `cards[].content` | yes | list | Any block types from the main schema. The builder renders these into the lightbox panel. `card-group` may not nest inside `content`. |

---

### Rendering — card face

Follows the content-hub card pattern (DESIGN.md §5.3) with configurable
stroke and fill instead of fixed values:

```
┌─ SVG rect, stroke: url(#{stroke}), fill: {fill} ─────────────┐
│  Card Title          Walter Turncoat, --light, ~1.2rem        │
│  Description text    Overlock, --light 70% opacity, ~0.9rem   │
│                                                               │
│  ▶ Open →            --meadow link, Overlock, small           │
└───────────────────────────────────────────────────────────────┘
```

- Card width: fluid, minimum 240px, wraps at container edge
- Hover: `gradTarget = GRAD_HOVER` on the card's SVG rect. No transform,
  no shadow, no movement (DESIGN.md §1 philosophy).
- `registerGradientInteraction(cardEl)` must be called on each card wrapper.

---

### Rendering — lightbox panel

Reuses the existing lightbox overlay (`#lightbox`, `#lightbox-inner`).
The panel replaces the iframe with a scrollable content column.

Builder implementation notes:

1. **Extend lightbox open/close** — add a `data-card-content` attribute to
   each card's trigger element containing a JSON-serialised array of
   pre-rendered HTML blocks (rendered at build time, not at runtime).
   On click, the JS inserts that HTML into `#lightbox-inner` and opens
   the overlay. This avoids runtime YAML parsing in the browser.

2. **Lightbox inner for cards** — swap `aspect-ratio: 16/9` for
   `max-height: 85vh; overflow-y: auto; width: min(90vw, 680px)` when
   the lightbox is opened by a card (not a media button). A `data-mode`
   attribute on `#lightbox` (`data-mode="media"` vs `data-mode="card"`)
   can drive this via CSS.

3. **Block rendering inside content** — the builder already knows how to
   render every block type. For `card-group` content blocks, run them
   through the same renderer and capture the HTML output as a string.
   Escape it for JSON embedding in `data-card-content`.

4. **`rates_public` flag** — the builder should check this flag on any
   `table` block inside `cards[].content`. If `false`, replace the table
   with the standard "rates on request" button (see toggle script note
   in the main schema). If `true`, render normally.

5. **No-JS fallback** — each card should render as a `<details>`/`<summary>`
   element in a `<noscript>` context, or the content blocks should be
   included statically below the card and hidden via JS on load
   (`el.style.display = 'none'`). This ensures content is accessible
   without JS.

6. **Shimmer border** — the card SVG `<rect>` uses
   `stroke: url(#{stroke-id})` where `stroke-id` comes from the YAML
   `stroke` field. Validate against the known pool IDs at build time
   and warn if unrecognised. `"none"` → omit the SVG rect entirely.

7. **Fill** — map palette token names to hex at build time using the
   palette from DESIGN.md §2. Pass through any valid CSS color string
   unchanged. Default: `transparent`.

---

### Spacing

Same as other block types: 1 line after the card-group block.
Internal card spacing: builder's discretion — suggest `gap: 1em` in the
flex/grid container.

---

### Example — SkillsRates page usage

```yaml
- type: heading
  level: 2
  text: "Consulting & Institutional"

- type: card-group
  stroke: shimmer-org-h
  fill: rgba(255,255,255,0.03)
  cards:
    - title: "Stakeholder Communications & Content Strategy"
      description: "Research, writing and strategic framing for complex audiences."
      content:
        - type: table
          rates_public: true
          headers: [Engagement, Standard, Partner Rate]
          rows:
            - [Day rate, "$500", "$340"]
```


---
## Inline Formatting (inside `text` values)

| Pattern | Output |
|---|---|
| `**bold text**` | `<strong>bold text</strong>` — renders at font weight 700 |
| `[label](url)` | `<a href="url">label</a>` — green / orange hover / red visited |

No other markdown is supported. Headings, lists, code blocks, etc. are all handled as explicit block `type` values, not markdown syntax.

---

## Multi-paragraph Paragraphs

Use multiple `paragraph` blocks rather than blank lines within a single block.  
The page builder maps one YAML `paragraph` block to one visually separated chunk.

```yaml
# DO THIS:
  - type: paragraph
    text: First paragraph text.

  - type: paragraph
    text: Second paragraph text.

# NOT THIS:
  - type: paragraph
    text: |
      First paragraph text.

      Second paragraph text.
```

---

## Migration from `*-content.md`

| Old pattern | New block |
|---|---|
| `# Title` | `meta.title` (page metadata, not a block) |
| `## Heading` | `{type: heading, level: 2, text: ...}` |
| `<quotation-text>...<quote/author>attr</quote-author></quotation-text>` | `{type: quote, text: ..., attribution: ...}` |
| `<iframe src="...">` | `{type: media, src: ...}` |
| `---` | `{type: separator, svg: ...}` |
| `[Label1] [Label2] ...` | `{type: link-row, links: [...]}` |
| Plain paragraph text | `{type: paragraph, text: ...}` |

---

## Parser Notes (for JS page builder)

```javascript
import yaml from 'js-yaml'   // or use a minimal YAML parser

const doc = yaml.load(fileContent)
const meta   = doc.meta    // { title, slug, description }
const blocks = doc.blocks  // array of typed block objects
```

Text pre-processing before Pretext measurement:
1. Strip `**` markers → pass plain text to Pretext (measure at base weight)
2. Strip `[text](url)` → pass only `text` to Pretext
3. After layout, re-apply `<strong>` and `<a>` tags using character-position mapping

Inline bold note: since Pretext measures at a single font weight, `**bold**` text
measured at 400 weight will be slightly narrower than rendered at 700 weight.
For most uses this is acceptable. If precision is needed, measure the bold
segments separately and account for the width delta in the layout pass.

---

## Spacing Config

For the purposes of Pretext and other rendering, spacing between blocks is set as some number of lines before or after a given element. 

- default spacing: 1 line after every block.
- exceptions: H1: 2 lines before 1 line after, separator: 1 line before 2 lines after, critter:1 line before 2 lines after, special: 1 line before 1 line after, media: 1 line before, 1 line after, image: 1 line before, 1 line after.

---
