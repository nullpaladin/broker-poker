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
# your data was sold or shared with unconditionally; Delete my personal
# information gated on REMOVE_INFORMATION. Correct my personal information
# and Other skipped (no concrete inaccuracy/inquiry to describe). No
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
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://my.datasubject.com/AkrxLuYOww/60579"

RIGHTS = [
    ("Access Request", "access"),
    ("Do Not Sell or Share to a Third Party", "opt_out_sale"),
    ("Don't use my personal information for advertising", "opt_out_ads"),
    ("Third parties your data was sold or shared with", "third_parties"),
]
DELETE_RIGHT = ("Delete my personal information", "delete")


def _split_address(address):
    parts = address.split()
    if len(parts) < 2:
        return "", address, ""
    house_number = parts[0]
    suffix = parts[-1]
    street_name = " ".join(parts[1:-1]) or parts[-1]
    return house_number, street_name, suffix


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

    label_suffix = " (Proof of Identity file upload not automated — attach manually before submitting)" if label == "access" else ""

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/windfall_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/windfall_dry_run_{label}.png")
    print(
        f"\n'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile checkbox "
        f"requires a manual solve before submitting.{label_suffix}"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for card_text, label in rights:
            await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())
