# iqviadigital.com — OneTrust privacy webform (privacyportal.onetrust.com),
# IQVIA's cascading DSAR form.
# Distinctive field ids: requestTypesDSARElement ("CHOOSE YOUR RIGHTS HERE:"),
# subjectTypesDSARElement ("RELATIONSHIP WITH IQVIA"), formField87DSARElement
# ("YOUR INTERACTION WITH IQVIA", free text), firstNameDSARElement ("YOUR NAME",
# a full-name field), formField83DSARElement (phone), emailDSARElement,
# countryDSARElement (NOT geo-prefilled — set explicitly), formField79DSARElement
# (full address), formField81DSARElement (city), formField82DSARElement (zip).
# stateDSARElement ("STATE", required) is a combobox that only renders after
# COUNTRY is set.
# requestTypesDSARElement / subjectTypesDSARElement / countryDSARElement are all
# OneTrust autocomplete comboboxes (type, then click the matching role=option).
# The right options carry curly quotes, so they are matched by a lowercase
# substring keyword rather than exact text. One submission per right — Access,
# Opt-Out of Sale/Sharing, Opt-Out of Targeted Advertising and Limit Sensitive
# PI unconditional; Delete gated on REMOVE_INFORMATION. Relationship answered
# "None" (no Healthcare Provider / Study Participant / Employee / Agent applies).
# reCAPTCHA v2 requires a manual solve before submit.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/07e8dc4d-6686-403e-9b11-39fe7347d2f4/2f999bd2-c826-498c-a504-894eaf543b6f"

# (substring keyword to match the option, screenshot label)
REQUESTS = [
    ("access my personal information", "access"),
    ("opt-out of the sale", "optout_sale"),
    ("targeted advertising", "optout_ads"),
    ("limit the use of my", "limit_sensitive"),
]
DELETE_REQUEST = ("delete my personal information", "delete")


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


async def _select_combobox(tab, field_id, type_text, match_substr=None):
    """OneTrust autocomplete combobox — type, then click the role=option whose
    label matches (exact on `type_text`, or containing `match_substr`)."""
    needle = (match_substr or type_text).lower()
    for _ in range(2):
        field = await tab.find(id=field_id, raise_exc=False)
        if not field:
            return
        if not match_substr and (await _field_value(field)).lower() == type_text.lower():
            return
        await field.click()
        await field.execute_script(
            "this.value=''; this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await tab.keyboard.type_text(type_text)
        await asyncio.sleep(2.5)
        clicked = False
        for opt in await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip().lower()
            if needle in label:
                await opt.click_using_js()
                clicked = True
                break
        if not clicked:
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.6)
        if match_substr:
            return
        field = await tab.find(id=field_id, raise_exc=False)
        if field and (await _field_value(field)).lower() == type_text.lower():
            return


async def submit_request(tab, right_keyword, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(8)

    await _select_combobox(tab, "requestTypesDSARElement", "the right to", match_substr=right_keyword)
    await _select_combobox(tab, "subjectTypesDSARElement", "None")
    await _select_combobox(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    # STATE combobox only renders after COUNTRY is set
    await _select_combobox(tab, "stateDSARElement", SuperScraper.STATE)

    interaction = await tab.find(id="formField87DSARElement", raise_exc=False)
    if interaction:
        await interaction.type_text(
            "I am a consumer whose personal data IQVIA Digital may have processed "
            "through its advertising products. I have no direct account relationship."
        )

    for fid, value in [
        ("firstNameDSARElement", f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}"),
        ("formField83DSARElement", SuperScraper.PHONE_NUMBER),
        ("emailDSARElement", SuperScraper.EMAIL),
        ("formField79DSARElement", SuperScraper.ADDRESS),
        ("formField81DSARElement", SuperScraper.CITY),
        ("formField82DSARElement", SuperScraper.ZIP_CODE),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await tab.take_screenshot(f"resources/screenshots/iqviadigital_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/iqviadigital_dry_run_{label}.png")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right_keyword}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{right_keyword}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right_keyword}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right_keyword}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2600")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_keyword, label in requests:
            await submit_request(tab, right_keyword, label, super_scraper)


asyncio.run(main())
