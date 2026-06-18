import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://crportal.tapad.com/#/email"

REQUEST_TYPE_XPATH = '//ta-select[@formcontrolname="requestType"]'
COUNTRY_XPATH = '//ta-select[@formcontrolname="country"]'
EMAIL_XPATH = '//ta-input[@formcontrolname="email"]//input'


async def submit_request(tab, super_scraper, request_type: str):
    await tab.go_to(URL)
    time.sleep(5)

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab,
        input_xpath=REQUEST_TYPE_XPATH,
        dropdown_option_text=request_type,
        sleep=1,
    )

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab,
        input_xpath=COUNTRY_XPATH,
        dropdown_option_text="United States",
        sleep=1,
    )

    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit {request_type} request for {SuperScraper.EMAIL}")
        return

    # reCAPTCHA v2 is required — pause for manual solve or 2captcha integration
    # TODO: integrate 2captcha reCAPTCHA solver (site key: 6Lc59qEcAAAAAPUJ01XooqhDt_0rEa4IaAgDinAP)
    print(f"Please solve the reCAPTCHA for {request_type} request, then press Enter...")
    input()

    # TODO: Data Access and Deletion require a mouse-drawn signature in a canvas element before
    # submission. This step is not automated. The form will reject those submissions without it.
    # Opt Out does not require a signature and submits cleanly.

    await super_scraper.click_item_by_text(tab=tab, text="Submit")
    time.sleep(3)
    print(f"Submitted {request_type} request for {SuperScraper.EMAIL}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        await submit_request(tab, super_scraper, "Data Access")
        await submit_request(tab, super_scraper, "Opt Out")

        if SuperScraper.REMOVE_INFORMATION:
            await submit_request(tab, super_scraper, "Deletion")

        await asyncio.sleep(3)


asyncio.run(main())
