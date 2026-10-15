# crunchbase.com — DataGrail Privacy Request Center (same template as bridg.com in this repo).
# Cards: Access Request, Opt Out Request, Deletion Request run here. "Transfer" and "Update
# Inaccuracies" cards also exist but are not automated. Country/State default correctly to
# United States / the configured STATE, but this scraper sets State explicitly anyway.
# No captcha observed. Which rights run is decided ONLY by SuperScraper.rights_to_exercise.
#
# Page elements:
#   #privacy-request-center-region-picker              State picker (MUI Autocomplete)
#   li[role=option][aria-label=<STATE>]                 State option
#   "Start <card>" button                               Start Access / Opt Out / Deletion Request
#   input[name=first_name] / [name=last_name]           First / Last name
#   input[name=email_address]                           Email
#   #mui-component-select-data_subject_relationship     "Relationship" select -> li[data-value=customer]
#   "Review Request" / "Submit Request" buttons         Review, then submit
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://preferences.crunchbase.com/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access Request",
    Right.RIGHT_TO_OPT_OUT: "Opt Out Request",
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
        state_opt = await tab.find(xpath=f"//li[@role='option' and @aria-label='{SuperScraper.STATE}']", raise_exc=False)
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

    relationship = await tab.find(id="mui-component-select-data_subject_relationship", raise_exc=False)
    if relationship:
        await relationship.click()
        await asyncio.sleep(1)
        customer_opt = await tab.find(xpath="//li[@data-value='customer']", raise_exc=False)
        if customer_opt:
            await customer_opt.click()
            await asyncio.sleep(0.5)

    label = f"{right.value}"

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            "First name": "//input[@name='first_name']",
            "Last name": "//input[@name='last_name']",
            "Email": "//input[@name='email_address']",
        })

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
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
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
