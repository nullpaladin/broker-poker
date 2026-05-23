import asyncio
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.directmail.com/mail_preference/"

FIRST_NAME_XPATH = '//input[@id="wrap_txtFirstName"]'
LAST_NAME_XPATH = '//input[@id="wrap_txtLastName"]'
ADDRESS1_XPATH = '//input[@id="wrap_txtAdd1"]'
ADDRESS2_XPATH = '//input[@id="wrap_txtAdd2"]'
CITY_XPATH = '//input[@id="wrap_txtCity"]'
ZIP_XPATH = '//input[@id="wrap_txtZip"]'
PHONE_XPATH = '//input[@id="wrap_txtPhone"]'
EMAIL_XPATH = '//input[@id="wrap_txtEmail"]'
SUBMIT_XPATH = '//input[@id="wrap_btnCompleteReg"]'
SELECT_ALL_XPATH = '//input[@id="checkbox"]'


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    super_scraper = SuperScraper()

    state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS1_XPATH, text=SuperScraper.ADDRESS)
        if SuperScraper.ADDRESS_LINE_TWO:
            await super_scraper.input_text_field(tab=tab, xpath=ADDRESS2_XPATH, text=SuperScraper.ADDRESS_LINE_TWO)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        # Native <select> — set via JS since CDP click on <option> doesn't trigger change events
        await tab.execute_script(
            f'var s = document.getElementById("wrap_ddlState"); s.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)
        if SuperScraper.PHONE_NUMBER:
            await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit Do Not Mail opt-out for {SuperScraper.EMAIL}")
            await asyncio.sleep(3)
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
            print(f"Submitted Do Not Mail opt-out for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Step 2 category selection not found — verify submission succeeded")

        await asyncio.sleep(3)


asyncio.run(main())
