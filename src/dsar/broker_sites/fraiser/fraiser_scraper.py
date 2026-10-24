# fraiser.org — Osano DataSubject privacy portal (my.datasubject.com), same
# platform used elsewhere in this repo (e.g. windfall.com). The wrapper page
# at fraiser.org/data-request-form only embeds this via a near-invisible
# (height:0) iframe with no accessible text in the outer document — navigate
# directly to the iframe URL instead. Jurisdiction auto-detects from STATE.
# One card per right, each its own URL flow (click card -> fill -> submit).
# Which cards run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Correct my personal information" is not automated (PAGE_RIGHTS -> None).
# Cloudflare Turnstile present — requires manual solve in live mode.
#
# Page elements (cards are matched by their visible text):
#   Card "Summarize my personal information"                 -> Access
#   Card "Transfer my personal information"                  -> Access (portability)
#   Card "Do Not Sell or Share to a Third Party"             -> Opt-out
#   Card "Don't use my personal information for advertising" -> Opt-out (targeted ads)
#   Card "Opt Out of Profiling / Automated Decision-Making"  -> Opt-out
#   Card "Third parties your data was sold or shared with"   -> List of third parties
#   Card "Delete my personal information"                    -> Delete
#   select[name=o-submitter]  "I am submitting this request for" -> "Myself"
#   email / given-name / family-name       Email / First name / Last name
#   o-address-line-1 / o-city / o-state / o-zip   Street address / City / State / ZIP
#   phone-number                           Phone number
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/Azq9ITU2sQioIKhOV/44046"

SUBMITTER_SELECT_NAME = "o-submitter"  # "I am submitting this request for"

# Right -> list of (card text, screenshot label); one pass per card.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        ("Summarize my personal information", "access"),
        ("Transfer my personal information", "portability"),
    ],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell or Share to a Third Party", "opt_out_sale"),
        ("Don't use my personal information for advertising", "opt_out_ads"),
        ("Opt Out of Profiling / Automated Decision-Making", "profiling"),
    ],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: [
        ("Third parties your data was sold or shared with", "third_parties"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Cards the portal offers -> the Right they map to (None = deliberately not automated).
PAGE_RIGHTS = {
    "Correct my personal information": None,
    "Summarize my personal information": Right.RIGHT_TO_ACCESS,
    "Transfer my personal information": Right.RIGHT_TO_ACCESS,
    "Do Not Sell or Share to a Third Party": Right.RIGHT_TO_OPT_OUT,
    "Don't use my personal information for advertising": Right.RIGHT_TO_OPT_OUT,
    "Third parties your data was sold or shared with": Right.RIGHT_TO_LIST_OF_THIRD_PARTIES,
    "Opt Out of Profiling / Automated Decision-Making": Right.RIGHT_TO_OPT_OUT,
    "Delete my personal information": Right.RIGHT_TO_DELETE,
}


async def submit_request(tab, card_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    card = await tab.find(text=card_text, raise_exc=False)
    if not card:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(1)

    submitter = await tab.find(name=SUBMITTER_SELECT_NAME, raise_exc=False)
    if submitter:
        await js_utils.select_native_option(submitter, value="Myself", dispatch=("change",))
    else:
        print(f"{super_scraper.OOPS} 'submitting this request for' select not found")

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
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{card_text}'. Solve the Cloudflare Turnstile challenge,")
    print("click Submit, then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{card_text}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            for card_text, label in RIGHT_MAP[right]:
                await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())
