# mobilityglobal.com — Mobility Global OneTrust privacy webform
# (privacyportal.onetrust.com). Deeply CASCADING Angular form — each combobox
# only populates after the previous ones are answered:
#   formField34 "Requesting Party" -> "I am making a request for myself"
#   country "Country/Jurisdiction" -> United States
#   state "State/Province" -> from STATE
#   subjectTypes "I am a" -> first available option (keyboard ArrowDown+Enter)
#   requestTypes "Select request type(s)" -> the access/know option (or first)
#   formField29 "For which division within Mobility Global ..." -> looped over
#     the three divisions: automotiveMastermind / Polk Automotive Solutions /
#     Market Scan (per the maintainer's note "one for each division").
# Per that note, every right except Do Not Sell works on THIS ("Right to
# Access") form, so the specific rights are spelled out in requestDetails and
# this is one submission per division. Do Not Sell has its own separate webform:
#   https://privacyportal.onetrust.com/webform/87c0b060-447b-4c56-a99e-6fc89bd3c7e4/16d2d526-dd07-4f31-b8ec-ce2451c0c373
# Fields: email, first/last, formField49 address, formField50 city, formField51
# zip, formField39 title (skipped), formField38 url (skipped), requestDetails.
# reCAPTCHA v2 requires a manual solve per pass.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/87c0b060-447b-4c56-a99e-6fc89bd3c7e4/c5ce1867-0472-4257-953c-7ed388ede130"
DIVISIONS = ["automotiveMastermind", "Polk Automotive Solutions", "Market Scan"]


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


async def _combobox(tab, field_id, search_text=None):
    """Type search_text (if given) and pick the matching role=option; otherwise
    open the combobox and pick the first option via keyboard."""
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.5)
    if search_text:
        await field.execute_script("this.value=''; this.dispatchEvent(new Event('input',{bubbles:true}));")
        await tab.keyboard.type_text(search_text)
        await asyncio.sleep(2)
        for opt in await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip().lower()
            if search_text.lower() in label:
                await opt.click_using_js()
                await asyncio.sleep(0.5)
                return
    await tab.keyboard.press(Key.ARROWDOWN)
    await asyncio.sleep(0.3)
    await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)


async def submit_request(tab, division, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    await _combobox(tab, "formField34DSARElement", "myself")
    await _combobox(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    await _combobox(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(1)
    await _combobox(tab, "subjectTypesDSARElement")          # first available "I am a"
    await asyncio.sleep(1)
    await _combobox(tab, "requestTypesDSARElement", "access")  # falls back to first
    await asyncio.sleep(1)
    await _combobox(tab, "formField29DSARElement", division)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("formField49DSARElement", SuperScraper.ADDRESS),
        ("formField50DSARElement", SuperScraper.CITY),
        ("formField51DSARElement", SuperScraper.ZIP_CODE),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        rights = (
            f"I am a {SuperScraper.STATE} resident exercising my rights under the Minnesota "
            f"Consumer Data Privacy Act with respect to the {division} division. I request: "
            f"to know/access the personal information you hold about me, its sources and the "
            f"parties it has been disclosed to; to correct any inaccurate personal information; "
            f"and to opt out of targeted advertising and profiling"
        )
        if SuperScraper.REMOVE_INFORMATION:
            rights += "; and deletion of all personal information you hold about me"
        rights += ". (Do Not Sell / opt-out of sale is submitted via the separate webform.)"
        await details.type_text(rights)

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/mobilityglobal_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit access/correct request for division '{division}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for division '{division}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for i, division in enumerate(DIVISIONS):
            await submit_request(tab, division, f"div{i}", super_scraper)


asyncio.run(main())
