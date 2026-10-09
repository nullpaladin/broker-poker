# diablomedia.com — Osano DataSubject privacy portal (my.datasubject.com),
# embedded on diablomedia.com/privacy-request/ via a src'd iframe; navigate
# straight to the underlying form URL.
# This deployment is the MINIMAL DataSubject variant: after a card is clicked
# the only fields are email / given-name / family-name (no address, phone, or
# representative-type — unlike arccorp.com/windfall.com elsewhere in this repo).
# Jurisdiction auto-detects from the request context. One card/right per pass —
# Summarize (Access), Do Not Sell or Share, Don't use for advertising
# unconditional; Delete gated on REMOVE_INFORMATION. "Correct" and "Other"
# skipped (nothing concrete to describe). Cloudflare Turnstile gates the
# submit — form filled and left for a manual solve.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/aSCwO6P3vw/60584"

RIGHT_MAP = {
    "access": [("Summarize my personal information", "access")],
    "opt_out_sale_share": [("Do Not Sell or Share to a Third Party", "opt_out_sale")],
    "opt_out_targeted_ads": [("Don't use my personal information for advertising", "opt_out_ads")],
    "delete": [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

FIELDS = {
    "given-name": "FIRST_NAME",
    "family-name": "LAST_NAME",
    "email": "EMAIL",
    "phone-number": "PHONE_NUMBER",
    "o-Physical Address": "ADDRESS",
    "o-City": "CITY",
    "o-State": "STATE",
    "o-Zip Code": "ZIP_CODE",
}


async def submit_request(tab, card_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    card = await tab.find(
        xpath=f"//h4[@data-testid='card-title' and normalize-space()={card_text!r}]", raise_exc=False
    )
    if not card:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(2)

    for name, attr in FIELDS.items():
        value = getattr(SuperScraper, attr, None)
        if not value:
            continue
        field = await tab.find(name=name, timeout=3, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    # NOTE: any name="representative-type" control is the "on behalf of someone
    # else" checkbox — left UNCHECKED (default) so this stays a self-submission.

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/diablomedia_dry_run_{label}.png")
    print(
        f"'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile "
        f"checkbox must be solved manually before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for card_text, label in rights:
            await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())
