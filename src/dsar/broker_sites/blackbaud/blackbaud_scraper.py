# blackbaud.com — custom OneTrust Angular portal DSAR form.
# formField100DSARElement = Yes/No listbox "Are you an authorized agent?" — click "No".
# Country + State: independent autocompletes.
# Subject type "Consumer" and request type buttons are Angular choice cards (click_using_js).
# Request types available after MN (and other qualifying states) selected:
#   Data Subject Access Request, Data Subject Opt-out Request,
#   Data Subject Correction Request (not automated), Data Subject Deletion Request.
# All requested rights go in ONE submission; which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# No phone field. confirmEmailInputDSARElement must match emailDSARElement.
# formFields 93/98/101/102 are informational display text — no user input needed.
# captchaCode is an image CAPTCHA — manual entry required in live mode.
#
# Page elements:
#   [aria-label="No"]            "Are you an authorized agent?" -> No
#   #countryDSARElement          Country (autocomplete)
#   #stateDSARElement            State (autocomplete)
#   [aria-label="Consumer"]      Subject type choice card
#   [aria-label=<entry>]         Request type choice cards (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement            Email
#   #confirmEmailInputDSARElement  Confirm email
#   #addressDSARElement / #cityDSARElement / #zipDSARElement   Address / City / ZIP
#   #captchaCode                 Image CAPTCHA (manual)
#   [aria-label="Click to submit form"]  Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://blackbaud-privacy.my.onetrust.com/webform/170c909c-5ed2-49f1-a59c-2a44be2f6f27/de22df57-d96c-480a-afb0-ac090b928192"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Data Subject Access Request"],
    Right.RIGHT_TO_OPT_OUT: ["Data Subject Opt-out Request"],
    Right.RIGHT_TO_DELETE: ["Data Subject Deletion Request"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)


async def _select_autocomplete(tab, field_id, search_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(search_text)
    await asyncio.sleep(2)
    opts = await tab.find(text=search_text, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            break
    await asyncio.sleep(1)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = list(dict.fromkeys(rt for r in rights for rt in RIGHT_MAP[r]))

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        # "Are you an authorized agent?" — select No
        no_btn = await tab.find(**{"aria-label": "No"}, raise_exc=False)
        if no_btn:
            await no_btn.click_using_js()
            await asyncio.sleep(0.5)

        await _select_autocomplete(tab, "countryDSARElement", "United States")
        await asyncio.sleep(1)
        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
        await asyncio.sleep(1)

        consumer = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
        if consumer:
            await consumer.click_using_js()
            await asyncio.sleep(1)

        for req_type in request_types:
            btn = await tab.find(**{"aria-label": req_type}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        confirm = await tab.find(id="confirmEmailInputDSARElement", raise_exc=False)
        if confirm:
            await confirm.type_text(SuperScraper.EMAIL)

        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        zipcode = await tab.find(id="zipDSARElement", raise_exc=False)
        if zipcode:
            await zipcode.type_text(SuperScraper.ZIP_CODE)

        time.sleep(0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": "//input[@id='firstNameDSARElement']",
                "Last name": "//input[@id='lastNameDSARElement']",
                "Email": "//input[@id='emailDSARElement']",
                "Confirm email": "//input[@id='confirmEmailInputDSARElement']",
                "Address": "//input[@id='addressDSARElement']",
                "City": "//input[@id='cityDSARElement']",
                "Zip": "//input[@id='zipDSARElement']",
            })

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
            if not submit_btn:
                submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        print(f"\nForm filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}.")
        print("Enter the image CAPTCHA value into the captchaCode field.")
        print("Then click Submit. Press Enter after submission completes...")
        input()

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
