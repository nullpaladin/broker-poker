# nexxen.com — OneTrust Angular portal (privacyportal.onetrust.com) embedded on nexxen.com.
# Form requires one separate submission per right (explicitly stated on form).
# Country → State autocomplete reveals subject type, request types, acknowledgement.
# Subject type: formField72DSARElement, buttons "Customer"/"Employee"/"Vendor" → "Customer".
# Acknowledgement: click "Yes" via click_using_js.
# reCAPTCHA v2 — manual solve in live mode.
# Exercises Access/Portability, Correct, Do Not Sell/Share, Opt-out Sensitive,
# Opt-out Profiling/Ads; Delete gated on REMOVE_INFORMATION.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/76394770-3c6c-4d28-a57b-18817b0a8e3f/2bbd01a5-983c-440b-9fd5-fd341c9326a1"

ALWAYS_REQUESTS = [
    ("A copy of your personal information/Right to Data Portability", "access"),
    ("Correct your personal information",                              "correct"),
    ("Do Not Sell/Share your personal information",                    "optout"),
    ("Opt-out of Processing Sensitive Data",                           "sensitive"),
    ("Opt-Out of Automated Decision-Making and Profiling/Opt-out of Targeted Advertising", "profiling"),
]
DELETE_REQUEST = ("Delete your personal information", "delete")


async def _autocomplete(tab, field_id, text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(text)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            t = await opt.text
            if t and t.strip() == text:
                await opt.click()
                await asyncio.sleep(1)
                return


async def _submit_request(tab, request_aria, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Country
    await _autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)

    # State (appears after country)
    await _autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(1)

    # Subject type: Customer (formField72 container)
    customer = await tab.find(**{"aria-label": "Customer"}, raise_exc=False)
    if customer:
        await customer.click_using_js()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} 'Customer' subject button not found for {label}")

    # Request type
    req_btn = await tab.find(**{"aria-label": request_aria}, raise_exc=False)
    if req_btn:
        await req_btn.click_using_js()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} Request button '{request_aria}' not found")
        return

    # Acknowledgement: Yes
    yes_btn = await tab.find(**{"aria-label": "Yes"}, raise_exc=False)
    if yes_btn:
        await yes_btn.click_using_js()
        await asyncio.sleep(0.5)

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
        await tab.take_screenshot(f"resources/screenshots/nexxen_dry_run_{label}.png")
        print(f"Screenshot: resources/screenshots/nexxen_dry_run_{label}.png")
        return

    print(
        f"\nForm filled for '{label}'. "
        f"Solve the reCAPTCHA, then click Submit. "
        f"Press Enter after the confirmation page appears..."
    )
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}'")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_aria, label in requests:
            await _submit_request(tab, request_aria, label, super_scraper)


asyncio.run(main())
