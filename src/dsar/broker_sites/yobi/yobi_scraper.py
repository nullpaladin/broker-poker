# yobi.ai — "opt-out" / privacy-rights form at yobi.ai/opt-out (custom form that
# posts to HubSpot; field names are HubSpot internal names).
# Server-rendered. All personal fields are required: firstname, lastname, email,
# phone, address, city, state, zip, country, and date_of_birth__do_not_sell_
# (an <input type="date"> — DATE_OF_BIRTH is DD/MM/YYYY in .env and MUST be
# converted to YYYY-MM-DD or the field silently stays empty).
# "I am submitting on behalf of" is a required radio group — "Myself".
# "Select the right(s) you want to exercise" is a multi-select checkbox group
# (one combined submission): Access My Information, Do Not Sell My Information,
# "Object or Restrict the Processing of My Data", Move My Data unconditionally;
# Delete My Information; "Correct My Data" is not automated.
# Which of them are checked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# No CAPTCHA observed.
#
# Page elements:
#   [name=firstname] / [name=lastname] / [name=email] / [name=phone]   Name, email, phone
#   [name=address] / [name=city] / [name=state] / [name=zip] / [name=country]   Address
#   #date_of_birth__do_not_sell_    Date of birth (<input type="date">, YYYY-MM-DD)
#   [name=i_am_submitting_on_behalf_of][value=Myself]   "I am submitting on behalf of" radio
#   [name=select_the_right_s__you_want_to_exercise_]    Right checkboxes (see RIGHT_MAP)
#   form#optout-form button[type=submit]                Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.yobi.ai/opt-out"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access My Information", "Move My Data"],
    Right.RIGHT_TO_OPT_OUT: ["Do Not Sell My Information", "Object or Restrict the Processing of My Data"],
    Right.RIGHT_TO_DELETE: "Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Select the right(s) you want to exercise" checkbox group, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Access My Information": Right.RIGHT_TO_ACCESS,
    "Move My Data": Right.RIGHT_TO_ACCESS,
    "Do Not Sell My Information": Right.RIGHT_TO_OPT_OUT,
    "Object or Restrict the Processing of My Data": Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
    "Correct My Data": None,
}
RIGHTS_OPTIONS_CSS = "label:has(input[name='select_the_right_s__you_want_to_exercise_'])"

FIELD_XPATHS = {
    "First name": "//*[@name='firstname']",
    "Last name": "//*[@name='lastname']",
    "Email": "//*[@name='email']",
    "Phone": "//*[@name='phone']",
    "Address": "//*[@name='address']",
    "City": "//*[@name='city']",
    "State": "//*[@name='state']",
    "Zip": "//*[@name='zip']",
    "Country": "//*[@name='country']",
    "Date of birth": "//*[@id='date_of_birth__do_not_sell_']",
}


def _dob_iso():
    raw = (SuperScraper.DATE_OF_BIRTH or "").strip()
    for sep in ("/", "-", "."):
        if sep in raw:
            parts = raw.split(sep)
            if len(parts) == 3 and len(parts[2]) == 4:
                d, m, y = parts
                return f"{y}-{int(m):02d}-{int(d):02d}"
    return raw


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
        await tab.go_to(URL)
        await asyncio.sleep(4)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

        text_fields = {
            "firstname": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
            "country": "United States",
        }
        for name, value in text_fields.items():
            await super_scraper.input_text_field(
                tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2,
            )

        dob = await tab.find(id="date_of_birth__do_not_sell_", raise_exc=False)
        if dob:
            await js_utils.js_set_value(dob, _dob_iso())

        myself = await tab.find(
            xpath="//input[@name='i_am_submitting_on_behalf_of' and @value='Myself']", raise_exc=False
        )
        if myself:
            await myself.click()

        values = []
        for right in rights:
            entries = RIGHT_MAP[right]
            values += entries if isinstance(entries, list) else [entries]
        for value in values:
            box = await tab.find(
                xpath=f"//input[@name='select_the_right_s__you_want_to_exercise_' and @value={value!r}]",
                raise_exc=False,
            )
            if box:
                await js_utils.js_check(box)
                await asyncio.sleep(0.1)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//form[@id='optout-form']//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(3)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
