import asyncio
import json
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

# Rights exercised: Don't Sell/Share, View My Data, Edit My Data, Delete My Data (if REMOVE_INFORMATION).
# Form is an embedded Google Form — navigated to directly.
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSff6gJEpA6rv7dXX643lMIjzYEp4yeeD7_odWxU3HRteHVtGg/viewform"

EMAIL_XPATH = '//input[@aria-label="Your email"]'
NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[1]'
ADVERTISING_ID_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[2]'


async def check_checkbox(tab, aria_label):
    # json.dumps safely escapes apostrophes and other special chars in aria-label
    await tab.execute_script(
        f"Array.from(document.querySelectorAll('[role=\"checkbox\"]')).find(e => e.getAttribute('aria-label') === {json.dumps(aria_label)}).click()"
    )
    time.sleep(0.5)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(FORM_URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=1)

        await check_checkbox(tab, "Don't Sell/Share")
        await check_checkbox(tab, "View My Data")
        await check_checkbox(tab, "Edit My Data")
        if SuperScraper.wants("delete"):
            await check_checkbox(tab, "Delete My Data")

        await super_scraper.input_text_field(tab=tab, xpath=NAME_XPATH,
                                             text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=ADVERTISING_ID_XPATH,
                                             text=SuperScraper.ADVERTISING_ID, sleep=1)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit privacy request for {SuperScraper.EMAIL} (ad ID: {SuperScraper.ADVERTISING_ID})")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(4)

        result = await tab.execute_script("return document.body.innerText")
        print(result['result']['result']['value'][:500])
        print(f"Submitted privacy request for {SuperScraper.EMAIL}")


asyncio.run(main())
