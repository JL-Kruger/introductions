"""contenthub.py — render /content.html (and, via placeholder.py, /404.html).

Body migrated verbatim from contenthub-builder.py. The internal render()
function is also used by placeholder.py (BUILD-ARCH §2 — "reuses contenthub
render").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import (
    load_yaml, esc, norm_path, fallback_href, norm_asset_id,
    frame_overlays, render_navbar, head_block, shared_defs_svg,
    write_output, get_viewbox, _svg_path, sprite_use, asset_version,
    set_rel_prefix, asset_url,
)

# § 3.4  style → CSS variant mapping
_STYLE = {
    'static':   ('card-static',  'card-desc',    'card-link'),
    'standard': ('card-static',  'card-desc',    'card-link'),
    'featured': ('card-special', 'card-desc-sp', 'card-link-sp'),
    'special':  ('card-special', 'card-desc-sp', 'card-link-sp'),
}


def _card(card):
    wrap_cls, desc_cls, link_cls = _STYLE.get(
        card.get('style', 'static'), _STYLE['static']
    )
    label = esc(card.get('label', ''))
    desc  = esc(card.get('description', ''))
    href  = fallback_href(card.get('href'))
    thumb = norm_path(card.get('thumbnail', '')) or asset_url('/404.html')
    return (
        f'<div class="card-wrap {wrap_cls}">\n'
        f'  <svg class="card-border" aria-hidden="true">'
        f'<rect class="card-border-rect" x="0.75" y="0.75" '
        f'width="calc(100% - 1.5px)" height="calc(100% - 1.5px)" rx="4"/>'
        f'</svg>\n'
        f'  <div class="card-body">'
        f'<div class="card-thumb-wrap">'
        f'<svg aria-hidden="true" class="card-thumb-circle">'
        f'<circle cx="50%" cy="50%" r="calc(50% - 1px)" fill="none" '
        f'stroke="url(#shine-org-h)" stroke-width="2"/>'
        f'</svg>'
        f'<img class="card-thumb" src="{thumb}" alt="" loading="lazy">'
        f'</div>\n'
        f'    <h4 class="card-title">{label}</h4>\n'
        f'    <p class="{desc_cls}">{desc}</p>\n'
        f'    <a class="{link_cls}" href="{href}">Visit &rarr;</a>\n'
        f'  </div>\n'
        f'</div>'
    )


def _critter(asset_id, ver=None):
    filename = asset_id if asset_id.endswith('.svg') else asset_id + '.svg'
    raw = open(_svg_path(filename)).read()
    vb = get_viewbox(raw)
    parts = list(map(float, vb.split()))
    is_wide = len(parts) == 4 and (parts[2] - parts[0]) > (parts[3] - parts[1])
    cls = 'decor-critter critter-wide' if is_wide else 'decor-critter'
    svg = sprite_use(asset_id, ver=ver, width='100%', height='100%')
    return f'<div class="{cls}">\n  {svg}\n</div>'


def _logo(asset_id, ver=None):
    svg = sprite_use(asset_id, ver=ver, width='100%', height='100%')
    return (f'<div class="logo-wrap" id="logo-svg">\n'
            f'  <a href="{asset_url("/index.html")}" data-shimmer-nav class="logo-link" '
            f'aria-label="JL Kruger — home">{svg}</a>\n</div>')


def _render_item(item, ver=None):
    kind, value = next(iter(item.items()))
    if kind == 'text':
        return f'<p>{esc(value)}</p>'
    if kind in ('h1', 'h2', 'h3'):
        return f'<{kind}>{esc(value)}</{kind}>'
    if kind == 'special':
        return f'<span class="special">{esc(value)}</span>'
    if kind == 'critter':
        return _critter(norm_asset_id(value), ver=ver)
    if kind == 'logo':
        return _logo(norm_asset_id(Path(value).stem), ver=ver)
    if kind == 'card':
        return _card(value)
    return ''


def _render_col(items, ver=None):
    return '\n'.join(_render_item(i, ver=ver) for i in (items or []))


# § 3.5 — verbatim from content.html lines 854–864
_SCRIPT_TAIL = """\
<script src="/js/shimmer.js"></script>
<script>
    // Register shimmer interactions on logo and shimmer-bordered cards
    const logo = document.getElementById('logo-svg');
    if (logo && window.registerGradientInteraction) window.registerGradientInteraction(logo);

    document.querySelectorAll('.card-wrap.card-special, .decor-critter').forEach(el => {
        if (window.registerGradientInteraction) window.registerGradientInteraction(el);
    });

    // Mobile hamburger → toggle the dropdown nav
    const _ham = document.getElementById('mobile-hamburger');
    const _stickyNav = document.querySelector('.sticky-nav');
    if (_ham && _stickyNav) {
        _ham.addEventListener('click', () => {
            const open = _stickyNav.classList.toggle('nav-open');
            _ham.setAttribute('aria-expanded', open);
        });
        if (window.registerGradientInteraction) window.registerGradientInteraction(_ham);
    }

</script>"""


def render(data, section_key, title, out_path, root):
    """Render a bento-grid hub page. Used by both build() and placeholder.build()."""
    hub    = data[section_key]
    layout = hub['layout']
    site   = data['site']

    ver         = asset_version(root)
    description = site.get('description', '')
    head        = head_block(title, description,
                             f'{asset_url("/css/tokens.css")}?v={ver}',
                             f'{asset_url("/css/layers.css")}?v={ver}',
                             f'{asset_url("/css/sky.css")}?v={ver}',
                             f'{asset_url("/css/glow.css")}?v={ver}',
                             f'{asset_url("/css/vines.css")}?v={ver}',
                             f'{asset_url("/css/content.css")}?v={ver}')
    navbar = render_navbar(data, 'standard')
    left   = _render_col(layout.get('bento_left',   []), ver=ver)
    center = _render_col(layout.get('bento_center', []), ver=ver)
    right  = _render_col(layout.get('bento_right',  []), ver=ver)
    frames = frame_overlays('contenthub')

    html = f"""<!DOCTYPE html>
<html lang="en">
{head}
<body>

{shared_defs_svg()}

<div id="sky" aria-hidden="true"></div>
<canvas id="stars" aria-hidden="true"></canvas>
<div id="sky-glow" aria-hidden="true"></div>
<canvas id="starfield" aria-hidden="true"></canvas>

{navbar}

<div id="scroll-container">
<main class="hub-content">
<div class="bento-grid">

<!-- ── Left column ──────────────────────────────────────────────────────── -->
<div class="bento-col bento-left">

{left}

</div>

<!-- ── Centre column ─────────────────────────────────────────────────────── -->
<div class="bento-col bento-center">

{center}

</div>

<!-- ── Right column ──────────────────────────────────────────────────────── -->
<div class="bento-col bento-right">

{right}

</div>

</div><!-- /.bento-grid -->
</main>
</div><!-- /#scroll-container -->

{frames}

{_SCRIPT_TAIL.replace('/js/shimmer.js', f'{asset_url("/js/shimmer.js")}?v={ver}')}
<script src="{asset_url("/js/starfield.js")}?v={ver}" defer></script>
</body>
</html>"""

    write_output(out_path, html)


def build(unit, root):
    set_rel_prefix(unit.output, root)
    data = load_yaml('Toolbox/Python/site.yaml')
    render(data, 'contenthub', 'JL Kruger - Content Index', unit.output, root)
