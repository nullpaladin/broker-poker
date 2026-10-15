# infillion.com — Custom OneTrust Angular DSAR portal, MAID-based (no
# address). "I am submitting this information on behalf of" set to "Myself".
# Request type is single-select (one submission per right): Info Request
# (Access) and Do Not Sell My Information unconditionally; Data Deletion
# gated on REMOVE_INFORMATION. Type of Mobile Advertising ID defaults to GAID
# (Android) — change to IDFA manually for an Apple identifier. Authorized
# agent question answered "No, the request is for myself". Country/State are
# vt-autocomplete comboboxes. reCAPTCHA v2 requires manual solve in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f7e3f6db-ed65-4759-a3f5-3b5c8b7e9bff/draft/9949a1a8-aa69-4848-a93f-d093d877a981"

RIGHT_MAP = {
    "access": [("Info Request", "access")],
    "opt_out_sale_share": [("Do Not Sell My Information", "opt_out")],
    "delete": [("Data Deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    myself_btn = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
    if myself_btn:
        await myself_btn.click_using_js()
        await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": right}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{right}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    gaid_btn = await tab.find(**{"aria-label": "GAID (Google Android)"}, raise_exc=False)
    if gaid_btn:
        await gaid_btn.click_using_js()
        await asyncio.sleep(0.5)

    if SuperScraper.ADVERTISING_ID:
        maid = await tab.find(id="formField57DSARElement", raise_exc=False)
        if maid:
            await maid.type_text(SuperScraper.ADVERTISING_ID)

    request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if request_details:
        await request_details.type_text(
            f"I am exercising my '{right}' rights under the {SuperScraper.LAW_FULL_NAME or 'applicable state and federal privacy law'}."
        )

    not_agent_btn = await tab.find(**{"aria-label": "No, the request is for myself"}, raise_exc=False)
    if not_agent_btn:
        await not_agent_btn.click_using_js()

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/infillion_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right, label in rights:
            await submit_request(tab, right, label, super_scraper)


asyncio.run(main())
