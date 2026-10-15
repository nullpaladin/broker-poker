# veeva — OneTrust privacy-portal webform (Angular). Country is pre-filled as United States;
# all chosen request types are selected on ONE form and submitted together. Rights the form
# exposes: Access Data, Correct Data, Opt-Out, Data Portability, List of Third Party Recipients,
# Delete Data. Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Correct Data" is not automated. reCAPTCHA v2 — manual solve required on a live run.
#
# Page elements:
#   #stateDSARElement          State (autocomplete; matching option clicked by text)
#   "Consumer"                 Requester type button (clicked by text)
#   [aria-label="<request type>"]   Request type buttons (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #formField80DSARElement    Middle name (not filled)
#   #emailDSARElement          Email
#   #addressDSARElement / #cityDSARElement / #zipDSARElement   Address / City / Zip
#   #dateOfBirthDSARElement    Date of birth
#   "Submit Request"           Submit button (clicked by text)
import asyncio
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/3d676ed2-16b1-4c48-97f8-a911923a3adf/a0df0a98-d990-40ff-9bdb-35b5f9e06620"

STATE_XPATH = '//input[@id="stateDSARElement"]'
FIRST_NAME_XPATH = '//input[@id="firstNameDSARElement"]'
MIDDLE_NAME_XPATH = '//input[@id="formField80DSARElement"]'
LAST_NAME_XPATH = '//input[@id="lastNameDSARElement"]'
EMAIL_XPATH = '//input[@id="emailDSARElement"]'
ADDRESS_XPATH = '//input[@id="addressDSARElement"]'
CITY_XPATH = '//input[@id="cityDSARElement"]'
ZIP_XPATH = '//input[@id="zipDSARElement"]'
DOB_XPATH = '//input[@id="dateOfBirthDSARElement"]'

# Request types — div buttons identified by aria-label
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access Data", "Data Portability"],
    Right.RIGHT_TO_OPT_OUT: "Opt-Out",
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "List of Third Party Recipients",
    Right.RIGHT_TO_DELETE: "Delete Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    state_name = SuperScraper.STATE.title()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(5)

        # State autocomplete (country is pre-filled as United States)
        await super_scraper.input_text_field(tab=tab, xpath=STATE_XPATH, text=state_name)
        time.sleep(1)
        await super_scraper.click_item_by_text(tab=tab, text=state_name)
        time.sleep(1)

        # Requester type
        await super_scraper.click_item_by_text(tab=tab, text="Consumer")
        time.sleep(2)

        # Select all applicable request types — JS click fires Angular's event handlers
        async def click_request_type(label):
            await tab.execute_script(f'document.querySelector(\'[aria-label="{label}"]\').click()')
            time.sleep(0.5)

        entries = [e for right in rights for e in (RIGHT_MAP[right] if isinstance(RIGHT_MAP[right], list) else [RIGHT_MAP[right]])]
        for request_type in dict.fromkeys(entries):
            await click_request_type(request_type)

        # Personal info
        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_XPATH, text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)
        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)
        await super_scraper.input_text_field(tab=tab, xpath=DOB_XPATH, text=SuperScraper.DATE_OF_BIRTH)

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run")
            print(f"DRY RUN: would submit {', '.join(r.name for r in rights)} for {SuperScraper.EMAIL}")
            await asyncio.sleep(3)
            return

        # reCAPTCHA v2 — pause for manual solve or 2captcha
        print("Please solve the reCAPTCHA, then press Enter...")
        input()

        await super_scraper.click_item_by_text(tab=tab, text="Submit Request")
        time.sleep(3)
        print(f"Submitted '{', '.join(r.name for r in rights)}' for {SuperScraper.EMAIL} — confirm in the browser.")

        await asyncio.sleep(3)


asyncio.run(main())
