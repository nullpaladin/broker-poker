# xcelerated.com — "Unsubscribe" / opt-out form (xcelerated.com/unsubscribe/),
# a Fluent Forms form.
# Right to Opt-Out ONLY — the site says every other right (Access, etc.) must be
# exercised by POSTAL MAIL, which is arguably non-compliant with Minn. Stat.
# 325M.14 subd. 4(b). info@xcelerated.com is not for privacy requests
# (phone 877.236.9155).
# Server-rendered. The "checkbox[]" group is four opt-out categories — ALL are
# checked (Sale of personal information / Sharing for targeted or cross-context
# advertising / Use for targeted advertising / Profiling producing legal or
# similarly significant effects). Fields: names[first_name], names[last_name],
# input_text (Address), input_text_2 (City), "dropdown" (state <select>, full
# names), input_text_3 (Zip), email, phone. input_text_1 (Apt/Suite) left blank.
# A CAPTCHA (reCAPTCHA / Turnstile markers present) gates submission — the form
# is filled and left for a manual solve.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://xcelerated.com/unsubscribe/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        for name, value in [
            ("names[first_name]", SuperScraper.FIRST_NAME),
            ("names[last_name]", SuperScraper.LAST_NAME),
            ("input_text", SuperScraper.ADDRESS),
            ("input_text_2", SuperScraper.CITY),
            ("input_text_3", SuperScraper.ZIP_CODE),
            ("email", SuperScraper.EMAIL),
            ("phone", SuperScraper.PHONE_NUMBER),
        ]:
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2
            )

        state_select = await tab.find(xpath="//select[@name='dropdown']", raise_exc=False)
        if state_select:
            await state_select.execute_script(
                f"const o=[...this.options].find(x=>x.text.trim()=={SuperScraper.STATE!r});"
                "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
                "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
            )

        checkboxes = await tab.find(xpath="//input[@name='checkbox[]']", find_all=True, raise_exc=False) or []
        for box in checkboxes:
            await SuperScraper.js_check(box)
            await asyncio.sleep(0.1)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/xcelerated_dry_run.png")
        print(
            "Opt-out request filled but NOT submitted — a CAPTCHA must be solved "
            "manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the CAPTCHA, click Submit Form, then press Enter once confirmed...")
            input()


asyncio.run(main())
