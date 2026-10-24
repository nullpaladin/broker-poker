# locatesmarter.com — two separate Gravity Forms (WordPress), one per URL.
# "Request to Know or Delete" form has checkboxes for "know" (access) and
# "delete" that can both be ticked in the same
# submission — filled together in one pass. Separate "Request to Opt Out of
# Do Not Sell" form only has the self/minor/third-party toggles; "own
# personal information" (self) is used. Both forms also have minor/
# third-party sections that are skipped (this repo only ever requests on
# behalf of the account holder). Both use an invisible reCAPTCHA v2
# (size=invisible sitekey) that auto-resolves without a visible challenge —
# no manual solve needed, so DRY_RUN is respected and a real submission goes
# through when DRY_RUN is False.
#
# Page elements ("Request to Know or Delete" form = Gravity Forms form 2):
#   input_2_2 / input_2_3     Name (first + last) / Email
#   input_2_5_1 / _3 / _4 / _5   Street / City / State <select> / ZIP
#   choice_2_14_1             "I want to know my own personal information" (own PI, always ticked)
#   choice_2_29_1             "know for past 12 months"
#   choice_2_20_1             "receive copy of personal information" (access)
#   choice_2_32_1             "delete personal information"
#   gform_submit_button_2     Submit
# ("Request to Opt Out of Do Not Sell" form = Gravity Forms form 1):
#   input_1_2 / input_1_3     Name (first + last) / Email
#   input_1_5_1 / _3 / _4 / _5   Street / City / State <select> / ZIP
#   choice_1_14_1             "stop selling my personal information"
#   gform_submit_button_1     Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

KNOW_DELETE_URL = "https://locatesmarter.com/request-to-know-or-delete-my-personal-information/"
OPT_OUT_URL = "https://locatesmarter.com/request-to-opt-out-do-not-sell-my-personal-information/"

OWN_PI = "choice_2_14_1"  # own personal information (always ticked on the know/delete form)
KNOW_12_MONTHS = "choice_2_29_1"  # know for past 12 months
RECEIVE_COPY = "choice_2_20_1"  # receive copy of personal information
DELETE_PI = "choice_2_32_1"  # delete personal information
STOP_SELLING = "choice_1_14_1"  # stop selling my personal information (opt-out form)

# Right -> checkbox id(s) ticked on that right's form. ACCESS and DELETE share the
# "know or delete" form (one submission); OPT_OUT is its own form.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [KNOW_12_MONTHS, RECEIVE_COPY],
    Right.RIGHT_TO_DELETE: DELETE_PI,
    Right.RIGHT_TO_OPT_OUT: STOP_SELLING,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Checkbox labels are paraphrased in the notes, so no inventory is built.)

KNOW_DELETE_FIELD_XPATHS = {
    "Name": "//*[@id='input_2_2']",
    "Email": "//*[@id='input_2_3']",
    "Street": "//*[@id='input_2_5_1']",
    "City": "//*[@id='input_2_5_3']",
    "State": "//*[@id='input_2_5_4']",
    "Zip": "//*[@id='input_2_5_5']",
}
OPT_OUT_FIELD_XPATHS = {
    "Name": "//*[@id='input_1_2']",
    "Email": "//*[@id='input_1_3']",
    "Street": "//*[@id='input_1_5_1']",
    "City": "//*[@id='input_1_5_3']",
    "State": "//*[@id='input_1_5_4']",
    "Zip": "//*[@id='input_1_5_5']",
}


async def _fill_common_fields(tab, name_id, email_id, street_id, city_id, state_id, zip_id, super_scraper):
    fields = {
        name_id: f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
        email_id: SuperScraper.EMAIL,
        street_id: SuperScraper.ADDRESS,
        city_id: SuperScraper.CITY,
        zip_id: SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    state_select = await tab.find(id=state_id, raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, value=SuperScraper.STATE)
    else:
        print(f"{super_scraper.OOPS} State select '{state_id}' not found")


async def _check(tab, checkbox_id, super_scraper):
    checkbox = await tab.find(id=checkbox_id, raise_exc=False)
    if checkbox:
        await checkbox.click()
        await asyncio.sleep(0.3)
    else:
        print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")


async def _submit_or_dry_run(tab, submit_button_id, label, super_scraper):
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.EMAIL}")
        return

    submit_button = await tab.find(id=submit_button_id, raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print(f"Submitted '{label}' request for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} submit button '{submit_button_id}' not found")


async def submit_know_delete(tab, checkbox_ids, super_scraper):
    await tab.go_to(KNOW_DELETE_URL)
    await asyncio.sleep(4)

    await _fill_common_fields(
        tab, "input_2_2", "input_2_3", "input_2_5_1", "input_2_5_3", "input_2_5_4", "input_2_5_5", super_scraper
    )
    await _check(tab, OWN_PI, super_scraper)
    for checkbox_id in checkbox_ids:
        await _check(tab, checkbox_id, super_scraper)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, KNOW_DELETE_FIELD_XPATHS)

    await _submit_or_dry_run(tab, "gform_submit_button_2", "know_delete", super_scraper)


async def submit_opt_out(tab, super_scraper):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(4)

    await _fill_common_fields(
        tab, "input_1_2", "input_1_3", "input_1_5_1", "input_1_5_3", "input_1_5_4", "input_1_5_5", super_scraper
    )
    await _check(tab, "choice_1_14_1", super_scraper)  # STOP_SELLING

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, OPT_OUT_FIELD_XPATHS)

    await _submit_or_dry_run(tab, "gform_submit_button_1", "opt_out", super_scraper)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    know_delete_checks = []
    for right in rights:
        if right is Right.RIGHT_TO_OPT_OUT:
            continue
        entries = RIGHT_MAP[right]
        know_delete_checks.extend(entries if isinstance(entries, list) else [entries])

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        if know_delete_checks:
            await submit_know_delete(tab, know_delete_checks, super_scraper)
        if Right.RIGHT_TO_OPT_OUT in rights:
            await submit_opt_out(tab, super_scraper)


asyncio.run(main())
