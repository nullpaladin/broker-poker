# uplead.com — Elementor form (WordPress) rendered directly on
# uplead.com/opt-out/. Only two "Request Type" options exist: "Request my
# Information" (Access) and "Delete my Information" — the page's own copy
# states opt-out of sale/sharing is achieved via the SAME "Delete my
# information" option (there is no separate opt-out-only choice), so that
# submission is mapped to delete only (like other deletion requests in this
# repo), even though it also covers opt-out. Which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). "Data Privacy
# Jurisdiction options" only lists CCPA/VDPA/OCPA/TDPSA/GDPR/Other — none
# apply directly to a Minnesota resident, so "Other" is used (same
# closest-available-option precedent as reonomy.com/finthrive.com
# elsewhere in this repo). Contact Email and Email (the email being
# requested-about) may differ per the page's own note; both filled with the
# same persona email. reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   #form-field-full_name              Full name
#   #form-field-contact_email_address  Contact Email
#   #form-field-email                  Email (being requested about)
#   #form-field-phone_number           Phone number
#   #form-field-jurisdiction           "Data Privacy Jurisdiction" <select> -> "Other"
#   #form-field-type                   "Request Type" <select> (see RIGHT_MAP)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.uplead.com/opt-out/"

# Right -> "Request Type" option.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request my Information",
    Right.RIGHT_TO_DELETE: "Delete my Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await js_utils.select_native_option(jurisdiction_select, value="Other")
    else:
        print(f"{super_scraper.OOPS} Jurisdiction select not found")

    type_select = await tab.find(id="form-field-type", raise_exc=False)
    if type_select:
        await js_utils.select_native_option(type_select, value=request_type)
    else:
        print(f"{super_scraper.OOPS} Request Type select not found")

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a reCAPTCHA v2 checkbox "
        "requires a manual solve before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [RIGHT_MAP[right] for right in rights]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())
