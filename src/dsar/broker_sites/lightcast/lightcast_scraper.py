# lightcast.io — OneTrust Angular DSAR form (privacyportal.onetrust.com).
# The OneTrust URL redirects to lightcast.io/privacy-request, which embeds
# the form in an iframe; navigate directly to the iframe URL instead.
# CRITICAL: Country + State must be filled FIRST — selecting Minnesota reveals
# state-specific request type buttons and resets any previously clicked ones.
# Country: element.type_text() + ArrowDown+Enter.
# State: element.type_text() → dropdown opens → find(text=STATE).click().
# Personal info + textarea: JS native value setter + input/change event dispatch.
#   (element.type_text doesn't trigger Angular ngModel on vt-input components)
# Request type buttons (MN-specific, revealed after state selection): click_using_js.
# Subject type: "data owner / subject" — clicked after request types.
# Phone country code: vt-input-7 (element.type_text works for this combobox).
# captchaCode: BotDetect image CAPTCHA — manual entry required in live mode.
# Exercises: Right to Know/Access, Right to Object/Opt-out, Right to Rectify/Correct,
#   and Right to Delete (gated on REMOVE_INFORMATION).
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/0f61f895-d08d-410f-b96d-ecfd34fd42e3/4b91c2db-5fdc-4f47-8523-b9f01d9e92a3"

ALWAYS_RIGHTS = [
    "Right to Know / Access",
    "Right to Object / Opt out of Sales",
    "Right to Rectify / Correct",
]
DELETE_RIGHT = "Right to Delete"

DETAILS = (
    "I am exercising my rights under the Minnesota Consumer Data Privacy Act "
    "(MCDPA) and other applicable privacy laws regarding all personal data "
    "Lightcast holds about me."
)

_FILL_JS = """
(function(id, value) {
    var el = document.getElementById(id);
    if (!el) return 'not found: ' + id;
    var inp = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el
              : el.querySelector('input, textarea');
    if (!inp) return 'no input/textarea in ' + id;
    var proto = inp.tagName === 'TEXTAREA'
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(inp, value);
    inp.dispatchEvent(new Event('input', {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
    return 'ok';
})('%s', '%s');
"""


async def _js_fill(tab, field_id, value):
    js = _FILL_JS % (field_id, value.replace("'", "\\'"))
    await tab.execute_script(js)
    await asyncio.sleep(0.3)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(ALWAYS_RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        # 1. Country — element.type_text triggers combobox; ArrowDown+Enter selects
        country_field = await tab.find(id="countryDSARElement", raise_exc=False)
        if country_field:
            await country_field.type_text("United States")
            await asyncio.sleep(2)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        else:
            print(f"{super_scraper.OOPS} countryDSARElement not found")
        await asyncio.sleep(1.5)

        # 2. State — element.type_text triggers Angular autocomplete; find by text to select
        state_field = await tab.find(id="stateDSARElement", raise_exc=False)
        if state_field:
            await state_field.click()
            await asyncio.sleep(0.3)
            await state_field.type_text(SuperScraper.STATE)
            await asyncio.sleep(2)
            state_opt = await tab.find(text=SuperScraper.STATE, raise_exc=False)
            if state_opt and await state_opt.is_visible():
                await state_opt.click()
            else:
                await tab.keyboard.press(Key.ARROWDOWN)
                await asyncio.sleep(0.3)
                await tab.keyboard.press(Key.ENTER)
        else:
            print(f"{super_scraper.OOPS} stateDSARElement not found")
        await asyncio.sleep(1.5)

        # 3. Personal info via JS native value dispatch
        await _js_fill(tab, "firstNameDSARElement", SuperScraper.FIRST_NAME)
        await _js_fill(tab, "lastNameDSARElement", SuperScraper.LAST_NAME)
        await _js_fill(tab, "emailDSARElement", SuperScraper.EMAIL)

        # Phone country code (vt-input combobox — element.type_text works here)
        phone_cc = await tab.find(id="vt-input-7", raise_exc=False)
        if phone_cc:
            await phone_cc.click()
            await asyncio.sleep(0.3)
            await tab.keyboard.type_text("1")
        await asyncio.sleep(0.5)

        await _js_fill(tab, "phoneNumberDSARElement", SuperScraper.PHONE_NUMBER)

        # 4. Request type buttons — revealed only after state selection
        for right in rights:
            btn = await tab.find(**{"aria-label": right}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} Right button '{right}' not found")

        # 5. Subject type
        subject_btn = await tab.find(**{"aria-label": "data owner / subject"}, raise_exc=False)
        if subject_btn:
            await subject_btn.click_using_js()
        else:
            print(f"{super_scraper.OOPS} 'data owner / subject' button not found")
        await asyncio.sleep(0.5)

        # 6. Additional request details (textarea — JS fill handles textarea too)
        await _js_fill(tab, "requestDetailsDSARElement", DETAILS)

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit lightcast DSAR for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await tab.take_screenshot("lightcast_dry_run.png")
            print("Screenshot saved to lightcast_dry_run.png")
            return

        print(
            "\nForm filled. Enter the image CAPTCHA code into the captchaCode field, "
            "then click Submit. Press Enter after the confirmation page appears..."
        )
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
