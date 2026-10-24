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
# Which request types run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   #getcopy / #donotsell / #delete   "Request type" radios (Get a copy / Do Not Sell / Delete)
#   #fname-field / #lname-field / #email-field   First name / Last name / Email
#   Label "Other..."          "Relationship with GRIN" radio (UUID ids -> clicked by label text)
#   Label "Yes, the information provided is true and I am aware of the consequences of
#         deleting data."     first required acknowledgment radio
#   Label "Please confirm your acknowledgment of this before submitting your request."
#                             second required acknowledgment radio
#   reCAPTCHA v2 checkbox, then the portal's Submit button (clicked manually)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://grin.privacy.saymine.io/Grin"

REQ_GET_COPY = "getcopy"      # "Get a copy of my data" request-type radio
REQ_DO_NOT_SELL = "donotsell"  # "Do Not Sell my data" request-type radio
REQ_DELETE = "delete"          # "Delete my data" request-type radio
FIRST_NAME_FIELD = "fname-field"
LAST_NAME_FIELD = "lname-field"
EMAIL_FIELD = "email-field"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: (REQ_GET_COPY, "Get a copy of my data (Access)"),
    Right.RIGHT_TO_OPT_OUT: (REQ_DO_NOT_SELL, "Do Not Sell my data"),
    Right.RIGHT_TO_DELETE: (REQ_DELETE, "Delete my data"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='fname-field']",
    "Last name": "//*[@id='lname-field']",
    "Email": "//*[@id='email-field']",
}


async def _fill(tab, el_id, value):
    el = await tab.find(id=el_id, raise_exc=False)
    if not el:
        return f"not found: {el_id}"
    await js_utils.js_set_value(el, value)
    return "ok"


async def _click(tab, el_id):
    el = await tab.find(id=el_id, raise_exc=False)
    if not el:
        return f"not found: {el_id}"
    await js_utils.js_click(el)
    return "clicked"


async def _click_by_label_text(tab, text):
    # The relationship/acknowledgment radios use backend-generated UUID ids
    # (stable per question, but not the readable ids like "Customer-3" they
    # might resemble) — their real <input> is wrapped inside a <label> with
    # no `for` attribute, so match by the label's visible text and click the
    # label itself (native wrapping semantics propagate the click to the
    # input) rather than guessing an id.
    escaped = text.replace("'", "\\'")
    return await js_utils.js_eval(tab, f"""
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
    await _fill(tab, FIRST_NAME_FIELD, SuperScraper.FIRST_NAME)
    await _fill(tab, LAST_NAME_FIELD, SuperScraper.LAST_NAME)
    await _fill(tab, EMAIL_FIELD, SuperScraper.EMAIL)

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

    await asyncio.sleep(0.5)
    return True


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right in rights:
            right_id, right_label = RIGHT_MAP[right]
            await tab.go_to(URL)
            await asyncio.sleep(12)

            if not await _fill_form(tab, super_scraper, right_id):
                continue

            if SuperScraper.HEALTH_CHECK:
                await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

            if SuperScraper.DRY_RUN:
                await asyncio.sleep(1)
                await SuperScraper.screenshot(tab, f"dry_run_{right_id}")
                print(
                    f"DRY RUN: would submit '{right.name}' ('{right_label}') for {SuperScraper.EMAIL}"
                )
                continue

            print(
                f"\n'{right_label}' form filled. Solve the reCAPTCHA, then click Submit. "
                "Press Enter after the confirmation page loads..."
            )
            input()

            print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
