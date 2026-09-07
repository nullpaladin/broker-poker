# leadmemedia.com — policy.leadmemedia.com/States/privacyrequestform.html.
# A single server-rendered form with plain, stable field ids/names and a
# select-all-that-apply checkbox group (name=DeleteInfo/NotSell/Access/
# Correct/Limit/NoTarget/ThirdParty) — one submission covers every right
# checked. Correct/Limit/NoTarget/ThirdParty are skipped as auxiliary (not
# core Access/Opt-Out/Delete rights). State is a plain free-text field, not
# a select — the full state name is accepted (no format hint/maxlength
# constraint found). reCAPTCHA v2 present — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://policy.leadmemedia.com/States/privacyrequestform.html"

RIGHT_CHECKBOXES = ["NotSell", "Access"]
DELETE_CHECKBOX = "DeleteInfo"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "email": SuperScraper.EMAIL,
            "first-name": SuperScraper.FIRST_NAME,
            "last-name": SuperScraper.LAST_NAME,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        checkbox_names = list(RIGHT_CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkbox_names.append(DELETE_CHECKBOX)
        for name in checkbox_names:
            checkbox = await tab.find(xpath=f"//input[@name='{name}']", raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{name}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/leadmemedia_dry_run.png")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
