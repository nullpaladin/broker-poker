# quinstreet.com — Securiti.ai-hosted "Consumer Data Request Form -
# Request to Opt-Out" (privacy-central.securiti.ai), a new platform for
# this repo. Opt-Out ONLY — no Access/Delete/Correct option exists
# anywhere on this form. "I am submitting a request" (For Myself/On
# behalf of another person) answered "For Myself". The state-of-residence
# picker is oddly split across TWO separate radio groups laid out as two
# table columns with different underlying `name` attributes
# (`data[user_type][esqnmev]` for the first column, `data[i_am_a][esqnmev]`
# for the "continued:" second column) — functionally one combined choice,
# so this looks for the state in either group by its rendered
# "{State} Resident" label text. A required Certification checkbox
# attests under penalty of perjury that the submitter resides in the
# selected state and the information is correct — true for a matching
# persona, so it's checked. hCaptcha present but rendered as an invisible
# checkbox widget (`display:none`) — auto-resolves in most cases, no
# manual solve built in here, though it may occasionally challenge.
#
# Page elements:
#   label[for*='forMyself']            "I am submitting a request" -> "For Myself"
#   #first_name / #last_name           First / Last name
#   #email / #phone / #zipCode         Email / Phone / ZIP code
#   label "{State} Resident"           State-of-residence radio (either column group)
#   input[name='data[certification]']  Certification checkbox
#   button "Submit Request"            Submit
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacy-central.securiti.ai/#/dsr/1b319101-f00c-470f-a7f0-26aa81f057b8"

# Opt-out only: the form offers no other right.
RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "Request to Opt-Out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='first_name']",
    "Last name": "//*[@id='last_name']",
    "Email": "//*[@id='email']",
    "Phone": "//*[@id='phone']",
    "Zip": "//*[@id='zipCode']",
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        for_myself = await tab.find(
            xpath="//label[contains(@for,'forMyself')]", raise_exc=False
        )
        if for_myself:
            await for_myself.click()
        else:
            print(f"{super_scraper.OOPS} 'For Myself' option not found")

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "zipCode": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state_option = await tab.find(
            xpath=f"//label[contains(@class,'form-check-label')][span[normalize-space()='{SuperScraper.STATE} Resident']]",
            raise_exc=False,
        )
        if state_option:
            await state_option.click()
        else:
            print(f"{super_scraper.OOPS} '{SuperScraper.STATE} Resident' option not found (state may be unsupported by this form)")

        certification = await tab.find(
            xpath="//label[input[@name='data[certification]']]",
            raise_exc=False,
        )
        if certification:
            await certification.click()
        else:
            print(f"{super_scraper.OOPS} Certification checkbox not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit Opt-Out request")
            return

        submit_btn = await tab.find(xpath="//button[normalize-space()='Submit Request']", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted Opt-Out request for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
