# rhetorik.com — OneTrust privacy webform (privacyportal.onetrust.com), embedded
# on rhetorik.com/do-not-sell-my-info/ via a src'd iframe; go direct.
# Angular form. The "Select request type(s)" listbox (requestTypesDSARElement)
# is INCONSISTENT between loads — sometimes it offers four granular buttons
# ("Right to Delete", "Right to Object / Opt out of Sales", "Right to Know /
# Access", "Right to Rectify / Correct"), sometimes only "General User Request"
# / "Other". So this scraper does ONE combined submission: it clicks whichever
# granular right buttons are present (those selected by rights_to_exercise:
# Know/Access, Object/Opt-out, Delete), falls back to "General User Request" if the granular
# set isn't rendered, and ALWAYS spells the requested rights out in the
# "Additional Request Details" textarea so intent is unambiguous either way.
# "I am submitting this request as the" (subjectTypesDSARElement) is answered
# "data owner / subject". Country geo-prefills to "United States"; State is an
# autocomplete combobox. Submission is gated by a distorted-text image CAPTCHA
# (captchaCode), NOT reCAPTCHA — filled completely, code left for manual entry.
# **CAPTCHA solution required**
#
# Page elements:
#   role=option "Right to Know / Access" / "Right to Object / Opt out of Sales" / "Right to Delete"
#                                  request-type listbox buttons ("General User Request" is the fallback)
#   role=option "data owner / subject"   "I am submitting this request as the" answer
#   #countryDSARElement / #stateDSARElement   Country / State autocompletes
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement / #phoneNumberDSARElement
#   #requestDetailsDSARElement     "Additional Request Details" textarea
#   #dsar-webform-submit-button    Submit button
#   captchaCode                    distorted-text image CAPTCHA (manual entry)
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/0f61f895-d08d-410f-b96d-ecfd34fd42e3/83acc2bf-4742-4946-8a7a-7b2a463d00a5"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Know / Access"],
    Right.RIGHT_TO_OPT_OUT: ["Right to Object / Opt out of Sales"],
    Right.RIGHT_TO_DELETE: ["Right to Delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _field_value(field):
    return ((await js_utils.js_eval(field, "return this.value;")) or "").strip()


async def _select_autocomplete(tab, field_id, search_text):
    for _ in range(2):
        field = await tab.find(id=field_id, raise_exc=False)
        if not field:
            return
        if (await _field_value(field)).lower() == search_text.lower():
            return
        await field.click()
        await field.execute_script(
            "this.value=''; this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await tab.keyboard.type_text(search_text)
        await asyncio.sleep(2.5)
        clicked = False
        for opt in await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []:
            if not await opt.is_visible():
                continue
            label = (opt.get_attribute("aria-label") or opt.text or "").strip()
            if label.lower() == search_text.lower():
                await opt.click_using_js()
                clicked = True
                break
        if not clicked:
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.6)
        field = await tab.find(id=field_id, raise_exc=False)
        if field and (await _field_value(field)).lower() == search_text.lower():
            return


async def _click_listbox_option(tab, aria_label):
    opt = await tab.find(**{"aria-label": aria_label, "role": "option"}, raise_exc=False)
    if opt and await opt.is_visible():
        await opt.click_using_js()
        await asyncio.sleep(0.4)
        return True
    return False


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        wanted = [entry for right in rights for entry in RIGHT_MAP[right]]
        picked_any = False
        for entry in wanted:
            if await _click_listbox_option(tab, entry):
                picked_any = True
        if not picked_any:
            await _click_listbox_option(tab, "General User Request")

        await _click_listbox_option(tab, "data owner / subject")

        await _select_autocomplete(tab, "countryDSARElement", "United States")
        await asyncio.sleep(0.5)
        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

        for fid, value in [
            ("firstNameDSARElement", SuperScraper.FIRST_NAME),
            ("lastNameDSARElement", SuperScraper.LAST_NAME),
            ("emailDSARElement", SuperScraper.EMAIL),
            ("phoneNumberDSARElement", SuperScraper.PHONE_NUMBER),
        ]:
            el = await tab.find(id=fid, raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)

        rights_text = SuperScraper.request_statement(rights, broker="Rhetorik")
        details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details:
            await details.type_text(rights_text)

        time.sleep(0.5)
        submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit combined privacy request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Type the CAPTCHA code shown in the browser, click Submit,")
        print("then press Enter once the confirmation page appears...")
        input()
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")

asyncio.run(main())
