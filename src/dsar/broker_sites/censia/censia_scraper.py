# censia.com — Google Form ("Remove My Data"). All fields are short-answer
# text inputs; Google Forms wires them up with aria-labelledby pointing at
# the question heading rather than a direct aria-label, so each is targeted
# by an xpath scoped to its role="listitem" container instead. Rights are
# a single multi-select checkbox group (checkboxes DO carry aria-label
# directly): "Access my PI" and "Do not sell my PI" unconditionally; the
# third option is left labeled "Option 3" by Censia itself (a form-authoring
# mistake, not something this scraper can fix) but is positioned as the third
# of a standard Access/Opt-Out/Delete triad, so it is treated as Delete and
# gated on REMOVE_INFORMATION. No CAPTCHA.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://docs.google.com/forms/d/1VhF33VAQG4AmUqBWf7e3m8fw17h9ek64EtQXnuuBQcA/viewform?edit_requested=true"

CHECKBOXES = ["Access my PI", "Do not sell my PI"]
DELETE_CHECKBOX = "Option 3"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        fields = [
            ("First Name", SuperScraper.FIRST_NAME),
            ("Last Name", SuperScraper.LAST_NAME),
            ("Phone Number", SuperScraper.PHONE_NUMBER),
            ("Email Address", SuperScraper.EMAIL),
            ("City", SuperScraper.CITY),
            ("State", SuperScraper.STATE),
            ("Zip Code", SuperScraper.ZIP_CODE),
            ("Country", "United States"),
        ]
        for label, value in fields:
            field = await tab.find(
                xpath=f"//div[@role='listitem'][.//span[contains(text(),'{label}')]]//input",
                raise_exc=False,
            )
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        checkboxes = list(CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for label in checkboxes:
            box = await tab.find(**{"aria-label": label}, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/censia_dry_run.png")
            print("Screenshot saved to resources/screenshots/censia_dry_run.png")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
