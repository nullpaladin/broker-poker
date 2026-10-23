# jobot.com — Google Form (forms.gle short link, resolves to
# docs.google.com/forms/...). Jobot states it does not sell personal data,
# so there's no opt-out-of-sale option on this form at all — only Right to
# Know/Access/Delete/Correct/Portability checkboxes (multi-select) plus a
# required single-select "relationship to Jobot" radio group. "I have used
# Jobot to look for a job" is used for the relationship question (Jobot is
# a recruiting platform — this is the closest fit for a generic consumer,
# unlike the "Other" catch-all used on sites with no fitting option).
# First/Last/Email/Phone are all required text fields; all text inputs
# share `jsname="YPqjbf"` with no stable per-field id, so they're targeted
# positionally (indices 3-6 out of 7 total — indices 1-2 are the hidden
# "Other:" free-text boxes for the rights checkbox group and relationship
# radio group respectively). ONE submission: the checkboxes for every selected
# right are ticked together (Access -> "Right to Know" + "Right of Access";
# Delete -> "Right to Delete"). Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Correct/Portability are not automated.
#
# Page elements:
#   checkbox aria-label RIGHT_TO_KNOW / RIGHT_OF_ACCESS / RIGHT_TO_DELETE   (see constants)
#   radio aria-label RELATIONSHIP                                           relationship to Jobot
#   FIRST_NAME_XPATH / LAST_NAME_XPATH / EMAIL_XPATH / PHONE_XPATH          required text fields
#   "Submit" button
import asyncio
import json

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

FORM_URL = "https://forms.gle/y8LzfvuoJWRAgqNL9"

CHECK_RIGHT_TO_KNOW = "Right to Know: I would like to know how Jobot handles personal data it collects about me."
CHECK_RIGHT_OF_ACCESS = "Right of Access: I would like to access the personal data that Jobot maintains about me."
CHECK_RIGHT_TO_DELETE = "Right to Delete: I would like to delete personal data Jobot maintains about me."
RELATIONSHIP = "I have used Jobot to look for a job"

# Right -> aria-labels of the checkboxes to tick (several for one right).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CHECK_RIGHT_TO_KNOW, CHECK_RIGHT_OF_ACCESS],
    Right.RIGHT_TO_DELETE: [CHECK_RIGHT_TO_DELETE],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Correct / Portability checkbox texts are not recorded verbatim, so no inventory is built; labels are aria-labels.)

FIRST_NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[3]'
LAST_NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[4]'
EMAIL_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[5]'
PHONE_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[6]'

FIELD_XPATHS = {
    "First name": FIRST_NAME_XPATH,
    "Last name": LAST_NAME_XPATH,
    "Email": EMAIL_XPATH,
    "Phone": PHONE_XPATH,
}


async def check_checkbox(tab, aria_label):
    await tab.execute_script(
        f"Array.from(document.querySelectorAll('[role=\"checkbox\"]')).find(e => e.getAttribute('aria-label') === {json.dumps(aria_label)}).click()"
    )
    await asyncio.sleep(0.5)


async def click_radio(tab, aria_label):
    await tab.execute_script(
        f"Array.from(document.querySelectorAll('[role=\"radio\"]')).find(e => e.getAttribute('aria-label') === {json.dumps(aria_label)}).click()"
    )
    await asyncio.sleep(0.5)


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

        for right in rights:
            for aria_label in RIGHT_MAP[right]:
                await check_checkbox(tab, aria_label)

        await click_radio(tab, RELATIONSHIP)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER, sleep=0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(4)
        result = await js_utils.page_text(tab)
        print(result[:500])
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
