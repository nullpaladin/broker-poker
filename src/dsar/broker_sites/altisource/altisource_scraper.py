# altisource.com — /contact-us/ is a single Gravity Forms contact form whose
# visible fields change based on a "Select One" reason dropdown
# (id=input_1_13). Choosing "Privacy Data (Access/Delete)" reveals First/Last
# Name, Email, Phone, Company, a required "Area of Interest" checkbox group,
# and a free-text Message — there's no dedicated Access vs Delete selector,
# so every requested right is stated together in one message and ONE submission
# covers them all. Rights the form exposes (via the message): access, opt-out, delete;
# which ones are named is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Area of Interest" is a leftover from the generic
# contact-form template (Servicer/Origination/Technology/Real Estate
# Investors business lines) — none of it is relevant to a privacy request,
# but the group is required, so the first checkbox is ticked purely to
# satisfy validation. No captcha observed.
#
# Page elements (keep this list current):
#   #input_1_13     "Select One" reason <select> -> "Privacy Data (Access/Delete)"
#   #input_1_14_3   First name
#   #input_1_14_6   Last name
#   #input_1_4      Email
#   #input_1_5      Phone (masked input, see NOTE)
#   #input_1_41     Company
#   #choice_1_18_1  "Area of Interest" first checkbox (required group)
#   #input_1_7      Message textarea
#   #gform_submit_button_1  Submit ("SEND") button
#   "Reject All"    Cookie banner button
#
# NOTE: the PHONE field has a JS input mask ("(___) ___-____") that
# corrupts simulated keystrokes typed via type_text() — even one character
# at a time with delays, only the last few digits ever land, the rest stay
# blank underscores. Setting the value via the native input-value setter +
# input/change/blur event dispatch instead lets the mask library reformat
# the whole string correctly in one pass.
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.altisource.com/contact-us/"

# The form has no per-right selector; each right is requested in the message body, and
# all requested rights go out in a single submission.
REASON_OPTION = "Privacy Data (Access/Delete)"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: REASON_OPTION,
    Right.RIGHT_TO_OPT_OUT: REASON_OPTION,
    Right.RIGHT_TO_DELETE: REASON_OPTION,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='input_1_14_3']",
    "Last name": "//*[@id='input_1_14_6']",
    "Email": "//*[@id='input_1_4']",
    "Phone": "//*[@id='input_1_5']",
    "Company": "//*[@id='input_1_41']",
    "Message": "//*[@id='input_1_7']",
}


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
        await asyncio.sleep(5)

        reject = await tab.find(text="Reject All", raise_exc=False)
        if reject:
            await reject.click()
            await asyncio.sleep(1)

        category_select = await tab.find(id="input_1_13", raise_exc=False)
        if not category_select:
            print(f"{super_scraper.OOPS} category dropdown not found")
            return
        await js_utils.select_native_option(category_select, value=REASON_OPTION, dispatch=("change",))
        await asyncio.sleep(2)

        first = await tab.find(id="input_1_14_3", raise_exc=False)
        last = await tab.find(id="input_1_14_6", raise_exc=False)
        email = await tab.find(id="input_1_4", raise_exc=False)
        phone = await tab.find(id="input_1_5", raise_exc=False)
        company = await tab.find(id="input_1_41", raise_exc=False)
        message = await tab.find(id="input_1_7", raise_exc=False)

        if first:
            await first.click()
            await first.type_text(SuperScraper.FIRST_NAME)
        if last:
            await last.click()
            await last.type_text(SuperScraper.LAST_NAME)
        if email:
            await email.click()
            await email.type_text(SuperScraper.EMAIL)
        if phone:
            digits = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
            await js_utils.js_set_value(phone, digits, blur=True)
        if company:
            await company.click()
            await company.type_text(SuperScraper.COMPANY_NAME or "N/A")

        area_of_interest = await tab.find(id="choice_1_18_1", raise_exc=False)
        if area_of_interest:
            await area_of_interest.click()

        request_text = SuperScraper.request_statement(rights, broker="Altisource")
        if message:
            await message.click()
            await message.type_text(request_text)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        submit_btn = await tab.find(id="gform_submit_button_1", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} SEND button not found")


asyncio.run(main())
