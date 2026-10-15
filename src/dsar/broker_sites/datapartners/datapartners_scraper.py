# datapartners.com — two separate Zoho CRM webforms (Zoho custom field ids
# like "CASECF1", "CASECF2" — opaque but stable across both pages): Access
# request (/information-access-request/) and Opt-Out request
# (/opt-out-request/). Each page has its own BotDetect-style image CAPTCHA
# (name="enterdigest") requiring manual entry in live mode, so the script only
# fills the form. Which of the two run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). The "2nd/3rd" variants of every
# field (for aliases) are left blank.
#
# Page elements:
#   #Subject      Subject (required, free text — short description used)
#   #CASECF17     Privacy Submitter <select> (required) -> "Submitted by the Individual Requesting"
#   #CASECF1      First Name (required)
#   #CASECF2      Last Name (required)
#   #Email        Email (required)
#   #CASECF7      State (required)
#   #Phone        Phone (optional)
#   #CASECF3      Address1 (optional)
#   #CASECF5      City (optional)
#   #CASECF6      Zip Code (optional)
#   [name=enterdigest]  Image CAPTCHA (manual)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

ACCESS_URL = "https://www.datapartners.com/information-access-request/"
OPT_OUT_URL = "https://www.datapartners.com/opt-out-request/"

# Right -> (form URL, Subject text)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: (ACCESS_URL, "Information Access Request"),
    Right.RIGHT_TO_OPT_OUT: (OPT_OUT_URL, "Opt Out Request"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, entry, super_scraper):
    url, subject = entry
    await tab.go_to(url)
    await asyncio.sleep(5)

    subject_field = await tab.find(id="Subject", raise_exc=False)
    if subject_field:
        await subject_field.type_text(subject)

    submitter_select = await tab.find(id="CASECF17", raise_exc=False)
    if submitter_select:
        await js_utils.select_native_option(submitter_select, value="Submitted by the Individual Requesting")

    fields = {
        "CASECF1": SuperScraper.FIRST_NAME,
        "CASECF2": SuperScraper.LAST_NAME,
        "Email": SuperScraper.EMAIL,
        "Phone": SuperScraper.PHONE_NUMBER,
        "CASECF3": SuperScraper.ADDRESS,
        "CASECF5": SuperScraper.CITY,
        "CASECF7": SuperScraper.STATE,
        "CASECF6": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: forms filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}, not submitted")
            return

        print("\nForms filled. Solve each page's image CAPTCHA and click Submit manually.")


asyncio.run(main())
