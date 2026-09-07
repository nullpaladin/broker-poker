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
# radio group respectively). Exercises Right to Know and Right of Access
# unconditionally; Right to Delete gated on REMOVE_INFORMATION. Correct/
# Portability skipped as auxiliary (not core Access/Opt-Out/Delete rights).
import asyncio
import json

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

FORM_URL = "https://forms.gle/y8LzfvuoJWRAgqNL9"

RIGHT_TO_KNOW = "Right to Know: I would like to know how Jobot handles personal data it collects about me."
RIGHT_OF_ACCESS = "Right of Access: I would like to access the personal data that Jobot maintains about me."
RIGHT_TO_DELETE = "Right to Delete: I would like to delete personal data Jobot maintains about me."
RELATIONSHIP = "I have used Jobot to look for a job"

FIRST_NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[3]'
LAST_NAME_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[4]'
EMAIL_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[5]'
PHONE_XPATH = '(//input[@jsname="YPqjbf" and @type="text"])[6]'


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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(FORM_URL)
        await asyncio.sleep(4)

        await check_checkbox(tab, RIGHT_TO_KNOW)
        await check_checkbox(tab, RIGHT_OF_ACCESS)
        if SuperScraper.wants("delete"):
            await check_checkbox(tab, RIGHT_TO_DELETE)

        await click_radio(tab, RELATIONSHIP)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER, sleep=0.5)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit privacy request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/jobot_dry_run.png")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(4)
        result = await SuperScraper.page_text(tab)
        print(result[:500])


asyncio.run(main())
