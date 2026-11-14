# precisely.com — OneTrust webform for Precisely itself (PlaceIQ, its subsidiary, has its
# own form: see ../placeiq/placeiq_scraper.py). A cascading single-page form (later fields only
# render in the DOM once earlier ones are answered — inspect a fresh load before assuming a field
# is missing) with a role="option" toggle-button "Select Privacy Right" group that's single-select
# despite offering many options — one submission per right.
#
# NOTE: the URL below contains "/draft/" — confirm it is the live, published form.
#
# Flow / elements:
#   "I am submitting this request as"   role=option toggle -> "Myself", then the "Submit" button
#   countryDSARElement                  Country autocomplete combobox -> "United States"
#   formField97DSARElement              State autocomplete combobox
#   "Your relationship with Precisely"  role=option toggle -> "Website Visitor" (closest generic fit)
#   "Select which Privacy Right you seek to exercise"  role=option toggle (one per right)
#   firstNameDSARElement                Full name   (revealed only after the right is picked)
#   emailDSARElement                    Email       (revealed only after the right is picked)
# reCAPTCHA v2 — **CAPTCHA solution required** (manual solve on a live run).
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu.onetrust.com/webform/d88b298e-1f7e-420f-949c-fedc475c1e77/draft/9c253316-9abf-49fb-a3e1-a4e214c4cf41"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Know - Categories"],
    Right.RIGHT_TO_OPT_OUT: ["Right to Opt Out of the Sale of Personal Information"],
    Right.RIGHT_TO_DELETE: ["Right to Delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The "Select Privacy Right" group offers many options; only three are recorded.)

FIELD_XPATHS = {
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='formField97DSARElement']",
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

    await _toggle_select(tab, "Myself", super_scraper, "submitter type")
    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)

    await _autocomplete_select(tab, "countryDSARElement", "United States", super_scraper, "country")
    await _autocomplete_select(tab, "formField97DSARElement", SuperScraper.STATE, super_scraper, "state")
    await _toggle_select(tab, "Website Visitor", super_scraper, "relationship")
    await _toggle_select(tab, entry, super_scraper, "privacy right")

    name_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in entry.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(f"\n[Precisely] '{entry}' request filled but NOT submitted — reCAPTCHA v2 requires a manual solve.")


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
