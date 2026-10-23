# babelstreet.com — OneTrust Angular portal DSAR form.
# Subject type and request type buttons are Angular choice cards (click_using_js).
# State and Country are both visible from page load (no dynamic reveal between them).
# Phone country code field id="vt-input-8" — type "1" for US +1.
# Confirm Email must match Email.
# formField78DSARElement = "Today's Date" — type MM/DD/YYYY.
# captchaCode is a text input (image CAPTCHA) — manual entry required in live mode.
# Rights the form exposes: Access My Data, Edit / Update My Data (correct, not automated),
# Data Portability (RIGHT_TO_ACCESS), Do Not Sell or Share + Object to Processing
# (RIGHT_TO_OPT_OUT), Delete My Data. All requested ones are multi-selected in ONE
# submission; which are selected is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   role=button aria-label="Other"       Subject type
#   role=button aria-label=<request type>  Request-type cards (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement / #confirmEmailInputDSARElement   Email / Confirm Email
#   #vt-input-8                 Phone country code (typed "1")
#   #phoneNumberDSARElement     Phone number
#   #addressDSARElement         Address
#   #cityDSARElement            City
#   #stateDSARElement           State autocomplete
#   #countryDSARElement         Country autocomplete -> "United States"
#   #formField78DSARElement     "Today's Date" (MM/DD/YYYY)
#   captchaCode                 Image CAPTCHA text input (manual entry)
#   aria-label "Click to submit form"   Submit button
import asyncio
import time
from datetime import date

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/43f52ed9-df36-44dc-94b6-ce2f8458ca29/2ddc0d62-7d6a-4de2-b5c4-9f9f68116970"

# "Object to Processing" has no exact canonical right — it rides along with RIGHT_TO_OPT_OUT.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access My Data", "Data Portability"],
    Right.RIGHT_TO_OPT_OUT: ["Do Not Sell or Share My Personal Information", "Object to Processing"],
    Right.RIGHT_TO_DELETE: ["Delete My Data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Confirm email": "//*[@id='confirmEmailInputDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "Today's date": "//*[@id='formField78DSARElement']",
}


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
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = list(dict.fromkeys(rt for right in rights for rt in RIGHT_MAP[right]))

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        other = await tab.find(**{"aria-label": "Other"}, raise_exc=False)
        if other:
            await other.click_using_js()
            await asyncio.sleep(0.5)

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

        # Phone country code vt-input-8: type "1" for US +1
        phone_cc = await tab.find(id="vt-input-8", raise_exc=False)
        if phone_cc:
            await phone_cc.type_text("1")
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

        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
        await _select_autocomplete(tab, "countryDSARElement", "United States")

        # Today's Date — type in MM/DD/YYYY format
        today_str = date.today().strftime("%m/%d/%Y")
        today_field = await tab.find(id="formField78DSARElement", raise_exc=False)
        if today_field:
            await today_field.click()
            await asyncio.sleep(0.5)
            await tab.keyboard.type_text(today_str)
            await asyncio.sleep(1)

        time.sleep(0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} ({request_types}) for {SuperScraper.EMAIL}")
            submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
            if not submit_btn:
                submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            suffix = "_delete" if Right.RIGHT_TO_DELETE in rights else ""
            await SuperScraper.screenshot(tab, f"dry_run{suffix}")
            return

        print(f"\nForm filled for {[r.name for r in rights]}.")
        print("Enter the image CAPTCHA value into the captchaCode field.")
        print("Then click Submit. Press Enter after submission completes...")
        input()

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
