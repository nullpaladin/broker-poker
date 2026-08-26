# uplead.com — Elementor form (WordPress) rendered directly on
# uplead.com/opt-out/. Only two "Request Type" options exist: "Request my
# Information" (Access) and "Delete my Information" — the page's own copy
# states opt-out of sale/sharing is achieved via the SAME "Delete my
# information" option (there is no separate opt-out-only choice), so that
# submission stays gated on REMOVE_INFORMATION like other deletion requests
# in this repo, even though it also covers opt-out. "Data Privacy
# Jurisdiction options" only lists CCPA/VDPA/OCPA/TDPSA/GDPR/Other — none
# apply directly to a Minnesota resident, so "Other" is used (same
# closest-available-option precedent as reonomy.com/finthrive.com
# elsewhere in this repo). Contact Email and Email (the email being
# requested-about) may differ per the page's own note; both filled with the
# same persona email. reCAPTCHA v2 — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.uplead.com/opt-out/"

REQUEST_TYPES = ["Request my Information"]
DELETE_REQUEST_TYPE = "Delete my Information"


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "form-field-full_name": f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
        "form-field-contact_email_address": SuperScraper.EMAIL,
        "form-field-email": SuperScraper.EMAIL,
        "form-field-phone_number": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    jurisdiction_select = await tab.find(id="form-field-jurisdiction", raise_exc=False)
    if jurisdiction_select:
        await _select_native_option(jurisdiction_select, "Other")
    else:
        print(f"{super_scraper.OOPS} Jurisdiction select not found")

    type_select = await tab.find(id="form-field-type", raise_exc=False)
    if type_select:
        await _select_native_option(type_select, request_type)
    else:
        print(f"{super_scraper.OOPS} Request Type select not found")

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/uplead_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/uplead_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a reCAPTCHA v2 checkbox "
        "requires a manual solve before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
