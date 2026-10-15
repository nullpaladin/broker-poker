# onpointdatastrategy.com — OnPoint Data Strategy "opt-out" request, a 2-page
# Gravity Forms form (form id 1) at onpointdatastrategy.com/opt-out/.
# Page 1 holds every field; "Submit Request" (gform_next_button_1_8) advances to
# page 2 (reCAPTCHA + final submit). ONE submission per run: the "Request Type"
# <select> offers "Opt-Out Only", "Do Not Sell My Data Only", "Request Information
# Only", "Opt Out & Request Information", "Remove me from your database". Which of
# them is picked is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP):
# "Remove me from your database" when RIGHT_TO_DELETE is requested, else the combined
# "Opt Out & Request Information" (opt-out + access).
# The page-1 "Next" advances cleanly once every required field (incl. the
# free-text State) is set. NOTE: the placeholder `.env` email jdoe@example.com
# is rejected by the form as an invalid domain — a real address is needed for a
# live run. reCAPTCHA v2 on page 2 needs a manual solve.
# **CAPTCHA solution required**
#
# Page elements (keep this list current):
#   #input_1_1_3 / #input_1_1_6   Name: First / Last (1.2 prefix, 1.4 middle, 1.8 suffix left blank)
#   #input_1_3                    Email
#   #input_1_4_1 / _3 / _4 / _5   Address: street / city / state (a TEXT input, not a select) / ZIP
#   #input_1_4_6                  Address country <select> -> "United States"
#   #input_1_6                    Phone (optional)
#   #input_1_5 (REQUEST_TYPE_SELECT)  Required "Request Type" <select> (enhanced-UI / chosen)
#   #gform_next_button_1_8        "Submit Request" — advances to page 2
#   #gform_page_1_2               Page 2 container (reCAPTCHA + final submit)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://onpointdatastrategy.com/opt-out/"

COMBINED = "Opt Out & Request Information"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: COMBINED,
    Right.RIGHT_TO_OPT_OUT: COMBINED,
    Right.RIGHT_TO_DELETE: "Remove me from your database",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)
REQUEST_TYPE_SELECT = "input_1_5"


async def _select_native(tab, element_id, match_text):
    el = await tab.find(id=element_id, raise_exc=False)
    if not el:
        return
    await js_utils.select_native_option(el, text=match_text, ci=True)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    # The form takes a single request type: deletion wins, otherwise the combined opt-out+access.
    right = Right.RIGHT_TO_DELETE if Right.RIGHT_TO_DELETE in rights else rights[0]
    request_type = RIGHT_MAP[right]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        for xpath, value in {
            "//input[@id='input_1_1_3']": SuperScraper.FIRST_NAME,
            "//input[@id='input_1_1_6']": SuperScraper.LAST_NAME,
            "//input[@id='input_1_3']": SuperScraper.EMAIL,
            "//input[@id='input_1_4_1']": SuperScraper.ADDRESS,
            "//input[@id='input_1_4_3']": SuperScraper.CITY,
            "//input[@id='input_1_4_4']": SuperScraper.STATE,
            "//input[@id='input_1_4_5']": SuperScraper.ZIP_CODE,
            "//input[@id='input_1_6']": SuperScraper.PHONE_NUMBER,
        }.items():
            await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.2)

        await _select_native(tab, "input_1_4_6", "United States")      # address: country
        await _select_native(tab, REQUEST_TYPE_SELECT, request_type)           # request type

        await asyncio.sleep(0.5)
        next_btn = await tab.find(id="gform_next_button_1_8", raise_exc=False)
        if next_btn:
            await next_btn.click()
            await asyncio.sleep(4)

        advanced = bool(await js_utils.js_eval(
            tab,
            "const p=document.getElementById('gform_page_1_2');"
            "return !!p && getComputedStyle(p).display!=='none';",
        ))
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        if not advanced:
            print(
                f"{super_scraper.OOPS} Page 1 filled (request type: '{request_type}') but 'Next' "
                f"did not advance — Gravity Forms anti-spam under automation. Click Next manually, "
                f"then solve the page-2 reCAPTCHA and submit."
            )
            return

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: page 1 filled and advanced (request type: '{request_type}') for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>. "
                f"Page 2 has a reCAPTCHA + final submit."
            )
            return

        print("\nPage 2 reached. Solve the reCAPTCHA, click the final Submit, then press Enter...")
        input()


asyncio.run(main())
