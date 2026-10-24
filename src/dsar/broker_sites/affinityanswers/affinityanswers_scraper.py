# affinityanswers.com — single Gravity Forms POST form (form 11) with one checkbox per
# right: Access, Correct, Opt-Out of Sale, Opt-Out of Targeted Advertising, Delete. All
# requested rights are ticked in ONE submission; which are ticked is decided only by
# SuperScraper.rights_to_exercise. Correct is not automatable (not in RIGHT_MAP).
# Residency select uses full state name.
# reCAPTCHA v3 is invisible and auto-resolves in the browser.
#
# Page elements:
#   select[name=input_4]          Residency <select> (full state name)
#   input[name=input_3]           Email
#   input[name=input_13]          Honeypot field — must be left empty
#   CHECK_ACCESS      #choice_11_5_1  Access checkbox
#   CHECK_DELETE      #choice_11_5_2  Delete checkbox
#   (#choice_11_5_3                   Correct checkbox — not automated)
#   CHECK_OPT_OUT_SALE #choice_11_5_4 Opt-out of sale checkbox
#   CHECK_OPT_OUT_ADS  #choice_11_5_5 Opt-out of targeted advertising checkbox
#   #gform_submit_button_11        Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.affinityanswers.com/your-privacy-choices/"

CHECK_ACCESS = "choice_11_5_1"
CHECK_DELETE = "choice_11_5_2"
CHECK_OPT_OUT_SALE = "choice_11_5_4"
CHECK_OPT_OUT_ADS = "choice_11_5_5"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CHECK_ACCESS],
    Right.RIGHT_TO_OPT_OUT: [CHECK_OPT_OUT_SALE, CHECK_OPT_OUT_ADS],
    Right.RIGHT_TO_DELETE: [CHECK_DELETE],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

RESIDENCY_XPATH = "//select[@name='input_4']"
EMAIL_XPATH = "//input[@name='input_3']"


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    checkbox_ids = [entry for right in rights for entry in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        # Residency select — full state name
        residency_select = await tab.find(tag_name="select", name="input_4", raise_exc=False)
        if residency_select:
            state_opt = await residency_select.find(tag_name="option", value=SuperScraper.STATE, raise_exc=False)
            if state_opt:
                await state_opt.click()
            else:
                print(f"{super_scraper.OOPS} State '{SuperScraper.STATE}' not in residency dropdown")
        time.sleep(0.5)

        # Email field
        email_field = await tab.find(tag_name="input", name="input_3", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        # Rights checkboxes
        for cb_id in checkbox_ids:
            cb = await tab.find(id=cb_id, raise_exc=False)
            if cb:
                await cb.click()
            time.sleep(0.3)

        # Leave honeypot input_13 untouched

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {"Residency": RESIDENCY_XPATH, "Email": EMAIL_XPATH})

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} for "
                f"{SuperScraper.EMAIL} / state={SuperScraper.STATE}"
            )
            submit_btn = await tab.find(id="gform_submit_button_11", raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            return

        submit_btn = await tab.find(id="gform_submit_button_11", raise_exc=False)
        if not submit_btn:
            print(f"{super_scraper.OOPS} Submit button not found")
            return
        await submit_btn.click()
        await asyncio.sleep(5)

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())
