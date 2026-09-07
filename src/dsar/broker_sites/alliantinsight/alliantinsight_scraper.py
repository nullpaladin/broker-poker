# alliantinsight.com — three separate OneTrust CDN DSAR forms (one URL per right,
# same portal id). Fields: firstNameDSARElement, lastNameDSARElement,
# emailDSARElement, addressDSARElement, cityDSARElement, zipDSARElement.
# Country (Access/Delete only) and State are vt-autocomplete comboboxes
# (countryDSARElement / stateDSARElement on Access+Delete, formField21DSARElement
# for State on Opt-Out) — type then ArrowDown+Enter. Phone (id="phoneNumber")
# only present on Access/Delete. reCAPTCHA v2 checkbox (g-recaptcha-response)
# requires manual solve in live mode. After submission Alliant runs its own
# identity-verification quiz (several knowledge-based questions) before
# processing — cannot be automated; the user must answer those manually.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URLS = {
    "access": "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/ed491735-e5be-4f7b-80dd-153c159744b2.html",
    "optout": "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/2b52262e-8ada-4725-b86e-e4b960336f96.html",
}
DELETE_URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/604f597f-4486-46cd-99d2-ffa1218c7d6b.html"


async def _fill_autocomplete(tab, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await tab.keyboard.type_text(value)
    await asyncio.sleep(2)
    await tab.keyboard.press(Key.ARROWDOWN)
    await asyncio.sleep(0.3)
    await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)


async def submit_request(tab, url, label, super_scraper):
    await tab.go_to(url)
    await asyncio.sleep(6)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    await _fill_autocomplete(tab, "countryDSARElement", "United States")

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _fill_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
    await _fill_autocomplete(tab, "formField21DSARElement", SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    phone = await tab.find(id="phoneNumber", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/alliantinsight_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{label}'. Solve the reCAPTCHA checkbox, click Submit,")
    print("then complete Alliant's identity-verification quiz. Press Enter when done...")
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

    urls = dict(URLS)
    if SuperScraper.REMOVE_INFORMATION:
        urls["delete"] = DELETE_URL

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for label, url in urls.items():
            await submit_request(tab, url, label, super_scraper)


asyncio.run(main())
