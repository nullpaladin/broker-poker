# wiland.com — Two separate OneTrust forms (no country/state autocomplete).
# Access form: Delivery = Electronic Delivery (default button), name, email
#   (id="email" not emailDSARElement), address, city, state (2-letter abbr via
#   formField79DSARElement), zip, authorization checkbox, image CAPTCHA.
#   File upload (Data Verification Document) is skipped.
# Delete/Opt-Out form: same fields minus delivery, covers Delete + Opt-Out of
#   Sensitive Data + Correct (per Wiland privacy page). Gated on REMOVE_INFORMATION.
# State env var is full name — converted to 2-letter abbreviation.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper
from src.state_privacy_request_factory.state_name_abbreviation import StateAbbreviation

ACCESS_URL = "https://privacyportal.onetrust.com/webform/7567ece3-2d27-4ee0-a506-1153cb7a62b7/a1e6c0c7-b7ff-45f9-9c62-7f1eb47a6e77"
DELETE_URL = "https://privacyportal.onetrust.com/webform/7567ece3-2d27-4ee0-a506-1153cb7a62b7/718ad3c3-e1f5-4463-a301-2d6f84938588"


async def _fill_common_fields(tab, state_abbr):
    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="email", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    state_field = await tab.find(id="formField79DSARElement", raise_exc=False)
    if state_field:
        await state_field.type_text(state_abbr)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)


async def submit_access(tab, state_abbr, super_scraper):
    await tab.go_to(ACCESS_URL)
    await asyncio.sleep(7)

    delivery = await tab.find(**{"aria-label": "Electronic Delivery"}, raise_exc=False)
    if delivery:
        await delivery.click_using_js()
    await asyncio.sleep(0.5)

    await _fill_common_fields(tab, state_abbr)

    auth = await tab.find(**{"aria-label": "I Am Authorized to Submit This Request"}, raise_exc=False)
    if auth:
        await auth.click_using_js()
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit Access for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot("resources/screenshots/wiland_dry_run_access.png")
        print("Screenshot saved to resources/screenshots/wiland_dry_run_access.png")
        return

    print(
        f"\nAccess form filled. "
        f"Enter the CAPTCHA code, then click Submit. "
        f"Press Enter after confirmation..."
    )
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted Access for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for Access — verify in browser")


async def submit_delete(tab, state_abbr, super_scraper):
    await tab.go_to(DELETE_URL)
    await asyncio.sleep(7)

    await _fill_common_fields(tab, state_abbr)

    auth = await tab.find(**{"aria-label": "I Certify That I Am the Indicated Data Subject"}, raise_exc=False)
    if auth:
        await auth.click_using_js()
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit Delete/Opt-Out for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot("resources/screenshots/wiland_dry_run_delete.png")
        print("Screenshot saved to resources/screenshots/wiland_dry_run_delete.png")
        return

    print(
        f"\nDelete/Opt-Out form filled. "
        f"Enter the CAPTCHA code, then click Submit. "
        f"Press Enter after confirmation..."
    )
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted Delete/Opt-Out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for Delete/Opt-Out — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    state_abbr = StateAbbreviation[SuperScraper.STATE.upper()].value

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_access(tab, state_abbr, super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await submit_delete(tab, state_abbr, super_scraper)


asyncio.run(main())
