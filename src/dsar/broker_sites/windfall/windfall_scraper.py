# windfall.com — Osano DataSubject privacy portal (my.datasubject.com),
# same platform as fraiser.org elsewhere in this repo, but a DIFFERENT set
# of cards and a DIFFERENT address layout — don't assume the two Osano
# deployments share a form shape just because they share a URL pattern.
#
# Cards found by their stable `h4[data-testid="card-title"]` text — a
# plain `tab.find(text=...)` on "Access Request" matched the page's
# <title> tag first (which is also literally "Access Request" for that
# card) and raised ElementNotVisible, so cards are matched by xpath scoped
# to the card-title heading instead.
#
# One card/right per pass: Access Request, Do Not Sell or Share to a Third
# Party, Don't use my personal information for advertising, Third parties
# your data was sold or shared with, Delete my personal information. Which of
# them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Correct my personal information" and "Other" are not automated. No
# Transfer/Portability or Opt-Out-of-Profiling cards exist on this
# instance (unlike fraiser.org).
#
# Address is a granular parsed layout (House Number/Direction/Street Name/
# Address Suffix/Post Direction/Unit Prefix/Unit Value/City/State/Zipcode)
# rather than a single free-text line — this repo's single ADDRESS string
# ("123 Main Street") is split naively: first token = house number, last
# token = suffix, everything between = street name.
#
# Access Request ADDITIONALLY requires a "Proof of Identity" file upload
# (no equivalent card requires this) — this repo has no real ID document
# to supply, so that field is left empty; a real submission would need a
# manual file attached. Cloudflare Turnstile — **CAPTCHA solution
# required**.
#
# Page elements:
#   h4[data-testid=card-title]   Request cards (see RIGHT_MAP for the titles)
#   [name=given-name] / [name=family-name]   First / Last name
#   [name=email] / [name=phone-number]       Email / Phone
#   [name=o-house-number] / [name=o-street-name] / [name=o-address-suffix]   Address parts
#   [name=o-city] / [name=o-state] / [name=o-zipcode]   City / State / Zipcode
#   Proof of Identity file upload (Access Request only; not automated)
#   Cloudflare Turnstile checkbox (manual solve)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://my.datasubject.com/AkrxLuYOww/60579"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access Request",
    Right.RIGHT_TO_OPT_OUT: [
        "Do Not Sell or Share to a Third Party",
        "Don't use my personal information for advertising",
    ],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "Third parties your data was sold or shared with",
    Right.RIGHT_TO_DELETE: "Delete my personal information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request card title, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Access Request": Right.RIGHT_TO_ACCESS,
    "Do Not Sell or Share to a Third Party": Right.RIGHT_TO_OPT_OUT,
    "Don't use my personal information for advertising": Right.RIGHT_TO_OPT_OUT,
    "Third parties your data was sold or shared with": Right.RIGHT_TO_LIST_OF_THIRD_PARTIES,
    "Delete my personal information": Right.RIGHT_TO_DELETE,
    "Correct my personal information": None,
    "Other": None,
}
RIGHTS_OPTIONS_CSS = "h4[data-testid='card-title']"

FIELD_XPATHS = {
    "First name": "//*[@name='given-name']",
    "Last name": "//*[@name='family-name']",
    "Email": "//*[@name='email']",
    "City": "//*[@name='o-city']",
    "State": "//*[@name='o-state']",
    "Zipcode": "//*[@name='o-zipcode']",
}


def _split_address(address):
    parts = address.split()
    if len(parts) < 2:
        return "", address, ""
    house_number = parts[0]
    suffix = parts[-1]
    street_name = " ".join(parts[1:-1]) or parts[-1]
    return house_number, street_name, suffix


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

    house_number, street_name, suffix = _split_address(SuperScraper.ADDRESS)
    fields = {
        "given-name": SuperScraper.FIRST_NAME,
        "family-name": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "phone-number": SuperScraper.PHONE_NUMBER,
        "o-house-number": house_number,
        "o-street-name": street_name,
        "o-address-suffix": suffix,
        "o-city": SuperScraper.CITY,
        "o-state": SuperScraper.STATE,
        "o-zipcode": SuperScraper.ZIP_CODE,
    }
    for name, value in fields.items():
        if not value:
            continue
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{name}' not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label_suffix = (
        " (Proof of Identity file upload not automated — attach manually before submitting)"
        if right == Right.RIGHT_TO_ACCESS else ""
    )
    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile checkbox "
        f"requires a manual solve before submitting.{label_suffix}"
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
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
