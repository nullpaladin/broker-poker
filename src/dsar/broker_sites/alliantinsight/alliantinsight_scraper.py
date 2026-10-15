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
# Which rights run is decided only by SuperScraper.rights_to_exercise.
#
# Page elements (ids as used on the forms):
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement                              Email
#   #countryDSARElement                            Country combobox -> "United States" (Access/Delete)
#   #addressDSARElement                            Address
#   #cityDSARElement                               City
#   #stateDSARElement                              State combobox (Access/Delete)
#   #formField21DSARElement                        State combobox (Opt-Out form)
#   #zipDSARElement                                Zip code
#   #phoneNumber                                   Phone (Access/Delete only)
#   g-recaptcha-response                           reCAPTCHA v2 checkbox (manual solve)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

# One separate form (URL) per right.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/ed491735-e5be-4f7b-80dd-153c159744b2.html",
    Right.RIGHT_TO_OPT_OUT: "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/2b52262e-8ada-4725-b86e-e4b960336f96.html",
    Right.RIGHT_TO_DELETE: "https://privacyportal-cdn.onetrust.com/dsarwebform/591ac1c1-3a1e-496f-9e43-ff4afb5fef85/604f597f-4486-46cd-99d2-ffa1218c7d6b.html",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def submit_request(tab, right, url, super_scraper):
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
            f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA checkbox, click Submit,")
    print("then complete Alliant's identity-verification quiz. Press Enter when done...")
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
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
