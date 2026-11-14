# diablomedia.com — Osano DataSubject privacy portal (my.datasubject.com),
# embedded on diablomedia.com/privacy-request/ via a src'd iframe; navigate
# straight to the underlying form URL.
# This deployment is the MINIMAL DataSubject variant: after a card is clicked
# the only fields are email / given-name / family-name (no address, phone, or
# representative-type — unlike arccorp.com/windfall.com elsewhere in this repo).
# Jurisdiction auto-detects from the request context. One card/right per pass.
# Which cards run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Correct" and "Other" cards are skipped (nothing concrete to describe).
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
#
# Page elements:
#   h4[data-testid=card-title]   Request cards (texts in RIGHT_MAP)
#   [name=given-name] / [name=family-name] / [name=email]   First name / Last name / Email
#   [name=phone-number], [name=o-Physical Address], [name=o-City], [name=o-State],
#   [name=o-Zip Code]            Optional fields (filled only when the form shows them)
#   [name=representative-type]   "On behalf of someone else" checkbox — left unchecked
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/aSCwO6P3vw/60584"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Summarize my personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell or Share to a Third Party", "opt_out_sale"),
        ("Don't use my personal information for advertising", "opt_out_ads"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "h4[data-testid='card-title']"

FIELD_XPATHS = {
    "First name": "//*[@name='given-name']",
    "Last name": "//*[@name='family-name']",
    "Email": "//*[@name='email']",
}

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

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    # NOTE: any name="representative-type" control is the "on behalf of someone
    # else" checkbox — left UNCHECKED (default) so this stays a self-submission.

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
