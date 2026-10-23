# hartehanks.com — Request My Data (Access), Do Not Sell My Information (Opt-out), Delete Data.
# Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Custom vt-autocomplete portal (privacy-in-action.hartehanks.com). Subject type = "Individual".
# Subject type + country use ArrowDown+Enter. State uses vt-option click (full state names).
# Text fields use Angular-compatible JS value dispatch (click + InputEvent bubbles).
# After "Request My Data": infoRequestOptionDSARElement sub-field; select both categories via vt-option.
# After "Delete Data": deleteRequestConfirmationDSARElement appears; click "Yes" via role=option.
# Phone country code vt-input-14, reCAPTCHA v2 manual. Single submission covers all rights.
#
# Page elements:
#   subjectTypesDSARElement      "I am a" subject type -> "Individual"
#   firstNameDSARElement / lastNameDSARElement   First / Last name
#   countryDSARElement           Country -> "United States"
#   addressDSARElement / cityDSARElement         Street address / City
#   stateDSARElement             State (vt-option list, full state names)
#   zipDSARElement / emailDSARElement            ZIP / Email
#   vt-input-14                  Phone country code -> "1"
#   phoneNumberDSARElement       Phone number
#   requestTypesDSARElement      Request types (multi-select role=option list)
#   infoRequestOptionDSARElement "Which would you like to receive?" (categories of personal
#                                information + specific pieces of data)
#   deleteRequestConfirmationDSARElement   Delete confirmation -> "Yes"
#   dsar-webform-submit-button   Submit button (clicked manually after the reCAPTCHA v2)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacy-in-action.hartehanks.com/"

# Right -> "Select request type(s)" option text.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request My Data",
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell My Information",
    Right.RIGHT_TO_DELETE: "Delete Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The request-type options live in a multi-select dropdown; only three are recorded.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
}

_CLICK_VT_OPTION_JS = """
(function(text) {
    var opts = document.querySelectorAll('vt-option');
    for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === text) {
            opts[i].click();
            return 'clicked: ' + text;
        }
    }
    return 'not found: ' + text;
})('%s');
"""


async def _js_fill(tab, field_id, value):
    """Set an Angular input value by triggering native InputEvent."""
    el = await tab.find(id=field_id, raise_exc=False)
    if el:
        await js_utils.js_set_value(el, value)
    await asyncio.sleep(0.2)


async def _js_click_vt_option(tab, text):
    """Click the first vt-option whose text matches exactly."""
    js = _CLICK_VT_OPTION_JS % text.replace("'", "\\'")
    await tab.execute_script(js)
    await asyncio.sleep(0.5)


async def _type_arrowdown_enter(tab, field_id, text):
    """Click field, type text, ArrowDown, Enter — for subject type and country."""
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"  Field {field_id} not found")
        return
    await field.click()
    await tab.keyboard.type_text(text)
    await asyncio.sleep(2)
    await tab.keyboard.press(Key.ARROWDOWN)
    await asyncio.sleep(0.3)
    await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)


async def _pick_visible_role_option(tab, field_id, text):
    """Click field, iterate visible role=option elements, click matching one."""
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"  Field {field_id} not found")
        return
    await field.click()
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            t = await opt.text
            if t and t.strip() == text:
                await opt.click_using_js()
                await asyncio.sleep(0.5)
                return
    print(f"  Option '{text}' not found in {field_id}")


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
        await asyncio.sleep(8)

        # Subject type: "Individual" via ArrowDown+Enter
        await _type_arrowdown_enter(tab, "subjectTypesDSARElement", "Individual")

        # Text fields via JS Angular-compatible dispatch
        await _js_fill(tab, "firstNameDSARElement", SuperScraper.FIRST_NAME)
        await _js_fill(tab, "lastNameDSARElement", SuperScraper.LAST_NAME)

        # Country via ArrowDown+Enter
        await _type_arrowdown_enter(tab, "countryDSARElement", "United States")
        await asyncio.sleep(1)

        await _js_fill(tab, "addressDSARElement", SuperScraper.ADDRESS)
        await _js_fill(tab, "cityDSARElement", SuperScraper.CITY)

        # State: click to focus, JS native setter to filter dropdown, click vt-option
        state_field = await tab.find(id="stateDSARElement", raise_exc=False)
        if state_field:
            await state_field.click()
            await asyncio.sleep(0.5)
            state_name = SuperScraper.STATE.title().replace("'", "\\'")
            await tab.execute_script(f"""
                var inp = document.getElementById('stateDSARElement');
                var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(inp, '{state_name}');
                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
            """)
            await asyncio.sleep(2)
            await _js_click_vt_option(tab, SuperScraper.STATE.title())
        else:
            print("  stateDSARElement not found")

        await _js_fill(tab, "zipDSARElement", SuperScraper.ZIP_CODE)
        await _js_fill(tab, "emailDSARElement", SuperScraper.EMAIL)

        # Phone country code (vt-input-14) click + type; phone number via JS fill
        phone_cc = await tab.find(id="vt-input-14", raise_exc=False)
        if phone_cc:
            await phone_cc.click()
            await tab.keyboard.type_text("1")

        await _js_fill(tab, "phoneNumberDSARElement", SuperScraper.PHONE_NUMBER)

        # Request types: select all wanted rights, then close before handling sub-fields
        for right in rights:
            await _pick_visible_role_option(tab, "requestTypesDSARElement", RIGHT_MAP[right])
            await asyncio.sleep(0.3)

        # Close request type dropdown before interacting with sub-fields
        await tab.keyboard.press(Key.ESCAPE)
        await asyncio.sleep(0.8)

        # Sub-field: "Which would you like to receive?" — both categories via JS role=option click
        info_field = await tab.find(id="infoRequestOptionDSARElement", raise_exc=False)
        if Right.RIGHT_TO_ACCESS in rights and info_field:
            for snippet in ("categories of personal", "specific pieces of data"):
                await tab.execute_script(
                    "document.getElementById('infoRequestOptionDSARElement').click();"
                )
                await asyncio.sleep(2)
                await tab.execute_script(f"""
                    var opts = document.querySelectorAll('[role="option"]');
                    for (var i = 0; i < opts.length; i++) {{
                        if (opts[i].textContent.includes('{snippet}')) {{
                            opts[i].click();
                            break;
                        }}
                    }}
                """)
                await asyncio.sleep(0.5)
                await tab.keyboard.press(Key.ESCAPE)
                await asyncio.sleep(0.3)

        if Right.RIGHT_TO_DELETE in rights:
            await _pick_visible_role_option(tab, "deleteRequestConfirmationDSARElement", "Yes")

        await asyncio.sleep(0.5)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            # Screenshot top of form first, then scroll to submit
            await SuperScraper.screenshot(tab, "dry_run_top")
            submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await SuperScraper.screenshot(tab, "dry_run")
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA v2, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
