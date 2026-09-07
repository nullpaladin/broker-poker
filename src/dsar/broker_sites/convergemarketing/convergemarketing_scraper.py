# convergemarketing.com — Osano DataSubject privacy portal (my.datasubject.com).
# After a card is clicked the fields are given-name / family-name / email /
# phone-number and a "representative-type" select (set to "Myself"). No address
# fields on this deployment.
# Cards found by their h4[data-testid="card-title"] text. One card/right per
# pass: Summarize (Access), Do Not Sell or Share to a Third Party, Don't use my
# personal information for advertising, Opt Out of Profiling / Automated
# Decision-Making, Transfer my personal information (portability), "Third
# parties your data was sold or shared with" unconditionally; Delete my personal
# information gated on REMOVE_INFORMATION. "Correct my personal information" and
# "Other" skipped (nothing concrete to describe).
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/FMy59nP1cQ/53694"

RIGHT_MAP = {
    "access": [("Summarize my personal information", "access")],
    "opt_out_sale_share": [("Do Not Sell or Share to a Third Party", "opt_out_sale")],
    "opt_out_targeted_ads": [("Don't use my personal information for advertising", "opt_out_ads")],
    "opt_out_profiling": [("Opt Out of Profiling / Automated Decision-Making", "opt_out_profiling")],
    "portability": [("Transfer my personal information", "portability")],
    "know_third_parties": [("Third parties your data was sold or shared with", "third_parties")],
    "delete": [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

FIELDS = {
    "given-name": "FIRST_NAME",
    "family-name": "LAST_NAME",
    "email": "EMAIL",
    "phone-number": "PHONE_NUMBER",
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
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    # NOTE: name="representative-type" is the "I am submitting this request on
    # behalf of someone other than myself." CHECKBOX — left UNCHECKED (default)
    # so this stays a self-submission. Ticking it reveals a required
    # Representative section incl. a proof-of-authorization file upload.

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/convergemarketing_dry_run_{label}.png")
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
