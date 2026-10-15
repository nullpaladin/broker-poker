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
# Rights offered: Right to Know / Access, Right to Object / Opt out of Sales, Right to
# Rectify / Correct (not automatable, not mapped), Right to Delete. Which run is decided only
# by rights_to_exercise(RIGHT_MAP); all chosen request-type buttons go in ONE submission.
#
# Page elements:
#   #countryDSARElement / #stateDSARElement   Country / State comboboxes (fill first)
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name / Email
#   #vt-input-7                Phone country code combobox
#   #phoneNumberDSARElement    Phone number
#   Request-type buttons (aria-label): "Right to Know / Access",
#                              "Right to Object / Opt out of Sales", "Right to Delete"
#   aria-label "data owner / subject"   Subject type button
#   #requestDetailsDSARElement Additional request details textarea
#   #captchaCode               BotDetect image CAPTCHA code
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/0f61f895-d08d-410f-b96d-ecfd34fd42e3/4b91c2db-5fdc-4f47-8523-b9f01d9e92a3"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Right to Know / Access",
    Right.RIGHT_TO_OPT_OUT: "Right to Object / Opt out of Sales",
    Right.RIGHT_TO_DELETE: "Right to Delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

async def _js_fill(tab, field_id, value):
    el = await tab.find(id=field_id, raise_exc=False)
    if not el:
        print(f"{SuperScraper.OOPS} {field_id} not found")
        return
    await js_utils.js_set_value(el, value)
    await asyncio.sleep(0.3)


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
            label = RIGHT_MAP[right]
            btn = await tab.find(**{"aria-label": label}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} Right button '{label}' not found")

        # 5. Subject type
        subject_btn = await tab.find(**{"aria-label": "data owner / subject"}, raise_exc=False)
        if subject_btn:
            await subject_btn.click_using_js()
        else:
            print(f"{super_scraper.OOPS} 'data owner / subject' button not found")
        await asyncio.sleep(0.5)

        # 6. Additional request details (textarea — JS fill handles textarea too)
        await _js_fill(tab, "requestDetailsDSARElement",
                       SuperScraper.request_statement(rights, broker="Lightcast"))

        await asyncio.sleep(0.5)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit lightcast DSAR for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        print(
            "\nForm filled. Enter the image CAPTCHA code into the captchaCode field, "
            "then click Submit. Press Enter after the confirmation page appears..."
        )
        input()

        print(
            f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser."
        )


asyncio.run(main())
