# jungroup — embedded Google Form, navigated to directly. ONE submission: the
# checkboxes for every selected right are ticked together (Access -> "View My Data";
# Opt-out -> "Don't Sell/Share"; Delete -> "Delete My Data"). The form also offers
# "Edit My Data" (Correct) — not automated. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   //input[@aria-label="Your email"]                  Email
#   checkbox aria-label "Don't Sell/Share" / "View My Data" / "Delete My Data"   (see RIGHT_MAP)
#   NAME_XPATH            first text input: name
#   ADVERTISING_ID_XPATH  second text input: advertising ID
#   "Submit" button
import asyncio
import json
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSff6gJEpA6rv7dXX643lMIjzYEp4yeeD7_odWxU3HRteHVtGg/viewform"

# Right -> aria-labels of the checkboxes to tick.
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: ["Don't Sell/Share"],
    Right.RIGHT_TO_ACCESS: ["View My Data"],
    Right.RIGHT_TO_DELETE: ["Delete My Data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

EMAIL_XPATH = '//input[@aria-label="Your email"]'
NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[1]'
ADVERTISING_ID_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[2]'


async def check_checkbox(tab, aria_label):
    # json.dumps safely escapes apostrophes and other special chars in aria-label
    await tab.execute_script(
        f"Array.from(document.querySelectorAll('[role=\"checkbox\"]')).find(e => e.getAttribute('aria-label') === {json.dumps(aria_label)}).click()"
    )
    time.sleep(0.5)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(FORM_URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=1)

        for right in rights:
            for aria_label in RIGHT_MAP[right]:
                await check_checkbox(tab, aria_label)

        await super_scraper.input_text_field(tab=tab, xpath=NAME_XPATH,
                                             text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=1)
        await super_scraper.input_text_field(tab=tab, xpath=ADVERTISING_ID_XPATH,
                                             text=SuperScraper.ADVERTISING_ID, sleep=1)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL} (ad ID: {SuperScraper.ADVERTISING_ID})")
            await SuperScraper.screenshot(tab, "dry_run")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(4)

        result = await js_utils.page_text(tab)
        print(result[:500])
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
