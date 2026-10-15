# specialtycontactdatabases.com — /do-not-sell/ Gravity Forms (form id 2),
# server-rendered, POSTs in place. One submission per right, chosen via the
# "input_7" radio group:
#   - "Request to Know ..."  -> Access
#   - "Do Not Sell My Info ..." -> Opt-Out
#   - "Delete My Info ..."   -> Delete
# Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Page elements (GF renders name='input_N' as id='input_2_N', name='input_6.1' as
# id='input_2_6_1'):
#   input[name=input_7]  Request-type radio group (values above)
#   input_2_3_3 / input_2_3_6   First / Last name
#   input_2_4            Email
#   input_2_5            Phone
#   input_2_6_1 / input_2_6_2   Street / Address line 2
#   input_2_6_3          City
#   input_2_6_4          State (plain text)
#   input_2_6_5          Zip
#   input_2_6_6          Country <select> -> "United States"
# Ends in a Gravity Forms reCAPTCHA v2 checkbox — every other field is filled
# and the form is left for a manual solve + Submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://specialtycontactdatabases.com/do-not-sell/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request to Know", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do Not Sell My Info", "opt_out")],
    Right.RIGHT_TO_DELETE: [("Delete My Info", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, value_prefix, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    radio = await tab.find(
        xpath=f"//input[@name='input_7' and starts-with(@value, {value_prefix!r})]", raise_exc=False
    )
    if not radio:
        print(f"{super_scraper.OOPS} request-type radio {value_prefix!r} not found")
        return
    await radio.click()
    await asyncio.sleep(0.5)

    fields = {
        "input_2_3_3": SuperScraper.FIRST_NAME,
        "input_2_3_6": SuperScraper.LAST_NAME,
        "input_2_4": SuperScraper.EMAIL,
        "input_2_5": SuperScraper.PHONE_NUMBER,
        "input_2_6_1": SuperScraper.ADDRESS,
        "input_2_6_2": SuperScraper.ADDRESS_LINE_TWO,
        "input_2_6_3": SuperScraper.CITY,
        "input_2_6_4": SuperScraper.STATE,
        "input_2_6_5": SuperScraper.ZIP_CODE,
    }
    for field_id, val in fields.items():
        if not val:
            continue
        el = await tab.find(id=field_id, raise_exc=False)
        if el:
            await el.type_text(val)
            await asyncio.sleep(0.15)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    country = await tab.find(id="input_2_6_6", raise_exc=False)
    if country:
        await js_utils.select_native_option(country, text="United States")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"'{value_prefix}' request filled but NOT submitted — a reCAPTCHA v2 "
        f"checkbox must be solved manually before Submit."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for value_prefix, label in requests:
            await submit_request(tab, value_prefix, label, super_scraper)


asyncio.run(main())
