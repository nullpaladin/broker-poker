# addresssearch.com — plain "remove info" form at /remove-info.php (name, email, address).
# Single removal request, mapped to RIGHT_TO_DELETE; runs only when deletion is requested
# (decided by SuperScraper.rights_to_exercise). No CAPTCHA handling in this scraper.
#
# Page elements:
#   input[name=fname] / input[name=lname]   First / Last name
#   input[name=email]                       Email
#   input[name=address1]                    Address
#   input[name=city]                        City
#   select[name=state]                      State (2-letter value)
#   input[name=zip]                         Zip code
#   input[name=submit]                      Submit button
import asyncio
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.addresssearch.com/remove-info.php"

RIGHT_MAP = {
    Right.RIGHT_TO_DELETE: "remove-info",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIRST_NAME_XPATH = '//input[@name="fname"]'
LAST_NAME_XPATH = '//input[@name="lname"]'
EMAIL_XPATH = '//input[@name="email"]'
ADDRESS_XPATH = '//input[@name="address1"]'
CITY_XPATH = '//input[@name="city"]'
ZIP_XPATH = '//input[@name="zip"]'
STATE_XPATH = '//select[@name="state"]'
SUBMIT_XPATH = '//input[@name="submit"]'


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
        time.sleep(2)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_XPATH, text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        await tab.execute_script(
            f'var s = document.querySelector("select[name=state]"); s.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": FIRST_NAME_XPATH,
                "Last name": LAST_NAME_XPATH,
                "Email": EMAIL_XPATH,
                "Address": ADDRESS_XPATH,
                "City": CITY_XPATH,
                "State": STATE_XPATH,
                "Zip": ZIP_XPATH,
            })

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run_delete")
            print(f"DRY RUN: would submit '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        time.sleep(3)
        print(f"Submitted '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL} — confirm in the browser.")

        await asyncio.sleep(3)


asyncio.run(main())
