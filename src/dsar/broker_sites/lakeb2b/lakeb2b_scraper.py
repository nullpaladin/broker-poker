# lakeb2b.com — /do-not-sell-my-data "Data Alteration Request" form (a
# Contact Form 7 form whose submit button still reads "Get a Quote Now!" from
# the template it was cloned from). Server-rendered, AJAX POST in place.
#
# The two CF7 "acceptance" checkboxes act as the request selector:
#   acceptance1 = "Alter frequency of news notifications ..." (left unchecked)
#   acceptance2 = "Opt-out of the mailing list ..."          (checked)
# There is no Access/Delete option on this form — the site says those go by
# email (privacy@lakeb2b.com) — so this exercises Opt-Out only; the free-text
# "message" field additionally states the request in words.
# Fields: first-name, last-name, your-email, phone, address, city, state, zip,
# message. No CAPTCHA seen.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.lakeb2b.com/do-not-sell-my-data"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        optout = await tab.find(xpath="//input[@name='acceptance2']", raise_exc=False)
        if optout:
            await optout.click()
        else:
            print(f"{super_scraper.OOPS} opt-out acceptance checkbox not found")

        fields = {
            "first-name": SuperScraper.FIRST_NAME,
            "last-name": SuperScraper.LAST_NAME,
            "your-email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
            "message": (
                "I am exercising my right to opt out of the sale and sharing of my "
                "personal information. Please also confirm removal from all marketing lists."
            ),
        }
        for name, val in fields.items():
            if not val:
                continue
            el = await tab.find(xpath=f"//*[@name={name!r}]", raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/lakeb2b_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/lakeb2b_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//input[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out for {SuperScraper.EMAIL}")


asyncio.run(main())
