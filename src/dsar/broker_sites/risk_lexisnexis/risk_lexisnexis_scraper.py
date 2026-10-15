# risk.lexisnexis.com — LexisNexis Risk Solutions' FCRA/state-privacy
# "Online Request Form" (consumer.risk.lexisnexis.com/request). CASCADING
# FORM: the Opt-Out/Opt-In/Delete section is entirely absent from the DOM
# until a state IS selected — it's gated by per-state CSS classes
# (`state-options MN-options` etc.), so inspecting the page before picking
# a state will wrongly suggest this form only covers Access (the separate
# "Opt-Out" nav page turned out to be a redundant/harder path — its
# "Request Opt-Out/Opt-In" button opens a new tab pydoll doesn't follow —
# but the exact same Opt-Out/Delete controls are reachable right here
# after State is set). Once revealed: "opts" radio group (Full Opt-Out /
# Partial Opt-Out / Opt-In) — Full Opt-Out used; a checkbox
# "deleteMyPersonalInfo" (Delete); and the
# earlier "orderConsumerDisclosureReport" checkbox (Access — the page's
# copy confirms this single checkbox covers BOTH the FCRA Consumer
# Disclosure Report AND the state Privacy Act Report once a state is set).
# A dispute-related "Description of Procedure Letter" checkbox is skipped
# (no active dispute to reference).
#
# The form requires EITHER a full SSN or a Driver's License Number+State
# ("at least one is required") to verify identity for a genuine background-
# check-style report — this repo's persona only defines LAST_FOUR_SSN, not
# a full 9-digit SSN or DL number, so LAST_FOUR_SSN is submitted into the
# unqualified "SSN" field as the best available data (no maxlength/format
# restriction observed on that field); a real request likely needs a
# genuine full SSN or DL number instead. DOB required, converted from
# .env's DD/MM/YYYY to this form's MM/DD/YYYY. Two field ids collide as
# "State" in the raw markup — the real, live resident-address state select
# is `Residence_State`; a same-id Driver's License-issuer `<select
# name="Issuer" id="State">` and a commented-out dead `<input id="State">`
# both also claim that id, so don't target by id="State" — use
# name="Residence_State" instead. reCAPTCHA v2 — **CAPTCHA solution
# required**.
#
# ONE combined submission: the access / opt-out / delete controls below are each clicked
# only if the matching Right is selected by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   name=FirstName / LastName                  First / Last name
#   name=Residence_StreetAddress1 / Residence_City / Residence_Zip5   Residence address
#   name=Residence_State                       Residence State <select> (reveals Opt-Out/Delete controls)
#   name=Email / Phone / SSN / DOB             Email / Phone / SSN / Date of birth (MM/DD/YYYY)
#   #orderConsumerDisclosureReport             "Request Your Consumer Disclosure Report" checkbox (Access)
#   #globalOptoutFlag                          "Full Opt-Out" radio of the "opts" group (Opt-Out)
#   #deleteMyPersonalInfo                      "Delete My Personal Information" checkbox (Delete)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

# Right -> (element id, human-readable name)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("orderConsumerDisclosureReport", "'Request Your Consumer Disclosure Report' checkbox"),
    Right.RIGHT_TO_OPT_OUT: ("globalOptoutFlag", "'Full Opt-Out' radio"),
    Right.RIGHT_TO_DELETE: ("deleteMyPersonalInfo", "'Delete My Personal Information' checkbox"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

URL = "https://consumer.risk.lexisnexis.com/request#privacy"


def _to_mm_dd_yyyy(dd_mm_yyyy):
    day, month, year = dd_mm_yyyy.split("/")
    return f"{month}/{day}/{year}"


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "FirstName": SuperScraper.FIRST_NAME,
            "LastName": SuperScraper.LAST_NAME,
            "Residence_StreetAddress1": SuperScraper.ADDRESS,
            "Residence_City": SuperScraper.CITY,
            "Residence_Zip5": SuperScraper.ZIP_CODE,
            "Email": SuperScraper.EMAIL,
            "SSN": SuperScraper.LAST_FOUR_SSN,
            "Phone": SuperScraper.PHONE_NUMBER,
        }
        for field_name, value in fields.items():
            if not value:
                continue
            field = await tab.find(name=field_name, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_name}' not found")

        state_select = await tab.find(name="Residence_State", raise_exc=False)
        if state_select:
            state_abbrev = SuperScraper.STATE_ABBREVIATED
            await js_utils.select_native_option(state_select, value=state_abbrev)
        else:
            print(f"{super_scraper.OOPS} Residence_State select not found")

        if SuperScraper.DATE_OF_BIRTH:
            dob_field = await tab.find(name="DOB", raise_exc=False)
            if dob_field:
                await dob_field.type_text(_to_mm_dd_yyyy(SuperScraper.DATE_OF_BIRTH))
            else:
                print(f"{super_scraper.OOPS} DOB field not found")

        # Opt-Out / Delete controls are only revealed in the DOM after Residence_State is set above.
        for right in rights:
            element_id, description = RIGHT_MAP[right]
            control = await tab.find(id=element_id, raise_exc=False)
            if control:
                await control.click()
            else:
                print(f"{super_scraper.OOPS} {description} not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nConsumer Disclosure Report request filled but NOT submitted — a reCAPTCHA v2 "
            "checkbox requires a manual solve. Note: submitted SSN is only the last 4 digits "
            "(this repo's persona doesn't define a full SSN); a real request may need the "
            "genuine full SSN or a driver's license number+state instead."
        )


asyncio.run(main())
