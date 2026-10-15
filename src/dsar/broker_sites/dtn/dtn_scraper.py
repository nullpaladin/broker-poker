# dtn.com — Gravity Forms privacy request form, no name/address section
# beyond zip. All rights are one multi-select checkbox group in a single
# submission: Do Not Sell/Share, Limit Sensitive PI, Access/Correct, Object
# to Processing, Data Portability, Withdraw Consent unconditionally; Delete.
# "Other" is left unchecked (its textarea is
# only actually required by Gravity Forms' conditional logic when "Other"
# itself is selected). In place of a CAPTCHA, the form asks a randomized
# arithmetic question ("What is X+Y?") via a <select> of multiple-choice
# answers — solved dynamically by parsing the placeholder text and picking
# the option whose value matches the computed sum. A required attestation
# checkbox ("Please verify: ...true and accurate...") is checked. A OneTrust
# cookie-consent modal ("Privacy Preference Center") auto-opens over the form
# on load and intercepts clicks until dismissed via its aria-label="Close" (×)
# button — its "Accept All Cookies"/"Confirm My Choices" buttons are red
# herrings (hidden/inert on this page).
#
# Page elements:
#   input_47_1 / _2 / _3 / _4 / _17   First name / Last name / Email / Phone / Zip
#   input_36.1 .. input_36.7          rights checkbox group (named below)
#   #input_47_42                      arithmetic-question <select> (anti-bot)
#   #choice_47_31_1                   "Please verify: ... true and accurate ..." attestation
#   "Submit" button                   clicked by its text
#   aria-label="Close"                x button of the OneTrust cookie-consent modal
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import captcha_solutions_util
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

URL = "https://www.dtn.com/do-not-sell-my-information-form/"

# Checkbox names in the rights group (input_36.N). Only the labels the file records are named.
DELETE_BOX = "input_36.1"            # Delete
LIMIT_SENSITIVE_BOX = "input_36.3"   # Limit Sensitive PI
ACCESS_BOX = "input_36.4"            # Access
PORTABILITY_BOX = "input_36.6"       # Data Portability
# input_36.2 / .5 / .7 are the remaining opt-out style choices (Do Not Sell/Share, Object to
# Processing, Withdraw Consent); the per-box order was not recorded.
OPT_OUT_BOX_A = "input_36.2"
OPT_OUT_BOX_B = "input_36.5"
OPT_OUT_BOX_C = "input_36.7"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [ACCESS_BOX, PORTABILITY_BOX],
    Right.RIGHT_TO_OPT_OUT: [LIMIT_SENSITIVE_BOX, OPT_OUT_BOX_A, OPT_OUT_BOX_B, OPT_OUT_BOX_C],
    Right.RIGHT_TO_DELETE: [DELETE_BOX],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await asyncio.sleep(6)

        close_modal = await tab.find(**{"aria-label": "Close"}, timeout=5, raise_exc=False)
        if close_modal:
            await close_modal.click()
            await asyncio.sleep(1)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_1']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_2']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_3']", text=SuperScraper.EMAIL, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_4']", text=SuperScraper.PHONE_NUMBER, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='input_47_17']", text=SuperScraper.ZIP_CODE, sleep=0.2)

        checkboxes = [entry for right in rights for entry in RIGHT_MAP[right]]
        for name in checkboxes:
            box = await tab.find(name=name, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.2)

        placeholder_text = await js_utils.js_eval(
            tab,
            "var o = document.querySelector('#input_47_42 option[selected]'); return o ? o.textContent : '';",
        )
        answer = captcha_solutions_util.solve_math_captcha(placeholder_text or "")
        if answer is not None:
            math_select = await tab.find(id="input_47_42", raise_exc=False)
            if math_select:
                await js_utils.select_native_option(math_select, value=answer)
        else:
            print(f"{super_scraper.OOPS} Could not parse the arithmetic question '{placeholder_text}'")

        verify_box = await tab.find(id="choice_47_31_1", raise_exc=False)
        if verify_box:
            await verify_box.click()

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
