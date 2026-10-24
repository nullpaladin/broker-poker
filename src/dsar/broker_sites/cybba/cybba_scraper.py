# cybba.com — OneTrust privacy webform (cybba-requests.my.onetrust.com).
# Angular form. "I am a (an)" is a role="listbox" (subjectTypesDSARElement):
# Customer / Contractor / Employee — "Customer" selected. "Select request
# type(s)" is a role="listbox" (requestTypesDSARElement): "Info Request",
# "Data Deletion", "Do Not Sell My Information". Treated as one submission per
# right for safety.
# Country geo-prefills to "United States"; State is an autocomplete combobox.
# requestDetailsDSARElement is a required free-text box. Selecting "Info
# Request" reveals an optional (no asterisk) "Which would you like to receive?"
# combobox — left at its default. Optional "Loyalty ID" field and an optional
# supporting-document file upload are left empty. Submission is gated by a
# distorted-text image CAPTCHA (captchaCode), not reCAPTCHA — the form is
# filled completely and the code is left for manual entry.
# **CAPTCHA solution required**
#
# Page elements:
#   #countryDSARElement            Country autocomplete -> "United States"
#   [role=option][aria-label="Customer"]   "I am a (an)" listbox (subjectTypesDSARElement) -> Customer
#   [role=option][aria-label=...]  "Select request type(s)" listbox (requestTypesDSARElement), see RIGHT_MAP
#   #stateDSARElement              State autocomplete
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   Name / Email
#   #requestDetailsDSARElement     Required free-text details
#   #captchaCode                   Image CAPTCHA (manual entry)
#   #dsar-webform-submit-button    Submit
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://cybba-requests.my.onetrust.com/webform/a4a1351e-d293-4305-bde4-b9cf8f5c0989/f89c576a-b5c6-498e-bad5-698f084ffd30"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Info Request",
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell My Information",
    Right.RIGHT_TO_DELETE: "Data Deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _field_value(field):
    return str((await js_utils.js_eval(field, "return this.value;")) or "").strip()


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


async def submit_request(tab, right, right_label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(0.5)
    await _click_listbox_option(tab, "Customer")
    if not await _click_listbox_option(tab, right_label):
        print(f"{super_scraper.OOPS} Right '{right_label}' not found")
        return
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(SuperScraper.request_statement([right], broker="Cybba"))

    time.sleep(0.5)
    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right.name}'. Enter the CAPTCHA code into captchaCode, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
