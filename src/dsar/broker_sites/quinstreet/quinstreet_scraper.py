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
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacy-central.securiti.ai/#/dsr/1b319101-f00c-470f-a7f0-26aa81f057b8"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/quinstreet_dry_run.png")
        print("Screenshot saved to resources/screenshots/quinstreet_dry_run.png")

        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit Opt-Out request")
            return

        submit_btn = await tab.find(xpath="//button[normalize-space()='Submit Request']", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print("Submitted Opt-Out request")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())
