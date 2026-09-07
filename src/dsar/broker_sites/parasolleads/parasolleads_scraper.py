import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

# Rights exercised: Do Not Sell My Information (opt-out only).
# Server-rendered POST form. No captcha.
URL = "https://www.parasolleads.com/ccpa-opt-out-form.php"

NAME_XPATH = '//input[@name="FirstName"]'
EMAIL_XPATH = '//input[@name="EmailID"]'
ADDRESS_XPATH = '(//input[@name="LastName"])[1]'
CITY_XPATH = '(//input[@name="LastName"])[2]'
STATE_XPATH = '(//input[@name="LastName"])[3]'
ZIP_XPATH = '//input[@name="pin"]'
DO_NOT_SELL_CHECKBOX_XPATH = '//input[@name="gender"]'


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        await tab.execute_script(
            "document.querySelector('input[name=\"gender\"]').click()"
        )
        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "resources/screenshots/parasolleads_dry_run.png")
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_text(tab=tab, text="Send", sleep=3)
        await asyncio.sleep(4)

        result = await tab.execute_script("return document.body.innerText")
        print(result['result']['result']['value'][:500])
        print(f"Submitted opt-out for {SuperScraper.EMAIL}")


asyncio.run(main())
