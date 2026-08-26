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
# "deleteMyPersonalInfo" (Delete, gated on REMOVE_INFORMATION); and the
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
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://consumer.risk.lexisnexis.com/request#privacy"


def _to_mm_dd_yyyy(dd_mm_yyyy):
    day, month, year = dd_mm_yyyy.split("/")
    return f"{month}/{day}/{year}"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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
            state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].value==={state_abbrev!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} Residence_State select not found")

        if SuperScraper.DATE_OF_BIRTH:
            dob_field = await tab.find(name="DOB", raise_exc=False)
            if dob_field:
                await dob_field.type_text(_to_mm_dd_yyyy(SuperScraper.DATE_OF_BIRTH))
            else:
                print(f"{super_scraper.OOPS} DOB field not found")

        disclosure_checkbox = await tab.find(id="orderConsumerDisclosureReport", raise_exc=False)
        if disclosure_checkbox:
            await disclosure_checkbox.click()
        else:
            print(f"{super_scraper.OOPS} 'Request Your Consumer Disclosure Report' checkbox not found")

        # Only revealed in the DOM after Residence_State is set above.
        full_opt_out = await tab.find(id="globalOptoutFlag", raise_exc=False)
        if full_opt_out:
            await full_opt_out.click()
        else:
            print(f"{super_scraper.OOPS} 'Full Opt-Out' radio not found")

        if SuperScraper.REMOVE_INFORMATION:
            delete_checkbox = await tab.find(id="deleteMyPersonalInfo", raise_exc=False)
            if delete_checkbox:
                await delete_checkbox.click()
            else:
                print(f"{super_scraper.OOPS} 'Delete My Personal Information' checkbox not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/risk_lexisnexis_dry_run.png")
        print("Screenshot saved to resources/screenshots/risk_lexisnexis_dry_run.png")
        print(
            "\nConsumer Disclosure Report request filled but NOT submitted — a reCAPTCHA v2 "
            "checkbox requires a manual solve. Note: submitted SSN is only the last 4 digits "
            "(this repo's persona doesn't define a full SSN); a real request may need the "
            "genuine full SSN or a driver's license number+state instead."
        )


asyncio.run(main())
