# datonics.com — a Squarespace-built form (sqs-* classes) at
# /privacy/privacy-choices. "Type of Request" is single-select, so one submission
# per right. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). The form has no free-text box.
# Ends in a reCAPTCHA badge that may require a manual solve in live mode.
#
# Page elements:
#   "Reject Non-essential"        Cookie banner button
#   EMAIL_FIELD                   Email
#   select[aria-label='Resident of']    State select (an "Other Location" text field
#                                 appears only when "Other" is chosen — not needed here)
#   select[aria-label='Type of Request']  Request type -> options in RIGHT_MAP
#   MAID_FIELD                    Mobile Advertising ID (IDFA/AAID), optional, from ADVERTISING_ID
#   CERTIFICATION_RADIO_NAME      "Resident Certification" radio -> RESIDENT_CERTIFICATION_VALUE
#                                 (attests residency, as opposed to authorized-agent status)
#   button[type=submit]           Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.datonics.com/privacy/privacy-choices"

EMAIL_FIELD = "email-yui_3_17_2_1_1734056193020_5730-field"
MAID_FIELD = "text-yui_3_17_2_1_1734056193020_5731-field"  # "Mobile Advertising ID"
CERTIFICATION_RADIO_NAME = "radio-68c2cafe-eb6d-45f4-b6f1-21929019c667-field"
RESIDENT_CERTIFICATION_VALUE = (
    "I certify that I am a resident of selected state / location and that all information "
    "I have submitted is true and accurate."
)

# The one opt-out option covers both sale/share and targeted ads.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access/Obtain Copy of My Information",
    Right.RIGHT_TO_OPT_OUT: "Opt-out of Targeted Advertising / Do Not Sell or Share My Personal Information",
    Right.RIGHT_TO_DELETE: "Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "select[aria-label='Type of Request'] option"

FIELD_XPATHS = {
    "Email": f"//*[@id='{EMAIL_FIELD}']",
    "Resident of": "//select[@aria-label='Resident of']",
    "Type of Request": "//select[@aria-label='Type of Request']",
}


async def _select_by_aria_label(tab, aria_label, value, super_scraper, description):
    field = await tab.find(xpath=f"//select[@aria-label='{aria_label}']", raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return
    await js_utils.select_native_option(field, value=value)


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    reject_cookies = await tab.find(text="Reject Non-essential", raise_exc=False)
    if reject_cookies and await reject_cookies.is_visible():
        await reject_cookies.click()
        await asyncio.sleep(1)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    submit_btn = await tab.find(xpath="//button[@type='submit']", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{right.name}'")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
