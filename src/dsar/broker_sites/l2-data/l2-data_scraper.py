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
# DRY_RUN is False. Whether it runs is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (Gravity Forms form 5):
#   #input_5_2_3 / #input_5_2_6   First / Last name
#   #input_5_3                    Phone
#   #input_5_4                    Email
#   #input_5_5_1 / _3 / _4 / _5   Street address / City / State / ZIP
#   #input_5_11_1                 Consent checkbox ("I am legally certifying that I am the
#                                 individual whose information is being provided")
#   label[for=input_5_16]         Arithmetic CAPTCHA question; #input_5_16 is its answer field
#   #gform_submit_button_5        Submit button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import captcha_solutions_util
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

URL = "https://l2-data.com/optout1-667457/"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='input_5_2_3']",
    "Last name": "//*[@id='input_5_2_6']",
    "Phone": "//*[@id='input_5_3']",
    "Email": "//*[@id='input_5_4']",
    "Address": "//*[@id='input_5_5_1']",
    "City": "//*[@id='input_5_5_3']",
    "State": "//*[@id='input_5_5_4']",
    "Zip": "//*[@id='input_5_5_5']",
    "Arithmetic answer": "//*[@id='input_5_16']",
}


async def main():
    super_scraper = SuperScraper()
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

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

        math_text = await js_utils.js_eval(
            tab,
            "var l=document.querySelector('label[for=input_5_16]'); return l ? l.textContent.trim() : ''",
        )
        answer = captcha_solutions_util.solve_math_captcha(math_text or "")
        if answer is not None:
            math_field = await tab.find(id="input_5_16", raise_exc=False)
            if math_field:
                await math_field.type_text(answer)
            else:
                print(f"{super_scraper.OOPS} math CAPTCHA field not found")
        else:
            print(f"{super_scraper.OOPS} could not parse math CAPTCHA text: '{math_text}'")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out request for {SuperScraper.EMAIL}")
            return

        submit_button = await tab.find(id="gform_submit_button_5", raise_exc=False)
        if submit_button:
            await submit_button.click()
            await asyncio.sleep(3)
            print(f"Submitted 'RIGHT_TO_OPT_OUT' for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} submit button not found")


asyncio.run(main())
