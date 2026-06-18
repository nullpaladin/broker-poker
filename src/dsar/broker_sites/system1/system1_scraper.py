# system1.com — exercises Do Not Sell, Disclosure of Information We Share, Data Deletion (gated).
# OneTrust portal (privacyportal.onetrust.com) embedded as iframe on privacy-inquiries page.
# Country uses ArrowDown+Enter (not type+click pattern). Request types are dropdown options.
# formField50DSARElement = "Which website did you visit?" (required, filled with "system1.com").
# reCAPTCHA v2 requires manual solve before submit. One submission per right type.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f25d1283-339b-438f-9445-922b74e13939/a65f494a-fd3d-4117-8051-f2c0f0d66133"

# (request type option text, screenshot label)
REQUESTS = [
    ("Do Not Sell My Information",          "optout"),
    ("Disclosure of Information we share",  "access"),
]
DELETE_REQUEST = ("Data Deletion", "delete")


async def submit_request(tab, req_type_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Country — ArrowDown+Enter
    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(1)

    # Request type: click field, then click the visible option
    req_field = await tab.find(id="requestTypesDSARElement", raise_exc=False)
    if req_field:
        await req_field.click()
        await asyncio.sleep(2)
        opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
        clicked = False
        for opt in opts:
            if await opt.is_visible():
                t = await opt.text
                if t and t.strip() == req_type_text:
                    await opt.click()
                    clicked = True
                    break
        if not clicked:
            print(f"{super_scraper.OOPS} Request type option '{req_type_text}' not found")
            return
    await asyncio.sleep(1)

    # Which website did you visit?
    website_field = await tab.find(id="formField50DSARElement", raise_exc=False)
    if website_field:
        await website_field.type_text("system1.com")

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(
            f"I am a Minnesota resident exercising my privacy rights. "
            f"Request type: {req_type_text}."
        )

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await tab.take_screenshot(f"resources/screenshots/system1_dry_run_{label}.png")
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{label}'. Solve the reCAPTCHA, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2000")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_type_text, label in requests:
            await submit_request(tab, req_type_text, label, super_scraper)


asyncio.run(main())
