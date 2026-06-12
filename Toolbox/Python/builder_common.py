#!/usr/bin/env python3
"""builder_common.py — shared utilities for all JL Kruger site builders."""

import re
import hashlib
import html as _html
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# Relative-path prefix
#
# Every linked URL (css/js/media/inter-page) is emitted *relative to the page's
# own location*, never root-absolute ("/css/..."). Root-absolute paths break the
# moment the site is served from anywhere but a domain root — e.g. a GitHub Pages
# project site at https://user.github.io/<repo>/, or a local file:// open. With
# relative paths the same build works from any sub-path.
#
# `_PREFIX` is the hop from the current page back up to the site root: '' for a
# root page (index.html), '../../' for Content/Business/*.html, etc. Builders set
# it via set_rel_prefix() before emitting any path for that page.
# ─────────────────────────────────────────────────────────────────────────────

_PREFIX = ''


def set_rel_prefix(out_path, root=None):
    """Set the module-level page→root prefix from an output file path.

    depth = number of directories the output file sits below the site root;
    prefix = that many '../' segments. Returns the prefix.
    """
    global _PREFIX
    base = (Path(root) if root else _ROOT).resolve()
    try:
        rel = Path(out_path).resolve().relative_to(base)
        _PREFIX = '../' * (len(rel.parts) - 1)
    except ValueError:
        # Output outside the root: fall back to root-relative-from-here.
        _PREFIX = ''
    return _PREFIX


def asset_url(p):
    """Turn a root-relative site path ('/css/x.css') into one relative to the
    current page ('../../css/x.css'), honouring the active _PREFIX. External
    URLs and fragments are returned untouched."""
    s = str(p)
    if re.match(r'^https?://', s) or s.startswith('mailto:') or s.startswith('#'):
        return s
    return _PREFIX + s.lstrip('/')


def asset_version(root=None):
    """Site-wide cache-busting token = short content hash of js/*.js, css/*.css,
    Media/sprite.svg, and css/fonts/*.woff2.  Changes whenever any asset changes
    so a normal reload picks up the new content.  Append as `?v=<token>` to every
    linked asset URL.
    """
    base = Path(root) if root else _ROOT
    h = hashlib.sha1()
    for d, ext in (('js', '*.js'), ('css', '*.css')):
        for p in sorted((base / d).glob(ext)):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    sprite = base / 'Media' / 'sprite.svg'
    if sprite.exists():
        h.update(b'sprite.svg')
        h.update(sprite.read_bytes())
    fonts_dir = base / 'css' / 'fonts'
    if fonts_dir.is_dir():
        for p in sorted(fonts_dir.glob('*.woff2')):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:8]

# variables.yaml lives next to this module and is the design-system source of
# truth. Loaded once, lazily, and resolved relative to __file__ so it is found
# regardless of the active project root.
_VARS = None


def load_variables():
    """Return the parsed variables.yaml (cached)."""
    global _VARS
    if _VARS is None:
        with open(Path(__file__).resolve().parent / 'variables.yaml',
                  encoding='utf-8') as f:
            _VARS = yaml.safe_load(f)
    return _VARS


# ─────────────────────────────────────────────────────────────────────────────
# SVG helpers — lifted verbatim from svg-assets-builder.py
# ─────────────────────────────────────────────────────────────────────────────

def get_viewbox(text):
    m = re.search(r'viewBox=["\']([^"\']+)["\']', text)
    return m.group(1) if m else '0 0 0 0'


def org_shimmer_id(viewbox):
    parts = list(map(float, viewbox.split()))
    if len(parts) == 4:
        w = parts[2] - parts[0]
        h = parts[3] - parts[1]
        return 'shimmer-org-v' if h > w else 'shimmer-org-h'
    return 'shimmer-org-h'


LABEL_SHIMMER = {
    'statics':    'shimmer-sta',
    'geometrics': 'shimmer-geo',
}


def rewire_strokes(text, shimmer_map):
    """Re-point labelled gradient strokes at the shared shimmer ids.

    Emits stroke:var(--<sid>, url(#<sid>)) rather than a bare url so that
    host documents can re-target the stroke via a CSS custom property.
    Custom properties inherit into external-<use> shadow trees, and a url()
    declared in the host resolves against the host's rotating gradient
    copies (shared_defs_svg) — a bare url(#...) inside sprite.svg resolves
    against the sprite's own static defs, freezing the shimmer (Phase 2.5.2,
    gate G2). The var fallback keeps the static look in no-CSS contexts.
    """
    shape_tags = r'path|circle|rect|ellipse|line|polyline|polygon'

    def replace_elem(m):
        elem = m.group(0)
        lm = re.search(r'inkscape:label=["\']([^"\']+)["\']', elem)
        if not lm:
            return elem
        label = lm.group(1)
        if label not in shimmer_map:
            return elem
        sid = shimmer_map[label]
        sval = f'var(--{sid}, url(#{sid}))'
        elem = re.sub(r'stroke:url\(#[^)]+\)', f'stroke:{sval}', elem)
        # Attribute-form strokes can't carry var(); fold them into style
        # (inline style wins over the presentation attribute).
        if re.search(r'stroke="url\(#[^)]+\)"', elem):
            elem = re.sub(r'\s*stroke="url\(#[^)]+\)"', '', elem)
            if 'style="' in elem:
                elem = elem.replace('style="', f'style="stroke:{sval};', 1)
            else:
                elem = elem.replace('/>', f' style="stroke:{sval}"/>', 1)
        return elem

    return re.sub(
        rf'<(?:{shape_tags})\b[^>]*/>', replace_elem, text, flags=re.DOTALL
    )


def strip_gradient_defs(text):
    def clean_defs(m):
        defs_inner = m.group(1)
        defs_inner = re.sub(
            r'<linearGradient\b[^>]*(?:/>|>.*?</linearGradient>)',
            '', defs_inner, flags=re.DOTALL
        )
        defs_inner = re.sub(
            r'<radialGradient\b[^>]*(?:/>|>.*?</radialGradient>)',
            '', defs_inner, flags=re.DOTALL
        )
        defs_inner = defs_inner.strip()
        if not defs_inner:
            return ''
        return f'<defs>{defs_inner}</defs>'

    return re.sub(r'<defs\b[^>]*>(.*?)</defs>', clean_defs, text, flags=re.DOTALL)


def strip_editor_junk(text):
    # Self-closing form: <sodipodi:namedview ... />
    text = re.sub(r'<sodipodi:namedview\b[^>]*/>', '', text, flags=re.DOTALL)
    # Element form: <sodipodi:namedview ...>...</sodipodi:namedview>
    text = re.sub(
        r'<sodipodi:namedview\b[^>]*>.*?</sodipodi:namedview>',
        '', text, flags=re.DOTALL
    )
    text = re.sub(r'\s*inkscape:label=["\'][^"\']*["\']', '', text)
    text = re.sub(r'\s*inkscape:[a-z\-]+=(?:"[^"]*"|\'[^\']*\')', '', text)
    text = re.sub(r'\s*sodipodi:[a-z\-]+=(?:"[^"]*"|\'[^\']*\')', '', text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Core utilities
# ─────────────────────────────────────────────────────────────────────────────

def project_root(argv_root=None):
    global _ROOT
    if argv_root:
        _ROOT = Path(argv_root).resolve()
    else:
        _ROOT = Path(__file__).resolve().parent.parent.parent
    return _ROOT


def load_yaml(path):
    p = Path(path)
    if not p.is_absolute():
        p = _ROOT / p
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f)


def slugify(text):
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def norm_path(p):
    if not p:
        return ''
    s = str(p)
    if re.match(r'^https?://', s) or s.startswith('mailto:') or s.startswith('#'):
        return s
    if s.startswith('./'):
        s = s[2:]
    # Emit relative to the current page (see _PREFIX), not root-absolute, so the
    # link survives being served from a sub-path (GitHub Pages, file://, …).
    return _PREFIX + s.lstrip('/')


def fallback_href(p):
    n = norm_path(p) if p else ''
    return n if n else asset_url('/404.html')


def norm_asset_id(s):
    if not s:
        return s
    s = str(s)
    if s.endswith('.svg'):
        s = s[:-4]
    return s.replace('_', '-')


def esc(s):
    return _html.escape(str(s), quote=True)


_ASSET_IDS = None


def asset_id_pool():
    """Return the set of SVG asset ids from Media/sprite.svg (cached).

    Returns an empty set if sprite.svg is absent so validation degrades
    to a no-op rather than crashing (e.g. during --check before first build).
    """
    global _ASSET_IDS
    if _ASSET_IDS is None:
        path = _ROOT / 'Media' / 'sprite.svg'
        if path.exists():
            text = path.read_text(encoding='utf-8')
            _ASSET_IDS = set(re.findall(r'<symbol\s+id="([^"]+)"', text))
        else:
            _ASSET_IDS = set()
    return _ASSET_IDS


def sprite_use(asset_id, ver=None, **svg_attrs):
    """Emit <svg ...><use href="Media/sprite.svg[?v=...]#asset_id"/></svg>.

    svg_attrs are added as attributes on the outer <svg> element.
    Always sets aria-hidden="true" unless overridden.
    """
    v = f'?v={ver}' if ver else ''
    href = f'{asset_url("/Media/sprite.svg")}{v}#{asset_id}'
    attrs = {'aria-hidden': 'true', **svg_attrs}
    attrs_str = ' '.join(f'{k}="{val}"' for k, val in attrs.items())
    return f'<svg {attrs_str}><use href="{href}"/></svg>'


# ─────────────────────────────────────────────────────────────────────────────
# Gradient defs — generated from variables.yaml (gradients.stop_sets + .defs).
# Output is byte-identical to the original proto8 <defs> block; offset fields
# are space-aligned per gradient to the widest offset token, as in the source.
# ─────────────────────────────────────────────────────────────────────────────

_GRAD_AXIS = {
    'h': 'x1="0" y1=".5" x2="1" y2=".5"',
    'v': 'x1=".5" y1="0" x2=".5" y2="1"',
}

# Glow filters used by critters and separators — defined once here so they
# are available both in the sprite's <defs> and in every page's shared_defs
# block, ensuring cross-document <use> instances resolve url(#glow-filter-*)
# against the host document.
GLOW_FILTER_DEFS = (
    '<filter id="glow-filter-statics"    x="-0.1" y="-0.1" width="1.2" height="1.2">'
    '<feGaussianBlur stdDeviation="3"/></filter>\n'
    '<filter id="glow-filter-geometrics" x="-0.1" y="-0.1" width="1.2" height="1.2">'
    '<feGaussianBlur stdDeviation="3"/></filter>\n'
    '<filter id="glow-filter-organics"   x="-0.1" y="-0.1" width="1.2" height="1.2">'
    '<feGaussianBlur stdDeviation="3"/></filter>'
)

# Glow primitives — the ember/spectral language for decor, vines, and buttons.
# No feGaussianBlur; zero per-frame blur cost.
# Palette rgba values from variables.yaml (locked):
#   ember:    sun #f2c62a → fire #eb7513 → rust #a52c16 → transparent
#   spectral: light #e8e2da → meadow #5e9a0e → forest #0e4d0e → transparent
# CSS equivalent lives in css/glow.css; canvas pattern in js/starfield.js glow().
# glow-ember-rg is a vertical linearGradient (top=bright, bottom=fade) for a
# fire-rising directional quality; glow-spectral-rg stays radial (diffuse moonlit).
GLOW_RADIAL_DEFS = (
    '<linearGradient id="glow-ember-rg" x1="50%" y1="0%" x2="50%" y2="100%"'
    ' gradientUnits="objectBoundingBox">'
    '<stop offset="0%"   stop-color="#f2c62a" stop-opacity=".65"/>'
    '<stop offset="35%"  stop-color="#eb7513" stop-opacity=".40"/>'
    '<stop offset="65%"  stop-color="#a52c16" stop-opacity=".18"/>'
    '<stop offset="100%" stop-color="#442204" stop-opacity="0"/>'
    '</linearGradient>\n'
    '<radialGradient id="glow-spectral-rg" cx="50%" cy="50%" r="50%">'
    '<stop offset="0%"   stop-color="#e8e2da" stop-opacity=".45"/>'
    '<stop offset="30%"  stop-color="#5e9a0e" stop-opacity=".28"/>'
    '<stop offset="60%"  stop-color="#0e4d0e" stop-opacity=".12"/>'
    '<stop offset="100%" stop-color="#073720" stop-opacity="0"/>'
    '</radialGradient>'
)


def shared_defs_inner():
    """Return the shimmer gradient definitions as a bare string (no wrapper SVG)."""
    grads = load_variables()['gradients']
    stop_sets = grads['stop_sets']
    lines = []
    for d in grads['defs']:
        stops = stop_sets[d['stops']]
        pad = max(len(f'offset="{s["offset"]}"') for s in stops)
        lines.append(
            f'<linearGradient id="{d["id"]}" gradientUnits="objectBoundingBox"'
            f' {_GRAD_AXIS[d["axis"]]}>'
        )
        for s in stops:
            field = f'offset="{s["offset"]}"'.ljust(pad)
            lines.append(
                f'  <stop {field} stop-color="{s["color"]}"'
                f' stop-opacity="{s["opacity"]}"/>'
            )
        lines.append('</linearGradient>')
    return '\n'.join(lines)


def shared_defs_svg():
    """Inline shared gradient + filter defs block for each page."""
    return (
        '<svg id="shared-defs" width="0" height="0" aria-hidden="true"'
        ' style="position:absolute;overflow:hidden">\n'
        '<defs>\n'
        + shared_defs_inner() + '\n'
        + GLOW_FILTER_DEFS + '\n'
        + GLOW_RADIAL_DEFS + '\n'
        '</defs></svg>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# SVG inlining
# ─────────────────────────────────────────────────────────────────────────────

def inline_svg(path, rewire=True):
    p = Path(path)
    if not p.is_absolute():
        p = _ROOT / p
    with open(p, encoding='utf-8') as f:
        raw = f.read()
    vb = get_viewbox(raw)
    if rewire:
        shimmer_map = dict(LABEL_SHIMMER)
        shimmer_map['organics'] = org_shimmer_id(vb)
        processed = rewire_strokes(raw, shimmer_map)
    else:
        processed = raw
    processed = strip_gradient_defs(processed)
    processed = strip_editor_junk(processed)
    # Strip XML declaration and Inkscape/Sodipodi namespace declarations
    processed = re.sub(r'<\?xml[^?]*\?>\s*', '', processed)
    processed = re.sub(r'\s+xmlns:(?:inkscape|sodipodi|dc|cc|rdf)="[^"]*"', '', processed)
    return processed.strip()


def _svg_add_attrs(svg_text, attrs):
    """Insert attrs dict onto the root <svg> opening tag."""
    def replacer(m):
        tag = m.group(0)
        for k, v in attrs.items():
            pat = re.compile(r'\s+' + re.escape(k) + r'=["\'][^"\']*["\']')
            if pat.search(tag):
                tag = pat.sub(f' {k}="{v}"', tag)
            else:
                # Insert before closing >
                if tag.rstrip().endswith('>'):
                    tag = tag.rstrip()[:-1].rstrip() + f' {k}="{v}">'
        return tag
    return re.sub(r'<svg\b[^>]*>', replacer, svg_text, count=1)


def _svg_path(filename):
    """Resolve an SVG-Assets filename to its actual repo path."""
    # Actual files live at Media/SVG-Assets/ (plan says SVG-Assets/ — §8 discrepancy)
    candidate = _ROOT / 'Media' / 'SVG-Assets' / filename
    if candidate.exists():
        return candidate
    # Fallback: try plan-specified path
    return _ROOT / 'SVG-Assets' / filename


def vine_decor(page_type='homepage'):
    """Emit the .vine-decor fixed overlay: two planter pieces (BL / BR).

    Styling pattern shared with the critters/separators: white line skeleton
    (#e8e2da, the locked light value) on top, with a duplicate shimmer copy
    behind, offset like a thin drop shadow (the planter sources' Glow layer,
    minus the feGaussianBlur, which is forbidden on animated decor).
    Shimmer strokes are presentation attributes on the host <use> elements —
    they inherit into the external-<use> shadow tree and resolve against the
    host document's rotating gradient defs, so the shimmer rAF reaches them.

    Geometry: Media/SVG-Assets/vine-decor.svg, generated from the planter
    Shape layers by Toolbox/Python/planter-extract.py (BL=planter3,
    BR=planter1). Requires css/vines.css linked after layers.css.
    """
    sprite = asset_url('/Media/sprite.svg')

    # label-group symbol suffix → shimmer gradient (site label mapping;
    # org uses the -v variant: both planter viewBoxes are taller than wide)
    layers = [('sta', 'url(#shimmer-sta)',   'v-struct'),
              ('geo', 'url(#shimmer-geo)',   'v-struct'),
              ('org', 'url(#shimmer-org-v)', 'v-vine')]

    def _piece(cls, corner, vb, par):
        shimmer = '\n  '.join(
            f'<use class="v-shimmer {beat}" href="{sprite}#vine-{corner}-{s}" '
            f'stroke="{grad}"/>'
            for s, grad, beat in layers)
        line = '\n  '.join(
            f'<use class="v-line {beat}" href="{sprite}#vine-{corner}-{s}" '
            f'stroke="#e8e2da"/>'
            for s, _, beat in layers)
        return (f'<svg class="vine-piece {cls}" viewBox="{vb}" '
                f'preserveAspectRatio="{par}" aria-hidden="true">\n'
                f'  {shimmer}\n  {line}\n'
                f'</svg>')

    bl = _piece('vine--bl', 'bl', '0 0 263.25312 752.48425', 'xMinYMax meet')
    br = _piece('vine--br', 'br', '0 0 81.531886 584.09772', 'xMaxYMax meet')

    return ('<div class="vine-decor" aria-hidden="true">\n'
            f'{bl}\n{br}\n'
            '</div>')


def frame_overlays(page_type):
    """Bridge: was the old frames emitter; now delegates to vine_decor()."""
    return vine_decor(page_type)


def sidebar_logo():
    svg = sprite_use('jl-site-logo-main',
                     id='sidebar-logo-svg', width='100%', height='100%')
    # Logo links home; data-shimmer-nav flashes the shimmer before navigating.
    return (f'<div id="sidebar-logo">'
            f'<a href="{asset_url("/index.html")}" data-shimmer-nav class="logo-link" '
            f'aria-label="JL Kruger — home">{svg}</a></div>')


# ─────────────────────────────────────────────────────────────────────────────
# Navbar
# ─────────────────────────────────────────────────────────────────────────────

# NOTE: `doc` is the *whole* site.yaml document, not its `site:` sub-mapping —
# navbar/homepage are top-level keys. Passing data['site'] here breaks nav.
def render_navbar(doc, mode, page_title=''):
    if mode == 'standard':
        links = doc.get('navbar', [])
        desktop = '\n    '.join(
            f'<a href="{fallback_href(lnk["href"])}">{esc(lnk["label"])}</a>'
            for lnk in links
        )
        dropdown = '\n    '.join(
            f'<a href="{fallback_href(lnk["href"])}">{esc(lnk["label"])}</a>'
            for lnk in links
        )
        return (
            f'<nav class="sticky-nav" aria-label="Site navigation">\n'
            f'  <div class="link-row nav-links">\n'
            f'    {desktop}\n'
            f'  </div>\n'
            f'  <div class="mobile-nav-bar">\n'
            f'    <span class="mobile-page-title">{esc(page_title)}</span>\n'
            f'    <button class="mobile-hamburger" id="mobile-hamburger"'
            f' aria-label="Open navigation menu" aria-expanded="false">☰</button>\n'
            f'  </div>\n'
            f'  <div class="mobile-nav-dropdown" id="mobile-nav-dropdown">\n'
            f'    {dropdown}\n'
            f'  </div>\n'
            f'</nav>'
        )
    if mode == 'home':
        links = (doc.get('homepage', {})
                    .get('layout', {})
                    .get('navbar_home', []))
        link_html = '\n    '.join(
            f'<a href="{fallback_href(lnk["href"])}">{esc(lnk["label"])}</a>'
            for lnk in links
        )
        return (
            f'<nav class="navbar-home sticky-nav" aria-label="Site navigation">\n'
            f'  <div class="link-row nav-links">\n'
            f'    {link_html}\n'
            f'  </div>\n'
            f'</nav>'
        )
    raise ValueError(f'Unknown navbar mode: {mode!r}')


# ─────────────────────────────────────────────────────────────────────────────
# <head> block
# ─────────────────────────────────────────────────────────────────────────────

def google_fonts_url():
    """RETIRED — fonts are now self-hosted (css/fonts/*.woff2 + css/fonts.css).
    Kept until variables.yaml google_fonts section is cleaned up. Not called."""
    gf = load_variables()['typography']['google_fonts']
    families = '&family='.join([gf['base']] + gf['families'])
    return f'https://fonts.googleapis.com/css2?family={families}&display={gf["display"]}'


def head_block(title, description, *css_hrefs):
    ver = asset_version()
    css_links = '\n'.join(
        f'<link rel="stylesheet" href="{href}">'
        for href in css_hrefs
    )
    return (
        f'<head>\n'
        f'<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<meta name="description" content="{esc(description)}">\n'
        f'<title>{esc(title)}</title>\n'
        f'<link rel="icon" type="image/svg+xml" href="{asset_url("/Media/SVG-Assets/jl-site-logo-favicon.svg")}">\n'
        f'<link rel="preload" as="font" type="font/woff2" crossorigin href="{asset_url("/css/fonts/tagesschrift-regular.woff2")}">\n'
        f'<link rel="preload" as="font" type="font/woff2" crossorigin href="{asset_url("/css/fonts/overlock-regular.woff2")}">\n'
        f'<link rel="stylesheet" href="{asset_url("/css/fonts.css")}?v={ver}">\n'
        f'{css_links}\n'
        f'</head>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Design-token CSS — generated :root{} from variables.yaml (palette + layout).
# Emitted to /css/tokens.css and linked by every page, replacing the per-file
# :root blocks that previously duplicated these values.
# ─────────────────────────────────────────────────────────────────────────────

def _num(x):
    """Trim a float to ≤4 decimals, drop trailing zeros (e.g. 1.5000 → 1.5)."""
    s = f'{x:.4f}'.rstrip('0').rstrip('.')
    return s if s else '0'


def _fluid_clamp(min_px, max_px, vmin_px, vmax_px, rem_ref=16):
    """One CSS clamp() that grows linearly from min_px (at vmin) to max_px (at
    vmax). Returns clamp(<min>rem, <intercept>rem + <coeff>vw, <max>rem) with
    the rem reference fixed to the browser root (rem_ref) so user font-size
    prefs are preserved. (Utopia-style fluid step.)"""
    slope = (max_px - min_px) / (vmax_px - vmin_px)        # px per px of viewport
    intercept_rem = (min_px - slope * vmin_px) / rem_ref   # y-axis crossing, in rem
    coeff_vw = slope * 100                                  # vw coefficient
    lo, hi = min_px / rem_ref, max_px / rem_ref
    return (f'clamp({_num(lo)}rem, {_num(intercept_rem)}rem + '
            f'{_num(coeff_vw)}vw, {_num(hi)}rem)')


def tokens_css():
    v = load_variables()
    pal = v['colors']['palette']
    lay = v['layout']
    sc = v['scale']
    width = max(len(k) for k in pal)
    lines = [
        '/* AUTO-GENERATED from variables.yaml by builder_common — do not edit. */',
        ':root {',
    ]
    for name, hexval in pal.items():
        lines.append(f'  --{name}:{" " * (width - len(name))} {hexval};')
    lines.append(f'  --sidebar-w:      {lay["sidebar_w"]};')
    lines.append(f'  --logo-h:         {lay["logo_h"]};')
    lines.append(f'  --content-max-w:  {lay["content_max_w"]};')
    lines.append(f'  --content-pad-v:  {lay["content_pad_v"]};')
    lines.append(f'  --lh:             {lay["lh"]};')

    # ── Fluid type ramp ── (--step--1 … --step-6; --step-0 = body base)
    t = sc['type']
    vmin, vmax = t['viewport_min_px'], t['viewport_max_px']
    lines.append('')
    lines.append('  /* Fluid type — clamp() steps, see LAYOUT-SPEC.md §3 */')
    for n in t['steps']:
        min_px = t['base_min_px'] * (t['ratio_min'] ** n)
        max_px = t['base_max_px'] * (t['ratio_max'] ** n)
        lines.append(f'  --step-{n}: {_fluid_clamp(min_px, max_px, vmin, vmax)};')

    # ── Rhythm + spacing ── (baseline = one body line; --space-* are multiples)
    lines.append('')
    lines.append('  /* Vertical rhythm + spacing scale, see LAYOUT-SPEC.md §2 */')
    lines.append('  --rhythm: calc(var(--step-0) * var(--lh));')
    for key, mult in sc['spacing'].items():
        lines.append(f'  --space-{key}: calc(var(--rhythm) * {_num(float(mult))});')

    # ── Content measure ──
    lines.append('')
    lines.append(f'  --measure: {sc["measure"]};   /* ideal prose line length */')

    lines.append('}')
    return '\n'.join(lines) + '\n'


def write_tokens_css(root=None):
    base = Path(root) if root else _ROOT
    path = base / 'css' / 'tokens.css'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tokens_css(), encoding='utf-8')
    print(f'Wrote {path}  ({path.stat().st_size:,} bytes)')


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

def write_output(path, html):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding='utf-8')
    print(f'Wrote {p}  ({len(html):,} chars)')
