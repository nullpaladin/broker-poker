# claritas.com — Custom OneTrust Angular DSAR portal. Two single-select
# request-type buttons (one submission per right): "Data Request" (Access)
# and "Request to be Deleted from Database" (Delete) — no separate Opt-Out option.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). No subject-type step.
# State is a plain text field requiring the 2-letter uppercase code (not an
# autocomplete combobox like most other OneTrust forms) — converted from
# STATE via SuperScraper.state_full_name_to_abbreviated. Correction requests
# are handled by email only (privacyinfo@claritas.com), per the intro text.
# A required "Contact Preference" button group (Voice/Text) appears after
# phone — defaulted to "Text". An optional (no asterisk) file upload asks for
# a photo ID or utility bill — left unfilled, not a blocker. reCAPTCHA v2
# requires manual solve in live mode.
#
# Page elements:
#   [aria-label=<entry>]            Request-type buttons (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #addressDSARElement / #cityDSARElement         Address / City
#   #stateDSARElement               State (text, 2-letter code)
#   #zipDSARElement                 ZIP
#   #emailDSARElement               Email
#   #phoneNumber                    Phone country code
#   #phoneNumberDSARElement         Phone number
#   [aria-label="Text"]             "Contact Preference" -> Text
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/68582716-6ce4-4f6e-bf08-78371b5f3292/6c7dc52d-0e2b-481f-9256-0755179e3783"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Data Request",
    Right.RIGHT_TO_DELETE: "Request to be Deleted from Database",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
}


async def submit_request(tab, right, right_label, super_scraper):
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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
