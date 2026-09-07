# groundtruth.com — HubSpot form (share.hsforms.com). No discrete right
# picker — a single free-text "Request Details" field states which right(s)
# to exercise. MAID (Mobile Advertising ID) is required, since GroundTruth is
# a location/mobile-ad data company. Request text only mentions deletion when
# REMOVE_INFORMATION is set. No CAPTCHA observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://share.hsforms.com/1BoOyoq-ASaS-3zNW4dh5Agnn8aa"


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
            ("email", SuperScraper.EMAIL),
            ("maid", SuperScraper.ADVERTISING_ID),
            ("state", SuperScraper.STATE),
        ]:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        if SuperScraper.REMOVE_INFORMATION:
            request_text = "I am requesting opt-out, correction, access, and deletion of my personal information."
        else:
            request_text = "I am requesting opt-out, correction, and access to my personal information."
        notes_field = await tab.find(name="additional_notes__c", raise_exc=False)
        if notes_field:
            await notes_field.type_text(request_text)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit request for MAID {SuperScraper.ADVERTISING_ID}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/groundtruth_dry_run.png")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted request for MAID {SuperScraper.ADVERTISING_ID}")


asyncio.run(main())
