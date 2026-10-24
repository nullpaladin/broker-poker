# leadloft.com — user-agreements/personal-data. The page itself states
# "We are not CCPA regulated... We do not honor automated requests," so a
# submission here may simply be ignored — documented for completeness
# regardless, consistent with this repo's policy of filling and
# documenting rather than skipping based on a site's own claims. Only
# Delete/Rectify/Restrict Processing are offered — no Access or explicit
# Opt-Out-of-Sale option at all. "Restrict Processing" is used as the
# closest available analog to Opt-Out; "Rectify" (=Correct) is not automated. The email field ids are INVERTED from what they suggest:
# `id="Email"` is CSS-hidden (`hide-this-scale`, height:0) and is the
# actual spam trap, while `id="HoneyPot"` is the real, visibly-rendered
# field carrying the "Email Address *" label — filling "Email" instead
# would both miss the real field and trip the trap. Additional Information
# textarea is required, filled with the request statement. The form's own submit button uses an
# auto-generated Webflow node id (not a readable one) and there's a
# second, unrelated form on the page with a plain `id="submit"` (a
# newsletter-signup CTA) — targeted via the stable `wf-form-Personal-Data`
# form id instead of guessing either id directly. A `cf-turnstile-response`
# hidden field exists but no visible Turnstile widget renders — appears to
# run in invisible/managed mode with nothing to solve. Exercises Restrict
# Processing (as this form's Opt-out) and Delete. Which rights run is decided ONLY
# by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   #First-Name-2 / #Last-Name-2   First / Last name
#   #HoneyPot                      the REAL "Email Address *" field (see above)
#   #Email                         hidden spam trap — never touched
#   #Request-2                     "Request" <select> (Delete / Rectify / Restrict Processing)
#   #field-2                       "Additional Information" textarea (required)
#   //form[@id='wf-form-Personal-Data']//input[@type='submit']   Submit
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.leadloft.com/user-agreements/personal-data"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: ["Restrict Processing"],
    Right.RIGHT_TO_DELETE: ["Delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "#Request-2 option"  # may include a placeholder option; the first live run shows it

FIELD_XPATHS = {
    "First name": "//*[@id='First-Name-2']",
    "Last name": "//*[@id='Last-Name-2']",
    "Email": "//*[@id='HoneyPot']",
    "Request": "//*[@id='Request-2']",
    "Additional information": "//*[@id='field-2']",
}


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    first_field = await tab.find(id="First-Name-2", raise_exc=False)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)

    last_field = await tab.find(id="Last-Name-2", raise_exc=False)
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)

    # The field ids are inverted from what they suggest: id="Email" is
    # CSS-hidden (class "hide-this-scale", height:0) and is the actual
    # spam trap, while id="HoneyPot" is the real, visibly-rendered email
    # field (h:48, the one with the "Email Address *" label above it).
    # Filling "Email" instead would both miss the real field and trip the
    # trap.
    email_field = await tab.find(id="HoneyPot", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    request_select = await tab.find(id="Request-2", raise_exc=False)
    if request_select:
        await js_utils.select_native_option(request_select, text=request_type, dispatch=("change",))

    details_field = await tab.find(id="field-2", raise_exc=False)
    if details_field:
        await details_field.type_text(SuperScraper.request_statement([right], broker="LeadLoft"))

    label = request_type.lower().replace(" ", "_")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' ({request_type}) for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    # NOT id="submit" — that belongs to an unrelated newsletter-signup form
    # elsewhere on the page ("Your work email"). This form's own submit
    # button uses an auto-generated Webflow node id instead of a readable
    # one, so it's targeted via the stable form id + its submit input.
    submit_btn = await tab.find(
        xpath="//form[@id='wf-form-Personal-Data']//input[@type='submit']", raise_exc=False
    )
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' ({request_type}) for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{request_type}'")


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
            for request_type in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, super_scraper)


asyncio.run(main())
