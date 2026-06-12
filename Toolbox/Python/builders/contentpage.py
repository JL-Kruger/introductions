"""contentpage.py — render a content page from a *-content.yaml.

Body migrated verbatim from contentpage-builder.py. SLUG_TO_DIR now lives in
scan.py (canonical copy); the local reference here is the same dict, kept for
the error message in build().
"""

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import (
    load_yaml, slugify, norm_path, fallback_href,
    norm_asset_id, esc, shared_defs_svg, frame_overlays, sidebar_logo,
    render_navbar, head_block, write_output, asset_id_pool,
    asset_version, set_rel_prefix, asset_url,
)
from builders.scan import SLUG_TO_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Block transform (§2.3)  — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

def transform_block(b):
    t = b.get('type', '')

    if t == 'heading':
        out = {'type': 'heading', 'level': b['level'], 'text': b['text']}
        if b['level'] == 2:
            out['id'] = slugify(b['text'])
        return out

    if t == 'paragraph':
        return {'type': 'paragraph', 'text': b['text'].rstrip('\n')}

    if t == 'special':
        out = {'type': 'special', 'text': b['text']}
        if 'attribution' in b:
            out['attribution'] = b['attribution']
        return out

    if t == 'quote':
        out = {'type': 'quote', 'text': b['text']}
        if 'attribution' in b:
            out['attribution'] = b['attribution']
        return out

    if t == 'separator':
        return {'type': 'separator', 'svg': norm_asset_id(b['svg'])}

    if t == 'critter':
        return {'type': 'critter', 'svg': norm_asset_id(b['svg'])}

    if t == 'media':
        out = {
            'type': 'media',
            'src': norm_path(b['src']),
            'text': b.get('text') or b.get('title', ''),
        }
        if 'critter' in b:
            out['critter'] = norm_asset_id(b['critter'])
        if 'caption' in b:
            out['caption'] = b['caption']
        return out

    if t == 'gallery':
        out = {
            'type': 'media',
            'src': norm_path(b['src']),
            'text': b.get('text', ''),
        }
        if 'critter' in b:
            out['critter'] = norm_asset_id(b['critter'])
        return out

    if t == 'image':
        return {
            'type': 'image',
            'src': norm_path(b['src']),
            'alt': b.get('alt-text', ''),
        }

    if t == 'thumbnail':
        out = {'type': 'thumbnail', 'src': norm_path(b['src'])}
        if 'alt-text' in b:
            out['alt'] = b['alt-text']
        return out

    if t == 'button':
        return {
            'type': 'button',
            'text': b['text'],
            'href': fallback_href(b.get('href')),
        }

    if t == 'link-row':
        return {
            'type': 'link-row',
            'links': [
                {'text': lnk['text'], 'href': fallback_href(lnk.get('href'))}
                for lnk in b.get('links', [])
            ],
        }

    if t == 'table':
        return {
            'type': 'table',
            'headers': b['headers'],
            'rows': b['rows'],
        }

    if t == 'accordion':
        return {
            'type': 'accordion',
            'cards': b['cards'],
        }

    if t == 'html-asset':
        print(f'WARNING: html-asset block encountered (§8.6 key mismatch). Emitting file key.', file=sys.stderr)
        return {'type': 'html-asset', 'file': b.get('text') or b.get('href', '')}

    print(f'WARNING: unknown block type {t!r}', file=sys.stderr)
    return b


# ─────────────────────────────────────────────────────────────────────────────
# Input validation — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_KEYS = {
    'heading':    ('level', 'text'),
    'paragraph':  ('text',),
    'special':    ('text',),
    'quote':      ('text',),
    'separator':  ('svg',),
    'critter':    ('svg',),
    'media':      ('src',),
    'gallery':    ('src',),
    'image':      ('src',),
    'thumbnail':  ('src',),
    'button':     ('text',),
    'link-row':   ('links',),
    'table':      ('headers', 'rows'),
    'accordion':  ('cards',),
}

_SVG_ID_KEYS = {
    'separator': ('svg',),
    'critter':   ('svg',),
    'media':     ('critter',),
    'gallery':   ('critter',),
}


def validate_blocks(raw_blocks, source):
    pool = asset_id_pool()
    errors = 0
    for i, b in enumerate(raw_blocks):
        t = b.get('type', '')
        if t and t not in _REQUIRED_KEYS and t != 'html-asset':
            print(f'WARNING: {source} block {i}: unknown type {t!r}', file=sys.stderr)
        for key in _REQUIRED_KEYS.get(t, ()):
            if key not in b:
                print(f'ERROR: {source} block {i} (type {t!r}): '
                      f'missing required key {key!r}', file=sys.stderr)
                errors += 1
        for key in _SVG_ID_KEYS.get(t, ()):
            if key in b and pool:
                aid = norm_asset_id(b[key])
                if aid not in pool:
                    print(f'WARNING: {source} block {i} (type {t!r}): '
                          f'svg id {aid!r} not in asset pool — will render '
                          f'empty', file=sys.stderr)
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# SVG id collection — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

def collect_svgs(blocks):
    seen = []
    seen_set = set()
    for b in blocks:
        ids = []
        if b.get('type') in ('separator', 'critter'):
            ids.append(b['svg'])
        if b.get('type') in ('media', 'gallery') and 'critter' in b:
            ids.append(b['critter'])
        for svg_id in ids:
            if svg_id not in seen_set:
                seen.append(svg_id)
                seen_set.add(svg_id)
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# Section nav — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

def _nav_label(text):
    return text.split('(')[0].strip()


def build_section_nav(blocks):
    h2s = [(b['id'], _nav_label(b['text']))
           for b in blocks
           if b.get('type') == 'heading' and b.get('level') == 2]
    desktop_links = '\n'.join(
        f'<a href="#{sid}">{esc(label)}</a>'
        for sid, label in h2s
    )
    mobile_links = '\n    '.join(
        f'<a href="#{sid}">{esc(label)}</a>'
        for sid, label in h2s
    )
    return desktop_links, mobile_links


# ─────────────────────────────────────────────────────────────────────────────
# Inline scripts — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

_SCRIPTS = '''\
<script>
// ── Sidebar toggle ─────────────────────────────────────────────────────────
const _sb=document.getElementById('sidebar')
const _st=document.getElementById('sidebar-toggle')
if(_sb&&_st){
  _st.addEventListener('click',()=>{
    const hidden=_sb.classList.toggle('hidden')
    _st.textContent=hidden?'▶':'◀'
  })
}
// ── Section tracking ───────────────────────────────────────────────────────
const _navLinks=[...document.querySelectorAll('.section-nav a')]
if(_navLinks.length){
  const _sc=document.getElementById('scroll-container')
  const _setActive=id=>{
    _navLinks.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+id))
  }
  const _io=new IntersectionObserver(entries=>{
    entries.forEach(e=>{if(e.isIntersecting)_setActive(e.target.id)})
  },{root:_sc,rootMargin:'0px 0px -60% 0px',threshold:0})
  const _trackSections=()=>{
    document.querySelectorAll('[id]').forEach(el=>{
      if(_navLinks.some(a=>a.getAttribute('href')==='#'+el.id))_io.observe(el)
    })
  }
  document.addEventListener('pretext:done',_trackSections,{once:true})
  setTimeout(_trackSections,2000)
}

// ── Lightbox close ─────────────────────────────────────────────────────
const _lb=document.getElementById('lightbox')
const _lc=document.getElementById('lightbox-close')
if(_lb&&_lc){
  _lc.addEventListener('click',()=>{_lb.classList.remove('open');const fr=document.getElementById('lightbox-frame');if(fr)setTimeout(()=>{fr.src=''},300)})
  _lb.addEventListener('click',e=>{if(e.target===_lb)_lb.classList.remove('open')})
}
// ── Mobile hamburger ────────────────────────────────────────────────────
const _ham=document.getElementById('mobile-hamburger')
const _stickyNav=document.querySelector('.sticky-nav')
if(_ham&&_stickyNav){
  _ham.addEventListener('click',()=>{
    const open=_stickyNav.classList.toggle('nav-open')
    _ham.setAttribute('aria-expanded',open)
  })
  if(window.registerGradientInteraction)window.registerGradientInteraction(_ham)
}
// ── Section nav FAB (mobile) ────────────────────────────────────────────
const _fab=document.getElementById('section-nav-fab')
const _sheet=document.getElementById('section-nav-sheet')
if(_fab&&_sheet){
  if(window.registerGradientInteraction)window.registerGradientInteraction(_fab)
  _fab.addEventListener('click',()=>{
    const open=_sheet.classList.toggle('open')
    _fab.setAttribute('aria-expanded',open)
    _sheet.setAttribute('aria-hidden',!open)
  })
  _sheet.querySelectorAll('a').forEach(a=>{
    a.addEventListener('click',()=>{
      _sheet.classList.remove('open')
      _fab.setAttribute('aria-expanded','false')
      _sheet.setAttribute('aria-hidden','true')
    })
  })
}
</script>'''


# ─────────────────────────────────────────────────────────────────────────────
# Shell assembly — verbatim from contentpage-builder.py
# ─────────────────────────────────────────────────────────────────────────────

def assemble(meta, doc, blocks_json, svgs_list, section_nav_desktop, section_nav_mobile, asset_ver=0):
    title_html = esc(meta['title'])
    page_title_full = f"{meta['title']} — {doc['site']['title']}"
    meta.setdefault('description', '')
    v = f'?v={asset_ver}'

    # Build SVGS entries: each id maps to an inline <svg><use href="sprite#id"/> string.
    # The pretext engine injects these via innerHTML into the rendered content.
    sprite_base = f'{asset_url("/Media/sprite.svg")}{v}'
    svgs_entries = ',\n  '.join(
        f'[{json.dumps(s)}, {json.dumps(f"<svg width=100% height=100% aria-hidden=true><use href={chr(39)}{sprite_base}#{s}{chr(39)}/></svg>")}]'
        for s in svgs_list
    )

    frames = frame_overlays("contentpages")

    return f'''<!DOCTYPE html>
<html lang="en">
{head_block(page_title_full, meta['description'],
            f'{asset_url("/css/tokens.css")}{v}',
            f'{asset_url("/css/layers.css")}{v}',
            f'{asset_url("/css/sky.css")}{v}',
            f'{asset_url("/css/glow.css")}{v}',
            f'{asset_url("/css/vines.css")}{v}',
            f'{asset_url("/css/content.css")}{v}',
            f'{asset_url("/css/content-page.css")}{v}')}
<body>
{shared_defs_svg()}
<div id="sky" aria-hidden="true"></div>
<canvas id="stars" aria-hidden="true"></canvas>
<div id="sky-glow" aria-hidden="true"></div>
<canvas id="starfield" data-max="60" aria-hidden="true"></canvas>
<div class="page-shell">
{render_navbar(doc, "standard", page_title=meta['title'])}
<div class="page-body">
<div class="left-col" id="left-col-area">
{sidebar_logo()}
  <nav class="sidebar-nav" id="sidebar" aria-label="Sections">
  <div class="page-title">{title_html}</div>
  <nav class="section-nav">
{section_nav_desktop}
  </nav>
  </nav>
  <button class="sidebar-toggle" id="sidebar-toggle" aria-label="Toggle sidebar" title="Toggle sidebar">◀</button>
</div>
<div class="sidebar-gap"></div>
<div style="overflow:hidden;height:100%;grid-column:3">
<div id="scroll-container"><div id="content-area"></div></div>
</div>
</div>
</div>
<div id="lightbox" role="dialog" aria-modal="true" aria-label="Media viewer">
  <div id="lightbox-inner">
    <button id="lightbox-close" aria-label="Close">&#x2715;</button>
    <iframe id="lightbox-frame" src="" allowfullscreen></iframe>
  </div>
</div>
<div class="section-nav-sheet" id="section-nav-sheet" aria-hidden="true">
  <div class="page-title">{title_html}</div>
  <nav class="section-nav-mobile">
    {section_nav_mobile}
  </nav>
</div>
<button class="section-nav-fab" id="section-nav-fab" aria-label="Section navigation" aria-expanded="false">§</button>
{frames}
<script src="{asset_url("/js/shimmer.js")}{v}"></script>
<script type="module">
import {{ PretextEngine }} from '{asset_url("/js/pretext-engine.js")}{v}'
const BLOCKS={blocks_json}
const SVGS = Object.fromEntries([
  {svgs_entries}
])
window._pretextEngine = new PretextEngine(); window._pretextEngine.init(
  document.getElementById('content-area'),
  document.getElementById('scroll-container'),
  BLOCKS, SVGS
)
</script>
{_SCRIPTS}
<script src="{asset_url("/js/starfield.js")}{v}" defer></script>
</body>
</html>'''


# ─────────────────────────────────────────────────────────────────────────────
# Build entry point
# ─────────────────────────────────────────────────────────────────────────────

def build(unit, root):
    with open(unit.yaml_path, encoding='utf-8') as f:
        page_doc = yaml.safe_load(f)

    meta       = page_doc['meta']
    raw_blocks = page_doc.get('blocks', [])

    # set_rel_prefix before transform_block so norm_path uses correct prefix
    set_rel_prefix(unit.output, root)

    errors = validate_blocks(raw_blocks, unit.yaml_path.name)
    if errors:
        print(f'ERROR: {errors} invalid block(s) in {unit.yaml_path.name}; aborting.',
              file=sys.stderr)
        sys.exit(1)

    blocks   = [transform_block(b) for b in raw_blocks]
    svgs_list = collect_svgs(blocks)
    section_nav_desktop, section_nav_mobile = build_section_nav(blocks)
    blocks_json = json.dumps(blocks, ensure_ascii=False)

    doc = load_yaml('Toolbox/Python/site.yaml')

    html = assemble(meta, doc, blocks_json, svgs_list,
                    section_nav_desktop, section_nav_mobile,
                    asset_ver=asset_version(root))
    write_output(unit.output, html)
