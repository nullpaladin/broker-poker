# paramountdirectmarketing.com — /do-not-sell-non-ca (the CA-resident
# variant at /do-not-sell-ca is a separate, near-identical form; non-CA
# used here since the persona is Minnesota). Right to Access is CALIFORNIA
# ONLY per the README and not covered by either form — only "Right to Opt
# Out" and "Right to Delete" checkboxes (select-all-that-apply, one
# combined submission), no Access option exists at all on this flow.
# First choose "I am submitting this request for myself" (vs. authorized
# agent) to reveal the form. State is a plain 2-letter-abbreviation
# `<select>`. The page notes "the state you select is compared against
# the general location of your connection" for fraud prevention — worth
# knowing if a submission is unexpectedly rejected, doesn't change what
# gets filled here. reCAPTCHA v2 present — **CAPTCHA solution required**.
# Rights the form exposes: Opt-Out and Delete (checkboxes). Which of them are
# checked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# The non-CA form is used; the page itself says it compares the chosen state to the
# connection location (fraud prevention) — no residency bail needed.
#
# Page elements (keep this list current):
#   text "I am submitting this request for myself"   Requester type (vs. authorized agent)
#   #optOut                    "Right to Opt Out" checkbox -> RIGHT_TO_OPT_OUT
#   #deleteInfo                "Right to Delete" checkbox  -> RIGHT_TO_DELETE
#   #firstName / #lastName / #email   First / Last name, Email
#   #address1 / #address2 / #city / #zip   Address
#   #state                     State <select> (2-letter abbreviation text)
#   reCAPTCHA v2 checkbox      manual solve
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils

URL = "https://paramountdirectmarketing.com/do-not-sell-non-ca"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: ["optOut"], Right.RIGHT_TO_DELETE: ["deleteInfo"]}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        myself_btn = await tab.find(text="I am submitting this request for myself", raise_exc=False)
        if myself_btn:
            await myself_btn.click()
            await asyncio.sleep(2)
        else:
            print(f"{super_scraper.OOPS} 'I am submitting this request for myself' option not found")

        checkbox_ids = [cb for right in rights for cb in RIGHT_MAP[right]]
        for checkbox_id in checkbox_ids:
            checkbox = await tab.find(id=checkbox_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        fields = {
            "firstName": SuperScraper.FIRST_NAME,
            "lastName": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "address1": SuperScraper.ADDRESS,
            "address2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "zip": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state_select = await tab.find(id="state", raise_exc=False)
        if state_select:
            state_abbrev = SuperScraper.STATE_ABBREVIATED
            await js_utils.select_native_option(state_select, text=state_abbrev)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())
