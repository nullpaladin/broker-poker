# delivr.ai — the "Submit a Request" button on /privacy (not the more
# prominent "Submit a Data Subject Request" paragraph text right above it,
# which is non-interactive) opens an in-page modal: Request Type (single-
# select radio — view/delete/change/do_not_sell, defaults to "view"),
# Email, First Name, Last Name, then Submit Request. Every radio's real
# input is visually hidden (class "sr-only") inside a clickable `<label>`
# wrapper — click the label, not the input, same pattern as audigent.com/
# datasys.com elsewhere in this repo. Exercises "view" (Access) and
# "do_not_sell" (Opt-Out) unconditionally; "delete" gated on
# REMOVE_INFORMATION. No captcha observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.delivr.ai/privacy"

REQUEST_TYPES = ["view", "do_not_sell"]
DELETE_REQUEST_TYPE = "delete"


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    open_btn = await tab.find(text="Submit a Request", raise_exc=False)
    if not open_btn:
        print(f"{super_scraper.OOPS} 'Submit a Request' button not found")
        return
    await open_btn.click()
    await asyncio.sleep(1.5)

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

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/delivr_dry_run_{request_type}.png")
        print(f"Screenshot saved to resources/screenshots/delivr_dry_run_{request_type}.png")
        return

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{request_type}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
