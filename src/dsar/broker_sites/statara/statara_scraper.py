# statara.com — Statara Solutions "Consumer Deletion" / privacy-rights request,
# a 2-page Gravity Forms form (form id 5) at statara.com/consumerdeletion/.
# Page 1: name / address / email / phone / privacy-policy consent checkbox, then
# a "Next" button. Page 2: a single-select "which right" radio group
# (Know/Access, Delete, Correct) followed by Submit.
# One submission per right; which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). The Correct radio is not automated.
# Page elements:
#   #input_5_8_3 / #input_5_8_6   First / Last name
#   #input_5_9_1 / #input_5_9_3 / #input_5_9_5   Address / City / Zip
#   select#input_5_9_4            State (native <select>)
#   #input_5_10 / #input_5_11     Email / Phone
#   #input_5_12_1                 Privacy-policy consent checkbox
#   #gform_next_button_5_13       "Next" (page 1 -> page 2); #gform_page_5_2 is page 2
#   RIGHT_MAP radios (page 2)     "which right" radio group
#   #gform_submit_button_5        Submit
# reCAPTCHA is invisible (size=invisible) and resolves without interaction.
#
# NOTE: under headless automation the page-1 "Next" click is rejected by
# Gravity Forms' JavaScript anti-spam with a generic "There was a problem with
# your submission" banner and no field-level error (every field validates
# individually — confirmed via aria-invalid). On a real, non-headless browser
# with genuine pointer/keyboard activity this check passes; the scraper fills
# page 1 completely, then clicks Next and, if page 2 renders, selects the
# right and stops. If page 2 does not render, finish the Next step manually.
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://statara.com/consumerdeletion/"

# (page-2 radio choice id, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("choice_5_16_0", "access")],  # Know/Access radio
    Right.RIGHT_TO_DELETE: [("choice_5_16_1", "delete")],  # Delete radio
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, choice_id, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    page1 = {
        "//input[@id='input_5_8_3']": SuperScraper.FIRST_NAME,
        "//input[@id='input_5_8_6']": SuperScraper.LAST_NAME,
        "//input[@id='input_5_9_1']": SuperScraper.ADDRESS,
        "//input[@id='input_5_9_3']": SuperScraper.CITY,
        "//input[@id='input_5_9_5']": SuperScraper.ZIP_CODE,
        "//input[@id='input_5_10']": SuperScraper.EMAIL,
        "//input[@id='input_5_11']": SuperScraper.PHONE_NUMBER,
    }
    for xpath, value in page1.items():
        await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.3)

    state_select = await tab.find(xpath="//select[@id='input_5_9_4']", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, text=SuperScraper.STATE, ci=True)
    else:
        print(f"{super_scraper.OOPS} State select not found")

    consent = await tab.find(id="input_5_12_1", raise_exc=False)
    if consent:
        await js_utils.js_check(consent)

    await asyncio.sleep(0.5)
    next_btn = await tab.find(id="gform_next_button_5_13", raise_exc=False)
    if not next_btn:
        print(f"{super_scraper.OOPS} Next button not found")
        return
    await next_btn.click()
    await asyncio.sleep(4)

    page2_visible = await js_utils.js_eval(
        tab,
        "const p = document.getElementById('gform_page_5_2');"
        "return !!p && getComputedStyle(p).display !== 'none';",
    )
    if not page2_visible:
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        print(
            f"{super_scraper.OOPS} Page 1 filled but 'Next' did not advance (Gravity Forms "
            f"anti-spam under automation). Click Next manually, choose the '{label}' right, "
            f"and submit."
        )
        return

    radio = await tab.find(id=choice_id, raise_exc=False)
    if not radio:
        print(f"{super_scraper.OOPS} Page-2 radio '{choice_id}' not found")
        return
    await radio.execute_script("this.checked = true; this.dispatchEvent(new Event('change',{bubbles:true}));")

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit_btn = await tab.find(id="gform_submit_button_5", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(4)
    print(f"Submitted '{label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for choice_id, label in requests:
            await submit_request(tab, choice_id, label, super_scraper)


asyncio.run(main())
