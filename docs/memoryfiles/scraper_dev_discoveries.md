# Scraper Development Discoveries

Running log of non-obvious things learned while building DSAR scrapers for the sites merged from `new_sites.txt` into `README.md`. Read this before starting a new scraper — it'll save re-discovering the same traps.

## Headless mode for local development

Use headless Chrome while developing/testing a scraper, even outside CI:

```python
options.add_argument("--headless=new")
```

- **Required** in any environment without a display (CI runners, remote sandboxes, agent/cloud dev environments) — `pydoll`'s default headed launch raises `FailedToStartBrowser` with no `DISPLAY` set.
- **Useful** even on a machine with a display: it avoids a visible Chrome window popping up on every test iteration during rapid dev-loop testing.
- **Do NOT commit it.** Every shipped scraper in `src/dsar/broker_sites/` runs headed by default. This is intentional: several forms need a visible browser so the user can manually solve a CAPTCHA or eyeball a confirmation page during a live (non-`DRY_RUN`) run. Add the flag temporarily while iterating, then remove it before finalizing the file. A quick way to do this safely:

  ```bash
  # add temporarily
  sed -i 's/options.add_argument("--no-sandbox")/options.add_argument("--no-sandbox")\n    options.add_argument("--headless=new")  # TEMP-FOR-TESTING/' path/to/scraper.py

  # remove before finalizing
  sed -i '/options.add_argument("--headless=new")  # TEMP-FOR-TESTING/d' path/to/scraper.py
  ```

## dotenv breaks in scratch/inspection scripts

`dotenv.load_dotenv()` with no arguments walks up from the *calling script's own file location* to find `.env` — not from `cwd`. A one-off inspection script saved outside the project tree (e.g. a scratch/tmp directory) will silently fail to load `.env` (`load_dotenv()` returns `False`, every `os.getenv()` comes back `None`), and pydoll then dies with a confusing `InvalidBrowserPath` because `CHROMIUM_LOCATION` was never set.

Fix: pass the explicit path in any script that lives outside the repo:

```python
dotenv.load_dotenv("/absolute/path/to/broker-poker/.env")
```

(This does not affect `src/dsar/super_scraper.py` itself or real scrapers under `src/`, since those live inside the project tree.)

## Screenshot verification: scroll position lies

`tab.take_screenshot()` without `beyond_viewport=True` only captures whatever is currently in the viewport — which is wherever the last-typed-into field scrolled to, not necessarily the field you want to check. This produced two false "the field is empty!" scares:

- **audisense.com**: the screenshot after filling MAID showed an empty "State"/"Zip" pair right above it — that was the *Work Address* section (never filled, correctly), not the *Home Address* section (filled correctly, just scrolled off-screen).
- **inboundinsight.com** (Trust Superset): a mid-loop screenshot appeared to show the wrong Request Type selected — actually just an artifact of which iteration's screenshot was being viewed, not a real state leak.

Before concluding a field didn't fill, either:

```python
await tab.take_screenshot(path="...png", beyond_viewport=True)
```

or scroll/verify the specific field's value directly via `execute_script`.

## click()-then-type can silently fail on some pages — fall back to a JS setter

On issgovernance.com, `input_field.click()` followed by `tab.keyboard.type_text(...)` (the `SuperScraper.input_text_field` pattern, and equivalently `element.type_text()`) left `first_name`/`last_name` empty every time — `document.activeElement` stayed `BODY` after the click, meaning focus never actually landed on the field, even though the identical click-then-type approach worked fine on the neighboring `email_address` field on the *same* form. No exception is raised either way, so this fails silently — the only tell is an empty field in the validation screenshot.

When click-based typing doesn't stick on a specific field (but works on others nearby), don't fight it — set the value directly via the input's native setter and dispatch the events the framework listens for:

```python
def _js_set(field_id, value):
    return (
        f"var el=document.getElementById('{field_id}');"
        f"var proto = Object.getPrototypeOf(el);"
        f"var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
        f"setter.call(el, {value!r});"
        f"el.dispatchEvent(new Event('input', {{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change', {{bubbles:true}}));"
        f"return el.value;"  # top-level return — no wrapping IIFE, see next section
    )

await tab.execute_script(_js_set("first_name", SuperScraper.FIRST_NAME))
```

This is the same native-setter technique `lightcast.io`'s existing scraper already uses for Angular's `ngModel` — it's a general-purpose fallback whenever click-based interaction is unreliable, not just an Angular-specific fix.

## `tab.execute_script()` needs a top-level `return`, not a wrapped IIFE

Wrapping a script as `(function(){ ...; return x; })();` makes the *statement* execute but discards its value — `execute_script()` only captures a value if the script's own top level has a `return`. Writing the same logic as flat statements ending in `return x;` (no wrapping function) gets the value back correctly. A script that mysteriously returns `{'type': 'undefined'}` despite no thrown error is usually this, not a real failure — check the wrapping before assuming the underlying DOM operation didn't work.

## `tab.find(id=...)` breaks on ids containing a colon (e.g. React's `:rN:`)

React 18's `useId()` produces ids like `:r2:`, `:r3:`, etc. — valid HTML, but `pydoll`'s `find(id=...)` builds a raw CSS selector as `f'#{value}'` with no escaping beyond double-quotes (see `find_elements_mixin.py`). `document.querySelector('#:r2:')` is invalid/misinterpreted CSS (a leading colon after `#` reads as a pseudo-class), so the lookup silently resolves to the wrong thing — `find()` still returns *something*, but the returned element fails `is_visible()` and any `.click()`/`.type_text()` on it raises `ElementNotVisible`, even though the real element is genuinely visible on the page (confirmed via `getBoundingClientRect`/`getComputedStyle` directly).

Any site built with a modern React form library (MUI, react-hook-form, etc. using default `useId`) can hit this. Work around it by matching on id via xpath instead, which takes a different code path unaffected by the bug:

```python
# Fails on React's `:rN:` ids:
field = await tab.find(id=":r2:", raise_exc=False)

# Works:
field = await tab.find(xpath="//*[@id=':r2:']", raise_exc=False)
```

Found on instantly.ai — every MUI-generated field on both of its forms needed this.

## Don't regex-scrape dumped HTML for `id="..."`

A naive regex like `id="([^"]*)"` over raw page HTML matches the *tail* of other attribute names too — `ot-auto-id="email"` and `data-describe-by-id="firstNameDesc"` both contain the literal substring `id="..."`. This produced wrong element IDs multiple times (alliantinsight.com, belardiwong.com, claritas.com all hit this — e.g. grabbing `"email"` when the real input `id` was `"emailDSARElement"`).

Verify the real `id` with a targeted, anchored search instead:

```bash
grep -oE '<input[^>]*\bid="[^"]*"[^>]*>' file.html
```

or better, query the live DOM directly:

```python
await tab.execute_script("return document.querySelector('[name=email]').id")
```

## Google Forms: text inputs have no `aria-label`

On a Google Form, checkbox/radio inputs carry `aria-label` directly and can be targeted with `tab.find(**{"aria-label": "..."})`. Short-answer **text** inputs do not — they're wired up with `aria-labelledby` pointing at a separate heading element. Targeting them by `aria-label` finds nothing and silently leaves the field blank (no exception raised).

Use an xpath scoped to the question's `role="listitem"` container instead:

```python
xpath = f"//div[@role='listitem'][.//span[contains(text(),'{question_title}')]]//input"
```

## HTML5 `<input type="date">` silently rejects non-ISO values

Setting `element.value = "01/01/1900"` via JS on a native `<input type="date">` is a silent no-op — the browser only accepts `YYYY-MM-DD`. `.env`'s `DATE_OF_BIRTH` is stored as `DD/MM/YYYY` (per `.env.example`'s comment), so any site using a real date input needs an explicit conversion before setting:

```python
day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
iso_dob = f"{year}-{month}-{day}"
```

Found on anchorcomputer.com. `enformion.com`'s existing scraper sets `DATE_OF_BIRTH` directly onto a date input without this conversion — likely has the same latent bug, not yet verified/fixed.

## Shadow-DOM cookie-consent widgets are invisible to `tab.find()`

Some cookie-consent implementations (e.g. "WP Consent Wall" on audisense.com) render inside a closed/open shadow root attached to a container div. Normal DOM queries and `pydoll`'s `.find()` can't see inside it. Detect and dismiss via a direct script:

```python
await tab.execute_script(
    "var host = document.getElementById('wpconsent-container'); "
    "if(host && host.shadowRoot){ "
    "  var btns = Array.from(host.shadowRoot.querySelectorAll('button')); "
    "  var b = btns.find(x=>x.textContent.trim().toLowerCase()==='accept all'); "
    "  if(b) b.click(); "
    "}"
)
```

If a form seems to silently fail to fill and a cookie banner was visible in an earlier screenshot, check for a shadow root before assuming anything else is wrong:

```python
await tab.execute_script(
    "var out=[]; document.querySelectorAll('*').forEach(e=>{ if(e.shadowRoot){ out.push(e.tagName+'#'+e.id); } }); return JSON.stringify(out);"
)
```

## Trust Superset platform quirk (shared across multiple brokers)

`dsr.trustsuperset.com` (used by brooksim.com, datadelivers.com, inboundinsight.com, and likely more not yet built) presents the same 7-option Request Type dropdown on every deployment (only `orgId` differs). Selecting **"Right to Rectification"** specifically reveals an additional required textarea (`name="rectification_info"`) that none of the other 6 rights trigger. Easy to miss because `DRY_RUN` never surfaces the resulting validation error — the field just stays required-and-empty until you actually look.

## Rapid repeated testing can trip third-party bot detection

TrustArc (`submit-irm.trustarc.com`, ariza.com) and `app.termly.io` (atom.com) both went from rendering normally to showing a Cloudflare/PerimeterX "confirm you're human" full-page interstitial after roughly 5-8 automated requests to the same URL within a short window during development. The interstitial replaces the entire page — there's no form left to interact with once it appears, and it did not clear up on retry within the same session.

Implication: don't hammer the same third-party DSAR vendor's URL repeatedly while exploring a new site's structure. Where possible, batch your exploration into fewer page loads (e.g. read the full rendered HTML once and grep it locally, rather than reloading the page for every follow-up question).

## CAPTCHA handling policy

A visible CAPTCHA/reCAPTCHA/Turnstile widget on an otherwise-interactable form is **never** a reason to stop early — fill every other field and stop only at the CAPTCHA/submit step, leaving that for a manual solve in live (non-`DRY_RUN`) mode. Mark the site `[x]` complete in the README with a `**CAPTCHA solution required**` note.

Only leave a site `[ ]` unchecked when the CAPTCHA/bot-check blocks access to the page itself — i.e. the interstitial *replaces* the form entirely (see the TrustArc/Termly bot-wall case above), rather than merely sitting alongside a fillable form.

When any other kind of blocker comes up (ambiguous conditional flow, wrong/dead-end URL, mandatory ID upload, anti-automation attestation, etc.), write it down clearly in the README and move to the next site rather than sinking more time into a workaround. A human PR review is the real checkpoint, not a perfect first pass.

## `SuperScraper.REMOVE_INFORMATION` / `DRY_RUN` used to be broken (fixed)

`os.getenv("REMOVE_INFORMATION")` returns the literal string `"False"` when `.env` has `REMOVE_INFORMATION=False` — and any non-empty string is truthy in Python. Every scraper written as `if SuperScraper.REMOVE_INFORMATION:` would attempt the deletion request regardless of the actual `.env` value. Fixed in `src/dsar/super_scraper.py` by parsing both flags into real booleans at the base-class level. A few scrapers (grin, lightcast, quantcast, spycloud) had already worked around this locally with their own `_is_remove_information()` helper — those were updated to use the base-class value directly instead of re-deriving it (their old helper would otherwise now always return `False`, since it checked `isinstance(v, str)` and `v` is a real bool post-fix).

If you ever see a new `_is_remove_information()`-style workaround being (re-)introduced, that's a sign someone didn't realize the base class already handles this correctly now — just use `SuperScraper.REMOVE_INFORMATION` directly.

## Docs vs. actual repo convention

- **Screenshots**: AGENTS.md / `docs/scraper_methodology.md`-adjacent docs reference a `validation/` directory. Actual convention across all 130+ shipped scrapers is `resources/screenshots/`. Use `resources/screenshots/`.
- **Blacklist/memory files**: `docs/blacklist_management.md` describes a `src/dsar/blacklist.json` + `src/dsar/memory/*.json` system in detail. In practice, neither has ever been created by any shipped scraper. Known-unmappable fields and quirks are instead documented inline as a `Note:` in the scraper's own file-header comment and in the corresponding README entry. Follow that convention rather than building the documented-but-unused JSON system, unless explicitly asked to.

## Recorded URLs are sometimes stale or simply wrong

`new_sites.txt`'s DSAR list was hand-researched and isn't always accurate. Examples hit so far:

- **adstradata.com**: the on-file URL loaded Adstra's "Authorized Agent Portal" — a dead end with no fields for a consumer submitting their own request. The real self-service form was found via the "Do Not Sell My Personal Information" link in the site's own privacy-policy footer.
- **audisense.com**: labeled that way in the tracking doc, but the real working domain is `audiense.com` (no "s") — the bare `audisense.com` domain refuses connections entirely.
- **adara.com**: the company has been folded into sojern.com; its own `/privacy/opt-out-data` page just embeds `privacy.sojern.com` in an iframe — navigate to the iframe URL directly rather than the outer page.

Always verify a recorded URL actually renders a self-service consumer form (not a redirect, an agent-only portal, or a dead domain) before building a scraper against it.

## Termly DSAR forms (app.termly.io/dsar/<uuid>) — another generic third-party platform

Like OneTrust/Trust Superset/Osano, Termly is a common white-label DSAR vendor: the customer's own privacy page (e.g. 01advertising.com's `/legal/dsar/`) is often just a static landing page with a "Submit a Privacy Request" link out to `app.termly.io/dsar/<customer-uuid>`, prefilled with a read-only "Website" field naming the customer. Field names observed are the vendor's own and likely stable across every Termly customer: `name`, `email`, `identity_type` (radio: personal/agent), a single `role="combobox"` react-select for the applicable law (CCPA/CPA/CTDPA/UCPA/VCDPA/OTHER), then a single-select `action` radio group revealed only after picking a law (`request_to_know`, `request_to_delete`, `request_to_opt_out`, `request_to_opt_in`, `access_personal_info`, `fix_inaccurate_info`, `receive_a_copy_of_info`, `opt_out_cross_context_advertising`, `limit_sensitive_personal_info`, `specify_comment`), a free-text `detail.content` textarea, and three `__doNotSubmit__.*`-prefixed attestation checkboxes that gate submission regardless of which action was picked. If another site's DSAR link resolves to `app.termly.io/dsar/...`, this whole field map should transfer directly.

`app.termly.io` sits behind a Cloudflare Turnstile interstitial that can replace the *entire* form (not just the submit step) — and testing this domain a few times in a short window during exploration was enough to trigger it consistently on every subsequent load, even in a fresh browser context. Confirmed the underlying form/field structure from an earlier clean load before the gate kicked in, and shipped the scraper against that confirmed structure rather than treating the now-persistent interstitial as proof the site is unreachable. Be extra conservative about repeat-loading `app.termly.io` while exploring; if it's already gated by the time you get there, the field map above can still be trusted.

## Driving a form embedded in an `<iframe>`, when the iframe's own URL frame-busts

Some sites (acxiom.com) embed their real DSAR form as an `<iframe src="https://other-domain/...">` on an otherwise-static privacy page. The instinct is to just `tab.go_to()` the iframe's `src` directly — but some of these frames contain an anti-clickjacking script that redirects any top-level (non-framed) load of that URL straight back to the outer page. Confirm this by checking `window.location.href` after navigating — if it silently lands back on the parent page's URL, that's what's happening, and the frame must be driven in place instead.

pydoll supports this: find the `<iframe>` tag itself as a `WebElement` (e.g. `iframe = await tab.find(id="frameresize")`), and then call `.find(...)` **on that iframe element** — pydoll's `IFrameContextResolver` correctly resolves into the frame's own document, so `iframe.find(id="SomeFieldInsideTheFrame")` works exactly like `tab.find()` would if the frame's page had loaded standalone.

The one trap: `iframe.execute_script(...)` (called on the iframe element itself) does **not** run inside the frame — `this` is bound to the `<iframe>` tag as it exists in the *parent* document, and any `document.` reference inside the script string still resolves to the parent's `document`, so `document.getElementById(...)` returns `null` for anything that only exists inside the frame. The fix: `.find()` the target element from inside the iframe first (e.g. `select_el = await iframe.find(id="State")`), then call `.execute_script(...)` **on that element**, not on the iframe. A script run against an element that itself lives inside the frame's execution context correctly sees the frame's own `document`.

## JS-masked inputs (phone number formatters, etc.) can silently corrupt `type_text()`

altisource.com's Gravity Forms phone field has a JS input mask (renders as `(___) ___-____` placeholders). Typing into it via `type_text()` — even one character at a time with a delay between each — left most of the field as blank underscores, with only the last few typed digits actually landing (e.g. typing all 10 digits of a phone number produced `(___) ___-1888`, discarding everything but the last 4). Slowing down the typing did not fix it. The mask library appears to reformat/reset the field faster than simulated keystrokes can keep up with, or misinterprets the rapid synthetic key events.

Fix: bypass keystroke simulation entirely — set the value via the native input-value property setter and dispatch `input`/`change`(/`blur`) events, exactly like the earlier click-then-type-focus-failure workaround:
```js
var proto = Object.getPrototypeOf(this);
var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
setter.call(this, '6514888888');
this.dispatchEvent(new Event('input', {bubbles:true}));
this.dispatchEvent(new Event('change', {bubbles:true}));
```
This let the mask library reformat the whole string correctly in one pass (`(651) 488-8888`). If a field renders with placeholder underscores/parens/dashes baked into its empty state, assume it's masked and reach for this approach before spending time debugging `type_text()` timing.

## `tab.find(id=...)` bug generalizes beyond colon-ids: any id starting with a digit breaks too

Previously documented: `tab.find(id=value)` builds an unescaped `#{value}` CSS selector, which breaks for ids containing a colon (React's `:r2:`-style ids). ariza.com's TrustArc IRM form surfaced the same root cause from a different angle — its field ids are literally UUIDs (`00000000-0000-0000-0000-000000001002fn`), which start with a digit. A CSS id selector can't start with an unescaped digit either, so `#00000000-...` is invalid, and the bug manifests differently here: instead of finding nothing, `find()` returns *something* — but `.is_visible()` on it is `False`, and calling `.type_text()`/`.click()` on it raises `ElementNotVisible`, even though the real field is plainly visible on screen (confirmed by re-finding the exact same id via `xpath=f"//*[@id='{value}']"`, which correctly reports it as visible).

Practical rule: don't reach for `tab.find(id=...)` at all when the id is machine-generated (UUID, React-style `:rN:`, or anything else that isn't a plain CSS-safe identifier) — use `tab.find(xpath=f"//*[@id='{value}']")` unconditionally for those. It's a strict upgrade with no downside for plain ids too.

## A field can silently self-clear ~750ms after being filled — some page JS is watching input/change events

bi2technologies.com's Contact Form 7 fields looked filled immediately after `type_text()`/a native-setter dispatch, but a fresh `document.querySelector(...).value` check a second later showed empty — reproduced even on a single field in total isolation (no other field touched). Narrowing it down: setting the value via the native setter **without dispatching any event at all** left the value intact indefinitely; dispatching `input` or `change` (either one) was what triggered some page-level JS to clear it roughly 750ms later. Whatever is doing the clearing is watching those events specifically, not polling the DOM generally.

Fix: set the value via the native setter and dispatch **no events**. A plain (non-React/non-Vue) HTML form reads `.value` directly off the input at submit time — it doesn't need a synthetic event to "notice" the value, so skipping the dispatch entirely is safe for real submission and avoids the self-clearing behavior. If a field on a plain server-rendered form seems to revert to empty a moment after being set — even with no other field interaction in between — suspect this pattern and try the no-event variant before assuming the selector or timing is wrong.

## Ketch Preference Center can geo-fence the DSAR tab itself out of the DOM entirely

datadecisionsgroup.com uses a Ketch-branded ("ketch-...") Preference Center widget whose own on-page copy says the "Data Subject Rights" tab "may not be visible to visitors outside of the United States." This isn't just a disabled/greyed-out tab — the tab and its underlying form are absent from the DOM entirely; only a single "Welcome" tab renders (confirmed by counting actual tab-label elements, not just searching for the phrase "Data Subject Rights," which only turns up in the instructional paragraph text). Ketch determines "US" via the visitor's IP geolocation server-side, so there's no client-side toggle or query param to force it — if this environment's outbound IP isn't classified as US, the real form never ships to the page at all. Distinct from a captcha or bot-wall: there's nothing to solve or wait out, and nothing productive to fill in until Ketch's own geolocation decides otherwise.

## A "bot-check interstitial" during dev testing isn't necessarily a permanent block — retry later

ariza.com's TrustArc-hosted form threw a PerimeterX-style "confirm you are human" wall after repeated rapid requests during one development session (same family of issue as the Termly Cloudflare Turnstile case above, and previously seen on oracle.com/liveramp.com). Rather than concluding the site was permanently walled and leaving it unchecked, it was retried in a later, separate session — the interstitial was gone, the form loaded cleanly, and the scraper (once fixed for the id-selector bug above) completed and screenshot-verified without issue. If a site was previously documented in the README as blocked/bot-walled due to a bot-check triggered by dev-time testing traffic (as opposed to a hard WAF block with no underlying form, e.g. absolutepeoplesearch.com), it's worth a fresh, low-frequency retry before permanently writing it off.

## A radio/checkbox `<label>` with no `for` attribute can still wrap its `<input>` as a child — click the label by text, not the input by id

grin.co's SayMine Angular form has some radio questions ("What's your relationship with GRIN?", two acknowledgment questions) whose real `<input>` ids are backend-generated UUIDs (e.g. `ca82dd39-617e-429c-be69-0a2bfcb1220f-3`) — stable across page loads, but not the kind of readable id you'd guess or hardcode from a first pass. A prior attempt at this scraper hardcoded plausible-looking-but-wrong ids (`Customer-3`, `custom-question-1-0`) that simply didn't exist in the DOM; `document.getElementById(...)` returned null and the fields were silently never touched (confirmed by screenshot: the radios were still empty even though the script printed no errors, because `_click()`'s "not found" check wasn't being surfaced/checked for these calls).

Fix: don't try to find a stable readable id for these. Instead find the `<label>` whose `innerText.trim()` matches the option's visible text and call `.click()` on the *label* — even though it has no `for` attribute (so `document.querySelector('label[for=...]')` returns nothing), the label still wraps the `<input>` as a direct child, and clicking a `<label>` that contains its target input propagates the click via native browser semantics exactly like a `for`-linked label would. Verified via `.checked` on the wrapped input after the label click. This is a cheap, generalizable check when a checkbox/radio's real id isn't a stable, guessable string: dump `outerHTML` of the element or its parent label first — if the input is a child of a `<label>`, click the label by text instead of hunting for an id.

## MUI `<li role="option">` text can be wrapped in a child `<p>` — `text()` misses it, `normalize-space()` doesn't

On hightouch.com's DataGrail/MUI-based dropdown, some `<li role="option">` elements render their label as a direct text node (`<li>Other</li>`) while others (same page, different `<Select>`) wrap it in a child `<p>` (`<li><p>Opt Out</p></li>`). An xpath like `//li[normalize-space(text())='Opt Out']` only inspects direct text-node children, so it silently matched zero elements for the `<p>`-wrapped ones even though `tab.find(text=...)`-style substring search or a `querySelectorAll` scan would find them fine. Default to `normalize-space()` (with no argument — it operates on the node's full string-value, i.e. all descendant text) instead of `normalize-space(text())` for any option/label xpath match; it's a strict superset with no downside, so there's no reason to reach for the `text()`-scoped version at all going forward.

Also: a MUI `<Select>` dropdown menu (rendered via a portal) does not close on a plain `document.body.click()` after clicking an option — the click event doesn't reach MUI's own outside-click listener when dispatched synthetically. `tab.keyboard.press(Key.ESCAPE)` after the option click reliably dismisses it (the selection was already committed by the click) if a clean screenshot without the menu overlay is needed.

## DataGrail Privacy Request Center — now confirmed on 5+ sites, and the pattern for its randomly-named extra fields

Confirmed the same DataGrail-hosted "Privacy Request Center" template (see prior entry on bridg.com/clearbit.com/crunchbase.com) on hightouch.com, hubspot.com, and inmarket.com too — it's evidently a common off-the-shelf privacy-ops product, not a one-off. Stable across every instance: `first_name`/`last_name`/`email_address` field names, `mui-component-select-data_subject_relationship` relationship select, `privacy-request-center-region-picker` state autocomplete, "Review Request" → "Submit Request" two-step submit. Cards offered vary per customer (some split Opt-Out and Delete into separate cards, some combine them with a sub-select, some add site-specific extra fields like a MAID input) but the base template is worth recognizing immediately and reusing the crunchbase.com scraper's structure as a starting point.

Site-specific extra fields on these forms (a "Deletion or Opt Out" sub-select, a MAID field, etc.) get a random per-site UUID as both their `name` and their `aria-labelledby`/id — there's no stable string to hardcode. Two positional tricks that work well instead:
- For a same-page MUI `<Select>` that isn't the relationship one: `//div[starts-with(@aria-labelledby,'mui-component-select-') and not(contains(@aria-labelledby,'data_subject_relationship'))]` — there's normally only one other such select per card.
- For a plain `<input>` whose `name` is the raw UUID itself (36 chars, `8-4-4-4-12` with dashes): `//input[@name and string-length(@name)=36]` picks it out without needing to know the value ahead of time.

Both are generalizable wherever a form vendor emits `crypto.randomUUID()`-style names for custom/dynamic fields instead of a stable schema name.

## A field literally named "HoneyPot" can be the REAL field — check computed layout, not the name

leadloft.com's Webflow-built privacy-request form has two email inputs sharing the same visible label area: `id="Email"` (the semantically obvious one) and `id="HoneyPot"` (the name every bot-avoidance instinct says to skip). Checking actual rendered layout inverted the assumption: `#Email` carries class `hide-this-scale` and has `getBoundingClientRect().height === 0` — it's the spam trap, invisible and never meant to be filled. `#HoneyPot` renders normally (`height: 48`, under the visible "Email Address *" label) and is the field a real user actually types into. Filling `#Email` instead raised `ElementNotVisible` immediately, which is what surfaced the mismatch.

General rule reinforced here: never trust a field's `name`/`id`/`placeholder` as a semantic guarantee, especially on a form built with an anti-bot framework (Webflow forms with a "HoneyPot" field are common). When a field can't be interacted with, or when a form has more inputs than visible labels, check `getBoundingClientRect()` + `getComputedStyle()` for every candidate before deciding which one is real — the one with nonzero size and `visibility:visible` is the one to fill, regardless of what its attributes claim to be.

Separately on the same site: the submit `<input>` for the actual form used an auto-generated Webflow node id (`w-node-...`) while an unrelated newsletter-signup form elsewhere on the page had the readable `id="submit"` — another case where the "obviously right" id belonged to the wrong element. Scope the search to the target `<form>`'s own id (`//form[@id='...']//input[@type='submit']`) rather than picking the first plausible-looking id on the page.

## privacyrequest.net — another generic third-party DSAR platform, iframe-embedded

media.net embeds its "Privacy Rights Requests" section as `<iframe id="pr-iframe" src="https://privacyrequest.net/privacy-request/?flavor=<per-customer-hash>">` — like Termly/DataGrail, this is a white-label vendor likely reused by other sites too, worth recognizing on sight. The iframe doesn't frame-bust, so navigate to its `src` directly. It's a wizard: country → state (both custom autocomplete comboboxes — click the input, `keyboard.type_text()` the value, then click the matching `<li>` by exact text) → click "Next" → a request form renders (relationship radio "I am a", single-select "request type" radio, name/email, a `name="website"` honeypot to leave blank, free-text details, Submit).

The trap: the page ships EVERY country/state/customer-flavor's field set simultaneously in the DOM, all sharing the same handful of `name`/`id` values across different flavors (e.g. `id="request-to-access"` exists multiple times with different label text in different blocks: "Request to Access" in one flavor's set, contributing to a totally different set in another). Only one flavor's block is actually shown at a time, gated by the wizard's country/state answers, but `document.getElementById()` / a plain `tab.find(id=...)` will grab whichever matching id comes first in DOM order — not necessarily the visible one. Don't target these radios by id. After completing the wizard, read the page's own rendered visible text to get the exact label strings for the active flavor, then match radios by their associated `<label>` text (`//label[normalize-space()='...']` or by walking to the label's `for` target) rather than by id.

Also flaky under rapid repeated testing during exploration (the wizard's "Next" button intermittently failed to appear even after long waits) — treat this the same as the ariza.com/liveramp.com transient-block family: don't hammer it, and a clean single run is more informative than several rapid retries.

## OneTrust dsarwebform Country/State fields can be autocomplete comboboxes that steal the next field's focus

mediawallah.com's OneTrust dsarwebform iframe has `countryDSARElement`/`stateDSARElement` fields that look like plain text inputs but are actually autocomplete comboboxes backed by a `role="option"` dropdown. Calling `type_text("United States")` then moving straight to the State field (typing `SuperScraper.STATE` into it) produced a corrupted result: the Country field ended up containing `"United States Minor Outlying IslandsMinnesota"` — the widget auto-completed to the wrong (alphabetically-adjacent) full match on blur, and the second `type_text()` call's keystrokes landed in the still-focused Country field instead of the State field. Screenshot review was what caught it — the bug was silent, no exception raised.

Fix: for each field, click it, type the target text, wait ~1s for the dropdown to populate, then find and click the `role="option"` element whose text exactly matches (`//*[@role='option' and normalize-space()='United States']`) rather than trusting the typed text to land correctly on its own. This is the same family of issue as the react-select comboboxes on ariza.com/liveramp.com and media.net's privacyrequest.net country/state fields — any field that renders a dropdown-with-options after typing should be treated as "click the option," never "trust the typed text," even when the field visually looks like a plain `<input>`.

## `tab.find(text=...)` is a substring match, not exact — a short target string can silently grab unrelated prose

merkle.com's OneTrust webform has a single-option "Which dentsu brands relate to your request" button labeled "Merkle". `tab.find(text="Merkle", raise_exc=False)` didn't error and didn't raise — it just silently resolved to a `<p>` intro paragraph containing the substring "...personal information in **Merkle**'s US data products", clicked that (a no-op, since it's plain text), and left the real button unselected. No exception surfaced this; only a screenshot review caught the button never lighting up.

This is a sharp edge specifically when the target string is short, generic, or likely to appear in surrounding prose (a company name, a single common word) — long, specific button labels ("Do Not Share or Sell My Information", "Yes, myself") are safe in practice because they're unlikely to appear verbatim elsewhere on the page, but don't assume any `text=` match is exact. When a `text=`-matched click doesn't visibly toggle/select as expected, checking what `tab.find(text=...)` actually resolved to (`el.execute_script("return this.outerHTML")`) is a fast way to confirm whether it grabbed the right element before hunting for other causes. Prefer a structural xpath (`//*[@role='option' and @aria-label='Merkle']`, or matching a stable attribute) over a bare short `text=` match whenever the target string could plausibly appear elsewhere on the page.

## Monday.com forms (forms.monday.com): Downshift comboboxes need their `triggerWrapper` ancestor clicked, not the input itself

perion.com's Monday.com-hosted form uses Downshift for its dropdown fields. The real `<input role="combobox">` reports fully visible CSS properties (`display:block`, nonzero size, `visibility:visible`) via `getBoundingClientRect()`/`getComputedStyle()`, yet `pydoll`'s own `.click()` and `.click_using_js()` both raise `ElementNotVisible` on it, and manually dispatching `mousedown`/`mouseup`/`click`/`focus` events or an `ArrowDown` keypress directly at the input does nothing — the option menu never opens (`aria-expanded` stays `false`). The fix: walk up from the input to its ancestor `div` with a class starting `triggerWrapper_` (`//input[@id='...']/ancestor::div[contains(@class,'triggerWrapper')]`) and click *that* instead — this opens the menu reliably. Once open, options are plain `[role="option"]` elements matchable by exact text.

Also on this same form: plain (non-combobox) text inputs silently dropped their first couple of keystrokes when `type_text()` was called right after `tab.find()` on a freshly-loaded page — "John Doe" landed as "n Doe", no error raised. An explicit `.click()` followed by a short `asyncio.sleep(~0.4)` before `type_text()` fixed it every time. If a filled value on a plain-looking text field comes back truncated/missing its leading characters with no exception thrown, suspect this same click-then-pause fix before looking elsewhere.

## DPOrganizer/DataGuard portals (portals.dporganizer.com): stable `data-test="portal-input-N"` beats the random per-instance field id

preqin.com's DSAR form is hosted at `portals.dporganizer.com/<uuid>` (a DPOrganizer/DataGuard-branded platform, new to this repo) and embedded on the marketing site via a non-frame-busting iframe — same "navigate to the iframe's `src` directly" pattern as media.net's privacyrequest.net and TrustArc forms elsewhere in this repo. Every field's own `id` is a random per-portal-instance UUID that won't transfer to a different DPOrganizer customer's form, but each field also carries a stable `data-test="portal-input-N"` attribute in a fixed order matching the form's visual field order (0, 1, 2, ... top to bottom) — use that instead of the id if this platform shows up again. One inconsistency to watch for: on the two react-select fields (indices 0/1 here), `data-test` sits on a wrapping `<div>` around the actual `<input>` (so target `//div[@data-test='portal-input-0']//input`), while on the plain text fields (indices 2+), `data-test` sits directly on the `<input>` itself (target `//input[@data-test='portal-input-2']` — no wrapping div). Using the wrong pattern for a given field silently resolves to nothing (`raise_exc=False` swallows it) rather than erroring, so always print an OOPS on a not-found field for these platforms rather than silently skipping — that's what caught this mismatch here (the Name/Email/Comments fields tested as unfilled in a screenshot with zero error output, until per-field OOPS prints were added and the fix became obvious).

This particular form's "Type of request" field is a genuinely multi-select react-select (Select all/Deselect all buttons, removable chips) — one combined submission covering every applicable right, not the one-submission-per-right pattern used by most sites in this repo. Options are `<div id="react-select-{N}-option-{i}">`, clickable by exact text match once the dropdown is open (click the field's input to open it).

## Securiti.ai / Formio forms (privacy-central.securiti.ai): component ids carry a random per-page-load suffix — never hardcode it

quinstreet.com's DSR form is hosted on Securiti.ai, built with the Formio form framework — a new platform for this repo. Formio component wrapper/label ids look stable at a glance (e.g. `eqtdwkp-esqnmev`) but the second segment is a session/render-instance suffix that changes on every fresh page load (`eqtdwkp-ebrr2rg` the next time) — an xpath or CSS selector built around one observed id will work once during exploration and then silently match nothing on the next real run (`raise_exc=False` swallows it with no error). Always match Formio fields by their stable `name` attribute instead (Formio consistently emits `name="data[<field_key>]"`, e.g. `data[certification]`, `data[first_name]` — these don't vary between loads), or by visible label/span text, never by the full component id.

Also worth noting for future Formio/Securiti forms: a visually single-looking question can be split across two separate radio groups with different `name`s purely for layout (quinstreet.com's state-of-residence picker renders as two side-by-side table columns, "I am a:" and "continued:", backed by `data[user_type][...]` and `data[i_am_a][...]` respectively) — functionally one combined choice from the user's perspective, so search across all such groups by rendered label text rather than assuming a single `name` covers every visible option.

## Multiple independent cascading fields can stack on the same OneTrust webform — verify the full chain, not just the first reveal

slashdotmedia.com's OneTrust portal had TWO separate cascading reveals in the same form, easy to catch only one of and ship a scraper that silently skips a required field: (1) picking "Data Deletion" as the request type reveals a new required confirmation toggle ("By exercising your right to deletion, you will lose all account information. Do you wish to proceed?" → Yes/No) that doesn't exist in the DOM for any other request type; (2) completely independently, the State field doesn't exist in the DOM at all until Country is filled in — this one is unconditional (happens for every request type), not tied to which right was picked. Testing only the "happy path" first request type in a quick pass can miss both, since neither is visible until you're several steps into filling the form. Reinforces the existing cascading-field lesson (messagedigital.com/precisely.com) but the specific new wrinkle here: don't assume a form has only ONE cascade trigger — re-screenshot after every field is filled, all the way to the end, not just after the field you expect to reveal something.

## Cascading fields can DIVERGE per request type, not just accumulate — t-mobile.com

Most cascading OneTrust forms in this repo reveal the *same* extra fields regardless of which right was picked (or reveal fields unconditionally after some earlier field, e.g. slashdotmedia.com's Country→State). t-mobile.com's portal does something new: after selecting "Type of request," a common block of fields cascades in for every right (Relationship with T-Mobile, US States & Territories, a vt-autocomplete State of residence, Phone, Email) — but then a request-type-SPECIFIC block cascades on top: "Access personal data" additionally reveals a "Delivery method" toggle (no name/address fields at all), while "Delete personal data" instead reveals First/Last Name + Street address + City + Zip (no delivery-method field). Explored only the Access path initially and would have shipped a scraper with no way to fill Delete's name/address fields if the Delete path hadn't been separately screenshotted after selecting it. Lesson: when a form has multiple request-type options, re-screenshot the FULL cascade separately for each option — don't assume the second option's cascade is a subset/superset of the first's.

## `type_text()`'s click-based visibility check can flake on animated reveals — set `.value` via JS instead

usa-people-search.com's form fades/slides a field block into view after a preceding `<select>`'s change event fires. Even after polling `element.offsetParent !== null` via JS to confirm the DOM considers the field visible, pydoll's `type_text()` (which calls `.click()` first) intermittently raised `ElementNotVisible` — worked on some runs/fields, failed on others, with no code difference. The fix: skip `type_text()`/`.click()` entirely for these fields and set the value directly — `field.execute_script(f"this.value = {value!r}; this.dispatchEvent(new Event('input',{{bubbles:true}})); this.dispatchEvent(new Event('change',{{bubbles:true}}));")`. This sidesteps whatever race pydoll's click-visibility check has with an in-progress CSS transition. Reach for this pattern whenever a field sits inside a container that animates open (fade/slide), not just when a plain sleep-based wait already failed once — the flakiness can be intermittent enough that a single successful test run doesn't prove it's fixed.

## Drupal webform radios/checkboxes that silently ignore `.click()` — set `.checked` + dispatch both events via JS

verizon.com's Privacy Inquiry Form (a Drupal webform with custom-styled radio/checkbox inputs) accepted pydoll's plain `element.click()` without error, but the input's `.checked` property never actually flipped and none of the form's conditional show/hide logic fired — no OOPS printed, just a silently no-op click (worse than ElementNotVisible, since nothing indicates failure). Confirmed via `el.checked` read back as `False` after the click. Fix: `element.execute_script("this.checked = true; this.dispatchEvent(new Event('change', {bubbles:true})); this.dispatchEvent(new Event('click', {bubbles:true}));")` — Drupal's conditional-logic JS listens for these events, not the native click. When a radio/checkbox click "succeeds" (no exception) but a cascading section that should depend on it never appears, don't assume the cascade is simply absent — verify the input's actual `.checked` state via JS before concluding there's no conditional field to fill.

## HubSpot forms (`hbspt.forms.create()`) embedded via a src-less iframe are unreachable — genuine blocker, not a skill issue

unacast.com's DSAR forms are both HubSpot forms embedded the standard way: `hbspt.forms.create({portalId, formId})` injects an `<iframe class="hs-form-iframe">` with NO `src` attribute — HubSpot populates its content via an internal postMessage/API handshake, not by navigating the iframe to a URL. Confirmed via `document.getElementById(...).src` reading back empty even after a 10s wait. This breaks both of this repo's usual iframe-form techniques: `tab.find()` on the outer page can't see inside the iframe at all, and pydoll's `tab.get_frame(element)` explicitly requires a valid `src` and raises `InvalidIFrame` without one — there is no navigable URL to go to directly, unlike every other iframe-embedded form this repo has handled (OneTrust CDN, Osano, DPOrganizer, etc., which all set a real `src`). If a future site turns out to use `hbspt.forms.create` (check for that literal call, or a `class="hs-form-iframe"` element with an empty `src`), don't spend time hunting for a workaround — document it as unreachable and move on; no fix was found for this platform.

thomsonreuters.com pushed this further: THREE stacked cascades, and the third one diverges by request type even though the first divergence (full-identity-fields vs. name-only) suggested only two "buckets." Residency → State+WhoIsRequesting → "I am a (an)" → Select request type → [full name/address/DOB/SSN/phone fields for Access/DoNotSell/Delete, vs. just name/phone/email for Opt-Out-of-Marketing] → filling DOB reveals a THIRD cascade (a no-smartphone checkbox + a second, stricter-validated phone field) but ONLY on the Access path — Do Not Sell and Delete show the identical DOB field and never reveal it. Don't stop re-testing after finding one divergence; a cascade can be nested arbitrarily deep, and confirming it for two request types doesn't mean a third/fourth won't diverge again further down.

## Tally.so forms embedded via a real-`src` iframe ARE reachable with `tab.get_frame()` — and fields have no stable id

realsourcedata.com's opt-out form is a Tally.so embed (`<iframe src="https://tally.so/embed/...">`) — unlike HubSpot's src-less iframe (see above), Tally always sets a real, populated `src`, so pydoll's `tab.get_frame(iframe_element)` works immediately (it's deprecated in favor of "interact with iframe WebElements directly" per a runtime warning, but still functions and was the only thing tried that worked). The general rule this confirms: before writing off an iframe-embedded form as unreachable, always check whether the iframe's `src` is populated — a real `src` means `get_frame()` is worth trying; an empty one (HubSpot) means don't bother.

Once inside the frame, Tally's field ids are random UUIDs regenerated on every page load (e.g. `3cb88560-1c40-42a1-9994-6137bb7c50d2`) with no `name` or `placeholder` attribute to key off instead — unlike Formio's stable `name="data[field_key]"` (see Securiti.ai above). The only stable thing is DOM order: read the frame's visible label text (`document.body.innerText`, or the label elements if they're proper `<label>` tags) once during exploration to confirm field order, then in the scraper select all `input`/`textarea` elements of the expected types via `frame.find(tag_name="input", find_all=True)` and zip them positionally against a hardcoded value list in that same order — don't hardcode a specific UUID, it won't survive the next page load.

## UPDATE: src-less HubSpot iframes ARE reachable — call `.find()` on the iframe WebElement

The unacast.com entry above (and the README notes for venntel.com / marketforcecorp.com) concluded that a HubSpot form embedded as `<iframe class="hs-form-iframe">` with an empty `src` is unreachable. That is now out of date. `tab.find()` on the outer page and `tab.get_frame(iframe)` both still fail on a src-less HubSpot frame — but pydoll's newer "interact with the iframe WebElement directly" path works:

```python
iframe = await tab.find(class_name="hs-form-iframe", raise_exc=False)   # the <iframe> element in the PARENT doc
field  = await iframe.find(xpath="//textarea[@name='enter_advertising_id_']", raise_exc=False)  # resolves INTO the frame
await field.type_text(SuperScraper.ADVERTISING_ID)
```

Gotchas found on motrixi.com / withrealcustomers.com:
- Use `iframe.find(xpath=...)` (or `tag_name=`). `iframe.find(name=...)` built a bad selector and matched nothing; `iframe.find(..., find_all=True)` raised `TypeError("'NoneType' object can't be awaited")` — a pydoll bug. Find elements one at a time by xpath.
- `<select>` inside the frame: get the element via `iframe.find`, then `.execute_script("this.value=...; this.dispatchEvent(new Event('change',{bubbles:true}))")` on that element.
- Checking a request-type checkbox can cascade in a whole extra identity block (name/DOB/city + optional ID-upload fields) that wasn't in the DOM before — re-dump the frame's form HTML after ticking the boxes.

So: a src-less `hs-form-iframe` is worth a real attempt now. unacast.com / venntel.com / marketforcecorp.com are candidates for a re-try with this technique.

## OneTrust `privacyportal[-de].onetrust.com/webform` vt-autocomplete can DOUBLE a fully-typed value

On iqm.com's OneTrust webform (`privacyportal-de.onetrust.com/webform/...`), the Country/State autocomplete comboboxes type-ahead-complete the field AND keep the characters you typed, so `keyboard.type_text("United States")` ended up as `"United StatesUnited States"` in the field — regardless of whether the match was then committed by clicking the `role="option"` or by ArrowDown+Enter. Screenshot review was the only tell; no exception.

What worked: set the value via the native setter + `input` event so the option list still filters to the single match, commit it, then hard-correct the field if it still came out wrong:

```python
await field.execute_script(
    "var s=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(this),'value').set;"
    f"s.call(this,{value!r});"
    "this.dispatchEvent(new Event('input',{bubbles:true}));"
)
await asyncio.sleep(1.4)
opt = await tab.find(xpath=f"//*[@role='option' and normalize-space()={value!r}]", raise_exc=False)
if opt: await opt.click()
else:   await tab.keyboard.press(Key.ENTER)
current = await field.execute_script("return this.value")
# if `current` still != value: re-run the native-setter block + dispatch input/change/blur
```

Not every OneTrust build does this — yellowpages.com (CDN Angular `dsarwebform`), gumgum.com and idstrong.com's plain type + ArrowDown+Enter came out clean. It's specific to this newer `-de`/vt-autocomplete variant. Always screenshot-verify a combo value on these forms.

## OneTrust `requestTypesDSARElement` "Select request type(s)" is often SINGLE-select despite the "(s)"

idstrong.com, gumgum.com, iqm.com, synapsegroupinc.com, allantgroup.com all label the request-type group "Select request type(s)" but picking a second `role="option"` deselects the first (confirmed by screenshot — only ever one lit). Treat these as one-submission-per-right (reload the form per right, gate Delete on `REMOVE_INFORMATION`), the same as slashdotmedia.com. zetaglobal.com is the documented exception that is genuinely multi-select — so verify per form, don't assume either way.
