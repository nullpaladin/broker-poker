# carfax.com — /company/consumer-privacy/ "CARFAX Consumer Privacy Request
# Form", a custom React multi-step form. Selecting a "State of Residence"
# (<select name="state">) progressively reveals the request-type radios, and
# picking a radio reveals the identity fields — all on one page (no navigation).
#
# One submission per requestTypeInput radio (single-select):
#   "I want to know what personal information CARFAX has about me"  -> Access
#   "I want to correct the personal information ..."                -> Correct (skipped)
#   "I want to have my personal information deleted ..."            -> Delete
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Fields (stable `textInput-userInput-<name>-input` ids): firstName, lastName,
# email, confirmEmail (both = EMAIL), phone. A required "By submitting this
# request, you are confirming ..." attestation checkbox is checked.
# reCAPTCHA v2 gates submit — filled to that point.
# **CAPTCHA solution required**
#
# Page elements:
#   #selectInput-userInput-state-input        "State of Residence" <select> (value = 2-letter abbreviation)
#   label > input[name=requestTypeInput]      Request-type radios (see RIGHT_MAP)
#   #textInput-userInput-firstName-input      First name
#   #textInput-userInput-lastName-input       Last name
#   #textInput-userInput-email-input          Email
#   #textInput-userInput-confirmEmail-input   Confirm email
#   #textInput-userInput-phone-input          Phone
#   input[name=cfx-checkmark]                 "By submitting this request, you are confirming ..." attestation
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.carfax.com/company/consumer-privacy/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "I want to know what personal information CARFAX has about me",
    Right.RIGHT_TO_DELETE: "I want to have my personal information deleted",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[name='requestTypeInput'])"  # revealed once a State is chosen

FIELD_XPATHS = {
    "State of residence": "//*[@id='selectInput-userInput-state-input']",
    "First name": "//*[@id='textInput-userInput-firstName-input']",
    "Last name": "//*[@id='textInput-userInput-lastName-input']",
    "Email": "//*[@id='textInput-userInput-email-input']",
    "Confirm email": "//*[@id='textInput-userInput-confirmEmail-input']",
    "Phone": "//*[@id='textInput-userInput-phone-input']",
}


async def submit_request(tab, right, radio_label, super_scraper):
    try:
        await tab.go_to(URL)
    except Exception as exc:
        print(f"(carfax: go_to reported {exc!r} — continuing)")
    await asyncio.sleep(9)

    state_abbr = SuperScraper.STATE_ABBREVIATED
    state_select = await tab.find(id="selectInput-userInput-state-input", raise_exc=False)
    if state_select:
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={state_abbr!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(2)
    else:
        print(f"{super_scraper.OOPS} state select not found")

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    # The radio lives inside its <label>; click the label (clicking the bare
    # <input> via pydoll doesn't fire React's onChange, so the identity fields
    # never cascade in).
    radio_label_el = await tab.find(
        xpath=f"//label[.//input[@name='requestTypeInput']][contains(normalize-space(), {radio_label!r})]",
        raise_exc=False,
    )
    if not radio_label_el:
        radio_label_el = await tab.find(
            xpath=f"//*[contains(normalize-space(), {radio_label!r})]"
            f"/ancestor-or-self::label[.//input[@name='requestTypeInput']][1]",
            raise_exc=False,
        )
    if radio_label_el:
        await radio_label_el.click()
        await asyncio.sleep(3)
    else:
        print(f"{super_scraper.OOPS} request-type radio {radio_label!r} not found")

    for field_id, value in (
        ("textInput-userInput-firstName-input", SuperScraper.FIRST_NAME),
        ("textInput-userInput-lastName-input", SuperScraper.LAST_NAME),
        ("textInput-userInput-email-input", SuperScraper.EMAIL),
        ("textInput-userInput-confirmEmail-input", SuperScraper.EMAIL),
        ("textInput-userInput-phone-input", SuperScraper.PHONE_NUMBER),
    ):
        if not value:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    attest = await tab.find(
        xpath="//input[@type='checkbox' and @name='cfx-checkmark']", raise_exc=False
    )
    if not attest:
        attest = await tab.find(
            xpath="//label[contains(normalize-space(), 'By submitting this request')]//input[@type='checkbox']",
            raise_exc=False,
        )
    if attest:
        await attest.click()
    else:
        print(f"{super_scraper.OOPS} attestation checkbox not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    print(f"'{right.name}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    super_scraper = SuperScraper()
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
