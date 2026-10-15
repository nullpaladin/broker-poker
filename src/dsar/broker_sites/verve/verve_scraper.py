# verve.com — Formidable Forms (WordPress) "Data Subject Request Form"
# rendered directly on verve.com/data-subject-request-form/. "I am a (an)"
# (name="item_meta[6]") is single-select radios — "End-User" used (closest
# generic-consumer fit; others are B2B Customer/Employee/Job Applicant).
# "Select request type(s)" (name="item_meta[7][]") is GENUINELY multi-
# select checkboxes (confirmed via markup, not just wording) — all
# applicable rights checked in ONE combined submission: Info Request, Data
# Access, "Do Not Sell or Share My Personal Information", "Limit the Use
# of My Sensitive Personal Information", Data Deletion. Which of them are
# checked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Correct Data and File a Complaint are not automated. Matched by stable field
# id (field_ebdv3-N) rather than by option value text, since one value
# string has an odd embedded literal quote/asterisk
# ("Limit the Use of My Sensitive Personal Information*"). Country is a
# plain free-text field (not a dropdown) — filled "United States". reCAPTCHA
# v2 is invisible (data-size="invisible") — auto-resolves, no manual
# solve needed.
#
# Page elements:
#   #field_u1j66-3             "I am a (an)" radio -> "End-User"
#   #field_ebdv3-N             "Select request type(s)" checkboxes (see constants below)
#   #field_xr2fa_first / #field_xr2fa_last   First / Last name
#   #field_ayz61               Email
#   #field_zf5gh               Country (free text -> "United States")
#   #field_ck1lr               Request details textarea
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://verve.com/data-subject-request-form/"

# "Info Request" and "Data Access" are field_ebdv3-1 / -4 (which is which is not recorded here).
INFO_REQUEST_AND_DATA_ACCESS = ["field_ebdv3-1", "field_ebdv3-4"]
DO_NOT_SELL_OR_SHARE = "field_ebdv3-5"  # "Do Not Sell or Share My Personal Information"
LIMIT_SENSITIVE_PI = "field_ebdv3-6"  # "Limit the Use of My Sensitive Personal Information"
DATA_DELETION = "field_ebdv3-2"  # "Data Deletion"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: INFO_REQUEST_AND_DATA_ACCESS,
    Right.RIGHT_TO_OPT_OUT: [DO_NOT_SELL_OR_SHARE, LIMIT_SENSITIVE_PI],
    Right.RIGHT_TO_DELETE: DATA_DELETION,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_type_ids = []
    for right in rights:
        entries = RIGHT_MAP[right]
        request_type_ids += entries if isinstance(entries, list) else [entries]

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
            await details_field.type_text(SuperScraper.request_statement(rights, broker="Verve"))
        else:
            print(f"{super_scraper.OOPS} Request Details field not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print("\nRequest filled but NOT submitted (invisible reCAPTCHA v2, no manual solve needed).")


asyncio.run(main())
