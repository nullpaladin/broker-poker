# i-360.com — Custom OneTrust Angular DSAR portal. Subject type "I am
# submitting this request as a/an" set to "Consumer". Request type is
# single-select (one submission per right) out of 12 buttons; the core
# data-subject rights are exercised here (Know categories/specific pieces,
# Update/correct, Object/restrict processing, Obtain+transmit to a third
# party (portability), Opt-out of sale/sharing, Limit Sensitive PI); "File a
# complaint", "Raise concerns", and "Appeal previously denied request" are
# skipped as auxiliary contact options rather than data-subject rights.
# Erase personal data is gated on REMOVE_INFORMATION. U.S. State
# (formField40DSARElement) is a vt-autocomplete combobox. reCAPTCHA v2
# requires manual solve in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/94afa614-d9cb-419b-99f1-20c87afaca7f/7527122f-48fe-46ad-bd59-6d69a33ac4db"

# "Object/restrict processing" has no exact canonical code -> rides with opt-out.
RIGHT_MAP = {
    "access": ["Know categories of personal data", "Know specific pieces of personal data"],
    "correct": ["Update/correct personal data"],
    "portability": ["Obtain personal data to transmit to a third-party"],
    "opt_out_sale_share": [
        "Opt-out of sale or sharing of personal information",
        "Object/restrict processing of personal data",
    ],
    "limit_sensitive_pi": ["Limit Use / Disclosure of Sensitive Personal Information"],
    "delete": ["Erase personal data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    consumer_btn = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
    if consumer_btn:
        await consumer_btn.click_using_js()
        await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": right}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{right}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    state_field = await tab.find(id="formField40DSARElement", raise_exc=False)
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
    address = await tab.find(id="formField34DSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)
    city = await tab.find(id="formField36DSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    phone_cc = await tab.find(id="vt-input-8", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if request_details:
        await request_details.type_text(
            f"I am exercising my '{right}' rights under applicable privacy law."
        )

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/i-360_dry_run_{label}.png")
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
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())
