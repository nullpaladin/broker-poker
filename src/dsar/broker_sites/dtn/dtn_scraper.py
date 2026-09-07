# dtn.com — Gravity Forms privacy request form, no name/address section
# beyond zip. All rights are one multi-select checkbox group in a single
# submission: Do Not Sell/Share, Limit Sensitive PI, Access/Correct, Object
# to Processing, Data Portability, Withdraw Consent unconditionally; Delete
# gated on REMOVE_INFORMATION. "Other" is left unchecked (its textarea is
# only actually required by Gravity Forms' conditional logic when "Other"
# itself is selected). In place of a CAPTCHA, the form asks a randomized
# arithmetic question ("What is X+Y?") via a <select> of multiple-choice
# answers — solved dynamically by parsing the placeholder text and picking
# the option whose value matches the computed sum. A required attestation
# checkbox ("Please verify: ...true and accurate...") is checked. A OneTrust
# cookie-consent modal ("Privacy Preference Center") auto-opens over the form
# on load and intercepts clicks until dismissed via its aria-label="Close" (×)
# button — its "Accept All Cookies"/"Confirm My Choices" buttons are red
# herrings (hidden/inert on this page).
import asyncio
import re

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.dtn.com/do-not-sell-my-information-form/"

CHECKBOXES = [
    "input_36.2",  # Do Not Sell or Share My Personal Information
    "input_36.3",  # Limit the Disclosure or Use of My Sensitive Personal Information
    "input_36.4",  # Access to and/or correction of My Personal Data
    "input_36.5",  # Objection or restriction to the processing of My Personal Data
    "input_36.6",  # Transfer my Personal Data to another party
    "input_36.7",  # Withdrawal of my consent previously provided to DTN
]
DELETE_CHECKBOX = "input_36.1"  # Delete My Personal Data


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        close_modal = await tab.find(**{"aria-label": "Close"}, timeout=5, raise_exc=False)
        if close_modal:
            await close_modal.click()
            await asyncio.sleep(1)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_1']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_2']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_3']", text=SuperScraper.EMAIL, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_4']", text=SuperScraper.PHONE_NUMBER, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_17']", text=SuperScraper.ZIP_CODE, sleep=0.2)

        checkboxes = list(CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for name in checkboxes:
            box = await tab.find(name=name, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        placeholder = await tab.execute_script(
            "var o = document.querySelector('#input_47_42 option[selected]'); return o ? o.textContent : '';"
        )
        placeholder_text = placeholder.get("result", {}).get("result", {}).get("value", "") if isinstance(placeholder, dict) else ""
        match = re.search(r"(\d+)\s*\+\s*(\d+)", placeholder_text)
        if match:
            answer = str(int(match.group(1)) + int(match.group(2)))
            await tab.execute_script(
                f'var s = document.querySelector("select#input_47_42"); s.value = "{answer}"; s.dispatchEvent(new Event("change"));'
            )
        else:
            print(f"{super_scraper.OOPS} Could not parse the arithmetic question '{placeholder_text}'")

        verify_box = await tab.find(id="choice_47_31_1", raise_exc=False)
        if verify_box:
            await verify_box.click()

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/dtn_dry_run.png")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
