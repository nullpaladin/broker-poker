# hightouch.com — same DataGrail Privacy Request Center template as
# bridg.com/clearbit.com/crunchbase.com elsewhere in this repo (identical
# field names/ids: first_name, last_name, email_address,
# mui-component-select-data_subject_relationship, privacy-request-center-
# region-picker). Country/State default correctly to United States/the
# configured STATE without needing to be touched, but set explicitly anyway
# for correctness. Relationship options here are Business Contact/Customer/
# Employee/Former Employee/Job Applicant/Other — "Other" used (closest
# generic fit). Unlike crunchbase.com, Opt-Out and Delete are NOT separate
# cards — there's a single "Deletion or Opt Out Request" card with its own
# sub-select ("Is this a deletion or an opt out request?") offering
# "Deletion"/"Opt Out"; that sub-select's DOM id is a random per-site UUID
# (not a stable name), so it's targeted positionally (the one MuiSelect
# combobox on the page that ISN'T the relationship select) rather than by
# id. Previously logged in this repo as a hard 500 server error; that had
# cleared by the time this scraper was written (same
# "not-necessarily-permanent block" pattern as ariza.com/atom.com/
# deloitte.com). Exercises Access and Opt Out unconditionally; Deletion
# gated on REMOVE_INFORMATION. No captcha observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

URL = "https://preferences.hightouch.com/"

ACCESS = ("access", None)
OPT_OUT = ("opt_out", "Opt Out")
DELETE = ("delete", "Deletion")


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


async def submit_request(tab, right_id, sub_choice, super_scraper):
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

    card_text = "Start Access Request" if sub_choice is None else "Start Deletion Request"
    start_btn = await tab.find(text=card_text, raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} '{card_text}' button not found")
        return
    await start_btn.click()
    await asyncio.sleep(2)

    await _fill_common(tab, super_scraper)

    if sub_choice is not None:
        # the "Deletion"/"Opt Out" sub-select — targeted positionally since
        # its own DOM id is a random per-site UUID, not a stable name
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
                # MUI's menu portal doesn't close on a plain body click —
                # Escape dismisses it (selection is already committed by the
                # click above)
                await tab.keyboard.press(Key.ESCAPE)
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} sub-option '{sub_choice}' not found")
        else:
            print(f"{super_scraper.OOPS} deletion/opt-out sub-select not found")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right_id}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/hightouch_dry_run_{right_id}.png")
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
        for right_id, sub_choice in requests:
            await submit_request(tab, right_id, sub_choice, super_scraper)


asyncio.run(main())
