# usa-people-search.com — custom "Privacy Rights Form"
# (usa-people-search.com/privacy-rights). A top-level "Please choose from
# the following options" select (id="chooseOption", value "ADC" for the
# combined Access/Delete/Correct form vs. "Appeal", not used) MUST be set
# first — the real form (id="adcPrivacyRightsForm") is already in the page
# source but its fields are not visible/interactable until this selection
# is made.
#
# "Request Type" (id="adc-request-type") is single-select. Only
# right_to_know (Access) is exercised through THIS form — for a user with
# "no direct relationship with the company" (id="adc-company-interactions",
# value "no-relation", the honest answer for this persona on a people-
# search site), selecting right_to_delete or right_to_correct reveals
# boilerplate text explaining that third-party-sourced data can't be
# corrected/deleted through this form and points to a SEPARATE opt-out/
# removal page instead — the actual name/email/etc. input fields never
# render for those two request types under "no-relation", confirmed by
# screenshot (a cascading-fields trap: don't assume every Request Type
# option reveals the same field set just because they share a DOM
# container). "I am" (id="adc-user-type") answered "subject". State
# (id="adc-state") uses full state names, not abbreviations.
#
# Deletion/opt-out instead uses the site's own referenced flow:
# usa-people-search.com/removal — a "USA People Search Opt-Out Form" that
# is itself only STEP 1 of a multi-step, email-verification-gated process
# (per the page's own numbered instructions: submitting this step emails a
# link to continue to the actual record-removal form). This scraper fills
# and would submit step 1 (name + email + "I am" + agreement checkbox) but
# cannot proceed past the emailed verification link, matching this repo's
# existing precedent (statsocial.com) of stopping at an email-verification
# wall. Mapped to delete only since it initiates a removal request.
# Which of the two flows run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (privacy-rights form):
#   #chooseOption        "Please choose from the following options" <select> -> "ADC"
#   #adc-request-type    "Request Type" <select> -> "right_to_know"
#   #adc-company-interactions   company-relationship <select> -> "no-relation"
#   #adc-firstname / #adc-lastname / #adc-email / #adc-phone   First / Last name, Email, Phone
#   #adc-streetaddress / #adc-city / #adc-zipcode   Street address, City, Zip
#   #adc-dob             Date of birth (native date input)
#   #adc-user-type       "I am" <select> -> "subject"
#   #adc-state           State <select> (lower-case full state name)
# Page elements (removal form, step 1):
#   #user-type "I am" <select> -> "subject"; #subject-firstname / #subject-lastname /
#   #subject-email   First / Last name, Email; #agreement   agreement checkbox
#
# Google reCAPTCHA Enterprise on both forms — **CAPTCHA solution required**.
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

PRIVACY_RIGHTS_URL = "https://www.usa-people-search.com/privacy-rights"
REMOVAL_URL = "https://www.usa-people-search.com/removal"

# Right -> this site's flow: the privacy-rights form's "Request Type" value, or the
# separate removal form (opt-out/deletion, step 1 only).
REQUEST_TYPE_ACCESS = "right_to_know"
REMOVAL_FLOW = "removal"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: REQUEST_TYPE_ACCESS,
    Right.RIGHT_TO_DELETE: REMOVAL_FLOW,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The "Request Type" options are recorded by value only; the removal flow is a separate page.)

ADC_FIELD_XPATHS = {
    "Request type": "//*[@id='adc-request-type']",
    "Company interactions": "//*[@id='adc-company-interactions']",
    "First name": "//*[@id='adc-firstname']",
    "Last name": "//*[@id='adc-lastname']",
    "Email": "//*[@id='adc-email']",
    "Street address": "//*[@id='adc-streetaddress']",
    "City": "//*[@id='adc-city']",
    "Zip": "//*[@id='adc-zipcode']",
    "I am": "//*[@id='adc-user-type']",
    "State": "//*[@id='adc-state']",
}
REMOVAL_FIELD_XPATHS = {
    "I am": "//*[@id='user-type']",
    "First name": "//*[@id='subject-firstname']",
    "Last name": "//*[@id='subject-lastname']",
    "Email": "//*[@id='subject-email']",
}


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(PRIVACY_RIGHTS_URL)
    await asyncio.sleep(5)

    choose_option_select = await tab.find(id="chooseOption", raise_exc=False)
    if choose_option_select:
        await js_utils.select_native_option(choose_option_select, value="ADC")
        # The ADC form section fades/slides in — poll until it's actually
        # visible rather than a fixed sleep, since a fixed short sleep was
        # intermittently too short and caused ElementNotVisible errors.
        for _ in range(20):
            await asyncio.sleep(0.3)
            is_visible = await js_utils.js_eval(
                tab,
                "var el = document.getElementById('adc-firstname');"
                "return !!(el && el.offsetParent !== null);",
            )
            if is_visible:
                await asyncio.sleep(1.5)  # let any fade/slide-in CSS transition finish
                break
        else:
            print(f"{super_scraper.OOPS} ADC form never became visible after selecting 'ADC'")
    else:
        print(f"{super_scraper.OOPS} 'Please choose from the following options' select not found")

    request_type_select = await tab.find(id="adc-request-type", raise_exc=False)
    if request_type_select:
        await js_utils.select_native_option(request_type_select, value=request_type)
    else:
        print(f"{super_scraper.OOPS} Request Type select not found")

    interactions_select = await tab.find(id="adc-company-interactions", raise_exc=False)
    if interactions_select:
        await js_utils.select_native_option(interactions_select, value="no-relation")
    else:
        print(f"{super_scraper.OOPS} Company interactions select not found")

    text_fields = {
        "adc-firstname": SuperScraper.FIRST_NAME,
        "adc-lastname": SuperScraper.LAST_NAME,
        "adc-email": SuperScraper.EMAIL,
        "adc-phone": SuperScraper.PHONE_NUMBER,
        "adc-streetaddress": SuperScraper.ADDRESS,
        "adc-city": SuperScraper.CITY,
        "adc-zipcode": SuperScraper.ZIP_CODE,
    }
    for field_id, value in text_fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await js_utils.js_set_value(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if SuperScraper.DATE_OF_BIRTH:
        day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        dob_field = await tab.find(id="adc-dob", raise_exc=False)
        if dob_field:
            # Native <input type="date"> — set via JS in ISO format (YYYY-MM-DD).
            await js_utils.js_set_value(dob_field, f"{year}-{month}-{day}")
        else:
            print(f"{super_scraper.OOPS} Date of Birth field not found")

    user_type_select = await tab.find(id="adc-user-type", raise_exc=False)
    if user_type_select:
        await js_utils.select_native_option(user_type_select, value="subject")
    else:
        print(f"{super_scraper.OOPS} 'I am' select not found")

    state_select = await tab.find(id="adc-state", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, value=SuperScraper.STATE.lower())
    else:
        print(f"{super_scraper.OOPS} State select not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, ADC_FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{request_type}' request filled but NOT submitted — Google reCAPTCHA Enterprise "
        "requires a manual solve before submitting."
    )


async def submit_removal_step1(tab, super_scraper):
    await tab.go_to(REMOVAL_URL)
    await asyncio.sleep(5)

    user_type_select = await tab.find(id="user-type", raise_exc=False)
    if user_type_select:
        await js_utils.select_native_option(user_type_select, value="subject")
    else:
        print(f"{super_scraper.OOPS} 'I am' select not found")

    fields = {
        "subject-firstname": SuperScraper.FIRST_NAME,
        "subject-lastname": SuperScraper.LAST_NAME,
        "subject-email": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await js_utils.js_set_value(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    agreement_checkbox = await tab.find(id="agreement", raise_exc=False)
    if agreement_checkbox:
        await agreement_checkbox.click()
    else:
        print(f"{super_scraper.OOPS} agreement checkbox not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, REMOVAL_FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_removal_step1")
    print(
        "\nOpt-Out Form step 1 filled but NOT submitted — Google reCAPTCHA Enterprise requires "
        "a manual solve, and submitting only emails a continuation link (step 2, the actual "
        "record-removal form, is not reachable without that emailed link)."
    )


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
            if RIGHT_MAP[right] == REMOVAL_FLOW:
                await submit_removal_step1(tab, super_scraper)
            else:
                await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())
