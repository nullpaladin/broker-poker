import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/3d676ed2-16b1-4c48-97f8-a911923a3adf/a0df0a98-d990-40ff-9bdb-35b5f9e06620"

STATE_XPATH = '//input[@id="stateDSARElement"]'
FIRST_NAME_XPATH = '//input[@id="firstNameDSARElement"]'
MIDDLE_NAME_XPATH = '//input[@id="formField80DSARElement"]'
LAST_NAME_XPATH = '//input[@id="lastNameDSARElement"]'
EMAIL_XPATH = '//input[@id="emailDSARElement"]'
ADDRESS_XPATH = '//input[@id="addressDSARElement"]'
CITY_XPATH = '//input[@id="cityDSARElement"]'
ZIP_XPATH = '//input[@id="zipDSARElement"]'
DOB_XPATH = '//input[@id="dateOfBirthDSARElement"]'

# Request types — div buttons identified by aria-label
REQUEST_TYPES_ALWAYS = [
    "Access Data",
    "Correct Data",
    "Opt-Out",
    "Data Portability",
    "List of Third Party Recipients",
]
REQUEST_TYPE_DELETE = "Delete Data"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_name = SuperScraper.STATE.title()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(5)

        # State autocomplete (country is pre-filled as United States)
        await super_scraper.input_text_field(tab=tab, xpath=STATE_XPATH, text=state_name)
        time.sleep(1)
        await super_scraper.click_item_by_text(tab=tab, text=state_name)
        time.sleep(1)

        # Requester type
        await super_scraper.click_item_by_text(tab=tab, text="Consumer")
        time.sleep(2)

        # Select all applicable request types — JS click fires Angular's event handlers
        async def click_request_type(label):
            await tab.execute_script(f'document.querySelector(\'[aria-label="{label}"]\').click()')
            time.sleep(0.5)

        for request_type in REQUEST_TYPES_ALWAYS:
            await click_request_type(request_type)

        if SuperScraper.REMOVE_INFORMATION:
            await click_request_type(REQUEST_TYPE_DELETE)

        # Personal info
        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_XPATH, text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)
        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)
        await super_scraper.input_text_field(tab=tab, xpath=DOB_XPATH, text=SuperScraper.DATE_OF_BIRTH)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit privacy request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(3)
            return

        # reCAPTCHA v2 — pause for manual solve or 2captcha
        print("Please solve the reCAPTCHA, then press Enter...")
        input()

        await super_scraper.click_item_by_text(tab=tab, text="Submit Request")
        time.sleep(3)
        print(f"Submitted privacy request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        await asyncio.sleep(3)


asyncio.run(main())
