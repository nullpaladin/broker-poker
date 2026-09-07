# snov.io — /do-not-sell-my-personal-information is a custom opt-out-only
# form (no Right to Access or Delete on this page — just a single "Do not
# sell my personal information" checkbox, the only option offered). Field
# names are random UUID-suffixed hashes, targeted by their stable `id`
# instead. Country/State are plain free text (full names). Both a visible
# reCAPTCHA v2 checkbox and a hidden Cloudflare Turnstile response field are
# present — **CAPTCHA solution required**. Even past the CAPTCHA, submitting
# reveals an OTP code input (`otpInput`/`otpSubmitBtn`) — a verification code
# emailed to the supplied address that must be entered to complete the
# request, which this repo has no way to read from a real inbox; form filled
# and left at the CAPTCHA gate regardless.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://snov.io/do-not-sell-my-personal-information"


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
            "name": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "pcode": SuperScraper.ZIP_CODE,
            "country": "United States",
        }
        for field_id, value in fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        requested_checkbox = await tab.find(id="requested", raise_exc=False)
        if requested_checkbox:
            await requested_checkbox.click()
        else:
            print(f"{super_scraper.OOPS} 'Do not sell my personal information' checkbox not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/snov_dry_run.png")
        print("Screenshot saved to resources/screenshots/snov_dry_run.png")
        print(
            "\nOpt-out request filled but NOT submitted — a reCAPTCHA v2 checkbox requires a "
            "manual solve before submitting, and a follow-up email OTP code (not readable by "
            "this repo) would still be required to complete the request afterward."
        )


asyncio.run(main())
