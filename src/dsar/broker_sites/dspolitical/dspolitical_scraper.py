# dspolitical.com — OneTrust privacy webform (privacyportal.onetrust.com).
# Angular form. "I am submitting this information on behalf of:" is a
# role="listbox" (subjectTypesDSARElement) with options Myself / My Household —
# "Myself" is selected. "Select the Right You Want to Exercise:" is a
# role="listbox" (requestTypesDSARElement) with options "Access My Information",
# "Delete My Information", "Do Not Sell My Information" — single-select, so one
# submission per right. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# Country of residence is geo-prefilled to "United States"; State is an
# autocomplete combobox. reCAPTCHA v2 requires a manual solve before submit.
# **CAPTCHA solution required**
#
# Page elements:
#   [role=option][aria-label="Myself"]   Subject type listbox option (subjectTypesDSARElement)
#   [role=option][aria-label=<right>]    "Select the Right You Want to Exercise" option
#                                        (requestTypesDSARElement; labels in RIGHT_MAP)
#   #countryDSARElement / #stateDSARElement   Country / State autocomplete comboboxes
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #addressDSARElement / #cityDSARElement / #zipDSARElement   Address / City / Zip
#   #emailDSARElement / #phoneNumberDSARElement   Email / Phone
#   #requestDetailsDSARElement           Request details textarea
#   #dsar-webform-submit-button          Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/2de5f42a-3bbb-4bcf-867b-251b00739ee1/a8b3a307-cdeb-46d5-bb3c-7733424b01ff"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access My Information", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do Not Sell My Information", "optout")],
    Right.RIGHT_TO_DELETE: [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _field_value(field):
    return ((await js_utils.js_eval(field, "return this.value;")) or "").strip()


async def _select_autocomplete(tab, field_id, search_text):
    for _ in range(2):
        field = await tab.find(id=field_id, raise_exc=False)
        if not field:
            return
        if (await _field_value(field)).lower() == search_text.lower():
            return
        await field.click()
        await field.execute_script(
            "this.value=''; this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await tab.keyboard.type_text(search_text)
        await asyncio.sleep(2.5)
        clicked = False
        for opt in await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip()
            if label.lower() == search_text.lower():
                await opt.click_using_js()
                clicked = True
                break
        if not clicked:
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.6)
        field = await tab.find(id=field_id, raise_exc=False)
        if field and (await _field_value(field)).lower() == search_text.lower():
            return


async def _click_listbox_option(tab, aria_label):
    opt = await tab.find(**{"aria-label": aria_label, "role": "option"}, raise_exc=False)
    if opt:
        await opt.click_using_js()
        await asyncio.sleep(0.4)
        return True
    return False


async def submit_request(tab, right, right_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _click_listbox_option(tab, "Myself")
    if not await _click_listbox_option(tab, right_label):
        print(f"{super_scraper.OOPS} Right '{right_label}' not found")
        return

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(0.5)
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("addressDSARElement", SuperScraper.ADDRESS),
        ("cityDSARElement", SuperScraper.CITY),
        ("zipDSARElement", SuperScraper.ZIP_CODE),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("phoneNumberDSARElement", SuperScraper.PHONE_NUMBER),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(SuperScraper.request_statement([right], broker="DS Political"))

    time.sleep(0.5)
    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' ({right_label}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' ({right_label}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
            for right_label, label in RIGHT_MAP[right]:
                await submit_request(tab, right, right_label, label, super_scraper)


asyncio.run(main())
