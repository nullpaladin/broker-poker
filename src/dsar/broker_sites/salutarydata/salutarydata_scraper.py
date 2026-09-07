# salutarydata.com — /privacy-opt-out-and-disclosure-form/ . Right to Opt-Out
# of Sale/Sharing only (their Access email is broken and Delete does not exist
# per the site — see README). The page embeds three HubSpot forms via the newer
# `js.hsforms.net/ui-forms-embed-components-app/frame.html` iframe; the opt-out
# form is the one containing a "work email" / "Current Employer" field. Despite
# the marketforcecorp.com note that this embed "renders no fields standalone",
# pydoll's `.find()` on the iframe WebElement DOES resolve into it here.
#
# Fields (frame 0): 0-1/firstname, 0-1/lastname, 0-1/work_email, 0-1/company
# (current employer name), 0-2/address / 0-2/city / 0-2/state / 0-2/zip
# (employer address — filled from the persona's address, the best available).
# Invisible reCAPTCHA Enterprise gates submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://salutarydata.com/privacy-opt-out-and-disclosure-form/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(10)

        iframes = await tab.find(
            xpath="//iframe[contains(@src,'ui-forms-embed-components-app')]",
            find_all=True,
            raise_exc=False,
        ) or []
        target = None
        for ifr in iframes:
            probe = await ifr.find(xpath="//input[@name='0-1/work_email']", raise_exc=False)
            if probe:
                target = ifr
                break
        if not target:
            print(f"{super_scraper.OOPS} opt-out HubSpot form iframe not found")
            return

        fields = {
            "0-1/firstname": SuperScraper.FIRST_NAME,
            "0-1/lastname": SuperScraper.LAST_NAME,
            "0-1/work_email": SuperScraper.EMAIL,
            "0-1/company": SuperScraper.COMPANY_NAME,
            "0-2/address": SuperScraper.ADDRESS,
            "0-2/city": SuperScraper.CITY,
            "0-2/state": SuperScraper.STATE,
            "0-2/zip": SuperScraper.ZIP_CODE,
        }
        for name, value in fields.items():
            if not value:
                continue
            el = await target.find(xpath=f"//input[@name={name!r}]", raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field name={name!r} not found in frame")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/salutarydata_dry_run.png", beyond_viewport=True)
        print("Opt-out request filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())
