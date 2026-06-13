// shimmer.js — gradient rAF loop + interaction registration
// tags: shimmer animation gradient raf interaction

const GRAD_IDS = [
  { id: 'shimmer-org-h',    off: 0   },
  { id: 'shimmer-org-v',    off: 90  },
  { id: 'shimmer-geo',      off: 44  },
  { id: 'shimmer-sta',      off: 88  },
  { id: 'shimmer-oth',      off: 144 },
  { id: 'shimmer-ember',    off: 22  },   // warm: sun/fire/rust glow strokes
  { id: 'shimmer-spectral', off: 110 },   // cool: light/meadow/forest glow strokes
]

const GRAD_BASE  = 360 / 22    // 16.4 deg/s
const GRAD_HOVER = 360 / 8     // 45 deg/s
const GRAD_CLICK = 360 / 0.88  // 409 deg/s

let gradAngle  = 0
let gradSpeed  = GRAD_BASE
let gradTarget = GRAD_BASE
let gradLast   = null
let rafId      = null

let isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

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
  document.documentElement.style.setProperty('--shimmer-deg', gradAngle.toFixed(2) + 'deg')
  rafId = requestAnimationFrame(gradTick)
}

function startShimmer() {
  if (!isReducedMotion && rafId === null) {
    gradLast = null
    rafId = requestAnimationFrame(gradTick)
  }
}

function stopShimmer() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null  // must null so startShimmer() can re-enter
  }
}

// Scroll contribution — adds to rotation angle on scroll. Essay pages scroll
// inside #scroll-container; home/hub scroll the window (Phase 3 removed the
// container there), so fall back to window.scrollY when it is absent (D7,
// Phase 3.5.4). Same dy → gradAngle math, passive either way.
function scrollNudge(y) {
  if (isReducedMotion) return
  const dy = y - (window._lastScrollY || 0)
  window._lastScrollY = y
  gradAngle = (gradAngle + dy * 0.025) % 360
}

const _scrollContainer = document.getElementById('scroll-container')
if (_scrollContainer) {
  _scrollContainer.addEventListener('scroll',
    e => scrollNudge(e.target.scrollTop), { passive: true })
} else {
  window.addEventListener('scroll',
    () => scrollNudge(window.scrollY), { passive: true })
}

// OS motion preference changes
window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {
  isReducedMotion = e.matches
  isReducedMotion ? stopShimmer() : startShimmer()
})

function registerGradientInteraction(el) {
  if (!el) return
  el.addEventListener('mouseenter',  () => { gradTarget = GRAD_HOVER })
  el.addEventListener('mouseleave',  () => { gradTarget = GRAD_BASE  })
  el.addEventListener('touchstart',  () => { gradTarget = GRAD_HOVER }, { passive: true })
  el.addEventListener('touchend',    () => { gradTarget = GRAD_BASE  }, { passive: true })
  el.addEventListener('click', () => {
    gradTarget = GRAD_CLICK
    setTimeout(() => { gradTarget = GRAD_BASE }, 880)
  })
}

// Shimmer-nav links (e.g. the logo): on a plain left click, hold for a beat so
// the user sees the shimmer spin up to full speed — and warm the destination
// during that beat — then navigate. Modified/middle clicks and reduced-motion
// fall through to normal navigation.
const SHIMMER_NAV_DELAY = 480  // ms — visible spin + preload window

function wireShimmerNav() {
  document.querySelectorAll('a[data-shimmer-nav]').forEach(a => {
    if (a.dataset.shimmerWired) return
    a.dataset.shimmerWired = '1'
    registerGradientInteraction(a)
    const href = a.getAttribute('href')
    let warmed = false
    const warm = () => {
      if (warmed || !href) return
      warmed = true
      const l = document.createElement('link')
      l.rel = 'prefetch'; l.as = 'document'; l.href = href
      document.head.appendChild(l)
    }
    a.addEventListener('pointerenter', warm, { passive: true })
    a.addEventListener('click', e => {
      if (!href || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey ||
          e.altKey || e.defaultPrevented) return
      e.preventDefault()
      warm()
      gradTarget = GRAD_CLICK
      setTimeout(() => { window.location.href = href },
                 isReducedMotion ? 0 : SHIMMER_NAV_DELAY)
    })
  })
}

startShimmer()
window.registerGradientInteraction = registerGradientInteraction
window.wireShimmerNav = wireShimmerNav
if (document.readyState === 'loading')
  document.addEventListener('DOMContentLoaded', wireShimmerNav)
else
  wireShimmerNav()
