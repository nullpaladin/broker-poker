# minerva.io — same DataGrail Privacy Request Center template as
# bridg.com/clearbit.com/crunchbase.com/hightouch.com/hubspot.com/
# inmarket.com elsewhere in this repo (identical field names/ids:
# first_name, last_name, email_address, mui-component-select-
# data_subject_relationship, privacy-request-center-region-picker).
# Separate Access/Deletion/Opt Out/Transfer/Update Inaccuracies cards, like
# crunchbase.com — Transfer/Update Inaccuracies skipped as auxiliary.
# Country/State default correctly to United States/the configured STATE.
# Relationship dropdown answered "Other". No captcha observed. Which rights run
# (Access, Opt Out, Deletion) is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   #privacy-request-center-region-picker   State picker (type, click matching li[role=option])
#   "Start <card>" button      per-right card (see RIGHT_MAP)
#   input[name=first_name] / [name=last_name]   First / Last name
#   input[name=email_address]  Email
#   [aria-labelledby=mui-component-select-data_subject_relationship]   Relationship dropdown -> "Other"
#   "Review Request" / "Submit Request" buttons
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://preferences.minerva.io/"

STATE_PICKER = "privacy-request-center-region-picker"  # State picker

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access Request",
    Right.RIGHT_TO_OPT_OUT: "Opt Out Request",
    Right.RIGHT_TO_DELETE: "Deletion Request",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, option, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_field = await tab.find(id=STATE_PICKER, raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.5)
        state_opt = await tab.find(xpath=f"//li[@role='option' and @aria-label='{SuperScraper.STATE}']", raise_exc=False)
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(0.5)

    start_btn = await tab.find(text=f"Start {option}", raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} 'Start {option}' button not found")
        return
    await start_btn.click()
    await asyncio.sleep(2)

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

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
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
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
