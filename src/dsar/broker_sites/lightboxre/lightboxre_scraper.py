# lightboxre.com — the recorded URL is a Proofpoint URL-defense redirect
# wrapper; decoded, it resolves to https://my.datasubject.com/16BXQXSvkBnuN4W2w/51306
# (a "datasubject.com"-hosted portal, navigated to directly rather than
# through the wrapper). No explicit Opt-Out-of-Sale card exists — cards are
# Correct/Access/Delete/"Third parties your data was sold or shared with".
# The last one is mapped to Right.RIGHT_TO_LIST_OF_THIRD_PARTIES. Correct
# is not automatable and not mapped. Every card
# shares the same field set: email/given-name/family-name/phone-number
# (all stable ids) plus an address block (o-Address/o-City/o-State/
# o-ZipCode) whose ids are random per-field UUIDs — targeted by `name`
# instead. State is a plain text field expecting the 2-letter abbreviation
# (SuperScraper.state_full_name_to_abbreviated). No CAPTCHA observed on
# this vendor. Which rights run is decided only by rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   Request cards (clicked by text)  "Access my personal information",
#                            "Third parties your data was sold or shared with",
#                            "Delete my personal information"
#   #email / #given-name / #family-name / #phone-number   Email / First / Last name / Phone
#   name=o-Address / o-City / o-State / o-ZipCode   Address / City / State (2-letter) / ZIP
#   "Submit" button (found by text)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/16BXQXSvkBnuN4W2w/51306"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access my personal information",
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "Third parties your data was sold or shared with",
    Right.RIGHT_TO_DELETE: "Delete my personal information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, card_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    card_btn = await tab.find(text=card_text, raise_exc=False)
    if not card_btn:
        print(f"{super_scraper.OOPS} '{card_text}' card not found")
        return
    await card_btn.click()
    await asyncio.sleep(2)

    email_field = await tab.find(id="email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    first_field = await tab.find(id="given-name", raise_exc=False)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)

    last_field = await tab.find(id="family-name", raise_exc=False)
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)

    phone_field = await tab.find(id="phone-number", raise_exc=False)
    if phone_field and SuperScraper.PHONE_NUMBER:
        await phone_field.type_text(SuperScraper.PHONE_NUMBER)

    address_fields = {
        "o-Address": SuperScraper.ADDRESS,
        "o-City": SuperScraper.CITY,
        "o-ZipCode": SuperScraper.ZIP_CODE,
    }
    for field_name, value in address_fields.items():
        if not value:
            continue
        field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
        if field:
            await field.type_text(value)

    state_field = await tab.find(xpath="//input[@name='o-State']", raise_exc=False)
    if state_field:
        state_abbrev = SuperScraper.STATE_ABBREVIATED
        await state_field.type_text(state_abbrev)

    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{card_text}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        return

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{card_text}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{card_text}'")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
