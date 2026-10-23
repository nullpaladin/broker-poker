# clarivate.com — single general DSAR request form (no per-right-type picker, no free-text
# message box). OneTrust Angular portal. Country of Residence is an autocomplete combobox —
# must type then click the dropdown option; setting .value alone is insufficient.
# reCAPTCHA v2 requires manual user solve before submit.
# The form cannot say WHICH right is being exercised, so RIGHT_MAP lists every right as
# the same "general request"; rights_to_exercise() only decides whether to run at all, and
# the one general request is submitted once.
#
# Page elements:
#   [aria-label="Myself"]        "Myself" request-subject choice
#   #countryDSARElement          Country of Residence autocomplete -> "United States"
#   #stateDSARElement            State autocomplete (appears after choosing United States)
#   #subjectTypesDSARElement     "This request is for:" autocomplete -> "Customer"
#   #firstNameDSARElement        First name
#   #lastNameDSARElement         Last name
#   [role=option]                Autocomplete dropdown entries
import asyncio
import json

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/7636e208-dda4-4218-8026-e1bc155873fc/ae937376-9b21-4996-9327-81eaaa1b20f9"

GENERAL_REQUEST = "general request"
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: GENERAL_REQUEST,
    Right.RIGHT_TO_OPT_OUT: GENERAL_REQUEST,
    Right.RIGHT_TO_DELETE: GENERAL_REQUEST,
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: GENERAL_REQUEST,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (One general request form: there is no rights chooser to inventory.)

FIELD_XPATHS = {
    "Country of residence": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "This request is for": "//*[@id='subjectTypesDSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        # Select "Myself"
        await tab.execute_script(
            "document.querySelector('[aria-label=\"Myself\"]').click();"
        )

        # Country autocomplete — must type then select from dropdown
        country_input = await tab.find(
            xpath="//input[@id='countryDSARElement']",
            timeout=10,
            raise_exc=False,
        )
        if not country_input:
            print(f"{super_scraper.OOPS} Country input not found")
            return
        await country_input.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        clicked = await tab.execute_script(
            "var opts = Array.from(document.querySelectorAll('[role=option]'));"
            "var opt = opts.find(o => o.innerText.trim() === 'United States' && o.offsetParent !== null);"
            "if (opt) { opt.click(); return true; } return false;"
        )
        if not clicked:
            print(f"{super_scraper.OOPS} 'United States' option not found in country dropdown")

        await asyncio.sleep(1)

        # State autocomplete — appears dynamically after selecting United States
        state_input = await tab.find(
            xpath="//input[@id='stateDSARElement']",
            timeout=8,
            raise_exc=False,
        )
        if state_input:
            await state_input.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(2)
            state_name = json.dumps(SuperScraper.STATE)
            clicked = await tab.execute_script(
                f"var opts = Array.from(document.querySelectorAll('[role=option]'));"
                f"var opt = opts.find(o => o.innerText.trim() === {state_name} && o.offsetParent !== null);"
                f"if (opt) {{ opt.click(); return true; }} return false;"
            )
            if not clicked:
                print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found in dropdown")
        else:
            print(f"{super_scraper.OOPS} State field not found — may not be required for this country")

        await asyncio.sleep(1)

        # Subject type autocomplete — "This request is for:" (data subject role, not DSAR right type).
        # "Customer" is the most applicable category for a general data broker DSAR.
        subject_input = await tab.find(
            xpath="//input[@id='subjectTypesDSARElement']",
            timeout=8,
            raise_exc=False,
        )
        if subject_input:
            await subject_input.click()
            await tab.keyboard.type_text("Customer")
            await asyncio.sleep(2)
            clicked = await tab.execute_script(
                "var opts = Array.from(document.querySelectorAll('[role=option]'));"
                "var opt = opts.find(o => o.innerText.trim() === 'Customer' && o.offsetParent !== null);"
                "if (opt) { opt.click(); return true; } return false;"
            )
            if not clicked:
                print(f"{super_scraper.OOPS} 'Customer' option not found in subject type dropdown")
        else:
            print(f"{super_scraper.OOPS} Subject type field not found")

        await asyncio.sleep(1)

        # Name fields
        for field_id, value in (
            ("firstNameDSARElement", SuperScraper.FIRST_NAME),
            ("lastNameDSARElement", SuperScraper.LAST_NAME),
        ):
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await js_utils.js_set_value(field, str(value))

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "dry_run_general_request")
            print(f"DRY RUN: would submit a general request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            return

        print(f"\nForm filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}.")
        print("Solve the reCAPTCHA in the browser, then click Submit.")
        print("Press Enter after submission completes...")
        input()

        print(f"Submitted general request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} — confirm in the browser.")


asyncio.run(main())
