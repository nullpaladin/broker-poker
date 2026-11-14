# evs7.com — Contact Form 7 (WordPress) request form. Single submission,
# rights via checkbox group: "view the information" (Access), "not be
# sold" (Opt-Out) and "delete any information" (Delete). State select uses full state names as values.
# reCAPTCHA is invisible (badge only) — auto-resolves, no manual solve needed.
#
# Page elements (Contact Form 7 field names):
#   text-163 / text-52     First / Last name
#   text-637 / text-566    Address / City
#   menu-415               State <select> (full state names)
#   text-863               Zip code
#   tel-877 / email-382    Phone / Email
#   checkbox group         rights, matched by value (see RIGHT_MAP)
#   input[type=submit]     Submit
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.evs7.com/personal-information-request"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["I request to view the information that you have about me."],
    Right.RIGHT_TO_OPT_OUT: ["I request that any information about me will not be sold to anyone."],
    Right.RIGHT_TO_DELETE: ["I request that you delete any information about me."],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the rights checkbox group, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "I request to view the information that you have about me.": Right.RIGHT_TO_ACCESS,
    "I request that any information about me will not be sold to anyone.": Right.RIGHT_TO_OPT_OUT,
    "I request that you delete any information about me.": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = ".wpcf7-checkbox .wpcf7-list-item-label"  # Contact Form 7 checkbox labels

FIELD_XPATHS = {
    "First name": "//input[@name='text-163']",
    "Last name": "//input[@name='text-52']",
    "Address": "//input[@name='text-637']",
    "City": "//input[@name='text-566']",
    "State": "//select[@name='menu-415']",
    "Zip": "//input[@name='text-863']",
    "Phone": "//input[@name='tel-877']",
    "Email": "//input[@name='email-382']",
}


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
        await asyncio.sleep(3)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-163']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-52']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-637']", text=SuperScraper.ADDRESS, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-566']", text=SuperScraper.CITY, sleep=0.2)

        state_select = await tab.find(xpath="//select[@name='menu-415']", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, value=SuperScraper.STATE)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-863']", text=SuperScraper.ZIP_CODE, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='tel-877']", text=SuperScraper.PHONE_NUMBER, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='email-382']", text=SuperScraper.EMAIL, sleep=0.2)

        checkboxes = [entry for right in rights for entry in RIGHT_MAP[right]]
        for value in checkboxes:
            box = await tab.find(xpath=f"//input[@type='checkbox' and @value=\"{value}\"]", raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
