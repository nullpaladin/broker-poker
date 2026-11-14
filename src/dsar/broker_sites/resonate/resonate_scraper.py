# resonate.com — the marketing page (submit-consumer-privacy-request/)
# only lazy-loads an iframe pointing at the real form host,
# https://optout-form.reson8.com/ — navigate there directly (the marketing
# page's own raw HTML has no form fields at all until the iframe loads,
# same "navigate to the iframe src" pattern as media.net/preqin.com
# elsewhere in this repo). Simple custom (non-OneTrust) form, no CAPTCHA
# observed. Fields have no id/name on the plain inputs — targeted by CSS
# class (first_name/last_name/email/state). "Requested Action(s)" is a
# genuinely multi-select checkbox group (all applicable rights checked in
# ONE combined submission): Access to Information, Opt Out of Sale and
# Deletion of My Data, each only if selected by rights_to_exercise. Limit
# Use of Sensitive Info/Correct My Data/Port My Data left unchecked (no
# concrete correction/portability need for a generic request).
# "Designated Agent" checkbox left unchecked. "Resonate Identifier" is a
# disabled, auto-populated-only field (shows "Resonate Identifier not
# found" for a fresh session with no Resonate cookie) — left as-is, not
# fillable.
#
# Page elements:
#   input.first_name / input.last_name / input.email   First / Last name, Email
#   select.state                                       State
#   input[name=aboutInfoRequested]     "Access to Information" checkbox
#   input[name=optOutRequested]        "Opt Out of Sale" checkbox
#   input[name=deleteDataRequested]    "Deletion of My Data" checkbox
#   #submit-btn                        Submit button
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://optout-form.reson8.com/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["aboutInfoRequested"],
    Right.RIGHT_TO_OPT_OUT: ["optOutRequested"],
    Right.RIGHT_TO_DELETE: ["deleteDataRequested"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The checkbox labels are not recorded verbatim, only their input names.)

FIELD_XPATHS = {
    "First name": "//input[@class='first_name']",
    "Last name": "//input[@class='last_name']",
    "Email": "//input[@class='email']",
    "State": "//select[@class='state']",
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
        }
        for class_name, value in fields.items():
            field = await tab.find(xpath=f"//input[@class='{class_name}']", raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{class_name}' not found")

        state_select = await tab.find(xpath="//select[@class='state']", raise_exc=False)
        if state_select:
            state_abbrev = SuperScraper.STATE_ABBREVIATED
            await js_utils.select_native_option(state_select, value=state_abbrev)
        else:
            print(f"{super_scraper.OOPS} State select not found")

        checkbox_values = [entry for right in rights for entry in RIGHT_MAP[right]]
        for value in checkbox_values:
            checkbox = await tab.find(xpath=f"//input[@name='{value}']", raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{value}' not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit consumer privacy request")
            return

        submit_btn = await tab.find(id="submit-btn", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
