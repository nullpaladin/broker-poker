# videoamp.com — Ketch-powered "Privacy Center" (new platform for this
# repo) at videoamp.com/your-privacy-choices. Loads fine directly, no VPN
# needed (an earlier repo note suspected a geo-restriction, not confirmed
# here). Each request type is its own card on the landing screen; clicking
# one reveals an identical 6-field form (verified across two request types)
# — First Name, Last Name, Email, Country, State, "I am a (an)". "I am a
# (an)" (select-field-typeCode) only offers "Customer"/"Authorized Agent" —
# "Customer" used as the closest fit (no generic-visitor option). Country
# select value is the 2-letter code ("US"). State select only lists the ~19
# states with applicable privacy laws, keyed by lowercase full name (e.g.
# "minnesota") — statically present regardless of country selection order.
# One submission per right: Access, Third Parties We Share With, Opt Out of
# Sales/Shares/Targeted Advertising unconditionally; Delete gated on
# REMOVE_INFORMATION. Correct skipped (no concrete inaccuracy to describe).
# reCAPTCHA is invisible (badge only, no challenge widget ever renders) —
# auto-resolves, no manual solve needed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://videoamp.com/your-privacy-choices"

RIGHT_MAP = {
    "access": ["Request to Know/Access Your Personal Information"],
    "know_third_parties": ["Request to Know to Specific Third Parties We Share Your Personal Information With"],
    "opt_out_sale_share": ["Request to Opt Out of Sales/Shares/Targeted Advertising"],
    "opt_out_targeted_ads": ["Request to Opt Out of Sales/Shares/Targeted Advertising"],
    "delete": ["Request to Delete Your Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, card_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    card = await tab.find(text=card_text, raise_exc=False)
    if not card:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(2)

    fields = {
        "text-field-firstName": SuperScraper.FIRST_NAME,
        "text-field-lastName": SuperScraper.LAST_NAME,
        "text-field-email": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    country_select = await tab.find(id="select-field-country", raise_exc=False)
    if country_select:
        await _select_native_option(country_select, "US")
    else:
        print(f"{super_scraper.OOPS} Country select not found")

    state_select = await tab.find(id="select-field-state_", raise_exc=False)
    if state_select:
        await _select_native_option(state_select, SuperScraper.STATE.lower())
    else:
        print(f"{super_scraper.OOPS} State select not found")

    type_select = await tab.find(id="select-field-typeCode", raise_exc=False)
    if type_select:
        await _select_native_option(type_select, "customer")
    else:
        print(f"{super_scraper.OOPS} 'I am a (an)' select not found")

    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/videoamp_dry_run_{label}.png")
    print(f"\n'{card_text}' request filled but NOT submitted (invisible reCAPTCHA, no manual solve needed).")


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
        for card_text in rights:
            await submit_request(tab, card_text, super_scraper)


asyncio.run(main())
