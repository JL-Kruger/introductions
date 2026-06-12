"""homepage.py — render /index.html from site.yaml › homepage.

Body migrated verbatim from homepage-builder.py. project_root() and
write_tokens_css() are handled by build.py before dispatch; this module
only renders and writes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import (
    load_yaml, esc, norm_path, fallback_href, norm_asset_id,
    frame_overlays, render_navbar, head_block, shared_defs_svg,
    write_output, get_viewbox, _svg_path, sprite_use,
    asset_version, set_rel_prefix, asset_url,
)


def _thumbnail(src):
    img_src = norm_path(src) or asset_url('/404.html')
    return (
        '<div class="thumbnail-wrap" style="position:relative;width:120px;height:120px;'
        'margin:1.5rem auto 1.5rem auto;display:flex;justify-content:center;'
        'align-items:center;border-radius:50%;">\n'
        '    <svg aria-hidden="true" style="position:absolute;top:0;left:0;width:100%;'
        'height:100%;pointer-events:none;z-index:2;">\n'
        '        <circle cx="50%" cy="50%" r="calc(50% - 1px)" fill="none" '
        'stroke="url(#shimmer-org-h)" stroke-width="2"/>\n'
        '    </svg>\n'
        f'    <img src="{img_src}" alt="" style="width:100%;height:100%;'
        'object-fit:cover;border-radius:50%;" />\n'
        '</div>'
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


def _logo_center(asset_id, ver=None):
    svg = sprite_use(asset_id, ver=ver, id='logo-svg', width='100%', height='100%')
    return (f'<a href="{asset_url("/content.html")}" data-shimmer-nav class="logo-link" '
            f'aria-label="Enter — content hub">{svg}</a>')


def _render_item(item, ver=None):
    kind, value = next(iter(item.items()))
    if kind == 'text':
        return f'<p>{esc(value)}</p>'
    if kind == 'h1':
        return f'<h1>{esc(value)}</h1>'
    if kind == 'h2':
        return f'<h2>{esc(value)}</h2>'
    if kind == 'h3':
        return f'<h3>{esc(value)}</h3>'
    if kind == 'special':
        return f'<span class="special">{esc(value)}</span>'
    if kind == 'thumbnail':
        return _thumbnail(value)
    if kind == 'critter':
        return _critter(norm_asset_id(value), ver=ver)
    if kind == 'logo':
        return _logo_center(norm_asset_id(Path(value).stem), ver=ver)
    return ''


def _render_col(items, ver=None):
    return '\n'.join(_render_item(i, ver=ver) for i in (items or []))


def _hero_buttons(featured_links):
    parts = []
    for lnk in (featured_links or []):
        href  = fallback_href(lnk.get('href'))
        label = esc(lnk.get('label', ''))
        parts.append(
            '<span class="media-btn-wrap">\n'
            '    <svg class="media-btn-border" aria-hidden="true" preserveAspectRatio="none">\n'
            '      <rect class="media-btn-rect" x="0.75" y="0.75" '
            'width="calc(100% - 1.5px)" height="calc(100% - 1.5px)" rx="3"/>\n'
            '    </svg>\n'
            f'    <a href="{href}" class="media-btn">{label}</a>\n'
            '</span>'
        )
    return '\n'.join(parts)


# § 4.5 — verbatim from index.html lines 1077–1086
_SCRIPT_TAIL = """\
<script src="/js/shimmer.js"></script>
<script>
    // Register interactions on all shimmer-bordered elements
    document.querySelectorAll('.media-btn-wrap, .thumbnail-wrap, .decor-critter').forEach(el => {
        if (window.registerGradientInteraction) window.registerGradientInteraction(el);
    });
    // Logo also participates in gradient speed
    const logoSvg = document.getElementById('logo-svg');
    if (logoSvg && window.registerGradientInteraction) window.registerGradientInteraction(logoSvg);
</script>"""


def build(unit, root):
    set_rel_prefix(unit.output, root)
    data = load_yaml('Toolbox/Python/site.yaml')
    site = data['site']
    hp   = data['homepage']
    layout = hp['layout']
    featured_links = hp.get('featured_links', [])

    ver         = asset_version(root)
    description = site.get('description', '')
    head        = head_block('JL Kruger Introductions', description,
                             f'{asset_url("/css/tokens.css")}?v={ver}',
                             f'{asset_url("/css/layers.css")}?v={ver}',
                             f'{asset_url("/css/sky.css")}?v={ver}',
                             f'{asset_url("/css/glow.css")}?v={ver}',
                             f'{asset_url("/css/vines.css")}?v={ver}',
                             f'{asset_url("/css/styles.css")}?v={ver}')
    navbar  = render_navbar(data, 'home')
    left    = _render_col(layout.get('bento_left',   []), ver=ver)
    center  = _render_col(layout.get('bento_center', []), ver=ver)
    right   = _render_col(layout.get('bento_right',  []), ver=ver)
    buttons = _hero_buttons(featured_links)
    frames  = frame_overlays('homepage')

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

<div class="container flex-row" id="scroll-container">
    <main class="hero-content">
        <div class="bento-grid">
            <div class="bento-col bento-left">
{left}
            </div>

            <div class="bento-col bento-center">
{center}
            </div>

            <div class="bento-col bento-right">
{right}
            </div>
        </div>

        <div class="hero-buttons">
{buttons}
        </div>
    </main>
</div>

{frames}

{_SCRIPT_TAIL.replace('/js/shimmer.js', f'{asset_url("/js/shimmer.js")}?v={ver}')}
<script src="{asset_url("/js/starfield.js")}?v={ver}" defer></script>
</body>
</html>"""

    write_output(unit.output, html)
