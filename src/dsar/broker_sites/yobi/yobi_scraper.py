# yobi.ai — "opt-out" / privacy-rights form at yobi.ai/opt-out (custom form that
# posts to HubSpot; field names are HubSpot internal names).
# Server-rendered. All personal fields are required: firstname, lastname, email,
# phone, address, city, state, zip, country, and date_of_birth__do_not_sell_
# (an <input type="date"> — DATE_OF_BIRTH is DD/MM/YYYY in .env and MUST be
# converted to YYYY-MM-DD or the field silently stays empty).
# "I am submitting on behalf of" is a required radio group — "Myself".
# "Select the right(s) you want to exercise" is a multi-select checkbox group
# (one combined submission): Access My Information, Do Not Sell My Information,
# "Object or Restrict the Processing of My Data", Move My Data unconditionally;
# Delete My Information gated on REMOVE_INFORMATION; "Correct My Data" skipped.
# No CAPTCHA observed.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.yobi.ai/opt-out"

RIGHTS = [
    "Access My Information",
    "Do Not Sell My Information",
    "Object or Restrict the Processing of My Data",
    "Move My Data",
]
DELETE_RIGHT = "Delete My Information"


def _dob_iso():
    raw = (SuperScraper.DATE_OF_BIRTH or "").strip()
    for sep in ("/", "-", "."):
        if sep in raw:
            parts = raw.split(sep)
            if len(parts) == 3 and len(parts[2]) == 4:
                d, m, y = parts
                return f"{y}-{int(m):02d}-{int(d):02d}"
    return raw


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        text_fields = {
            "firstname": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
            "country": "United States",
        }
        for name, value in text_fields.items():
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2,
            )

        dob = await tab.find(id="date_of_birth__do_not_sell_", raise_exc=False)
        if dob:
            await dob.execute_script(
                f"this.value = {_dob_iso()!r}; "
                "this.dispatchEvent(new Event('input',{bubbles:true})); "
                "this.dispatchEvent(new Event('change',{bubbles:true}));"
            )

        myself = await tab.find(
            xpath="//input[@name='i_am_submitting_on_behalf_of' and @value='Myself']", raise_exc=False
        )
        if myself:
            await myself.click()

        rights = list(RIGHTS)
        if SuperScraper.REMOVE_INFORMATION:
            rights.append(DELETE_RIGHT)
        for value in rights:
            box = await tab.find(
                xpath=f"//input[@name='select_the_right_s__you_want_to_exercise_' and @value={value!r}]",
                raise_exc=False,
            )
            if box:
                await box.execute_script("if (!this.checked) this.click();")
                await asyncio.sleep(0.1)

        time.sleep(0.5)
        await tab.take_screenshot("resources/screenshots/yobi_dry_run.png")
        print("Screenshot saved to resources/screenshots/yobi_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit privacy request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        submit = await tab.find(xpath="//form[@id='optout-form']//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(3)
        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
