import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.addresssearch.com/remove-info.php"

FIRST_NAME_XPATH = '//input[@name="fname"]'
LAST_NAME_XPATH = '//input[@name="lname"]'
EMAIL_XPATH = '//input[@name="email"]'
ADDRESS_XPATH = '//input[@name="address1"]'
CITY_XPATH = '//input[@name="city"]'
ZIP_XPATH = '//input[@name="zip"]'
SUBMIT_XPATH = '//input[@name="submit"]'


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)

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

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        time.sleep(3)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        await asyncio.sleep(3)


asyncio.run(main())
