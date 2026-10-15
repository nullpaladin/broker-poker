# deloitte.com — datasubject.deloitte.com. Previously documented in this
# repo as fully blocked by a DataDome WAF; that block had cleared by the
# time this scraper was written (confirmed with a fresh clean load) — same
# "bot-check interstitials aren't always permanent" pattern seen elsewhere
# in this repo (ariza.com, atom.com).
#
# Clicking "Request Form" -> "Myself" reveals the ENTIRE form at once (no
# further multi-step navigation): Contact Info, "Relationship to Deloitte"
# (checkboxes, select-all-that-apply — none of the options fit a generic
# consumer with no real Deloitte relationship, so "Subscriber to Deloitte US
# marketplace information..." is used as the closest analog, matching this
# repo's established pattern of picking the most generic available option
# rather than leaving a required question unanswered), "Request Type"
# (checkboxes, ALSO select-all-that-apply — unlike most other sites in this
# repo, this means Access/Opt-Out/Delete can all be checked in ONE
# submission rather than needing separate passes), then required
# Confirmation and Acceptance (terms) checkboxes. The Country dropdown
# populates asynchronously a few seconds after the form appears — appears
# empty in a page-source snapshot taken too early even though it's already
# populated in the live DOM. State/Province is a plain text field, not a
# select. Every checkbox/radio is targeted by its `name` attribute (ids are
# a mix of stable semantic names and auto-generated-looking strings).
# Native `.click()` on these checkboxes is unreliable — the real `<input>`
# is visually replaced by a sibling icon span, and a click sometimes lands
# without actually toggling `checked` (confirmed: out of several checkboxes
# clicked identically, only one reliably ended up checked). Checkboxes are
# set via JS (checked=true + click/change event dispatch) instead.
# Which request types are checked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP); they all go out in ONE submission.
#
# Page elements:
#   "Decline all optional cookies"   Cookie banner button
#   "Request Form" button            Opens the form
#   input[name=requestTypeMyself]    "Myself" radio (reveals the whole form)
#   #Fname / #Lname / #email / #PhoneNumber   First / Last name, Email, Phone
#   #Currentaddress / #City / #State / #Postalcode   Street address / City / State (text) / Postal code
#   #Country                         Country <select> (populates asynchronously) -> "United States"
#   RELATIONSHIP_NAME                "Relationship to Deloitte" checkbox (see above)
#   REQUEST_TYPE_ACCESS / _OPT_OUT / _DELETE   "Request Type" checkboxes (see RIGHT_MAP)
#   input[name=Confirmation]         Required "Confirmation" checkbox
#   input[name=terms]                Required "Acceptance" (terms) checkbox
#   "Submit Request" button          Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://datasubject.deloitte.com/"

RELATIONSHIP_NAME = "SubscribertoDeloitteUSmarketplaceinformation"

REQUEST_TYPE_ACCESS = "IsPersonalInformation"
REQUEST_TYPE_OPT_OUT = "Reqchkispresent1"
REQUEST_TYPE_DELETE = "IsdeleteMyPersonalInformation"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [REQUEST_TYPE_ACCESS],
    Right.RIGHT_TO_OPT_OUT: [REQUEST_TYPE_OPT_OUT],
    Right.RIGHT_TO_DELETE: [REQUEST_TYPE_DELETE],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _check(tab, name, super_scraper, description):
    box = await tab.find(xpath=f"//input[@name='{name}']", raise_exc=False)
    if not box:
        print(f"{super_scraper.OOPS} {description} checkbox not found")
        return
    # native .click() is unreliable on these Angular custom checkboxes (the
    # real <input> is visually replaced by a sibling icon span and doesn't
    # always register a real click) — set + dispatch via JS instead
    await box.execute_script(
        "this.checked=true;"
        "this.dispatchEvent(new Event('click', {bubbles:true}));"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


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
        await tab.go_to(URL)
        await asyncio.sleep(5)

        decline_cookies = await tab.find(text="Decline all optional cookies", raise_exc=False)
        if decline_cookies:
            await decline_cookies.click()
            await asyncio.sleep(1)

        open_form = await tab.find(text="Request Form", raise_exc=False)
        if not open_form:
            print(f"{super_scraper.OOPS} 'Request Form' button not found")
            return
        await open_form.click()
        await asyncio.sleep(3)

        myself = await tab.find(xpath="//input[@name='requestTypeMyself']", raise_exc=False)
        if not myself:
            print(f"{super_scraper.OOPS} 'Myself' radio not found")
            return
        await myself.click()
        await asyncio.sleep(3)

        fields = {
            "Fname": SuperScraper.FIRST_NAME,
            "Lname": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "PhoneNumber": SuperScraper.PHONE_NUMBER,
            "City": SuperScraper.CITY,
            "State": SuperScraper.STATE,
            "Postalcode": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        street_field = await tab.find(id="Currentaddress", raise_exc=False)
        if street_field and SuperScraper.ADDRESS:
            await street_field.type_text(SuperScraper.ADDRESS)

        country_select = await tab.find(id="Country", raise_exc=False)
        if country_select:
            await js_utils.select_native_option(country_select, text="United States")

        await _check(tab, RELATIONSHIP_NAME, super_scraper, "relationship")

        request_type_names = [entry for right in rights for entry in RIGHT_MAP[right]]
        for name in request_type_names:
            await _check(tab, name, super_scraper, f"request type '{name}'")

        await _check(tab, "Confirmation", super_scraper, "Confirmation")
        await _check(tab, "terms", super_scraper, "Acceptance/terms")

        if SuperScraper.DRY_RUN:
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            print(f"DRY RUN: would submit {', '.join(r.name for r in rights)} for {SuperScraper.EMAIL}")
            return

        submit_btn = await tab.find(text="Submit Request", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted {', '.join(r.name for r in rights)} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit Request button not found")


asyncio.run(main())
