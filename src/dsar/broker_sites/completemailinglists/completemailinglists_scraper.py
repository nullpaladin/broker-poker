# completemailinglists.com — HubSpot form ("Complete Mailing Lists"). All
# rights AND the requestor-type are one combined multi-select checkbox group
# sharing the same (oddly-named) field: Access, Opt Out of Sale/Sharing,
# Limit Sensitive PI Use, Correct, and "INDIVIDUAL requestor" unconditionally;
# "Delete My Information" gated on REMOVE_INFORMATION. Single submission.
# Zip field name is literally "0-2/zip" (a HubSpot quirk, not a typo here).
# Optional file upload for requestor verification — left unfilled. reCAPTCHA
# is HubSpot's own hidden/invisible integration (hs-recaptcha-response) and
# does not require manual solving.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.completemailinglists.com/consumer-privacy-request"

CHECKBOXES = [
    "INDIVIDUAL requestor *",
    "Access My Information",
    "Opt Out of Sale and Sharing or Use for Targeted Advertising",
    "Limit the Use of My Sensitive Personal Information",
    "Correct My Information",
]
DELETE_CHECKBOX = "Delete My Information"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        text_fields = [
            ("firstname", SuperScraper.FIRST_NAME),
            ("lastname", SuperScraper.LAST_NAME),
            ("phone", SuperScraper.PHONE_NUMBER),
            ("email", SuperScraper.EMAIL),
            ("address", SuperScraper.ADDRESS),
            ("city", SuperScraper.CITY),
            ("state", SuperScraper.STATE),
            ("0-2/zip", SuperScraper.ZIP_CODE),
            ("date_of_birth", SuperScraper.DATE_OF_BIRTH),
        ]
        for name, value in text_fields:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        checkboxes = list(CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for value in checkboxes:
            box = await tab.find(xpath=f"//input[@type='checkbox' and @value=\"{value}\"]", raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/completemailinglists_dry_run.png")
            print("Screenshot saved to resources/screenshots/completemailinglists_dry_run.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
