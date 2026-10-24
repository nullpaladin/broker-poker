# throtle.io — custom OneTrust portal, branded/hosted for IQVIA (throtle is
# an IQVIA-owned identity resolution company).
#
# "Choose your rights here" (requestTypesDSARElement) is a vt-autocomplete
# that is GENUINELY multi-select (confirmed: selecting a second right keeps
# the first as a removable chip, and reveals a description block for each
# selected right) — all applicable rights checked in ONE combined
# submission, unlike most single-select OneTrust sites in this repo.
# Reopen the dropdown (click the input) before each selection since picking
# one option closes it. Offers (see RIGHT_MAP): "The right to access my personal
# information" + "A data portability request" (access), "The right to opt-out of the sale or
# 'sharing' of my personal information" + "The right to opt-out of the use of my personal
# information for targeted advertising purposes" (opt-out), "The right to delete my personal
# information" (delete); which are chosen is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Skipped: Correct/amend (no concrete
# inaccuracy), restrict-for-automated-decision-making / restrict-or-object /
# revoke-consent / limit-sensitive-info (all too narrow/inapplicable
# without a concrete basis to cite).
#
# "Relationship with IQVIA" (subjectTypesDSARElement, vt-autocomplete,
# single-select) answered "None" (options are Healthcare Provider/Study
# Participant/Business Contact/Employee/Job Applicant/Agent/None — IQVIA is
# a healthcare data company, so its relationship options skew clinical).
# "Your Name" (firstNameDSARElement) is a single combined full-name field,
# not split first/last. "Full Address" (formField79DSARElement) is a single
# combined address field. Telephone Number and "Your interaction with
# IQVIA" are optional free text (interaction left blank — no concrete
# interaction to describe). A "State" field (stateDSARElement, vt-
# autocomplete) is entirely absent from the DOM until Country is filled in
# — standard OneTrust cascade, easy to miss since it renders below Country
# rather than right after it. reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   requestTypesDSARElement   "Choose your rights here" (multi-select vt-autocomplete)
#   subjectTypesDSARElement   "Relationship with IQVIA" -> "None"
#   firstNameDSARElement      "Your Name" (full name, single field)
#   formField83DSARElement    Telephone Number (optional)
#   emailDSARElement          Email
#   countryDSARElement        Country -> "United States"
#   stateDSARElement          State (appears only after Country is set)
#   formField79DSARElement    "Full Address" (single combined field)
#   formField81DSARElement    City
#   formField82DSARElement    Zip Code
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/07e8dc4d-6686-403e-9b11-39fe7347d2f4/2f999bd2-c826-498c-a504-894eaf543b6f"

# Right -> "Choose your rights here" option(s); all chosen ones go in ONE combined submission.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["The right to access my personal information", "A data portability request"],
    Right.RIGHT_TO_OPT_OUT: [
        "The right to opt-out of the sale or “sharing” of my personal information",
        "The right to opt-out of the use of my personal information for targeted advertising purposes",
    ],
    Right.RIGHT_TO_DELETE: ["The right to delete my personal information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The multi-select lists option texts with curly quotes and several unnamed skipped rights.)

FIELD_XPATHS = {
    "Relationship with IQVIA": "//*[@id='subjectTypesDSARElement']",
    "Your Name": "//*[@id='firstNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Full Address": "//*[@id='formField79DSARElement']",
    "City": "//*[@id='formField81DSARElement']",
    "Zip": "//*[@id='formField82DSARElement']",
}


async def _select_option(tab, option_text, super_scraper, description):
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.6)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    right_labels = list(dict.fromkeys(label for r in rights for label in RIGHT_MAP[r]))

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        rights_field = await tab.find(id="requestTypesDSARElement", raise_exc=False)
        if rights_field:
            for label in right_labels:
                await rights_field.click()
                await asyncio.sleep(0.6)
                await _select_option(tab, label, super_scraper, "Choose your rights")
        else:
            print(f"{super_scraper.OOPS} Choose your rights field not found")

        relationship_field = await tab.find(id="subjectTypesDSARElement", raise_exc=False)
        if relationship_field:
            await relationship_field.click()
            await asyncio.sleep(0.6)
            await _select_option(tab, "None", super_scraper, "Relationship with IQVIA")
        else:
            print(f"{super_scraper.OOPS} Relationship with IQVIA field not found")

        name_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if name_field:
            await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Your Name field not found")

        phone_field = await tab.find(id="formField83DSARElement", raise_exc=False)
        if phone_field and SuperScraper.PHONE_NUMBER:
            await phone_field.type_text(SuperScraper.PHONE_NUMBER)

        email_field = await tab.find(id="emailDSARElement", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

        country_field = await tab.find(id="countryDSARElement", raise_exc=False)
        if country_field:
            await country_field.click()
            await asyncio.sleep(0.3)
            await tab.keyboard.type_text("United States")
            await asyncio.sleep(1.2)
            option = await tab.find(xpath="//*[@role='option' and normalize-space()='United States']", raise_exc=False)
            if option:
                await option.click()
                await asyncio.sleep(0.7)
            else:
                print(f"{super_scraper.OOPS} country option 'United States' not found")
        else:
            print(f"{super_scraper.OOPS} Country field not found")

        # Only revealed in the DOM after Country is set above.
        state_field = await tab.find(id="stateDSARElement", raise_exc=False)
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
                print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found")
        else:
            print(f"{super_scraper.OOPS} State field not found")

        address_field = await tab.find(id="formField79DSARElement", raise_exc=False)
        if address_field:
            full_address = SuperScraper.ADDRESS
            if SuperScraper.ADDRESS_LINE_TWO:
                full_address = f"{full_address}, {SuperScraper.ADDRESS_LINE_TWO}"
            await address_field.type_text(full_address)
        else:
            print(f"{super_scraper.OOPS} Full Address field not found")

        city_field = await tab.find(id="formField81DSARElement", raise_exc=False)
        if city_field:
            await city_field.type_text(SuperScraper.CITY)
        else:
            print(f"{super_scraper.OOPS} City field not found")

        zip_field = await tab.find(id="formField82DSARElement", raise_exc=False)
        if zip_field:
            await zip_field.type_text(SuperScraper.ZIP_CODE)
        else:
            print(f"{super_scraper.OOPS} Zip Code field not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())
