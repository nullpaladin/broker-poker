# issgovernance.com — server-rendered CCPA form (iss-stoxx.com). Required
# "cal_resident" checkbox attests California residency — same CA-only
# framing already used elsewhere in this repo (e.g. reonomy.com, finthrive.com),
# followed here rather than introduced as a new exception. No discrete right
# picker — a free-text "right_to_limit" textarea states which right(s) to
# exercise, so all selected rights go into ONE submission via request_statement.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# ria_broker_dealer/licenced_insurance_agent are optional and left blank
# (not applicable). "trap" is a honeypot field — left untouched. reCAPTCHA
# v3 is invisible and auto-resolves.
#
# Page elements:
#   #cal_resident       Checkbox attesting California residency   (required)
#   #first_name         First name
#   #last_name          Last name
#   #email_address      Email address
#   #right_to_limit     Free-text textarea stating the right(s) to exercise
#   //form[@id='ccpa-form']//button[@type='submit']   Submit button
#
# NOTE: click()-then-type_text() silently fails on first_name/last_name on
# this page (click never focuses the field — document.activeElement stays
# BODY, likely something on the page intercepting the click), even though
# the identical approach works fine on email_address. Every field here is
# instead set via the native input-value setter + input/change event
# dispatch (js_utils.js_set_value), which is reliable regardless of focus behavior.
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.iss-stoxx.com/legal/ccpa/"

# The form has no right picker: every right is stated in the #right_to_limit textarea.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "right_to_limit",
    Right.RIGHT_TO_OPT_OUT: "right_to_limit",
    Right.RIGHT_TO_DELETE: "right_to_limit",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (No rights chooser: every right is stated in the free-text field.)

CAL_RESIDENT = "cal_resident"  # checkbox: California residency attestation
FIRST_NAME = "first_name"  # "First name"
LAST_NAME = "last_name"  # "Last name"
EMAIL = "email_address"  # "Email address"
REQUEST_TEXT = "right_to_limit"  # free-text "which right(s) to exercise" textarea
SUBMIT = "//form[@id='ccpa-form']//button[@type='submit']"


async def _set(tab, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if field:
        await js_utils.js_set_value(field, value)
    else:
        print(f"field '{field_id}' not found")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        checkbox = await tab.find(id=CAL_RESIDENT, raise_exc=False)
        if checkbox:
            await js_utils.js_check(checkbox)

        await _set(tab, FIRST_NAME, SuperScraper.FIRST_NAME)
        await _set(tab, LAST_NAME, SuperScraper.LAST_NAME)
        await _set(tab, EMAIL, SuperScraper.EMAIL)
        await _set(tab, REQUEST_TEXT, SuperScraper.request_statement(rights, broker="ISS"))

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": f"//*[@id='{FIRST_NAME}']",
                "Last name": f"//*[@id='{LAST_NAME}']",
                "Email address": f"//*[@id='{EMAIL}']",
                "Right(s) to exercise": f"//*[@id='{REQUEST_TEXT}']",
            })

        rights_label = ", ".join(r.name for r in rights)
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit '{rights_label}' for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT, sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted '{rights_label}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
