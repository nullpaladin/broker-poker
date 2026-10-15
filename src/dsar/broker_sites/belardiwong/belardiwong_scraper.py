# belardiwong.com — three separate OneTrust DSAR forms (one URL per right,
# same portal id as adstradata.com but a distinct, working consumer-facing
# deployment — no "authorized agent" dead end here).
# Rights the form exposes: access, opt-out, delete (one form each). Which of them run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Two-step email verification required after submission. No free-text details box.
#
# Page elements:
#   #firstNameDSARElement      First name
#   #lastNameDSARElement       Last name
#   #email                     Email
#   #countryDSARElement        Country (vt-autocomplete combobox: type, ArrowDown, Enter)
#   #vt-input-6                Phone country code
#   #phoneNumberDSARElement    Phone number
#   #addressDSARElement        Address
#   #formField16DSARElement    Address Line 2 (optional, not filled)
#   #cityDSARElement           City
#   #stateDSARElement          State (vt-autocomplete combobox)
#   #zipDSARElement            ZIP code
#   #captchaCode               BotDetect image CAPTCHA (manual entry in live mode)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

# Right -> the URL of that right's OneTrust webform.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "https://privacyportal.onetrust.com/webform/3d2d5e0c-bd98-46b8-906c-ede68a6f6a80/db862165-db28-4966-885c-8ace2d0c1512",
    Right.RIGHT_TO_OPT_OUT: "https://privacyportal.onetrust.com/webform/3d2d5e0c-bd98-46b8-906c-ede68a6f6a80/400f54ed-fcbb-4749-ab5b-32f491c72390",
    Right.RIGHT_TO_DELETE: "https://privacyportal.onetrust.com/webform/3d2d5e0c-bd98-46b8-906c-ede68a6f6a80/dd119353-8970-4dbf-ac1d-b6406173c7bb",
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
    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    await _fill_autocomplete(tab, "countryDSARElement", "United States")

    phone_cc = await tab.find(id="vt-input-6", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _fill_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{right.name}'. Enter the CAPTCHA code, click Submit,")
    print("then complete the two-step email verification. Press Enter when done...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} — confirm in the browser.")


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
