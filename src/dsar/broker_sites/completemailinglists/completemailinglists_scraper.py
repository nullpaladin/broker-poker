# completemailinglists.com — HubSpot form ("Complete Mailing Lists"). All rights AND the
# requestor-type are one combined multi-select checkbox group sharing the same
# (oddly-named) field. Single submission with every selected right ticked.
# Zip field name is literally "0-2/zip" (a HubSpot quirk, not a typo here).
# Optional file upload for requestor verification — left unfilled. reCAPTCHA
# is HubSpot's own hidden/invisible integration (hs-recaptcha-response) and
# does not require manual solving.
# "Correct My Information" is offered by the form but not automated (see PAGE_RIGHTS).
#
# Page elements (inputs located by name=):
#   firstname / lastname      First / Last name
#   phone                     Phone
#   email                     Email
#   address / city / state    Address / City / State (text inputs)
#   0-2/zip                   ZIP code
#   date_of_birth             Date of birth
#   checkbox "INDIVIDUAL requestor *"   Requestor type (always ticked)
#   checkboxes by value       Rights (see RIGHT_MAP)
#   input[type=submit]        Submit
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.completemailinglists.com/consumer-privacy-request"

ATTESTATION_CHECKBOX = "INDIVIDUAL requestor *"
OPT_OUT_SALE_SHARE_TARGETED_ADS = "Opt Out of Sale and Sharing or Use for Targeted Advertising"
LIMIT_SENSITIVE_PI = "Limit the Use of My Sensitive Personal Information"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access My Information",
    Right.RIGHT_TO_OPT_OUT: [OPT_OUT_SALE_SHARE_TARGETED_ADS, LIMIT_SENSITIVE_PI],
    Right.RIGHT_TO_DELETE: "Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Checkbox values the page lists -> Right (None = offered but not automated).
PAGE_RIGHTS = {
    "Access My Information": Right.RIGHT_TO_ACCESS,
    "Correct My Information": None,
    OPT_OUT_SALE_SHARE_TARGETED_ADS: Right.RIGHT_TO_OPT_OUT,
    LIMIT_SENSITIVE_PI: Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        text_fields = [
            ("firstname", SuperScraper.FIRST_NAME),
            ("lastname", SuperScraper.LAST_NAME),
            ("phone", SuperScraper.PHONE_NUMBER),
            ("email", SuperScraper.EMAIL),
            ("address", SuperScraper.ADDRESS),
            ("city", SuperScraper.CITY),
            ("state", SuperScraper.STATE),
            ("0-2/zip", SuperScraper.ZIP_CODE),
            ("date_of_birth", SuperScraper.DATE_OF_BIRTH),
        ]
        for name, value in text_fields:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        checkboxes = [ATTESTATION_CHECKBOX]
        for right in rights:
            entries = RIGHT_MAP[right]
            checkboxes += entries if isinstance(entries, list) else [entries]
        for value in checkboxes:
            box = await tab.find(xpath=f"//input[@type='checkbox' and @value=\"{value}\"]", raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        rights_label = ", ".join(r.name for r in rights)
        if SuperScraper.DRY_RUN:
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            print(f"DRY RUN: would submit '{rights_label}' for {SuperScraper.EMAIL}")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted '{rights_label}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
