# monitorbase.com — MonitorBase CCPA/privacy request form on my.monitorbase.com/privacypolicy.
# Plain Laravel Livewire page, but the final submit is a native form POST to
# my.monitorbase.com/ccpa/remove, so typing into the wire:model inputs is enough.
# "Request Type" is a native <select id="type">: 1 = What Information Do You Have (access),
# 2 = Opt Me Out Of Having My Data Sold (opt-out), 3 = Delete My Information.
# Single-select — one submission per right. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# A dynamic image CAPTCHA (name="captcha") gates submission — form is filled
# completely and left for a manual solve.  **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   #first_name / #last_name   First / Last name
#   #email                     Email
#   #phone_number              Phone number
#   #address / #city / #state / #zip   Address / City / State (free text) / Zip
#   #type                      "Request Type" <select> -> RIGHT_MAP option text
#   #agreement                 agreement checkbox
#   name="captcha"             "Please Insert Captcha" field (manual)
#   "Submit Request" button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://my.monitorbase.com/privacypolicy"

# Right -> visible text of the "Request Type" option
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "What Information of Mine Do You Have?",
    Right.RIGHT_TO_OPT_OUT: "Opt Me Out Of Having My Data Sold",
    Right.RIGHT_TO_DELETE: "Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Request Type" <select>, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "What Information of Mine Do You Have?": Right.RIGHT_TO_ACCESS,
    "Opt Me Out Of Having My Data Sold": Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = "select#type option"  # a placeholder option, if any, is unrecorded

FIELD_XPATHS = {
    "First name": "//*[@id='first_name']",
    "Last name": "//*[@id='last_name']",
    "Email": "//*[@id='email']",
    "Phone": "//*[@id='phone_number']",
    "Address": "//*[@id='address']",
    "City": "//*[@id='city']",
    "State": "//*[@id='state']",
    "Zip": "//*[@id='zip']",
    "Request type": "//*[@id='type']",
}


async def submit_request(tab, right, option_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    fields = {
        "//input[@id='first_name']": SuperScraper.FIRST_NAME,
        "//input[@id='last_name']": SuperScraper.LAST_NAME,
        "//input[@id='email']": SuperScraper.EMAIL,
        "//input[@id='phone_number']": SuperScraper.PHONE_NUMBER,
        "//input[@id='address']": SuperScraper.ADDRESS,
        "//input[@id='city']": SuperScraper.CITY,
        "//input[@id='state']": SuperScraper.STATE,
        "//input[@id='zip']": SuperScraper.ZIP_CODE,
    }
    for xpath, value in fields.items():
        await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.3)

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab, input_xpath="//select[@id='type']", dropdown_option_text=option_text, sleep=0.5
    )

    agreement = await tab.find(id="agreement", raise_exc=False)
    if agreement:
        await js_utils.js_check(agreement)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({option_text}) for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{right.name}'. Type the CAPTCHA shown in the browser")
    print("into the 'Please Insert Captcha' field, click Submit Request, then press Enter...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
