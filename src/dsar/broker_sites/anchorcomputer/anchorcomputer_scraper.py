# anchorcomputer.com — server-rendered ASP.NET POST form, no captcha. Single
# submission covers all selected rights via checkboxes: RequestReport (Access —
# labeled "CA residents only" but not enforced client-side), RequestDoNotSell
# (Opt-Out) unconditionally, RequestDelete gated on REMOVE_INFORMATION.
# DateOfBirth is an HTML5 date input — set via JS native setter as YYYY-MM-DD
# (DATE_OF_BIRTH must be in that format). SsnLastFour is optional — filled only
# if LAST_FOUR_SSN is set in .env.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://ecom2.anchorcomputer.com/privacyrequest"

FIRST_NAME_XPATH = "//input[@id='FirstName']"
LAST_NAME_XPATH = "//input[@id='LastName']"
ADDRESS1_XPATH = "//input[@id='Address1']"
CITY_XPATH = "//input[@id='City']"
ZIP_XPATH = "//input[@id='Zip']"
SSN_XPATH = "//input[@id='SsnLastFour']"
PHONE_XPATH = "//input[@id='PhoneNumber']"
EMAIL_XPATH = "//input[@id='Email']"
SUBMIT_XPATH = "//input[@type='submit']"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_abbrev = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS1_XPATH, text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        await tab.execute_script(
            f'var s = document.querySelector("select#State"); s.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)

        if SuperScraper.LAST_FOUR_SSN:
            await super_scraper.input_text_field(tab=tab, xpath=SSN_XPATH, text=SuperScraper.LAST_FOUR_SSN)

        if SuperScraper.DATE_OF_BIRTH:
            # .env stores DATE_OF_BIRTH as DD/MM/YYYY; the native <input type="date">
            # here silently rejects anything but YYYY-MM-DD, so convert first.
            day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
            iso_dob = f"{year}-{month}-{day}"
            await tab.execute_script(
                'var d = document.querySelector("#DateOfBirth"); '
                f'd.value = "{iso_dob}"; '
                'd.dispatchEvent(new Event("input", {bubbles: true})); '
                'd.dispatchEvent(new Event("change", {bubbles: true}));'
            )

        await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='RequestReport']", sleep=0.3)
        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='RequestDoNotSell']", sleep=0.3)
        if SuperScraper.REMOVE_INFORMATION:
            await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='RequestDelete']", sleep=0.3)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "resources/screenshots/anchorcomputer_dry_run.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        await asyncio.sleep(3)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
