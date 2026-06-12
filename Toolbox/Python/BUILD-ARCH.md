# BUILD-ARCH.md — single-entrypoint `build.py` architecture

**Status:** spec for sign-off · design only (no `build.py` written this pass)
**Author tier:** Architect (Opus) · **Phase:** 0 — Foundations
**Supersedes:** `homepage-builder.py`, `contenthub-builder.py`, `contentpage-builder.py`,
`gallery-builder.py`, `svg-assets-builder.py`, `sitebuilder-server.py` + `sitebuilder-ui.html`

Goal: one `python3 build.py` that **scans the asset/content/YAML folders and emits the
whole static site**, replacing five `*-builder.py` entrypoints plus the preview server.
`builder_common.py` survives as the shared primitive layer; the per-page entrypoints
collapse into render modules orchestrated by `build.py`.

This document is the contract. It does **not** change the look — see §5 for why the first
landing of `build.py` must be a *byte-for-byte* refactor, with the aesthetic phases (sprite,
fonts, pretext, tokens, vines) layered on top afterward, each re-verified.

---

## 0. What exists today (ground truth the design must absorb)

| Entrypoint | Input | Output | Uses `builder_common`? |
|---|---|---|---|
| `homepage-builder.py` | `site.yaml › homepage` | `/index.html` | yes |
| `contenthub-builder.py` | `site.yaml › contenthub` | `/content.html` | yes |
| `contentpage-builder.py <yaml>` | `*-content.yaml` (6 files) | `Content/**/<slug>.html` | yes |
| `gallery-builder.py <folder>` | `Media/Images/<folder>/` | `Media/Images/<folder>.html` | **no — self-contained, own CSS + own Google-fonts link + own palette** |
| `svg-assets-builder.py` | `Media/SVG-Assets/critter*+separator*` | `js/svg-assets.js` (151 KB) | no (predecessor of the seams) |
| `sitebuilder-server.py` + `-ui.html` | the above, via HTTP | local control panel | n/a |

Gaps found while reading (the new builder closes them):
- **`404.html` is orphaned.** `site.yaml › placeholder` exists and is shaped exactly like
  `contenthub`, but **no builder consumes it**; committed `404.html` is stale (May 24,
  121 KB, hand-built). build.py must own a `placeholder → /404.html` stage.
- **Galleries are off-system.** `gallery-builder.py` duplicates the palette, hardcodes the
  Google-fonts `<link>`, and the dropped frame-era background SVG. It must route through the
  same head/token/font path as every other page (Phase 4 work; the *scan slot* is defined now).
- **Two content YAMLs (`WorkHistory`, `CollaboratorsCommunities`) carry `meta.dest`**; the
  other four rely on `SLUG_TO_DIR`. Both paths stay supported.
- **Legacy Writings pages** (`doomy-mcdoomface.html`, `escape-annotated-v2.html`, … — 11 of
  the 12 files in `Content/Writings/`) have **no `*-content.yaml`**. They are hand-built
  artifacts the scan must **leave untouched** (see §3, "scan is additive, never destructive").

---

## 1. Pipeline stages (scan → transform → emit)

Three stages, run once per invocation. Everything is pure-Python + PyYAML (no new deps).

```
                 ┌── SCAN ──────────┐   ┌── TRANSFORM ────────┐   ┌── EMIT ──────────┐
 folders/YAML ─► │ discover work    │ ► │ YAML→model, paths,  │ ► │ render HTML/CSS, │ ► committed
                 │ units (plan)     │   │ SVG hygiene, ids    │   │ write_output     │   files
                 └──────────────────┘   └─────────────────────┘   └──────────────────┘
```

### Stage A — SCAN (`scan.py` → a `BuildPlan`)
Pure discovery: read the filesystem + `site.yaml`, produce an in-memory list of **work units**.
No HTML, no file writes. Inputs / outputs:

| Source scanned | Produces work unit(s) |
|---|---|
| `site.yaml › homepage` | 1 × `PageUnit(kind=home  → /index.html)` |
| `site.yaml › contenthub` | 1 × `PageUnit(kind=hub   → /content.html)` |
| `site.yaml › placeholder` | 1 × `PageUnit(kind=placeholder → /404.html)` |
| `Toolbox/Python/*-content.yaml` | N × `ContentUnit(yaml → dest from meta.dest or SLUG_TO_DIR)` |
| `Media/Images/*/` (immediate subdirs) | N × `GalleryUnit(folder → Media/Images/<name>.html)` |
| `Media/SVG-Assets/*.svg` (critters, separators, vines) | 1 × `SpriteUnit(→ Media/sprite.svg)` |
| `variables.yaml` | `TokensUnit(→ css/tokens.css)`, font manifest (Phase 0+) |
| static `css/*.css`, `js/*.js` | passthrough (hashed for `?v=`, not regenerated) |

The plan is **deterministic and order-independent**; the scan result is what `--list` prints
and what the (optional) preview UI renders. This is the seam that replaces
`sitebuilder-server.py`'s hardcoded `BUILDERS` dict + its `content_yamls()` /
`gallery_folders()` discovery — discovery now lives in one place and the server (if kept) reads
the plan instead of duplicating it.

### Stage B — TRANSFORM (per unit → a render-ready model)
Exactly the work the current builders do between "load YAML" and "f-string the HTML":
- resolve every path through `set_rel_prefix` + `norm_path`/`asset_url` for the unit's depth,
- `transform_block()` for content pages (heading ids, media normalisation, validation),
- collect SVG ids (`collect_svgs`), build section nav,
- SVG hygiene for the sprite (`strip_editor_junk` / `strip_gradient_defs` / `rewire_strokes`).

Transform **must not write files** and **must not depend on emit order** — a content page's
model is computed the same whether or not the sprite has been emitted yet. (Ordering is handled
in §1's emit sequence, not by side effects.)

### Stage C — EMIT (model → bytes on disk)
- shared assets first: `css/tokens.css`, `Media/sprite.svg`, font CSS — these are referenced
  by every page, so emit before pages (a page's `?v=` hash covers them).
- then each `PageUnit` / `ContentUnit` / `GalleryUnit` via `write_output`.
- every write prints `Wrote <path> (<n> bytes)` exactly as today (parity of console output is
  not required, but keep it for the operator).

**Emit order (fixed):** `tokens.css` → `sprite.svg` → fonts → home → hub → placeholder →
content pages → galleries. Rationale: assets before consumers so `asset_version()` is stable
within a run, and pages last so a sprite/token error fails the build before any page is written.

---

## 2. Module boundaries & `builder_common.py` seam disposition

### Layout
Keep everything under `Toolbox/Python/`. Introduce a thin orchestrator + a `builders/` package;
`builder_common.py` stays the primitive layer (low-level, page-agnostic).

```
Toolbox/Python/
  build.py                 # NEW. CLI + orchestrator only: parse args, scan(), emit loop, report.
  builder_common.py        # KEPT. Primitives (paths, esc, SVG hygiene, head, navbar, write).
  builders/                # NEW package. One module per render concern; each exports build(unit).
    scan.py                #   filesystem+site.yaml → BuildPlan (replaces server's BUILDERS dict)
    homepage.py            #   ← homepage-builder.py body (render only)
    contenthub.py          #   ← contenthub-builder.py body
    placeholder.py         #   NEW. site.yaml › placeholder → 404.html (reuses contenthub render)
    contentpage.py         #   ← contentpage-builder.py body (transform_block, assemble, …)
    gallery.py             #   ← gallery-builder.py, re-pointed at builder_common head/tokens/fonts
    sprite.py              #   NEW (Phase 0 Sonnet). SVG-Assets → Media/sprite.svg <symbol>s
    fonts.py               #   NEW (Phase 0 Sonnet). variables.yaml → @font-face + preload, woff2
    tokens.py              #   NEW (Phase 0 Opus). extended token system (was tokens_css())
  build_ui.py              # NEW. stdlib tkinter GUI for the non-technical operator:
                           #   lists scan units, runs build.py --only <unit>, supports
                           #   batch (build-all) + per-unit runs; replaces the HTTP server.
  site.yaml, variables.yaml, *-content.yaml   # unchanged authoring inputs
```

**`build_ui.py` (replaces `sitebuilder-server.py` + `sitebuilder-ui.html`).** A stdlib-only
`tkinter` window — no browser, no localhost port, no HTTP surface to reason about. It calls
`scan.build_plan()` to populate a list of work units (so it never duplicates a `BUILDERS`
dict — discovery stays single-sourced in `scan.py`), and each button shells
`python3 build.py --only <unit>` (or `--all` for batch), streaming stdout into a text pane.
It is a **dev/authoring tool, not part of the site or the build path**; the canonical
interface remains `python3 build.py`. Same security posture as before comes for free: no
network listener at all, every run is an argument list (never `shell=True`).

`build.py` itself stays small: it owns argument parsing (`--root`, `--only <kind|slug>`,
`--list`, `--check`), calls `scan.build_plan()`, then dispatches each unit to its module. No
rendering logic lives in `build.py`. This keeps each module a clean single-workstream target a
Builder (Sonnet) can own without touching the orchestrator.

### `builder_common.py` seam disposition

| Seam | Disposition | Notes |
|---|---|---|
| `set_rel_prefix`, `asset_url`, `norm_path`, `fallback_href` | **REUSE as-is** | Per-page relative-path discipline is load-bearing (GitHub Pages sub-path). Do not regress to root-absolute. |
| `asset_version` | **REUSE, widen** | Already hashes `js/*` + `css/*`. Extend its glob to include `Media/sprite.svg` and self-hosted font files so a sprite/font change busts caches. |
| `esc`, `slugify`, `norm_asset_id`, `load_yaml`, `project_root` | **REUSE as-is** | Core utilities. |
| `get_viewbox`, `org_shimmer_id`, `rewire_strokes`, `strip_gradient_defs`, `strip_editor_junk` | **REUSE, retarget** | Move from "inline per page / bake into JS" to feeding the **`sprite.py`** emitter once. Same hygiene, single output. |
| `inline_svg` | **RETARGET** | Today inlines full SVG into each page. New role: used **only** by `sprite.py` to build `<symbol>` bodies. Pages stop inlining; they emit `<svg><use href="…/sprite.svg#id"/></svg>`. |
| `shared_defs_svg` | **REUSE, relocate** | The rotating gradient `<defs>` still needed by shimmer. Move the single copy into `sprite.svg`'s `<defs>` (or keep one inline `#shared-defs` block) instead of repeating per page. Decide in sprite spec; either way it is emitted **once**. |
| `frame_overlays(page_type)` | **RETIRE** | Frames dropped (locked decision). Replaced by the **vine-decor emitter** (Phase 2), a new function in `builders/` — not a rename of this one. Remove `_svg_path('…frame…')` calls. |
| `google_fonts_url` | **RETIRE** | Self-host kills the runtime Google link. Logic moves to `fonts.py`. |
| `head_block` | **RETARGET** | Drop the two `preconnect` + the `<link href=google_fonts>` lines; inject `fonts.py`'s `<style>@font-face</style>` (or `<link rel=stylesheet css/fonts.css>`) + `rel=preload` for the 2 critical faces. Keep the favicon line (swap to sprite/self-host as decided). Signature unchanged so callers don't move. |
| `tokens_css` / `write_tokens_css` | **EXTEND → `tokens.py`** | Grow `:root{}` from palette+5 layout vars into the full system: spacing scale, vertical rhythm locked to `--lh`, fluid type (`clamp()` ramp), content measure. Keep emitting `css/tokens.css`. |
| `render_navbar` | **REUSE as-is** | `home` and `standard` modes already cover home/hub/content/placeholder. |
| `sidebar_logo` | **RETARGET** | Switch its `inline_svg(...logo...)` to a `<use href=sprite#logo>` once the sprite carries the logo. Same wrapper/markup otherwise. |
| `asset_id_pool` | **RETARGET** | Reads ids from `js/svg-assets.js` today. Re-point to read `<symbol id>`s from `Media/sprite.svg` so content-page validation still catches unknown ids after the JS file is retired. |
| `write_output` | **REUSE as-is** | The one write primitive for all units. |

Nothing in `builder_common.py` is deleted in the parity pass; retirements happen in their own
phase commits (§5).

---

## 3. Folder-scan contract (assets/content/YAML → outputs)

The scan is **convention over configuration** and obeys three rules:

1. **Additive, never destructive.** The scan only *writes* outputs it can trace to a source
   (a YAML, an image folder, an SVG set). It never deletes or rewrites a file with no source —
   so the 11 legacy hand-built Writings pages are safe. (A `--prune` flag may be added later;
   default off.)
2. **Source path determines output path** via the existing prefix discipline; outputs are
   always relative-linked.
3. **One source of truth per output.** No output is produced by two units.

| Output | Source | Mapping rule |
|---|---|---|
| `/index.html` | `site.yaml › homepage` | fixed |
| `/content.html` | `site.yaml › contenthub` | fixed |
| `/404.html` | `site.yaml › placeholder` | fixed (**new**; reuses the hub renderer — same bento shape) |
| `Content/**/{slug}.html` | each `Toolbox/Python/*-content.yaml` | `meta.dest` if present, else `SLUG_TO_DIR[meta.slug]/{slug}.html`; error if neither resolves |
| `Media/Images/{name}.html` | each immediate subdir of `Media/Images/` | gallery of that folder's images (natural-sorted) |
| `Media/sprite.svg` | `Media/SVG-Assets/{critter*,separator*,vine*,logo*}.svg` | one sprite of `<symbol id=…>`; ids = filename minus `.svg`, `_`→`-` (`norm_asset_id`) |
| `css/tokens.css` | `variables.yaml › colors,layout,(spacing,type)` | regenerated every build |
| `css/fonts.css` + `css/fonts/*.woff2` | `variables.yaml › typography.fonts` + subset sources | self-hosted faces (Phase 0 fonts task) |
| `css/styles.css`, `css/content.css`, `css/content-page.css`, `js/*.js` | authored by hand | **passthrough** — hashed for `?v=`, never regenerated by build.py |

**`SLUG_TO_DIR`** (today hardcoded in `contentpage-builder.py`) moves into `scan.py` as the
canonical slug→folder map; `meta.dest` overrides it. New content pages get a one-line entry
there (or just set `meta.dest`).

**Discovery primitives** (lifted from `sitebuilder-server.py`, now the only copy):
`scan.content_yamls()` = `sorted(glob('Toolbox/Python/*-content.yaml'))`;
`scan.gallery_folders()` = sorted immediate subdirs of `Media/Images/`.

---

## 4. Named insertion points (where the later-phase features bolt in)

These are the exact seams the spec promises so Phase 0–2 Builders know where to land work
without re-architecting:

1. **`sprite.svg` emitter** → `builders/sprite.py : build_sprite(plan, root)`, called from
   `build.py` emit-stage **before any page**. Consumes `SpriteUnit`. Reuses the five hygiene
   seams. Output `Media/sprite.svg`. Retires `svg-assets-builder.py` + `js/svg-assets.js`.
   *Page-side insertion:* a `sprite_use(id, **attrs)` helper in `builder_common.py` emitting
   `<svg …><use href="{asset_url('/Media/sprite.svg')}#{id}"/></svg>` — this replaces every
   current `inline_svg(...)` call site in homepage/contenthub/contentpage `_critter`/`_logo`.

2. **Font self-host** → `builders/fonts.py : build_fonts(root)` (emits `css/fonts.css` +
   copies subset `woff2`), plus the retarget of `head_block` (§2). *Insertion in head:*
   the block currently spanning the two `preconnect` lines + the google `<link>` in
   `head_block` is the single replace site → preload(2 critical) + fonts stylesheet.

3. **Pretext vendoring** → drop `js/vendor/pretext.js` (vendored `@chenglou/pretext`); the
   insertion point is the literal line in `contentpage.assemble()`:
   `<script type="importmap">{"imports":{"@chenglou/pretext":"https://esm.sh/…"}}</script>`
   → delete the importmap; change the module import to
   `import { PretextEngine } from '{asset_url('/js/pretext-engine.js')}'` already local, and
   ensure `pretext-engine.js` imports the **local** vendored path. This is the only `esm.sh`
   reference in the tree; removing it satisfies "no third-party CDN at load."

4. **Extended token/layout system** → `builders/tokens.py : tokens_css()` (extends the current
   function). New `:root` groups append after the existing palette+layout block (so the parity
   diff is purely additive): `--space-*` scale, `--rhythm` (= `--lh`-locked), fluid `--step-*`
   type ramp, `--measure`. CSS files consume them; no page-template change required to land the
   variables, which keeps this decoupled from the layout-rebuild (Phase 3).

---

## 5. Migration: five entrypoints → one, with an OUTPUT-PARITY gate

The migration is staged so the risky part (consolidation) is provably safe **before** any
look-changing work, and each aesthetic change is independently verifiable.

### Step 0 — capture the baseline (do once, before touching anything)
Run the current builders for all YAML-driven outputs and snapshot:
```
homepage, contenthub, each of the 6 *-content.yaml, svg-assets, each gallery folder
```
Copy the resulting committed files to `Toolbox/Python/.parity-baseline/` (git-ignored).
These are the bytes `build.py` must reproduce.

### Step 1 — consolidate as a **pure refactor** (one commit)
Move each builder's body into its `builders/*.py` module **verbatim** (same f-strings, same
seams). `build.py` scans + dispatches. **No output may change.** Placeholder/404 is the one
*addition* (it had no prior output) — generate it and eyeball it, but it is excluded from the
byte-diff gate since there is no baseline.

**Parity gate (hard):**
```
python3 build.py --root .            # regenerate everything
diff -r index.html content.html Content/ Media/Images/*.html  .parity-baseline/
# plus: js/svg-assets.js identical until sprite.py lands
```
Must be **byte-identical** for index, content, the 6 content pages, the galleries, and
`svg-assets.js`. Any diff is a refactor bug, not an improvement — fix until clean.
Acceptance for Step 1 = empty diff + `404.html` newly produced from `placeholder`.

### Step 2..n — land each aesthetic change as its own commit, re-running the gate
Each of these **intentionally** changes specific bytes; verify the diff contains *only* the
expected change and nothing else:

| Commit | Expected diff (and only this) | Re-point baseline after |
|---|---|---|
| `sprite.py` + `<use>` | inline SVG blobs → `<use href=sprite#id>`; `svg-assets.js` deleted; pages shrink | yes |
| fonts self-host | google `<link>`+preconnect → preload+`fonts.css` in every `<head>` | yes |
| pretext vendor | `esm.sh` importmap line removed on content pages | yes |
| tokens extend | `css/tokens.css` grows (additive `:root` vars); pages unchanged | yes |
| gallery on-system | gallery `<head>` now uses shared head/tokens/fonts | yes |

After each verified commit, refresh `.parity-baseline/` so the *next* change diffs against the
new known-good state. This converts "did the look change correctly?" into a reviewable diff.

### Step 3 — delete the superseded files (final cleanup commit)
Once `build.py` reproduces everything: delete `homepage-builder.py`, `contenthub-builder.py`,
`contentpage-builder.py`, `gallery-builder.py`, `svg-assets-builder.py`. **Server retired**
(operator decision 2026-06-11): delete `sitebuilder-server.py` + `sitebuilder-ui.html`; the
click-to-build affordance moves to the stdlib `tkinter` `build_ui.py` (§2), which reads `scan`'s
`BuildPlan` and shells `build.py --only <unit>` / `--all`. Update `AGENTS.md` §1
"Build / preview" to the single command (`python3 build.py`; optional GUI via `build_ui.py`).

### Build order for a full run (what `python3 build.py` does)
`scan` → emit `tokens.css` → `sprite.svg` → `fonts` → `index` → `content` → `404` →
content pages → galleries → print summary (counts + total bytes).

### Verifying parity is meaningful, not just equal
The diff gate proves consolidation didn't alter output. Separately, after Step 1, **open
`index.html` + one content page from a `file://` sub-path** and confirm relative links resolve
(the whole reason for the `_PREFIX` discipline) — a thing byte-diff cannot catch if both old
and new are wrong identically.

---

## 6. Dependency / risk decisions — RESOLVED (operator sign-off 2026-06-11)

**No new runtime or build dependency is introduced** by this architecture. PyYAML (already
vendored in `.venv`) remains the only third-party import; the new GUI is stdlib `tkinter`.
Decisions, as ratified:

1. **Module layout: `builders/` package.** ✅ **APPROVED.** One module per output type; each
   Phase-0/2 task is a clean single-file workstream for a Builder. (BUILD-ARCH §2.)

2. **Preview server: SCRAPPED, replaced by tkinter GUI.** ✅ **DECIDED.** Delete
   `sitebuilder-server.py` + `sitebuilder-ui.html`; the click-to-build + batch affordance moves
   to stdlib `tkinter` `build_ui.py` (§2), which reads `scan`'s `BuildPlan` and shells
   `build.py --only <unit>` / `--all`. No HTTP listener, no port, no duplicate `BUILDERS` dict.

3. **Fail-closed on sprite / SVG-id errors.** ✅ **CONFIRMED.** `build.py --check` validates the
   sprite and content-page ids (via the retargeted `asset_id_pool`) and **aborts before emit**
   rather than shipping broken pages. A full `build.py` run runs `--check` implicitly first.

4. **`asset_version()` content-hash widening.** Accepted (flag-only): include `Media/sprite.svg`
   + the self-hosted woff2 in the hash so asset edits bust every page's `?v=`. Changes a query
   string only.

5. **Self-hosted woff2 sourcing: offline subsetting.** ✅ **APPROVED.** Subset `woff2` for
   Tagesschrift, Walter Turncoat, Overlock, Protest Revolution are produced **offline** with a
   dev-time tool (`fonttools`/`glyphhanger`) and **committed under `css/fonts/`**. `fonttools`
   never enters the build path or the site's dependency surface.

6. **Out of scope, flagged for a content decision (unchanged):** the 11 legacy Writings pages
   have no YAML source and are left as-is by the scan. Bringing them in = authoring N new
   `*-content.yaml` files (Phase 4), not a `build.py` change.

---

## Status

All §6 decisions resolved (operator sign-off 2026-06-11). Architecture is locked; ready to
implement. Implementation order: `build.py` + `builders/` parity refactor (Step 1 gate) →
`build_ui.py` → Phase-0 emitters (sprite, fonts, tokens) → pretext vendor, each re-verified
against the parity gate (§5). No site code changed by this spec.
