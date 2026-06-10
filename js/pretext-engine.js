/**
 * pretext-engine.js — JL Kruger Content Page Renderer
 * tags: pretext scroll-effect focal-layout content-page engine
 *
 * API (static site use):
 *   import { PretextEngine } from '/js/pretext-engine.js'
 *   new PretextEngine().init(containerEl, scrollEl, BLOCKS, SVGS)
 *
 * BLOCKS and SVGS are embedded by contentpage-builder.py at build time.
 * Pages are static — no rebuild path. If content changes, rebuild and redeploy.
 *
 * Spool effect: CSS scroll-driven animations (animation-timeline: view())
 * handle scale and opacity. JS only manages rich content lazy-loading via
 * IntersectionObserver — no scroll listener, no forced reflow.
 */

import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'

// ── Configuration ─────────────────────────────────────────────────────────
const CONFIG = {
  EDGE:        0.60,   // stable zone boundary — used to size IO rootMargin
  BASE_LINE_PX: 27,    // base line height in px (18px font × 1.5 lh)
  LH:           1.5,

  COLORS: {
    h1: '#eb7513', h2: '#5e9a0e', h3: '#5e9a0e',
    h4: '#a52c16', h5: '#a52c16', h6: '#a52c16',
    special: '#f2c62a', quote: '#f2c62a', paragraph: '#e8e2da'
  },
  FONTS: {
    paragraph: '400 18px Overlock',
    special:   '400 21px "Protest Revolution"',
    quote:     '400 21px "Protest Revolution"',
    h1:  '400 50px Tagesschrift',
    h2:  '400 32px "Walter Turncoat"',
    h3:  '400 24px "Walter Turncoat"',
    h4:  '400 22px "Walter Turncoat"',
    h5:  '400 20px "Walter Turncoat"',
    h6:  '400 18px "Walter Turncoat"',
    mono: '400 15px "Courier New"'
  },
  BASE_SIZES: {
    paragraph: 18, special: 21, quote: 21,
    h1: 50, h2: 32, h3: 24, h4: 22, h5: 20, h6: 18, mono: 15
  },

  SPACING: {
    default:   { before: 0, after: 1 },
    h1:        { before: 2, after: 1 },
    h2:        { before: 1, after: 1 },
    separator: { before: 1, after: 2 },
    critter:   { before: 1, after: 2 },
    media:     { before: 1, after: 1 },
    image:     { before: 1, after: 1 },
    accordion: { before: 1, after: 1 },
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

// ── Inline markup extraction ──────────────────────────────────────────────
function _extractSpans(raw, offset) {
  const spans = []; let clean = '', i = 0
  while (i < raw.length) {
    const lm = raw.slice(i).match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (lm) {
      spans.push({ start: offset+clean.length, end: offset+clean.length+lm[1].length, type: 'a', href: lm[2] })
      clean += lm[1]; i += lm[0].length; continue
    }
    clean += raw[i++]
  }
  return { clean, spans }
}
function extractMarkup(raw) {
  const spans = []; let clean = '', i = 0
  while (i < raw.length) {
    const bm = raw.slice(i).match(/^\*\*(.+?)\*\*/s)
    if (bm) {
      const bs = clean.length; const inner = _extractSpans(bm[1], bs)
      spans.push({ start: bs, end: bs + inner.clean.length, type: 'strong' })
      inner.spans.forEach(sp => spans.push(sp))
      clean += inner.clean; i += bm[0].length; continue
    }
    const lm = raw.slice(i).match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (lm) {
      spans.push({ start: clean.length, end: clean.length+lm[1].length, type: 'a', href: lm[2] })
      clean += lm[1]; i += lm[0].length; continue
    }
    clean += raw[i++]
  }
  return { clean, spans }
}
function applyMarkupToLine(lineText, lineStart, spans) {
  const len = lineText.length; const events = []
  for (const sp of spans) {
    const s = Math.max(0, sp.start - lineStart), e = Math.min(len, sp.end - lineStart)
    if (e <= 0 || s >= len || s >= e) continue
    events.push({ pos: s, open: true, sp }); events.push({ pos: e, open: false, sp })
  }
  events.sort((a, b) => a.pos - b.pos || (a.open ? 1 : -1))
  let html = '', pos = 0; const stack = []
  const openTag  = sp => sp.type === 'strong' ? '<strong>' : `<a href="${sp.href}">`
  const closeTag = sp => sp.type === 'strong' ? '<\/strong>' : '<\/a>'
  for (const ev of events) {
    if (pos < ev.pos) html += esc(lineText.slice(pos, ev.pos))
    pos = ev.pos
    if (ev.open) { stack.push(ev.sp); html += openTag(ev.sp) }
    else {
      const idx = stack.indexOf(ev.sp); if (idx < 0) continue
      const reopen = stack.slice(idx + 1)
      for (let j = stack.length - 1; j >= idx; j--) html += closeTag(stack[j])
      stack.splice(idx, 1)
      for (const s of reopen) html += openTag(s)
    }
  }
  if (pos < len) html += esc(lineText.slice(pos))
  for (const s of [...stack].reverse()) html += closeTag(s)
  return html
}

// ── Word-wrap for monospace table cells ───────────────────────────────────
function wordWrapCell(text, width, opts) {
  if (width <= 0) return ['']
  const words = String(text).replace(/\s+/g, ' ').trim().split(' ')
  const lines = []; let cur = ''
  for (let w of words) {
    if (w.length > width) w = w.slice(0, width - 1) + '…'
    if (!cur) { cur = w; continue }
    if (opts?.breakOnParen && w.startsWith('(')) { lines.push(cur); cur = w; continue }
    if ((cur + ' ' + w).length <= width) { cur += ' ' + w }
    else { lines.push(cur); cur = w }
  }
  if (cur) lines.push(cur)
  return lines.length ? lines : ['']
}

// ── Engine class ──────────────────────────────────────────────────────────
export class PretextEngine {

  // init(containerEl, scrollEl, blocks, svgs, commonSvgs) → void
  // Called once per page. Awaits fonts, then builds DOM and starts IO.
  init(containerEl, scrollEl, blocks, svgs, commonSvgs) {
    this._fontsP   = document.fonts.ready
    this.container = containerEl
    this.scrollEl  = scrollEl
    this.blocks    = blocks
    this.svgs      = svgs || {}
    const _common  = commonSvgs || {}

    Object.keys(this.svgs).forEach(k => {
      const h = k.replace(/_/g, '-')
      if (h !== k && !this.svgs[h]) this.svgs[h] = this.svgs[k]
    })
    Object.keys(_common).forEach(k => {
      const h = k.replace(/_/g, '-')
      if (!this.svgs[h]) this.svgs[h] = _common[k]
    })

    this.colWidth = 0

    new ResizeObserver(entries => {
      const w = entries[0].contentRect.width
      if (w <= 0) return
      if (!this._roReady) {
        this._fontsP.then(() => {
          this.colWidth = w
          this.buildDOM()
          this._observeRichLines()
          this._roReady = true
          document.dispatchEvent(new CustomEvent('pretext:done'))
        })
      } else if (Math.abs(w - this.colWidth) > 5) {
        this.colWidth = w
        this.buildDOM()
        this._observeRichLines()
      }
    }).observe(containerEl)

    const w0 = containerEl.getBoundingClientRect().width
    if (w0 > 0 && !this._roReady) {
      this._fontsP.then(() => {
        if (this._roReady) return
        this.colWidth = w0
        this.buildDOM()
        this._observeRichLines()
        this._roReady = true
        document.dispatchEvent(new CustomEvent('pretext:done'))
      })
    }
  }

  // ── DOM build ──────────────────────────────────────────────────────────
  buildDOM() {
    this.container.innerHTML = ''

    const spacer = n => {
      for (let i = 0; i < n; i++) {
        const d = document.createElement('div')
        d.className = 'line'
        d.dataset.baseSize  = 18
        d.dataset.baseColor = '#e8e2da'
        d.style.fontSize = '18px'
        d.style.setProperty('--lc', '#e8e2da')
        d.innerHTML = '&nbsp;'
        this.container.appendChild(d)
      }
    }

    this.blocks.forEach(b => {
      const sp = CONFIG.SPACING[b.type] || CONFIG.SPACING.default
      if (sp.before) spacer(sp.before)
      const frag = this.renderBlock(b)
      if (frag) this.container.appendChild(frag)
      if (sp.after) spacer(sp.after)
    })
  }

  // ── Block router ───────────────────────────────────────────────────────
  renderBlock(b) {
    const type = b.type

    if (type === 'heading') {
      const k = `h${b.level}`
      return this.buildTextBlock(b.text, CONFIG.FONTS[k], CONFIG.BASE_SIZES[k], '', CONFIG.COLORS[k] || '#e8e2da', b.id)
    }
    if (type === 'paragraph') {
      const frag = document.createDocumentFragment()
      b.text.split('\n').forEach(p => {
        if (p.trim()) frag.appendChild(
          this.buildTextBlock(p.trim(), CONFIG.FONTS.paragraph, CONFIG.BASE_SIZES.paragraph, '', CONFIG.COLORS.paragraph)
        )
      })
      return frag
    }
    if (type === 'special' || type === 'quote') {
      const frag = this.buildTextBlock(b.text, CONFIG.FONTS.special, CONFIG.BASE_SIZES.special, 'special-line', CONFIG.COLORS.special)
      if (b.attribution) {
        const a = document.createElement('div')
        a.className = 'line attrib'
        a.dataset.baseSize = 16; a.dataset.baseColor = '#e8e2da'
        a.style.fontSize = '16px'; a.style.setProperty('--lc', '#e8e2da')
        a.textContent = b.attribution
        frag.appendChild(a)
      }
      return frag
    }
    if (type === 'separator')  return this.mkRichLine('separator-line',        { svgKey: b.svg })
    if (type === 'critter')    return this.mkRichLine('critter-line critter-solo', { critterSvg: b.svg })
    if (type === 'media') {
      if (b.critter)
        return this.mkRichLine('critter-line', { critterSvg: b.critter, mediaSrc: b.src, mediaTitle: b.text || '' })
      return this.mkRichLine('button-line', { mediaSrc: b.src, mediaTitle: b.text || '' })
    }
    if (type === 'image')     return this.mkRichLine('image-line',             { imgSrc: b.src, imgAlt: b.alt || '' })
    if (type === 'thumbnail') return this.mkRichLine('image-line thumbnail-line', { imgSrc: b.src, imgAlt: b.alt || '' })
    if (type === 'button')    return this.mkRichLine('button-line btn-nav',    { mediaSrc: b.href, mediaTitle: b.text })
    if (type === 'link-row') {
      const div = document.createElement('div')
      div.className = 'line'
      div.dataset.baseSize = 20
      div.style.fontSize = '20px'
      div.style.setProperty('--lc', '#e8e2da')
      const row = document.createElement('div'); row.className = 'link-row'
      b.links.forEach(l => {
        const a = document.createElement('a'); a.href = l.href; a.textContent = l.text
        row.appendChild(a)
      })
      div.appendChild(row); return div
    }
    if (type === 'table')      return this.buildTerminalTable(b)
    if (type === 'accordion')  return this.buildAccordion(b)
    if (type === 'html-asset') return this.mkRichLine('html-asset-line',       { assetKey: b.file })
    return null
  }

  // ── Text block (Pretext) ───────────────────────────────────────────────
  buildTextBlock(text, font, sz, cls, bc, id) {
    const frag = document.createDocumentFragment()
    if (id) {
      const anchor = document.createElement('div')
      anchor.id = id; anchor.style.cssText = 'position:relative;top:-2rem'
      frag.appendChild(anchor)
    }
    const { clean, spans } = extractMarkup(text)
    const { lines } = layoutWithLines(
      prepareWithSegments(clean, font, { whiteSpace: 'pre-wrap' }),
      this.colWidth,
      sz * CONFIG.LH
    )
    let pos = 0
    lines.forEach(l => {
      const div = document.createElement('div')
      div.className = 'line' + (cls ? ' ' + cls : '')
      div.dataset.baseSize  = sz
      div.dataset.baseColor = bc || '#e8e2da'
      div.style.fontSize = sz + 'px'
      div.style.fontFamily = font.split(/\d+px\s*/)[1]
      div.style.setProperty('--lc', bc || '#e8e2da')
      div.innerHTML = applyMarkupToLine(l.text, pos, spans)
      frag.appendChild(div)
      pos += l.text.length
      if (pos < clean.length && clean[pos] === ' ') pos++
    })
    return frag
  }

  mkRichLine(cls, data) {
    const div = document.createElement('div')
    div.className = 'line rich-line ' + cls
    div.dataset.rich = 'true'; div.dataset.loaded = 'false'
    Object.keys(data).forEach(k => { if (data[k] != null) div.dataset[k] = data[k] })
    return div
  }

  // ── Terminal table ─────────────────────────────────────────────────────
  buildTerminalTable(b) {
    const frag = document.createDocumentFragment()
    const allRows = [...(b.headers ? [b.headers] : []), ...(b.rows || [])]
    const nCols = allRows[0]?.length || 0
    if (!nCols) return frag

    const strip = s => String(s)
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/\*/g, '')

    const alignCell = (text, width, dir) =>
      dir === 'R' ? text.padStart(width) : text.padEnd(width)

    const GUTTER     = ' | '
    const GUTTER_SEP = '─┼─'

    const charW      = this.getCourierCharW()
    const totalChars = Math.floor(this.colWidth / charW)
    const pipeTotal  = (nCols - 1) * GUTTER.length

    // Fixed schema: last col = year (9), second-to-last = role (22), first = expand.
    // Year width = 9 fits "YYYY–YYYY" on one line; longer ranges split on the en-dash.
    const fixedWidths = b.col_widths
      ? b.col_widths.slice()
      : Array.from({ length: nCols }, (_, i) => {
          if (i === nCols - 1) return 9
          if (i === nCols - 2) return 22
          return null
        })

    const fixedSum    = fixedWidths.reduce((s, w) => s + (w || 0), 0)
    const expandWidth = Math.max(6, totalChars - fixedSum - pipeTotal)
    const colWidths   = fixedWidths.map(w => w ?? expandWidth)

    // Last column right-aligned, rest left-aligned
    const colAligns = b.col_aligns
      ? b.col_aligns
      : Array.from({ length: nCols }, (_, i) => i === nCols - 1 ? 'R' : 'L')

    // Year column: split on en-dash so "2018–Present" wraps cleanly to two lines
    const wrapCell = (cell, i) => {
      const s = strip(cell)
      if (i === nCols - 1) {
        if (s.length <= colWidths[i]) return [s]
        const dash = s.indexOf('–')
        if (dash !== -1) return [s.slice(0, dash + 1), s.slice(dash + 1)].filter(p => p)
      }
      return wordWrapCell(s, colWidths[i], i === 0 ? { breakOnParen: true } : undefined)
    }

    const SZ = CONFIG.BASE_SIZES.mono

    const appendLine = (text, bc, cls) => {
      const d = document.createElement('div')
      d.className = 'line' + (cls ? ' ' + cls : '')
      d.dataset.baseSize  = SZ
      d.dataset.baseColor = bc
      d.style.fontFamily  = '"Courier New", monospace'
      d.style.fontSize    = SZ + 'px'
      d.style.whiteSpace  = 'pre'
      d.style.setProperty('--lc', bc)
      d.textContent = text
      frag.appendChild(d)
    }

    const renderRow = (row, bc) => {
      const wrapped = row.map((cell, i) => wrapCell(cell, i))
      const height = Math.max(...wrapped.map(c => c.length))
      for (let l = 0; l < height; l++) {
        const line = wrapped
          .map((c, i) => alignCell(c[l] || '', colWidths[i], colAligns[i]))
          .join(GUTTER)
        appendLine(line, bc)
      }
    }

    if (b.headers) {
      renderRow(b.headers, CONFIG.COLORS.h3)
      appendLine(colWidths.map(w => '─'.repeat(w)).join(GUTTER_SEP), '#442204', 'table-terminal-sep')
    }
    const rows = b.rows || []
    rows.forEach((row, ri) => {
      renderRow(row, CONFIG.COLORS.paragraph)
      if (ri < rows.length - 1) appendLine(colWidths.map(w => ' '.repeat(w)).join(GUTTER), CONFIG.COLORS.paragraph)
    })
    return frag
  }

  getCourierCharW() {
    if (this._courierCharW) return this._courierCharW
    const c = document.createElement('canvas')
    const ctx = c.getContext('2d')
    ctx.font = `${CONFIG.BASE_SIZES.mono}px "Courier New"`
    this._courierCharW = ctx.measureText('W').width || 9.6
    return this._courierCharW
  }

  // ── Rich content lazy-loading ──────────────────────────────────────────
  // IntersectionObserver fires when rich lines enter the preload margin
  // (30% of the stable zone above/below the scroll root). No scroll reads,
  // no layout invalidation.
  _observeRichLines() {
    if (this._richObserver) this._richObserver.disconnect()

    const margin = Math.round(this.scrollEl.clientHeight * 0.5 * CONFIG.EDGE)

    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const el = entry.target
        if (entry.isIntersecting && el.dataset.loaded !== 'true' && el.dataset.anim !== 'out') {
          this.insertRichContent(el)
        }
      })
    }, { root: this.scrollEl, rootMargin: `${margin}px 0px`, threshold: 0 })

    this.container.querySelectorAll('.rich-line').forEach(el => io.observe(el))
    this._richObserver = io
  }

  // ── Rich content insert/remove ─────────────────────────────────────────
  insertRichContent(wrapper) {
    wrapper.dataset.loaded = 'true'
    const inner = document.createElement('div')
    const cls = wrapper.classList
    const rgi = window.registerGradientInteraction

    if (cls.contains('separator-line')) {
      inner.style.cssText = 'width:100%;height:100%;opacity:0;transform:scale(.88);display:flex;align-items:center;'
      inner.innerHTML = this.svgs[wrapper.dataset.svgKey] || ''
      if (rgi) rgi(inner)

    } else if (cls.contains('critter-line')) {
      const isSolo = cls.contains('critter-solo')
      inner.style.cssText = `display:flex;align-items:center;justify-content:center;gap:.8em;width:100%;height:100%;opacity:0;transform:scale(.88);`
      const sw = document.createElement('div'); sw.className = 'critter-svg-wrap'
      sw.innerHTML = this.svgs[wrapper.dataset.critterSvg] || ''; inner.appendChild(sw)
      if (wrapper.dataset.mediaSrc) {
        const bw = this._mkBtnWrap(wrapper.dataset.mediaSrc, wrapper.dataset.mediaTitle)
        inner.appendChild(bw); if (rgi) rgi(bw)
      }
      if (rgi) rgi(sw)

    } else if (cls.contains('image-line')) {
      inner.style.cssText = 'display:flex;justify-content:center;align-items:center;opacity:0;transform:scale(.88);width:100%;'
      const img = document.createElement('img'); img.src = wrapper.dataset.imgSrc; img.alt = wrapper.dataset.imgAlt
      img.style.cssText = cls.contains('thumbnail-line')
        ? 'width:120px;height:120px;object-fit:cover;border-radius:50%;'
        : 'max-width:100%;height:auto;display:block;'
      inner.appendChild(img)

    } else if (cls.contains('button-line')) {
      inner.style.cssText = 'display:flex;align-items:center;opacity:0;transform:scale(.88);'
      const bw = this._mkBtnWrap(wrapper.dataset.mediaSrc, wrapper.dataset.mediaTitle, cls.contains('btn-nav'))
      inner.appendChild(bw); if (rgi) rgi(bw)

    } else if (cls.contains('html-asset-line')) {
      inner.style.cssText = 'display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(.88);'
      const fr = document.createElement('iframe')
      fr.style.cssText = 'border:none;width:100%;height:220px;display:block;overflow:hidden;'
      fr.setAttribute('scrolling', 'no')
      fr.srcdoc = this.svgs[wrapper.dataset.assetKey] || ''
      inner.appendChild(fr); if (rgi) rgi(inner)
    }

    wrapper.appendChild(inner)
    requestAnimationFrame(() => {
      inner.style.transition = 'opacity 880ms ease,transform 880ms cubic-bezier(0.34,1.56,0.64,1)'
      requestAnimationFrame(() => { inner.style.opacity = '1'; inner.style.transform = 'scale(1)' })
    })
  }

  removeRichContent(wrapper) {
    if (wrapper.dataset.anim === 'out') return
    wrapper.dataset.anim = 'out'
    const inner = wrapper.firstElementChild
    if (!inner) { wrapper.innerHTML = ''; wrapper.dataset.loaded = 'false'; wrapper.dataset.anim = ''; return }
    inner.style.transition = 'opacity 400ms ease,transform 400ms ease'
    inner.style.opacity = '0'; inner.style.transform = 'scale(.88)'
    setTimeout(() => { wrapper.innerHTML = ''; wrapper.dataset.loaded = 'false'; wrapper.dataset.anim = '' }, 420)
  }

  // ── Button helper ──────────────────────────────────────────────────────
  _mkBtnWrap(src, title, isNav = false) {
    const w = document.createElement('span'); w.className = 'media-btn-wrap'
    const s = document.createElementNS('http://www.w3.org/2000/svg','svg')
    s.setAttribute('class','media-btn-border'); s.setAttribute('aria-hidden','true')
    const r = document.createElementNS('http://www.w3.org/2000/svg','rect')
    r.setAttribute('class','media-btn-rect')
    r.setAttribute('x','.75'); r.setAttribute('y','.75'); r.setAttribute('width','99%'); r.setAttribute('height','99%'); r.setAttribute('rx','3')
    s.appendChild(r); w.appendChild(s)
    if (isNav) {
      const a = document.createElement('a'); a.className = 'media-btn-link'; a.href = src
      a.innerHTML = `<svg class="play-icon" viewBox="0 0 16 16"><polygon points="3,2 13,8 3,14"\/><\/svg>${title || 'Open'}`
      w.appendChild(a)
    } else {
      const btn = document.createElement('button'); btn.className = 'media-btn'
      btn.innerHTML = `<svg class="play-icon" viewBox="0 0 16 16"><polygon points="3,2 13,8 3,14"\/><\/svg>${title || 'Open Media'}`
      btn.addEventListener('click', () => {
        const frame = document.getElementById('lightbox-frame')
        if (frame) frame.src = src
        document.getElementById('lightbox')?.classList.add('open')
      })
      w.appendChild(btn)
    }
    return w
  }

  // ── Accordion (native <details>; content spools via the engine) ──────────
  // Both the summary (title + teaser) and the expanded content render as
  // Pretext lines, so they keep the scroll-spool like the rest of the page.
  // Text is laid out at (colWidth − ACC_INDENT) and the panel is padded by the
  // same amount, so the chevron column and the body align and lines stay full-
  // width-measured (never a narrow modal → no wrap/clip bug). ACC_INDENT must
  // match content-page.css (.accordion-chevron width + .accordion-panel pad).
  buildAccordion(b) {
    const ACC_INDENT = 28
    const frag = document.createDocumentFragment()
    const name = 'acc-' + (this._accGroups = (this._accGroups || 0) + 1)
    const full = this.colWidth
    const inner = Math.max(40, full - ACC_INDENT)

    ;(b.cards || []).forEach(c => {
      const det = document.createElement('details')
      det.className = 'accordion-item'
      det.name = name   // exclusive: opening one closes the others in this group

      // Summary is plain semantic HTML (real <summary> text → accessible, wraps
      // natively, never depends on the line engine). Only the expanded panel
      // runs through Pretext so it keeps the scroll-spool.
      const sum = document.createElement('summary')
      sum.className = 'accordion-summary'
      sum.innerHTML =
        '<span class="accordion-chevron" aria-hidden="true"></span>' +
        '<span class="accordion-summary-text">' +
          `<span class="accordion-title">${esc(c.title)}</span>` +
          (c.description ? `<span class="accordion-teaser">${esc(c.description)}</span>` : '') +
        '</span>'
      det.appendChild(sum)

      const panel = document.createElement('div')
      panel.className = 'accordion-panel'
      this.colWidth = inner
      ;(c.content || []).forEach(cb => {
        const sp = CONFIG.SPACING[cb.type] || CONFIG.SPACING.default
        if (sp.before) this._spacer(panel, sp.before)
        const cfrag = this.renderBlock(cb)
        if (cfrag) panel.appendChild(cfrag)
        if (sp.after) this._spacer(panel, sp.after)
      })
      this.colWidth = full
      det.appendChild(panel)
      // On open, (re)observe so any lazy rich-line in the panel (e.g. a button)
      // that was display:none at build time gets picked up and loaded.
      det.addEventListener('toggle', () => { if (det.open) this._observeRichLines() })
      frag.appendChild(det)
    })
    return frag
  }

  // Append n blank spool lines to an arbitrary target (panel-local spacer).
  _spacer(target, n) {
    for (let i = 0; i < n; i++) {
      const d = document.createElement('div')
      d.className = 'line'
      d.dataset.baseSize = 18; d.dataset.baseColor = '#e8e2da'
      d.style.fontSize = '18px'; d.style.setProperty('--lc', '#e8e2da')
      d.innerHTML = '&nbsp;'
      target.appendChild(d)
    }
  }
}
