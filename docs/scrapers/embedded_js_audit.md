# Embedded JavaScript audit (`execute_script`) across the scrapers

Snapshot: **257 `execute_script` call sites across 125 scrapers**. `SuperScraper`
historically had **zero** — every snippet was hand-copied into a per-scraper
helper (`_js_set`, `_select_native_option`, `_FILL_JS`, …). This audit is the
basis for the shared helpers now on `SuperScraper` (see the "SuperScraper Method
Reference" in `AGENTS.md`).

pydoll's `execute_script` returns a nested dict
(`{"result": {"result": {"value": X}}}`) and needs a **top-level `return`** (not a
wrapping IIFE). `SuperScraper.js_eval(target, script)` centralises both quirks.

## What the inline JS does, and where it goes

| # | Pattern | ~scrapers | Representative files | Shared helper |
|---|---------|-----------|----------------------|---------------|
| **A** | Select an `<option>` in a native `<select>` by value / visible text / index, then `dispatchEvent('change')` (some also `'input'`). ~60 verbatim `_select_native_option` / `_select_by_value` / `_select_by_text` copies, ~13 inline `document.querySelector("select")` variants, ~6 using the `HTMLSelectElement.prototype` value setter for framework-bound selects. | ~80 | `acxiom`, `deepsync`, `usdatacorporation`, `connectedinvestors`, `traackr`, `aspirenorth`, `spydialer` | `SuperScraper.select_native_option(el, *, value=None, text=None, index=None, ci=False, dispatch=("input","change"))` |
| **B** | Set a value on a React/Angular **controlled** `<input>`/`<textarea>` via the native prototype `value` setter, then dispatch `input`/`change`(/`blur`). ~30 copies (`_js_set`, `_FILL_JS`, `_set_text_via_js`, plus id5/altisource/propstream/iqm/mckessoncompile blocks). Reason: `click()`+`type_text()` silently no-ops on these; a JS input-mask can also corrupt typed input. | ~30 | `enformion`, `issgovernance`, `grin`, `hartehanks`, `gostrata`, `id5`, `lightcast`, `eyeota` | `SuperScraper.js_set_value(el, value, *, blur=False)` (handles INPUT/TEXTAREA and a wrapper around one) |
| **C** | Autocomplete combobox: clear the field via JS, `keyboard.type_text`, then read `this.value` back to verify / click the matching `role=option`. ~8 near-identical OneTrust `_select_autocomplete` / `_select_combobox`. Timing-fragile — each site hand-tuned its sleeps. | ~8 | `viantic`, `dspolitical`, `cybba`, `spglobal`, `kalibrate`, `rhetorik` | `SuperScraper.fill_autocomplete(tab, field, value, *, option_text=None, settle=1.3)` |
| **D** | Check a checkbox/radio in JS (`if(!this.checked) this.click()` or `this.checked=true` + dispatch `click`/`change`) to bypass a 1×1px / visually-hidden / overlay-covered input. ~20 copies. | ~20 | `monitorbase`, `dnb`, `liveramp`, `connectedinvestors`, `issgovernance`, `gostrata` | `SuperScraper.js_check(el, checked=True, *, dispatch=("click","change"))` |
| **E** | Force every `input[name^="__doNotSubmit__"]` Termly attestation checkbox checked + dispatch. Byte-identical in `01advertising` / `atom`; `listkit` clicks the labels instead. | 3 | `01advertising`, `atom`, `listkit` | `SuperScraper.check_termly_attestations(tab)` |
| **F** | Click an arbitrary element via JS `.click()` — overlay interception, `ElementNotVisible` on a genuinely-visible element, or no stable selector. By `aria-label`, by id, by button text, or in a `role=option` loop. | ~15+ | `clarivate`, `veeva`, `jungroup`, `jobot`, `33across`, `media_net` | `SuperScraper.js_click(el)` for the simple case; bespoke `role=option` loops stay inline |
| **G** | Read DOM state: `return document.body.innerText` for a post-submit confirmation check (8); `return this.value` / `this.checked` / `this.type` readbacks (~15); arithmetic-CAPTCHA label extraction (4); visibility/layout checks (`getComputedStyle`, `offsetParent`, `getBoundingClientRect`). The pydoll return-dict unwrap was re-implemented ~33×. | ~40 | `33across`, `civicelement`, `mrginc`, `l2-data`, `usa_people_search` | `SuperScraper.js_eval(target, script)` (unwraps), `SuperScraper.page_text(tab)`, `SuperScraper.solve_math_captcha(text)` |
| **H** | Shadow-DOM traversal to dismiss a closed-shadow-root cookie widget. | 1 | `audisense` | none — too specific, kept inline |
| **I** | Reveal hidden form sections (`classList.remove('hidden')`, `style.display=''`) + sync a sibling `<select>`. | 1 | `enformion` | none — kept inline |
| **J** | Scrolling (`scrollIntoView({block:'center'})`, `window.scrollTo`). Elsewhere the pydoll `.scroll_into_view()` method is used. | 2 | `media_net`, `peoplefinders` | prefer pydoll's `.scroll_into_view()` |
| **K** | `document.activeElement.blur()` to commit a react-select value. | 1 | `preqin` | folded into `js_set_value(..., blur=True)` |

## Rollout

Retrofitting the ~125 scrapers onto these helpers is opportunistic, not required
for correctness — do it when touching a file for another reason. Keep each
helper's `dispatch=` tuple matching whatever events the original site-specific
copy fired (some forms are tuned to a specific `input` vs `change` vs `blur`
order). `fill_autocomplete` (row C) is the highest-regression-risk retrofit and
should be verified against the live form.
