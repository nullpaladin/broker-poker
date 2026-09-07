# fraiser.org — Osano DataSubject privacy portal (my.datasubject.com), same
# platform used elsewhere in this repo (e.g. windfall.com). The wrapper page
# at fraiser.org/data-request-form only embeds this via a near-invisible
# (height:0) iframe with no accessible text in the outer document — navigate
# directly to the iframe URL instead. Jurisdiction auto-detects from STATE.
# One card/right per pass, own URL flow (click card -> fill -> submit):
# Correct, Summarize (Access), Transfer (Portability), Do Not Sell/Share,
# Don't Use for Advertising (Opt-Out targeted ads), Third Parties Data Was
# Sold/Shared With, Opt-Out of Profiling unconditionally; Delete gated on
# REMOVE_INFORMATION. "I am submitting this request for" select set to
# "Myself". Cloudflare Turnstile present — requires manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://my.datasubject.com/Azq9ITU2sQioIKhOV/44046"

RIGHT_MAP = {
    "correct": [("Correct my personal information", "correct")],
    "access": [("Summarize my personal information", "access")],
    "portability": [("Transfer my personal information", "portability")],
    "opt_out_sale_share": [("Do Not Sell or Share to a Third Party", "opt_out_sale")],
    "opt_out_targeted_ads": [("Don't use my personal information for advertising", "opt_out_ads")],
    "know_third_parties": [("Third parties your data was sold or shared with", "third_parties")],
    "opt_out_profiling": [("Opt Out of Profiling / Automated Decision-Making", "opt_out_profiling")],
    "delete": [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, card_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    card = await tab.find(text=card_text, raise_exc=False)
    if not card:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(1)

    await tab.execute_script(
        'var s = document.querySelector("select[name=\\"o-submitter\\"]"); '
        's.value = "Myself"; s.dispatchEvent(new Event("change"));'
    )

    for name, value in [
        ("email", SuperScraper.EMAIL),
        ("given-name", SuperScraper.FIRST_NAME),
        ("family-name", SuperScraper.LAST_NAME),
        ("o-address-line-1", SuperScraper.ADDRESS),
        ("o-city", SuperScraper.CITY),
        ("o-state", SuperScraper.STATE),
        ("o-zip", SuperScraper.ZIP_CODE),
        ("phone-number", SuperScraper.PHONE_NUMBER),
    ]:
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{card_text}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/fraiser_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{card_text}'. Solve the Cloudflare Turnstile challenge,")
    print("click Submit, then press Enter once the confirmation appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{card_text}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{card_text}' — verify in browser")


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
