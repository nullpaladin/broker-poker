# aspire-north.com — the DSAR mechanism is the "California - Right to Deletion"
# form on the related domain americanspiritcorp.com. Formsite-hosted, server-
# rendered, POSTs in place. Right to Delete / Opt-Out (the button reads
# "Submit Request/Opt-Out"). The right email (per README) has gone unanswered.
# Fields (Formsite `fieldNNNNNNNNN-...` names):
#   field103068929-first / -last
#   field103068930-address / -address2 / -city / -state (<select>, full names)
#     / -zip
#   field103068931_1  a required checkbox (declaration) -> checked
#   field103068933    email
# An invisible reCAPTCHA v3 badge is present; no manual solve for a dry run,
# though Google may still score the automated submit.
# Rights the form exposes: deletion / opt-out in ONE submission (no separate chooser), so
# both map to the same single submission; it runs if either is requested via
# SuperScraper.rights_to_exercise(RIGHT_MAP). Form is titled "California - Right to
# Deletion", so it is treated as only for residents of states with a privacy law.
#
# Page elements (keep this list current):
#   #field103068929-first / -last   First / Last name
#   #field103068930-address / -address2 / -city / -zip   Address, Address 2, City, Zip
#   #field103068930-state           State <select> (full names)
#   #field103068931_1              Required declaration checkbox
#   #field103068933                Email
#   "Submit Request/Opt-Out"       Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.americanspiritcorp.com/ca-right-to-deletion.html"

SERVES_NO_LAW_STATES = False

# One form, one submission: the button reads "Submit Request/Opt-Out".
SUBMIT_LABEL = "Submit Request/Opt-Out"
RIGHT_MAP = {
    Right.RIGHT_TO_DELETE: SUBMIT_LABEL,
    Right.RIGHT_TO_OPT_OUT: SUBMIT_LABEL,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='field103068929-first']",
    "Last name": "//*[@id='field103068929-last']",
    "Address": "//*[@id='field103068930-address']",
    "City": "//*[@id='field103068930-city']",
    "State": "//*[@id='field103068930-state']",
    "Zip": "//*[@id='field103068930-zip']",
    "Email": "//*[@id='field103068933']",
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        fields = {
            "field103068929-first": SuperScraper.FIRST_NAME,
            "field103068929-last": SuperScraper.LAST_NAME,
            "field103068930-address": SuperScraper.ADDRESS,
            "field103068930-address2": SuperScraper.ADDRESS_LINE_TWO,
            "field103068930-city": SuperScraper.CITY,
            "field103068930-zip": SuperScraper.ZIP_CODE,
            "field103068933": SuperScraper.EMAIL,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state = await tab.find(id="field103068930-state", raise_exc=False)
        if state:
            await js_utils.select_native_option(state, text=SuperScraper.STATE)

        checkbox = await tab.find(id="field103068931_1", raise_exc=False)
        if checkbox:
            await checkbox.click()
        else:
            print(f"{super_scraper.OOPS} declaration checkbox not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(
            xpath=f"//*[normalize-space()='{SUBMIT_LABEL}' or @type='submit']", raise_exc=False
        )
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
