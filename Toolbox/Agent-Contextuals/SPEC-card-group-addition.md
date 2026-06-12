# tags: [spec, card-group, block-type, builder-notes, v0.1]
# Append this to SPEC-content-schema.md under "Block Types"
# Written for the builder-refinement agent.

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
# tags: [spec, card-group, block-type, builder-notes, v0.1]
