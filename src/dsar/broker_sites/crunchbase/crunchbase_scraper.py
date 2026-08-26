# crunchbase.com — same DataGrail Privacy Request Center template as
# bridg.com elsewhere in this repo (identical field names/ids: first_name,
# last_name, email_address, mui-component-select-data_subject_relationship
# with data-value="customer", MUI Autocomplete State picker). Country/State
# default correctly to United States/the configured STATE without needing to
# touch them, but this scraper sets them explicitly anyway for correctness
# regardless of what the page happens to default to. Exercises Access and
# Opt Out unconditionally; Deletion gated on REMOVE_INFORMATION (Transfer
# and Update Inaccuracies also exist as cards but aren't exercised — not a
# core Access/Opt-Out/Delete right). No captcha observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://preferences.crunchbase.com/"

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
        await tab.take_screenshot(path=f"resources/screenshots/crunchbase_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/crunchbase_dry_run_{label}.png")
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
