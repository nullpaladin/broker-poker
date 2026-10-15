# arccorp.com — Osano DataSubject privacy portal (my.datasubject.com).
# This deployment has the fuller field set: after a card is clicked the fields
# are email / given-name / o-Middle Name (if applicable) / family-name /
# o-Physical Address / o-City / o-State / o-Zip Code / o-Country plus optional
# o-Credit Card and o-Minor Children (left empty) and a "representative-type"
# select ("Myself"). The o-* fields are single free-text inputs.
# Cards found by their h4[data-testid="card-title"] text. One card/right per
# pass. Rights the form exposes: Summarize my personal information (Access), Transfer my
# personal information (portability, also RIGHT_TO_ACCESS), Do Not Sell or Share to a Third
# Party / Don't use my personal information for advertising / Opt Out of Profiling /
# Automated Decision-Making (all RIGHT_TO_OPT_OUT), "Third parties your data was sold or
# shared with" (list of third parties) and Delete my personal information. Which run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). "Correct my personal
# information" is skipped (nothing concrete to describe).
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   h4[data-testid=card-title]   Request-type cards (see RIGHT_MAP)
#   name=given-name / family-name   First / Last name
#   name=email                   Email
#   name=o-Physical Address / o-City / o-State / o-Zip Code / o-Country   Address fields
#   name=representative-type     "I am submitting this request on behalf of someone other than
#                                myself." checkbox (left unchecked)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/Uw03R7mCGS/60313"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        ("Summarize my personal information", "access"),
        ("Transfer my personal information", "transfer"),
    ],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell or Share to a Third Party", "opt_out_sale"),
        ("Don't use my personal information for advertising", "opt_out_ads"),
        ("Opt Out of Profiling / Automated Decision-Making", "opt_out_automated_decisions"),
    ],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: [("Third parties your data was sold or shared with", "third_parties")],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

FIELDS = {
    "given-name": "FIRST_NAME",
    "family-name": "LAST_NAME",
    "email": "EMAIL",
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
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    country = await tab.find(name="o-Country", timeout=4, raise_exc=False)
    if country:
        await country.type_text("United States")

    # NOTE: name="representative-type" is the "I am submitting this request on
    # behalf of someone other than myself." CHECKBOX — left UNCHECKED (default)
    # so this stays a self-submission. Ticking it reveals a required
    # Representative section incl. a proof-of-authorization file upload.

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile "
        f"checkbox must be solved manually before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for card_text, label in RIGHT_MAP[right]:
                await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())
