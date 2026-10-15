# healthcare.com — server-rendered form, no captcha. "Inquiry" select is
# single-select (one submission per right): "Right to know what information
# is collected" (Access), "Right to opt-out of sales" (Opt-out) and "Right to
# delete personal information" (Delete); which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Per the
# form's own note, identification requires the *exact* email and phone number
# previously provided to healthcare.com — this only works for an existing
# customer, not an arbitrary consumer. A cookie consent banner covers part of
# the form on load and must be dismissed first.
#
# Page elements:
#   select#case_type   "Inquiry" <select> (single-select):
#       CASE_INFO_REQ   "Right to know what information is collected"
#       CASE_OPT_OUT    "Right to opt-out of sales"
#       CASE_DELETE     "Right to delete personal information"
#   first_name / last_name   First / Last name
#   email / phone_number     Email / Phone (must match what healthcare.com already has)
#   zip_code                 ZIP code
#   Button "Deny Non-Essential"   cookie banner
#   Button "Submit"
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.healthcare.com/data-request/request-form/"

CASE_INFO_REQ = "ccpa-info-req"          # "Right to know what information is collected"
CASE_OPT_OUT = "ccpa-opt-out-sales-req"  # "Right to opt-out of sales"
CASE_DELETE = "ccpa-delete-req"          # "Right to delete personal information"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: (CASE_INFO_REQ, "access"),
    Right.RIGHT_TO_OPT_OUT: (CASE_OPT_OUT, "opt_out"),
    Right.RIGHT_TO_DELETE: (CASE_DELETE, "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, case_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    deny_cookies = await tab.find(text="Deny Non-Essential", raise_exc=False)
    if deny_cookies:
        await deny_cookies.click()
        await asyncio.sleep(1)

    case_select = await tab.find(id="case_type", raise_exc=False)
    if case_select:
        await js_utils.select_native_option(case_select, value=case_type, dispatch=("change",))
    else:
        print(f"{super_scraper.OOPS} 'Inquiry' select not found")

    for name, value in [
        ("first_name", SuperScraper.FIRST_NAME),
        ("last_name", SuperScraper.LAST_NAME),
        ("email", SuperScraper.EMAIL),
        ("zip_code", SuperScraper.ZIP_CODE),
        ("phone_number", SuperScraper.PHONE_NUMBER),
    ]:
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{case_type}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
    await asyncio.sleep(2)
    print(f"Submitted '{case_type}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            case_type, label = RIGHT_MAP[right]
            await submit_request(tab, case_type, label, super_scraper)


asyncio.run(main())
