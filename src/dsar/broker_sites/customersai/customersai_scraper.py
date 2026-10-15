# customers.ai (formerly MobileMonkey) — https://app.mobilemonkey.com/opt-out .
# "Opt Out of Tracking and Personal Data Processing" — opt-out only. Other rights
# are email-only (info@customers.ai, unanswered) per README.
# Fields: email (required), a Zip Code text input, and an "I am an authorized
# agent ..." checkbox (left unchecked for a self-submission). An hCaptcha gates
# the submit — filled to that point.  **CAPTCHA solution required**
#
# Page elements:
#   input[type=email] / [name=email]     Email
#   first form text input (not email)    Zip Code
#   "I am an authorized agent" checkbox  left unchecked
#   hCaptcha + "Opt-Out" button          manual
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://app.mobilemonkey.com/opt-out"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "Opt Out of Tracking and Personal Data Processing"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        email = await tab.find(xpath="//input[@type='email' or @name='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} email field not found")

        # The first non-email text input in the form is the Zip Code field.
        zip_field = await tab.find(
            xpath="(//form//input[@type='text' and not(@name='email')])[1]", raise_exc=False
        )
        if zip_field and SuperScraper.ZIP_CODE:
            await zip_field.type_text(SuperScraper.ZIP_CODE)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        print("Opt-out request filled but NOT submitted — solve the hCaptcha manually, then Opt-Out.")


asyncio.run(main())
