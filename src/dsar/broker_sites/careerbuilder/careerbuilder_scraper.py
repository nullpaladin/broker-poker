# careerbuilder.com — server-rendered privacy request form, no captcha. One
# submission per request type: "access" (Access) and "dns" (Do Not Sell/Share)
# unconditionally; "deletion" gated on REMOVE_INFORMATION. Relation defaults
# to "Other" since a generic data-subject request doesn't map to any of the
# job-seeker/employee-specific options. Address is a plain textarea (single
# free-text field, not split into street/city/state/zip).
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.careerbuilder.com/privacy/"

RIGHTS = [("access", "access"), ("dns", "opt_out")]
DELETE_RIGHT = ("deletion", "delete")


async def submit_request(tab, type_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(3)

    await super_scraper.input_text_field(tab=tab, xpath="//input[@id='name']", text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=0.3)
    await super_scraper.input_text_field(tab=tab, xpath="//input[@id='email']", text=SuperScraper.EMAIL, sleep=0.3)
    await super_scraper.input_text_field(tab=tab, xpath="//textarea[@id='address']", text=SuperScraper.ADDRESS, sleep=0.3)

    await tab.execute_script(
        'var s = document.querySelector("select#relation"); s.value = "other"; s.dispatchEvent(new Event("change"));'
    )
    await tab.execute_script(
        f'var s = document.querySelector("select#type"); s.value = "{type_value}"; s.dispatchEvent(new Event("change"));'
    )

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{type_value}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/careerbuilder_dry_run_{label}.png")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath="//button[@id='submitBtn']", sleep=2)
    await asyncio.sleep(2)
    print(f"Submitted '{type_value}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for type_value, label in rights:
            await submit_request(tab, type_value, label, super_scraper)


asyncio.run(main())
