# convergemarketing.com — Osano DataSubject privacy portal (my.datasubject.com).
# After a card is clicked the fields are given-name / family-name / email /
# phone-number and a "representative-type" checkbox. No address fields on this
# deployment. One card per pass. "Correct my personal information" and "Other"
# cards are skipped (not automatable / nothing concrete to describe).
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
#
# Page elements:
#   h4[data-testid="card-title"]   Request cards (see RIGHT_MAP for the titles used)
#   given-name / family-name       First / Last name (by name=)
#   email                          Email
#   phone-number                   Phone
#   representative-type            "I am submitting this request on behalf of someone other
#                                  than myself." checkbox — left unchecked
import asyncio
import re

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/FMy59nP1cQ/53694"

CARD_SUMMARIZE = "Summarize my personal information"
CARD_TRANSFER = "Transfer my personal information"
CARD_DO_NOT_SELL = "Do Not Sell or Share to a Third Party"
CARD_NO_ADS = "Don't use my personal information for advertising"
CARD_NO_PROFILING = "Opt Out of Profiling / Automated Decision-Making"
CARD_THIRD_PARTIES = "Third parties your data was sold or shared with"
CARD_DELETE = "Delete my personal information"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CARD_SUMMARIZE, CARD_TRANSFER],
    Right.RIGHT_TO_OPT_OUT: [CARD_DO_NOT_SELL, CARD_NO_ADS, CARD_NO_PROFILING],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: CARD_THIRD_PARTIES,
    Right.RIGHT_TO_DELETE: CARD_DELETE,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request card title, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    CARD_SUMMARIZE: Right.RIGHT_TO_ACCESS,
    CARD_TRANSFER: Right.RIGHT_TO_ACCESS,
    CARD_DO_NOT_SELL: Right.RIGHT_TO_OPT_OUT,
    CARD_NO_ADS: Right.RIGHT_TO_OPT_OUT,
    CARD_NO_PROFILING: Right.RIGHT_TO_OPT_OUT,
    CARD_THIRD_PARTIES: Right.RIGHT_TO_LIST_OF_THIRD_PARTIES,
    CARD_DELETE: Right.RIGHT_TO_DELETE,
    "Correct my personal information": None,
    "Other": None,
}
RIGHTS_OPTIONS_CSS = "h4[data-testid='card-title']"

FIELDS = {
    "given-name": "FIRST_NAME",
    "family-name": "LAST_NAME",
    "email": "EMAIL",
    "phone-number": "PHONE_NUMBER",
}


async def submit_request(tab, right, card_text, super_scraper):
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
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {name: f"//*[@name='{name}']" for name in FIELDS})

    # NOTE: name="representative-type" is the "I am submitting this request on
    # behalf of someone other than myself." CHECKBOX — left UNCHECKED (default)
    # so this stays a self-submission. Ticking it reveals a required
    # Representative section incl. a proof-of-authorization file upload.

    await asyncio.sleep(1)
    slug = re.sub(r"[^a-z0-9]+", "_", card_text.lower()).strip("_")
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{slug}")
    print(
        f"'{right.name}' request ('{card_text}') filled but NOT submitted — a Cloudflare Turnstile "
        f"checkbox must be solved manually before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            entries = RIGHT_MAP[right]
            for card_text in (entries if isinstance(entries, list) else [entries]):
                await submit_request(tab, right, card_text, super_scraper)


asyncio.run(main())
