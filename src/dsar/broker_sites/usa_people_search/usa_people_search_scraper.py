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
# wall. Gated on REMOVE_INFORMATION since it initiates a removal request.
#
# Google reCAPTCHA Enterprise on both forms — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

PRIVACY_RIGHTS_URL = "https://www.usa-people-search.com/privacy-rights"
REMOVAL_URL = "https://www.usa-people-search.com/removal"


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def _set_text_via_js(field_element, value):
    # A CSS fade/slide-in transition on this form intermittently makes
    # pydoll's click-based type_text() raise ElementNotVisible even after
    # confirming offsetParent is set — set the value directly via JS
    # instead, which doesn't require the element to be clickable.
    await field_element.execute_script(
        f"this.value = {value!r};"
        "this.dispatchEvent(new Event('input', {bubbles:true}));"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(PRIVACY_RIGHTS_URL)
    await asyncio.sleep(5)

    choose_option_select = await tab.find(id="chooseOption", raise_exc=False)
    if choose_option_select:
        await _select_native_option(choose_option_select, "ADC")
        # The ADC form section fades/slides in — poll until it's actually
        # visible rather than a fixed sleep, since a fixed short sleep was
        # intermittently too short and caused ElementNotVisible errors.
        for _ in range(20):
            await asyncio.sleep(0.3)
            result = await tab.execute_script(
                "var el = document.getElementById('adc-firstname');"
                "return !!(el && el.offsetParent !== null);"
            )
            is_visible = result["result"]["result"]["value"]
            if is_visible:
                await asyncio.sleep(1.5)  # let any fade/slide-in CSS transition finish
                break
        else:
            print(f"{super_scraper.OOPS} ADC form never became visible after selecting 'ADC'")
    else:
        print(f"{super_scraper.OOPS} 'Please choose from the following options' select not found")

    request_type_select = await tab.find(id="adc-request-type", raise_exc=False)
    if request_type_select:
        await _select_native_option(request_type_select, request_type)
    else:
        print(f"{super_scraper.OOPS} Request Type select not found")

    interactions_select = await tab.find(id="adc-company-interactions", raise_exc=False)
    if interactions_select:
        await _select_native_option(interactions_select, "no-relation")
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
            await _set_text_via_js(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if SuperScraper.DATE_OF_BIRTH:
        day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        dob_field = await tab.find(id="adc-dob", raise_exc=False)
        if dob_field:
            # Native <input type="date"> — set via JS in ISO format (YYYY-MM-DD).
            await _set_text_via_js(dob_field, f"{year}-{month}-{day}")
        else:
            print(f"{super_scraper.OOPS} Date of Birth field not found")

    user_type_select = await tab.find(id="adc-user-type", raise_exc=False)
    if user_type_select:
        await _select_native_option(user_type_select, "subject")
    else:
        print(f"{super_scraper.OOPS} 'I am' select not found")

    state_select = await tab.find(id="adc-state", raise_exc=False)
    if state_select:
        await _select_native_option(state_select, SuperScraper.STATE.lower())
    else:
        print(f"{super_scraper.OOPS} State select not found")

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/usa_people_search_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/usa_people_search_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT submitted — Google reCAPTCHA Enterprise "
        "requires a manual solve before submitting."
    )


async def submit_removal_step1(tab, super_scraper):
    await tab.go_to(REMOVAL_URL)
    await asyncio.sleep(5)

    user_type_select = await tab.find(id="user-type", raise_exc=False)
    if user_type_select:
        await _select_native_option(user_type_select, "subject")
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
            await _set_text_via_js(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    agreement_checkbox = await tab.find(id="agreement", raise_exc=False)
    if agreement_checkbox:
        await agreement_checkbox.click()
    else:
        print(f"{super_scraper.OOPS} agreement checkbox not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path="resources/screenshots/usa_people_search_dry_run_removal_step1.png")
    print("Screenshot saved to resources/screenshots/usa_people_search_dry_run_removal_step1.png")
    print(
        "\nOpt-Out Form step 1 filled but NOT submitted — Google reCAPTCHA Enterprise requires "
        "a manual solve, and submitting only emails a continuation link (step 2, the actual "
        "record-removal form, is not reachable without that emailed link)."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_request(tab, "right_to_know", super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await submit_removal_step1(tab, super_scraper)


asyncio.run(main())
