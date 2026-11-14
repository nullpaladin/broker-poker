# delivr.ai — the "Submit a Request" button on /privacy (not the more
# prominent "Submit a Data Subject Request" paragraph text right above it,
# which is non-interactive) opens an in-page modal. Request Type is a
# single-select radio (view / delete / change / do_not_sell, defaults to "view"),
# so one submission per right. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). "change" is not automated.
# Every radio's real input is visually hidden (class "sr-only") inside a
# clickable `<label>` wrapper — click the label, not the input, same pattern as
# audigent.com/datasys.com elsewhere in this repo. No captcha observed.
#
# Page elements:
#   "Submit a Request" button          Opens the modal
#   input[name=requestType]            Request Type radio (view / delete / change / do_not_sell)
#   #dsr-email / #dsr-first / #dsr-last   Email / First Name / Last Name
#   "Submit Request" button            Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.delivr.ai/privacy"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "view",
    Right.RIGHT_TO_OPT_OUT: "do_not_sell",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[name='requestType'])"  # request-type radios in the modal

FIELD_XPATHS = {
    "Email": "//*[@id='dsr-email']",
    "First name": "//*[@id='dsr-first']",
    "Last name": "//*[@id='dsr-last']",
}


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    open_btn = await tab.find(text="Submit a Request", raise_exc=False)
    if not open_btn:
        print(f"{super_scraper.OOPS} 'Submit a Request' button not found")
        return
    await open_btn.click()
    await asyncio.sleep(1.5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    radio_label = await tab.find(
        xpath=f"//input[@name='requestType' and @value='{request_type}']/ancestor::label",
        raise_exc=False,
    )
    if not radio_label:
        print(f"{super_scraper.OOPS} request type option '{request_type}' not found")
        return
    await radio_label.click()

    email_field = await tab.find(id="dsr-email", raise_exc=False)
    first_field = await tab.find(id="dsr-first", raise_exc=False)
    last_field = await tab.find(id="dsr-last", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{right.name}'")


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
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
