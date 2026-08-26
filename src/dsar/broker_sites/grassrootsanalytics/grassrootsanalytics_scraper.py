# grassrootsanalytics.com — Wix site, single submission. Rights via checkbox
# group: Access My Personal Information and Do Not Sell My Personal
# Information unconditionally; Delete My Personal Information gated on
# REMOVE_INFORMATION. Wix checkboxes are visually hidden (opacity:0) —
# clicked via their wrapping <label> ancestor, not the input directly. The
# "Do Not Sell" label text is truncated on the live site (missing its final
# "n" — "...Informatio") so the match string below is deliberately a shorter
# substring that survives either spelling. Wix's own CAPTCHA widget requires
# manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.grassrootsanalytics.com/california-consumer-privacy-act-ccpa"

CHECKBOXES = ["Access My Personal Information", "Do Not Sell My Personal Informat"]
DELETE_CHECKBOX = "Delete My Personal Information"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        for name, value in [
            ("first-name", SuperScraper.FIRST_NAME),
            ("last-name", SuperScraper.LAST_NAME),
            ("email", SuperScraper.EMAIL),
            ("phone-number", SuperScraper.PHONE_NUMBER),
            ("city", SuperScraper.CITY),
            ("street-address", SuperScraper.ADDRESS),
            ("state", SuperScraper.STATE),
        ]:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        checkboxes = list(CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for text in checkboxes:
            label = await tab.find(xpath=f"//label[.//span[contains(text(),'{text}')]]", raise_exc=False)
            if label:
                await label.click()
                await asyncio.sleep(0.2)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/grassrootsanalytics_dry_run.png")
            print("Screenshot saved to resources/screenshots/grassrootsanalytics_dry_run.png")
            return

        print("\nForm filled. Solve the CAPTCHA, click Submit,")
        print("then press Enter once the confirmation appears...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
