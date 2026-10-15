# liftbasedata.com — request-to-know/liftbase/. Page is titled "Opt-Out
# Request" but that's really the umbrella for the whole form — the actual
# rights are exercised via independent Yes/No <select> toggles further
# down (a Gravity Forms form, `input_N` naming), NOT single-select radios:
# "Delete all the personal data..." (Right to delete),
# "Send a summary [of] the data categories..." and "Send a summary of
# where the data... has been shared" (together = Access/Right-to-Know),
# "Correct / update my data..." (not automatable; always answered "No"). Because these are independent toggles on ONE form rather than
# a single-select request-type picker, this is a single submission with
# every desired toggle set, not one submission per right.
#
# "Are you acting as an agency on behalf of a consumer?" must be answered
# "No" first — the entire Consumer Information / Mailing Address / rights-
# toggle section only renders in the DOM after that. Marital Status is a
# required select with no "prefer not to answer" option (Single/Married
# only) — "Single" is used as the arbitrary required pick. DATE_OF_BIRTH
# (DD/MM/YYYY per this repo's .env convention) is split into separate
# MM/DD/YYYY number inputs. Both Cloudflare Turnstile and reCAPTCHA v2 are
# present — **CAPTCHA solution required**; the form is filled completely
# and left there regardless.
#
# Page elements (Gravity Forms form 1; select answers are by visible text):
#   input_1_16     "Are you acting as an agency on behalf of a consumer?" <select> -> "No"
#   input_1_1_3 / input_1_1_6   First / Last name
#   input_1_3_1 / _2 / _3       Date of birth: month / day / year
#   input_1_28     "Marital Status" <select> -> "Single" (required)
#   input_1_4 / input_1_4_2     Email / confirm email
#   input_1_9_1 / _2 / _3 / _5  Address / Address line 2 / City / ZIP
#   input_1_9_4    State <select>
#   input_1_26     "Delete all the personal data..." Yes/No <select>
#   input_1_24     "Send a summary [of] the data categories..." Yes/No <select>
#   input_1_25     "Send a summary of where the data... has been shared" Yes/No <select>
#   input_1_27     "Correct / update my data..." Yes/No <select> -> always "No"
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.liftbasedata.com/request-to-know/liftbase/"

AGENCY_SELECT = "input_1_16"  # "Are you acting as an agency on behalf of a consumer?"
FIRST_NAME_ID = "input_1_1_3"
LAST_NAME_ID = "input_1_1_6"
MARITAL_SELECT = "input_1_28"  # "Marital Status"
EMAIL_ID = "input_1_4"
EMAIL_CONFIRM_ID = "input_1_4_2"
STATE_SELECT = "input_1_9_4"
DELETE_SELECT = "input_1_26"  # "Delete all the personal data..."
CATEGORIES_SELECT = "input_1_24"  # "Send a summary [of] the data categories..."
SHARING_SELECT = "input_1_25"  # "Send a summary of where the data... has been shared"
CORRECT_SELECT = "input_1_27"  # "Correct / update my data..."

# Right -> the Yes/No <select> id(s) set to "Yes" when that right is exercised.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CATEGORIES_SELECT, SHARING_SELECT],
    Right.RIGHT_TO_DELETE: DELETE_SELECT,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_text(tab, element_id, text):
    select = await tab.find(id=element_id, raise_exc=False)
    if select:
        await js_utils.select_native_option(select, text=text)


async def main():
    super_scraper = SuperScraper()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    yes_ids = set()
    for right in rights:
        entries = RIGHT_MAP[right]
        yes_ids.update(entries if isinstance(entries, list) else [entries])

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        agency_select = await tab.find(id=AGENCY_SELECT, raise_exc=False)
        if not agency_select:
            agency_select = await tab.find(xpath="//select", raise_exc=False)
        if agency_select:
            await js_utils.select_native_option(agency_select, text="No")
        await asyncio.sleep(2)

        first_field = await tab.find(id=FIRST_NAME_ID, raise_exc=False)
        if first_field:
            await first_field.type_text(SuperScraper.FIRST_NAME)
        last_field = await tab.find(id=LAST_NAME_ID, raise_exc=False)
        if last_field:
            await last_field.type_text(SuperScraper.LAST_NAME)

        try:
            day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
        except (ValueError, AttributeError):
            month, day, year = "01", "01", "1980"
        dob_fields = {"input_1_3_1": month, "input_1_3_2": day, "input_1_3_3": year}
        for field_id, value in dob_fields.items():
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        await _select_text(tab, MARITAL_SELECT, "Single")

        email_field = await tab.find(id=EMAIL_ID, raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        confirm_email_field = await tab.find(id=EMAIL_CONFIRM_ID, raise_exc=False)
        if confirm_email_field:
            await confirm_email_field.type_text(SuperScraper.EMAIL)

        address_fields = {
            "input_1_9_1": SuperScraper.ADDRESS,
            "input_1_9_2": SuperScraper.ADDRESS_LINE_TWO,
            "input_1_9_3": SuperScraper.CITY,
            "input_1_9_5": SuperScraper.ZIP_CODE,
        }
        for field_id, value in address_fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        await _select_text(tab, STATE_SELECT, SuperScraper.STATE)

        for select_id in (DELETE_SELECT, CATEGORIES_SELECT, SHARING_SELECT):
            await _select_text(tab, select_id, "Yes" if select_id in yes_ids else "No")
        await _select_text(tab, CORRECT_SELECT, "No")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "\nForm filled but NOT submitted — both Cloudflare Turnstile and reCAPTCHA v2 "
            "are present and require a manual solve before submitting."
        )


asyncio.run(main())
