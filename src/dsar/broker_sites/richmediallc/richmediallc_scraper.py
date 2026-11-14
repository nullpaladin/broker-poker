# richmediallc.com — custom (non-OneTrust) server-rendered "Privacy
# Request Form". "Request Type" is single-select (the page's own copy
# says to submit a separate request for each right) — one submission per
# right: Opt out of sale/share, Right to know, Right to delete (each gated by
# SuperScraper.rights_to_exercise(RIGHT_MAP)). "Limit use of sensitive personal information" and
# "Correct inaccurate personal information" are skipped (no concrete
# sensitive-use limitation or inaccuracy to describe). Postal
# Address/City/Zip are optional (only relevant "if your request relates
# to postal marketing") — filled anyway since the data is available.
# Cloudflare Turnstile checkbox — **CAPTCHA solution required**.
#
# Page elements:
#   #firstName / #lastName / #email   First / Last name, Email
#   #postalAddress / #city / #zipCode Postal Address / City / Zip (optional)
#   #state                            State <select>
#   input[name=requestType] radios    "Request Type": access_request ("Right to know"),
#                                     opt_out_sale_share ("Opt out of sale/share"),
#                                     delete_request ("Right to delete")
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacy.richmediallc.com/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["access_request"],
    Right.RIGHT_TO_OPT_OUT: ["opt_out_sale_share"],
    Right.RIGHT_TO_DELETE: ["delete_request"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option of the "Request Type" radio, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Right to know": Right.RIGHT_TO_ACCESS,
    "Opt out of sale/share": Right.RIGHT_TO_OPT_OUT,
    "Right to delete": Right.RIGHT_TO_DELETE,
    "Limit use of sensitive personal information": None,
    "Correct inaccurate personal information": None,
}
RIGHTS_OPTIONS_CSS = "label:has(input[name='requestType'])"

FIELD_XPATHS = {
    "First name": "//*[@id='firstName']",
    "Last name": "//*[@id='lastName']",
    "Email": "//*[@id='email']",
    "Postal address": "//*[@id='postalAddress']",
    "City": "//*[@id='city']",
    "Zip": "//*[@id='zipCode']",
    "State": "//*[@id='state']",
}

RIGHT_LABELS = {
    "opt_out_sale_share": "Opt out of sale/share",
    "access_request": "Right to know",
    "delete_request": "Right to delete",
}


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "postalAddress": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "zipCode": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_abbrev = SuperScraper.STATE_ABBREVIATED
        await js_utils.select_native_option(state_select, value=state_abbrev)
    else:
        print(f"{super_scraper.OOPS} State select not found")

    radio = await tab.find(xpath=f"//input[@name='requestType' and @value='{right}']", raise_exc=False)
    if radio:
        await radio.click()
    else:
        print(f"{super_scraper.OOPS} request type '{right}' not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right}")
    print(
        f"\n'{RIGHT_LABELS[right]}' request filled but NOT submitted — a Cloudflare "
        "Turnstile checkbox requires a manual solve."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_values = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_value in request_values:
            await submit_request(tab, request_value, super_scraper)


asyncio.run(main())
