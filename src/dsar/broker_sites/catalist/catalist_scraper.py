# catalist.us — Gravity Forms privacy request form (/your-privacy-choices/).
# The visible "In which state do you reside?" list only names ~15 states
# explicitly (CA, CO, DE, IN, KY, IA, MD, MT, NE, NH, NJ, OR, TN, RI, UT)
# plus "Any other state" — used here since a typical .env STATE value (e.g.
# Minnesota) isn't one of the named ones. Both "I would like to" and
# "State" (address) are actually a *set* of near-identical selects, one per
# possible residency-state choice, with only the one matching the current
# residency selection left enabled (the rest stay disabled/invisible) —
# input_105 ("I would like to") and input_119 (address State, full 50-state
# list, values are 2-letter abbreviations not full names) are the ones left
# enabled for the "Any other state" branch used here; if this scraper starts
# erroring after picking a named state instead, the enabled field ids will
# differ and need re-deriving.
#
# Crucially, "Any other state"'s "I would like to" select (input_105) offers
# only ONE option: "delete and opt out of the sale of my personal
# information" — a single bundled right, no separate Access/Correct/Limit
# choices (those exist on the named-state variants, which offer 3-4 options
# each depending on the state's specific law). Since it bundles deletion,
# this scraper only submits it when REMOVE_INFORMATION is set — for a
# non-enumerated-state resident with REMOVE_INFORMATION off, this form
# genuinely offers no right to exercise, which is a real limitation of the
# vendor's form rather than something to work around by misrepresenting the
# requester's state.
#
# "I am making this request on behalf of myself" declaration checkbox is
# required. Birthdate is a plain text datepicker expecting mm/dd/yyyy
# (converted from the .env DD/MM/YYYY).
#
# The form ends in a "Send Verification Code" step (an 8-digit OTP field,
# input_144.1) gating the actual Submit button — sending a real code to the
# entered email/phone is a genuine side effect, so this scraper fills every
# other field and stops there regardless of DRY_RUN; completing the OTP step
# and clicking Submit must be done manually.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://catalist.us/your-privacy-choices/"

DELETE_RIGHT = "delete and opt out"


async def _select_by_value(select_element, value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


def _to_mm_dd_yyyy(dd_mm_yyyy):
    day, month, year = dd_mm_yyyy.split("/")
    return f"{month}/{day}/{year}"


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    residency_select = await tab.find(id="input_8_46", raise_exc=False)
    if not residency_select:
        print(f"{super_scraper.OOPS} residency-state dropdown not found")
        return
    await _select_by_value(residency_select, "Any other state")
    await asyncio.sleep(1.5)

    request_type_select = await tab.find(id="input_8_105", raise_exc=False)
    if not request_type_select:
        print(f"{super_scraper.OOPS} 'I would like to' dropdown not found")
        return
    await _select_by_value(request_type_select, right)
    await asyncio.sleep(0.5)

    declare_checkbox = await tab.find(id="choice_8_145_1", raise_exc=False)
    if declare_checkbox:
        await declare_checkbox.click()

    address_parts = SuperScraper.ADDRESS.split(" ", 1) if SuperScraper.ADDRESS else ["", ""]
    fields = {
        "input_8_62": SuperScraper.FIRST_NAME,
        "input_8_64": SuperScraper.LAST_NAME,
        "input_8_118": address_parts[0],
        "input_8_69": address_parts[1] if len(address_parts) > 1 else "",
        "input_8_72": SuperScraper.CITY,
        "input_8_76": SuperScraper.ZIP_CODE,
        "input_8_79": SuperScraper.EMAIL,
        "input_8_138": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    state_select = await tab.find(id="input_8_119", raise_exc=False)
    if state_select:
        state_abbr = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
        await _select_by_value(state_select, state_abbr)

    if SuperScraper.DATE_OF_BIRTH:
        birthdate_field = await tab.find(id="input_8_77", raise_exc=False)
        if birthdate_field:
            await birthdate_field.type_text(_to_mm_dd_yyyy(SuperScraper.DATE_OF_BIRTH))

    label = right.replace(" ", "_")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/catalist_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/catalist_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT sent — click 'Send Verification Code' yourself, "
        "enter the code you receive, and click Submit. This sends a real verification code "
        "regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    if not SuperScraper.REMOVE_INFORMATION:
        print(
            "For a non-enumerated-state resident (this scraper always selects 'Any other "
            "state'), this form's only available request bundles deletion with opt-out — "
            "there is no separate Access/Opt-Out-only option. REMOVE_INFORMATION is False, "
            "so there is nothing to submit."
        )
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_request(tab, DELETE_RIGHT, super_scraper)


asyncio.run(main())
