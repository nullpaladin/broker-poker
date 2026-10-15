# usdatacorporation.com — the marketing page (usdatacorporation.com/opt-out)
# only embeds a forgetmenaut.com-hosted "Submit a Data Request" form via an
# iframe (a new platform for this repo); navigate directly to the
# underlying portal: https://www.forgetmenaut.com/rtbf/unjVFFNnmFvsZ17Fnk3Tap6U
#
# Rights the form exposes (webform_category): collection, opt_out, deletion, correction,
# limit_use, incomplete. Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). One submission per category.
# "collection" (what data is collected) is the closest equivalent to Access.
# Not automated: "correction" and "limit_use" (no concrete inaccuracy/sensitive-use to cite),
# "incomplete" (ambiguous internal-sounding category, not a clear consumer right).
# "Jurisdiction" only lists CCPA/GDPR/CACD/LGPDP/TIPA/VCDPA/OTHER; "OTHER" is used for every
# user (same closest-available-option precedent as reonomy.com/finthrive.com).
# Native <input type="date"> Date of Birth is set via JS in ISO format (YYYY-MM-DD).
# MAID/VIN/CTVID left blank (no equivalent persona data). reCAPTCHA v2 — **CAPTCHA solution required**.
#
# Page elements:
#   #webform_email / #webform_first_name / #webform_last_name   Email / First / Last name
#   #webform_phone                 Phone
#   #webform_address_1 / #webform_address_2 / #webform_city / #webform_state / #webform_zip   Address
#   #webform_country               Country
#   #webform_birthday              Date of Birth (<input type="date">)
#   #webform_jurisdiction          "Jurisdiction" <select> (set to OTHER)
#   #webform_category              "Request Category" <select>
#   #webform_direct                "This is a first-party request" checkbox
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.forgetmenaut.com/rtbf/unjVFFNnmFvsZ17Fnk3Tap6U"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "collection",
    Right.RIGHT_TO_OPT_OUT: "opt_out",
    Right.RIGHT_TO_DELETE: "deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
            await js_utils.js_set_value(field, value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    if SuperScraper.DATE_OF_BIRTH:
        day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        dob_field = await tab.find(id="webform_birthday", raise_exc=False)
        if dob_field:
            await js_utils.js_set_value(dob_field, f"{year}-{month}-{day}")
        else:
            print(f"{super_scraper.OOPS} Date of Birth field not found")

    jurisdiction_select = await tab.find(id="webform_jurisdiction", raise_exc=False)
    if jurisdiction_select:
        # The list has no entry for most states; "OTHER" is used for every user.
        await js_utils.select_native_option(jurisdiction_select, value="OTHER")
    else:
        print(f"{super_scraper.OOPS} Jurisdiction select not found")

    category_select = await tab.find(id="webform_category", raise_exc=False)
    if category_select:
        await js_utils.select_native_option(category_select, value=category)
    else:
        print(f"{super_scraper.OOPS} Request Category select not found")

    direct_checkbox = await tab.find(id="webform_direct", raise_exc=False)
    if direct_checkbox:
        await direct_checkbox.click()
    else:
        print(f"{super_scraper.OOPS} 'first-party request' checkbox not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{category}")
    print(
        f"\n'{category}' request filled but NOT submitted — a reCAPTCHA v2 checkbox requires "
        "a manual solve before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    categories = [RIGHT_MAP[right] for right in rights]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for category in categories:
            await submit_request(tab, category, super_scraper)


asyncio.run(main())
