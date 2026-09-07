# nexxagroup.com — OneTrust Angular portal DSAR form.
# Subject type "Myself" and request type buttons are Angular choice cards (click_using_js).
# Country and State are independent autocompletes (both visible from load).
# No Correct right available — only Access, Do Not Sell/Share, Delete.
# Delete gated on REMOVE_INFORMATION (multi-selected with other rights in one submission).
# Phone country code vt-input-10 (type "1" for US +1). Phone is optional.
# acknowledgementDSARElement = consent checkbox — click_using_js to check.
# captchaCode image CAPTCHA — manual entry required in live mode.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/c02129bc-bbab-43a6-a0b4-175489cb893e/156ac96a-9d7e-4fe6-bab8-a44df779202b"

RIGHT_MAP = {
    "access": ["Access Request"],
    "opt_out_sale_share": ["Do Not Sell/ Share Request"],
    "delete": ["Delete Request"],
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
    request_types = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        myself = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
        if myself:
            await myself.click_using_js()
            await asyncio.sleep(0.5)

        for req_type in request_types:
            btn = await tab.find(**{"aria-label": req_type}, raise_exc=False)
            if btn:
                await btn.click_using_js()
                await asyncio.sleep(0.3)

        await _select_autocomplete(tab, "countryDSARElement", "United States")
        await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        zipcode = await tab.find(id="zipDSARElement", raise_exc=False)
        if zipcode:
            await zipcode.type_text(SuperScraper.ZIP_CODE)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        phone_cc = await tab.find(id="vt-input-10", raise_exc=False)
        if phone_cc:
            await phone_cc.type_text("1")
            await asyncio.sleep(0.5)

        phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
        if phone:
            await phone.type_text(SuperScraper.PHONE_NUMBER)

        ack = await tab.find(id="acknowledgementDSARElement", raise_exc=False)
        if ack:
            await ack.click_using_js()
            await asyncio.sleep(0.5)

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
            suffix = "_delete" if SuperScraper.REMOVE_INFORMATION else ""
            await SuperScraper.screenshot(tab, f"resources/screenshots/nexxagroup_dry_run{suffix}.png")
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
