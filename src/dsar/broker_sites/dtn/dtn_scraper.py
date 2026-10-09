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

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.dtn.com/do-not-sell-my-information-form/"

RIGHT_MAP = {
    "access": ["input_36.4"],
    "limit_sensitive_pi": ["input_36.3"],
    "portability": ["input_36.6"],
    "opt_out_sale_share": ["input_36.2", "input_36.5", "input_36.7"],
    "delete": ["input_36.1"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        checkboxes = [entry for code in codes for entry in RIGHT_MAP[code]]
        for name in checkboxes:
            box = await tab.find(name=name, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        placeholder_text = await SuperScraper.js_eval(
            tab,
            "var o = document.querySelector('#input_47_42 option[selected]'); return o ? o.textContent : '';",
        )
        answer = SuperScraper.solve_math_captcha(placeholder_text or "")
        if answer is not None:
            math_select = await tab.find(id="input_47_42", raise_exc=False)
            if math_select:
                await SuperScraper.select_native_option(math_select, value=answer)
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
