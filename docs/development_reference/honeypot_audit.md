# Honeypot fields — audit & handling rule

15 scrapers mention a honeypot. This is an audit of what each one does and the
one real trap to watch for.

## The rule

**Never trust a field's `name` / `id` / `placeholder` as a semantic guarantee**,
especially on a form built with an anti-bot framework (Webflow, Gravity Forms,
Contact Form 7, custom). Decide whether a field is real by its **computed
layout**, not its label:

- `getBoundingClientRect().height === 0`, `display:none`, `visibility:hidden`,
  `offsetParent === null`, a 1×1px box, `position:absolute` off-screen, or a
  class like `hide-this-scale` ⇒ it is a spam trap. Leave it **empty**.
- Nonzero size + `visibility:visible` under the visible label ⇒ it is the field a
  real user fills, regardless of what its attributes are named.

`SuperScraper.js_eval(el, "return this.getBoundingClientRect().height")` (or
`getComputedStyle`) is the check.

## The real trap

- **`leadloft`** — the Webflow form has two email inputs: `id="Email"` (class
  `hide-this-scale`, `height:0` — the **trap**) and `id="HoneyPot"` (renders
  normally under the visible "Email Address *" label — the **real** field).
  Filling `#Email` raises `ElementNotVisible`. The "obviously named" field is the
  wrong one here. Its real submit button also uses an auto-generated
  `w-node-...` id while an unrelated newsletter form has `id="submit"` — scope
  the submit lookup to the target `<form>`'s id.

## Everything else — benign

All other mentions are a scraper **correctly leaving a trap field blank** and
saying so in a comment. No action needed; listed for completeness:

| Scraper | Trap field | Note |
|---|---|---|
| `affinityanswers` | `input_13` | left empty |
| `gostrata` | `input_5_19` ("URL") | left blank |
| `homeownersmarketingservices` | `form_fields[privtrue]` (`display:none`) | left blank |
| `ididata` | `hp*`-prefixed selects + `hplegalAgree` checkbox | left empty/unchecked |
| `issgovernance` | `trap` | left untouched |
| `jmr_media` | `id="website"` | not touched |
| `kochava` | (unnamed) | left empty |
| `listservicedirect` | field whose label says "type YES" | honeypot despite the name — left blank |
| `lsmapps` | generic-looking label | left blank |
| `m1data` | field with `getBoundingClientRect().height === 0` | detected + skipped |
| `media_net` | `website` | left blank |
| `outlogic` | `input_2_3` ("Name", `height:0`, `autocomplete="new-password"`) | honeypot despite its label — left blank |
| `pacificeast` | documented built-in honeypot | left BLANK |
| `rayinsights` | named text input | left blank |
