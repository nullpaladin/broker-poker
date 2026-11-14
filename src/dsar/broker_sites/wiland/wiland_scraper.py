# wiland.com — Two separate OneTrust forms (no country/state autocomplete).
# Access form: Delivery = Electronic Delivery (default button), name, email
#   (id="email" not emailDSARElement), address, city, state (2-letter abbr via
#   formField79DSARElement), zip, authorization checkbox, image CAPTCHA.
#   File upload (Data Verification Document) is skipped.
# Delete/Opt-Out form: same fields minus delivery, covers Delete + Opt-Out of
#   Sensitive Data + Correct (per Wiland privacy page). The scraper selects no request
#   type on it, so it is mapped to Right.RIGHT_TO_DELETE only.
# Which forms run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# State env var is full name — converted to 2-letter abbreviation.
#
# Page elements (both forms):
#   [aria-label="Electronic Delivery"]   Delivery button (Access form only)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #email                    Email
#   #addressDSARElement / #cityDSARElement / #zipDSARElement   Address / City / Zip
#   #formField79DSARElement   State (2-letter abbreviation)
#   [aria-label="I Am Authorized to Submit This Request"]       Authorization (Access form)
#   [aria-label="I Certify That I Am the Indicated Data Subject"]   Certification (Delete form)
#   #captchaCode              Image CAPTCHA code (manual entry)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

ACCESS_URL = "https://privacyportal.onetrust.com/webform/7567ece3-2d27-4ee0-a506-1153cb7a62b7/a1e6c0c7-b7ff-45f9-9c62-7f1eb47a6e77"
DELETE_URL = "https://privacyportal.onetrust.com/webform/7567ece3-2d27-4ee0-a506-1153cb7a62b7/718ad3c3-e1f5-4463-a301-2d6f84938588"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ACCESS_URL,
    Right.RIGHT_TO_DELETE: DELETE_URL,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Two separate forms; their headings are unrecorded and the Delete form's request type is never selected.)

DELETE_FIELD_XPATHS = {
    "First name": "//input[@id='firstNameDSARElement']",
    "Last name": "//input[@id='lastNameDSARElement']",
    "Email": "//input[@id='email']",
    "Address": "//input[@id='addressDSARElement']",
    "City": "//input[@id='cityDSARElement']",
    "State": "//input[@id='formField79DSARElement']",
    "Zip": "//input[@id='zipDSARElement']",
}


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


async def submit_access(tab, state_abbr, super_scraper, right):
    await tab.go_to(RIGHT_MAP[right])
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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            "First name": "//input[@id='firstNameDSARElement']",
            "Last name": "//input[@id='lastNameDSARElement']",
            "Email": "//input[@id='email']",
            "Address": "//input[@id='addressDSARElement']",
            "City": "//input[@id='cityDSARElement']",
            "State": "//input[@id='formField79DSARElement']",
            "Zip": "//input[@id='zipDSARElement']",
        })

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_access")
        return

    print(
        f"\nAccess form filled. "
        f"Enter the CAPTCHA code, then click Submit. "
        f"Press Enter after confirmation..."
    )
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def submit_delete(tab, state_abbr, super_scraper, right):
    await tab.go_to(RIGHT_MAP[right])
    await asyncio.sleep(7)

    await _fill_common_fields(tab, state_abbr)

    auth = await tab.find(**{"aria-label": "I Certify That I Am the Indicated Data Subject"}, raise_exc=False)
    if auth:
        await auth.click_using_js()
    await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, DELETE_FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_delete")
        return

    print(
        f"\nDelete/Opt-Out form filled. "
        f"Enter the CAPTCHA code, then click Submit. "
        f"Press Enter after confirmation..."
    )
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

    state_abbr = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            if right == Right.RIGHT_TO_ACCESS:
                await submit_access(tab, state_abbr, super_scraper, right)
            else:
                await submit_delete(tab, state_abbr, super_scraper, right)


asyncio.run(main())
