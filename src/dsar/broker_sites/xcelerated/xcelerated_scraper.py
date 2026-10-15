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
# Whether the opt-out runs is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   [name="names[first_name]"] / [name="names[last_name]"]   First / Last name
#   [name=input_text]          Address
#   [name=input_text_1]        Apt/Suite (left blank)
#   [name=input_text_2]        City
#   [name=dropdown]            State <select> (full names)
#   [name=input_text_3]        Zip
#   [name=email] / [name=phone]   Email / Phone
#   [name="checkbox[]"]        The four opt-out category checkboxes (all checked)
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://xcelerated.com/unsubscribe/"

# The form has a single opt-out request; every category checkbox is checked.
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "checkbox[]",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

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
            await js_utils.select_native_option(state_select, text=SuperScraper.STATE, dispatch=("change",))

        checkboxes = await tab.find(xpath="//input[@name='checkbox[]']", find_all=True, raise_exc=False) or []
        for box in checkboxes:
            await js_utils.js_check(box)
            await asyncio.sleep(0.1)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "Opt-out request filled but NOT submitted — a CAPTCHA must be solved "
            "manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the CAPTCHA, click Submit Form, then press Enter once confirmed...")
            input()


asyncio.run(main())
