# datasys.com — /privacy/my-privacy-choices is just a marketing/FAQ page;
# its "Make a Privacy Request" button links out to the real wizard at
# privacy.datasys.com. A 4-step React wizard (single-select request type, so one
# submission per right). Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Every radio's real <input> is
# visually hidden (class "sr-only") inside a clickable <label> wrapper — click the
# label, not the input, same pattern as audigent.com elsewhere in this repo.
# No captcha observed anywhere in the flow.
#
# Page elements:
#   Step 1  input[name=requestType]    Request type radio (opt_out / deletion / access_know)
#   Step 2  input[name=submitterType]  Submitter type radio (self / authorized_agent /
#                                      parent_guardian — "self" used here)
#   Step 3  #firstName / #lastName / #email / #phone / #addressLine1 / #city / #postalCode
#           #state                     State <select> (value = state abbreviation)
#   Step 4  input[type=checkbox]       Required attestation on the Review & Submit page
#           "Submit Request" button
#   "Next" button                      Advances steps 1-3
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.datasys.com"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access_know",
    Right.RIGHT_TO_OPT_OUT: "opt_out",
    Right.RIGHT_TO_DELETE: "deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _click_radio_label(tab, name, value, super_scraper, description):
    label = await tab.find(
        xpath=f"//input[@name='{name}' and @value='{value}']/ancestor::label", raise_exc=False
    )
    if not label:
        print(f"{super_scraper.OOPS} {description} option '{value}' not found")
        return False
    await label.click()
    await asyncio.sleep(0.5)
    return True


async def _click_next(tab):
    next_btn = await tab.find(text="Next", raise_exc=False)
    if next_btn:
        await next_btn.click()
        await asyncio.sleep(1.5)


async def submit_request(tab, right, entry, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    if not await _click_radio_label(tab, "requestType", entry, super_scraper, "request type"):
        return
    await _click_next(tab)

    if not await _click_radio_label(tab, "submitterType", "self", super_scraper, "submitter type"):
        return
    await _click_next(tab)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "phone": SuperScraper.PHONE_NUMBER,
        "addressLine1": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "postalCode": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_abbr = SuperScraper.STATE_ABBREVIATED
        await js_utils.select_native_option(state_select, value=state_abbr)
    await _click_next(tab)

    checkbox = await tab.find(xpath="//input[@type='checkbox']", raise_exc=False)
    if checkbox:
        await checkbox.click()

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

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
