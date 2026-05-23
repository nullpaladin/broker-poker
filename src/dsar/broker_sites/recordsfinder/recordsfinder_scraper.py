import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://recordsfinder.com/optout/"

_PREFIX = "InfoPay_Core_Components_OptOuts_DataRemovalServiceModel"
FIRST_NAME_XPATH = f'//input[@id="{_PREFIX}_fname"]'
LAST_NAME_XPATH = f'//input[@id="{_PREFIX}_lname"]'
STATE_SELECT_ID = f"{_PREFIX}_state"
CITY_XPATH = f'//input[@id="{_PREFIX}_city"]'
SUBMIT_XPATH = '//button[@type="submit"]'


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    super_scraper = SuperScraper()

    state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(2)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)

        await tab.execute_script(
            f'var s = document.getElementById("{STATE_SELECT_ID}"); s.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        time.sleep(3)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        await asyncio.sleep(3)


asyncio.run(main())
