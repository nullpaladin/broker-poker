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

ATTESTATION_CHECKBOX = "INDIVIDUAL requestor *"
RIGHT_MAP = {
    "access": ["Access My Information"],
    "correct": ["Correct My Information"],
    "opt_out_sale_share": ["Opt Out of Sale and Sharing or Use for Targeted Advertising"],
    "opt_out_targeted_ads": ["Opt Out of Sale and Sharing or Use for Targeted Advertising"],
    "limit_sensitive_pi": ["Limit the Use of My Sensitive Personal Information"],
    "delete": ["Delete My Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        checkboxes = [ATTESTATION_CHECKBOX] + [cb for code in codes for cb in RIGHT_MAP[code]]
        for value in checkboxes:
            box = await tab.find(xpath=f"//input[@type='checkbox' and @value=\"{value}\"]", raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/completemailinglists_dry_run.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
