# firstorion.com — no privacy-request URL exists on the main site at all;
# the actual portal is linked only from the footer of an otherwise-unrelated
# 404 page ("Do Not Sell My Info" -> https://privacy.firstorion.com/).
# "GET STARTED ONLINE" leads to a single-page form: First/Last/Email/Phone
# Number (the phone number being opted out — First Orion sells phone/name/
# address/carrier/line-type data, so this *is* the identifying record, not
# just a contact method), "What right do you want to exercise?" (single-
# select radio: "opt-out" bundles opt-out-of-sale with deletion — no way to
# separate them, gated on REMOVE_INFORMATION like similar bundled-delete
# options elsewhere in this repo; "data" is Access, exercised
# unconditionally), and a required attestation checkbox. The submit button
# is literally labeled "Send Confirmation" — clicking it sends a real
# verification email/SMS/call to the phone number and address provided, so
# this scraper fills the form and stops there regardless of DRY_RUN.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacy.firstorion.com/"

REQUEST_TYPES = ["data"]
OPT_OUT_DELETE_TYPE = "opt-out"


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    start_btn = await tab.find(text="GET STARTED ONLINE", raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} 'GET STARTED ONLINE' button not found")
        return
    await start_btn.click()
    await asyncio.sleep(3)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "phone": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    radio = await tab.find(xpath=f"//input[@name='opt-out' and @value='{request_type}']", raise_exc=False)
    if radio:
        await radio.click()

    checkbox = await tab.find(xpath="//input[@type='checkbox']", raise_exc=False)
    if checkbox:
        await checkbox.click()

    label = request_type.replace("-", "_")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/firstorion_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/firstorion_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT sent — click 'Send Confirmation' yourself, "
        "complete the phone/email verification, and confirm the request. This sends a real "
        "verification message regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(OPT_OUT_DELETE_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
