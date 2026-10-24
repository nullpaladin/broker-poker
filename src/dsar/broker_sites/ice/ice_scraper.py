# ice.com (Intercontinental Exchange) — custom OneTrust Angular DSAR portal.
# Subject: "Customer". Country: "United States" → State: "Minnesota" (both autocomplete).
# Line of Service: "Data Services". Request type is SINGLE-SELECT — one submission per right.
# Fields: subjectTypesDSARElement, countryDSARElement, stateDSARElement (appears after country),
#   formField85DSARElement (Line of Service), requestTypesDSARElement,
#   First Name / Last Name via aria-label, emailDSARElement,
#   formField82DSARElement (phone, optional), requestDetailsDSARElement (textarea).
# CAPTCHA: id="captchaCode", BotDetect 6-char alphanumeric, manual entry per submission.
# Request types offered: Info Request, Update Data (not automated), Object to Processing,
# Data Portability, Restrict Processing, Data Deletion. Which run is decided only by
# SuperScraper.rights_to_exercise.
#
# Page elements:
#   #subjectTypesDSARElement      Subject type -> "Customer"
#   #countryDSARElement           Country -> "United States"
#   #stateDSARElement             State (appears after country) -> configured STATE
#   #formField85DSARElement       Line of Service -> "Data Services"
#   #requestTypesDSARElement      Request type (single-select)
#   [aria-label=First Name] / [aria-label=Last Name]   First / Last name
#   #emailDSARElement             Email
#   #formField82DSARElement       Phone (optional)
#   #requestDetailsDSARElement    Request details textarea
#   #captchaCode                  CAPTCHA code (BotDetect, manual entry)
#   "Submit" button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://ice-privacy.my.onetrust.com/webform/cca3ac39-00b6-45f4-819b-bec660878b46/124d1692-407b-4384-9036-bef3ece530e3"

# "Update Data" (correct) is not automated. Entries are (request type shown on the form, screenshot label).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        ("Info Request", "access"),
        ("Data Portability", "portability"),
    ],
    Right.RIGHT_TO_OPT_OUT: [
        ("Object to Processing", "object"),
        ("Restrict Processing", "restrict"),
    ],
    Right.RIGHT_TO_DELETE: [("Data Deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Only some of the request-type options are recorded, so no inventory is built.)

FIELD_XPATHS = {
    "First name": "//*[@aria-label='First Name']",
    "Last name": "//*[@aria-label='Last Name']",
    "Email": "//*[@id='emailDSARElement']",
    "Phone": "//*[@id='formField82DSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _autocomplete_select(tab, field_id, search, option_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return False
    await field.click()
    if search:
        await field.type_text(search)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for o in opts:
        if await o.is_visible():
            t = await o.text
            if t and t.strip() == option_text:
                await o.click()
                await asyncio.sleep(1)
                return True
    for o in opts:
        if await o.is_visible():
            await o.click()
            await asyncio.sleep(1)
            return True
    return False


async def _submit_request(tab, right, req_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(8)

    await _autocomplete_select(tab, "subjectTypesDSARElement", "", "Customer")
    await _autocomplete_select(tab, "countryDSARElement", "United States", "United States")
    await asyncio.sleep(2)

    await _autocomplete_select(tab, "stateDSARElement", SuperScraper.STATE, SuperScraper.STATE)
    await _autocomplete_select(tab, "formField85DSARElement", "", "Data Services")
    await _autocomplete_select(tab, "requestTypesDSARElement", "", req_type)

    first = await tab.find(**{"aria-label": "First Name"}, raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    time.sleep(0.3)

    last = await tab.find(**{"aria-label": "Last Name"}, raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    time.sleep(0.3)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    time.sleep(0.3)

    phone = await tab.find(id="formField82DSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)
    time.sleep(0.3)

    details_field = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details_field:
        await details_field.type_text(SuperScraper.request_statement([right], broker="ICE Data Services"))
    time.sleep(0.3)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({req_type}) for {SuperScraper.EMAIL}"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
        return

    captcha_field = await tab.find(id="captchaCode", raise_exc=False)
    if captcha_field:
        await captcha_field.scroll_into_view()
    print(f"\nForm filled for '{label}'. Enter the 6-char CAPTCHA code, then press Enter.")
    code = input("CAPTCHA code: ").strip()
    if captcha_field:
        await captcha_field.type_text(code)
    time.sleep(0.3)

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(5)

    print(f"Submitted '{right.name}' ({req_type}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    opts = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=opts) as browser:
        tab = await browser.start()
        for right in rights:
            for req_type, label in RIGHT_MAP[right]:
                await _submit_request(tab, right, req_type, label, super_scraper)


asyncio.run(main())
