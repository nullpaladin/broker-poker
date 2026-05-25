# blackbaud.com — custom OneTrust Angular portal DSAR form.
# formField100DSARElement = Yes/No listbox "Are you an authorized agent?" — click "No".
# Country + State: independent autocompletes.
# Subject type "Consumer" and request type buttons are Angular choice cards (click_using_js).
# Request types available after MN (and other qualifying states) selected:
#   Data Subject Access Request, Data Subject Opt-out Request,
#   Data Subject Correction Request, Data Subject Deletion Request (gated).
# No phone field. confirmEmailInputDSARElement must match emailDSARElement.
# formFields 93/98/101/102 are informational display text — no user input needed.
# captchaCode is an image CAPTCHA — manual entry required in live mode.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://blackbaud-privacy.my.onetrust.com/webform/170c909c-5ed2-49f1-a59c-2a44be2f6f27/de22df57-d96c-480a-afb0-ac090b928192"

BASE_REQUEST_TYPES = [
    "Data Subject Access Request",
    "Data Subject Opt-out Request",
    "Data Subject Correction Request",
]
DELETE_REQUEST_TYPE = "Data Subject Deletion Request"


async def _select_autocomplete(tab, field_id, search_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(search_text)
    await asyncio.sleep(2)
    opts = await tab.find(text=search_text, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            break
    await asyncio.sleep(1)


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")
    super_scraper = SuperScraper()

    request_types = list(BASE_REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        # "Are you an authorized agent?" — select No
        no_btn = await tab.find(**{"aria-label": "No"}, raise_exc=False)
        if no_btn:
            await no_btn.click_using_js()
            await asyncio.sleep(0.5)

        await _select_autocomplete(tab, "countryDSARElement", "United States")
        await asyncio.sleep(1)
        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
        await asyncio.sleep(1)

        consumer = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
        if consumer:
            await consumer.click_using_js()
            await asyncio.sleep(1)

        for req_type in request_types:
            btn = await tab.find(**{"aria-label": req_type}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        confirm = await tab.find(id="confirmEmailInputDSARElement", raise_exc=False)
        if confirm:
            await confirm.type_text(SuperScraper.EMAIL)

        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        zipcode = await tab.find(id="zipDSARElement", raise_exc=False)
        if zipcode:
            await zipcode.type_text(SuperScraper.ZIP_CODE)

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            rights = ", ".join(request_types)
            print(
                f"DRY RUN: would submit [{rights}] for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
            if not submit_btn:
                submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            suffix = "_delete" if SuperScraper.REMOVE_INFORMATION else ""
            await tab.take_screenshot(f"blackbaud_dry_run{suffix}.png")
            print(f"Screenshot saved to blackbaud_dry_run{suffix}.png")
            return

        print(f"\nForm filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}.")
        print("Enter the image CAPTCHA value into the captchaCode field.")
        print("Then click Submit. Press Enter after submission completes...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
