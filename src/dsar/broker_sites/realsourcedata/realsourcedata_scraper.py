# realsourcedata.com — /do-not-sell-my-personal-information embeds a Tally.so
# form via an iframe with a real, populated `src` (unlike HubSpot's src-less
# iframe elsewhere in this repo, which is unreachable) — `tab.get_frame()`
# works here. No Right to Access exists anywhere on the site (confirmed by
# prior manual investigation — this opt-out form is the only privacy
# mechanism offered). Fields have no name/placeholder, only random UUID ids,
# so they're targeted by DOM order (confirmed against the form's visible
# label order: First Name, Last Name, Street Address, City, State, Zip Code,
# Phone Number, Email) rather than by id directly, since Tally regenerates a
# fresh UUID per field on every page load. reCAPTCHA v2 present —
# **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.realsourcedata.com/do-not-sell-my-personal-information"

FIELD_VALUES = [
    SuperScraper.FIRST_NAME,
    SuperScraper.LAST_NAME,
    SuperScraper.ADDRESS,
    SuperScraper.CITY,
    SuperScraper.STATE,
    SuperScraper.ZIP_CODE,
    SuperScraper.PHONE_NUMBER,
    SuperScraper.EMAIL,
]


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        iframe_element = await tab.find(tag_name="iframe", raise_exc=False)
        if not iframe_element:
            print(f"{super_scraper.OOPS} Tally form iframe not found")
            return
        frame = await tab.get_frame(iframe_element)
        await asyncio.sleep(2)

        fields = await frame.find(tag_name="input", find_all=True, raise_exc=False)
        fields = [f for f in fields if f.get_attribute("type") in ("text", "tel", "email")]
        if len(fields) != len(FIELD_VALUES):
            print(f"{super_scraper.OOPS} expected {len(FIELD_VALUES)} fields, found {len(fields)}")
        for field, value in zip(fields, FIELD_VALUES):
            await field.type_text(value)
            await asyncio.sleep(0.2)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/realsourcedata_dry_run.png")
        print("Screenshot saved to resources/screenshots/realsourcedata_dry_run.png")
        print(
            "\nOpt-out request filled but NOT submitted — a reCAPTCHA v2 checkbox requires a "
            "manual solve before submitting."
        )


asyncio.run(main())
