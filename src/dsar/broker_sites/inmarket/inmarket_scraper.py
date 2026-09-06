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
# Deletion). Relationship dropdown answered "Other". Exercises Access and
# Opt Out unconditionally; Deletion gated on REMOVE_INFORMATION. No captcha
# observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

URL = "https://preferences.inmarket.com/?locationCode=US-MN"

ACCESS = ("access", "Start Access Request", None)
OPT_OUT = (
    "opt_out",
    "Start Request to Opt Out or Limit Use of Sensitive Personal Information",
    "Opt out of the sale and/or sharing of my personal information",
)
DELETE = ("delete", "Start Deletion Request", None)


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


async def submit_request(tab, right_id, card_text, sub_choice, super_scraper):
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

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right_id}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/inmarket_dry_run_{right_id}.png")
        print(f"Screenshot saved to resources/screenshots/inmarket_dry_run_{right_id}.png")
        return

    review_btn = await tab.find(text="Review Request", raise_exc=False)
    if review_btn:
        await review_btn.click()
        await asyncio.sleep(2)

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right_id}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{right_id}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = [ACCESS, OPT_OUT]
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_id, card_text, sub_choice in requests:
            await submit_request(tab, right_id, card_text, sub_choice, super_scraper)


asyncio.run(main())
