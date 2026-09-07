# cybba.com — OneTrust privacy webform (cybba-requests.my.onetrust.com).
# Angular form. "I am a (an)" is a role="listbox" (subjectTypesDSARElement):
# Customer / Contractor / Employee — "Customer" selected. "Select request
# type(s)" is a role="listbox" (requestTypesDSARElement): "Info Request",
# "Data Deletion", "Do Not Sell My Information". Treated as one submission per
# right for safety: Info Request (access) + Do Not Sell unconditional, Data
# Deletion gated on REMOVE_INFORMATION.
# Country geo-prefills to "United States"; State is an autocomplete combobox.
# requestDetailsDSARElement is a required free-text box. Selecting "Info
# Request" reveals an optional (no asterisk) "Which would you like to receive?"
# combobox — left at its default. Optional "Loyalty ID" field and an optional
# supporting-document file upload are left empty. Submission is gated by a
# distorted-text image CAPTCHA (captchaCode), not reCAPTCHA — the form is
# filled completely and the code is left for manual entry.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://cybba-requests.my.onetrust.com/webform/a4a1351e-d293-4305-bde4-b9cf8f5c0989/f89c576a-b5c6-498e-bad5-698f084ffd30"

RIGHT_MAP = {
    "access": [("Info Request", "access")],
    "opt_out_sale_share": [("Do Not Sell My Information", "optout")],
    "delete": [("Data Deletion", "delete")],
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
        await details.type_text(
            f"I am a {SuperScraper.STATE} resident exercising my privacy rights. "
            f"Request: {right_label}."
        )

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/cybba_dry_run_{label}.png")
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
