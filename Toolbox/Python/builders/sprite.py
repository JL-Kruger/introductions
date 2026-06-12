"""sprite.py — SVG sprite emitter (Phase 0).

Processes Media/SVG-Assets source files through the hygiene chain
(rewire_strokes → strip_gradient_defs → strip_editor_junk), then emits
Media/sprite.svg containing one <symbol> per decorative asset.  Pages
reference decor via <use href="Media/sprite.svg#id"> instead of inlining
SVG per page or duplicating data in js/svg-assets.js.

Glow filters (glow-filter-statics/geometrics/organics) are extracted from
the symbol inner content and placed in the sprite's outer <defs>; the same
IDs are also added to shared_defs_svg() so cross-document <use> instances
can resolve the filters against the host document.

SVGO multipass is run on the final sprite.svg to compress path data while
preserving all IDs (symbol ids, shimmer gradient ids, filter ids).
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import (
    LABEL_SHIMMER,
    get_viewbox,
    norm_asset_id,
    org_shimmer_id,
    rewire_strokes,
    strip_gradient_defs,
    strip_editor_junk,
    shared_defs_inner,
    GLOW_FILTER_DEFS,
    GLOW_RADIAL_DEFS,
)

CRITTERS   = ['jl-site-critter1', 'jl-site-critter2', 'jl-site-critter3']
SEPARATORS = [f'jl-site-separator{i}' for i in range(1, 9)]
LOGOS      = ['jl-site-logo-main', 'jl-site-logo-homepage']

SPRITE_ASSETS = CRITTERS + SEPARATORS + LOGOS


def _extract_inner(text):
    m = re.search(r'<svg\b[^>]*>(.*)</svg>', text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _strip_filter_defs(inner):
    """Remove <filter> elements from <defs> in inner SVG content.

    Filters are moved to the sprite's outer <defs> to avoid ID collisions
    across symbols and to support cross-document <use> resolution.
    """
    def clean_defs(m):
        defs_inner = m.group(1)
        defs_inner = re.sub(r'<filter\b[^>]*>.*?</filter>', '', defs_inner, flags=re.DOTALL)
        defs_inner = defs_inner.strip()
        if not defs_inner:
            return ''
        return f'<defs>{defs_inner}</defs>'
    return re.sub(r'<defs\b[^>]*>(.*?)</defs>', clean_defs, inner, flags=re.DOTALL)


def _run_svgo(svg_path):
    """Run SVGO multipass on svg_path in-place, preserving all IDs.

    Uses a .mjs config (required by SVGO v4's ES module loading).
    """
    # Sprite-safe config: only compresses path data and numbers.
    # Disables passes that strip defs/symbols not referenced within the same
    # document (removeUselessDefs, removeHiddenElems) and passes that would
    # collapse the hidden-container SVG root.
    config_mjs = """\
export default {
  multipass: true,
  plugins: [{
    name: 'preset-default',
    params: {
      overrides: {
        cleanupIds: { remove: false, minify: false },
        removeUselessDefs: false,
        removeHiddenElems: false,
        removeUnknownsAndDefaults: false,
        removeEmptyContainers: false,
      }
    }
  }]
}
"""
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.mjs', delete=False, encoding='utf-8'
        ) as f:
            f.write(config_mjs)
            config_path = f.name
        r = subprocess.run(
            ['npx', '--yes', 'svgo', '--multipass',
             '--config', config_path,
             '--input', str(svg_path),
             '--output', str(svg_path)],
            capture_output=True, text=True, timeout=120,
        )
        Path(config_path).unlink(missing_ok=True)
        if r.returncode != 0:
            print(f'  SVGO warning (exit {r.returncode}): {r.stderr[:200]}')
        else:
            print(f'  SVGO: {svg_path.name} OK')
    except FileNotFoundError:
        print('  SVGO: npx not found — skipping optimization')
    except subprocess.TimeoutExpired:
        print('  SVGO: timeout — skipping optimization')


def _load_vine_decor(svg_dir):
    """Extract raw vine symbols and micro-groups from vine-decor.svg.

    The file holds hand-authored <symbol> and <g> elements that are inserted
    directly into the sprite body (not re-wrapped as symbols).  These include
    the shared micro-groups (vine-leaf, vine-bud-*) and all per-piece symbols
    (vine-bl-*, vine-tr-*).  Internal href="#vine-leaf" references within the
    symbols resolve against the sprite document at runtime.
    """
    path = svg_dir / 'vine-decor.svg'
    if not path.exists():
        print(f'  SKIP vine-decor.svg (not found)')
        return ''
    raw = path.read_text(encoding='utf-8')
    # Strip XML declaration and xmlns attributes; keep only inner body content.
    inner = _extract_inner(raw)
    inner = re.sub(r'<\?xml[^?]*\?>\s*', '', inner)
    inner = re.sub(r'\s+xmlns(?::[a-z]+)?="[^"]*"', '', inner)
    # Strip HTML-style comments (kept in source for readability; not needed in sprite).
    inner = re.sub(r'<!--.*?-->', '', inner, flags=re.DOTALL)
    inner = re.sub(r'\n{3,}', '\n\n', inner).strip()
    print(f'  vine-decor.svg: loaded {len(inner):,} chars of vine geometry')
    return inner


def build(unit, root):
    svg_dir = root / 'Media' / 'SVG-Assets'
    symbols = []

    for name in SPRITE_ASSETS:
        svg_path = svg_dir / f'{name}.svg'
        if not svg_path.exists():
            print(f'  SKIP {svg_path} (not found)')
            continue

        raw = svg_path.read_text(encoding='utf-8')
        vb  = get_viewbox(raw)

        shimmer_map = dict(LABEL_SHIMMER)
        shimmer_map['organics'] = org_shimmer_id(vb)

        processed = rewire_strokes(raw, shimmer_map)
        processed = strip_gradient_defs(processed)
        processed = strip_editor_junk(processed)
        # Defensive: strip any remaining editor-namespace elements/declarations
        processed = re.sub(r'<(?:inkscape|sodipodi|dc|cc|rdf):[^>]*/>', '', processed, flags=re.DOTALL)
        processed = re.sub(r'<(?:inkscape|sodipodi|dc|cc|rdf):[^>]*>.*?</(?:inkscape|sodipodi|dc|cc|rdf):[^>]*>', '', processed, flags=re.DOTALL)
        processed = re.sub(r'<\?xml[^?]*\?>\s*', '', processed)
        processed = re.sub(r'\s+xmlns:(?:inkscape|sodipodi|dc|cc|rdf)="[^"]*"', '', processed)

        inner = _extract_inner(processed)
        inner = _strip_filter_defs(inner)   # filters move to outer <defs>

        sym_id = norm_asset_id(name)
        symbols.append((sym_id, vb, inner))
        print(f'  {name}: viewBox={vb!r}')

    vine_defs = _load_vine_decor(svg_dir)

    # Build sprite document: outer <defs> = shimmer gradients + glow filters + radial primitives
    shimmer_defs = shared_defs_inner()
    symbol_blocks = '\n'.join(
        f'<symbol id="{sid}" viewBox="{vb}">\n{inner}\n</symbol>'
        for sid, vb, inner in symbols
    )
    sprite_svg = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        ' width="0" height="0" aria-hidden="true"'
        ' style="position:absolute;overflow:hidden">\n'
        '<defs>\n'
        f'{shimmer_defs}\n'
        f'{GLOW_FILTER_DEFS}\n'
        f'{GLOW_RADIAL_DEFS}\n'
        '</defs>\n'
        f'{symbol_blocks}\n'
        f'{vine_defs}\n'
        '</svg>'
    )

    out = unit.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sprite_svg, encoding='utf-8')
    raw_size = out.stat().st_size
    print(f'Wrote {out}  ({raw_size:,} bytes, pre-SVGO)')

    _run_svgo(out)
    final_size = out.stat().st_size
    print(f'  post-SVGO: {final_size:,} bytes  '
          f'(saved {raw_size - final_size:,} bytes, '
          f'{100 * (raw_size - final_size) // raw_size}%)')
