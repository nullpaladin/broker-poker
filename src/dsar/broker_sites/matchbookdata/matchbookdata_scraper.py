# matchbookdata.com — /your-privacy-choices/. Matchbook Data identifies
# consumers only by mobile Device ID (Advertising ID or Installation ID),
# not by name/address — the entire form is just two fields:
# `form_fields[device_ID]` (ADVERTISING_ID) and `form_fields[email]`. There
# is no separate control for Opt-Out vs. Deletion vs. Limit-Sensitive-PI —
# the surrounding page text describes all three rights but funnels every
# request through this same single Device-ID-based form, so this is one
# unconditional submission rather than a per-right selection. No CAPTCHA
# observed. A Cookiebot consent banner covers the page on first load and
# must be dismissed first.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.matchbookdata.com/your-privacy-choices/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        deny_btn = await tab.find(id="CybotCookiebotDialogBodyButtonDecline", raise_exc=False)
        if deny_btn:
            await deny_btn.click()
            await asyncio.sleep(1)

        device_id_field = await tab.find(id="form-field-device_ID", raise_exc=False)
        if device_id_field and SuperScraper.ADVERTISING_ID:
            await device_id_field.type_text(SuperScraper.ADVERTISING_ID)
        else:
            print(f"{super_scraper.OOPS} device_ID field not found or ADVERTISING_ID not set")

        email_field = await tab.find(id="form-field-email", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/matchbookdata_dry_run.png")
        print("Screenshot saved to resources/screenshots/matchbookdata_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out/deletion request for {SuperScraper.EMAIL} (device ID: {SuperScraper.ADVERTISING_ID})")
            return

        submit_btn = await tab.find(text="Submit", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted request for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
