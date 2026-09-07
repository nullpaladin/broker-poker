# ileads.com — iLeads "Submit Request" form (ileads.com/submitrequest/), a
# Contact Form 7 form. Real-estate lead data keyed on a PROPERTY address.
# Server-rendered. "checkbox-datatypes[]" is a multi-select checkbox group
# (one combined submission): "Data Access", "Right to Know", "Do Not Sell My
# Information" unconditionally; "Data Deletion" gated on REMOVE_INFORMATION.
# Fields: fname, lname, proaddress (Property Address), states-list (native
# <select>, 2-letter values), cityname, zipaddress, email, phone-number.
# A Cloudflare Turnstile gates submission — the form is filled and left for a
# manual solve.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://ileads.com/submitrequest/"

RIGHT_MAP = {
    "access": ["Data Access", "Right to Know"],
    "opt_out_sale_share": ["Do Not Sell My Information"],
    "delete": ["Data Deletion"],
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
        await asyncio.sleep(5)

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        rights = [entry for code in codes for entry in RIGHT_MAP[code]]
        for value in rights:
            box = await tab.find(
                xpath=f"//input[@name='checkbox-datatypes[]' and @value={value!r}]", raise_exc=False
            )
            if box:
                await box.execute_script("if (!this.checked) this.click();")
                await asyncio.sleep(0.1)

        for name, value in [
            ("fname", SuperScraper.FIRST_NAME),
            ("lname", SuperScraper.LAST_NAME),
            ("proaddress", SuperScraper.ADDRESS),
            ("cityname", SuperScraper.CITY),
            ("zipaddress", SuperScraper.ZIP_CODE),
            ("email", SuperScraper.EMAIL),
            ("phone-number", SuperScraper.PHONE_NUMBER),
        ]:
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2
            )

        state_select = await tab.find(name="states-list", raise_exc=False)
        if state_select:
            abbr = SuperScraper.STATE_ABBREVIATED
            await state_select.execute_script(
                f"const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
                f"s.call(this,{abbr!r});this.dispatchEvent(new Event('change',{{bubbles:true}}));"
            )

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/ileads_dry_run.png")
        print(
            "Request filled but NOT submitted — a Cloudflare Turnstile must be solved "
            "manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the Turnstile, click Submit Request, then press Enter once confirmed...")
            input()


asyncio.run(main())
