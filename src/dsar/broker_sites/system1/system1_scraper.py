# system1.com — OneTrust portal (privacyportal.onetrust.com) embedded as iframe on privacy-inquiries page.
# Rights the form exposes: access ("Disclosure of Information we share"), opt-out ("Do Not Sell My
# Information"), delete ("Data Deletion"). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). One submission per right.
# Country uses ArrowDown+Enter (not type+click pattern). Request types are dropdown options.
# reCAPTCHA v2 requires manual solve before submit.
#
# Page elements:
#   #countryDSARElement         "Country" combobox -> "United States"
#   #requestTypesDSARElement    "Request type" dropdown (role=option items, see RIGHT_MAP)
#   #formField50DSARElement     "Which website did you visit?" (required) -> "system1.com"
#   #firstNameDSARElement       First name
#   #lastNameDSARElement        Last name
#   #emailDSARElement           Email
#   #requestDetailsDSARElement  Request details textarea
#   [aria-label="click to submit form"]  Submit button (manual click after reCAPTCHA)
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f25d1283-339b-438f-9445-922b74e13939/a65f494a-fd3d-4117-8051-f2c0f0d66133"

# Right -> the "Request type" option text.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Disclosure of Information we share",
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell My Information",
    Right.RIGHT_TO_DELETE: "Data Deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, req_type_text, super_scraper):
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
        await details.type_text(SuperScraper.request_statement([right], broker="System1"))

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
