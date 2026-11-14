# inmarket.com — same DataGrail Privacy Request Center template as
# bridg.com/clearbit.com/crunchbase.com/hightouch.com/hubspot.com elsewhere
# in this repo. URL's `?locationCode=US-MN` query param pre-sets
# Country/State (Minnesota, United States) with no need to touch the
# picker at all. Opt-Out and "Limit Sensitive PI" share one combined card
# ("Opt Out Requests and Limit the Use of Sensitive Personal Information
# Requests") with a single-select sub-dropdown (NOT aria-multiselectable —
# one submission per choice) offering exactly those two options; only Opt
# Out is exercised (Limit Sensitive PI treated as auxiliary, same as
# Transfer/Update Inaccuracies elsewhere in this repo). That sub-select and
# the MAID field both have random per-site UUID names/ids, so they're
# targeted positionally rather than by id. InMarket sells location/MAID
# data, so ADVERTISING_ID is filled into the "Your Mobile Advertising ID
# (MAID)" field on the Opt-Out card (present only there, not on Access/
# Deletion). Relationship dropdown answered "Other". Which of Access / Opt Out /
# Deletion run is decided only by SuperScraper.rights_to_exercise. No captcha
# observed.
#
# Page elements:
#   "Start Access Request" / "Start Deletion Request" /
#   "Start Request to Opt Out or Limit Use of Sensitive Personal Information"   request cards
#   input[name=first_name] / [name=last_name]   First / Last name
#   input[name=email_address]                   Email address
#   div[aria-labelledby=mui-component-select-data_subject_relationship]
#                                               "Data subject relationship" select -> "Other"
#   input with a 36-char (UUID) name            "Your Mobile Advertising ID (MAID)" (opt-out card only)
#   div[aria-labelledby=mui-component-select-<uuid>]   opt-out / limit-sensitive-PI sub-select
#   "Review Request" / "Submit Request"         review and final submit buttons
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

URL = "https://preferences.inmarket.com/?locationCode=US-MN"

# Right -> (card button text, sub-select choice or None).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Start Access Request", None),
    Right.RIGHT_TO_OPT_OUT: (
        "Start Request to Opt Out or Limit Use of Sensitive Personal Information",
        "Opt out of the sale and/or sharing of my personal information",
    ),
    Right.RIGHT_TO_DELETE: ("Start Deletion Request", None),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//input[@name='first_name']",
    "Last name": "//input[@name='last_name']",
    "Email": "//input[@name='email_address']",
}


async def _fill_common(tab, super_scraper):
    first = await tab.find(xpath="//input[@name='first_name']", raise_exc=False)
    last = await tab.find(xpath="//input[@name='last_name']", raise_exc=False)
    email = await tab.find(xpath="//input[@name='email_address']", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    relationship = await tab.find(
        xpath="//div[@aria-labelledby='mui-component-select-data_subject_relationship']",
        raise_exc=False,
    )
    if relationship:
        await relationship.click()
        await asyncio.sleep(1)
        other_opt = await tab.find(xpath="//li[normalize-space()='Other']", raise_exc=False)
        if other_opt:
            await other_opt.click()
            await asyncio.sleep(0.5)


async def submit_request(tab, right, card_text, sub_choice, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    start_btn = await tab.find(text=card_text, raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} '{card_text}' button not found")
        return
    await start_btn.click()
    await asyncio.sleep(2)

    await _fill_common(tab, super_scraper)

    if sub_choice is not None:
        maid_field = await tab.find(
            xpath="//input[@name and string-length(@name)=36 and not(@name='data_subject_relationship')]",
            raise_exc=False,
        )
        if maid_field and SuperScraper.ADVERTISING_ID:
            await maid_field.type_text(SuperScraper.ADVERTISING_ID)

        # the "Limit sensitive PI"/"Opt Out" sub-select — targeted
        # positionally since its own DOM id is a random per-site UUID, not
        # a stable name
        type_div = await tab.find(
            xpath="//div[starts-with(@aria-labelledby,'mui-component-select-') "
            "and not(contains(@aria-labelledby,'data_subject_relationship'))]",
            raise_exc=False,
        )
        if type_div:
            await type_div.click()
            await asyncio.sleep(1)
            sub_opt = await tab.find(
                xpath=f"//li[normalize-space()='{sub_choice}']", raise_exc=False
            )
            if sub_opt:
                await sub_opt.click()
                await asyncio.sleep(0.5)
                await tab.keyboard.press(Key.ESCAPE)
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} sub-option '{sub_choice}' not found")
        else:
            print(f"{super_scraper.OOPS} opt-out/limit-PI sub-select not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    review_btn = await tab.find(text="Review Request", raise_exc=False)
    if review_btn:
        await review_btn.click()
        await asyncio.sleep(2)

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{right.name}'")


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
            card_text, sub_choice = RIGHT_MAP[right]
            await submit_request(tab, right, card_text, sub_choice, super_scraper)


asyncio.run(main())
