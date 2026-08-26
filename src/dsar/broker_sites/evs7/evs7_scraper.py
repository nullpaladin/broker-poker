# evs7.com — Contact Form 7 (WordPress) request form. Single submission,
# rights via checkbox group: "view the information" (Access) and "not be
# sold" (Opt-Out) unconditionally; "delete any information" gated on
# REMOVE_INFORMATION. State select uses full state names as values.
# reCAPTCHA is invisible (badge only) — auto-resolves, no manual solve needed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.evs7.com/personal-information-request"

CHECKBOXES = [
    "I request to view the information that you have about me.",
    "I request that any information about me will not be sold to anyone.",
]
DELETE_CHECKBOX = "I request that you delete any information about me."


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-163']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-52']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-637']", text=SuperScraper.ADDRESS, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-566']", text=SuperScraper.CITY, sleep=0.2)

        await tab.execute_script(
            f'var s = document.querySelector("select[name=\\"menu-415\\"]"); '
            f's.value = "{SuperScraper.STATE}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='text-863']", text=SuperScraper.ZIP_CODE, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='tel-877']", text=SuperScraper.PHONE_NUMBER, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@name='email-382']", text=SuperScraper.EMAIL, sleep=0.2)

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
            await tab.take_screenshot(path="resources/screenshots/evs7_dry_run.png")
            print("Screenshot saved to resources/screenshots/evs7_dry_run.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
