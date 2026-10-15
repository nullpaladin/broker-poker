# eltoro.com — IP targeting data broker.
# Three separate OneTrust Angular portals (privacyportal.onetrust.com):
#   Access form: all 4 sub-types selected in one submission
#   Opt-Out form: Limit Sensitive + Do Not Sell/Share in one submission
#   Delete form: Delete My Information
# Request type and subject type buttons are role="option" divs — click_using_js().
# Country and state use autocomplete comboboxes — type, then click first visible
# role="option" element.
# Image CAPTCHA (captchaCode text input) — manual entry required in live mode.
# No phone field. Email verification required within 5 days of submission.
#
# Page elements (all three portals share them):
#   aria-label=<request type>          request-type option buttons (names in the *_REQUESTS lists)
#   aria-label="Consumer"              subject-type button
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name / Email
#   #addressDSARElement / #cityDSARElement                             Address / City
#   #countryDSARElement / #stateDSARElement                            Country / State comboboxes
#   #zipDSARElement                                                    Zip code
#   #captchaCode                       image CAPTCHA text input
#   aria-label="Click to submit form"  Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
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

# Right -> (portal URL, request-type buttons to click on it). One portal per right.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: (ACCESS_URL, ACCESS_REQUESTS),
    Right.RIGHT_TO_OPT_OUT: (OPTOUT_URL, OPTOUT_REQUESTS),
    Right.RIGHT_TO_DELETE: (DELETE_URL, DELETE_REQUESTS),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def submit_form(tab, url, request_types, right, super_scraper):
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
            f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    captcha = await tab.find(id="captchaCode", raise_exc=False)
    if captcha and await captcha.is_visible():
        code = input("Enter the CAPTCHA text shown in the browser: ")
        await captcha.type_text(code)

    print(f"\nForm filled for '{right.name}'.")
    print("Click Submit in the browser, then press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            url, request_types = RIGHT_MAP[right]
            await submit_form(tab, url, request_types, right, super_scraper)


asyncio.run(main())
