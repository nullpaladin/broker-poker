# swoop.com — the /your-privacy-choices/ page embeds an Osano DataSubject
# portal (my.datasubject.com) in an iframe — navigate straight to it.
# (The page's Gravity Forms are only a cookie/newsletter widget.)
# After a card is clicked the fields are: requestor-type (select — options
# "Healthcare Professional" / "Consumer" / "Agent for Data Subject", set to
# "Consumer"), given-name, family-name, email, and a representative-type
# "on behalf of someone else" checkbox (left UNCHECKED for a self-submission).
# Cards found by their h4[data-testid="card-title"] text. One card per pass (see
# RIGHT_MAP): "Access or Request to Know" + "Transfer my personal information"
# (Access), "Opt-Out Request" + "Automated Decision-Making" (Opt-Out), "Third
# parties your data was sold or shared with", "Delete my personal information".
# "Correct my personal information" and "Employee Request" are not automated.
# Which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Page elements: select[name=requestor-type], given-name, family-name, email,
# phone-number (inputs by name), representative-type checkbox (left unchecked).
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/16A0AaT1hE8CL2xPu/19933"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        ("Access or Request to Know", "access"),
        ("Transfer my personal information", "transfer"),
    ],
    Right.RIGHT_TO_OPT_OUT: [
        ("Opt-Out Request", "opt_out"),
        ("Automated Decision-Making", "adm"),
    ],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: [
        ("Third parties your data was sold or shared with", "third_parties"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
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

    # requestor-type options: "" / "Healthcare Professional" / "Consumer" /
    # "Agent for Data Subject" — "Consumer" is the right answer for a data
    # subject exercising their own rights.
    rt = await tab.find(name="requestor-type", timeout=4, raise_exc=False)
    if rt:
        await js_utils.select_native_option(rt, text="Consumer", ci=True)

    for name, attr in FIELDS.items():
        value = getattr(SuperScraper, attr, None)
        if not value:
            continue
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    # name="representative-type" is the "on behalf of someone else" checkbox —
    # left UNCHECKED for a self-submission.

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile "
        f"checkbox must be solved manually before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for card_text, label in requests:
            await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())
