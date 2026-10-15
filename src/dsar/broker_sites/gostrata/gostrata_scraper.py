# gostrata.com — /do-not-sell-my-personal-information/ Gravity Forms (form id 5),
# server-rendered, POSTs in place. A single bundled request: the required
# certification checkbox reads "...you wish to have your personal information
# deleted and not sold", so this is Opt-Out + Delete combined with no separate
# Access path. It is the only mechanism the site offers, so it is filled whenever
# SuperScraper.rights_to_exercise(RIGHT_MAP) includes Opt-out or Delete (the one
# checkbox covers both; the form cannot request just one).
#
# Quirks:
#  - The whole #gform_wrapper_5 ships with style="display:none" and is only
#    un-hidden by the page's own jQuery on ready; a Complianz cookie banner
#    ("Accept") sits in front of it. This scraper clicks Accept, then force-
#    un-hides the wrapper if it is still hidden, before filling.
#  - Every field starts with 0x0 layout, so type_text()'s visibility check
#    fails — values are set via the native input setter + input/change events
#    instead (the phone field also has a jQuery .mask('(999) 999-9999') that
#    reformats on the input event).
# Fields (GF id scheme: name='input_12.3' -> id='input_5_12_3'):
#   input_5_19  honeypot ("URL") — left blank
#   input_5_12_3 / input_5_12_6  first / last name
#   input_5_13_1 street, input_5_13_3 city, input_5_13_4 <select> state,
#   input_5_13_5 zip  (input_5_13_6 hidden country already "United States")
#   input_5_14 email, input_5_8 email confirmation, input_5_15 phone
#   input_5_16_1 required certification checkbox ("...you wish to have your personal
#       information deleted and not sold"), input_5_17 comments (blank)
#   .cmplz-accept  Complianz cookie banner "Accept"
# Ends in a CAPTCHA (input_5_18) — filled to that point and left for a manual
# solve + Submit.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.gostrata.com/do-not-sell-my-personal-information/"

STATE_SELECT = "input_5_13_4"
CERTIFICATION_CHECKBOX = "input_5_16_1"  # "...you wish to have your personal information deleted and not sold"

# One bundled form covers both rights.
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: CERTIFICATION_CHECKBOX,
    Right.RIGHT_TO_DELETE: CERTIFICATION_CHECKBOX,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        # Dismiss the Complianz cookie banner (may be absent/offscreen in
        # headless) — click it via JS rather than a visibility-gated .click().
        await tab.execute_script(
            "var b=document.querySelector('.cmplz-accept,.cmplz-btn.cmplz-accept');"
            "if(b){b.click();}"
        )
        await asyncio.sleep(2)

        # Un-hide the form wrapper if the page JS hasn't already.
        await tab.execute_script(
            "var w=document.getElementById('gform_wrapper_5');"
            "if(w){w.style.display='';w.removeAttribute('style');}"
            "var f=document.getElementById('gform_5'); if(f){f.style.opacity='';}"
        )
        await asyncio.sleep(1)

        text_fields = {
            "input_5_12_3": SuperScraper.FIRST_NAME,
            "input_5_12_6": SuperScraper.LAST_NAME,
            "input_5_13_1": SuperScraper.ADDRESS,
            "input_5_13_3": SuperScraper.CITY,
            "input_5_13_5": SuperScraper.ZIP_CODE,
            "input_5_14": SuperScraper.EMAIL,
            "input_5_8": SuperScraper.EMAIL,
            "input_5_15": SuperScraper.PHONE_NUMBER,
        }
        for field_id, val in text_fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if not el:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")
                continue
            await js_utils.js_set_value(el, val)
            if not await js_utils.js_eval(el, "return this.value"):
                print(f"{super_scraper.OOPS} field '{field_id}' set but read back empty")

        state = await tab.find(id=STATE_SELECT, raise_exc=False)
        if state:
            await js_utils.select_native_option(state, text=SuperScraper.STATE, dispatch=("change",))
        else:
            print(f"{super_scraper.OOPS} state <select> not found")

        cert = await tab.find(id=CERTIFICATION_CHECKBOX, raise_exc=False)
        if cert:
            await js_utils.js_check(cert)
        else:
            print(f"{super_scraper.OOPS} certification checkbox not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            f"{[r.name for r in rights]} request filled but NOT submitted — solve the CAPTCHA "
            "(input_5_18) manually, then click Submit."
        )


asyncio.run(main())
