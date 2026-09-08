# datonics.com — a Squarespace-built form (sqs-* classes) at
# /privacy/privacy-choices. Fields: Email, "Resident of" (state select,
# reveals an "Other Location" text field only when "Other" is chosen — not
# needed here since Minnesota is directly listed), "Type of Request"
# (single-select, one submission per right: "Opt-out of Targeted
# Advertising / Do Not Sell or Share My Personal Information" and
# "Access/Obtain Copy of My Information" unconditionally; "Delete My
# Information" gated on REMOVE_INFORMATION), optional Mobile Advertising ID
# (IDFA/AAID, filled from ADVERTISING_ID when set), and a required "Resident
# Certification" radio (attesting residency, as opposed to authorized-agent
# status) — the resident option is used here. Ends in a reCAPTCHA badge that
# may require a manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.datonics.com/privacy/privacy-choices"

EMAIL_FIELD = "email-yui_3_17_2_1_1734056193020_5730-field"
MAID_FIELD = "text-yui_3_17_2_1_1734056193020_5731-field"
CERTIFICATION_RADIO_NAME = "radio-68c2cafe-eb6d-45f4-b6f1-21929019c667-field"
RESIDENT_CERTIFICATION_VALUE = (
    "I certify that I am a resident of selected state / location and that all information "
    "I have submitted is true and accurate."
)

# The one opt-out option covers both sale/share and targeted ads.
RIGHT_MAP = {
    "access": ["Access/Obtain Copy of My Information"],
    "opt_out_sale_share": ["Opt-out of Targeted Advertising / Do Not Sell or Share My Personal Information"],
    "opt_out_targeted_ads": ["Opt-out of Targeted Advertising / Do Not Sell or Share My Personal Information"],
    "delete": ["Delete My Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_by_aria_label(tab, aria_label, value, super_scraper, description):
    field = await tab.find(xpath=f"//select[@aria-label='{aria_label}']", raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return
    await field.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    reject_cookies = await tab.find(text="Reject Non-essential", raise_exc=False)
    if reject_cookies and await reject_cookies.is_visible():
        await reject_cookies.click()
        await asyncio.sleep(1)

    email_field = await tab.find(id=EMAIL_FIELD, raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    await _select_by_aria_label(tab, "Resident of", SuperScraper.STATE, super_scraper, "'Resident of'")
    await _select_by_aria_label(tab, "Type of Request", request_type, super_scraper, "'Type of Request'")

    if SuperScraper.ADVERTISING_ID:
        maid_field = await tab.find(id=MAID_FIELD, raise_exc=False)
        if maid_field:
            await maid_field.type_text(SuperScraper.ADVERTISING_ID)

    certification = await tab.find(
        xpath=f"//input[@name='{CERTIFICATION_RADIO_NAME}' and @value='{RESIDENT_CERTIFICATION_VALUE}']",
        raise_exc=False,
    )
    if certification:
        await certification.click()

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/datonics_dry_run_{label}.png")
        return

    submit_btn = await tab.find(xpath="//button[@type='submit']", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{request_type}'")


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
