# deepsync.com — two separate custom pages, both needing a Cloudflare
# Turnstile manual solve (**CAPTCHA solution required**): privacy.deepsync.com
# (opt-out/delete) and privacy.deepsync.com/request/data (Access + Correct —
# reachable only via the "Data Access Request" footer link, easy to miss).
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP):
# opt-out and delete go through the opt-out page (one combined submission),
# access through the access page. "Correct" (correct_toggle) is not automated.
# Both pages: "Who is this request for?" radio defaults to "Myself"
# (request_type=opt_out on the opt-out page); email/phone/address are
# repeatable (Add another) but only the first slot (`_ctx1`) is filled — this
# repo only submits one identity's worth of data. State select uses 2-letter
# abbreviations, unlike most forms in this repo that expect the full name.
# Access page requires Date of Birth via three separate month/day/year selects
# (zero-padded numeric values, e.g. "01"/"1990") that populate a hidden
# `date_of_birth` field via change-event listeners.
#
# Page elements (both pages):
#   input[name=request_type][value=opt_out]   "Who is this request for?" -> Myself
#   #first_name / #last_name                  First / Last name
#   #email_ctx1 / #phone_ctx1                 Email / Phone (first slot)
#   #who_address_ctx1 / #who_address2_ctx1 / #who_city_ctx1 / #who_zip_ctx1   Address (first slot)
#   #who_state_ctx1                           State <select> (2-letter abbreviation)
# Opt-out page "What would you like us to do?" checkboxes (REQUEST_TYPE_*):
#   #request_type_1  Opt out of sale/share
#   #request_type_2  Opt out of targeted advertising
#   #request_type_3  Opt out of profiling
#   #request_type_4  Limit use of sensitive information
#   #request_type_5  "Please delete my personal information"
# Access page:
#   #dob_month / #dob_day / #dob_year         Date of Birth selects
#   #information_type_1 .. #information_type_6  Information-type checkboxes (categories /
#       sources / specific pieces / sold-to / Oregon + Minnesota third-party list); all checked
#   #correct_toggle                           Right to Correct (left unchecked)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

OPT_OUT_URL = "https://privacy.deepsync.com"
ACCESS_URL = "https://privacy.deepsync.com/request/data"

INFORMATION_TYPE_CHECKBOXES = [
    "information_type_1",
    "information_type_2",
    "information_type_3",
    "information_type_4",
    "information_type_5",
    "information_type_6",
]

# Right -> checkbox ids to tick (the form has one checkbox per choice, so lists).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: INFORMATION_TYPE_CHECKBOXES,  # on the access page
    Right.RIGHT_TO_OPT_OUT: ["request_type_1", "request_type_2", "request_type_3", "request_type_4"],
    Right.RIGHT_TO_DELETE: ["request_type_5"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)
OPT_OUT_PAGE_RIGHTS = (Right.RIGHT_TO_OPT_OUT, Right.RIGHT_TO_DELETE)


async def _fill_who_fields(tab, super_scraper, state_abbreviation):
    fields = {
        "first_name": SuperScraper.FIRST_NAME,
        "last_name": SuperScraper.LAST_NAME,
        "email_ctx1": SuperScraper.EMAIL,
        "phone_ctx1": SuperScraper.PHONE_NUMBER,
        "who_address_ctx1": SuperScraper.ADDRESS,
        "who_address2_ctx1": SuperScraper.ADDRESS_LINE_TWO,
        "who_city_ctx1": SuperScraper.CITY,
        "who_zip_ctx1": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    state_select = await tab.find(id="who_state_ctx1", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, value=state_abbreviation)
    else:
        print(f"{super_scraper.OOPS} State select not found")


async def submit_opt_out_delete(tab, rights, super_scraper, state_abbreviation):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(5)

    who_radio = await tab.find(xpath="//input[@name='request_type' and @value='opt_out']", raise_exc=False)
    if who_radio:
        await who_radio.click()
    else:
        print(f"{super_scraper.OOPS} 'Myself' radio not found")

    await _fill_who_fields(tab, super_scraper, state_abbreviation)

    checkbox_ids = [entry for right in rights for entry in RIGHT_MAP[right]]
    for checkbox_id in checkbox_ids:
        checkbox = await tab.find(id=checkbox_id, raise_exc=False)
        if checkbox:
            await checkbox.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_opt_out")
    print(
        "\nOpt-out/delete request filled but NOT submitted — a Cloudflare Turnstile checkbox "
        "requires a manual solve before submitting."
    )


async def submit_access(tab, super_scraper, state_abbreviation):
    await tab.go_to(ACCESS_URL)
    await asyncio.sleep(5)

    await _fill_who_fields(tab, super_scraper, state_abbreviation)

    day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
    for select_id, value in (("dob_month", month), ("dob_day", day), ("dob_year", year)):
        select_element = await tab.find(id=select_id, raise_exc=False)
        if select_element:
            await js_utils.select_native_option(select_element, value=value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} '{select_id}' select not found")

    for checkbox_id in RIGHT_MAP[Right.RIGHT_TO_ACCESS]:
        checkbox = await tab.find(id=checkbox_id, raise_exc=False)
        if checkbox:
            await checkbox.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_access")
    print(
        "\nAccess request filled but NOT submitted — a Cloudflare Turnstile checkbox requires a "
        "manual solve before submitting."
    )


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    state_abbreviation = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        opt_out_page_rights = [r for r in rights if r in OPT_OUT_PAGE_RIGHTS]
        if opt_out_page_rights:
            await submit_opt_out_delete(tab, opt_out_page_rights, super_scraper, state_abbreviation)
        if Right.RIGHT_TO_ACCESS in rights:
            await submit_access(tab, super_scraper, state_abbreviation)


asyncio.run(main())
