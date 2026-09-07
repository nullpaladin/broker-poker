# l2-data.com — /optout1-667457/ is a Gravity Forms (WordPress) opt-out form,
# same platform as locatesmarter.com elsewhere in this repo. Opt-out only (no
# Right to Access/Delete — the page explicitly routes California residents to
# a separate "I Am A California Resident" mechanism instead, which is a
# distinct, un-automated page). Fields are name/phone/email/address/city/
# state/zip plus a required consent checkbox ("I am legally certifying that
# I am the individual whose information is being provided") and a Gravity
# Forms arithmetic CAPTCHA (e.g. "14 + 3 ="), regenerated per page load and
# parsed/solved at runtime rather than hardcoded — no manual CAPTCHA step
# needed, so DRY_RUN is respected and a real submission goes through when
# DRY_RUN is False.
import asyncio
import re

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://l2-data.com/optout1-667457/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "input_5_2_3": SuperScraper.FIRST_NAME,
            "input_5_2_6": SuperScraper.LAST_NAME,
            "input_5_3": SuperScraper.PHONE_NUMBER,
            "input_5_4": SuperScraper.EMAIL,
            "input_5_5_1": SuperScraper.ADDRESS,
            "input_5_5_3": SuperScraper.CITY,
            "input_5_5_4": SuperScraper.STATE,
            "input_5_5_5": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        consent_checkbox = await tab.find(id="input_5_11_1", raise_exc=False)
        if consent_checkbox:
            await consent_checkbox.click()
        else:
            print(f"{super_scraper.OOPS} Consent checkbox not found")

        math_label = await tab.execute_script(
            "var l=document.querySelector('label[for=input_5_16]'); return l ? l.textContent.trim() : ''"
        )
        math_text = math_label["result"]["result"]["value"]
        match = re.search(r"(\d+)\s*\+\s*(\d+)", math_text)
        if match:
            answer = str(int(match.group(1)) + int(match.group(2)))
            math_field = await tab.find(id="input_5_16", raise_exc=False)
            if math_field:
                await math_field.type_text(answer)
            else:
                print(f"{super_scraper.OOPS} math CAPTCHA field not found")
        else:
            print(f"{super_scraper.OOPS} could not parse math CAPTCHA text: '{math_text}'")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/l2-data_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out request for {SuperScraper.EMAIL}")
            return

        submit_button = await tab.find(id="gform_submit_button_5", raise_exc=False)
        if submit_button:
            await submit_button.click()
            await asyncio.sleep(3)
            print(f"Submitted opt-out request for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} submit button not found")


asyncio.run(main())
