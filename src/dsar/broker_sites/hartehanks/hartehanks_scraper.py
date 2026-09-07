# hartehanks.com — exercises Request My Data (Access), Do Not Sell, Delete Data (gated).
# Custom vt-autocomplete portal (privacy-in-action.hartehanks.com). Subject type = "Individual".
# Subject type + country use ArrowDown+Enter. State uses vt-option click (full state names).
# Text fields use Angular-compatible JS value dispatch (click + InputEvent bubbles).
# After "Request My Data": infoRequestOptionDSARElement sub-field; select both categories via vt-option.
# After "Delete Data": deleteRequestConfirmationDSARElement appears; click "Yes" via role=option.
# Phone country code vt-input-14, reCAPTCHA v2 manual. Single submission covers all rights.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacy-in-action.hartehanks.com/"

_FILL_JS = """
(function(id, value) {
    var el = document.getElementById(id);
    if (!el) return 'not found: ' + id;
    var inp = el.tagName === 'INPUT' ? el : el.querySelector('input');
    if (!inp) return 'no input in ' + id;
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, value);
    inp.dispatchEvent(new Event('input', {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
    return 'ok';
})('%s', '%s');
"""

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
    js = _FILL_JS % (field_id, value.replace("'", "\\'"))
    await tab.execute_script(js)
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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        # Request types: select all, then close before handling sub-fields
        await _pick_visible_role_option(tab, "requestTypesDSARElement", "Request My Data")
        await asyncio.sleep(0.3)
        await _pick_visible_role_option(tab, "requestTypesDSARElement", "Do Not Sell My Information")

        if SuperScraper.REMOVE_INFORMATION:
            await asyncio.sleep(0.3)
            await _pick_visible_role_option(tab, "requestTypesDSARElement", "Delete Data")

        # Close request type dropdown before interacting with sub-fields
        await tab.keyboard.press(Key.ESCAPE)
        await asyncio.sleep(0.8)

        # Sub-field: "Which would you like to receive?" — both categories via JS role=option click
        info_field = await tab.find(id="infoRequestOptionDSARElement", raise_exc=False)
        if info_field:
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

        if SuperScraper.REMOVE_INFORMATION:
            await _pick_visible_role_option(tab, "deleteRequestConfirmationDSARElement", "Yes")

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            # Screenshot top of form first, then scroll to submit
            await SuperScraper.screenshot(tab, "resources/screenshots/hartehanks_dry_run_top.png")
            submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await SuperScraper.screenshot(tab, "resources/screenshots/hartehanks_dry_run.png")
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA v2, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()
        print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())
