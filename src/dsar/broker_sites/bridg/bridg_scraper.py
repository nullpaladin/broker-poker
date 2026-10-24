# bridg.com — the on-file URL (datagrail.cardlytics.com) 404s; the real
# DataGrail-hosted Privacy Request Center is at datagrail.bridg.com/ (linked
# from bridg.com's own /privacy-policy/ page). Country defaults to United
# States; State is a MUI Autocomplete typeahead (click, type, click the
# matching li[role='option']). Each of the 5 cards on the landing page
# (Access/Deletion/Opt Out/Transfer/Correction) opens its own simple form:
# First/Last/Email, a "Data subject's relationship with Bridg" MUI Select
# defaulted to "Customer" (a real div[role='button'], not a native <select>),
# and an optional comments field, then Review Request -> Submit Request.
# Rights: Access, Opt Out, Deletion (Transfer/Correction cards are not automated);
# which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). Every text field has a React useId()-style colon id
# (":r4:") — targeted by name attribute via xpath rather than id= (same class
# of bug as pydoll's colon-id issue documented elsewhere in this repo). No
# captcha observed.
#
# Page elements:
#   #privacy-request-center-region-picker   State (MUI Autocomplete)
#   li[role=option][aria-label=<state>]     State option
#   "Start <entry>" button                  Card for the request (see RIGHT_MAP)
#   input[name=first_name] / [name=last_name]   First / Last name
#   input[name=email_address]               Email
#   #mui-component-select-data_subject_relationship  "Data subject's relationship with Bridg" -> li[data-value=customer]
#   "Review Request" / "Submit Request"     Buttons
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://datagrail.bridg.com/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access Request"],
    Right.RIGHT_TO_OPT_OUT: ["Opt Out Request"],
    Right.RIGHT_TO_DELETE: ["Deletion Request"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//input[@name='first_name']",
    "Last name": "//input[@name='last_name']",
    "Email": "//input[@name='email_address']",
}


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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
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
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right in rights:
            for entry in RIGHT_MAP[right]:
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())
