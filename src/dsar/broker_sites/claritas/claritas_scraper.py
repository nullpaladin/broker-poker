# claritas.com — Custom OneTrust Angular DSAR portal. Two single-select
# request-type buttons (one submission per right): "Data Request" (Access)
# and "Request to be Deleted from Database" (Delete, gated on
# REMOVE_INFORMATION) — no separate Opt-Out option. No subject-type step.
# State is a plain text field requiring the 2-letter uppercase code (not an
# autocomplete combobox like most other OneTrust forms) — converted from
# STATE via SuperScraper.state_full_name_to_abbreviated. Correction requests
# are handled by email only (privacyinfo@claritas.com), per the intro text.
# A required "Contact Preference" button group (Voice/Text) appears after
# phone — defaulted to "Text". An optional (no asterisk) file upload asks for
# a photo ID or utility bill — left unfilled, not a blocker. reCAPTCHA v2
# requires manual solve in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/68582716-6ce4-4f6e-bf08-78371b5f3292/6c7dc52d-0e2b-481f-9256-0755179e3783"

RIGHT_MAP = {
    "access": [("Data Request", "access")],
    "delete": [("Request to be Deleted from Database", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right_label, screenshot_label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    req_btn = await tab.find(**{"aria-label": right_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{right_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)
    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    state_abbrev = SuperScraper.STATE_ABBREVIATED
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.type_text(state_abbrev)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)
    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    phone_cc = await tab.find(id="phoneNumber", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    contact_pref = await tab.find(**{"aria-label": "Text"}, raise_exc=False)
    if contact_pref:
        await contact_pref.click_using_js()

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/claritas_dry_run_{screenshot_label}.png")
        return

    print(f"\nForm filled for '{right_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right_label}' — verify in browser")


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
        for right_label, screenshot_label in rights:
            await submit_request(tab, right_label, screenshot_label, super_scraper)


asyncio.run(main())
