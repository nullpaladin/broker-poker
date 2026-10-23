# penlink.com — /your-privacy-choices/ Gravity Forms (form 9), server-rendered.
# One submission per "Request Type" (input_9_33 <select>); which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Options offered but not automated: Correct,
# Object, "Opt out of marketing". The third-parties option is labelled "(Oregon and Minnesota
# only)" on the page. reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   #input_9_33 (REQUEST_TYPE_SELECT)  "Request Type" <select>, options -> see RIGHT_MAP
#   #input_9_1 / #input_9_10           First / Last name
#   #input_9_2                         Email
#   #input_9_23                        Advertising ID
#   #input_9_24_1 .. _5                Street / Line 2 / City / State / ZIP
#   #input_9_24_6                      Country <select> -> "United States"
#   #choice_9_25_0                     Radio "The consumer named above"
#   #input_9_34                        Comments (left blank)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://www.penlink.com/your-privacy-choices/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access my personal information / Port my personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Opt out of sale or sharing of my personal information", "opt_out")],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: [
        ("Request list of third parties to which personal information was disclosed "
         "(Oregon and Minnesota only)", "third_parties")
    ],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "#input_9_33 option"  # Correct / Object / marketing opt-out texts are unrecorded

FIELD_XPATHS = {
    "Request type": "//*[@id='input_9_33']",
    "First name": "//*[@id='input_9_1']",
    "Last name": "//*[@id='input_9_10']",
    "Email": "//*[@id='input_9_2']",
    "Street": "//*[@id='input_9_24_1']",
    "City": "//*[@id='input_9_24_3']",
    "State": "//*[@id='input_9_24_4']",
    "Zip": "//*[@id='input_9_24_5']",
    "Country": "//*[@id='input_9_24_6']",
}
REQUEST_TYPE_SELECT = "input_9_33"


async def submit_request(tab, right_label, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    rt = await tab.find(id=REQUEST_TYPE_SELECT, raise_exc=False)
    if rt:
        await js_utils.select_native_option(rt, text=right_label)
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} request-type select not found")

    fields = {
        "input_9_1": SuperScraper.FIRST_NAME,
        "input_9_10": SuperScraper.LAST_NAME,
        "input_9_2": SuperScraper.EMAIL,
        "input_9_23": SuperScraper.ADVERTISING_ID,
        "input_9_24_1": SuperScraper.ADDRESS,
        "input_9_24_2": SuperScraper.ADDRESS_LINE_TWO,
        "input_9_24_3": SuperScraper.CITY,
        "input_9_24_4": SuperScraper.STATE,
        "input_9_24_5": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.12)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    country = await tab.find(id="input_9_24_6", raise_exc=False)
    if country:
        await js_utils.select_native_option(country, text="United States")

    consumer_radio = await tab.find(id="choice_9_25_0", raise_exc=False)
    if consumer_radio:
        await consumer_radio.click()

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{tag}")
    print(f"'{right_label}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in requests:
            await submit_request(tab, right_label, tag, super_scraper)


asyncio.run(main())
