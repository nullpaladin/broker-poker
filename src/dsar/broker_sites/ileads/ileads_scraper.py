# ileads.com — iLeads "Submit Request" form (ileads.com/submitrequest/), a
# Contact Form 7 form. Real-estate lead data keyed on a PROPERTY address.
# Server-rendered. "checkbox-datatypes[]" is a multi-select checkbox group
# (one combined submission): "Data Access", "Right to Know", "Do Not Sell My
# Information", "Data Deletion". Which boxes get ticked is decided only by
# SuperScraper.rights_to_exercise.
# Fields: fname, lname, proaddress (Property Address), states-list (native
# <select>, 2-letter values), cityname, zipaddress, email, phone-number.
# A Cloudflare Turnstile gates submission — the form is filled and left for a
# manual solve.  **CAPTCHA solution required**
#
# Page elements:
#   input[name='checkbox-datatypes[]']  request-type checkboxes (values in RIGHT_MAP)
#   fname / lname                       First / Last name
#   proaddress                          Property Address
#   states-list                         State (native <select>, 2-letter values)
#   cityname / zipaddress               City / ZIP
#   email / phone-number                Email / Phone
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://ileads.com/submitrequest/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Data Access", "Right to Know"],
    Right.RIGHT_TO_OPT_OUT: ["Do Not Sell My Information"],
    Right.RIGHT_TO_DELETE: ["Data Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        values = [v for right in rights for v in RIGHT_MAP[right]]
        for value in values:
            box = await tab.find(
                xpath=f"//input[@name='checkbox-datatypes[]' and @value={value!r}]", raise_exc=False
            )
            if box:
                await js_utils.js_check(box)
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
            await js_utils.select_native_option(state_select, value=abbr, dispatch=("change",))

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "Request filled but NOT submitted — a Cloudflare Turnstile must be solved "
            "manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the Turnstile, click Submit Request, then press Enter once confirmed...")
            input()
            print(f"Submitted {', '.join(r.name for r in rights)} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
