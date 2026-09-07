# babelstreet.com — OneTrust Angular portal DSAR form.
# Subject type and request type buttons are Angular choice cards (click_using_js).
# State and Country are both visible from page load (no dynamic reveal between them).
# Phone country code field id="vt-input-8" — type "1" for US +1.
# Confirm Email must match Email.
# formField78DSARElement = "Today's Date" — type MM/DD/YYYY.
# captchaCode is a text input (image CAPTCHA) — manual entry required in live mode.
# Exercises Access, Edit/Update, Object to Processing, Data Portability, Do Not Sell/Share;
# Delete gated on REMOVE_INFORMATION (all multi-selected in one submission).
import asyncio
import time
from datetime import date

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/43f52ed9-df36-44dc-94b6-ce2f8458ca29/2ddc0d62-7d6a-4de2-b5c4-9f9f68116970"

# "Object to Processing" has no exact canonical code — it rides along with any
# sale/share, targeted-ads, or profiling opt-out.
RIGHT_MAP = {
    "access": ["Access My Data"],
    "correct": ["Edit / Update My Data"],
    "portability": ["Data Portability"],
    "opt_out_sale_share": ["Do Not Sell or Share My Personal Information", "Object to Processing"],
    "opt_out_targeted_ads": ["Object to Processing"],
    "opt_out_profiling": ["Object to Processing"],
    "delete": ["Delete My Data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_autocomplete(tab, field_id, search_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(search_text)
    await asyncio.sleep(2)
    opts = await tab.find(text=search_text, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            break
    await asyncio.sleep(1)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = list(dict.fromkeys(rt for c in codes for rt in RIGHT_MAP[c]))

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        other = await tab.find(**{"aria-label": "Other"}, raise_exc=False)
        if other:
            await other.click_using_js()
            await asyncio.sleep(0.5)

        for req_type in request_types:
            btn = await tab.find(**{"aria-label": req_type}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        confirm = await tab.find(id="confirmEmailInputDSARElement", raise_exc=False)
        if confirm:
            await confirm.type_text(SuperScraper.EMAIL)

        # Phone country code vt-input-8: type "1" for US +1
        phone_cc = await tab.find(id="vt-input-8", raise_exc=False)
        if phone_cc:
            await phone_cc.type_text("1")
            await asyncio.sleep(0.5)

        phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
        if phone:
            await phone.type_text(SuperScraper.PHONE_NUMBER)

        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
        await _select_autocomplete(tab, "countryDSARElement", "United States")

        # Today's Date — type in MM/DD/YYYY format
        today_str = date.today().strftime("%m/%d/%Y")
        today_field = await tab.find(id="formField78DSARElement", raise_exc=False)
        if today_field:
            await today_field.click()
            await asyncio.sleep(0.5)
            await tab.keyboard.type_text(today_str)
            await asyncio.sleep(1)

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            rights = ", ".join(request_types)
            print(
                f"DRY RUN: would submit [{rights}] for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
            if not submit_btn:
                submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            suffix = "_delete" if SuperScraper.wants("delete") else ""
            await SuperScraper.screenshot(tab, f"resources/screenshots/babelstreet_dry_run{suffix}.png")
            return

        print(f"\nForm filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}.")
        print("Enter the image CAPTCHA value into the captchaCode field.")
        print("Then click Submit. Press Enter after submission completes...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())
