import asyncio
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

# parasolleads.com — /ccpa-opt-out-form.php, server-rendered POST form. No captcha.
# Rights the form exposes: Do Not Sell My Information (opt-out only); whether it runs is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current; the form reuses generic field names):
#   input[name=FirstName]     "Name" (full name: first + last)
#   input[name=EmailID]       Email
#   input[name=LastName] #1   Street address  (mislabeled field name)
#   input[name=LastName] #2   City            (mislabeled field name)
#   input[name=LastName] #3   State           (mislabeled field name)
#   input[name=pin]           ZIP code
#   input[name=gender]        "Do Not Sell My Information" checkbox (mislabeled field name)
#   "Send" button             Submit
URL = "https://www.parasolleads.com/ccpa-opt-out-form.php"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "Do Not Sell My Information"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The only checkbox is the mislabeled name="gender" input; its label element is unrecorded.)

NAME_XPATH = '//input[@name="FirstName"]'
EMAIL_XPATH = '//input[@name="EmailID"]'
ADDRESS_XPATH = '(//input[@name="LastName"])[1]'
CITY_XPATH = '(//input[@name="LastName"])[2]'
STATE_XPATH = '(//input[@name="LastName"])[3]'
ZIP_XPATH = '//input[@name="pin"]'
DO_NOT_SELL_CHECKBOX_XPATH = '//input[@name="gender"]'

FIELD_XPATHS = {
    "Name": NAME_XPATH,
    "Email": EMAIL_XPATH,
    "Street address": ADDRESS_XPATH,
    "City": CITY_XPATH,
    "State": STATE_XPATH,
    "Zip": ZIP_XPATH,
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(4)

        await super_scraper.input_text_field(tab=tab, xpath=NAME_XPATH,
                                             text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_XPATH, text=SuperScraper.ADDRESS, sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY, sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=STATE_XPATH, text=SuperScraper.STATE, sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE, sleep=1)

        await js_utils.js_click(await tab.find(xpath=DO_NOT_SELL_CHECKBOX_XPATH))
        time.sleep(0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run_opt_out")
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_text(tab=tab, text="Send", sleep=3)
        await asyncio.sleep(4)

        print(f"Submitted 'RIGHT_TO_OPT_OUT' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
