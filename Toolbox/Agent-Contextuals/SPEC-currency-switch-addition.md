# tags: [spec, currency-switch, table-extension, sticky-toggle, builder-notes, v0.1]
# Append to SPEC-content-schema.md. Companion to SPEC-card-group-addition.md.

---

## Currency Switching

Applies to `table` blocks (including those inside `card-group` content).
Adds explicit per-currency row sets, a runtime locale-detection default,
and a sticky toggle for manual override.

---

### YAML extension — table block

```yaml
- type: table
  rates_public: true        # [rates-block]
  headers: [Engagement, Standard, Partner Rate]
  rows:                     # USD — shown if no locale match or en-US etc.
    - [Day rate, "$500", "$340"]
  rows_eur:                 # EUR — shown for en-GB, en-IE, and EU locales
    - [Day rate, "€460", "€313"]
  rows_zar:                 # ZAR — shown for Global South locales (see map below)
    - [Day rate, "R ???", "R ???"]   # TODO: set independently
```

`rows` remains required and serves as the USD fallback.
`rows_eur` and `rows_zar` are optional. If absent, the table is not
currency-switchable and `rows` always renders.
A table with only `rows` renders identically to the current schema — no
builder regression.

---

### Builder implementation notes

1. **Emit three tbody elements per switchable table**, each with a
   `data-currency` attribute:
   ```html
   <tbody data-currency="usd"> ... </tbody>
   <tbody data-currency="eur" hidden> ... </tbody>
   <tbody data-currency="zar" hidden> ... </tbody>
   ```
   The `hidden` attribute is set on non-default bodies at build time.
   The runtime JS removes/adds `hidden` on currency change.
   Use `hidden` (not `display:none`) for no-JS fallback: all three tbody
   elements are visible without JS — redundant but readable.

2. **Mark the table element** with `data-multicurrency="true"` if any of
   `rows_eur` or `rows_zar` are present, so the toggle JS can find
   switchable tables efficiently.

3. **Currency toggle JS** — add to the page script bundle:

```javascript
// ── Currency detection ───────────────────────────────────────────────────
const ZAR_LANGS = new Set([
  'af','zu','xh','st','tn','ts','ve','nr','ss', // SA official languages
  'sw','ha','am','yo','ig','ff','wo','ln',      // sub-Saharan Africa
  'ar','hi','bn','ur','ne','si','my','km','lo', // South/Southeast Asia
  'id','ms','tl','jv','su','ceb',              // Southeast Asia
  'pt-BR',                                      // Brazil
]);
const EUR_LANGS = new Set([
  'en-GB','en-IE',
  'de','fr','nl','it','es-ES','pt-PT','pl','sv',
  'da','fi','nb','nn','cs','sk','ro','hu','hr',
  'bg','el','lt','lv','et','sl','ga','mt','lb',
]);

function detectCurrency() {
  const langs = navigator.languages || [navigator.language || 'en'];
  for (const lang of langs) {
    const base = lang.split('-')[0].toLowerCase();
    const full = lang.toLowerCase();
    if (ZAR_LANGS.has(full) || ZAR_LANGS.has(base)) return 'zar';
    if (EUR_LANGS.has(full) || EUR_LANGS.has(base)) return 'eur';
    // pt-BR check: Portuguese but not pt-PT
    if (base === 'pt' && !lang.toLowerCase().startsWith('pt-pt')) return 'zar';
    // es: Latin America (not es-ES) → zar
    if (base === 'es' && full !== 'es-es') return 'zar';
    // fr: sub-Saharan French (not fr-FR, fr-BE, fr-CH, fr-LU, fr-CA) → zar
    if (base === 'fr' && !['fr-fr','fr-be','fr-ch','fr-lu','fr-ca'].includes(full)) return 'zar';
  }
  return 'usd'; // default
}

// ── Toggle behaviour ─────────────────────────────────────────────────────
let activeCurrency = detectCurrency();

function setCurrency(code) {
  activeCurrency = code;
  document.querySelectorAll('table[data-multicurrency] tbody[data-currency]')
    .forEach(tb => { tb.hidden = tb.dataset.currency !== code; });
  document.querySelectorAll('.currency-btn')
    .forEach(btn => btn.classList.toggle('active', btn.dataset.currency === code));
  try { localStorage.setItem('jl-currency', code); } catch(_) {}
}

// Restore saved preference before first paint
try {
  const saved = localStorage.getItem('jl-currency');
  if (saved && ['usd','eur','zar'].includes(saved)) activeCurrency = saved;
} catch(_) {}

document.addEventListener('DOMContentLoaded', () => {
  setCurrency(activeCurrency); // apply default/saved
  document.querySelectorAll('.currency-btn').forEach(btn => {
    btn.addEventListener('click', () => setCurrency(btn.dataset.currency));
    registerGradientInteraction(btn); // hook into shimmer rAF
  });
});
```

4. **localStorage persistence** — saves the user's last choice across
   page loads. Fails silently in private browsing.

---

### Toggle component — sticky bottom-right

```html
<div class="currency-toggle" role="group" aria-label="Pricing currency">
  <span class="currency-toggle__label">Pricing in</span>
  <button class="currency-btn" data-currency="zar">ZAR</button>
  <button class="currency-btn" data-currency="usd">USD</button>
  <button class="currency-btn" data-currency="eur">EUR</button>
</div>
```

CSS:
```css
.currency-toggle {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 300;
  display: flex;
  align-items: center;
  gap: .5em;
  background: rgba(1,4,3,.92);
  border: 1px solid rgba(232,226,218,.12);
  border-radius: 3px;
  padding: .4em .8em;
  font-family: 'Walter Turncoat', cursive;
  font-size: .85rem;
}
.currency-toggle__label {
  color: var(--light);
  opacity: .5;
  font-size: .75rem;
}
.currency-btn {
  background: transparent;
  border: none;
  color: var(--light);
  opacity: .55;
  cursor: pointer;
  font-family: inherit;
  font-size: inherit;
  padding: .15em .4em;
  border-radius: 2px;
  transition: none; /* no transitions — design rule */
}
.currency-btn:hover  { opacity: 1; color: var(--fire); }
.currency-btn.active {
  opacity: 1;
  color: var(--sun);
  /* shimmer border via SVG wrap — see note below */
}
```

**Active state shimmer border** — wrap each active button in the
`media-btn-wrap` SVG pattern (DESIGN.md §5.2) via JS when activated,
remove when deactivated. Simplest implementation: toggle a class
`.currency-btn--active-wrap` and use a pre-rendered SVG border element
that JS shows/hides. Do not use CSS `outline` or `box-shadow` —
design rule prohibits non-shimmer borders on interactive elements.

**No-JS fallback** — the toggle is injected by JS. Without JS all three
`tbody` elements are visible (stacked, each with a header row). Acceptable.
The toggle label should read "Pricing in" to be self-explanatory.

**Visibility** — only render the toggle if at least one
`table[data-multicurrency]` exists on the page. Check at
`DOMContentLoaded` before injecting.

---

### ZAR calibration note (for content authors)

ZAR values are set independently of USD/EUR — they are not conversions.
They are priced to be genuinely competitive against international suppliers
for Global South clients. Mark all ZAR cells `# TODO` until deliberately set.
Do not auto-populate ZAR from USD × exchange rate.

---
# tags: [spec, currency-switch, table-extension, sticky-toggle, builder-notes, v0.1]
