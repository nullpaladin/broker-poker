# demandscience.com — a PrivacyEngine-hosted webform. "I am making this
# request on behalf of" defaults to "Myself" (no need to touch it). Fields
# use opaque numeric names tied to the form builder (First Name=10652, Last
# Name=10661, Business Email=Email_10653, Company=10662, Country of
# Residence=QuestionTypeID_10663 — a <select> whose option values are also
# opaque numeric ids, not ISO codes, so United States is matched by option
# text ("22984") rather than value). "Business Email Address" and "company
# you work for" are both required despite this being a consumer DSAR form —
# COMPANY_NAME is used for the latter. "Privacy Request Type" (name=10657)
# is a single-select radio (one submission per right): "I would like to
# know what data you hold about me." (Access) and "I object to you
# processing my data and request opt-out." (Opt-Out) unconditionally; "I
# would like my data to be deleted." gated on REMOVE_INFORMATION. Every
# radio's real <input> is positioned off-canvas (opacity:0) inside a jQuery
# Custom Forms (jcf) wrapper whose `for`/`id` label linkage is broken (the
# label's `for` doesn't match the actual radio id) — set via JS
# (checked=true + click/change dispatch) rather than relying on a label
# click. No captcha observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://portal.privacyengine.io/app/0CEB4BAE-BBE7-4DD9-BD70-4E2DBB01D64D/4F5BED3F-8BFB-4BF4-A1F8-8A2261BDE0CE"

COUNTRY_SELECT_ID = "QuestionTypeID_10663"
UNITED_STATES_VALUE = "22984"

REQUEST_TYPE_RADIO_NAME = "10657"
# Opaque tagger ids — verify against the live form.
RIGHT_MAP = {
    "access": ["22792"],            # know what data you hold
    "opt_out_sale_share": ["22795"],
    "delete": ["22794"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _check_radio(tab, name, value, super_scraper, description):
    radio = await tab.find(xpath=f"//input[@name='{name}' and @value='{value}']", raise_exc=False)
    if not radio:
        print(f"{super_scraper.OOPS} {description} option not found")
        return
    await radio.execute_script(
        "this.checked=true;"
        "this.dispatchEvent(new Event('click', {bubbles:true}));"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    fields = {
        "10652": SuperScraper.FIRST_NAME,
        "10661": SuperScraper.LAST_NAME,
        "10662": SuperScraper.COMPANY_NAME or "N/A",
    }
    for field_name, value in fields.items():
        field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
        if field:
            await field.type_text(value)

    email_field = await tab.find(id="Email_10653", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    country_select = await tab.find(id=COUNTRY_SELECT_ID, raise_exc=False)
    if country_select:
        await country_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={UNITED_STATES_VALUE!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    await _check_radio(tab, REQUEST_TYPE_RADIO_NAME, request_type, super_scraper, "request type")

    label = {
        "22792": "know",
        "22795": "opt_out",
        "22794": "delete",
    }.get(request_type, request_type)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/demandscience_dry_run_{label}.png")
        return

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{label}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
