# dspolitical.com — OneTrust privacy webform (privacyportal.onetrust.com).
# Angular form. "I am submitting this information on behalf of:" is a
# role="listbox" (subjectTypesDSARElement) with options Myself / My Household —
# "Myself" is selected. "Select the Right You Want to Exercise:" is a
# role="listbox" (requestTypesDSARElement) with options "Access My Information",
# "Delete My Information", "Do Not Sell My Information" — single-select, so one
# submission per right: Access + Do Not Sell unconditional, Delete gated on
# REMOVE_INFORMATION.
# Country of residence is geo-prefilled to "United States"; State is an
# autocomplete combobox. reCAPTCHA v2 requires a manual solve before submit.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/2de5f42a-3bbb-4bcf-867b-251b00739ee1/a8b3a307-cdeb-46d5-bb3c-7733424b01ff"

RIGHT_MAP = {
    "access": [("Access My Information", "access")],
    "opt_out_sale_share": [("Do Not Sell My Information", "optout")],
    "delete": [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


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


async def submit_request(tab, right_label, label, super_scraper):
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
        await details.type_text(
            f"I am a {SuperScraper.STATE} resident exercising my privacy rights under the "
            f"{SuperScraper.LAW_FULL_NAME or 'applicable state and federal privacy law'}. "
            f"Request: {right_label}."
        )

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/dspolitical_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{right_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, label in requests:
            await submit_request(tab, right_label, label, super_scraper)


asyncio.run(main())
