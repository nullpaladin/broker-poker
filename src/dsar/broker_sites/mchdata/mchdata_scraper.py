# mchdata.com — /about/ccpaemail. ASP.NET server-rendered page with
# several unrelated forms sharing generic field ids on the same page
# (login, signup, school-closings newsletter) — the actual CCPA opt-out
# form is the one with `id="email"` (name="Email") and the
# `IsCaliforniaResident` radio group (MCHCustomerBoolYes/No). Only
# Opt-Out-of-Sale is offered here — no Access or Delete option on this
# page. The IsCaliforniaResident radio is answered "Yes" for any privacy-law
# state (a broker honoring CCPA must honor the equivalent request from that
# state's residents) and "No" only for genuine no-law states.
# reCAPTCHA v2 present — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.mchdata.com/about/ccpaemail"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        email_field = await tab.find(id="email", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} email field not found")

        radio_id = (
            "MCHCustomerBoolYes"
            if SuperScraper.state_has_privacy_law(SuperScraper.STATE)
            else "MCHCustomerBoolNo"
        )
        resident_radio = await tab.find(id=radio_id, raise_exc=False)
        if resident_radio:
            await resident_radio.click()
        else:
            print(f"{super_scraper.OOPS} California-resident radio '{radio_id}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/mchdata_dry_run.png")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
