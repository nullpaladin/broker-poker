# usdatacorporation.com — the marketing page (usdatacorporation.com/opt-out)
# only embeds a forgetmenaut.com-hosted "Submit a Data Request" form via an
# iframe (a new platform for this repo); navigate directly to the
# underlying portal: https://www.forgetmenaut.com/rtbf/unjVFFNnmFvsZ17Fnk3Tap6U
#
# Stable webform_* ids throughout. "Jurisdiction" (webform_jurisdiction)
# only lists CCPA/GDPR/CACD/LGPDP/TIPA/VCDPA/OTHER — none apply directly to
# a Minnesota resident, so "OTHER" is used (same closest-available-option
# precedent as reonomy.com/finthrive.com elsewhere in this repo). "Request
# Category" (webform_category) is a single-select native <select> — one
# submission per category: "collection" (what data is collected — closest
# equivalent to Access) and "opt_out" unconditionally; "deletion" gated on
# REMOVE_INFORMATION. "correction" and "limit_use" skipped (no concrete
# inaccuracy/sensitive-use to cite); "incomplete" skipped (ambiguous
# internal-sounding category, not a clear consumer right). Native <input
# type="date"> Date of Birth set via JS in ISO format (YYYY-MM-DD).
# "This is a first-party request" checkbox (webform_direct) checked. MAID/
# VIN/CTVID left blank (no equivalent persona data for those identifier
# types). reCAPTCHA v2 — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.forgetmenaut.com/rtbf/unjVFFNnmFvsZ17Fnk3Tap6U"

RIGHT_MAP = {
    "access": ["collection"],
    "opt_out_sale_share": ["opt_out"],
    "delete": ["deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def _set_text_via_js(field_element, value):
    await field_element.execute_script(
        f"this.value = {value!r};"
        "this.dispatchEvent(new Event('input', {bubbles:true}));"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, category, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "webform_email": SuperScraper.EMAIL,
        "webform_first_name": SuperScraper.FIRST_NAME,
        "webform_last_name": SuperScraper.LAST_NAME,
        "webform_phone": SuperScraper.PHONE_NUMBER,
        "webform_address_1": SuperScraper.ADDRESS,
        "webform_address_2": SuperScraper.ADDRESS_LINE_TWO,
        "webform_city": SuperScraper.CITY,
        "webform_state": SuperScraper.STATE,
        "webform_zip": SuperScraper.ZIP_CODE,
        "webform_country": "United States",
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await _set_text_via_js(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if SuperScraper.DATE_OF_BIRTH:
        day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        dob_field = await tab.find(id="webform_birthday", raise_exc=False)
        if dob_field:
            await _set_text_via_js(dob_field, f"{year}-{month}-{day}")
        else:
            print(f"{super_scraper.OOPS} Date of Birth field not found")

    jurisdiction_select = await tab.find(id="webform_jurisdiction", raise_exc=False)
    if jurisdiction_select:
        await _select_native_option(jurisdiction_select, "OTHER")
    else:
        print(f"{super_scraper.OOPS} Jurisdiction select not found")

    category_select = await tab.find(id="webform_category", raise_exc=False)
    if category_select:
        await _select_native_option(category_select, category)
    else:
        print(f"{super_scraper.OOPS} Request Category select not found")

    direct_checkbox = await tab.find(id="webform_direct", raise_exc=False)
    if direct_checkbox:
        await direct_checkbox.click()
    else:
        print(f"{super_scraper.OOPS} 'first-party request' checkbox not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/usdatacorporation_dry_run_{category}.png")
    print(
        f"\n'{category}' request filled but NOT submitted — a reCAPTCHA v2 checkbox requires "
        "a manual solve before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    categories = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for category in categories:
            await submit_request(tab, category, super_scraper)


asyncio.run(main())
