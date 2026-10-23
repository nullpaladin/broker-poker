# groundtruth.com — HubSpot form (share.hsforms.com). No discrete right
# picker — a single free-text "Request Details" field states which right(s)
# to exercise (built with SuperScraper.request_statement from the rights chosen by
# SuperScraper.rights_to_exercise(RIGHT_MAP)). MAID (Mobile Advertising ID) is
# required, since GroundTruth is a location/mobile-ad data company. No CAPTCHA observed.
#
# Page elements (inputs located by name):
#   email                  Email
#   maid                   Mobile Advertising ID (MAID)
#   state                  State
#   additional_notes__c    "Request Details" free-text field
#   Button "Submit"
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://share.hsforms.com/1BoOyoq-ASaS-3zNW4dh5Agnn8aa"

# No per-right control on the form: every right is just stated in the free-text field.
NOTES_FIELD = "additional_notes__c"  # "Request Details"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: NOTES_FIELD,
    Right.RIGHT_TO_OPT_OUT: NOTES_FIELD,
    Right.RIGHT_TO_DELETE: NOTES_FIELD,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (No rights chooser: every right is stated in the free-text field.)

FIELD_XPATHS = {
    "Email": "//*[@name='email']",
    "Mobile Advertising ID": "//*[@name='maid']",
    "State": "//*[@name='state']",
    "Request Details": "//*[@name='additional_notes__c']",
}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        for name, value in [
            ("email", SuperScraper.EMAIL),
            ("maid", SuperScraper.ADVERTISING_ID),
            ("state", SuperScraper.STATE),
        ]:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        request_text = SuperScraper.request_statement(rights, broker="GroundTruth")
        notes_field = await tab.find(name=NOTES_FIELD, raise_exc=False)
        if notes_field:
            await notes_field.type_text(request_text)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for MAID {SuperScraper.ADVERTISING_ID}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted {[r.name for r in rights]} for MAID {SuperScraper.ADVERTISING_ID} — confirm in the browser.")


asyncio.run(main())
