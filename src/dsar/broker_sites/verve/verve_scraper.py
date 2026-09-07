# verve.com — Formidable Forms (WordPress) "Data Subject Request Form"
# rendered directly on verve.com/data-subject-request-form/. "I am a (an)"
# (name="item_meta[6]") is single-select radios — "End-User" used (closest
# generic-consumer fit; others are B2B Customer/Employee/Job Applicant).
# "Select request type(s)" (name="item_meta[7][]") is GENUINELY multi-
# select checkboxes (confirmed via markup, not just wording) — all
# applicable rights checked in ONE combined submission: Info Request, Data
# Access, "Do Not Sell or Share My Personal Information", "Limit the Use
# of My Sensitive Personal Information" unconditionally; Data Deletion
# gated on REMOVE_INFORMATION. Correct Data and File a Complaint skipped
# (no concrete inaccuracy/complaint to describe). Matched by stable field
# id (field_ebdv3-N) rather than by option value text, since one value
# string has an odd embedded literal quote/asterisk
# ("Limit the Use of My Sensitive Personal Information*"). Country is a
# plain free-text field (not a dropdown) — filled "United States". reCAPTCHA
# v2 is invisible (data-size="invisible") — auto-resolves, no manual
# solve needed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://verve.com/data-subject-request-form/"

RIGHT_MAP = {
    "access": ["field_ebdv3-1", "field_ebdv3-4"],
    "opt_out_sale_share": ["field_ebdv3-5"],
    "limit_sensitive_pi": ["field_ebdv3-6"],
    "delete": ["field_ebdv3-2"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_type_ids = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        i_am_a_radio = await tab.find(id="field_u1j66-3", raise_exc=False)  # End-User
        if i_am_a_radio:
            await i_am_a_radio.click()
        else:
            print(f"{super_scraper.OOPS} 'I am a (an)' End-User radio not found")

        for field_id in request_type_ids:
            checkbox = await tab.find(id=field_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} request type checkbox '{field_id}' not found")

        first_field = await tab.find(id="field_xr2fa_first", raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        else:
            print(f"{super_scraper.OOPS} First Name field not found")

        last_field = await tab.find(id="field_xr2fa_last", raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)
        else:
            print(f"{super_scraper.OOPS} Last Name field not found")

        email_field = await tab.find(id="field_ayz61", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

        country_field = await tab.find(id="field_zf5gh", raise_exc=False)
        if country_field:
            await country_field.type_text("United States")
        else:
            print(f"{super_scraper.OOPS} Country field not found")

        details_field = await tab.find(id="field_ck1lr", raise_exc=False)
        if details_field:
            request_text = "I am requesting access to and opting out of the sale/sharing of my personal information."
            if SuperScraper.REMOVE_INFORMATION:
                request_text += " I am also requesting deletion of my personal information."
            await details_field.type_text(request_text)
        else:
            print(f"{super_scraper.OOPS} Request Details field not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/verve_dry_run.png")
        print("\nRequest filled but NOT submitted (invisible reCAPTCHA v2, no manual solve needed).")


asyncio.run(main())
