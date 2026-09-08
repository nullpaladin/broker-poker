# viantic.com — OneTrust privacy webform (privacyportal.onetrust.com).
# Angular form. Fields: countryDSARElement (autocomplete combobox, prefilled
# "United States"), stateDSARElement (autocomplete combobox), firstNameDSARElement,
# lastNameDSARElement, emailDSARElement, and an "I understand the above
# statements" attestation checkbox (formField86DSARElement).
# "Please select the type of request" is a single-select group of role="option"
# divs keyed by aria-label: "Request for Deletion", "Correct My Personal
# Information", "Access My Personal Information (Request to Know)". One
# submission per right — Access unconditional, Delete gated on
# REMOVE_INFORMATION, Correct skipped (nothing concrete to correct).
# reCAPTCHA v2 requires a manual solve before submit.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/18c06089-a9ec-473c-a6d8-23d20fea46af/43201dea-88d7-44cd-9142-e5b4f485e428"

RIGHT_MAP = {
    "access": [("Access My Personal Information (Request to Know)", "access")],
    "delete": [("Request for Deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


async def _select_autocomplete(tab, field_id, search_text):
    """OneTrust autocomplete combobox: type the term, then click the matching
    role=option. Verifies via the live .value property and retries once."""
    for attempt in range(2):
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

        opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
        clicked = False
        for opt in opts:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip()
            if label.lower() == search_text.lower():
                await opt.click_using_js()
                clicked = True
                break
        if not clicked:
            # keyboard fallback — highlight first suggestion and commit it
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.6)

        field = await tab.find(id=field_id, raise_exc=False)
        if field and (await _field_value(field)).lower() == search_text.lower():
            return


async def submit_request(tab, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    req = await tab.find(**{"aria-label": aria_label, "role": "option"}, raise_exc=False)
    if not req:
        print(f"{super_scraper.OOPS} Request type '{aria_label}' not found")
        return
    await req.click_using_js()
    await asyncio.sleep(1)

    for fid, value in [
        ("firstNameDSARElement", SuperScraper.FIRST_NAME),
        ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ("emailDSARElement", SuperScraper.EMAIL),
    ]:
        el = await tab.find(id=fid, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)

    # "I understand the above statements." is a role="listbox" with a single
    # role="option" aria-label="Agree" — click it like a request-type button.
    agree = await tab.find(**{"aria-label": "Agree", "role": "option"}, raise_exc=False)
    if agree:
        await agree.click_using_js()
        await asyncio.sleep(0.3)

    time.sleep(0.5)
    submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
    if submit_btn:
        await submit_btn.scroll_into_view()
    await SuperScraper.screenshot(tab, f"resources/screenshots/viantic_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{aria_label}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{aria_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{aria_label}' — verify in browser")


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
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())
