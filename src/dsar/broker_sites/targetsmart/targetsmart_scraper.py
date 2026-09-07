# targetsmart.com — TargetSmart privacy request, step 1 of an email-verification
# flow (privacy.targetsmart.com/US/email/verify/form/). Same shape as
# steppingblocks.com: you enter your email here, receive a verification email,
# and complete the actual request details from the link in that email.
# This step is a bare form: email, email_confirm, reCAPTCHA v2, Submit.
# The scraper fills both email fields and leaves the reCAPTCHA for a manual
# solve; the emailed follow-up form is not automatable without a real inbox.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.targetsmart.com/US/email/verify/form/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='email']", text=SuperScraper.EMAIL, sleep=0.3)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='email_confirm']", text=SuperScraper.EMAIL, sleep=0.3)

        time.sleep(0.5)
        await tab.take_screenshot("resources/screenshots/targetsmart_dry_run.png")
        print("Screenshot saved to resources/screenshots/targetsmart_dry_run.png")
        print(
            "Email verification form filled but NOT submitted — solve the reCAPTCHA and "
            "click Submit; then complete the request from the link emailed to you."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the reCAPTCHA, click Submit, then press Enter once confirmed...")
            input()


asyncio.run(main())
