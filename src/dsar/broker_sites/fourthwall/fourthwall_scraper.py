# fourthwall.tv — "Do Not Sell or Share" opt-out form (Wix form) at
# fourthwall.tv/donotsellorshare-fourthwall.
# Right to Opt-Out ONLY — the site offers no Access/Delete/Correct mechanism
# even though its privacy policy says those rights exist (privacypolicy@
# fourthwall.tv never responded; a complaint may be the only escalation).
# Server-rendered; field `name` attributes contain spaces/slashes so are matched
# verbatim: first-name, last-name, email, phone, street-address,
# "street-address line 2", city, "region/state/province", "postal-/ zip code".
# The optional "Country" field is a Wix dropdown component (not a native
# <select>) and is left blank — it has no required marker. reCAPTCHA v2 gates
# submission — the form is filled and left for a manual solve.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.fourthwall.tv/donotsellorshare-fourthwall"

FIELDS = [
    ("first-name", "FIRST_NAME"),
    ("last-name", "LAST_NAME"),
    ("email", "EMAIL"),
    ("phone", "PHONE_NUMBER"),
    ("street-address", "ADDRESS"),
    ("city", "CITY"),
    ("region/state/province", "STATE"),
    ("postal-/ zip code", "ZIP_CODE"),
]


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        for name, attr in FIELDS:
            value = getattr(SuperScraper, attr, None)
            if not value:
                continue
            # first matching input — the opt-out form is the first form on the page
            field = await tab.find(xpath=f"(//input[@name={name!r}])[1]", timeout=5, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "resources/screenshots/fourthwall_dry_run.png")
        print(
            "Opt-out request filled but NOT submitted — a reCAPTCHA v2 checkbox "
            "must be solved manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the reCAPTCHA, click Submit, then press Enter once confirmed...")
            input()
            source = await tab.page_source
            if any(w in source.lower() for w in ("thank", "success", "received", "submitted")):
                print(f"Submitted opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            else:
                print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
