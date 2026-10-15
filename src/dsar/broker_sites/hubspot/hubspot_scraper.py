# hubspot.com — same DataGrail Privacy Request Center template as
# bridg.com/clearbit.com/crunchbase.com/hightouch.com elsewhere in this
# repo (identical field names/ids: first_name, last_name, email_address,
# mui-component-select-data_subject_relationship, privacy-request-center-
# region-picker). Country/State default correctly to United States/the
# configured STATE without needing to be touched, but set explicitly anyway
# for correctness. Unlike hightouch.com, there is no combined "Deletion or
# Opt Out" card and no sub-select — only Access/Deletion/Transfer/Update
# Inaccuracies cards, no standalone opt-out-of-sale right offered at all.
# Relationship dropdown answered "Other" (closest generic fit). No captcha
# observed. Which rights run is decided only by SuperScraper.rights_to_exercise.
#
# Page elements:
#   #privacy-request-center-region-picker   State / region picker (combobox)
#   li[aria-label=<STATE>]                  State option in that picker
#   "Start Access Request" / "Start Deletion Request"   request cards
#   input[name=first_name] / [name=last_name]   First / Last name
#   input[name=email_address]               Email address
#   div[aria-labelledby=mui-component-select-data_subject_relationship]
#                                           "Data subject relationship" select -> "Other"
#   "Review Request" / "Submit Request"     review and final submit buttons
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://preferences.hubspot.com/?locale=en"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access Request",
    Right.RIGHT_TO_DELETE: "Deletion Request",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, entry, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_field = await tab.find(id="privacy-request-center-region-picker", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.5)
        state_opt = await tab.find(
            xpath=f"//li[@role='option' and @aria-label='{SuperScraper.STATE}']", raise_exc=False
        )
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(0.5)

    start_btn = await tab.find(text=f"Start {entry}", raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} 'Start {entry}' button not found")
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
            entries = RIGHT_MAP[right]
            for entry in (entries if isinstance(entries, list) else [entries]):
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())
