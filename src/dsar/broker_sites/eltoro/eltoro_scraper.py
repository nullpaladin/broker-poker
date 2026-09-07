# eltoro.com — IP targeting data broker.
# Three separate OneTrust Angular portals (privacyportal.onetrust.com):
#   Access form: all 4 sub-types selected in one submission
#   Opt-Out form: Limit Sensitive + Do Not Sell/Share in one submission
#   Delete form (gated): Delete My Information
# Request type and subject type buttons are role="option" divs — click_using_js().
# Country and state use autocomplete comboboxes — type, then click first visible
# role="option" element.
# Image CAPTCHA (captchaCode text input) — manual entry required in live mode.
# No phone field. Email verification required within 5 days of submission.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

ACCESS_URL = "https://privacyportal.onetrust.com/webform/96e88ef7-218d-4979-ba92-634d98263159/0a4612df-27c0-4726-8f16-a0a5f516997e"
OPTOUT_URL = "https://privacyportal.onetrust.com/webform/96e88ef7-218d-4979-ba92-634d98263159/518b4a8d-97b3-4fb6-a5a7-e1a1cd8de290"
DELETE_URL = "https://privacyportal.onetrust.com/webform/96e88ef7-218d-4979-ba92-634d98263159/9edfdd9d-053d-4e08-80af-cb72bdbf564b"

ACCESS_REQUESTS = [
    "Confirm Whether El Toro Has My Information",
    "Access - My Categories of Information",
    "Access - Was My Information Sold or Shared and to Whom",
    "Access - Pieces of My Information",
]
OPTOUT_REQUESTS = [
    "Limit the Use or Disclosure of My Sensitive Data",
    "Do Not Sell or Share My Information",
]
DELETE_REQUESTS = ["Delete My Information"]


async def _select_autocomplete(tab, field_id, text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(text)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            opt_text = await opt.text
            if opt_text and opt_text.strip() == text:
                await opt.click()
                await asyncio.sleep(1)
                return


async def submit_form(tab, url, request_types, label, super_scraper):
    await tab.go_to(url)
    await asyncio.sleep(7)

    # Select all request types
    for aria in request_types:
        btn = await tab.find(**{"aria-label": aria}, raise_exc=False)
        if btn:
            await btn.click_using_js()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} Request button '{aria}' not found")

    # Subject type: Consumer
    consumer = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
    if consumer:
        await consumer.click_using_js()
        await asyncio.sleep(0.5)

    time.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"resources/screenshots/eltoro_dry_run_{label}.png")
        print(f"Screenshot: resources/screenshots/eltoro_dry_run_{label}.png")
        return

    captcha = await tab.find(id="captchaCode", raise_exc=False)
    if captcha and await captcha.is_visible():
        code = input("Enter the CAPTCHA text shown in the browser: ")
        await captcha.type_text(code)

    print(f"\nForm filled for '{label}'.")
    print("Click Submit in the browser, then press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_form(tab, ACCESS_URL, ACCESS_REQUESTS, "access", super_scraper)
        await submit_form(tab, OPTOUT_URL, OPTOUT_REQUESTS, "optout", super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await submit_form(tab, DELETE_URL, DELETE_REQUESTS, "delete", super_scraper)


asyncio.run(main())
