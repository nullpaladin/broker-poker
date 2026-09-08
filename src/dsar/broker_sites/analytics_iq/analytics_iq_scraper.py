# analytics-iq.com — OneTrust portal DSAR form.
# Angular role="button" request type divs — click via click_using_js().
# Country and state use autocomplete comboboxes — type text, then click
# the first visible role="option" element.
# captchaCode is a plain text CAPTCHA input — manual entry required in live mode.
# Exercises Access, Do Not Sell/Share, Correct, Opt-Out Ads, Limit Sensitive;
# Delete is gated on REMOVE_INFORMATION.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f6a59500-f900-4652-b030-0cd51afe15a5/87ca07e4-e06c-4ad8-9aa6-ccbbaa8750c1"

RIGHT_MAP = {
    "access": [("Data Access and Information Request CA, CO, CT, OR, TX, UT, VA, MT, NJ, NH, NE, IA, DE, MN, MD Residents Only", "access")],
    "correct": [("Correct Inaccurate Data", "correct")],
    "opt_out_sale_share": [("Do Not Sell or Share My Information", "optout")],
    "opt_out_targeted_ads": [("Opt-Out of Targeted Advertising", "optout_ads")],
    "limit_sensitive_pi": [("Limit the Use of My Sensitive Personal Information", "sensitive")],
    "delete": [("Data Deletion Request Non-California Residents Only", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_autocomplete(tab, field_id, search_text):
    """Type into an autocomplete combobox and click the first visible option."""
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.type_text(search_text)
    await asyncio.sleep(1.5)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            await asyncio.sleep(0.5)
            return


async def submit_request(tab, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Request type button (Angular role="button" div)
    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"resources/screenshots/analytics_iq_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Enter the CAPTCHA value shown in the browser into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{aria_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{aria_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())
