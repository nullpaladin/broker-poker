# directmail.com — Mail Preference (Do Not Mail) registration at /mail_preference/.
# Two steps: (1) a contact form gated by a reCAPTCHA v2 (manual solve, then Enter),
# (2) a category page where "select all" opts out of every mailing category.
# The form is a mail opt-out, so it maps to RIGHT_TO_OPT_OUT; which rights run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (FIRST_NAME_XPATH ... SELECT_ALL_XPATH below):
#   #wrap_txtFirstName / #wrap_txtLastName   First / Last name
#   #wrap_txtAdd1 / #wrap_txtAdd2            Address line 1 / 2
#   #wrap_txtCity                            City
#   #wrap_ddlState                           State <select> (2-letter abbreviation)
#   #wrap_txtZip / #wrap_txtPhone / #wrap_txtEmail   Zip / Phone / Email
#   #wrap_btnCompleteReg                     Complete registration (step 1 submit)
#   #checkbox                                Step 2 "select all" categories checkbox
#   "Submit" button                          Step 2 submit
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.directmail.com/mail_preference/"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "Do Not Mail",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIRST_NAME_XPATH = '//input[@id="wrap_txtFirstName"]'
LAST_NAME_XPATH = '//input[@id="wrap_txtLastName"]'
ADDRESS_ONE_XPATH = '//input[@id="wrap_txtAdd1"]'
ADDRESS_TWO_XPATH = '//input[@id="wrap_txtAdd2"]'
CITY_XPATH = '//input[@id="wrap_txtCity"]'
ZIP_XPATH = '//input[@id="wrap_txtZip"]'
PHONE_XPATH = '//input[@id="wrap_txtPhone"]'
EMAIL_XPATH = '//input[@id="wrap_txtEmail"]'
SUBMIT_XPATH = '//input[@id="wrap_btnCompleteReg"]'
SELECT_ALL_XPATH = '//input[@id="checkbox"]'


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    state_abbrev = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_ONE_XPATH, text=SuperScraper.ADDRESS)
        if SuperScraper.ADDRESS_LINE_TWO:
            await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_TWO_XPATH, text=SuperScraper.ADDRESS_LINE_TWO)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        # Native <select> — set via JS since CDP click on <option> doesn't trigger change events
        state_select = await tab.find(id="wrap_ddlState", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, value=state_abbrev)

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)
        if SuperScraper.PHONE_NUMBER:
            await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": FIRST_NAME_XPATH,
                "Last name": LAST_NAME_XPATH,
                "Address": ADDRESS_ONE_XPATH,
                "City": CITY_XPATH,
                "State": '//select[@id="wrap_ddlState"]',
                "Zip": ZIP_XPATH,
                "Email": EMAIL_XPATH,
            })

        if SuperScraper.DRY_RUN:
            await asyncio.sleep(3)
            await SuperScraper.screenshot(tab, "dry_run_opt_out")
            print(f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' (Do Not Mail) for {SuperScraper.EMAIL}")
            return

        # reCAPTCHA v2 — pause for manual solve or 2captcha
        # TODO: integrate 2captcha (site key: 6Le9aeApAAAAAMRr0iCDa65cZ1iGkHUI1FwEAKZH)
        print("Please solve the reCAPTCHA, then press Enter...")
        input()

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        time.sleep(3)

        # Step 2: opt out of all mailing categories
        select_all = await tab.find(xpath=SELECT_ALL_XPATH, timeout=10, raise_exc=False)
        if select_all:
            await select_all.click()
            time.sleep(1)
            await super_scraper.click_item_by_text(tab=tab, text="Submit")
            time.sleep(3)
            print(f"Submitted '{Right.RIGHT_TO_OPT_OUT.name}' (Do Not Mail) for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Step 2 category selection not found — verify submission succeeded")

        await asyncio.sleep(3)


asyncio.run(main())
