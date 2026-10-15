# growinglibraries.com — Opt-Out/Delete only, no Access request offered.
# A HubSpot form (g-recaptcha-response/hs_context field names) embedded
# directly in the page (not an iframe). Field `name`s are stable HubSpot
# labels (firstname, lastname, address, street_address_2, city, state_,
# country, zip, email) but the DOM `id`s all carry a random per-load UUID
# suffix (e.g. "firstname-9adf795f-...-9895_6134"), so fields are targeted by
# `name` via xpath rather than by id. Phone number/extension select have NO
# `name` attribute at all (only the id-with-UUID) — targeted by an
# `id^="phone-"` / `id^="phone_ext-"` starts-with CSS selector instead.
# Country/Region is a plain free-text field, not a select. Shipping State
# *is* a real <select> with full state names as option text. A cookie
# consent modal ("Accept"/"Decline") covers the page on first load and must
# be dismissed before the form is interactable. reCAPTCHA v2 checkbox
# present — **CAPTCHA solution required** in live mode.
#
# Page elements (inputs located by name unless noted):
#   firstname / lastname        First / Last name
#   address / street_address_2  Street address / Address line 2
#   city / country              City / Country/Region (free text -> "United States")
#   state_                      Shipping State <select> (full state names)
#   zip / email                 ZIP / Email
#   input id^="phone-"          Phone number
#   checkbox name^="i_am_requesting"   attestation checkbox
#   Button "Decline"            cookie-consent modal
# The one form covers both Opt-Out and Delete; it is filled whenever either right is
# requested (SuperScraper.rights_to_exercise(RIGHT_MAP)). It is never submitted
# automatically.
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://growinglibraries.com/do-not-sell"

ATTESTATION_CHECKBOX = "i_am_requesting"  # name prefix of the attestation checkbox
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: ATTESTATION_CHECKBOX,
    Right.RIGHT_TO_DELETE: ATTESTATION_CHECKBOX,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        decline_cookies = await tab.find(text="Decline", raise_exc=False)
        if decline_cookies:
            await decline_cookies.click()
            await asyncio.sleep(1)

        fields = {
            "firstname": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "address": SuperScraper.ADDRESS,
            "street_address_2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "country": "United States",
            "zip": SuperScraper.ZIP_CODE,
            "email": SuperScraper.EMAIL,
        }
        for field_name, value in fields.items():
            if not value:
                continue
            field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_name}' not found")

        state_select = await tab.find(xpath="//select[@name='state_']", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, text=SuperScraper.STATE, dispatch=("change",))

        phone_field = await tab.find(xpath="//input[starts-with(@id,'phone-')]", raise_exc=False)
        if phone_field and SuperScraper.PHONE_NUMBER:
            await phone_field.type_text(SuperScraper.PHONE_NUMBER)

        checkbox = await tab.find(
            xpath=f"//input[@type='checkbox' and starts-with(@name,'{ATTESTATION_CHECKBOX}')]",
            raise_exc=False,
        )
        if checkbox:
            await checkbox.click()
        else:
            print(f"{super_scraper.OOPS} attestation checkbox not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            f"\n{[r.name for r in rights]} form filled but NOT submitted — a reCAPTCHA v2 checkbox is present and requires "
            "a manual solve before clicking SUBMIT."
        )


asyncio.run(main())
