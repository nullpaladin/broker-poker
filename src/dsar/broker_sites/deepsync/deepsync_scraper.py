# deepsync.com — two separate custom pages, both needing a Cloudflare
# Turnstile manual solve (**CAPTCHA solution required**): privacy.deepsync.com
# (opt-out/delete) and privacy.deepsync.com/request/data (Access + Correct —
# reachable only via the "Data Access Request" footer link, easy to miss).
# Both pages: "Who is this request for?" radio defaults to "Myself"
# (request_type=opt_out on the opt-out page); email/phone/address are
# repeatable (Add another) but only the first slot (`_ctx1`) is filled — this
# repo only submits one identity's worth of data. State select uses 2-letter
# abbreviations, unlike most forms in this repo that expect the full name.
# Opt-out page "What would you like us to do?" checkboxes: opt out of
# sale/share, targeted advertising, profiling, and sensitive-info use are
# exercised unconditionally; "Please delete my personal information" gated on
# REMOVE_INFORMATION. Access page requires Date of Birth via three separate
# month/day/year selects (zero-padded numeric values, e.g. "01"/"1990") that
# populate a hidden `date_of_birth` field via change-event listeners; all six
# "information_type" checkboxes (categories/sources/specific-pieces/sold-to/
# Oregon+Minnesota third-party list) are checked unconditionally as the
# access request. "correct_toggle" (Right to Correct) is left unchecked — no
# concrete inaccuracy to describe, same as Correct elsewhere in this repo.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

OPT_OUT_URL = "https://privacy.deepsync.com"
ACCESS_URL = "https://privacy.deepsync.com/request/data"

RIGHT_MAP = {
    "opt_out_sale_share": ["request_type_1"],
    "opt_out_targeted_ads": ["request_type_2"],
    "opt_out_profiling": ["request_type_3"],
    "limit_sensitive_pi": ["request_type_4"],
    "delete": ["request_type_5"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

INFORMATION_TYPE_CHECKBOXES = [
    "information_type_1",
    "information_type_2",
    "information_type_3",
    "information_type_4",
    "information_type_5",
    "information_type_6",
]


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


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
        await _select_native_option(state_select, state_abbreviation)
    else:
        print(f"{super_scraper.OOPS} State select not found")


async def submit_opt_out_delete(tab, super_scraper, state_abbreviation):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(5)

    who_radio = await tab.find(xpath="//input[@name='request_type' and @value='opt_out']", raise_exc=False)
    if who_radio:
        await who_radio.click()
    else:
        print(f"{super_scraper.OOPS} 'Myself' radio not found")

    await _fill_who_fields(tab, super_scraper, state_abbreviation)

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    checkbox_ids = [entry for code in codes for entry in RIGHT_MAP[code]]
    for checkbox_id in checkbox_ids:
        checkbox = await tab.find(id=checkbox_id, raise_exc=False)
        if checkbox:
            await checkbox.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/deepsync_dry_run_opt_out.png")
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
            await _select_native_option(select_element, value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} '{select_id}' select not found")

    for checkbox_id in INFORMATION_TYPE_CHECKBOXES:
        checkbox = await tab.find(id=checkbox_id, raise_exc=False)
        if checkbox:
            await checkbox.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/deepsync_dry_run_access.png")
    print(
        "\nAccess request filled but NOT submitted — a Cloudflare Turnstile checkbox requires a "
        "manual solve before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_abbreviation = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_opt_out_delete(tab, super_scraper, state_abbreviation)
        await submit_access(tab, super_scraper, state_abbreviation)


asyncio.run(main())
