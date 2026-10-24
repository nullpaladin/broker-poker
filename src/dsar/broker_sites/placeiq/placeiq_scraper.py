# placeiq (precisely.com subsidiary) — OneTrust webform, same portal id as Precisely's form
# (see ../precisely/precisely_scraper.py) but a different second URL segment. Cascading
# single-page form (later fields only render once earlier ones are answered) with a
# role="option" single-select "Request Type" group — one submission per right.
#
# Flow / elements:
#   formField103DSARElement   US State autocomplete combobox
#   subjectTypesDSARElement   "I am submitting this request as" — an autocomplete COMBOBOX here
#                             (not a toggle group like Precisely's), -> "Myself"
#   "Your relationship with Precisely"  role=option toggle (Partner/Customer/Consumer) -> "Consumer"
#   "Request Type"            role=option, single-select (one per right)
#   firstNameDSARElement      Full name
#   emailDSARElement          Email
#   formField83DSARElement    MAID — revealed ONLY by the Opt-out request type; PlaceIQ's own copy
#                             says it treats any Opt-Out as a deletion request and adds the MAID to its
#                             suppression list. Validates a strict UUID shape
#                             (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX); this repo's .env ADVERTISING_ID
#                             placeholder ("0000-0000-0000-0000") fails it — a persona-data limitation,
#                             a real run needs an ADVERTISING_ID in genuine UUID form.
# reCAPTCHA v2 — **CAPTCHA solution required** (manual solve on a live run).
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu.onetrust.com/webform/d88b298e-1f7e-420f-949c-fedc475c1e77/83126462-6c9f-4d90-9077-f029b129a2a6"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Know - Categories"],
    Right.RIGHT_TO_OPT_OUT: ["Opt-out of the Sale/Sharing of Personal Information"],
    Right.RIGHT_TO_DELETE: ["Delete Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Only three request-type texts are recorded; the group may offer more.)

FIELD_XPATHS = {
    "State": "//*[@id='formField103DSARElement']",
    "Name": "//*[@id='firstNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
}


async def _autocomplete_select(tab, field_id, text, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return False
    await field.click()
    await asyncio.sleep(0.3)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
        return True
    print(f"{super_scraper.OOPS} {description} option '{text}' not found")
    return False


async def _toggle_select(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
        return True
    print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")
    return False


async def submit_request(tab, right, entry, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    await _autocomplete_select(tab, "formField103DSARElement", SuperScraper.STATE, super_scraper, "state")
    await _autocomplete_select(tab, "subjectTypesDSARElement", "Myself", super_scraper, "submitter type")
    await _toggle_select(tab, "Consumer", super_scraper, "relationship")
    await _toggle_select(tab, entry, super_scraper, "request type")

    name_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    # The Opt-out request type reveals an additional required MAID field.
    maid_field = await tab.find(id="formField83DSARElement", raise_exc=False)
    if maid_field and SuperScraper.ADVERTISING_ID:
        await maid_field.type_text(SuperScraper.ADVERTISING_ID)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in entry.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(f"\n[PlaceIQ] '{entry}' request filled but NOT submitted — reCAPTCHA v2 requires a manual solve.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for entry in RIGHT_MAP[right]:
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())
