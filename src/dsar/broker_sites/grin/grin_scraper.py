# grin.co — SayMine Angular privacy portal (grin.privacy.saymine.io/Grin).
# Country is pre-set to "United States" by default.
# All interactions via JS click/fill — form renders visually black under pydoll
# but DOM is fully accessible. element.click() and click_using_js() raise
# ElementNotVisible; must use execute_script('.click()') for everything.
# Request types (getcopy, donotsell, delete) are radio buttons (single-select,
# all share name="") — one submission per right, ids are the plain readable
# strings above and stable.
# "Relationship with GRIN" (4 options) and the two acknowledgment questions
# are ALSO radios, but their real <input>s use backend-generated UUID ids
# (stable across loads, not readable strings) with NO `for`-linked <label> —
# the label instead wraps the input as a child with no for/id relationship.
# Selecting by id is a dead end (there's no readable id to hardcode); select
# by clicking the <label> whose visible text matches instead. "Other..." is
# used for relationship (closest generic fit for a consumer with no
# creator/brand relationship to GRIN); both acknowledgment radios are
# required regardless of which right was picked.
# reCAPTCHA v2 checkbox — manual solve required in live mode.
# Email verification sent after each submission.
# Exercises: Get a copy (Access), Do Not Sell, Delete (gated on REMOVE_INFORMATION).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://grin.privacy.saymine.io/Grin"

_FILL_JS = """
(function(wrapperId, value) {
    var wrapper = document.getElementById(wrapperId);
    if (!wrapper) return 'not found: ' + wrapperId;
    var inp = (wrapper.tagName === 'INPUT' || wrapper.tagName === 'TEXTAREA')
        ? wrapper : wrapper.querySelector('input, textarea');
    if (!inp) return 'no input in ' + wrapperId;
    var proto = inp.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype
                                           : window.HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(inp, value);
    inp.dispatchEvent(new Event('input', {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
    return 'ok';
})('%s', '%s');
"""

RIGHTS = [
    ("getcopy", "Get a copy of my data (Access)"),
    ("donotsell", "Do Not Sell my data"),
]
DELETE_RIGHT = ("delete", "Delete my data")


async def _js(tab, script):
    r = await tab.execute_script(script)
    if isinstance(r, dict):
        return r.get('result', {}).get('result', {}).get('value', '')
    return str(r)


async def _fill(tab, el_id, value):
    js = _FILL_JS % (el_id, value.replace("'", "\\'"))
    return await _js(tab, js)


async def _click(tab, el_id):
    return await _js(tab, f"""
        var el = document.getElementById('{el_id}');
        if (!el) return 'not found: {el_id}';
        el.click();
        return 'clicked';
    """)


async def _click_by_label_text(tab, text):
    # The relationship/acknowledgment radios use backend-generated UUID ids
    # (stable per question, but not the readable ids like "Customer-3" they
    # might resemble) — their real <input> is wrapped inside a <label> with
    # no `for` attribute, so match by the label's visible text and click the
    # label itself (native wrapping semantics propagate the click to the
    # input) rather than guessing an id.
    escaped = text.replace("'", "\\'")
    return await _js(tab, f"""
        var labels = Array.from(document.querySelectorAll('label'));
        var label = labels.find(function(l) {{ return l.innerText.trim() === '{escaped}'; }});
        if (!label) return 'label not found: {escaped}';
        label.click();
        return 'clicked';
    """)


async def _fill_form(tab, super_scraper, right_id):
    """Fill the form for one right type and return True if ready to submit."""
    # Request type radio (single-select)
    r = await _click(tab, right_id)
    if "not found" in r:
        print(f"{super_scraper.OOPS} {right_id} not found")
        return False
    await asyncio.sleep(0.3)

    # Personal info
    await _fill(tab, "fname-field", SuperScraper.FIRST_NAME)
    await _fill(tab, "lname-field", SuperScraper.LAST_NAME)
    await _fill(tab, "email-field", SuperScraper.EMAIL)

    # Relationship with GRIN: "Other..." (closest generic fit — no option
    # here matches a plain consumer with no creator/brand relationship)
    await _click_by_label_text(tab, "Other...")

    # Acknowledgment radios (both required regardless of which right was picked)
    await _click_by_label_text(
        tab,
        "Yes, the information provided is true and I am aware of the consequences of deleting data.",
    )
    await _click_by_label_text(
        tab, "Please confirm your acknowledgment of this before submitting your request."
    )

    time.sleep(0.5)
    return True


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right_id, right_label in rights:
            await tab.go_to(URL)
            await asyncio.sleep(12)

            if not await _fill_form(tab, super_scraper, right_id):
                continue

            if SuperScraper.DRY_RUN:
                await asyncio.sleep(1)
                await SuperScraper.screenshot(tab, f"resources/screenshots/grin_dry_run_{right_id}.png")
                print(
                    f"DRY RUN: would submit grin '{right_label}' for "
                    f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
                )
                continue

            print(
                f"\n'{right_label}' form filled. Solve the reCAPTCHA, then click Submit. "
                "Press Enter after the confirmation page loads..."
            )
            input()

            src = await tab.page_source
            if any(w in src.lower() for w in ("thank", "success", "received", "submitted", "confirmation", "request")):
                print(f"Submitted '{right_label}' DSAR for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            else:
                print(f"{super_scraper.OOPS} Confirmation unclear for '{right_label}' — verify in browser")


asyncio.run(main())
