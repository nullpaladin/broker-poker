# steppingblocks.com — "Personal Information Inquiry" form
# (steppingblocks.com/personal-information-inquiry), a HubSpot form.
# This is the FIRST step only: submitting it triggers an email that asks you to
# fill out the rest of the request yourself (per prior investigation), so the
# scraper just completes this initial form.
# Fields (ids carry a per-render GUID suffix, so target by name): firstname,
# lastname, email, and a "certification" attestation checkbox. reCAPTCHA gates
# submission — form filled and left for a manual solve.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.steppingblocks.com/personal-information-inquiry"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for name, value in [
            ("firstname", SuperScraper.FIRST_NAME),
            ("lastname", SuperScraper.LAST_NAME),
            ("email", SuperScraper.EMAIL),
        ]:
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2
            )

        cert = await tab.find(xpath="//input[@name='certification']", raise_exc=False)
        if cert:
            await SuperScraper.js_check(cert)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/steppingblocks_dry_run.png")
        print(
            "Inquiry form filled but NOT submitted — solve the reCAPTCHA and click Submit; "
            "you will then receive an email asking you to complete the rest of the request."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the reCAPTCHA, click Submit, then press Enter once confirmed...")
            input()


asyncio.run(main())
