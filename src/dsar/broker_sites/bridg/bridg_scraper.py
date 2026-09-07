# bridg.com — the on-file URL (datagrail.cardlytics.com) 404s; the real
# DataGrail-hosted Privacy Request Center is at datagrail.bridg.com/ (linked
# from bridg.com's own /privacy-policy/ page). Country defaults to United
# States; State is a MUI Autocomplete typeahead (click, type, click the
# matching li[role='option']). Each of the 5 cards on the landing page
# (Access/Deletion/Opt Out/Transfer/Correction) opens its own simple form:
# First/Last/Email, a "Data subject's relationship with Bridg" MUI Select
# defaulted to "Customer" (a real div[role='button'], not a native <select>),
# and an optional comments field, then Review Request -> Submit Request.
# Exercises Access and Opt Out unconditionally; Deletion gated on
# REMOVE_INFORMATION. Every text field has a React useId()-style colon id
# (":r4:") — targeted by name attribute via xpath rather than id= (same class
# of bug as pydoll's colon-id issue documented elsewhere in this repo). No
# captcha observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://datagrail.bridg.com/"

RIGHTS = ["Access Request", "Opt Out Request"]
DELETE_RIGHT = "Deletion Request"


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_field = await tab.find(id="privacy-request-center-region-picker", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.5)
        state_opt = await tab.find(xpath=f"//li[@role='option' and @aria-label='{SuperScraper.STATE}']", raise_exc=False)
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(0.5)

    start_btn = await tab.find(text=f"Start {right}", raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} 'Start {right}' button not found")
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

    relationship = await tab.find(id="mui-component-select-data_subject_relationship", raise_exc=False)
    if relationship:
        await relationship.click()
        await asyncio.sleep(1)
        customer_opt = await tab.find(xpath="//li[@data-value='customer']", raise_exc=False)
        if customer_opt:
            await customer_opt.click()
            await asyncio.sleep(0.5)

    label = right.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/bridg_dry_run_{label}.png")
        return

    review_btn = await tab.find(text="Review Request", raise_exc=False)
    if review_btn:
        await review_btn.click()
        await asyncio.sleep(2)

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{right}'")


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
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())
