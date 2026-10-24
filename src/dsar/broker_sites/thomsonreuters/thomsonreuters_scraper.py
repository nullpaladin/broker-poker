# thomsonreuters.com — custom OneTrust portal. Heavily cascading:
# Residency ("USA Resident") reveals State of Residency (vt-autocomplete)
# and "Who is making this request?" (answered "I am submitting this
# request for myself"); that reveals "I am a (an)" (answered "Other" — the
# rest are all Thomson Reuters customer/employee-specific relationships);
# that reveals "Select request type" — a single-select toggle group
# (confirmed: picking a second option deselects the first) — one
# submission per request type: Data Access Request (access), Do Not Sell My Personal
# Information + Opt Out of Marketing Communications (opt-out), Delete my PI (delete);
# which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). Correct/Expunge
# skipped (no concrete inaccuracy to describe).
#
# Page elements:
#   formField36DSARElement   "State of Residency" (vt-autocomplete)
#   firstNameDSARElement / lastNameDSARElement / emailDSARElement   First / Last name, Contact Email
#   addressDSARElement / cityDSARElement / zipDSARElement           Current Street Address / City / Zip Code
#   nationalIdDSARElement    Last four digits of SSN (optional)
#   formField73DSARElement   "US Phone Number"
#   formField54DSARElement   Phone Number (Opt Out of Marketing Communications only)
#   formField22DSARElement   "Day of Birth" (MM/DD)
#   phoneNumberDSARElement   "Requestor Phone Number" (Data Access Request only)
#
# Selecting a request type reveals its own final block of fields, and this
# DIVERGES by type (tested three of the four): Data Access Request and Do
# Not Sell My Personal Information (and presumably Delete my PI, same
# "full identity verification" bucket) reveal First/Last Name, Current
# Street Address, City, Zip Code (USA Residents), Day of Birth
# (formField22DSARElement, required — MM/DD only, no year; converted from
# .env's DD/MM/YYYY), Last four digits of SSN (nationalIdDSARElement, optional),
# US Phone Number (formField73DSARElement, required), Contact Email, and an
# optional free-text Request Details. Opt Out of Marketing Communications
# instead only reveals First/Last Name, an optional Phone Number
# (formField54DSARElement — a DIFFERENT id than the full-form's phone
# field), Contact Email, and Request Details — no address/DOB/SSN at all.
#
# Day of Birth wants MM/DD ONLY (no year — typing a full date fails
# validation with "Enter Day and Month of birth in format MM/DD"). Filling
# Day of Birth reveals a THIRD cascade, but ONLY for "Data Access Request"
# specifically (not Do Not Sell / Delete, even though they show the same
# DOB field) — a "DO NOT have a mobile phone with camera" checkbox (left
# unchecked — assume a smartphone) and a required "Requestor Phone Number"
# (plain phoneNumberDSARElement, distinct from the earlier "US Phone
# Number" formField73DSARElement). reCAPTCHA v2 — **CAPTCHA solution
# required**.
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/dbf5ae8a-0a6a-4f4b-b527-7f94d0de6bbc/23dce484-737f-4d47-a389-2e990f683e8c"

# Right -> "Select request type" option(s).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Data Access Request"],
    Right.RIGHT_TO_OPT_OUT: ["Do Not Sell My Personal Information", "Opt Out of Marketing Communications"],
    Right.RIGHT_TO_DELETE: ["Delete my PI"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The request-type toggles are listed without a Correct / Expunge label; the fields below are common to every type.)

FIELD_XPATHS = {
    "State of residency": "//*[@id='formField36DSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Contact email": "//*[@id='emailDSARElement']",
}
MARKETING_OPT_OUT_TYPE = "Opt Out of Marketing Communications"
ACCESS_REQUEST_TYPE = "Data Access Request"


def _to_mm_dd(dd_mm_yyyy):
    day, month, _year = dd_mm_yyyy.split("/")
    return f"{month}/{day}"


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.6)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    await _select_option(tab, "USA Resident", super_scraper, "Residency")

    state_field = await tab.find(id="formField36DSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        option = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} State of Residency option '{SuperScraper.STATE}' not found")
    else:
        print(f"{super_scraper.OOPS} State of Residency field not found")

    await _select_option(tab, "I am submitting this request for myself", super_scraper, "Who is making this request?")
    await _select_option(tab, "Other", super_scraper, "I am a (an)")
    await _select_option(tab, request_type, super_scraper, "Select request type")

    fields = {
        "firstNameDSARElement": SuperScraper.FIRST_NAME,
        "lastNameDSARElement": SuperScraper.LAST_NAME,
        "emailDSARElement": SuperScraper.EMAIL,
    }
    if request_type == MARKETING_OPT_OUT_TYPE:
        fields["formField54DSARElement"] = SuperScraper.PHONE_NUMBER
    else:
        fields.update(
            {
                "addressDSARElement": SuperScraper.ADDRESS,
                "cityDSARElement": SuperScraper.CITY,
                "zipDSARElement": SuperScraper.ZIP_CODE,
                "nationalIdDSARElement": SuperScraper.LAST_FOUR_SSN,
                "formField73DSARElement": SuperScraper.PHONE_NUMBER,
            }
        )

    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if request_type != MARKETING_OPT_OUT_TYPE and SuperScraper.DATE_OF_BIRTH:
        dob_field = await tab.find(id="formField22DSARElement", raise_exc=False)
        if dob_field:
            await dob_field.type_text(_to_mm_dd(SuperScraper.DATE_OF_BIRTH))
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} Day of Birth field not found")

        # Only revealed in the DOM after Day of Birth is filled in above,
        # and only for the Data Access Request type specifically.
        if request_type == ACCESS_REQUEST_TYPE:
            requestor_phone_field = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
            if requestor_phone_field and SuperScraper.PHONE_NUMBER:
                # This field rejects spaces/hyphens ("Do not include spaces or hyphens"),
                # unlike the earlier "US Phone Number" field which accepts them.
                digits_only = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
                await requestor_phone_field.type_text(digits_only)
            elif not requestor_phone_field:
                print(f"{super_scraper.OOPS} Requestor Phone Number field not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a reCAPTCHA v2 checkbox "
        "requires a manual solve before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
