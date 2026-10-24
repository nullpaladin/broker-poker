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
# One submission per right (Access, Third Parties We Share With, Opt Out of
# Sales/Shares/Targeted Advertising, Delete), decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Correct is not automated.
# The state select lists only states with a privacy law, so users in other states
# cannot use this form (SERVES_NO_LAW_STATES = False).
# reCAPTCHA is invisible (badge only, no challenge widget ever renders) —
# auto-resolves, no manual solve needed.
#
# Page elements:
#   request cards (clicked by text)   one per request type (see RIGHT_MAP)
#   #text-field-firstName / #text-field-lastName / #text-field-email   First / Last name, Email
#   #select-field-country             Country <select> (value "US")
#   #select-field-state_              State <select> (lowercase full name)
#   #select-field-typeCode            "I am a (an)" <select> (-> "customer")
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://videoamp.com/your-privacy-choices"

SERVES_NO_LAW_STATES = False

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request to Know/Access Your Personal Information",
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "Request to Know to Specific Third Parties We Share Your Personal Information With",
    Right.RIGHT_TO_OPT_OUT: "Request to Opt Out of Sales/Shares/Targeted Advertising",
    Right.RIGHT_TO_DELETE: "Request to Delete Your Personal Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The Correct card's title is not recorded, so no inventory is built.)

FIELD_XPATHS = {
    "First name": "//*[@id='text-field-firstName']",
    "Last name": "//*[@id='text-field-lastName']",
    "Email": "//*[@id='text-field-email']",
    "Country": "//*[@id='select-field-country']",
    "State": "//*[@id='select-field-state_']",
    "I am a (an)": "//*[@id='select-field-typeCode']",
}


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
        await js_utils.select_native_option(country_select, value="US")
    else:
        print(f"{super_scraper.OOPS} Country select not found")

    state_select = await tab.find(id="select-field-state_", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, value=SuperScraper.STATE.lower())
    else:
        print(f"{super_scraper.OOPS} State select not found")

    type_select = await tab.find(id="select-field-typeCode", raise_exc=False)
    if type_select:
        await js_utils.select_native_option(type_select, value="customer")
    else:
        print(f"{super_scraper.OOPS} 'I am a (an)' select not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(f"\n'{card_text}' request filled but NOT submitted (invisible reCAPTCHA, no manual solve needed).")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
