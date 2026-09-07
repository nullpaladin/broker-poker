# fetcher.ai — https://app.fetcher.ai/opt-out . Small React/Ant-Design form,
# opt-out only: "If we have a record of you in our database we will process your
# request for removal once you hit submit." Every other right is email-only
# (support@fetcher.ai — privacy@fetcher.ai does not exist) per README.
# Fields: #first_name, #last_name, #email, then a reCAPTCHA v2 checkbox and
# Submit — filled to that point and left for a manual solve.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://app.fetcher.ai/opt-out"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/fetcher_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/fetcher_dry_run.png")
        print(
            "Opt-out request filled but NOT submitted — solve the reCAPTCHA v2 "
            "checkbox manually, then click Submit."
        )


asyncio.run(main())
