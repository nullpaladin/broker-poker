# rhetorik.com — OneTrust privacy webform (privacyportal.onetrust.com), embedded
# on rhetorik.com/do-not-sell-my-info/ via a src'd iframe; go direct.
# Angular form. The "Select request type(s)" listbox (requestTypesDSARElement)
# is INCONSISTENT between loads — sometimes it offers four granular buttons
# ("Right to Delete", "Right to Object / Opt out of Sales", "Right to Know /
# Access", "Right to Rectify / Correct"), sometimes only "General User Request"
# / "Other". So this scraper does ONE combined submission: it clicks whichever
# granular right buttons are present (Know/Access + Object/Opt-out always, Delete
# when REMOVE_INFORMATION), falls back to "General User Request" if the granular
# set isn't rendered, and ALWAYS spells the requested rights out in the
# "Additional Request Details" textarea so intent is unambiguous either way.
# "I am submitting this request as the" (subjectTypesDSARElement) is answered
# "data owner / subject". Country geo-prefills to "United States"; State is an
# autocomplete combobox. Submission is gated by a distorted-text image CAPTCHA
# (captchaCode), NOT reCAPTCHA — filled completely, code left for manual entry.
# **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/0f61f895-d08d-410f-b96d-ecfd34fd42e3/83acc2bf-4742-4946-8a7a-7b2a463d00a5"

GRANULAR_RIGHTS = ["Right to Know / Access", "Right to Object / Opt out of Sales"]
GRANULAR_DELETE = "Right to Delete"


async def _field_value(field):
    res = await field.execute_script("return this.value;")
    try:
        return (res["result"]["result"]["value"] or "").strip()
    except (KeyError, TypeError):
        return ""


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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        wanted = list(GRANULAR_RIGHTS)
        if SuperScraper.REMOVE_INFORMATION:
            wanted.append(GRANULAR_DELETE)
        picked_any = False
        for right in wanted:
            if await _click_listbox_option(tab, right):
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

        rights_text = (
            "I am a resident exercising my state privacy rights. I request: "
            "(1) to know/access the personal information you hold about me, its "
            "sources and the parties it has been disclosed to; (2) to opt out of "
            "the sale and sharing of my personal information and of targeted "
            "advertising / profiling"
        )
        if SuperScraper.REMOVE_INFORMATION:
            rights_text += "; (3) deletion of all personal information you hold about me"
        rights_text += "."
        details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if details:
            await details.type_text(rights_text)

        time.sleep(0.5)
        submit_btn = await tab.find(id="dsar-webform-submit-button", raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await SuperScraper.screenshot(tab, "resources/screenshots/rhetorik_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit combined privacy request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Type the CAPTCHA code shown in the browser, click Submit,")
        print("then press Enter once the confirmation page appears...")
        input()
        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
