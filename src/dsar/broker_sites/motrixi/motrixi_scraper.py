# motrixi.com — /index.php/opt-out/ embeds a HubSpot form via the standard
# src-less `<iframe class="hs-form-iframe">` (hbspt.forms.create). Unlike the
# older note in scraper_dev_discoveries.md, pydoll CAN drive this: calling
# `.find()` on the iframe *WebElement* (not tab.find, not get_frame — both fail)
# resolves into the frame's document.
#
# The opt-out form is a single required textarea, "Enter Advertising ID"
# (name="enter_advertising_id_"), plus Submit — so this exercises Opt-Out only,
# keyed on the mobile advertising ID. Right to Access is email-only
# (privacy@Motrixi.com, never answered) — see README. No CAPTCHA (HubSpot's
# built-in spam protection is invisible).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.motrixi.com/index.php/opt-out/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2200")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        iframe = await tab.find(class_name="hs-form-iframe", raise_exc=False)
        if not iframe:
            print(f"{super_scraper.OOPS} HubSpot form iframe not found")
            return

        ad_id_field = await iframe.find(xpath="//textarea", raise_exc=False)
        if not ad_id_field:
            ad_id_field = await iframe.find(xpath="//*[@name='enter_advertising_id_']", raise_exc=False)
        if ad_id_field:
            await ad_id_field.type_text(SuperScraper.ADVERTISING_ID)
        else:
            print(f"{super_scraper.OOPS} 'Enter Advertising ID' field not found in iframe")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/motrixi_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/motrixi_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for advertising ID {SuperScraper.ADVERTISING_ID}")
            return

        submit = await iframe.find(xpath="//input[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out for advertising ID {SuperScraper.ADVERTISING_ID}")


asyncio.run(main())
